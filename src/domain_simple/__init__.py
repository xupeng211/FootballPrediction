from .league import League, LeagueTable
from .match import Match, MatchResult, MatchStatus
from .odds import MarketType, Odds, ValueBet
from .prediction import Prediction, PredictionConfidence, PredictionType
from .rules import BusinessRules, ValidationEngine
from .services import DomainServiceFactory
from .team import Team, TeamStatistics
from .user import User, UserPreferences, UserProfile

"""
简化的领域模型模块

包含核心业务逻辑和领域实体.
"""

__all__ = [
    # 核心实体
    "Match",
    "MatchStatus",
    "MatchResult",
    "Team",
    "TeamStatistics",
    "Prediction",
    "PredictionType",
    "PredictionConfidence",
    "League",
    "LeagueTable",
    "User",
    "UserProfile",
    "UserPreferences",
    "Odds",
    "MarketType",
    "ValueBet",
    # 业务规则
    "BusinessRules",
    "ValidationEngine",
    # 工厂
    "DomainServiceFactory",
]
