"""
足球数据模型
Football Data Models
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MatchStatus(Enum):
    """比赛状态枚举类"""

    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


@dataclass
class Team:
    """足球队数据模型"""

    id: str
    name: str
    short_name: str = ""
    country: str = ""
    founded: int = 1900


@dataclass
class Player:
    """足球运动员数据模型"""

    id: str
    name: str
    position: str
    age: int = 25
    team_id: str = ""


@dataclass
class Match:
    """足球比赛数据模型"""

    id: str
    home_team: Team
    away_team: Team
    start_time: datetime
    status: MatchStatus = MatchStatus.SCHEDULED
    home_score: int = 0
    away_score: int = 0


@dataclass
class FootballData:
    """足球API被适配者基类"""


def get_match_data(self, match_id: str) -> Match:
    """获取比赛数据"""
    raise NotImplementedError


def get_team_data(self, team_id: str) -> Team:
    """获取球队数据"""
    raise NotImplementedError


def get_player_data(self, player_id: str) -> Player:
    """获取球员数据"""
    raise NotImplementedError
