"""
预测策略模块
Prediction Strategies Module

提供各种预测策略实现，包括：
- 机器学习策略
- 统计策略
- 历史对战策略
- 集成策略
"""

from .base import (
    PredictionStrategy,
    StrategyMetrics,
    StrategyType,
    PredictionInput,
    PredictionOutput,
    PredictionContext,
)

# 导入具体策略实现
try:
    from .ml_model import MLModelStrategy
    from .statistical import StatisticalStrategy
    from .historical import HistoricalStrategy
    from .ensemble import EnsembleStrategy
    from .enhanced_ml_model import EnhancedMLModelStrategy
    from .factory import PredictionStrategyFactory
except ImportError as e:
    # 如果某些策略模块不存在，提供占位符
    MLModelStrategy = None
    StatisticalStrategy = None
    HistoricalStrategy = None
    EnsembleStrategy = None
    EnhancedMLModelStrategy = None
    PredictionStrategyFactory = None

# 预测相关的类型
try:
    from .base import PredictionContext, PredictionInput, PredictionOutput
except ImportError:
    PredictionContext = None
    PredictionInput = None
    PredictionOutput = None

# 异常类 - 暂时占位符
StrategyCreationError = Exception
StrategyConfigurationError = Exception

__all__ = [
    # 基础类
    "PredictionStrategy",
    "StrategyConfig",
    "StrategyMetrics",
    "StrategyType",
    # 具体策略
    "MLModelStrategy",
    "StatisticalStrategy",
    "HistoricalStrategy",
    "EnsembleStrategy",
    "EnhancedMLModelStrategy",
    # 工厂和配置
    "PredictionStrategyFactory",
    "StrategyConfig",
    # 类型定义
    "PredictionContext",
    "PredictionInput",
    "PredictionOutput",
    # 异常
    "StrategyCreationError",
    "StrategyConfigurationError",
]