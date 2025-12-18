"""
Football Prediction ML Pipeline
足球预测机器学习流水线

统一的模型训练、评估和部署流水线。
集成FeatureStore、DataQualityMonitor和现代化ML工程最佳实践。

主要组件:
- FeatureLoader: 统一特征加载和数据质量管理
- Trainer: 多算法训练调度器
- ModelRegistry: 模型版本管理和保存
- Evaluator: 模型评估和指标计算
- Flows: Prefect工作流编排

Author: ML Engineering Team
Version: P0-4
"""

from .config import (
    PipelineConfig,
    FeatureConfig,
    ModelConfig,
    TrainingConfig,
    EvaluationConfig,
)

from .feature_loader import FeatureLoader
from .trainer import Trainer
from .model_registry import ModelRegistry

__version__ = "0.4.0"
__all__ = [
    "PipelineConfig",
    "FeatureConfig",
    "ModelConfig",
    "TrainingConfig",
    "EvaluationConfig",
    "FeatureLoader",
    "Trainer",
    "ModelRegistry",
]
