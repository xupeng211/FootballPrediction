from .entities import MatchEntity, TeamEntity
from .feature_definitions import (
    AllMatchFeatures,
    AllTeamFeatures,
    HistoricalMatchupFeatures,
    OddsFeatures,
    RecentPerformanceFeatures,
)
from .features.feature_calculator_calculators import FeatureCalculator

"""
特征工程主模块

足球预测系统的特征工程入口：
- 特征计算器接口
- 特征存储接口
- 特征管理工具
"""

__all__ = [
    "FeatureCalculator",
    "RecentPerformanceFeatures",
    "HistoricalMatchupFeatures",
    "OddsFeatures",
    "AllMatchFeatures",
    "AllTeamFeatures",
    "MatchEntity",
    "TeamEntity",
]
