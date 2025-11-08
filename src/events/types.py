from datetime import datetime
from typing import Any

from .base import Event, EventData

"""
from typing import Dict, Optional
核心事件类型定义
Core Event Types

定义系统中的核心事件类型.
Defines core event types in the system.
"""


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
        venue: str | None = None,
        weather: dict[str, Any] | None = None,
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
        created_by: int | None = None,
        initial_odds: dict[str, float] | None = None,
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
        updated_fields: dict[str, Any] | None = None,
        previous_status: str | None = None,
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
        strategy_used: str | None = None,
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
        points_earned: int | None = None,
        accuracy_score: float | None = None,
        strategy_used: str | None = None,
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
        previous_prediction: dict[str, Any] | None = None,
        update_reason: str | None = None,
        strategy_used: str | None = None,
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
        referral_code: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
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


class MatchCreatedEvent(Event):
    """比赛创建事件"""

    def __init__(self, data: MatchCreatedEventData):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "match.created"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "match_id": self.data.match_id,
            "home_team_id": self.data.home_team_id,
            "away_team_id": self.data.away_team_id,
            "league_id": self.data.league_id,
            "match_time": self.data.match_time.isoformat(),
            "status": self.data.status,
            "venue": self.data.venue,
            "weather": self.data.weather,
            "created_by": self.data.created_by,
            "initial_odds": self.data.initial_odds,
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MatchCreatedEvent":
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
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "match.updated"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "match_id": self.data.match_id,
            "home_team_id": self.data.home_team_id,
            "away_team_id": self.data.away_team_id,
            "league_id": self.data.league_id,
            "match_time": self.data.match_time.isoformat(),
            "status": self.data.status,
            "venue": self.data.venue,
            "weather": self.data.weather,
            "updated_fields": self.data.updated_fields,
            "previous_status": self.data.previous_status,
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MatchUpdatedEvent":
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
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "prediction.made"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "prediction_id": self.data.prediction_id,
            "match_id": self.data.match_id,
            "user_id": self.data.user_id,
            "predicted_home": self.data.predicted_home,
            "predicted_away": self.data.predicted_away,
            "confidence": self.data.confidence,
            "strategy_used": self.data.strategy_used,
            "points_earned": self.data.points_earned,
            "accuracy_score": self.data.accuracy_score,
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PredictionMadeEvent":
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
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "prediction.updated"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "prediction_id": self.data.prediction_id,
            "match_id": self.data.match_id,
            "user_id": self.data.user_id,
            "predicted_home": self.data.predicted_home,
            "predicted_away": self.data.predicted_away,
            "confidence": self.data.confidence,
            "strategy_used": self.data.strategy_used,
            "previous_prediction": self.data.previous_prediction,
            "update_reason": self.data.update_reason,
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PredictionUpdatedEvent":
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
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "user.registered"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "user_id": self.data.user_id,
            "username": self.data.username,
            "email": self.data.email,
            "registration_date": self.data.registration_date.isoformat(),
            "referral_code": self.data.referral_code,
            "ip_address": self.data.ip_address,
            "user_agent": self.data.user_agent,
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserRegisteredEvent":
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
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(data)

    @classmethod
    def get_event_type(cls) -> str:
        return "team.stats_updated"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "team_id": self.data.team_id,
            "season": self.data.season,
            "matches_played": self.data.matches_played,
            "wins": self.data.wins,
            "draws": self.data.draws,
            "losses": self.data.losses,
            "goals_for": self.data.goals_for,
            "goals_against": self.data.goals_against,
            "points": self.data.points,
            "last_updated": self.data.last_updated.isoformat(),
            "metadata": self.data.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TeamStatsUpdatedEvent":
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
