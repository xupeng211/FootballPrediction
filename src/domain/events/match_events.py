"""
比赛领域事件
Match Domain Events

定义与比赛相关的领域事件.
Defines domain events related to matches.
"""

from typing import Any, Dict

from ..models.match import MatchResult, MatchScore
from .base import DomainEvent


class MatchStartedEvent(DomainEvent):
    """比赛开始事件"""

    def __init__(self, match_id: int, home_team_id: int, away_team_id: int, **kwargs):
    """函数文档字符串"""
    pass  # 添加pass语句
        super().__init__(aggregate_id=match_id)
        self.match_id = match_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id

    def _get_event_data(self) -> Dict[str, Any]:
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

    def _get_event_data(self) -> Dict[str, Any]:
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
    pass  # 添加pass语句
        super().__init__(aggregate_id=match_id)
        self.match_id = match_id
        self.reason = reason

    def _get_event_data(self) -> Dict[str, Any]:
        return {"match_id": self.match_id, "reason": self.reason}


class MatchPostponedEvent(DomainEvent):
    """比赛延期事件"""

    def __init__(self, match_id: int, new_date: str, reason: str, **kwargs):
    """函数文档字符串"""
    pass  # 添加pass语句
        super().__init__(aggregate_id=match_id)
        self.match_id = match_id
        self.new_date = new_date
        self.reason = reason

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "new_date": self.new_date,
            "reason": self.reason,
        }
