#!/usr/bin/env python3
"""
M4模块: XGBoost分类训练流水线

严格遵循TDD设计，实现完整的机器学习训练流水线。
整合数据加载、模型训练、评估和持久化的端到端流程。

核心功能:
1. 数据集加载和预处理
2. 训练/测试集分离
3. XGBoost模型训练和验证
4. 多维度性能评估 (Accuracy, Precision, Recall, F1-Score)
5. 模型持久化和元数据管理
6. 特征重要性分析和报告生成

依赖关系:
- M4.1: src/ml/dataset/dataset_generator.py - 训练数据生成
- M4.2: src/ml/models/xgboost_classifier.py - XGBoost模型实现
- 外部: pandas, numpy, scikit-learn, xgboost

MLOps规范:
- 无硬编码参数，全部通过配置管理
- 完整的实验跟踪和模型版本控制
- 自动化的数据验证和质量检查
- 标准化的评估指标和报告
- 模型可解释性和特征分析
"""

import json
import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import dataclasses

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# 导入M4模块组件
from ..models.xgboost_classifier import (
    create_xgboost_classifier,
)

# 设置日志
logger = logging.getLogger(__name__)

# 禁用警告
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


@dataclasses.dataclass
class TrainingPipelineConfig:
    """
    训练流水线配置类

    包含数据预处理、模型训练和评估的所有配置参数。
    """

    # 数据处理配置
    test_size: float = 0.2
    validation_split: float = 0.2
    random_state: int = 42
    stratify_split: bool = True

    # 特征处理配置
    normalize_features: bool = True
    handle_missing_values: str = "zero_fill"  # 'zero_fill', 'mean_fill', 'drop'
    feature_selection: bool = False
    max_features: Optional[int] = None

    # 模型配置类型
    model_config_type: str = "default"  # 'default', 'fine_tuning', 'fast_training'

    # 评估配置
    calculate_feature_importance: bool = True
    save_training_curves: bool = True
    cross_validation_folds: int = 5

    # 输出配置
    save_model_metadata: bool = True
    save_feature_importance: bool = True
    save_evaluation_report: bool = True

    # 实验跟踪
    experiment_name: str = "football_1x2_classification"
    experiment_version: str = "1.0.0"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "TrainingPipelineConfig":
        """从字典创建配置"""
        return cls(**config_dict)


class ClassificationTrainingPipeline:
    """
    1X2分类训练流水线

    实现完整的机器学习训练流程，从数据加载到模型部署。
    严格遵循MLOps最佳实践，提供可重现和可扩展的训练流程。

    主要工作流程:
    1. 加载和预处理训练数据集
    2. 特征工程和数据验证
    3. 训练/验证/测试集分离
    4. XGBoost模型训练和调优
    5. 多维度性能评估
    6. 模型持久化和元数据管理
    7. 特征重要性分析和报告

    使用示例:
        pipeline = ClassificationTrainingPipeline(
            model_output_dir="models/",
            config_type="fine_tuning"
        )

        metrics = await pipeline.run_pipeline(
            dataset_path="data/training_dataset.parquet",
            model_output_path="models/football_classifier.pkl"
        )

    """

    def __init__(
        self,
        model_output_dir: Union[str, Path],
        config: Optional[TrainingPipelineConfig] = None,
        config_type: str = "default",
    ):
        """
        初始化训练流水线

        Args:
            model_output_dir: 模型输出目录
            config: 流水线配置，如果为None则创建默认配置
            config_type: 模型配置类型 ('default', 'fine_tuning', 'fast_training')
        """
        self.model_output_dir = Path(model_output_dir)
        self.config = config or TrainingPipelineConfig()
        self.config_type = config_type

        # 创建输出目录
        self.model_output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化模型
        self.classifier = create_xgboost_classifier(config_type)

        # 内部状态
        self.feature_names: Optional[List[str]] = None
        self.feature_scaler: Optional[StandardScaler] = Optional[None]
        self.training_results: Dict[str, Any] = {}

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        self.logger.info(f"训练流水线初始化完成: {self.model_output_dir}")
        self.logger.info(f"模型配置类型: {config_type}")

    async def run_pipeline(
        self, dataset_path: str, model_output_path: str
    ) -> Dict[str, float]:
        """
        运行完整的训练流水线

        Args:
            dataset_path: 训练数据集路径 (Parquet格式)
            model_output_path: 模型输出路径

        Returns:
            Dict[str, float]: 训练和评估的性能指标

        Raises:
            FileNotFoundError: 当数据集文件不存在时
            ValueError: 当数据格式错误时
            Exception: 当训练过程失败时
        """
        start_time = datetime.now()
        self.logger.info(f"开始运行训练流水线: {dataset_path}")

        try:
            # 1. 加载和预处理数据
            self.logger.info("步骤 1/7: 加载和预处理数据")
            X, y, feature_names = await self._load_and_preprocess_data(dataset_path)

            # 2. 数据集分离
            self.logger.info("步骤 2/7: 数据集分离")
            X_train, X_test, y_train, y_test = self._split_dataset(X, y)

            # 3. 特征工程
            self.logger.info("步骤 3/7: 特征工程")
            X_train_processed, X_test_processed, y_train, y_test = (
                self._feature_engineering(X_train, X_test, y_train, y_test)
            )

            # 4. 模型训练
            self.logger.info("步骤 4/7: 模型训练")
            training_metrics = self._train_model(X_train_processed, y_train)

            # 5. 模型评估
            self.logger.info("步骤 5/7: 模型评估")
            evaluation_metrics = self._evaluate_model(X_test_processed, y_test)

            # 6. 模型保存
            self.logger.info("步骤 6/7: 模型保存")
            await self._save_model_and_metadata(
                model_output_path, feature_names, evaluation_metrics
            )

            # 7. 生成报告
            self.logger.info("步骤 7/7: 生成报告")
            await self._generate_reports(model_output_path, evaluation_metrics)

            # 合并指标
            all_metrics = {**training_metrics, **evaluation_metrics}
            all_metrics["total_training_time_seconds"] = (
                datetime.now() - start_time
            ).total_seconds()

            # 记录最终结果
            self.training_results = {
                "metrics": all_metrics,
                "config": self.config.to_dict(),
                "feature_names": feature_names,
                "model_path": model_output_path,
                "completed_at": datetime.now().isoformat(),
            }

            self.logger.info(
                f"训练流水线完成，耗时: {all_metrics['total_training_time_seconds']:.2f}秒"
            )
            self.logger.info(f"测试准确率: {all_metrics['test_accuracy']:.3f}")
            self.logger.info(f"测试F1分数: {all_metrics['test_f1_weighted']:.3f}")

            return all_metrics

        except Exception as e:
            self.logger.error(f"训练流水线失败: {e}")
            raise

    async def _load_and_preprocess_data(
        self, dataset_path: str
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        加载和预处理数据集

        Args:
            dataset_path: 数据集文件路径

        Returns:
            Tuple[np.ndarray, np.ndarray, List[str]]: 特征矩阵、标签向量、特征名称
        """
        # 验证文件存在
        dataset_file = Path(dataset_path)
        if not dataset_file.exists():
            raise FileNotFoundError(f"数据集文件不存在: {dataset_path}")

        # 加载数据
        try:
            df = pd.read_parquet(dataset_path)
            self.logger.info(f"成功加载数据集: {df.shape}")
        except Exception as e:
            raise ValueError(f"加载数据集失败: {e}") from e

        # 验证必需列
        required_columns = ["target_numeric"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"缺少必需列: {missing_columns}")

        # 提取特征列
        feature_columns = [col for col in df.columns if col.startswith("feature_")]
        if not feature_columns:
            raise ValueError("未找到特征列（以'feature_'开头）")

        self.logger.info(f"找到 {len(feature_columns)} 个特征列")

        # 提取特征和标签
        X = df[feature_columns].values
        y = df["target_numeric"].values

        # 数据质量检查
        self._validate_data_quality(X, y, feature_columns)

        # 保存特征名称
        self.feature_names = feature_columns

        return X, y, feature_columns

    def _validate_data_quality(
        self, X: np.ndarray, y: np.ndarray, feature_columns: List[str]
    ) -> None:
        """验证数据质量"""
        # 检查形状
        if X.shape[0] != len(y):
            raise ValueError(f"特征和标签样本数不匹配: X={X.shape[0]}, y={len(y)}")

        # 检查标签范围
        unique_labels = np.unique(y)
        invalid_labels = [label for label in unique_labels if label not in [0, 1, 2]]
        if invalid_labels:
            self.logger.warning(f"检测到无效标签: {invalid_labels}，将过滤这些样本")
            valid_mask = np.isin(y, [0, 1, 2])
            valid_count = np.sum(valid_mask)
            if valid_count < 100:  # 最少样本数检查
                raise ValueError(f"有效样本数太少: {valid_count}")

        # 检查缺失值
        nan_count = np.isnan(X).sum()
        if nan_count > 0:
            self.logger.info(f"检测到 {nan_count} 个NaN值，将在特征工程阶段处理")

        # 检查特征数量
        if len(feature_columns) < 5:
            self.logger.warning(f"特征数量较少: {len(feature_columns)}")

    def _split_dataset(
        self, X: np.ndarray, y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """分离训练集和测试集"""
        # 过滤有效样本
        valid_mask = np.isin(y, [0, 1, 2])
        X_clean = X[valid_mask]
        y_clean = y[valid_mask]

        self.logger.info(f"过滤后样本数: {len(y_clean)}")

        # 分离训练集和测试集
        if self.config.stratify_split:
            X_train, X_test, y_train, y_test = train_test_split(
                X_clean,
                y_clean,
                test_size=self.config.test_size,
                random_state=self.config.random_state,
                stratify=y_clean,
            )
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X_clean,
                y_clean,
                test_size=self.config.test_size,
                random_state=self.config.random_state,
            )

        self.logger.info(f"训练集: {X_train.shape}, 测试集: {X_test.shape}")

        # 验证标签分布
        train_dist = np.bincount(y_train)
        test_dist = np.bincount(y_test)
        self.logger.info(
            f"训练集标签分布: AWAY_WIN={train_dist[0]}, DRAW={train_dist[1]}, HOME_WIN={train_dist[2]}"
        )
        self.logger.info(
            f"测试集标签分布: AWAY_WIN={test_dist[0]}, DRAW={test_dist[1]}, HOME_WIN={test_dist[2]}"
        )

        return X_train, X_test, y_train, y_test

    def _feature_engineering(
        self,
        X_train: np.ndarray,
        X_test: np.ndarray,
        y_train: np.ndarray,
        y_test: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """特征工程"""
        X_train_processed = X_train.copy()
        X_test_processed = X_test.copy()

        # 处理缺失值
        if self.config.handle_missing_values == "zero_fill":
            X_train_processed = np.nan_to_num(X_train_processed, nan=0.0)
            X_test_processed = np.nan_to_num(X_test_processed, nan=0.0)
            self.logger.info("使用0填充缺失值")

        elif self.config.handle_missing_values == "mean_fill":
            from sklearn.impute import SimpleImputer

            imputer = SimpleImputer(strategy="mean")
            X_train_processed = imputer.fit_transform(X_train_processed)
            X_test_processed = imputer.transform(X_test_processed)
            self.logger.info("使用均值填充缺失值")

        # 特征标准化
        if self.config.normalize_features:
            self.feature_scaler = StandardScaler()
            X_train_processed = self.feature_scaler.fit_transform(X_train_processed)
            X_test_processed = self.feature_scaler.transform(X_test_processed)
            self.logger.info("应用特征标准化")

        # 特征选择（如果启用）
        if self.config.feature_selection and self.config.max_features:
            from sklearn.feature_selection import SelectKBest, f_classif

            selector = SelectKBest(
                f_classif, k=min(self.config.max_features, X_train_processed.shape[1])
            )
            X_train_processed = selector.fit_transform(X_train_processed, y_train)
            X_test_processed = selector.transform(X_test_processed)
            self.logger.info(f"应用特征选择，保留 {X_train_processed.shape[1]} 个特征")

        self.logger.info(f"特征工程完成，最终特征维度: {X_train_processed.shape[1]}")

        return X_train_processed, X_test_processed, y_train, y_test

    def _train_model(
        self, X_train: np.ndarray, y_train: np.ndarray
    ) -> Dict[str, float]:
        """训练模型"""
        # 分离验证集
        if self.config.validation_split > 0:
            X_train_main, X_val, y_train_main, y_val = train_test_split(
                X_train,
                y_train,
                test_size=self.config.validation_split,
                random_state=self.config.random_state,
                stratify=y_train,
            )
        else:
            X_train_main, y_train_main = X_train, y_train
            X_val, y_val = None, None

        # 训练模型
        training_metrics = self.classifier.train(
            X_train_main, y_train_main, X_val, y_val
        )

        self.logger.info(f"模型训练完成: {len(X_train_main)} 个训练样本")
        if X_val is not None:
            self.logger.info(
                f"验证准确率: {training_metrics.get('val_accuracy', 'N/A'):.3f}"
            )

        return training_metrics

    def _evaluate_model(
        self, X_test: np.ndarray, y_test: np.ndarray
    ) -> Dict[str, float]:
        """评估模型"""
        evaluation_metrics = self.classifier.evaluate(X_test, y_test)

        self.logger.info(f"模型评估完成: {len(X_test)} 个测试样本")
        self.logger.info(f"测试准确率: {evaluation_metrics['test_accuracy']:.3f}")
        self.logger.info(f"测试F1分数: {evaluation_metrics['test_f1_weighted']:.3f}")

        # 详细分类报告
        predictions = self.classifier.predict(X_test)
        from sklearn.metrics import classification_report

        report = classification_report(
            y_test,
            predictions,
            target_names=["AWAY_WIN", "DRAW", "HOME_WIN"],
            output_dict=True,
        )

        evaluation_metrics["classification_report"] = report

        return evaluation_metrics

    async def _save_model_and_metadata(
        self,
        model_output_path: str,
        feature_names: List[str],
        evaluation_metrics: Dict[str, float],
    ) -> None:
        """保存模型和元数据"""
        model_path = Path(model_output_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存模型
        self.classifier.save_model(model_path, include_config=True)

        # 保存元数据
        if self.config.save_model_metadata:
            metadata = {
                "experiment_name": self.config.experiment_name,
                "experiment_version": self.config.experiment_version,
                "pipeline_config": self.config.to_dict(),
                "model_config": self.classifier.config.to_dict(),
                "feature_names": feature_names,
                "n_features": len(feature_names),
                "evaluation_metrics": evaluation_metrics,
                "training_results": self.training_results,
                "model_info": self.classifier.get_model_info(),
                "saved_at": datetime.now().isoformat(),
                "notes": self.config.notes,
            }

            metadata_path = model_path.with_suffix(".json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"模型元数据已保存到: {metadata_path}")

    async def _generate_reports(
        self, model_output_path: str, evaluation_metrics: Dict[str, float]
    ) -> None:
        """生成训练报告"""
        output_dir = Path(model_output_path).parent

        # 特征重要性报告
        if (
            self.config.calculate_feature_importance
            and self.config.save_feature_importance
        ):
            await self._save_feature_importance_report(output_dir)

        # 评估报告
        if self.config.save_evaluation_report:
            await self._save_evaluation_report(output_dir, evaluation_metrics)

    async def _save_feature_importance_report(self, output_dir: Path) -> None:
        """保存特征重要性报告"""
        try:
            importance_df = self.classifier.get_feature_importance()

            # 保存为CSV
            importance_path = output_dir / "feature_importance.csv"
            importance_df.to_csv(importance_path, index=False)

            self.logger.info(f"特征重要性报告已保存到: {importance_path}")

        except Exception as e:
            self.logger.warning(f"特征重要性报告保存失败: {e}")

    async def _save_evaluation_report(
        self, output_dir: Path, evaluation_metrics: Dict[str, float]
    ) -> None:
        """保存评估报告"""
        try:
            report_path = output_dir / "evaluation_report.json"

            # 提取关键指标
            key_metrics = {
                "test_accuracy": evaluation_metrics.get("test_accuracy", 0),
                "test_precision_weighted": evaluation_metrics.get(
                    "test_precision_weighted", 0
                ),
                "test_recall_weighted": evaluation_metrics.get(
                    "test_recall_weighted", 0
                ),
                "test_f1_weighted": evaluation_metrics.get("test_f1_weighted", 0),
                "test_precision_HOME_WIN": evaluation_metrics.get(
                    "test_precision_HOME_WIN", 0
                ),
                "test_precision_DRAW": evaluation_metrics.get("test_precision_DRAW", 0),
                "test_precision_AWAY_WIN": evaluation_metrics.get(
                    "test_precision_AWAY_WIN", 0
                ),
                "classification_report": evaluation_metrics.get(
                    "classification_report", {}
                ),
            }

            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(key_metrics, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"评估报告已保存到: {report_path}")

        except Exception as e:
            self.logger.warning(f"评估报告保存失败: {e}")

    def get_training_summary(self) -> Dict[str, Any]:
        """获取训练摘要"""
        return self.training_results


# 便捷函数
async def train_classification_model(
    dataset_path: str,
    model_output_path: str,
    model_output_dir: str = "models/",
    config_type: str = "default",
    custom_config: Optional[TrainingPipelineConfig] = None,
) -> Dict[str, float]:
    """
    训练分类模型的便捷函数

    Args:
        dataset_path: 训练数据集路径
        model_output_path: 模型输出路径
        model_output_dir: 模型输出目录
        config_type: 配置类型
        custom_config: 自定义配置

    Returns:
        Dict[str, float]: 训练和评估指标
    """
    pipeline = ClassificationTrainingPipeline(
        model_output_dir=model_output_dir, config=custom_config, config_type=config_type
    )

    return await pipeline.run_pipeline(dataset_path, model_output_path)


if __name__ == "__main__":
    # 流水线演示
    async def main():
        """主函数 - 训练流水线演示"""

        try:
            # 创建示例数据集
            from ..dataset.dataset_generator import create_classification_dataset

            dataset_path = "demo_dataset.parquet"
            await create_classification_dataset(
                league_id="demo_league",
                start_date="2024-01-01",
                output_path=dataset_path,
            )

            # 创建训练流水线
            pipeline = ClassificationTrainingPipeline(
                model_output_dir="demo_models/",
                config_type="fast_training",  # 使用快速配置进行演示
            )

            # 运行训练流水线
            metrics = await pipeline.run_pipeline(
                dataset_path=dataset_path,
                model_output_path="demo_models/demo_football_classifier.pkl",
            )

            # 显示结果

            # 显示各类别指标
            logger.info(
                f"   主队获胜: 精确率={metrics.get('test_precision_HOME_WIN', 0):.3f}"
            )
            logger.info(
                f"   客队获胜: 精确率={metrics.get('test_precision_AWAY_WIN', 0):.3f}"
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return False

        return True

    # 运行演示
    success = main()
    if not success:
        exit(1)
