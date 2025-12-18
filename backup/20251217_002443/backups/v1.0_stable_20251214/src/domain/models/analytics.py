"""
Domain models for football analytics.

Contains Pydantic models for analytics data structures
following DDD principles.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TeamPerformanceStats(BaseModel):
    """Domain model for team performance statistics."""

    team_id: int = Field(..., description="Team identifier")
    team_name: str = Field(..., description="Team name")
    period_days: int = Field(..., description="Analysis period in days")
    matches_played: int = Field(..., ge=0, description="Number of matches played")

    performance: "PerformanceMetrics" = Field(
        ..., description="Win/Draw/Loss performance"
    )
    goals: "GoalsMetrics" = Field(..., description="Goals statistics")
    recent_form: list[str] = Field(
        default_factory=list, description="Recent match results"
    )
    form_summary: "FormSummary" = Field(..., description="Form trend analysis")
    metadata: "AnalyticsMetadata" = Field(..., description="Generation metadata")


class PerformanceMetrics(BaseModel):
    """Win/draw/loss performance metrics."""

    wins: int = Field(..., ge=0)
    draws: int = Field(..., ge=0)
    losses: int = Field(..., ge=0)
    win_rate: float = Field(..., ge=0, le=1)
    draw_rate: float = Field(..., ge=0, le=1)
    loss_rate: float = Field(..., ge=0, le=1)


class GoalsMetrics(BaseModel):
    """Goals-related metrics."""

    goals_for: int = Field(..., ge=0)
    goals_against: int = Field(..., ge=0)
    goal_difference: int = Field(..., description="Goal difference")
    avg_goals_for: float = Field(..., ge=0)
    avg_goals_against: float = Field(..., ge=0)
    clean_sheets: int = Field(..., ge=0, description="Matches with zero goals conceded")


class FormSummary(BaseModel):
    """Team form summary."""

    points: int = Field(..., ge=0)
    form_trend: str = Field(
        ..., description="Trend: improving/stable/declining/no_data"
    )
    last_match_date: Optional[datetime] = Field(None, description="Last match date")


class AnalyticsMetadata(BaseModel):
    """Metadata for analytics data."""

    generated_at: datetime = Field(..., description="When analytics were generated")
    data_freshness: str = Field(..., description="Data status: live/stale/no_data")


class LeagueStandingsStats(BaseModel):
    """Domain model for league standings statistics."""

    league_id: int = Field(..., description="League identifier")
    league_name: str = Field(..., description="League name")
    season: str = Field(..., description="Season identifier")
    total_teams: int = Field(..., ge=0)
    total_matches: int = Field(..., ge=0)
    matches_played: int = Field(..., ge=0)

    standings: list["StandingEntry"] = Field(..., description="League table")
    metadata: "AnalyticsMetadata" = Field(..., description="Generation metadata")


class StandingEntry(BaseModel):
    """Single entry in league standings."""

    position: int = Field(..., ge=1, description="League position")
    team_id: int = Field(..., description="Team identifier")
    team_name: str = Field(..., description="Team name")
    matches_played: int = Field(..., ge=0)
    wins: int = Field(..., ge=0)
    draws: int = Field(..., ge=0)
    losses: int = Field(..., ge=0)
    goals_for: int = Field(..., ge=0)
    goals_against: int = Field(..., ge=0)
    goal_difference: int = Field(..., description="Goal difference")
    points: int = Field(..., ge=0, description="League points")
    form: list[str] = Field(default_factory=list, description="Recent form")
