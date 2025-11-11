"""
特征管理模块

本模块提供足球预测系统的特征工程和特征存储功能,支持：
- 特征实体定义:match_id, team_id
- 核心特征计算:近期战绩,历史对战,赔率特征
- 在线特征和离线特征两种模式
- Feast特征存储集成
"""

from .entities import MatchEntity, TeamEntity
from .feature_calculator import FeatureCalculator

# 导入__init__相关类
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


# from .feature_store import FootballFeatureStore  # 暂时禁用有问题的导入

__all__ = [
    "MatchEntity",
    "TeamEntity",
    "RecentPerformanceFeatures",
    "HistoricalMatchupFeatures",
    "OddsFeatures",
    "AllMatchFeatures",
    "AllTeamFeatures",
    # "FootballFeatureStore",  # 暂时禁用
    "FeatureCalculator",
]
