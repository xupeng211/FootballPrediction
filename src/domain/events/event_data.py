"""事件数据类型
Event Data Types.

定义事件系统使用的数据结构.
Defines data structures used by the event system.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.events.base import EventData


@dataclass
class MatchCreatedEventData(EventData):
    """比赛创建事件数据."""

    match_id: int
    home_team_id: int
    away_team_id: int
    scheduled_at: datetime
    venue: str | None = None
    competition_id: int | None = None

    def __post_init__(self):
        if not hasattr(self, "data") or self.data is None:
            self.data = {}

        self.data.update(
            {
                "match_id": self.match_id,
                "home_team_id": self.home_team_id,
                "away_team_id": self.away_team_id,
                "scheduled_at": (
                    self.scheduled_at.isoformat() if self.scheduled_at else None
                ),
                "venue": self.venue,
                "competition_id": self.competition_id,
            }
        )


@dataclass
class MatchUpdatedEventData(EventData):
    """比赛更新事件数据."""

    match_id: int
    updated_fields: dict[str, Any]
    updated_at: datetime

    def __post_init__(self):
        if not hasattr(self, "data") or self.data is None:
            self.data = {}

        self.data.update(
            {
                "match_id": self.match_id,
                "updated_fields": self.updated_fields,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
        )


@dataclass
class PredictionMadeEventData(EventData):
    """预测事件数据."""

    prediction_id: int
    user_id: int
    match_id: int
    predicted_home_score: int
    predicted_away_score: int
    confidence: float | None = None
    prediction_time: datetime = None

    def __post_init__(self):
        if not hasattr(self, "data") or self.data is None:
            self.data = {}

        if self.prediction_time is None:
            self.prediction_time = datetime.utcnow()

        self.data.update(
            {
                "prediction_id": self.prediction_id,
                "user_id": self.user_id,
                "match_id": self.match_id,
                "predicted_home_score": self.predicted_home_score,
                "predicted_away_score": self.predicted_away_score,
                "confidence": self.confidence,
                "prediction_time": (
                    self.prediction_time.isoformat() if self.prediction_time else None
                ),
            }
        )


# 为了向后兼容，提供工厂函数
def create_match_created_data(
    match_id: int,
    home_team_id: int,
    away_team_id: int,
    scheduled_at: datetime,
    venue: str | None = None,
    competition_id: int | None = None,
) -> MatchCreatedEventData:
    """创建比赛创建事件数据."""
    return MatchCreatedEventData(
        match_id=match_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        scheduled_at=scheduled_at,
        venue=venue,
        competition_id=competition_id,
    )


def create_match_updated_data(
    match_id: int,
    updated_fields: dict[str, Any],
    updated_at: datetime | None = None,
) -> MatchUpdatedEventData:
    """创建比赛更新事件数据."""
    if updated_at is None:
        updated_at = datetime.utcnow()

    return MatchUpdatedEventData(
        match_id=match_id,
        updated_fields=updated_fields,
        updated_at=updated_at,
    )


def create_prediction_made_data(
    prediction_id: int,
    user_id: int,
    match_id: int,
    predicted_home_score: int,
    predicted_away_score: int,
    confidence: float | None = None,
    prediction_time: datetime | None = None,
) -> PredictionMadeEventData:
    """创建预测事件数据."""
    return PredictionMadeEventData(
        prediction_id=prediction_id,
        user_id=user_id,
        match_id=match_id,
        predicted_home_score=predicted_home_score,
        predicted_away_score=predicted_away_score,
        confidence=confidence,
        prediction_time=prediction_time,
    )


__all__ = [
    "MatchCreatedEventData",
    "MatchUpdatedEventData",
    "PredictionMadeEventData",
    "create_match_created_data",
    "create_match_updated_data",
    "create_prediction_made_data",
]
