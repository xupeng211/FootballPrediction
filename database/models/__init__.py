"""
足球预测系统数据模型

包含所有SQLAlchemy数据模型定义。
"""

from .features import Features, TeamType
from .league import League
from .match import Match, MatchStatus
from .odds import MarketType, Odds
from .predictions import PredictedResult, Predictions
from .team import Team

# 导出所有模型和枚举类
__all__ = [
    # 模型类
    "League",
    "Team",
    "Match",
    "Odds",
    "Features",
    "Predictions",
    # 枚举类
    "MatchStatus",
    "MarketType",
    "TeamType",
    "PredictedResult",
]
