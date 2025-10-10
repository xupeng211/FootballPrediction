# mypy: ignore-errors
"""
from typing import Dict, Optional
核心事件类型定义
Core Event Types

定义系统中的核心事件类型。
Defines core event types in the system.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Type, Union
from dataclasses import dataclass, field

from .base import Event, EventData


# 比赛相关事件数据
class MatchEventData(EventData):
    """比赛事件数据"""

    def __init__(
        self,
        match_id: int,
        home_team_id: int,
        away_team_id: int,
        league_id: int,
        match_time: datetime,
        status: str = "upcoming",
        venue: Optional[str] = None,
        weather: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.match_id = match_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        self.league_id = league_id
        self.match_time = match_time
        self.status = status
        self.venue = venue
        self.weather = weather


class MatchCreatedEventData(MatchEventData):
    """比赛创建事件数据"""

    def __init__(
        self,
        match_id: int,
        home_team_id: int,
        away_team_id: int,
        league_id: int,
        match_time: datetime,
        created_by: Optional[int] = None,
        initial_odds: Optional[Dict[str, float]] = None,
        **kwargs,
    ):
        super().__init__(
            match_id=match_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            league_id=league_id,
            match_time=match_time,
            **kwargs,
        )
        self.created_by = created_by
        self.initial_odds = initial_odds


class MatchUpdatedEventData(MatchEventData):
    """比赛更新事件数据"""

    def __init__(
        self,
        match_id: int,
        home_team_id: int,
        away_team_id: int,
        league_id: int,
        match_time: datetime,
        updated_fields: Optional[Dict[str, Any]] = None,
        previous_status: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            match_id=match_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            league_id=league_id,
            match_time=match_time,
            **kwargs,
        )
        self.updated_fields = updated_fields or {}
        self.previous_status = previous_status


# 预测相关事件数据
class PredictionEventData(EventData):
    """预测事件数据"""

    def __init__(
        self,
        prediction_id: int,
        match_id: int,
        user_id: int,
        predicted_home: int,
        predicted_away: int,
        confidence: float,
        strategy_used: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.prediction_id = prediction_id
        self.match_id = match_id
        self.user_id = user_id
        self.predicted_home = predicted_home
        self.predicted_away = predicted_away
        self.confidence = confidence
        self.strategy_used = strategy_used


class PredictionMadeEventData(PredictionEventData):
    """预测创建事件数据"""

    def __init__(
        self,
        prediction_id: int,
        match_id: int,
        user_id: int,
        predicted_home: int,
        predicted_away: int,
        confidence: float,
        points_earned: Optional[int] = None,
        accuracy_score: Optional[float] = None,
        strategy_used: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            prediction_id=prediction_id,
            match_id=match_id,
            user_id=user_id,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            confidence=confidence,
            strategy_used=strategy_used,
            **kwargs,
        )
        self.points_earned = points_earned
        self.accuracy_score = accuracy_score


class PredictionUpdatedEventData(PredictionEventData):
    """预测更新事件数据"""

    def __init__(
        self,
        prediction_id: int,
        match_id: int,
        user_id: int,
        predicted_home: int,
        predicted_away: int,
        confidence: float,
        previous_prediction: Optional[Dict[str, Any]] = None,
        update_reason: Optional[str] = None,
        strategy_used: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            prediction_id=prediction_id,
            match_id=match_id,
            user_id=user_id,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            confidence=confidence,
            strategy_used=strategy_used,
            **kwargs,
        )
        self.previous_prediction = previous_prediction
        self.update_reason = update_reason


# 用户相关事件数据
class UserEventData(EventData):
    """用户事件数据"""

    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        registration_date: datetime,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.username = username
        self.email = email
        self.registration_date = registration_date


class UserRegisteredEventData(UserEventData):
    """用户注册事件数据"""

    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        registration_date: datetime,
        referral_code: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            user_id=user_id,
            username=username,
            email=email,
            registration_date=registration_date,
            **kwargs,
        )
        self.referral_code = referral_code
        self.ip_address = ip_address
        self.user_agent = user_agent


# 球队统计事件数据
class TeamStatsEventData(EventData):
    """球队统计事件数据"""

    def __init__(
        self,
        team_id: int,
        season: str,
        matches_played: int,
        wins: int,
        draws: int,
        losses: int,
        goals_for: int,
        goals_against: int,
        points: int,
        last_updated: datetime,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.team_id = team_id
        self.season = season
        self.matches_played = matches_played
        self.wins = wins
        self.draws = draws
        self.losses = losses
        self.goals_for = goals_for
        self.goals_against = goals_against
        self.points = points
        self.last_updated = last_updated


# 事件类定义
class MatchCreatedEvent(Event):
    """比赛创建事件"""

    def __init__(self, data: MatchCreatedEventData):
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "match.created"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "match_id": self.data.match_id,  # type: ignore
            "home_team_id": self.data.home_team_id,  # type: ignore
            "away_team_id": self.data.away_team_id,  # type: ignore
            "league_id": self.data.league_id,  # type: ignore
            "match_time": self.data.match_time.isoformat(),  # type: ignore
            "status": self.data.status,  # type: ignore
            "venue": self.data.venue,  # type: ignore
            "weather": self.data.weather,  # type: ignore
            "created_by": self.data.created_by,  # type: ignore
            "initial_odds": self.data.initial_odds,  # type: ignore
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchCreatedEvent":
        event_data = MatchCreatedEventData(
            event_id=data.get("event_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source"),
            version=data.get("version", "1.0"),
            metadata=data.get("metadata", {}),
            match_id=data["match_id"],
            home_team_id=data["home_team_id"],
            away_team_id=data["away_team_id"],
            league_id=data["league_id"],
            match_time=datetime.fromisoformat(data["match_time"]),
            status=data.get("status", "upcoming"),
            venue=data.get("venue"),
            weather=data.get("weather"),
            created_by=data.get("created_by"),
            initial_odds=data.get("initial_odds"),
        )
        return cls(event_data)


class MatchUpdatedEvent(Event):
    """比赛更新事件"""

    def __init__(self, data: MatchUpdatedEventData):
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "match.updated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "match_id": self.data.match_id,  # type: ignore
            "home_team_id": self.data.home_team_id,  # type: ignore
            "away_team_id": self.data.away_team_id,  # type: ignore
            "league_id": self.data.league_id,  # type: ignore
            "match_time": self.data.match_time.isoformat(),  # type: ignore
            "status": self.data.status,  # type: ignore
            "venue": self.data.venue,  # type: ignore
            "weather": self.data.weather,  # type: ignore
            "updated_fields": self.data.updated_fields,  # type: ignore
            "previous_status": self.data.previous_status,  # type: ignore
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchUpdatedEvent":
        event_data = MatchUpdatedEventData(
            event_id=data.get("event_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source"),
            version=data.get("version", "1.0"),
            metadata=data.get("metadata", {}),
            match_id=data["match_id"],
            home_team_id=data["home_team_id"],
            away_team_id=data["away_team_id"],
            league_id=data["league_id"],
            match_time=datetime.fromisoformat(data["match_time"]),
            status=data.get("status", "upcoming"),
            venue=data.get("venue"),
            weather=data.get("weather"),
            updated_fields=data.get("updated_fields", {}),
            previous_status=data.get("previous_status"),
        )
        return cls(event_data)


class PredictionMadeEvent(Event):
    """预测创建事件"""

    def __init__(self, data: PredictionMadeEventData):
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "prediction.made"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "prediction_id": self.data.prediction_id,  # type: ignore
            "match_id": self.data.match_id,  # type: ignore
            "user_id": self.data.user_id,  # type: ignore
            "predicted_home": self.data.predicted_home,
            "predicted_away": self.data.predicted_away,
            "confidence": self.data.confidence,  # type: ignore
            "strategy_used": self.data.strategy_used,  # type: ignore
            "points_earned": self.data.points_earned,  # type: ignore
            "accuracy_score": self.data.accuracy_score,  # type: ignore
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PredictionMadeEvent":
        event_data = PredictionMadeEventData(
            event_id=data.get("event_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source"),
            version=data.get("version", "1.0"),
            metadata=data.get("metadata", {}),
            prediction_id=data["prediction_id"],
            match_id=data["match_id"],
            user_id=data["user_id"],
            predicted_home=data["predicted_home"],
            predicted_away=data["predicted_away"],
            confidence=data["confidence"],
            strategy_used=data.get("strategy_used"),
            points_earned=data.get("points_earned"),
            accuracy_score=data.get("accuracy_score"),
        )
        return cls(event_data)


class PredictionUpdatedEvent(Event):
    """预测更新事件"""

    def __init__(self, data: PredictionUpdatedEventData):
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "prediction.updated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "prediction_id": self.data.prediction_id,  # type: ignore
            "match_id": self.data.match_id,  # type: ignore
            "user_id": self.data.user_id,  # type: ignore
            "predicted_home": self.data.predicted_home,  # type: ignore
            "predicted_away": self.data.predicted_away,  # type: ignore
            "confidence": self.data.confidence,  # type: ignore
            "strategy_used": self.data.strategy_used,  # type: ignore
            "previous_prediction": self.data.previous_prediction,  # type: ignore
            "update_reason": self.data.update_reason,  # type: ignore
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PredictionUpdatedEvent":
        event_data = PredictionUpdatedEventData(
            event_id=data.get("event_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source"),
            version=data.get("version", "1.0"),
            metadata=data.get("metadata", {}),
            prediction_id=data["prediction_id"],
            match_id=data["match_id"],
            user_id=data["user_id"],
            predicted_home=data["predicted_home"],
            predicted_away=data["predicted_away"],
            confidence=data["confidence"],
            strategy_used=data.get("strategy_used"),
            previous_prediction=data.get("previous_prediction"),
            update_reason=data.get("update_reason"),
        )
        return cls(event_data)


class UserRegisteredEvent(Event):
    """用户注册事件"""

    def __init__(self, data: UserRegisteredEventData):
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "user.registered"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "user_id": self.data.user_id,  # type: ignore
            "username": self.data.username,  # type: ignore
            "email": self.data.email,  # type: ignore
            "registration_date": self.data.registration_date.isoformat(),  # type: ignore
            "referral_code": self.data.referral_code,  # type: ignore
            "ip_address": self.data.ip_address,  # type: ignore
            "user_agent": self.data.user_agent,  # type: ignore
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserRegisteredEvent":
        event_data = UserRegisteredEventData(
            event_id=data.get("event_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source"),
            version=data.get("version", "1.0"),
            metadata=data.get("metadata", {}),
            user_id=data["user_id"],
            username=data["username"],
            email=data["email"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
            referral_code=data.get("referral_code"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
        )
        return cls(event_data)


class TeamStatsUpdatedEvent(Event):
    """球队统计更新事件"""

    def __init__(self, data: TeamStatsEventData):
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "team.stats_updated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "team_id": self.data.team_id,  # type: ignore
            "season": self.data.season,  # type: ignore
            "matches_played": self.data.matches_played,  # type: ignore
            "wins": self.data.wins,  # type: ignore
            "draws": self.data.draws,  # type: ignore
            "losses": self.data.losses,  # type: ignore
            "goals_for": self.data.goals_for,  # type: ignore
            "goals_against": self.data.goals_against,  # type: ignore
            "points": self.data.points,  # type: ignore
            "last_updated": self.data.last_updated.isoformat(),  # type: ignore
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamStatsUpdatedEvent":
        event_data = TeamStatsEventData(
            event_id=data.get("event_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source"),
            version=data.get("version", "1.0"),
            metadata=data.get("metadata", {}),
            team_id=data["team_id"],
            season=data["season"],
            matches_played=data["matches_played"],
            wins=data["wins"],
            draws=data["draws"],
            losses=data["losses"],
            goals_for=data["goals_for"],
            goals_against=data["goals_against"],
            points=data["points"],
            last_updated=datetime.fromisoformat(data["last_updated"]),
        )
        return cls(event_data)
