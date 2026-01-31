"""
V85.0 Enterprise-Grade Data Models with Pydantic Validation

Provides strong type safety and validation for all data layers (L1/L2/L3).
Enforces business rules at the data model level with automatic validation.

Key Features:
    - Type-safe schemas for L1 (FotMob API), L2 (FotMob Web), L3 (OddsPortal)
    - Odds range validation (1.01 - 50.00)
    - Integrity score validation (1.02 - 1.08)
    - Automatic validation before database insertion
    - Clear error messages for invalid data
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ============================================================================
# Constants
# ============================================================================

# Odds validation range
MIN_ODDS_VALUE = 1.01
MAX_ODDS_VALUE = 50.00

# Integrity score validation range
MIN_INTEGRITY_SCORE = 1.02
MAX_INTEGRITY_SCORE = 1.08


# Entity source names
class EntitySource(str, Enum):
    """Valid entity source names for odds data."""

    PINNACLE = "Entity_P"
    WILLIAM_HILL = "Entity_WH"
    LADBROKES = "Entity_LB"
    ONEXBET = "Entity_B3"
    AVERAGE_ODDS = "Entity_AVG"


# ============================================================================
# L1: FotMob API - Base Match Data
# ============================================================================


class FotMobMatchData(BaseModel):
    """L1: Base match data from FotMob API.

    This represents the foundational match information retrieved from FotMob API.
    All odds data (L2/L3) is linked to this base data via match_id.
    """

    match_id: str = Field(..., min_length=1, description="Unique match identifier")
    home_team: str = Field(..., min_length=1, max_length=200, description="Home team name")
    away_team: str = Field(..., min_length=1, max_length=200, description="Away team name")
    match_date: datetime = Field(..., description="Match start time")
    league_name: str = Field(..., min_length=1, max_length=200, description="League name")
    season: str = Field(..., pattern=r"^\d{4}-\d{4}$", description="Season (e.g., 2024-2025)")
    oddsportal_url: str | None = Field(None, description="OddsPortal URL for L3 extraction")

    # Optional: Real-time statistics
    home_xg: float | None = Field(None, ge=0, le=20, description="Home team xG")
    away_xg: float | None = Field(None, ge=0, le=20, description="Away team xG")
    home_possession: float | None = Field(None, ge=0, le=100, description="Home possession %")
    away_possession: float | None = Field(None, ge=0, le=100, description="Away possession %")

    @model_validator(mode="after")
    def validate_team_names_different(self):
        """Ensure home and away teams are different."""
        if self.home_team and self.away_team and self.home_team == self.away_team:
            raise ValueError("Home and away teams must be different")
        return self

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# L2: FotMob Web - Opening Odds (Hover Extraction)
# ============================================================================


class OpeningOddsData(BaseModel):
    """L2: Opening odds data extracted via hover from FotMob Web.

    This data is captured by hovering over bookmaker elements on FotMob,
    which reveals the initial odds and their publication timestamps.
    """

    match_id: str = Field(..., min_length=1, description="Match identifier")
    source_name: EntitySource = Field(..., description="Bookmaker entity code")

    # Opening odds (may have only one value from hover)
    init_h: float | None = Field(
        None, ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE, description="Initial home win odds"
    )
    init_d: float | None = Field(
        None, ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE, description="Initial draw odds"
    )
    init_a: float | None = Field(
        None, ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE, description="Initial away win odds"
    )

    # Opening timestamps
    opening_time_h: datetime | None = Field(None, description="Home odds opening time")
    opening_time_d: datetime | None = Field(None, description="Draw odds opening time")
    opening_time_a: datetime | None = Field(None, description="Away odds opening time")

    # Metadata
    hover_failed: bool = Field(False, description="Whether hover extraction failed")
    hover_error: str | None = Field(None, max_length=500, description="Error message if failed")
    extraction_method: Literal["hover_tooltip_production"] = Field(
        default="hover_tooltip_production", description="Extraction method identifier"
    )
    data_timestamp: datetime = Field(
        default_factory=datetime.now, description="When this record was created"
    )

    @field_validator("init_h", "init_d", "init_a")
    @classmethod
    def validate_odds_not_zero(cls, v):
        """Ensure odds are not zero or negative."""
        if v is not None and v < MIN_ODDS_VALUE:
            raise ValueError(f"Odds must be >= {MIN_ODDS_VALUE}, got {v}")
        return v

    @model_validator(mode="after")
    def validate_hover_data_consistency(self):
        """Ensure hover data is consistent."""
        # If hover failed, error should be present
        if self.hover_failed and not self.hover_error:
            self.hover_error = "Hover extraction failed without specific error"

        # If hover succeeded, should have at least init_h
        if not self.hover_failed and self.init_h is None:
            self.hover_failed = True
            self.hover_error = "Hover succeeded but no data captured"

        return self


# ============================================================================
# L3: OddsPortal - Final Odds (Direct Extraction)
# ============================================================================


class FinalOddsData(BaseModel):
    """L3: Final odds data extracted directly from OddsPortal.

    This data represents the closing odds before match start,
    extracted using V82.6 logic (.odds-text selector).
    """

    match_id: str = Field(..., min_length=1, description="Match identifier")
    url: str = Field(..., min_length=1, description="OddsPortal URL")
    source_name: EntitySource = Field(
        default=EntitySource.PINNACLE, description="Bookmaker entity code"
    )

    # Final odds (all three required for L3)
    final_h: float = Field(
        ..., ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE, description="Final home win odds"
    )
    final_d: float = Field(..., ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE, description="Final draw odds")
    final_a: float = Field(
        ..., ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE, description="Final away win odds"
    )

    # Validation metadata
    integrity_score: float = Field(default=0.0, description="Integrity score (1/P1 + 1/P2 + 1/P3)")
    is_valid: bool = Field(default=False, description="Whether integrity score is in valid range")
    validation_error: str | None = Field(
        None, max_length=500, description="Validation error if any"
    )

    # Extraction metadata
    pinnacle_found: bool = Field(..., description="Whether Pinnacle container was found")
    success: bool = Field(..., description="Whether extraction was successful")
    error: str | None = Field(None, max_length=500, description="Error message if failed")

    data_timestamp: datetime = Field(
        default_factory=datetime.now, description="When this record was created"
    )

    @field_validator("integrity_score")
    @classmethod
    def validate_integrity_score(cls, v):
        """Ensure integrity score is calculated correctly."""
        if not (MIN_INTEGRITY_SCORE <= v <= MAX_INTEGRITY_SCORE):
            # Allow invalid scores but mark them
            pass
        return v

    @model_validator(mode="after")
    def calculate_and_validate_integrity(self) -> "FinalOddsData":
        """Calculate integrity score and validate data consistency."""
        # Calculate integrity score
        self.integrity_score = 1.0 / self.final_h + 1.0 / self.final_d + 1.0 / self.final_a

        # Validate integrity score
        self.is_valid = MIN_INTEGRITY_SCORE < self.integrity_score < MAX_INTEGRITY_SCORE

        if not self.is_valid:
            self.validation_error = (
                f"Integrity score {self.integrity_score:.4f} "
                f"outside valid range [{MIN_INTEGRITY_SCORE}, {MAX_INTEGRITY_SCORE}]"
            )
        else:
            self.validation_error = None

        return self

    @model_validator(mode="after")
    def validate_success_consistency(self) -> "FinalOddsData":
        """Ensure success flag is consistent with data."""
        # If pinnacle not found, should not have odds
        if not self.pinnacle_found:
            self.success = False
            if not self.error:
                self.error = "Pinnacle container not found"

        # If success true, all odds should be present
        if self.success and not all([self.final_h, self.final_d, self.final_a]):
            self.success = False
            self.error = "Success marked but odds missing"

        return self


# ============================================================================
# Combined: Multi-Source Odds Data (Unified Schema)
# ============================================================================


class MultiSourceOddsData(BaseModel):
    """Unified odds data model combining L2 and L3 data.

    This model represents the complete odds data stored in
    metrics_multi_source_data table, combining opening and final odds.
    """

    match_id: str = Field(..., min_length=1, description="Match identifier")
    source_name: EntitySource = Field(..., description="Bookmaker entity code")

    # Initial (opening) odds from L2
    init_h: float | None = Field(None, ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE)
    init_d: float | None = Field(None, ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE)
    init_a: float | None = Field(None, ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE)

    # Opening timestamps from L2
    opening_time_h: datetime | None = None
    opening_time_d: datetime | None = None
    opening_time_a: datetime | None = None

    # Final odds from L3
    final_h: float | None = Field(None, ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE)
    final_d: float | None = Field(None, ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE)
    final_a: float | None = Field(None, ge=MIN_ODDS_VALUE, le=MAX_ODDS_VALUE)

    # Validation metadata
    integrity_score: float | None = Field(None, ge=0.90, le=1.20)
    is_valid: bool = Field(default=False)
    validation_error: str | None = Field(None, max_length=500)

    # Capture status
    fully_captured: bool = Field(default=False, description="All data dimensions present")
    data_timestamp: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="after")
    def calculate_integrity_score(self) -> "MultiSourceOddsData":
        """Calculate integrity score if final odds are present."""
        if all([self.final_h, self.final_d, self.final_a]):
            self.integrity_score = 1.0 / self.final_h + 1.0 / self.final_d + 1.0 / self.final_a

            # Validate integrity score
            self.is_valid = MIN_INTEGRITY_SCORE < self.integrity_score < MAX_INTEGRITY_SCORE

            if not self.is_valid:
                self.validation_error = (
                    f"Integrity score {self.integrity_score:.4f} "
                    f"outside valid range [{MIN_INTEGRITY_SCORE}, {MAX_INTEGRITY_SCORE}]"
                )

        # Check fully captured status
        has_final = all([self.final_h, self.final_d, self.final_a])
        has_initial = all([self.init_h, self.init_d, self.init_a])
        has_time = any([self.opening_time_h, self.opening_time_d, self.opening_time_a])

        self.fully_captured = has_final and has_initial and has_time

        # Special case: L2 hover-only data (init + time only)
        if has_initial and has_time and not has_final:
            self.is_valid = True
            self.validation_error = None

        return self

    def to_dict(self) -> dict:
        """Convert to dictionary for database operations."""
        return self.model_dump(exclude_none=True)


# ============================================================================
# Database Insertion Models
# ============================================================================


class OddsDataForInsert(BaseModel):
    """Validated odds data ready for database insertion.

    This model is used as the final validation step before
    inserting data into metrics_multi_source_data table.
    """

    match_id: str
    source_name: str
    init_h: float | None = None
    init_d: float | None = None
    init_a: float | None = None
    opening_time_h: datetime | None = None
    opening_time_d: datetime | None = None
    opening_time_a: datetime | None = None
    final_h: float | None = None
    final_d: float | None = None
    final_a: float | None = None
    integrity_score: float | None = None
    is_valid: bool = False
    validation_error: str | None = None
    fully_captured: bool = False
    data_timestamp: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="after")
    def validate_before_insert(self) -> "OddsDataForInsert":
        """Final validation before database insertion."""
        # Ensure at least some data is present
        has_init = any([self.init_h, self.init_d, self.init_a])
        has_final = any([self.final_h, self.final_d, self.final_a])

        if not has_init and not has_final:
            raise ValueError("No odds data present for insertion")

        # Recalculate integrity score if final odds present
        if all([self.final_h, self.final_d, self.final_a]):
            self.integrity_score = 1.0 / self.final_h + 1.0 / self.final_d + 1.0 / self.final_a
            self.is_valid = MIN_INTEGRITY_SCORE < self.integrity_score < MAX_INTEGRITY_SCORE

        return self


# ============================================================================
# Export All Models
# ============================================================================

__all__ = [
    "MAX_INTEGRITY_SCORE",
    "MAX_ODDS_VALUE",
    "MIN_INTEGRITY_SCORE",
    # Constants
    "MIN_ODDS_VALUE",
    "EntitySource",
    # L3 Models
    "FinalOddsData",
    # L1 Models
    "FotMobMatchData",
    # Combined Models
    "MultiSourceOddsData",
    "OddsDataForInsert",
    # L2 Models
    "OpeningOddsData",
]
