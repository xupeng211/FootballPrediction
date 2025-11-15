"""
预测策略模块
Prediction Strategies Module

提供各种预测算法的策略模式实现.
Provides strategy pattern implementation for various prediction algorithms.
"""

    PredictionContext,
    PredictionInput,
    PredictionOutput,
    PredictionStrategy,
    StrategyMetrics,
    StrategyType,
)

# 导入具体策略实现
try:
    from .config import StrategyConfig
    from .enhanced_ml_model import EnhancedMLModel
    from .ensemble import EnsembleStrategy
    from .factory import PredictionStrategyFactory
    from .historical import HistoricalStrategy
    from .ml_model import MLModelStrategy
        EloStrategy,
        PoissonStrategy,
        StatisticalStrategy,
    )
except ImportError:
    EnhancedMLModel = None
    MLModelStrategy = None
    EloStrategy = None
    PoissonStrategy = None
    StatisticalStrategy = None
    HistoricalStrategy = None
    EnsembleStrategy = None
    PredictionStrategyFactory = None
    StrategyConfig = None

__all__ = [
    # 基础类
    "PredictionContext",
    "PredictionInput",
    "PredictionOutput",
    "PredictionStrategy",
    "StrategyMetrics",
    "StrategyType",
    # 配置
    "StrategyConfig",
    # 工厂
    "PredictionStrategyFactory",
    # 具体策略
    "EnhancedMLModel",
    "MLModelStrategy",
    "EloStrategy",
    "PoissonStrategy",
    "StatisticalStrategy",
    "HistoricalStrategy",
    "EnsembleStrategy",
]
