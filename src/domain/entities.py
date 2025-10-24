"""
领域实体模块 - 简化版本
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MatchStatus(Enum):
    """比赛状态枚举"""
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"


class TeamStatus(Enum):
    """队伍状态枚举"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


@dataclass
class Team:
    """队伍实体"""
    id: int
    name: str
    status: TeamStatus
    league_id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class Match:
    """比赛实体"""
    id: int
    home_team_id: int
    away_team_id: int
    league_id: int
    status: MatchStatus
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    home_score: Optional[int] = 0
    away_score: Optional[int] = 0


@dataclass
class League:
    """联赛实体"""
    id: int
    name: str
    country: str
    season: str
    is_active: bool = True


@dataclass
class Prediction:
    """预测实体"""
    id: int
    match_id: int
    user_id: int
    predicted_result: str
    confidence: float
    created_at: datetime
    is_correct: Optional[bool] = None


# 导出常用函数
def create_test_team(id: int, name: str) -> Team:
    """创建测试用队伍"""
    return Team(id=id, name=name, status=TeamStatus.ACTIVE)


def create_test_match(id: int, home_team: int, away_team: int) -> Match:
    """创建测试用比赛"""
    return Match(
        id=id,
        home_team_id=home_team,
        away_team_id=away_team,
        league_id=1,
        status=MatchStatus.SCHEDULED
    )


def validate_prediction_confidence(confidence: float) -> bool:
    """验证预测置信度"""
    return 0.0 <= confidence <= 1.0


__all__ = [
    'Team', 'Match', 'League', 'Prediction', 'MatchStatus', 'TeamStatus',
    'create_test_team', 'create_test_match', 'validate_prediction_confidence'
]