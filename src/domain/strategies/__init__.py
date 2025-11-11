"""
预测策略模块
Prediction Strategies Module

提供各种预测算法的策略模式实现.
Provides strategy pattern implementation for various prediction algorithms.
"""

from .base import (
    PredictionContext,
    PredictionInput,
    PredictionOutput,
    PredictionStrategy,
    StrategyMetrics,
    StrategyType,
)

# 导入具体策略实现
try:
    from .enhanced_ml_model import EnhancedMLModel
    from .ml_model import MLModel
    from .statistical import (
        EloStrategy,
        PoissonStrategy,
        StatisticalStrategy,
    )
except ImportError:
    EnhancedMLModel = None
    MLModel = None
    EloStrategy = None
    PoissonStrategy = None
    StatisticalStrategy = None

__all__ = [
    # 基础类
    "PredictionContext",
    "PredictionInput",
    "PredictionOutput",
    "PredictionStrategy",
    "StrategyMetrics",
    "StrategyType",
    # 具体策略
    "EnhancedMLModel",
    "MLModel",
    "EloStrategy",
    "PoissonStrategy",
    "StatisticalStrategy",
]
