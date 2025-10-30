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
from .config import StrategyConfig
from .ensemble import EnsembleStrategy
from .factory import PredictionStrategyFactory
from .historical import HistoricalStrategy
from .ml_model import MLModelStrategy
from .statistical import StatisticalStrategy

__all__ = [
    # 基础接口
    "PredictionStrategy",
    "PredictionContext",
    "PredictionInput",
    "PredictionOutput",
    "StrategyType",
    "StrategyMetrics",
    # 具体策略
    "MLModelStrategy",
    "StatisticalStrategy",
    "HistoricalStrategy",
    "EnsembleStrategy",
    # 工厂和配置
    "PredictionStrategyFactory",
    "StrategyConfig",
]
