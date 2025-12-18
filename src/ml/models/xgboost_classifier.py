#!/usr/bin/env python3
"""
M4模块: XGBoost分类器模型

实现高性能的XGBoost 1X2分类模型，严格遵循MLOps最佳实践。
提供完整的模型生命周期管理，包括训练、预测、评估和持久化。

核心功能:
1. XGBoost分类器封装，支持1X2分类任务
2. 模型训练和预测的统一接口
3. 超参数管理和模型版本控制
4. 模型持久化和加载功能
5. 特征重要性分析和模型解释

设计原则:
- MLOps驱动: 符合机器学习运维最佳实践
- 可配置性: 无硬编码，所有参数可配置
- 健壮性: 完整的错误处理和验证
- 可解释性: 提供特征重要性等解释性信息
- 性能优化: 支持GPU加速和并行计算

依赖关系:
- M4.1: src/ml/dataset/dataset_generator.py - 训练数据
- 外部: xgboost, scikit-learn, pandas, numpy
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import dataclasses

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class XGBoostModelConfig:
    """
    XGBoost模型配置类

    包含所有模型超参数，避免硬编码，支持实验跟踪和参数调优。
    """
    # 基础模型参数
    max_depth: int = 6
    learning_rate: float = 0.1
    n_estimators: int = 100
    min_child_weight: int = 1
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    colsample_bylevel: float = 0.8
    colsample_bynode: float = 0.8

    # 正则化参数
    gamma: float = 0.0
    reg_alpha: float = 0.0  # L1正则化
    reg_lambda: float = 1.0  # L2正则化

    # 训练参数
    random_state: int = 42
    n_jobs: int = -1
    objective: str = 'multi:softprob'
    num_class: int = 3  # HOME_WIN(2), DRAW(1), AWAY_WIN(0)
    eval_metric: str = 'mlogloss'
    early_stopping_rounds: int = 10

    # 高级参数
    tree_method: str = 'hist'  # 'hist', 'approx', 'exact'
    grow_policy: str = 'depthwise'  # 'depthwise', 'lossguide'
    max_leaves: int = 0
    max_bin: int = 256

    # 数据处理参数
    test_size: float = 0.2
    validation_split: float = 0.2

    # 模型元数据
    model_name: str = "football_1x2_classifier"
    model_version: str = "1.0.0"
    created_by: str = "M4_XGBoost_Training_Pipeline"

    @classmethod
    def create_default(cls) -> 'XGBoostModelConfig':
        """创建默认配置"""
        return cls()

    @classmethod
    def create_for_fine_tuning(cls) -> 'XGBoostModelConfig':
        """创建用于微调的配置（更保守的参数）"""
        return cls(
            max_depth=4,
            learning_rate=0.05,
            n_estimators=200,
            early_stopping_rounds=20,
            reg_alpha=0.1,
            reg_lambda=2.0
        )

    @classmethod
    def create_for_fast_training(cls) -> 'XGBoostModelConfig':
        """创建用于快速训练的配置（速度优先）"""
        return cls(
            max_depth=3,
            learning_rate=0.2,
            n_estimators=50,
            early_stopping_rounds=5,
            tree_method='hist',
            max_bin=128
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'XGBoostModelConfig':
        """从字典创建配置"""
        return cls(**config_dict)

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """保存配置到文件"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"模型配置已保存到: {file_path}")

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'XGBoostModelConfig':
        """从文件加载配置"""
        with open(file_path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)

        return cls.from_dict(config_dict)


class XGBoostClassifier(BaseEstimator, ClassifierMixin):
    """
    XGBoost 1X2分类器

    封装XGBoost模型，提供训练、预测、评估和持久化的统一接口。
    专门针对足球比赛1X2预测任务优化，支持多分类和概率预测。

    主要功能:
    - 模型训练和验证
    - 分类预测和概率输出
    - 性能评估和指标计算
    - 模型保存和加载
    - 特征重要性分析
    - 模型解释和调试

    使用示例:
        # 创建分类器
        config = XGBoostModelConfig.create_default()
        classifier = XGBoostClassifier(config)

        # 训练模型
        metrics = classifier.train(X_train, y_train, X_val, y_val)

        # 预测
        predictions = classifier.predict(X_test)
        probabilities = classifier.predict_proba(X_test)

        # 保存模型
        classifier.save_model("models/xgboost_classifier.pkl")
    """

    def __init__(self, config: Optional[XGBoostModelConfig] = None):
        """
        初始化XGBoost分类器

        Args:
            config: 模型配置，如果为None则使用默认配置
        """
        self.config = config or XGBoostModelConfig.create_default()
        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_names: Optional[List[str]] = None
        self.classes_: Optional[np.ndarray] = None
        self.training_history: Dict[str, Any] = {}
        self.is_trained: bool = False

        # 设置sklearn兼容的估计器类型
        self._estimator_type = "classifier"

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 初始化模型
        self._initialize_model()

    def _initialize_model(self) -> None:
        """初始化XGBoost模型"""
        try:
            self.model = xgb.XGBClassifier(
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                n_estimators=self.config.n_estimators,
                min_child_weight=self.config.min_child_weight,
                subsample=self.config.subsample,
                colsample_bytree=self.config.colsample_bytree,
                colsample_bylevel=self.config.colsample_bylevel,
                colsample_bynode=self.config.colsample_bynode,
                gamma=self.config.gamma,
                reg_alpha=self.config.reg_alpha,
                reg_lambda=self.config.reg_lambda,
                random_state=self.config.random_state,
                n_jobs=self.config.n_jobs,
                objective=self.config.objective,
                num_class=self.config.num_class,
                eval_metric=self.config.eval_metric,
                tree_method=self.config.tree_method,
                grow_policy=self.config.grow_policy,
                max_leaves=self.config.max_leaves,
                max_bin=self.config.max_bin,
                early_stopping_rounds=self.config.early_stopping_rounds,
                verbosity=1
            )

            self.logger.info(f"XGBoost模型初始化成功: {self.config.model_name} v{self.config.model_version}")

        except Exception as e:
            self.logger.error(f"模型初始化失败: {e}")
            raise

    def train(self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray],
              X_val: Optional[Union[pd.DataFrame, np.ndarray]] = None,
              y_val: Optional[Union[pd.Series, np.ndarray]] = None) -> Dict[str, float]:
        """
        训练XGBoost分类器

        Args:
            X: 训练特征
            y: 训练标签
            X_val: 验证特征（可选）
            y_val: 验证标签（可选）

        Returns:
            Dict[str, float]: 训练和验证的性能指标

        Raises:
            ValueError: 当输入数据格式错误时
            Exception: 当训练失败时
        """
        self.logger.info("开始训练XGBoost分类器")

        try:
            # 验证输入数据
            X_train, y_train = self._validate_training_data(X, y)

            # 处理验证数据
            eval_set = None
            if X_val is not None and y_val is not None:
                X_val_clean, y_val_clean = self._validate_training_data(X_val, y_val)
                eval_set = [(X_val_clean, y_val_clean)]
                self.logger.info(f"使用验证集: {X_val_clean.shape}")

            # 记录特征名称
            if isinstance(X_train, pd.DataFrame):
                self.feature_names = X_train.columns.tolist()
            else:
                self.feature_names = [f"feature_{i}" for i in range(X_train.shape[1])]

            # 记录类别
            self.classes_ = np.unique(y_train)
            self.logger.info(f"检测到类别: {self.classes_}")

            # 根据是否有验证集调整早停参数
            if eval_set is None:
                # 没有验证集，禁用早停
                original_early_stopping = self.model.early_stopping_rounds
                self.model.early_stopping_rounds = None

            # 训练模型
            start_time = datetime.now()

            try:
                self.model.fit(
                    X_train, y_train,
                    eval_set=eval_set,
                    verbose=False
                )
            finally:
                # 恢复早停参数
                if eval_set is None and 'original_early_stopping' in locals():
                    self.model.early_stopping_rounds = original_early_stopping

            training_time = (datetime.now() - start_time).total_seconds()

            # 计算训练指标
            train_metrics = self._calculate_metrics_after_training(X_train, y_train, prefix="train")

            # 计算验证指标
            val_metrics = {}
            if X_val is not None and y_val is not None:
                val_metrics = self._calculate_metrics_after_training(X_val, y_val, prefix="val")

            # 合并指标
            all_metrics = {**train_metrics, **val_metrics}
            all_metrics['training_time_seconds'] = training_time
            all_metrics['n_features'] = X_train.shape[1]
            all_metrics['n_samples'] = X_train.shape[0]
            all_metrics['n_estimators_used'] = getattr(self.model, 'best_iteration', self.model.n_estimators)

            # 记录训练历史
            self.training_history = {
                'config': self.config.to_dict(),
                'metrics': all_metrics,
                'feature_names': self.feature_names,
                'classes': self.classes_.tolist(),
                'training_time': training_time,
                'trained_at': datetime.now().isoformat()
            }

            self.is_trained = True

            self.logger.info(f"模型训练完成，耗时: {training_time:.2f}秒")
            self.logger.info(f"训练准确率: {all_metrics['train_accuracy']:.3f}")
            if val_metrics:
                self.logger.info(f"验证准确率: {all_metrics['val_accuracy']:.3f}")

            return all_metrics

        except Exception as e:
            self.logger.error(f"模型训练失败: {e}")
            raise

    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        预测分类标签

        Args:
            X: 预测特征

        Returns:
            np.ndarray: 预测的类别标签

        Raises:
            RuntimeError: 当模型未训练时
        """
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，请先调用train()方法")

        try:
            predictions = self.model.predict(X)
            return predictions
        except Exception as e:
            self.logger.error(f"预测失败: {e}")
            raise

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        预测分类概率

        Args:
            X: 预测特征

        Returns:
            np.ndarray: 预测的概率矩阵，shape为(n_samples, n_classes)

        Raises:
            RuntimeError: 当模型未训练时
        """
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，请先调用train()方法")

        try:
            probabilities = self.model.predict_proba(X)
            return probabilities
        except Exception as e:
            self.logger.error(f"概率预测失败: {e}")
            raise

    def evaluate(self, X: Union[pd.DataFrame, np.ndarray],
                 y: Union[pd.Series, np.ndarray]) -> Dict[str, float]:
        """
        评估模型性能

        Args:
            X: 测试特征
            y: 测试标签

        Returns:
            Dict[str, float]: 评估指标
        """
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，请先调用train()方法")

        return self._calculate_metrics(X, y, prefix="test")

    def get_feature_importance(self, importance_type: str = 'gain') -> pd.DataFrame:
        """
        获取特征重要性

        Args:
            importance_type: 重要性类型 ('gain', 'weight', 'cover', 'total_gain', 'total_cover')

        Returns:
            pd.DataFrame: 特征重要性表，按重要性降序排列
        """
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，请先调用train()方法")

        try:
            # 获取特征重要性分数
            importance_scores = self.model.get_booster().get_score(importance_type=importance_type)

            # 转换为DataFrame
            importance_df = pd.DataFrame([
                {'feature_name': f.split('f')[1] if f.startswith('f') else f,
                 'importance': score}
                for f, score in importance_scores.items()
            ])

            # 映射到实际特征名称
            if self.feature_names:
                importance_df['feature_display_name'] = importance_df['feature_name'].apply(
                    lambda x: self.feature_names[int(x)] if x.isdigit() else x
                )
            else:
                importance_df['feature_display_name'] = importance_df['feature_name']

            # 按重要性排序
            importance_df = importance_df.sort_values('importance', ascending=False)

            return importance_df

        except Exception as e:
            self.logger.error(f"获取特征重要性失败: {e}")
            raise

    def save_model(self, model_path: Union[str, Path],
                   include_config: bool = True) -> None:
        """
        保存模型到文件

        Args:
            model_path: 模型文件路径
            include_config: 是否包含配置文件
        """
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，请先调用train()方法")

        try:
            model_path = Path(model_path)
            model_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存模型 - 使用pickle保存整个模型对象
            import pickle
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)

            # 保存额外信息
            metadata = {
                'feature_names': self.feature_names,
                'classes': self.classes_.tolist() if self.classes_ is not None else None,
                'training_history': self.training_history,
                'model_config': self.config.to_dict(),
                'saved_at': datetime.now().isoformat(),
                'model_name': self.config.model_name,
                'model_version': self.config.model_version
            }

            metadata_path = model_path.with_suffix('.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # 保存配置文件
            if include_config:
                config_path = model_path.with_suffix('.config.json')
                self.config.save_to_file(config_path)

            self.logger.info(f"模型已保存到: {model_path}")

        except Exception as e:
            self.logger.error(f"模型保存失败: {e}")
            raise

    @classmethod
    def load_model(cls, model_path: Union[str, Path]) -> 'XGBoostClassifier':
        """
        从文件加载模型

        Args:
            model_path: 模型文件路径

        Returns:
            XGBoostClassifier: 加载的模型实例
        """
        try:
            model_path = Path(model_path)

            # 加载元数据
            metadata_path = model_path.with_suffix('.json')
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                # 重建配置
                config = XGBoostModelConfig.from_dict(metadata['model_config'])
            else:
                # 使用默认配置
                config = XGBoostModelConfig.create_default()
                metadata = {}

            # 创建分类器实例
            classifier = cls(config)

            # 使用pickle加载模型对象
            import pickle
            with open(model_path, 'rb') as f:
                try:
                    model_data = pickle.load(f)  # nosec B301
                    # 安全验证：确保是XGBoost模型
                    if not hasattr(model_data, 'predict'):
                        raise ValueError("加载的模型不是有效的XGBoost预测模型")
                    classifier.model = model_data
                    classifier.is_trained = True
                except (pickle.PickleError, EOFError, AttributeError, ValueError) as e:
                    raise ValueError(f"模型文件损坏或格式错误: {e}")

            # 恢复元数据
            if metadata:
                classifier.feature_names = metadata.get('feature_names')
                classifier.classes_ = np.array(metadata['classes']) if metadata.get('classes') else None
                classifier.training_history = metadata.get('training_history', {})

            logger.info(f"模型已从 {model_path} 加载")
            return classifier

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise

    def _validate_training_data(self, X: Union[pd.DataFrame, np.ndarray],
                               y: Union[pd.Series, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """验证和预处理训练数据"""
        # 转换为numpy数组
        if isinstance(X, pd.DataFrame):
            X_array = X.values
        else:
            X_array = np.array(X)

        if isinstance(y, pd.Series):
            y_array = y.values
        else:
            y_array = np.array(y)

        # 验证形状
        if X_array.shape[0] != y_array.shape[0]:
            raise ValueError(f"特征和标签的样本数不匹配: X={X_array.shape[0]}, y={y_array.shape[0]}")

        # 验证标签范围
        unique_labels = np.unique(y_array)
        if not all(label in [0, 1, 2] for label in unique_labels):
            logger.warning(f"检测到非标准标签: {unique_labels}，期望: [0, 1, 2] (AWAY_WIN, DRAW, HOME_WIN)")

        # 处理NaN值
        if np.isnan(X_array).any():
            logger.warning("检测到NaN值，使用0填充")
            X_array = np.nan_to_num(X_array, nan=0.0)

        return X_array, y_array

    def _calculate_metrics_after_training(self, X: Union[pd.DataFrame, np.ndarray],
                                           y: Union[pd.Series, np.ndarray],
                                           prefix: str = "") -> Dict[str, float]:
        """计算训练后的性能指标（模型已训练完成）"""
        y_pred = self.model.predict(X)  # 直接使用model，不调用self.predict
        self.model.predict_proba(X)

        # 基础指标
        accuracy = accuracy_score(y, y_pred)
        precision = precision_score(y, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y, y_pred, average='weighted', zero_division=0)

        # 各类别指标
        precision_per_class = precision_score(y, y_pred, average=None, zero_division=0)
        recall_per_class = recall_score(y, y_pred, average=None, zero_division=0)
        f1_per_class = f1_score(y, y_pred, average=None, zero_division=0)

        metrics = {
            f"{prefix}_accuracy": accuracy,
            f"{prefix}_precision_weighted": precision,
            f"{prefix}_recall_weighted": recall,
            f"{prefix}_f1_weighted": f1,
        }

        # 添加各类别指标
        labels = [0, 1, 2]  # AWAY_WIN, DRAW, HOME_WIN
        label_names = ['AWAY_WIN', 'DRAW', 'HOME_WIN']

        for i, (label, name) in enumerate(zip(labels, label_names)):
            if i < len(precision_per_class):
                metrics[f"{prefix}_precision_{name}"] = precision_per_class[i]
                metrics[f"{prefix}_recall_{name}"] = recall_per_class[i]
                metrics[f"{prefix}_f1_{name}"] = f1_per_class[i]

        return metrics

    def _calculate_metrics(self, X: Union[pd.DataFrame, np.ndarray],
                          y: Union[pd.Series, np.ndarray],
                          prefix: str = "") -> Dict[str, float]:
        """计算性能指标"""
        y_pred = self.predict(X)
        self.predict_proba(X)

        # 基础指标
        accuracy = accuracy_score(y, y_pred)
        precision = precision_score(y, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y, y_pred, average='weighted', zero_division=0)

        # 各类别指标
        precision_per_class = precision_score(y, y_pred, average=None, zero_division=0)
        recall_per_class = recall_score(y, y_pred, average=None, zero_division=0)
        f1_per_class = f1_score(y, y_pred, average=None, zero_division=0)

        metrics = {
            f"{prefix}_accuracy": accuracy,
            f"{prefix}_precision_weighted": precision,
            f"{prefix}_recall_weighted": recall,
            f"{prefix}_f1_weighted": f1,
        }

        # 添加各类别指标
        labels = [0, 1, 2]  # AWAY_WIN, DRAW, HOME_WIN
        label_names = ['AWAY_WIN', 'DRAW', 'HOME_WIN']

        for i, (label, name) in enumerate(zip(labels, label_names)):
            if i < len(precision_per_class):
                metrics[f"{prefix}_precision_{name}"] = precision_per_class[i]
                metrics[f"{prefix}_recall_{name}"] = recall_per_class[i]
                metrics[f"{prefix}_f1_{name}"] = f1_per_class[i]

        return metrics

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        info = {
            'model_name': self.config.model_name,
            'model_version': self.config.model_version,
            'is_trained': self.is_trained,
            'config': self.config.to_dict(),
            'feature_names': self.feature_names,
            'n_features': len(self.feature_names) if self.feature_names else 0,
            'classes': self.classes_.tolist() if self.classes_ is not None else None,
            'training_history': self.training_history
        }

        if self.is_trained:
            info['n_estimators'] = getattr(self.model, 'best_iteration', self.model.n_estimators)
            info['model_params'] = self.model.get_params()

        return info


# 便捷函数
def create_xgboost_classifier(config_type: str = "default") -> XGBoostClassifier:
    """
    创建XGBoost分类器的便捷函数

    Args:
        config_type: 配置类型 ("default", "fine_tuning", "fast_training")

    Returns:
        XGBoostClassifier: 分类器实例
    """
    config_map = {
        "default": XGBoostModelConfig.create_default,
        "fine_tuning": XGBoostModelConfig.create_for_fine_tuning,
        "fast_training": XGBoostModelConfig.create_for_fast_training
    }

    if config_type not in config_map:
        raise ValueError(f"未知的配置类型: {config_type}，可用选项: {list(config_map.keys())}")

    config = config_map[config_type]()
    return XGBoostClassifier(config)


if __name__ == "__main__":
    # 模块测试

    try:
        # 创建配置
        config = XGBoostModelConfig.create_default()

        # 创建分类器
        classifier = XGBoostClassifier(config)

        # 创建模拟数据
        np.random.seed(42)
        n_samples = 1000
        n_features = 13  # 对应Phase 5特征数量

        X = np.random.randn(n_samples, n_features)
        y = np.random.choice([0, 1, 2], n_samples, p=[0.28, 0.26, 0.46])  # 基于先验概率

        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )


        # 训练模型
        metrics = classifier.train(X_train, y_train, X_test, y_test)

        # 预测
        predictions = classifier.predict(X_test[:5])
        probabilities = classifier.predict_proba(X_test[:5])

        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            # 处理每个预测结果
            pass

        # 特征重要性
        importance_df = classifier.get_feature_importance()
        for _, row in importance_df.head().iterrows():
            # 处理特征重要性
            pass


    except Exception as e:
        import traceback
        traceback.print_exc()
        exit(1)