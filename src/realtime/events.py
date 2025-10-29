from typing import Optional
from typing import Dict
from typing import Union
from typing import Any
"""
实时事件定义 - 足球预测系统

Realtime Events Definition - Football Prediction System

定义所有实时事件的类型和数据结构
Define all realtime event types and data structures
"""

from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """事件类型枚举"""

    # 连接事件
    CONNECTION_STATUS = "connection_status"

    # 预测事件
    PREDICTION_CREATED = "prediction_created"
    PREDICTION_UPDATED = "prediction_updated"
    PREDICTION_COMPLETED = "prediction_completed"

    # 比赛事件
    MATCH_STARTED = "match_started"
    MATCH_SCORE_CHANGED = "match_score_changed"
    MATCH_STATUS_CHANGED = "match_status_changed"
    MATCH_ENDED = "match_ended"

    # 赔率事件
    ODDS_UPDATED = "odds_updated"
    ODDS_SIGNIFICANT_CHANGE = "odds_significant_change"

    # 系统事件
    SYSTEM_ALERT = "system_alert"
    SYSTEM_STATUS = "system_status"

    # 用户事件
    USER_SUBSCRIPTION_CHANGED = "user_subscription_changed"
    USER_PREFERENCE_UPDATED = "user_preference_updated"

    # 数据更新事件
    DATA_REFRESH = "data_refresh"
    ANALYTICS_UPDATED = "analytics_updated"


@dataclass
class PredictionEvent:
    """预测事件数据"""

    prediction_id: int
    match_id: int
    prediction_type: str  # home_win, draw, away_win
    confidence: float
    probabilities: Dict[str, float]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "match_id": self.match_id,
            "prediction_type": self.prediction_type,
            "confidence": self.confidence,
            "probabilities": self.probabilities,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MatchEvent:
    """比赛事件数据"""

    match_id: int
    home_team: str
    away_team: str
    league: str
    status: str  # upcoming, live, finished
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    minute: Optional[int] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "league": self.league,
            "status": self.status,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "minute": self.minute,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class OddsEvent:
    """赔率事件数据"""

    match_id: int
    bookmaker: str
    home_win_odds: float
    draw_odds: float
    away_win_odds: float
    timestamp: datetime
    change_percentage: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "bookmaker": self.bookmaker,
            "home_win_odds": self.home_win_odds,
            "draw_odds": self.draw_odds,
            "away_win_odds": self.away_win_odds,
            "timestamp": self.timestamp.isoformat(),
            "change_percentage": self.change_percentage,
        }


@dataclass
class SystemAlertEvent:
    """系统告警事件数据"""

    alert_type: str  # error, warning, info
    message: str
    component: str
    severity: str  # low, medium, high, critical
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_type": self.alert_type,
            "message": self.message,
            "component": self.component,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


@dataclass
class AnalyticsEvent:
    """分析事件数据"""

    metric_name: str
    value: Union[float, int]
    previous_value: Optional[Union[float, int]] = None
    change_percentage: Optional[float] = None
    timestamp: datetime
    period: str = "realtime"  # realtime, daily, weekly, monthly

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "previous_value": self.previous_value,
            "change_percentage": self.change_percentage,
            "timestamp": self.timestamp.isoformat(),
            "period": self.period,
        }


class RealtimeEvent(BaseModel):
    """实时事件基类"""

    event_type: EventType = Field(..., description="事件类型")
    data: Dict[str, Any] = Field(..., description="事件数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")
    source: Optional[str] = Field(None, description="事件源")
    correlation_id: Optional[str] = Field(None, description="关联ID")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return self.json()

    @classmethod
    def from_prediction(
        cls, prediction_event: PredictionEvent, event_type: EventType
    ) -> "RealtimeEvent":
        """从预测事件创建"""
        return cls(
            event_type=event_type,
            data=prediction_event.to_dict(),
            source="prediction_service",
        )

    @classmethod
    def from_match(cls, match_event: MatchEvent, event_type: EventType) -> "RealtimeEvent":
        """从比赛事件创建"""
        return cls(event_type=event_type, data=match_event.to_dict(), source="match_service")

    @classmethod
    def from_odds(cls, odds_event: OddsEvent, event_type: EventType) -> "RealtimeEvent":
        """从赔率事件创建"""
        return cls(event_type=event_type, data=odds_event.to_dict(), source="odds_service")

    @classmethod
    def from_system_alert(cls, alert_event: SystemAlertEvent) -> "RealtimeEvent":
        """从系统告警创建"""
        return cls(
            event_type=EventType.SYSTEM_ALERT,
            data=alert_event.to_dict(),
            source="system_monitor",
        )

    @classmethod
    def from_analytics(cls, analytics_event: AnalyticsEvent) -> "RealtimeEvent":
        """从分析事件创建"""
        return cls(
            event_type=EventType.ANALYTICS_UPDATED,
            data=analytics_event.to_dict(),
            source="analytics_service",
        )

    @classmethod
    def connection_status(
        cls, connection_id: str, user_id: Optional[str], status: str
    ) -> "RealtimeEvent":
        """创建连接状态事件"""
        return cls(
            event_type=EventType.CONNECTION_STATUS,
            data={
                "connection_id": connection_id,
                "user_id": user_id,
                "status": status,
                "timestamp": datetime.now().isoformat(),
            },
            source="websocket_manager",
        )


# 事件工厂函数
def create_prediction_created_event(
    prediction_id: int,
    match_id: int,
    prediction_type: str,
    confidence: float,
    probabilities: Dict[str, float],
) -> RealtimeEvent:
    """创建预测创建事件"""
    prediction_event = PredictionEvent(
        prediction_id=prediction_id,
        match_id=match_id,
        prediction_type=prediction_type,
        confidence=confidence,
        probabilities=probabilities,
        timestamp=datetime.now(),
    )
    return RealtimeEvent.from_prediction(prediction_event, EventType.PREDICTION_CREATED)


def create_match_score_changed_event(
    match_id: int,
    home_team: str,
    away_team: str,
    league: str,
    home_score: int,
    away_score: int,
    minute: Optional[int] = None,
) -> RealtimeEvent:
    """创建比分变化事件"""
    match_event = MatchEvent(
        match_id=match_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        status="live",
        home_score=home_score,
        away_score=away_score,
        minute=minute,
        timestamp=datetime.now(),
    )
    return RealtimeEvent.from_match(match_event, EventType.MATCH_SCORE_CHANGED)


def create_odds_updated_event(
    match_id: int,
    bookmaker: str,
    home_win_odds: float,
    draw_odds: float,
    away_win_odds: float,
    previous_odds: Optional[Dict[str, float]] = None,
) -> RealtimeEvent:
    """创建赔率更新事件"""
    change_percentage = None
    if previous_odds:
        change_percentage = {
            "home_win": ((home_win_odds - previous_odds["home_win"]) / previous_odds["home_win"])
            * 100,
            "draw": ((draw_odds - previous_odds["draw"]) / previous_odds["draw"]) * 100,
            "away_win": ((away_win_odds - previous_odds["away_win"]) / previous_odds["away_win"])
            * 100,
        }

    odds_event = OddsEvent(
        match_id=match_id,
        bookmaker=bookmaker,
        home_win_odds=home_win_odds,
        draw_odds=draw_odds,
        away_win_odds=away_win_odds,
        timestamp=datetime.now(),
        change_percentage=change_percentage,
    )

    # 判断是否为显著变化（变化超过5%）
    if change_percentage and any(abs(p) > 5 for p in change_percentage.values()):
        return RealtimeEvent.from_odds(odds_event, EventType.ODDS_SIGNIFICANT_CHANGE)
    else:
        return RealtimeEvent.from_odds(odds_event, EventType.ODDS_UPDATED)


def create_system_alert_event(
    alert_type: str,
    message: str,
    component: str,
    severity: str,
    details: Optional[Dict[str, Any]] = None,
) -> RealtimeEvent:
    """创建系统告警事件"""
    alert_event = SystemAlertEvent(
        alert_type=alert_type,
        message=message,
        component=component,
        severity=severity,
        timestamp=datetime.now(),
        details=details,
    )
    return RealtimeEvent.from_system_alert(alert_event)


def create_analytics_updated_event(
    metric_name: str,
    value: Union[float, int],
    previous_value: Optional[Union[float, int]] = None,
    period: str = "realtime",
) -> RealtimeEvent:
    """创建分析更新事件"""
    change_percentage = None
    if previous_value is not None and previous_value != 0:
        change_percentage = ((value - previous_value) / previous_value) * 100

    analytics_event = AnalyticsEvent(
        metric_name=metric_name,
        value=value,
        previous_value=previous_value,
        change_percentage=change_percentage,
        timestamp=datetime.now(),
        period=period,
    )
    return RealtimeEvent.from_analytics(analytics_event)


# 事件验证函数
def validate_event(event: RealtimeEvent) -> bool:
    """验证事件格式"""
    try:
        # 基本字段验证
        if not isinstance(event.event_type, EventType):
            return False

        if not isinstance(event.data, dict):
            return False

        if not isinstance(event.timestamp, datetime):
            return False

        # 根据事件类型验证数据结构
        if event.event_type == EventType.PREDICTION_CREATED:
            required_fields = [
                "prediction_id",
                "match_id",
                "prediction_type",
                "confidence",
                "probabilities",
            ]
            return all(field in event.data for field in required_fields)

        elif event.event_type in [
            EventType.MATCH_STARTED,
            EventType.MATCH_SCORE_CHANGED,
            EventType.MATCH_ENDED,
        ]:
            required_fields = ["match_id", "home_team", "away_team", "league", "status"]
            return all(field in event.data for field in required_fields)

        elif event.event_type in [
            EventType.ODDS_UPDATED,
            EventType.ODDS_SIGNIFICANT_CHANGE,
        ]:
            required_fields = [
                "match_id",
                "bookmaker",
                "home_win_odds",
                "draw_odds",
                "away_win_odds",
            ]
            return all(field in event.data for field in required_fields)

        elif event.event_type == EventType.SYSTEM_ALERT:
            required_fields = ["alert_type", "message", "component", "severity"]
            return all(field in event.data for field in required_fields)

        return True

    except Exception:
        return False
