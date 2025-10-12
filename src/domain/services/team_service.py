"""球队领域服务

提供围绕球队聚合的高级业务操作，例如比赛结果更新、
球队信息维护以及联赛积分榜计算。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from ..models.team import Team, TeamForm, TeamStats


class TeamRepositoryProtocol(Protocol):
    """球队仓储协议。"""

    def save(self, team: Team) -> Team:  # pragma: no cover - 协议定义
        ...

    def update(self, team: Team) -> Team:  # pragma: no cover - 协议定义
        ...


@dataclass(frozen=True)
class TeamStatsEvent:
    """球队统计更新事件快照."""

    team_id: int
    result: str
    goals_for: int
    goals_against: int
    matches_played: int
    points: int
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class TeamProfileUpdatedEvent:
    """球队资料更新事件."""

    team_id: int
    updated_fields: Dict[str, Any]
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class TeamPerformanceResetEvent:
    """球队表现重置事件."""

    team_id: int
    occurred_at: datetime = field(default_factory=datetime.utcnow)


class TeamDomainService:
    """球队领域服务"""

    def __init__(self, repository: Optional[TeamRepositoryProtocol] = None) -> None:
        self._events: List[Any] = []
        self._repository = repository

    def attach_repository(self, repository: TeamRepositoryProtocol) -> None:
        """绑定仓储实现。"""
        self._repository = repository

    def update_team_profile(
        self,
        team: Team,
        name: Optional[str] = None,
        short_name: Optional[str] = None,
        stadium: Optional[str] = None,
        capacity: Optional[int] = None,
    ) -> None:
        """批量更新球队基础信息。"""
        original = {
            "name": team.name,
            "short_name": team.short_name,
            "stadium": team.stadium,
            "capacity": team.capacity,
        }

        team.update_info(
            name=name, short_name=short_name, stadium=stadium, capacity=capacity
        )

        changed_fields: Dict[str, Any] = {}
        if name is not None and team.name != original["name"]:
            changed_fields["name"] = team.name
        if short_name is not None and team.short_name != original["short_name"]:
            changed_fields["short_name"] = team.short_name
        if stadium is not None and team.stadium != original["stadium"]:
            changed_fields["stadium"] = team.stadium
        if capacity is not None and team.capacity != original["capacity"]:
            changed_fields["capacity"] = team.capacity

        if changed_fields:
            self._events.append(
                TeamProfileUpdatedEvent(
                    team_id=team.id or 0, updated_fields=changed_fields
                )
            )
            self._persist(team)

    def record_match_result(
        self,
        team: Team,
        result: str,
        goals_for: int,
        goals_against: int,
    ) -> Team:
        """记录一场比赛的结果并更新球队统计。"""
        team.add_match_result(result, goals_for, goals_against)

        stats = team.stats  # type: ignore[assignment]
        if stats:
            event = TeamStatsEvent(
                team_id=team.id or 0,
                result=result,
                goals_for=goals_for,
                goals_against=goals_against,
                matches_played=stats.matches_played,
                points=stats.points,
            )
            self._events.append(event)

        self._persist(team)

        return team

    def reset_team_performance(self, team: Team) -> None:
        """重置球队的统计和状态信息。"""
        team.stats = TeamStats()
        team.form = TeamForm()
        self._events.append(
            TeamPerformanceResetEvent(team_id=team.id or 0)
        )
        self._persist(team)

    def calculate_league_table(self, teams: List[Team]) -> List[Dict[str, Any]]:
        """根据球队当前统计生成积分榜。"""
        table = []
        for team in teams:
            stats = team.stats or TeamStats()
            table.append(
                {
                    "team_id": team.id,
                    "name": team.name,
                    "points": stats.points,
                    "goal_difference": stats.goal_difference,
                    "goals_for": stats.goals_for,
                }
            )

        table.sort(
            key=lambda item: (
                item["points"],
                item["goal_difference"],
                item["goals_for"],
                item["name"].lower(),
            ),
            reverse=True,
        )
        return table

    def get_domain_events(self) -> List[Any]:
        """返回当前收集到的领域事件快照。"""
        return self._events.copy()

    def clear_domain_events(self) -> None:
        """清空领域事件缓存。"""
        self._events.clear()

    def _persist(self, team: Team) -> Team:
        """将球队状态同步到仓储（如有）。"""
        if not self._repository:
            return team

        if getattr(team, "id", None) is None:
            return self._repository.save(team)

        return self._repository.update(team)
