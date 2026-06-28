#!/usr/bin/env python3
"""
V41.155 Match Schema -
========================================

      :
-        Source_F (FotMob             ??? ???Source_O (OddsPortal             )
-
-                               ???
Author: V41.155 Joint Auditor
Date: 2026-01-17
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ============================================================================
#
# ============================================================================


class MatchStatus(str, Enum):
    """?"""

    FIXTURE = "Fixture"
    LIVE = "Live"
    FINISHED = "Finished"
    POSTPONED = "Postponed"
    CANCELLED = "Cancelled"
    ABANDONED = "Abandoned"
    UNKNOWN = "Unknown"


class DataSourceType(str, Enum):
    """?""" ""

    FOTMOB = "Source_F"  #                   ???    ODDSPORTAL = "Source_O"  #


class MatchQuality(str, Enum):
    """ """

    EXCELLENT = "Excellent"  # Fusion_Score >= 90
    GOOD = "Good"  # 80 <= Fusion_Score < 90
    FAIR = "Fair"  # 60 <= Fusion_Score < 80
    POOR = "Poor"  # Fusion_Score < 60


# ============================================================================
# Source_F: FotMob                   ???# ============================================================================


class SourceFData(BaseModel):
    """Source_F: FotMob             ???
                               :
    - ID,       ,       ,
    -             ,
    """

    match_id: str = Field(..., min_length=1, description="                  ???")
    home_team: str = Field(..., min_length=1, max_length=200, description="            ")
    away_team: str = Field(..., min_length=1, max_length=200, description="            ")
    match_time: datetime = Field(..., description="             (UTC)")
    league_name: str = Field(..., min_length=1, max_length=200, description="            ")
    season: str = Field(..., min_length=1, max_length=20, description="      ")
    status: MatchStatus = Field(default=MatchStatus.FIXTURE, description="         ???")

    #          ???    home_score: int | None = Field(None, ge=0, description="            ")
    away_score: int | None = Field(None, ge=0, description="            ")
    venue_name: str | None = Field(None, max_length=200, description="            ")
    referee_name: str | None = Field(None, max_length=100, description="            ")

    #       ???    collection_status: str = Field(default="pending", description="         ?")
    l1_collected_at: datetime | None = Field(None, description="L1             ")

    @model_validator(mode="after")
    def validate_teams_different(self):
        """?"""
        if self.home_team and self.away_team and self.home_team == self.away_team:
            raise ValueError("                        ?")
        return self

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        """?"""
        if isinstance(v, str):
            status_map = {
                "fixture": "Fixture",
                "live": "Live",
                "finished": "Finished",
                "postponed": "Postponed",
                "cancelled": "Cancelled",
                "abandoned": "Abandoned",
            }
            return status_map.get(v.lower(), v)
        return v


# ============================================================================
# Source_O: OddsPortal
# ============================================================================


class SourceOData(BaseModel):
    """Source_O: OddsPortal

                      :
    -       URL (oddsportal_hash)
    -              (init/final odds)
    -             ???"""

    match_id: str = Field(..., min_length=1, description="                  ???")
    oddsportal_hash: str | None = Field(
        None, max_length=8, description="OddsPortal        (8      )"
    )
    oddsportal_url: str | None = Field(None, max_length=500, description="OddsPortal URL")

    init_h: float | None = Field(None, ge=1.01, le=50.00, description="                  ")
    init_d: float | None = Field(None, ge=1.01, le=50.00, description="                  ")
    init_a: float | None = Field(None, ge=1.01, le=50.00, description="                  ")

    final_h: float | None = Field(None, ge=1.01, le=50.00, description="                  ")
    final_d: float | None = Field(None, ge=1.01, le=50.00, description="                  ")
    final_a: float | None = Field(None, ge=1.01, le=50.00, description="                  ")

    integrity_score: float | None = Field(
        None, ge=0.90, le=1.20, description="            ???(1/P1+1/P2+1/P3)"
    )
    is_valid: bool = Field(default=False, description="                  ")

    #       ???    source_name: str = Field(default="Entity_P", description="            ?")
    l3_collected_at: datetime | None = Field(None, description="L3             ")

    @model_validator(mode="after")
    def calculate_integrity_score(self) -> "SourceOData":
        """?"""
        if all([self.final_h, self.final_d, self.final_a]):
            self.integrity_score = 1.0 / self.final_h + 1.0 / self.final_d + 1.0 / self.final_a
            #             : 1.02 < integrity_score < 1.08
            self.is_valid = 1.02 < self.integrity_score < 1.08
        return self


# ============================================================================
# MatchSchema:
# ============================================================================


class MatchSchema(BaseModel):
    """V41.155

           Source_F ???Source_O                                  ???                                                       ???
                :
    -              (40%): ID,       ,       ,       ,       ,    ???    -              (30%): oddsportal_hash, oddsportal_url
    -              (30%): init/final odds, integrity_score
    """

    # ===              (       Source_F) ===
    match_id: str = Field(..., min_length=1, description="                  ?")
    home_team: str = Field(..., min_length=1, max_length=200, description="            ")
    away_team: str = Field(..., min_length=1, max_length=200, description="            ")
    match_time: datetime = Field(..., description="             (UTC)")
    league_name: str = Field(..., min_length=1, max_length=200, description="            ")
    season: str = Field(..., min_length=1, max_length=20, description="      ")
    status: MatchStatus = Field(default=MatchStatus.FIXTURE, description="         ?")

    home_score: int | None = Field(None, ge=0, description="            ")
    away_score: int | None = Field(None, ge=0, description="            ")
    venue_name: str | None = Field(None, max_length=200, description="            ")

    # ===              (       Source_O) ===
    oddsportal_hash: str | None = Field(
        None, max_length=8, description="OddsPortal        (8      )"
    )
    oddsportal_url: str | None = Field(None, max_length=500, description="OddsPortal URL")

    # ===              (       Source_O) ===
    init_h: float | None = Field(None, ge=1.01, le=50.00, description="                  ")
    init_d: float | None = Field(None, ge=1.01, le=50.00, description="                  ")
    init_a: float | None = Field(None, ge=1.01, le=50.00, description="                  ")

    final_h: float | None = Field(None, ge=1.01, le=50.00, description="                  ")
    final_d: float | None = Field(None, ge=1.01, le=50.00, description="                  ")
    final_a: float | None = Field(None, ge=1.01, le=50.00, description="                  ")

    integrity_score: float | None = Field(None, ge=0.90, le=1.20, description="            ?")
    is_valid: bool = Field(default=False, description="                  ")

    # ===       ???===
    source_f_available: bool = Field(default=False, description="Source_F                   ")
    source_o_available: bool = Field(default=False, description="Source_O                   ")
    fusion_score: float = Field(default=0.0, ge=0.0, le=100.0, description="             (0-100)")
    quality_rating: MatchQuality = Field(
        default=MatchQuality.POOR, description="                  "
    )

    #       ???    l1_collected_at: datetime | None = Field(None, description="L1             ")
    l3_collected_at: datetime | None = Field(None, description="L3             ")
    updated_at: datetime = Field(default_factory=datetime.now, description="            ")

    @model_validator(mode="after")
    def calculate_fusion_score(self) -> "MatchSchema":
        """(Fusion_Score)

                     (                        ???:
        -             ???(50%): match_id, home_team, away_team, match_time, league_name, season
        -              (50%): oddsportal_hash

              :                          metrics_multi_source_data                   ???                                      ???"""
        score = 0.0

        #             ???(50%)
        if (
            self.match_id
            and self.home_team
            and self.away_team
            and self.match_time
            and self.league_name
            and self.season
        ):
            score += 50.0

        #              (50%)
        if self.oddsportal_hash:
            score += 50.0

        self.fusion_score = score

        if score >= 90:
            self.quality_rating = MatchQuality.EXCELLENT
        elif score >= 80:
            self.quality_rating = MatchQuality.GOOD
        elif score >= 60:
            self.quality_rating = MatchQuality.FAIR
        else:
            self.quality_rating = MatchQuality.POOR

        return self

    @model_validator(mode="after")
    def detect_source_availability(self) -> "MatchSchema":
        """?"""
        # Source_F       :
        self.source_f_available = bool(
            self.match_id
            and self.home_team
            and self.away_team
            and self.match_time
            and self.league_name
        )

        # Source_O       :
        self.source_o_available = bool(
            self.oddsportal_hash
            or any(
                [self.init_h, self.init_d, self.init_a, self.final_h, self.final_d, self.final_a]
            )
        )

        return self

    @classmethod
    def from_database_row(cls, row: dict[str, Any]) -> "MatchSchema":
        """???MatchSchema

        Args:
            row:                         ???
        Returns:
            MatchSchema
        """
        # ???matches
        match_id = row.get("match_id") or row.get("external_id")

        # ???matches_mapping
        oddsportal_hash = row.get("hash") or row.get("oddsportal_hash")
        oddsportal_url = row.get("url") or row.get("oddsportal_url")

        # ???metrics_multi_source_data
        init_h = row.get("init_h")
        init_d = row.get("init_d")
        init_a = row.get("init_a")
        final_h = row.get("final_h")
        final_d = row.get("final_d")
        final_a = row.get("final_a")
        integrity_score = row.get("integrity_score")

        status_value = row.get("status")
        if status_value:
            status_map = {
                "Fixture": "Fixture",
                "Live": "Live",
                "Finished": "Finished",
                "FT": "Finished",
                "Postponed": "Postponed",
                "Cancelled": "Cancelled",
                "Abandoned": "Abandoned",
                "Scheduled": "Fixture",  #       ???                "NS": "Fixture",  # Not Started
                "Unknown": "Unknown",
            }
            status = MatchStatus(status_map.get(status_value, "Fixture"))
        else:
            status = MatchStatus.FIXTURE

        return cls(
            match_id=match_id or "",
            home_team=row.get("home_team", ""),
            away_team=row.get("away_team", ""),
            match_time=row.get("match_time") or row.get("match_date"),
            league_name=row.get("league_name", ""),
            season=row.get("season", ""),
            status=status,
            home_score=row.get("home_score") or row.get("home_goals"),
            away_score=row.get("away_score") or row.get("away_goals"),
            venue_name=row.get("venue_name"),
            oddsportal_hash=oddsportal_hash,
            oddsportal_url=oddsportal_url,
            init_h=init_h,
            init_d=init_d,
            init_a=init_a,
            final_h=final_h,
            final_d=final_d,
            final_a=final_a,
            integrity_score=integrity_score,
            is_valid=bool(integrity_score and 1.02 < integrity_score < 1.08),
        )


# ============================================================================
#
# ============================================================================

__all__ = [
    "DataSourceType",
    "MatchQuality",
    "MatchSchema",
    "MatchStatus",
    "SourceFData",
    "SourceOData",
]
