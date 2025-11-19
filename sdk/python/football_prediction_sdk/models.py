#!/usr/bin/env python3
"""数据模型模块
Football Prediction SDK - 数据模型定义.

Author: Claude Code
Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MatchStatus(Enum):
    """比赛状态枚举."""
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class PredictionStatus(Enum):
    """预测状态枚举."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SubscriptionPlan(Enum):
    """订阅计划枚举."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class Team:
    """球队模型."""
    team_id: str
    name: str
    short_name: str | None = None
    league: str | None = None
    country: str | None = None
    founded_year: int | None = None
    stadium: str | None = None
    current_form: list[str] | None = None
    position: int | None = None
    points: int | None = None
    logo_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Team":
        """从字典创建Team实例."""
        return cls(
            team_id=data.get("team_id", ""),
            name=data.get("name", ""),
            short_name=data.get("short_name"),
            league=data.get("league"),
            country=data.get("country"),
            founded_year=data.get("founded_year"),
            stadium=data.get("stadium"),
            current_form=data.get("current_form"),
            position=data.get("position"),
            points=data.get("points"),
            logo_url=data.get("logo_url")
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "team_id": self.team_id,
            "name": self.name,
            "short_name": self.short_name,
            "league": self.league,
            "country": self.country,
            "founded_year": self.founded_year,
            "stadium": self.stadium,
            "current_form": self.current_form,
            "position": self.position,
            "points": self.points,
            "logo_url": self.logo_url
        }


@dataclass
class Match:
    """比赛模型."""
    match_id: str
    home_team: Team | dict[str, Any]
    away_team: Team | dict[str, Any]
    league: str
    match_date: datetime
    status: MatchStatus
    venue: str | None = None
    score: dict[str, int] | None = None
    weather: str | None = None
    odds: dict[str, float] | None = None

    def __post_init__(self):
        """后处理：确保team字段是Team对象."""
        if isinstance(self.home_team, dict):
            self.home_team = Team.from_dict(self.home_team)
        if isinstance(self.away_team, dict):
            self.away_team = Team.from_dict(self.away_team)

        # 确保status是MatchStatus枚举
        if isinstance(self.status, str):
            self.status = MatchStatus(self.status)

        # 确保match_date是datetime对象
        if isinstance(self.match_date, str):
            self.match_date = datetime.fromisoformat(self.match_date.replace("Z", "+00:00"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Match":
        """从字典创建Match实例."""
        return cls(
            match_id=data.get("match_id", ""),
            home_team=data.get("home_team", {}),
            away_team=data.get("away_team", {}),
            league=data.get("league", ""),
            match_date=data.get("match_date"),
            status=data.get("status", "scheduled"),
            venue=data.get("venue"),
            score=data.get("score"),
            weather=data.get("weather"),
            odds=data.get("odds")
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "match_id": self.match_id,
            "home_team": self.home_team.to_dict() if isinstance(self.home_team, Team) else self.home_team,
            "away_team": self.away_team.to_dict() if isinstance(self.away_team, Team) else self.away_team,
            "league": self.league,
            "match_date": self.match_date.isoformat(),
            "status": self.status.value,
            "venue": self.venue,
            "score": self.score,
            "weather": self.weather,
            "odds": self.odds
        }


@dataclass
class Prediction:
    """预测模型."""
    prediction_id: str
    match_id: str
    probabilities: dict[str, float]
    recommended_bet: str
    confidence_score: float
    model_version: str
    created_at: datetime
    status: PredictionStatus = PredictionStatus.PROCESSING
    actual_result: str | None = None
    is_correct: bool | None = None
    features_used: list[str] | None = None
    explanation: str | None = None

    def __post_init__(self):
        """后处理：确保字段类型正确."""
        # 确保status是PredictionStatus枚举
        if isinstance(self.status, str):
            self.status = PredictionStatus(self.status)

        # 确保created_at是datetime对象
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Prediction":
        """从字典创建Prediction实例."""
        return cls(
            prediction_id=data.get("prediction_id", ""),
            match_id=data.get("match_id", ""),
            probabilities=data.get("probabilities", {}),
            recommended_bet=data.get("recommended_bet", ""),
            confidence_score=data.get("confidence_score", 0.0),
            model_version=data.get("model_version", ""),
            created_at=data.get("created_at"),
            status=data.get("status", "processing"),
            actual_result=data.get("actual_result"),
            is_correct=data.get("is_correct"),
            features_used=data.get("features_used"),
            explanation=data.get("explanation")
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "prediction_id": self.prediction_id,
            "match_id": self.match_id,
            "probabilities": self.probabilities,
            "recommended_bet": self.recommended_bet,
            "confidence_score": self.confidence_score,
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "actual_result": self.actual_result,
            "is_correct": self.is_correct,
            "features_used": self.features_used,
            "explanation": self.explanation
        }


@dataclass
class PredictionRequest:
    """预测请求模型."""
    match_id: str
    home_team: str
    away_team: str
    match_date: datetime
    league: str
    features: dict[str, Any] | None = None
    priority: str = "normal"
    include_explanation: bool = False

    def __post_init__(self):
        """后处理：确保match_date是datetime对象."""
        if isinstance(self.match_date, str):
            self.match_date = datetime.fromisoformat(self.match_date.replace("Z", "+00:00"))

    def to_dict(self) -> dict[str, Any]:
        """转换为请求字典."""
        data = {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "match_date": self.match_date.isoformat(),
            "league": self.league
        }

        if self.features:
            data["features"] = self.features

        if self.priority != "normal":
            data["priority"] = self.priority

        if self.include_explanation:
            data["include_explanation"] = True

        return data


@dataclass
class PredictionResponse:
    """预测响应模型."""
    success: bool
    prediction: Prediction | None = None
    error: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PredictionResponse":
        """从字典创建PredictionResponse实例."""
        prediction_data = data.get("data")
        prediction = None

        if prediction_data:
            # 处理预测数据
            if "prediction_id" in prediction_data:
                prediction = Prediction.from_dict(prediction_data)
            else:
                # 创建新的预测对象
                prediction = Prediction(
                    prediction_id=prediction_data.get("prediction_id", ""),
                    match_id=prediction_data.get("match_id", ""),
                    probabilities=prediction_data.get("prediction", {}).get("probabilities", {}),
                    recommended_bet=prediction_data.get("prediction", {}).get("recommended_bet", ""),
                    confidence_score=prediction_data.get("prediction", {}).get("confidence_score", 0.0),
                    model_version=prediction_data.get("model_info", {}).get("model_version", ""),
                    created_at=data.get("meta", {}).get("timestamp", datetime.now()),
                    status=PredictionStatus.PROCESSING
                )

        return cls(
            success=data.get("success", False),
            prediction=prediction,
            error=data.get("error"),
            meta=data.get("meta")
        )


@dataclass
class MatchListResponse:
    """比赛列表响应模型."""
    success: bool
    matches: list[Match] = field(default_factory=list)
    pagination: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MatchListResponse":
        """从字典创建MatchListResponse实例."""
        matches_data = data.get("data", [])
        matches = [Match.from_dict(match_data) for match_data in matches_data]

        return cls(
            success=data.get("success", False),
            matches=matches,
            pagination=data.get("meta", {}).get("pagination"),
            meta=data.get("meta")
        )


@dataclass
class SubscriptionInfo:
    """订阅信息模型."""
    plan: SubscriptionPlan
    expires_at: datetime | None = None
    features: list[str] = field(default_factory=list)
    auto_renew: bool = False

    def __post_init__(self):
        """后处理：确保字段类型正确."""
        # 确保plan是SubscriptionPlan枚举
        if isinstance(self.plan, str):
            self.plan = SubscriptionPlan(self.plan)

        # 确保expires_at是datetime对象
        if isinstance(self.expires_at, str):
            self.expires_at = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SubscriptionInfo":
        """从字典创建SubscriptionInfo实例."""
        return cls(
            plan=data.get("plan", "free"),
            expires_at=data.get("expires_at"),
            features=data.get("features", []),
            auto_renew=data.get("auto_renew", False)
        )


@dataclass
class UserPreferences:
    """用户偏好设置模型."""
    favorite_teams: list[str] = field(default_factory=list)
    notification_settings: dict[str, bool] = field(default_factory=dict)
    language: str = "zh-CN"
    timezone: str = "UTC+8"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPreferences":
        """从字典创建UserPreferences实例."""
        return cls(
            favorite_teams=data.get("favorite_teams", []),
            notification_settings=data.get("notification_settings", {}),
            language=data.get("language", "zh-CN"),
            timezone=data.get("timezone", "UTC+8")
        )


@dataclass
class User:
    """用户模型."""
    user_id: str
    username: str
    email: str
    subscription: SubscriptionInfo
    preferences: UserPreferences
    created_at: datetime | None = None
    last_login: datetime | None = None

    def __post_init__(self):
        """后处理：确保字段类型正确."""
        # 确保subscription是SubscriptionInfo对象
        if isinstance(self.subscription, dict):
            self.subscription = SubscriptionInfo.from_dict(self.subscription)

        # 确保preferences是UserPreferences对象
        if isinstance(self.preferences, dict):
            self.preferences = UserPreferences.from_dict(self.preferences)

        # 确保时间字段是datetime对象
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        if isinstance(self.last_login, str):
            self.last_login = datetime.fromisoformat(self.last_login.replace("Z", "+00:00"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """从字典创建User实例."""
        return cls(
            user_id=data.get("user_id", ""),
            username=data.get("username", ""),
            email=data.get("email", ""),
            subscription=data.get("subscription", {}),
            preferences=data.get("preferences", {}),
            created_at=data.get("created_at"),
            last_login=data.get("last_login")
        )


@dataclass
class UserProfileResponse:
    """用户配置响应模型."""
    success: bool
    user: User | None = None
    error: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserProfileResponse":
        """从字典创建UserProfileResponse实例."""
        user_data = data.get("data")
        user = None

        if user_data:
            user = User.from_dict(user_data)

        return cls(
            success=data.get("success", False),
            user=user,
            error=data.get("error"),
            meta=data.get("meta")
        )


@dataclass
class UserStatistics:
    """用户统计信息模型."""
    total_predictions: int
    successful_predictions: int
    success_rate: float
    favorite_league: str | None = None
    monthly_stats: list[dict[str, Any]] = field(default_factory=list)
    average_confidence: float = 0.0
    best_streak: int = 0
    current_streak: int = 0

    @property
    def total_failed_predictions(self) -> int:
        """总失败预测数."""
        return self.total_predictions - self.successful_predictions

    @property
    def success_percentage(self) -> str:
        """成功率百分比字符串."""
        return f"{self.success_rate * 100:.1f}%"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserStatistics":
        """从字典创建UserStatistics实例."""
        return cls(
            total_predictions=data.get("total_predictions", 0),
            successful_predictions=data.get("successful_predictions", 0),
            success_rate=data.get("success_rate", 0.0),
            favorite_league=data.get("favorite_league"),
            monthly_stats=data.get("monthly_stats", []),
            average_confidence=data.get("average_confidence", 0.0),
            best_streak=data.get("best_streak", 0),
            current_streak=data.get("current_streak", 0)
        )
