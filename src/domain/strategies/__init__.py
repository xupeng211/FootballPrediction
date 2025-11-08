from src.domain.strategies.base import (
    PredictionContext,
    PredictionInput,
    PredictionOutput,
    PredictionStrategy,
    StrategyMetrics,
    StrategyType,
)
from src.domain.strategies.config import StrategyConfig
from src.domain.strategies.ensemble import EnsembleStrategy
from src.domain.strategies.factory import PredictionStrategyFactory
from src.domain.strategies.historical import HistoricalStrategy
from src.domain.strategies.ml_model import MLModelStrategy
from src.domain.strategies.statistical import StatisticalStrategy

"""
预测策略模块
Prediction Strategies Module

提供各种预测算法的策略模式实现.
Provides strategy pattern implementation for various prediction algorithms.
"""

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
