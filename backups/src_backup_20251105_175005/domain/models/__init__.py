"""
领域模型
Domain Models

包含足球预测系统的核心领域模型.
Contains core domain models for the football prediction system.
"""

from src.domain.models.league import League, LeagueSeason, LeagueSettings
from src.domain.models.match import Match, MatchResult, MatchScore, MatchStatus
from src.domain.models.prediction import (
    ConfidenceScore,
    Prediction,
    PredictionPoints,
    PredictionScore,
    PredictionStatus,
)
from src.domain.models.team import Team, TeamForm, TeamStats

__all__ = [
    # 比赛
    "Match",
    "MatchStatus",
    "MatchResult",
    "MatchScore",
    # 预测
    "Prediction",
    "PredictionStatus",
    "ConfidenceScore",
    "PredictionScore",
    "PredictionPoints",
    # 球队
    "Team",
    "TeamStats",
    "TeamForm",
    # 联赛
    "League",
    "LeagueSeason",
    "LeagueSettings",
]
