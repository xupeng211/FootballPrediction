"""
MLOps 模型重训练服务

负责执行完整的机器学习模型重训练流水线，包括数据获取、训练、评估和部署。
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, log_loss, classification_report
from sklearn.model_selection import train_test_split

from src.config import get_settings
from src.ml.data.postgres_loader import PostgreSQLDataLoader
from src.ml.features.advanced_feature_transformer import AdvancedFeatureTransformer

logger = logging.getLogger(__name__)


class ModelMetadata:
    """模型元数据类"""

    def __init__(
        self,
        version: str,
        accuracy: float,
        log_loss: float,
        training_samples: int,
        feature_count: int,
        training_time: float,
        model_path: str,
        created_at: datetime,
        description: str = "",
    ):
        self.version = version
        self.accuracy = accuracy
        self.log_loss = log_loss
        self.training_samples = training_samples
        self.feature_count = feature_count
        self.training_time = training_time
        self.model_path = model_path
        self.created_at = created_at
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "version": self.version,
            "accuracy": self.accuracy,
            "log_loss": self.log_loss,
            "training_samples": self.training_samples,
            "feature_count": self.feature_count,
            "training_time": self.training_time,
            "model_path": self.model_path,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelMetadata":
        """从字典创建实例"""
        return cls(
            version=data["version"],
            accuracy=data["accuracy"],
            log_loss=data["log_loss"],
            training_samples=data["training_samples"],
            feature_count=data["feature_count"],
            training_time=data["training_time"],
            model_path=data["model_path"],
            created_at=datetime.fromisoformat(data["created_at"]),
            description=data.get("description", ""),
        )


class ModelRegistry:
    """模型注册表，管理模型版本和元数据"""

    def __init__(self, models_dir: str):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.models_dir / "registry.json"
        self.current_best_file = self.models_dir / "current_best.txt"

        # 初始化注册表
        if not self.registry_file.exists():
            self._init_registry()

    def _init_registry(self):
        """初始化模型注册表"""
        registry = {
            "models": {},
            "current_best": None,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        self._save_registry(registry)

    def _load_registry(self) -> Dict[str, Any]:
        """加载模型注册表"""
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._init_registry()
            return self._load_registry()

    def _save_registry(self, registry: Dict[str, Any]):
        """保存模型注册表"""
        registry["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

    def register_model(self, metadata: ModelMetadata) -> bool:
        """注册新模型"""
        registry = self._load_registry()

        # 检查版本是否已存在
        if metadata.version in registry["models"]:
            logger.warning(f"模型版本 {metadata.version} 已存在，将被覆盖")

        # 添加模型到注册表
        registry["models"][metadata.version] = metadata.to_dict()

        # 更新当前最佳模型
        current_best = registry.get("current_best")
        if not current_best:
            registry["current_best"] = metadata.version
        else:
            current_accuracy = registry["models"][current_best]["accuracy"]
            if metadata.accuracy > current_accuracy:
                registry["current_best"] = metadata.version
                logger.info(
                    f"新模型 {metadata.version} 成为最佳模型 (准确率: {metadata.accuracy:.4f})"
                )

        # 保存注册表
        self._save_registry(registry)

        # 更新当前最佳文件
        with open(self.current_best_file, "w", encoding="utf-8") as f:
            f.write(registry["current_best"])

        return True

    def get_current_best(self) -> Optional[ModelMetadata]:
        """获取当前最佳模型"""
        registry = self._load_registry()
        current_best = registry.get("current_best")

        if not current_best or current_best not in registry["models"]:
            return None

        return ModelMetadata.from_dict(registry["models"][current_best])

    def get_model_metadata(self, version: str) -> Optional[ModelMetadata]:
        """获取指定版本的模型元数据"""
        registry = self._load_registry()
        model_data = registry["models"].get(version)

        if not model_data:
            return None

        return ModelMetadata.from_dict(model_data)

    def list_models(self) -> List[ModelMetadata]:
        """列出所有注册的模型"""
        registry = self._load_registry()
        return [
            ModelMetadata.from_dict(model_data)
            for model_data in registry["models"].values()
        ]

    def switch_current_best(self, version: str) -> bool:
        """切换当前最佳模型"""
        registry = self._load_registry()

        if version not in registry["models"]:
            logger.error(f"模型版本 {version} 不存在")
            return False

        registry["current_best"] = version
        self._save_registry(registry)

        with open(self.current_best_file, "w", encoding="utf-8") as f:
            f.write(version)

        logger.info(f"当前最佳模型已切换到 {version}")
        return True


class RetrainingService:
    """模型重训练服务"""

    def __init__(self):
        self.settings = get_settings()
        self.models_dir = Path(self.settings.model_path)
        self.registry = ModelRegistry(str(self.models_dir))
        self.data_loader = PostgreSQLDataLoader()
        self.feature_transformer = AdvancedFeatureTransformer()

        # 重训练配置
        self.improvement_threshold = 0.005  # 准确率提升阈值 0.5%
        self.min_samples = 1000  # 最少训练样本数
        self.test_size = 0.2  # 测试集比例

    def execute_pipeline(
        self, description: str = "Scheduled retraining"
    ) -> Dict[str, Any]:
        """
        执行完整的重训练流水线

        Args:
            description: 训练描述

        Returns:
            训练结果字典
        """
        start_time = time.time()
        logger.info("🚀 开始执行模型重训练流水线")

        try:
            # 1. 数据获取
            logger.info("📊 步骤 1/5: 获取训练数据...")
            X, y = self._fetch_training_data()

            if len(X) < self.min_samples:
                logger.warning(f"训练样本数不足: {len(X)} < {self.min_samples}")
                return {
                    "status": "failed",
                    "reason": f"Insufficient training samples: {len(X)}",
                    "training_time": time.time() - start_time,
                }

            # 2. 数据预处理
            logger.info("🔄 步骤 2/5: 数据预处理...")
            X_processed = self._preprocess_data(X)

            # 3. 模型训练
            logger.info("🤖 步骤 3/5: 训练新模型...")
            model, feature_count = self._train_model(X_processed, y)

            # 4. 模型评估
            logger.info("📈 步骤 4/5: 评估模型性能...")
            metrics = self._evaluate_model(model, X_processed, y)

            # 5. 模型注册
            logger.info("💾 步骤 5/5: 注册新模型...")
            result = self._register_model_if_improved(
                model, metrics, feature_count, start_time, description
            )

            return result

        except Exception as e:
            logger.error(f"❌ 重训练流水线失败: {str(e)}", exc_info=True)
            return {
                "status": "failed",
                "reason": str(e),
                "training_time": time.time() - start_time,
            }

    def _fetch_training_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """获取训练数据"""
        # 获取最近 6 个月的比赛数据
        df = self.data_loader.load_recent_matches(months=6)

        if df.empty:
            raise ValueError("无法获取训练数据")

        # 分离特征和标签
        feature_columns = [col for col in df.columns if col != "target"]
        X = df[feature_columns]
        y = df["target"]

        logger.info(f"获取到 {len(X)} 条训练数据")
        return X, y

    def _preprocess_data(self, X: pd.DataFrame) -> pd.DataFrame:
        """数据预处理"""
        # 移除缺失值过多的列
        threshold = len(X) * 0.8  # 80% 以上非空
        X = X.dropna(axis=1, thresh=threshold)

        # 填充缺失值
        numeric_columns = X.select_dtypes(include=[np.number]).columns
        X[numeric_columns] = X[numeric_columns].fillna(X[numeric_columns].median())

        # 特征工程
        X_transformed = self.feature_transformer.transform(X)

        logger.info(f"预处理后特征维度: {X_transformed.shape[1]}")
        return X_transformed

    def _train_model(
        self, X: pd.DataFrame, y: pd.Series
    ) -> Tuple[xgb.XGBClassifier, int]:
        """训练 XGBoost 模型"""
        # 分割训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=42, stratify=y
        )

        # 训练模型
        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
            eval_metric="logloss",
            use_label_encoder=False,
        )

        model.fit(X_train, y_train)

        feature_count = X.shape[1]
        logger.info(f"模型训练完成，特征数量: {feature_count}")

        return model, feature_count

    def _evaluate_model(
        self, model: xgb.XGBClassifier, X: pd.DataFrame, y: pd.Series
    ) -> Dict[str, float]:
        """评估模型性能"""
        # 分割训练集和测试集
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=42, stratify=y
        )

        # 预测
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)

        # 计算指标
        accuracy = accuracy_score(y_test, y_pred)
        logloss = log_loss(y_test, y_pred_proba)

        # 分类报告
        report = classification_report(y_test, y_pred, output_dict=True)

        metrics = {
            "accuracy": accuracy,
            "log_loss": logloss,
            "macro_precision": report["macro avg"]["precision"],
            "macro_recall": report["macro avg"]["recall"],
            "macro_f1": report["macro avg"]["f1-score"],
        }

        logger.info(f"模型评估结果 - 准确率: {accuracy:.4f}, LogLoss: {logloss:.4f}")

        return metrics

    def _register_model_if_improved(
        self,
        model: xgb.XGBClassifier,
        metrics: Dict[str, float],
        feature_count: int,
        start_time: float,
        description: str,
    ) -> Dict[str, Any]:
        """如果模型性能有提升则注册新模型"""
        training_time = time.time() - start_time
        accuracy = metrics["accuracy"]
        log_loss = metrics["log_loss"]

        # 生成版本号
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        version = f"v2.1.{timestamp}"

        # 保存模型文件
        model_path = self.models_dir / f"{version}.json"
        model.save_model(str(model_path))

        # 创建模型元数据
        metadata = ModelMetadata(
            version=version,
            accuracy=accuracy,
            log_loss=log_loss,
            training_samples=len(self._fetch_training_data()[0]),
            feature_count=feature_count,
            training_time=training_time,
            model_path=str(model_path),
            created_at=datetime.now(timezone.utc),
            description=description,
        )

        # 检查是否应该部署新模型
        current_best = self.registry.get_current_best()
        should_deploy = False
        improvement = 0.0

        if current_best is None:
            should_deploy = True
            improvement = 0.0
            logger.info("这是第一个模型，自动部署")
        else:
            current_accuracy = current_best.accuracy
            improvement = accuracy - current_accuracy

            if improvement > self.improvement_threshold:
                should_deploy = True
                logger.info(
                    f"新模型性能提升 {improvement:.4f}，超过阈值 {self.improvement_threshold}"
                )
            else:
                logger.info(
                    f"新模型性能提升 {improvement:.4f}，未达到阈值 {self.improvement_threshold}"
                )

        # 注册模型
        self.registry.register_model(metadata)

        result = {
            "status": "success" if should_deploy else "trained_not_deployed",
            "version": version,
            "metrics": metrics,
            "improvement": improvement,
            "threshold": self.improvement_threshold,
            "should_deploy": should_deploy,
            "training_time": training_time,
            "description": description,
        }

        # 记录日志
        if should_deploy:
            logger.info(f"✅ 新模型 {version} 已成功部署！")
        else:
            logger.info(f"📊 新模型 {version} 已训练但未部署（性能未达标）")

        return result

    def rollback_model(self, target_version: str) -> Dict[str, Any]:
        """回滚到指定版本"""
        if self.registry.switch_current_best(target_version):
            logger.info(f"✅ 成功回滚到模型版本 {target_version}")
            return {
                "status": "success",
                "version": target_version,
                "message": f"已回滚到模型版本 {target_version}",
            }
        else:
            logger.error(f"❌ 回滚失败，模型版本 {target_version} 不存在")
            return {
                "status": "failed",
                "reason": f"Model version {target_version} not found",
            }

    def get_training_status(self) -> Dict[str, Any]:
        """获取训练状态和历史"""
        models = self.registry.list_models()
        current_best = self.registry.get_current_best()

        # 按创建时间排序
        models.sort(key=lambda x: x.created_at, reverse=True)

        return {
            "total_models": len(models),
            "current_best": current_best.to_dict() if current_best else None,
            "recent_models": [
                {
                    "version": model.version,
                    "accuracy": model.accuracy,
                    "log_loss": model.log_loss,
                    "created_at": model.created_at.isoformat(),
                    "description": model.description,
                }
                for model in models[:10]  # 最近 10 个模型
            ],
        }
