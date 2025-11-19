"""球队领域服务".

提供围绕球队聚合的高级业务操作,例如比赛结果更新,
球队信息维护以及联赛积分榜计算.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from src.domain.models.team import Team, TeamForm, TeamStats


class TeamRepositoryProtocol(Protocol):
    """球队仓储协议."""

    def save(self, team: Team) -> Team:  # pragma: no cover - 协议定义
        ...

    def update(self, team: Team) -> Team:  # pragma: no cover - 协议定义
        ...


@dataclass(frozen=True)
class TeamStatsEvent:
    """类文档字符串."""

    pass  # 添加pass语句
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
    """类文档字符串."""

    pass  # 添加pass语句
    """球队资料更新事件."""

    team_id: int
    updated_fields: dict[str, Any]
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class TeamPerformanceResetEvent:
    """类文档字符串."""

    pass  # 添加pass语句
    """球队表现重置事件."""

    team_id: int
    occurred_at: datetime = field(default_factory=datetime.utcnow)


class TeamDomainService:
    """类文档字符串."""

    pass  # 添加pass语句
    """球队领域服务"""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        repository: TeamRepositoryProtocol | None = None,
    ) -> None:
        self._events: list[Any] = []
        self._repository = repository
        self._config = config or {}
        self._is_initialized = False
        self._is_disposed = False
        self._health_status = "healthy"
        self._created_at = datetime.utcnow()

    def initialize(self) -> bool:
        """初始化服务."""
        if self._is_disposed:
            raise RuntimeError("Cannot initialize disposed service")
        self._is_initialized = True
        return True

    def dispose(self) -> None:
        """销毁服务."""
        self._is_disposed = True
        self._is_initialized = False
        self._events.clear()

    def is_healthy(self) -> bool:
        """检查服务健康状态."""
        return self._health_status == "healthy" and not self._is_disposed

    def get_service_info(self) -> dict[str, Any]:
        """获取服务信息."""
        return {
            "name": "TeamDomainService",
            "initialized": self._is_initialized,
            "disposed": self._is_disposed,
            "healthy": self.is_healthy(),
            "created_at": self._created_at.isoformat() if self._created_at else None,
            "event_count": len(self._events),
            "config": self._config,
        }

    def attach_repository(self, repository: TeamRepositoryProtocol) -> None:
        """绑定仓储实现."""
        self._repository = repository

    def update_team_profile(
        self,
        team: Team,
        name: str | None = None,
        short_name: str | None = None,
        stadium: str | None = None,
        capacity: int | None = None,
    ) -> None:
        """批量更新球队基础信息."""
        original = {
            "name": team.name,
            "short_name": team.short_name,
            "stadium": team.stadium,
            "capacity": team.capacity,
        }

        team.update_info(
            name=name, short_name=short_name, stadium=stadium, capacity=capacity
        )

        changed_fields: dict[str, Any] = {}
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
        """记录一场比赛的结果并更新球队统计."""
        team.add_match_result(result, goals_for, goals_against)

        stats = team.stats
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
        """重置球队的统计和状态信息."""
        team.stats = TeamStats()
        team.form = TeamForm()
        self._events.append(TeamPerformanceResetEvent(team_id=team.id or 0))
        self._persist(team)

    def calculate_league_table(self, teams: list[Team]) -> list[dict[str, Any]]:
        """根据球队当前统计生成积分榜."""
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

    def get_domain_events(self) -> list[Any]:
        """返回当前收集到的领域事件快照."""
        return self._events.copy()

    def clear_domain_events(self) -> None:
        """清空领域事件缓存."""
        self._events.clear()

    def _persist(self, team: Team) -> Team:
        """将球队状态同步到仓储（如有）."""
        if not self._repository:
            return team

        if getattr(team, "id", None) is None:
            return self._repository.save(team)

        return self._repository.update(team)
