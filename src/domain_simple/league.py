"""
联赛领域模型
"""

from datetime import datetime
from typing import Any,  Dict[str, Any],  Any, List[Any]
from enum import Enum


class LeagueStatus(Enum):
    """联赛状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    SUSPENDED = "suspended"


class LeagueTable:
    """联赛积分榜"""

    def __init__(self):
        self.standings: List[Dict[str, Any] = []
        self.last_updated = datetime.now()

    def update_table(self, match_results: List[Dict[str, Any]) -> None:
        """更新积分榜"""
        # 简化实现，实际会更复杂
        self.last_updated = datetime.now()

    def get_position(self, team_id: int) -> Optional[int]:
        """获取球队排名"""
        for i, standing in enumerate(self.standings):
            if standing["team_id"] == team_id:
                return i + 1
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "standings": self.standings,
            "last_updated": self.last_updated.isoformat(),
        }


class League:
    """联赛领域模型"""

    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        country: str = "",
        season: str = "",
        status: LeagueStatus = LeagueStatus.ACTIVE,
    ):
        self.id = id
        self.name = name
        self.country = country
        self.season = season
        self.status = status

        # 联赛配置
        self.total_teams = 0
        self.matches_per_team = 0
        self.points_for_win = 3
        self.points_for_draw = 1

        # 积分榜
        self.table = LeagueTable()

        # 时间戳
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # 统计数据
        self.total_matches = 0
        self.completed_matches = 0

    def activate(self) -> None:
        """激活联赛"""
        self.status = LeagueStatus.ACTIVE
        self.updated_at = datetime.now()

    def deactivate(self) -> None:
        """停用联赛"""
        self.status = LeagueStatus.INACTIVE
        self.updated_at = datetime.now()

    def complete(self) -> None:
        """完成联赛"""
        self.status = LeagueStatus.COMPLETED
        self.updated_at = datetime.now()

    def update_statistics(self, total_matches: int, completed_matches: int) -> None:
        """更新统计"""
        self.total_matches = total_matches
        self.completed_matches = completed_matches
        self.updated_at = datetime.now()

    def get_completion_rate(self) -> float:
        """获取完成率"""
        if self.total_matches == 0:
            return 0.0
        return (self.completed_matches / self.total_matches) * 100

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "season": self.season,
            "status": self.status.value,
            "total_teams": self.total_teams,
            "matches_per_team": self.matches_per_team,
            "points_for_win": self.points_for_win,
            "points_for_draw": self.points_for_draw,
            "table": self.table.to_dict(),
            "total_matches": self.total_matches,
            "completed_matches": self.completed_matches,
            "completion_rate": self.get_completion_rate(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "League":
        """从字典创建实例"""
        league = cls(
            id=data.get("id"),
            name=data.get("name", ""),
            country=data.get("country", ""),
            season=data.get("season", ""),
            status=LeagueStatus(data.get("status", "active")),
        )

        league.total_teams = data.get("total_teams", 0)
        league.matches_per_team = data.get("matches_per_team", 0)
        league.points_for_win = data.get("points_for_win", 3)
        league.points_for_draw = data.get("points_for_draw", 1)

        # 设置统计数据
        league.total_matches = data.get("total_matches", 0)
        league.completed_matches = data.get("completed_matches", 0)

        # 设置时间戳
        if data.get("created_at"):
            league.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            league.updated_at = datetime.fromisoformat(data["updated_at"])

        return league

    def __str__(self) -> str:
        return f"League({self.name} - {self.season})"

    def __repr__(self) -> str:
        return f"<League(id={self.id}, name={self.name}, status={self.status.value})>"
