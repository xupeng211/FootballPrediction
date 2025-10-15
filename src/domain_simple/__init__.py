from typing import Any, Dict, List, Optional, Union

"""
简化的领域模型模块

包含核心业务逻辑和领域实体。
"""

from .match import Match, MatchStatus, MatchResult
from .team import Team, TeamStatistics
from .prediction import Prediction, PredictionType, PredictionConfidence
from .league import League, LeagueTable
from .user import User, UserProfile, UserPreferences
from .odds import Odds, MarketType, ValueBet
from .rules import BusinessRules, ValidationEngine
from .services import DomainServiceFactory

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
