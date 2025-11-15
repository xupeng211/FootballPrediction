"""
特征工程主模块

足球预测系统的特征工程入口：
- 特征计算器接口
- 特征存储接口
- 特征管理工具
"""

from .entities import MatchEntity, TeamEntity

# 导入engineering相关类
try:
        AllMatchFeatures,
        AllTeamFeatures,
        HistoricalMatchupFeatures,
        OddsFeatures,
        RecentPerformanceFeatures,
    )
except ImportError:
    AllMatchFeatures = None
    AllTeamFeatures = None
    HistoricalMatchupFeatures = None
    OddsFeatures = None
    RecentPerformanceFeatures = None

from .features.feature_calculator_calculators import FeatureCalculator

# 导出主要接口
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
