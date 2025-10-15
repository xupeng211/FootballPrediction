from typing import Any, Dict, List, Optional, Union

"""
领域模型
Domain Models

包含足球预测系统的核心领域模型。
Contains core domain models for the football prediction system.
"""

from .match import Match, MatchStatus, MatchResult, MatchScore
from .prediction import (
    Prediction,
    PredictionStatus,
    ConfidenceScore,
    PredictionScore,
    PredictionPoints,
)
from .team import Team, TeamStats, TeamForm
from .league import League, LeagueSeason, LeagueSettings

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
