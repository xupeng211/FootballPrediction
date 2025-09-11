"""
特征实体定义

定义足球预测系统中的核心实体：
- MatchEntity: 比赛实体，用于比赛级别的特征
- TeamEntity: 球队实体，用于球队级别的特征
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class MatchEntity:
    """
    比赛实体

    用于标识比赛级别的特征，包含比赛的基本信息
    """

    match_id: int
    home_team_id: int
    away_team_id: int
    league_id: int
    match_time: datetime
    season: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "match_id": self.match_id,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "league_id": self.league_id,
            "match_time": self.match_time.isoformat(),
            "season": self.season,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchEntity":
        """从字典创建实体"""
        return cls(
            match_id=data["match_id"],
            home_team_id=data["home_team_id"],
            away_team_id=data["away_team_id"],
            league_id=data["league_id"],
            match_time=datetime.fromisoformat(data["match_time"]),
            season=data["season"],
        )


@dataclass
class TeamEntity:
    """
    球队实体

    用于标识球队级别的特征，包含球队的基本信息
    """

    team_id: int
    team_name: str
    league_id: int
    home_venue: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "league_id": self.league_id,
            "home_venue": self.home_venue,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamEntity":
        """从字典创建实体"""
        return cls(
            team_id=data["team_id"],
            team_name=data["team_name"],
            league_id=data["league_id"],
            home_venue=data.get("home_venue"),
        )


@dataclass
class FeatureKey:
    """
    特征键，用于唯一标识一个特征记录
    """

    entity_type: str  # "match" 或 "team"
    entity_id: int  # match_id 或 team_id
    feature_timestamp: datetime

    def __hash__(self) -> int:
        return hash((self.entity_type, self.entity_id, self.feature_timestamp))

    def __eq__(self, other) -> bool:
        if not isinstance(other, FeatureKey):
            return False
        return (
            self.entity_type == other.entity_type
            and self.entity_id == other.entity_id
            and self.feature_timestamp == other.feature_timestamp
        )
