
"""
Data Models - Pydantic data model definitions
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MatchStatus(str, Enum):
    """Match status enumeration"""
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class HomeAway(str, Enum):
    """Home/Away team identifier"""
    HOME = "home"
    AWAY = "away"


class LeagueTier(str, Enum):
    """League tier for sentinel mechanism"""
    TOP_5 = "top_5"
    TOP_TIER = "top_tier"
    SECOND_TIER = "second_tier"


class TeamStats(BaseModel):
    """Team statistics data model"""
    model_config = ConfigDict(str_strip_whitespace=True)

    shots_total: int | None = Field(None, alias="shotsTotal")
    shots_on_target: int | None = Field(None, alias="shotsOnTarget")
    possession: float | None = Field(None, ge=0, le=100)
    corners: int | None = None
    offsides: int | None = None
    fouls: int | None = None
    expected_goals: float | None = Field(None, ge=0, alias="expectedGoals")
    team_rating: float | None = Field(None, ge=0, le=10, alias="teamRating")
    momentum_scores: list[float] | None = Field(default_factory=list)


class PlayerStats(BaseModel):
    """Player statistics data model"""
    model_config = ConfigDict(str_strip_whitespace=True)

    player_id: str | None = Field(None, alias="playerId")
    player_name: str | None = Field(None, alias="playerName")
    team_id: str | None = Field(None, alias="teamId")
    jersey_number: int | None = Field(None, ge=1, le=99, alias="jerseyNumber")
    is_starter: bool | None = Field(None, alias="isStarter")
    minutes_played: int | None = Field(None, ge=0, le=120, alias="minutesPlayed")
    expected_goals: float | None = Field(None, ge=0, alias="expectedGoals")
    total_shots: int | None = Field(None, ge=0, alias="totalShots")
    touches: int | None = Field(None, ge=0)
    accurate_passes: int | None = Field(None, ge=0, alias="accuratePasses")
    market_value: float | None = Field(None, ge=0, alias="marketValue")
    age: int | None = Field(None, ge=16, le=50)
    team_rating: float | None = Field(None, ge=0, le=10, alias="teamRating")


class MatchContext(BaseModel):
    """Match context information"""
    model_config = ConfigDict(str_strip_whitespace=True)

    match_time: datetime | None = Field(None, alias="matchTime")
    kickoff_time: str | None = Field(None, alias="kickoffTime")
    venue: str | None = None
    venue_capacity: int | None = Field(None, ge=0, alias="venueCapacity")
    venue_attendance: int | None = Field(None, ge=0, alias="venueAttendance")
    is_neutral: bool | None = Field(None, alias="isNeutral")
    referee_id: str | None = Field(None, alias="refereeId")
    referee_name: str | None = Field(None, alias="refereeName")
    referee_nationality: str | None = Field(None, alias="refereeNationality")
    weather_temperature: float | None = Field(None, alias="weatherTemperature")
    weather_condition: str | None = Field(None, alias="weatherCondition")
    is_cup_match: bool | None = Field(None, alias="isCupMatch")
    days_since_last_match: int | None = Field(None, ge=0, alias="daysSinceLastMatch")
    match_importance: float | None = Field(default=0.5, ge=0, le=1)
    odds: dict[str, Any] | None = None


class LineupInfo(BaseModel):
    """Lineup information model"""
    model_config = ConfigDict(str_strip_whitespace=True)

    formation: str | None = None
    starters_count: int | None = Field(None, ge=11, le=11, alias="startersCount")
    substitutes_count: int | None = Field(None, ge=0, alias="substitutesCount")
    unchanged_lineup: bool = Field(False, alias="unchangedLineup")
    changes_from_last_match: int | None = Field(None, ge=0, alias="changesFromLastMatch")
    total_market_value: float | None = Field(None, ge=0, alias="totalMarketValue")
    avg_market_value: float | None = Field(None, ge=0, alias="avgMarketValue")
    players: list[PlayerStats] = Field(default_factory=list)


class MatchData(BaseModel):
    """Main match data model"""
    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    match_id: str = Field(..., min_length=1)
    league_id: str = Field(..., min_length=1)
    season: str = Field(..., pattern=r"^\d{4}$")
    home_team: str = Field(..., min_length=1)
    away_team: str = Field(..., min_length=1)
    status: MatchStatus = MatchStatus.SCHEDULED
    home_score: int | None = Field(None, ge=0)
    away_score: int | None = Field(None, ge=0)
    home_stats: TeamStats | None = None
    away_stats: TeamStats | None = None
    context: MatchContext | None = None
    home_lineup: LineupInfo | None = None
    away_lineup: LineupInfo | None = None
    raw_data: dict[str, Any] | None = Field(default_factory=dict, exclude=True)

    @field_validator("season")
    @classmethod
    def validate_season(cls, v: str) -> str:
        if len(v) != 4 or not v.isdigit():
            raise ValueError("Season must be 4 digits like 2324")
        return v

    def get_team_stats(self, side: HomeAway) -> TeamStats | None:
        """Get stats for specified team"""
        return self.home_stats if side == HomeAway.HOME else self.away_stats

    def get_team_lineup(self, side: HomeAway) -> LineupInfo | None:
        """Get lineup for specified team"""
        return self.home_lineup if side == HomeAway.HOME else self.away_lineup


class FeatureVector(BaseModel):
    """Feature vector model"""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="allow",
    )

    match_id: str = Field(..., min_length=1)
    feature_version: str = Field(default="21.0.0")
    extracted_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (excluding metadata)"""
        return self.model_dump(exclude={"match_id", "feature_version", "extracted_at"})

    def to_flat_dict(self) -> dict[str, Any]:
        """Convert to flat dictionary (including metadata)"""
        return self.model_dump()


class ProcessingContext(BaseModel):
    """Processing context model"""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
    )

    match_id: str | None = None
    session_id: str | None = Field(default_factory=lambda: f"session_{datetime.now().timestamp()}")
    cache: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    checkpoint: dict[str, str] = Field(default_factory=dict)
    completed_processors: set[str] = Field(default_factory=set)

    def get_option(self, key: str, default: Any = None) -> Any:
        """Get configuration option"""
        return self.options.get(key, default)

    def set_option(self, key: str, value: Any) -> None:
        """Set configuration option"""
        self.options[key] = value

    def get_cached(self, key: str, default: Any = None) -> Any:
        """Get cached data"""
        return self.cache.get(key, default)

    def set_cached(self, key: str, value: Any) -> None:
        """Set cached data"""
        self.cache[key] = value

    def mark_completed(self, processor_name: str) -> None:
        """Mark processor as completed"""
        self.completed_processors.add(processor_name)

    def is_completed(self, processor_name: str) -> bool:
        """Check if processor is completed"""
        return processor_name in self.completed_processors


__all__ = [
    "FeatureVector",
    "HomeAway",
    "LeagueTier",
    "LineupInfo",
    "MatchContext",
    "MatchData",
    "MatchStatus",
    "PlayerStats",
    "ProcessingContext",
    "TeamStats",
]
