"""比赛领域模型
Match Domain Model.

封装比赛相关的业务逻辑和不变性约束.
Encapsulates match-related business logic and invariants.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.core.exceptions import DomainError


class MatchStatus(Enum):
    """比赛状态."""

    SCHEDULED = "scheduled"  # 已安排
    LIVE = "live"  # 进行中
    FINISHED = "finished"  # 已结束
    CANCELLED = "cancelled"  # 已取消
    POSTPONED = "postponed"  # 延期


class MatchResult(Enum):
    """比赛结果."""

    HOME_WIN = "home_win"  # 主队获胜
    AWAY_WIN = "away_win"  # 客队获胜
    DRAW = "draw"  # 平局


@dataclass
class MatchScore:
    """类文档字符串."""

    pass  # 添加pass语句
    """比赛比分值对象"""

    home_score: int = 0
    away_score: int = 0

    def __post_init__(self):
        """验证比赛数据."""
        if self.home_score < 0 or self.away_score < 0:
            raise DomainError("比分不能为负数")

    @property
    def total_goals(self) -> int:
        """总进球数."""
        return self.home_score + self.away_score

    @property
    def goal_difference(self) -> int:
        """净胜球."""
        return self.home_score - self.away_score

    @property
    def result(self) -> MatchResult:
        """比赛结果."""
        if self.home_score > self.away_score:
            return MatchResult.HOME_WIN
        elif self.away_score > self.home_score:
            return MatchResult.AWAY_WIN
        else:
            return MatchResult.DRAW

    def __str__(self) -> str:
        return f"{self.home_score}-{self.away_score}"


@dataclass
class Match:
    """类文档字符串."""

    pass  # 添加pass语句
    """
    比赛领域模型

    封装比赛的核心业务逻辑和不变性约束.
    """

    id: int | None = None
    home_team_id: int = 0
    away_team_id: int = 0
    league_id: int = 0
    season: str = ""
    match_date: datetime = field(default_factory=datetime.utcnow)
    status: MatchStatus = MatchStatus.SCHEDULED
    score: MatchScore | None = None
    venue: str | None = None
    referee: str | None = None
    weather: str | None = None
    attendance: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # 领域事件
    _domain_events: list[Any] = field(default_factory=list, init=False)

    def __post_init__(self):
        """函数文档字符串."""
        # 添加pass语句
        """初始化后的验证"""
        if self.home_team_id == self.away_team_id:
            raise DomainError("主队和客队不能相同")

        if self.season and not self._is_valid_season_format(self.season):
            raise DomainError("赛季格式无效,应为 YYYY-YYYY 或 YYYY")

    @staticmethod
    def _is_valid_season_format(season: str) -> bool:
        """验证赛季格式."""
        # 简单验证:2023-2024 或 2023
        parts = season.split("-")
        if len(parts) == 1:
            return parts[0].isdigit() and len(parts[0]) == 4
        elif len(parts) == 2:
            return (
                parts[0].isdigit()
                and parts[1].isdigit()
                and len(parts[0]) == 4
                and len(parts[1]) == 4
                and int(parts[1]) == int(parts[0]) + 1
            )
        return False

    # ========================================
    # 业务方法
    # ========================================

    def start_match(self) -> None:
        """开始比赛."""
        if self.status != MatchStatus.SCHEDULED:
            raise DomainError(f"比赛状态为 {self.status.value},无法开始")

        self.status = MatchStatus.LIVE
        self.updated_at = datetime.utcnow()

    def update_score(self, home_score: int, away_score: int) -> None:
        """更新比分."""
        if self.status not in [MatchStatus.LIVE, MatchStatus.SCHEDULED]:
            raise DomainError("只有进行中或已安排的比赛才能更新比分")

        old_score = self.score
        self.score = MatchScore(home_score=home_score, away_score=away_score)

        # 如果是首次有比分,将状态改为进行中
        if old_score is None and (home_score > 0 or away_score > 0):
            self.status = MatchStatus.LIVE

        self.updated_at = datetime.utcnow()

    def finish_match(self) -> None:
        """结束比赛."""
        if self.status != MatchStatus.LIVE:
            raise DomainError("只有进行中的比赛才能结束")

        if not self.score:
            raise DomainError("比赛必须要有比分才能结束")

        self.status = MatchStatus.FINISHED
        self.updated_at = datetime.utcnow()

        # 发布领域事件
        from src.domain.events import MatchFinishedEvent

        self._add_domain_event(
            MatchFinishedEvent(
                match_id=self.id,
                home_team_id=self.home_team_id,
                away_team_id=self.away_team_id,
                final_score=self.score,
                result=self.score.result,
            )
        )

    def cancel_match(self, reason: str | None = None) -> None:
        """取消比赛."""
        if self.status in [MatchStatus.FINISHED, MatchStatus.CANCELLED]:
            raise DomainError("已结束或已取消的比赛无法再次取消")

        self.status = MatchStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def postpone_match(self, new_date: datetime | None = None) -> None:
        """延期比赛."""
        if self.status in [MatchStatus.FINISHED, MatchStatus.CANCELLED]:
            raise DomainError("已结束或已取消的比赛无法延期")

        self.status = MatchStatus.POSTPONED
        if new_date:
            self.match_date = new_date
        self.updated_at = datetime.utcnow()

    def is_same_team(self, team_id: int) -> bool:
        """检查是否是参赛球队."""
        return team_id in [self.home_team_id, self.away_team_id]

    def is_home_team(self, team_id: int) -> bool:
        """检查是否是主队."""
        return team_id == self.home_team_id

    def is_away_team(self, team_id: int) -> bool:
        """检查是否是客队."""
        return team_id == self.away_team_id

    def get_opponent_id(self, team_id: int) -> int | None:
        """获取对手ID."""
        if team_id == self.home_team_id:
            return self.away_team_id
        elif team_id == self.away_team_id:
            return self.home_team_id
        return None

    # ========================================
    # 查询方法
    # ========================================

    @property
    def is_upcoming(self) -> bool:
        """是否是即将开始的比赛."""
        return (
            self.status == MatchStatus.SCHEDULED and self.match_date > datetime.utcnow()
        )

    @property
    def is_live(self) -> bool:
        """是否正在进行."""
        return self.status == MatchStatus.LIVE

    @property
    def is_finished(self) -> bool:
        """是否已结束."""
        return self.status == MatchStatus.FINISHED

    @property
    def can_be_predicted(self) -> bool:
        """是否可以预测."""
        return self.status in [MatchStatus.SCHEDULED, MatchStatus.LIVE]

    @property
    def days_until_match(self) -> int:
        """距离比赛还有多少天."""
        if self.match_date:
            delta = self.match_date - datetime.utcnow()
            return max(0, delta.days)
        return 0

    def get_duration(self) -> int | None:
        """获取比赛时长（分钟）."""
        if self.status == MatchStatus.FINISHED and self.created_at:
            # 这里简化处理,实际应该记录开始时间
            return 90  # 标准足球比赛时长
        return None

    # ========================================
    # 领域事件管理
    # ========================================

    def _add_domain_event(self, event: Any) -> None:
        """添加领域事件."""
        self._domain_events.append(event)

    def get_domain_events(self) -> list[Any]:
        """获取领域事件."""
        return self._domain_events.copy()

    def clear_domain_events(self) -> None:
        """清除领域事件."""
        self._domain_events.clear()

    # ========================================
    # 序列化方法
    # ========================================

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "league_id": self.league_id,
            "season": self.season,
            "match_date": self.match_date.isoformat() if self.match_date else None,
            "status": self.status.value,
            "score": (
                {
                    "home_score": self.score.home_score,
                    "away_score": self.score.away_score,
                    "result": self.score.result.value,
                }
                if self.score
                else None
            ),
            "venue": self.venue,
            "referee": self.referee,
            "weather": self.weather,
            "attendance": self.attendance,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Match":
        """从字典创建实例."""
        score_data = data.pop("score", None)
        score = None
        if score_data:
            score_data.pop("result", None)
            score = MatchScore(**score_data)

        # 处理日期
        if data.get("match_date"):
            data["match_date"] = datetime.fromisoformat(data["match_date"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # 处理状态枚举
        if data.get("status"):
            data["status"] = MatchStatus(data["status"])

        return cls(score=score, **data)

    def __str__(self) -> str:
        team_names = f"Team{self.home_team_id} vs Team{self.away_team_id}"
        score_str = f" ({self.score})" if self.score else ""
        return f"{team_names}{score_str} - {self.status.value}"
