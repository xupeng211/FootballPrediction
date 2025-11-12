"""
事件类型定义模块
Event Types Module

定义事件相关的数据类型
Defines event-related data types.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import EventData


@dataclass
class MatchCreatedEventData(EventData):
    """比赛创建事件数据"""

    match_id: int
    home_team: str
    away_team: str
    league: str
    scheduled_start: datetime
    odds: Optional[Dict[str, float]] = None

    def __post_init__(self):
        super().__init__(
            {
                "match_id": self.match_id,
                "home_team": self.home_team,
                "away_team": self.away_team,
                "league": self.league,
                "scheduled_start": self.scheduled_start.isoformat(),
                "odds": self.odds,
            }
        )


@dataclass
class MatchUpdatedEventData(EventData):
    """比赛更新事件数据"""

    match_id: int
    updated_fields: List[str]
    previous_values: Dict[str, Any]
    new_values: Dict[str, Any]

    def __post_init__(self):
        super().__init__(
            {
                "match_id": self.match_id,
                "updated_fields": self.updated_fields,
                "previous_values": self.previous_values,
                "new_values": self.new_values,
            }
        )


@dataclass
class PredictionMadeEventData(EventData):
    """预测事件数据"""

    prediction_id: str
    user_id: int
    match_id: int
    predicted_outcome: str
    confidence: float
    stake: float
    odds: float

    def __post_init__(self):
        super().__init__(
            {
                "prediction_id": str(self.prediction_id),
                "user_id": self.user_id,
                "match_id": self.match_id,
                "predicted_outcome": self.predicted_outcome,
                "confidence": self.confidence,
                "stake": self.stake,
                "odds": self.odds,
            }
        )


@dataclass
class MatchFinishedEventData(EventData):
    """比赛结束事件数据"""

    match_id: int
    final_score: Dict[str, int]  # {"home": 2, "away": 1}
    winner: Optional[str]  # "home", "away", or "draw"
    match_duration: Optional[int] = None  # 比赛时长（分钟）

    def __post_init__(self):
        super().__init__(
            {
                "match_id": self.match_id,
                "final_score": self.final_score,
                "winner": self.winner,
                "match_duration": self.match_duration,
            }
        )


@dataclass
class PredictionEvaluatedEventData(EventData):
    """预测评估事件数据"""

    prediction_id: str
    user_id: int
    match_id: int
    predicted_outcome: str
    actual_outcome: str
    is_correct: bool
    points_won: float
    stake_returned: float

    def __post_init__(self):
        super().__init__(
            {
                "prediction_id": str(self.prediction_id),
                "user_id": self.user_id,
                "match_id": self.match_id,
                "predicted_outcome": self.predicted_outcome,
                "actual_outcome": self.actual_outcome,
                "is_correct": self.is_correct,
                "points_won": self.points_won,
                "stake_returned": self.stake_returned,
            }
        )


@dataclass
class UserRegisteredEventData(EventData):
    """用户注册事件数据"""

    user_id: int
    email: str
    username: str
    registration_ip: str
    referral_code: Optional[str] = None

    def __post_init__(self):
        super().__init__(
            {
                "user_id": self.user_id,
                "email": self.email,
                "username": self.username,
                "registration_ip": self.registration_ip,
                "referral_code": self.referral_code,
            }
        )


@dataclass
class SystemErrorEventData(EventData):
    """系统错误事件数据"""

    error_id: str
    error_type: str
    error_message: str
    stack_trace: str
    affected_user_id: Optional[int] = None
    request_id: Optional[str] = None

    def __post_init__(self):
        super().__init__(
            {
                "error_id": str(self.error_id),
                "error_type": self.error_type,
                "error_message": self.error_message,
                "stack_trace": self.stack_trace,
                "affected_user_id": self.affected_user_id,
                "request_id": self.request_id,
            }
        )


# 便捷工厂函数
def create_match_created_data(
    match_id: int,
    home_team: str,
    away_team: str,
    league: str,
    scheduled_start: datetime,
    **kwargs,
) -> MatchCreatedEventData:
    """创建比赛创建事件数据"""
    return MatchCreatedEventData(
        match_id=match_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        scheduled_start=scheduled_start,
        **kwargs,
    )


def create_prediction_made_data(
    prediction_id: str,
    user_id: int,
    match_id: int,
    predicted_outcome: str,
    confidence: float,
    stake: float,
    odds: float,
) -> PredictionMadeEventData:
    """创建预测事件数据"""
    return PredictionMadeEventData(
        prediction_id=prediction_id,
        user_id=user_id,
        match_id=match_id,
        predicted_outcome=predicted_outcome,
        confidence=confidence,
        stake=stake,
        odds=odds,
    )


def create_system_error_data(
    error_id: str, error_type: str, error_message: str, stack_trace: str, **kwargs
) -> SystemErrorEventData:
    """创建系统错误事件数据"""
    return SystemErrorEventData(
        error_id=error_id,
        error_type=error_type,
        error_message=error_message,
        stack_trace=stack_trace,
        **kwargs,
    )


# 导出的公共接口
__all__ = [
    "MatchCreatedEventData",
    "MatchUpdatedEventData",
    "PredictionMadeEventData",
    "MatchFinishedEventData",
    "PredictionEvaluatedEventData",
    "UserRegisteredEventData",
    "SystemErrorEventData",
    "create_match_created_data",
    "create_prediction_made_data",
    "create_system_error_data",
]
