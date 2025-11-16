"""特征管理模块.

本模块提供足球预测系统的特征工程和特征存储功能,支持：
- 特征实体定义:match_id, team_id
- 核心特征计算:近期战绩,历史对战,赔率特征
- 在线特征和离线特征两种模式
- Feast特征存储集成
"""

from .entities import MatchEntity, TeamEntity
from .feature_store import FootballFeatureStore

# 导入特征定义类
try:
    from .feature_definitions import (
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

# 导入特征计算器
try:
    from .feature_calculator import FeatureCalculator
except ImportError:
    FeatureCalculator = None

__all__ = [
    # 实体
    "MatchEntity",
    "TeamEntity",
    # 特征存储
    "FootballFeatureStore",
    # 特征工程
    "AllMatchFeatures",
    "AllTeamFeatures",
    "HistoricalMatchupFeatures",
    "OddsFeatures",
    "RecentPerformanceFeatures",
    # 特征计算
    "FeatureCalculator",
]
