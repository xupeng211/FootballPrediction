"""
特征计算器

实现足球预测系统的核心特征计算逻辑：
- 近期战绩特征计算
- 历史对战特征计算
- 赔率特征计算
- 批量特征计算和缓存

该文件已重构为模块化架构，原始功能现在通过以下模块提供：
- recent_performance: 近期战绩特征计算
- historical_matchup: 历史对战特征计算
- odds_features: 赔率特征计算
- batch_calculator: 批量计算优化
- statistics_utils: 统计工具函数
"""

# 为了向后兼容，从新的模块化实现重新导出所有类
from .feature_calculator_mod import (
    FeatureCalculator,
    RecentPerformanceCalculator,
    HistoricalMatchupCalculator,
    OddsFeaturesCalculator,
    BatchCalculator,
    StatisticsUtils,
    stats_utils,
)

# 为了向后兼容，重新导出统计函数
from .feature_calculator_mod import (
    calculate_mean,
    calculate_std,
    calculate_min,
    calculate_max,
    calculate_rolling_mean,
)

# 保持原有的 __all__ 导出以维持兼容性
__all__ = [
    "FeatureCalculator",
    "RecentPerformanceCalculator",
    "HistoricalMatchupCalculator",
    "OddsFeaturesCalculator",
    "BatchCalculator",
    "StatisticsUtils",
    "stats_utils",
    "calculate_mean",
    "calculate_std",
    "calculate_min",
    "calculate_max",
    "calculate_rolling_mean",
]