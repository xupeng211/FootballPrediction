
"""

"""




from .entities import MatchEntity, TeamEntity
from .feature_calculator import FeatureCalculator
from .feature_definitions import (
from .feature_store import FootballFeatureStore

特征管理模块
本模块提供足球预测系统的特征工程和特征存储功能,支持:
- 特征实体定义:match_id, team_id
- 核心特征计算:近期战绩、历史对战、赔率特征
- 在线特征和离线特征两种模式
- Feast特征存储集成
    AllMatchFeatures, Any, Optional, Union
    AllTeamFeatures,
    HistoricalMatchupFeatures,
    OddsFeatures,
    RecentPerformanceFeatures,
)
__all__ = [
    "MatchEntity",
    "TeamEntity",
    "RecentPerformanceFeatures",
    "HistoricalMatchupFeatures",
    "OddsFeatures",
    "AllMatchFeatures",
    "AllTeamFeatures",
    "FootballFeatureStore",
    "FeatureCalculator",
]