"""比赛领域模型.

封装比赛的核心业务逻辑和规则.
"""

from datetime import datetime
from enum import Enum
from typing import Any


class MatchStatus(Enum):
    """比赛状态枚举."""

    SCHEDULED = "scheduled"  # 已安排
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消
    POSTPONED = "postponed"  # 延期


class MatchResult(Enum):
    """比赛结果枚举."""

    HOME_WIN = "home_win"  # 主队胜
    AWAY_WIN = "away_win"  # 客队胜
    DRAW = "draw"  # 平局
    UNKNOWN = "unknown"  # 未知


class Match:
    """类文档字符串."""

    pass  # 添加pass语句
    """比赛领域模型"""

    def __init__(
        self,
        match_id: int | None = None,
        home_team_id: int = 0,
        away_team_id: int = 0,
        league_id: int = 0,
        scheduled_time: datetime | None = None,
        status: MatchStatus = MatchStatus.SCHEDULED,
    ):
        self.id = match_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        self.league_id = league_id
        self.scheduled_time = scheduled_time or datetime.now()
        self.status = status

        # 比分
        self.home_score = 0
        self.away_score = 0

        # 预测相关
        self.prediction_made = False
        self.prediction_result = None
        self.confidence_score = 0.0

    def start_match(self) -> bool:
        """开始比赛."""
        if self.status != MatchStatus.SCHEDULED:
            return False

        self.status = MatchStatus.IN_PROGRESS
        return True

    def end_match(self, home_score: int, away_score: int) -> bool:
        """结束比赛."""
        if self.status != MatchStatus.IN_PROGRESS:
            return False

        self.home_score = home_score
        self.away_score = away_score
        self.status = MatchStatus.COMPLETED

        # 确定比赛结果
        if home_score > away_score:
            self.prediction_result = MatchResult.HOME_WIN
        elif away_score > home_score:
            self.prediction_result = MatchResult.AWAY_WIN
        else:
            self.prediction_result = MatchResult.DRAW

        return True

    def update_score(self, home_score: int, away_score: int) -> None:
        """更新比分."""
        if self.status == MatchStatus.IN_PROGRESS:
            self.home_score = home_score
            self.away_score = away_score

    def cancel_match(self, reason: str = "") -> bool:
        """取消比赛."""
        if self.status in [MatchStatus.COMPLETED, MatchStatus.CANCELLED]:
            return False

        self.status = MatchStatus.CANCELLED
        return True

    def postpone_match(self, new_time: datetime) -> bool:
        """延期比赛."""
        if self.status != MatchStatus.SCHEDULED:
            return False

        self.scheduled_time = new_time
        self.status = MatchStatus.POSTPONED
        return True

    def is_predictable(self) -> bool:
        """检查是否可以预测."""
        return self.status == MatchStatus.SCHEDULED and not self.prediction_made

    def set_prediction(self, prediction: Any, confidence: float) -> None:
        """设置预测结果."""
        if self.is_predictable():
            self.prediction_made = True
            self.prediction_result = prediction
            self.confidence_score = confidence

    def get_result(self) -> MatchResult | None:
        """获取比赛结果."""
        if self.status != MatchStatus.COMPLETED:
            return None
        return self.prediction_result

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "league_id": self.league_id,
            "scheduled_time": (
                self.scheduled_time.isoformat() if self.scheduled_time else None
            ),
            "status": self.status.value,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "prediction_made": self.prediction_made,
            "prediction_result": (
                self.prediction_result.value if self.prediction_result else None
            ),
            "confidence_score": self.confidence_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Match":
        """从字典创建实例."""
        match = cls(
            id=data.get("id"),
            home_team_id=data.get("home_team_id", 0),
            away_team_id=data.get("away_team_id", 0),
            league_id=data.get("league_id", 0),
            scheduled_time=(
                datetime.fromisoformat(data["scheduled_time"])
                if data.get("scheduled_time")
                else None
            ),
            status=MatchStatus(data.get("status", "scheduled")),
        )

        if "home_score" in data:
            match.home_score = data["home_score"]
        if "away_score" in data:
            match.away_score = data["away_score"]
        if "prediction_made" in data:
            match.prediction_made = data["prediction_made"]
        if "prediction_result" in data and data["prediction_result"]:
            match.prediction_result = MatchResult(data["prediction_result"])
        if "confidence_score" in data:
            match.confidence_score = data["confidence_score"]

        return match

    def __str__(self) -> str:
        return f"Match({self.id}: {self.home_team_id} vs {self.away_team_id})"

    def __repr__(self) -> str:
        return f"<Match(id={self.id}, status={self.status.value})>"
