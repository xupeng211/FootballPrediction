from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.events.base import DomainEvent
from src.domain.models.match import MatchResult, MatchScore


@dataclass
class MatchEvent:
    """比赛事件基类"""

    match_id: str
    timestamp: datetime
    event_type: str
    data: dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


# MatchStartedEvent moved to DomainEvent inheritance pattern below


@dataclass
class MatchEndedEvent(MatchEvent):
    """比赛结束事件"""

    event_type: str = "match_ended"
    final_score: str = ""
    winner: str | None = None


"""
比赛领域事件
Match Domain Events

定义与比赛相关的领域事件.
Defines domain events related to matches.
"""


class MatchStartedEvent(DomainEvent):
    """比赛开始事件"""

    def __init__(self, match_id: int, home_team_id: int, away_team_id: int, **kwargs):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(aggregate_id=match_id)
        self.match_id = match_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id

    def _get_event_data(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
        }


class MatchFinishedEvent(DomainEvent):
    """比赛结束事件"""

    def __init__(
        self,
        match_id: int,
        home_team_id: int,
        away_team_id: int,
        final_score: MatchScore,
        result: MatchResult,
        **kwargs,
    ):
        super().__init__(aggregate_id=match_id)
        self.match_id = match_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        self.final_score = final_score
        self.result = result

    def _get_event_data(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "final_score": {
                "home_score": self.final_score.home_score,
                "away_score": self.final_score.away_score,
                "result": self.result.value,
            },
        }


class MatchCancelledEvent(DomainEvent):
    """比赛取消事件"""

    def __init__(self, match_id: int, reason: str, **kwargs):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(aggregate_id=match_id)
        self.match_id = match_id
        self.reason = reason

    def _get_event_data(self) -> dict[str, Any]:
        return {"match_id": self.match_id, "reason": self.reason}


class MatchPostponedEvent(DomainEvent):
    """比赛延期事件"""

    def __init__(self, match_id: int, new_date: str, reason: str, **kwargs):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(aggregate_id=match_id)
        self.match_id = match_id
        self.new_date = new_date
        self.reason = reason

    def _get_event_data(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "new_date": self.new_date,
            "reason": self.reason,
        }
