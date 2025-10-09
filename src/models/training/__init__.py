"""
模型训练模块

提供模块化的模型训练功能：
- 基准模型训练器
- 特征数据处理
- MLflow 实验管理
- 工具函数
"""


from .features.feature_processor import FeatureProcessor
from .mlflow.experiment_manager import ExperimentManager
from .trainer.baseline_trainer import BaselineModelTrainer
from .utils.data_utils import calculate_match_result

__all__ = [
    "BaselineModelTrainer",
    "FeatureProcessor",
    "ExperimentManager",
    "calculate_match_result",
]
