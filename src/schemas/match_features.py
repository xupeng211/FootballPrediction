#!/usr/bin/env python3
"""
Match Features Pydantic Schema - 106
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

# V4.42:              -          ?         ?\nfrom src.constants.shared_constants import MatchStatus, DataSource\nfrom src.database.models import FotMobMatchData  # noqa: W505


class WeatherCondition(str, Enum):
    """ """

    SUNNY = "sunny"
    RAINY = "rainy"
    CLOUDY = "cloudy"
    SNOWY = "snowy"
    WINDY = "windy"
    UNKNOWN = "unknown"


class FeatureVersion(str, Enum):
    """ """

    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


class DataSource(str, Enum):
    """?"""

    FOTMOB_API = "fotmob_api"
    BET365_API = "bet365_api"
    MANUAL = "manual"
    IMPORTED = "imported"


class MatchFeatures(BaseModel):
    """
    class MatchFeatures(BaseModel):
    """

    """













































    ?    """

    # ====================              (10   ? ====================
    external_id: str = Field(..., description="            ID")
    match_time: datetime = Field(..., description="            ")
    home_team: str = Field(..., min_length=1, max_length=100, description="            ")
    away_team: str = Field(..., min_length=1, max_length=100, description="            ")
    league_id: str | None = Field(None, max_length=20, description="      ID")
    league_name: str | None = Field(None, max_length=100, description="            ")
    season: str | None = Field(None, max_length=20, description="      ")
    status: str | None = Field(None, max_length=50, description="            ?")
    home_score: int | None = Field(None, ge=0, description="            ")
    away_score: int | None = Field(None, ge=0, description="            ")

    # ==================== xG             (10   ? ====================
    home_xg: float | None = Field(None, ge=0.0, description="                     ?")
    away_xg: float | None = Field(None, ge=0.0, description="                     ?")
    xg_total: float | None = Field(None, ge=0.0, description="                  ")
    xg_diff: float | None = Field(None, description="                  ?")
    home_xg_first_half: float | None = Field(
        None, ge=0.0, description="                              "
    )
    away_xg_first_half: float | None = Field(
        None, ge=0.0, description="                              "
    )
    xg_total_first_half: float | None = Field(
        None, ge=0.0, description="                           "
    )
    home_xg_second_half: float | None = Field(
        None, ge=0.0, description="                              "
    )
    away_xg_second_half: float | None = Field(
        None, ge=0.0, description="                              "
    )
    xg_total_second_half: float | None = Field(
        None, ge=0.0, description="                           "
    )
    xg_dynamic_trend: str | None = Field(None, max_length=20, description="xG            ?")

    # ====================                ?(8   ? ====================
    home_possession: float | None = Field(None, ge=0.0, le=100.0, description="               ?%)")
    away_possession: float | None = Field(None, ge=0.0, le=100.0, description="               ?%)")
    possession_diff: float | None = Field(None, ge=-100.0, le=100.0, description="               ?")
    home_possession_first_half: float | None = Field(
        None, ge=0.0, le=100.0, description="                        "
    )
    away_possession_first_half: float | None = Field(
        None, ge=0.0, le=100.0, description="                        "
    )
    possession_first_half_diff: float | None = Field(
        None, ge=-100.0, le=100.0, description="                        ?"
    )

    home_possession_second_half: float | None = Field(
        None, ge=0.0, le=100.0, description="                        "
    )
    away_possession_second_half: float | None = Field(
        None, ge=0.0, le=100.0, description="                        "
    )
    possession_second_half_diff: float | None = Field(
        None, ge=-100.0, le=100.0, description="                        ?"
    )

    # ====================              (12   ? ====================
    home_shots_total: int | None = Field(None, ge=0, description="                  ")
    away_shots_total: int | None = Field(None, ge=0, description="                  ")
    shots_total_diff: int | None = Field(None, description="                  ?")
    home_shots_on_target: int | None = Field(None, ge=0, description="               ?")
    away_shots_on_target: int | None = Field(None, ge=0, description="               ?")
    shots_on_target_diff: int | None = Field(None, description="               ?")
    home_shots_off_target: int | None = Field(None, ge=0, description="               ?")
    away_shots_off_target: int | None = Field(None, ge=0, description="               ?")
    shots_off_target_diff: int | None = Field(None, description="               ?")
    home_shots_blocked: int | None = Field(None, ge=0, description="                        ")
    away_shots_blocked: int | None = Field(None, ge=0, description="                        ")
    shots_blocked_diff: int | None = Field(None, description="                        ?")
    home_shot_accuracy: float | None = Field(
        None, ge=0.0, le=100.0, description="                     ?"
    )
    away_shot_accuracy: float | None = Field(
        None, ge=0.0, le=100.0, description="                     ?"
    )
    shot_accuracy_diff: float | None = Field(
        None, ge=-100.0, le=100.0, description="                     ?"
    )

    # ====================              (8   ? ====================
    home_corners: int | None = Field(None, ge=0, description="               ?")
    away_corners: int | None = Field(None, ge=0, description="               ?")
    corners_diff: int | None = Field(None, description="               ?")
    home_corners_first_half: int | None = Field(None, ge=0, description="                        ")
    away_corners_first_half: int | None = Field(None, ge=0, description="                        ")
    corners_first_half_diff: int | None = Field(None, description="                        ?")
    home_corners_second_half: int | None = Field(None, ge=0, description="                        ")
    away_corners_second_half: int | None = Field(None, ge=0, description="                        ")
    corners_second_half_diff: int | None = Field(None, description="                        ?")

    # ====================              (6   ? ====================
    home_fouls: int | None = Field(None, ge=0, description="               ?")
    away_fouls: int | None = Field(None, ge=0, description="               ?")
    fouls_diff: int | None = Field(None, description="               ?")
    home_yellow_cards: int | None = Field(None, ge=0, description="               ?")
    away_yellow_cards: int | None = Field(None, ge=0, description="               ?")
    yellow_cards_diff: int | None = Field(None, description="               ?")
    home_red_cards: int | None = Field(None, ge=0, description="               ?")
    away_red_cards: int | None = Field(None, ge=0, description="               ?")
    red_cards_diff: int | None = Field(None, description="               ?")

    # ====================              (3   ? ====================
    home_offsides: int | None = Field(None, ge=0, description="               ?")
    away_offsides: int | None = Field(None, ge=0, description="               ?")
    offsides_diff: int | None = Field(None, description="               ?")

    # ====================              (9   ? ====================
    home_passes: int | None = Field(None, ge=0, description="               ?")
    away_passes: int | None = Field(None, ge=0, description="               ?")
    passes_diff: int | None = Field(None, description="               ?")
    home_pass_accuracy: float | None = Field(
        None, ge=0.0, le=100.0, description="                     ?"
    )
    away_pass_accuracy: float | None = Field(
        None, ge=0.0, le=100.0, description="                     ?"
    )
    pass_accuracy_diff: float | None = Field(
        None, ge=-100.0, le=100.0, description="                     ?"
    )
    home_successful_passes: int | None = Field(None, ge=0, description="                     ?")
    away_successful_passes: int | None = Field(None, ge=0, description="                     ?")
    successful_passes_diff: int | None = Field(None, description="                     ?")

    # ====================              (5   ? ====================
    home_aerial_won: int | None = Field(None, ge=0, description="                        ")
    away_aerial_won: int | None = Field(None, ge=0, description="                        ")
    aerial_won_diff: int | None = Field(None, description="                        ?")
    home_aerial_won_percentage: float | None = Field(
        None, ge=0.0, le=100.0, description="                     ?"
    )
    away_aerial_won_percentage: float | None = Field(
        None, ge=0.0, le=100.0, description="                     ?"
    )
    aerial_won_percentage_diff: float | None = Field(
        None, ge=-100.0, le=100.0, description="                     ?"
    )

    # ====================              (13   ? ====================
    home_opening_odds: float | None = Field(None, ge=0.0, description="                  ?")
    away_opening_odds: float | None = Field(None, ge=0.0, description="                  ?")
    draw_odds: float | None = Field(None, ge=0.0, description="                  ?")
    home_current_odds: float | None = Field(None, ge=0.0, description="                  ")
    away_current_odds: float | None = Field(None, ge=0.0, description="                  ")
    draw_current_odds: float | None = Field(None, ge=0.0, description="                  ")
    odds_movement_home: float | None = Field(None, description="                  ")
    odds_movement_away: float | None = Field(None, description="                  ")
    odds_movement_draw: float | None = Field(None, description="                  ")
    implied_home_win_prob: float | None = Field(
        None, ge=0.0, le=1.0, description="                  "
    )
    implied_away_win_prob: float | None = Field(
        None, ge=0.0, le=1.0, description="                  "
    )
    implied_draw_prob: float | None = Field(None, ge=0.0, le=1.0, description="                  ")

    # ====================              (3   ? ====================
    total_over_under: float | None = Field(None, gt=0.0, description="               ?")
    asian_handicap: float | None = Field(None, description="            ")
    both_teams_to_score_odds: float | None = Field(None, gt=0.0, description="                  ")

    # ====================       H2H       (5   ? ====================
    home_team_h2h_wins: int | None = Field(None, ge=0, description="                        ")
    away_team_h2h_wins: int | None = Field(None, ge=0, description="                        ")
    h2h_draws: int | None = Field(None, ge=0, description="                  ")
    home_team_h2h_goals: int | None = Field(None, ge=0, description="                           ?")
    away_team_h2h_goals: int | None = Field(None, ge=0, description="                           ?")

    # ====================                   ?(6   ? ====================
    home_team_form_points: int | None = Field(None, description="                  ")
    away_team_form_points: int | None = Field(None, description="                  ")
    home_team_recent_goals: int | None = Field(None, ge=0, description="                     ?")
    away_team_recent_goals: int | None = Field(None, ge=0, description="                     ?")
    home_team_recent_conceded: int | None = Field(None, ge=0, description="                     ?")
    away_team_recent_conceded: int | None = Field(None, ge=0, description="                     ?")

    # ====================                      ?(3   ? ====================
    weather_condition: WeatherCondition | None = Field(None, description="            ")
    temperature: float | None = Field(None, description="      (         ?")
    home_advantage_score: float | None = Field(
        None, ge=0.0, le=1.0, description="                  "
    )

    # ====================                   ?(6   ? ====================
    expected_assists_home: float | None = Field(None, ge=0.0, description="                     ?")
    expected_assists_away: float | None = Field(None, ge=0.0, description="                     ?")
    big_chances_home: int | None = Field(None, ge=0, description="                  ")
    big_chances_away: int | None = Field(None, ge=0, description="                  ")
    big_chances_missed_home: int | None = Field(None, ge=0, description="                        ")
    big_chances_missed_away: int | None = Field(None, ge=0, description="                        ")

    # ====================          VAR       (2   ? ====================
    referee_name: str | None = Field(None, max_length=100, description="            ")
    var_used: bool | None = Field(None, description="            VAR")

    # ====================          ?(9   ? ====================
    raw_data_source: DataSource = Field(DataSource.FOTMOB_API, description="         ?")
    feature_version: FeatureVersion = Field(FeatureVersion.V1_0, description="            ")
    feature_quality_score: float | None = Field(
        None, ge=0.0, le=1.0, description="                  "
    )
    extraction_confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="               ?"
    )
    data_completeness_score: float | None = Field(
        None, ge=0.0, le=1.0, description="                     ?"
    )
    extracted_at: datetime = Field(default_factory=datetime.now, description="            ")
    updated_at: datetime = Field(default_factory=datetime.now, description="            ")
    created_at: datetime = Field(default_factory=datetime.now, description="            ")

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            WeatherCondition: lambda v: v.value,
            DataSource: lambda v: v.value,
            FeatureVersion: lambda v: v.value,
        },
    )

    @computed_field
    @property
    def total_features_count(self) -> int:
        """?"""
        return 106

    @computed_field
    @property
    def has_complete_xg_data(self) -> bool:
        """xG"""

        return all(
            [
                self.home_xg is not None,
                self.away_xg is not None,
                self.xg_total is not None,
                self.xg_diff is not None,
            ]
        )

    @computed_field
    @property
    def has_complete_odds_data(self) -> bool:
        """ """
        return all(
            [
                self.home_opening_odds is not None,
                self.away_opening_odds is not None,
                self.draw_odds is not None,
            ]
        )


class MatchFeaturesTrainingBatch(BaseModel):
    """ """

    features: list[MatchFeatures]
    batch_id: str
    batch_size: int
    total_processed: int
    processing_time_seconds: float

    @field_validator("batch_size", mode="before")
    @classmethod
    def validate_batch_size(cls, v, info):
        """ """
        values = info.data if hasattr(info, "data") else {}
        if "features" in values:
            return len(values["features"])
        return v

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class FeatureExtractionRequest(BaseModel):
    """ """

    match_ids: list[str]
    extraction_mode: str = Field("full", pattern="^(full|incremental)$")
    batch_size: int = Field(50, ge=1, le=1000)
    use_cache: bool = True
    extract_advanced_features: bool = True


class FeatureExtractionResponse(BaseModel):
    """ """

    request_id: str
    status: str = Field(..., pattern="^(success|partial|failed)$")
    processed_count: int
    total_count: int
    success_count: int
    failed_count: int
    processing_time_seconds: float
    features: list[MatchFeatures] | None = None
    errors: list[str] | None = None
    metadata: dict[str, Any] | None = None

    #                      ?def create_match_features_from_dict(data: dict[str, Any]) -> MatchFeatures:  # noqa: W505
    # [dead code removed in parse-fix] orphaned docstring
    # [dead code removed in parse-fix] return MatchFeatures(**data)


def validate_feature_completeness(features: MatchFeatures) -> float:
    """?"""

    total_fields = 106
    non_null_fields = sum(
        1 for field, value in features.model_dump().items() if value is not None and value != ""
    )
    return non_null_fields / total_fields


if __name__ == "__main__":
    test_data = {
        "external_id": "test_123",
        "match_time": "2024-01-15T20:00:00Z",
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "home_xg": 1.5,
        "away_xg": 1.2,
        "home_possession": 55.0,
        "away_possession": 45.0,
        "home_opening_odds": 2.15,
        "away_opening_odds": 3.40,
        "draw_odds": 3.20,
    }

    features = create_match_features_from_dict(test_data)  # noqa: F821
