#!/usr/bin/env python3
# ruff: noqa: PLR2004
"""Tests for report-only filtered feature matrix stats.

lifecycle: permanent
scope: GOLD-AUDIT-2AE report-only matrix validation
"""

from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "filtered_matrix_report",
    PROJECT_ROOT / "src" / "ml" / "features" / "filtered_matrix_report.py",
)
filtered_matrix_report = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(filtered_matrix_report)


def _eligible_row(match_id: str, home_score: int, away_score: int) -> dict:
    return {
        "match_id": match_id,
        "external_id": match_id.rsplit("_", 1)[-1],
        "home_score": home_score,
        "away_score": away_score,
        "data_version": "fotmob_live_v1",
        "golden_features": {
            "_source": "FotMob",
            "_version": "V3.0.0-PRO",
            "_extractedAt": "2026-07-06T00:00:00Z",
            "home_age_avg": 27.1,
            "away_age_avg": 25.4,
            "age_gap": 1.7,
            "home_market_value_total": 120000000,
            "away_market_value_total": 80000000,
            "home_injury_count": 1,
            "away_injury_count": 2,
            "home_rating_avg": 7.5,
            "away_rating_avg": 6.8,
            "rating_gap": 0.7,
        },
        "tactical_features": {
            "_version": "V3.0.0-PRO",
            "_extractedAt": "2026-07-06T00:00:00Z",
            "home_xg": 1.2,
            "away_shots": 9,
            "home_possession": 61,
        },
        "odds_movement_features": {
            "_version": "V3.0.0-PRO",
            "_extractedAt": "2026-07-06T00:00:00Z",
            "_data_quality": "INCOMPLETE_ODDS",
            "_error": "No odds data available",
            "has_odds_data": False,
            "current_home_odds": 0,
            "implied_prob_home": 0.333333,
        },
        "odds_features": {},
        "elo_features": {
            "_is_default": True,
            "home_elo": 1500,
            "away_elo": 1500,
            "elo_diff": 0,
            "elo_expected_home": 0.571,
        },
        "rolling_features": {},
        "efficiency_features": {},
        "draw_features": {},
        "market_sentiment": {},
        "stitch_summary": {},
    }


def test_report_only_filters_leakage_and_excludes_legacy_rows() -> None:
    rows = [
        _eligible_row("53_20252026_4830466", 2, 1),
        _eligible_row("53_20252026_4830467", 1, 1),
        {**_eligible_row("legacy", 0, 1), "data_version": "PHASE4.23"},
        {**_eligible_row("synthetic", 0, 1), "data_version": "PHASE4.43_SYNTHETIC"},
    ]

    report = filtered_matrix_report.build_filtered_feature_matrix_report(rows)

    assert report["TASK"] == "filtered_feature_matrix_report_only"
    assert report["mode"] == "report-only"
    assert report["db_write"] is False
    assert report["artifact_write"] is False
    assert report["model_fit"] is False
    assert report["dataset_write"] is False

    matrix = report["Filtered matrix"]
    assert matrix["filtered_matrix_rows"] == 2
    assert matrix["excluded_legacy_or_synthetic_rows"] == 2
    assert matrix["metadata_columns"] == 2
    assert matrix["model_signal_feature_columns"] > 0
    assert "golden_features._source" in matrix["excluded_metadata_names"]
    assert "golden_features._version" in matrix["excluded_metadata_names"]

    leakage = report["Leakage check"]
    assert leakage["postmatch_leakage_remaining_count"] == 0
    assert leakage["rating_remaining_count"] == 0
    assert leakage["default_elo_remaining_count"] == 0
    assert leakage["odds_fallback_remaining_count"] == 0
    assert leakage["unknown_or_audit_only_remaining_count"] == 0

    assert report["raw_group_totals"]["tactical_features"] > 0
    assert report["filtered_group_totals"]["tactical_features"] == 0
    assert report["filtered_group_totals"]["elo_features"] == 0
    assert report["filtered_group_totals"]["odds_movement_features"] == 0


def test_report_only_signal_summary_and_readiness_are_conservative() -> None:
    rows = [
        _eligible_row("53_20252026_4830466", 2, 1),
        _eligible_row("53_20252026_4830467", 1, 1),
        _eligible_row("53_20252026_4830468", 0, 2),
    ]

    report = filtered_matrix_report.build_filtered_feature_matrix_report(rows)

    assert report["Label audit"]["rows_with_scores"] == 3
    assert report["Label audit"]["home_win_count"] == 1
    assert report["Label audit"]["draw_count"] == 1
    assert report["Label audit"]["away_win_count"] == 1

    signal = report["Signal availability"]
    assert signal["market_value_signal_available"] is True
    assert signal["age_signal_available"] is True
    assert signal["injury_availability_signal_available"] is True
    assert signal["odds_signal_available"] is False
    assert signal["elo_signal_available"] is False

    readiness = report["Readiness"]
    assert readiness["TRAINING_READINESS_STATUS"] == "NOT_READY"
    assert readiness["SAFE_FOR_TRAINING_DRY_RUN"] is False
    assert readiness["SAFE_FOR_REAL_TRAINING"] is False
    assert readiness["SAFE_FOR_REAL_PREDICTION"] is False
    assert readiness["SAFE_FOR_BACKTEST"] is False


def _report_value_rows(values: list) -> list[dict]:
    return [
        {
            "external_id": str(index + 1),
            "data_version": "fotmob_live_v1",
            "golden_features": value,
        }
        for index, value in enumerate(values)
    ]


def test_report_only_text_source_is_not_numeric() -> None:
    rows = _report_value_rows(
        [
            {"home_market_value_source": "totalStarterMarketValue", "home_injury_count": 0},
            {"home_market_value_source": "totalStarterMarketValue", "home_injury_count": 1},
        ]
    )
    report = filtered_matrix_report.build_filtered_feature_matrix_report(rows)
    quality = report["Feature quality"]
    assert quality["numeric_feature_count"] == 1, quality
    assert quality["non_numeric_feature_count"] == 1
    assert quality["low_variance_feature_examples"] == ["golden_features.home_injury_count"]
    assert quality["constant_feature_examples"] == ["golden_features.home_market_value_source"]
    assert report["Filtered matrix"]["model_signal_feature_columns"] == 2


def test_report_only_numeric_conversion_boundaries_and_input_unchanged() -> None:
    cases = [
        ([0, 1, "bad"], False, False, 0, 3, False),
        (["0", "1"], True, False, 0, 2, True),
        (["0", 0], True, True, 0, 2, True),
        ([0, None, "", "1"], True, False, 0, 2, True),
        ([False, True], False, False, 0, 2, False),
        ([0, 1, float("inf")], False, False, 0, 3, False),
        ([float("-inf"), "nan"], False, False, 0, 2, False),
        (["inf", "-inf"], False, False, 0, 2, False),
        ([None, ""], False, False, 1, 0, False),
        ([0, None], True, False, 0, 1, False),
        ([0, None, ""], True, False, 1, 1, False),
        ([0, 1, 2], True, False, 0, 3, False),
    ]
    for values, numeric, all_zero, high_missing, non_null, expected_low_variance in cases:
        rows = _report_value_rows([{"home_injury_count": value} for value in values])
        before = deepcopy(rows)
        report = filtered_matrix_report.build_filtered_feature_matrix_report(rows)
        assert rows == before
        quality = report["Feature quality"]
        assert quality["numeric_feature_count"] == int(numeric), values
        assert quality["non_numeric_feature_count"] == int(not numeric), values
        assert quality["all_zero_feature_count"] == int(all_zero), values
        assert quality["high_missing_feature_count"] == high_missing, values
        assert quality["top_missing_features"][0]["non_null_count"] == non_null
        assert quality["low_variance_feature_examples"] == (
            ["golden_features.home_injury_count"] if expected_low_variance else []
        ), values
        assert report["Readiness"]["TRAINING_READINESS_STATUS"] == "NOT_READY"
        assert all(
            value is False
            for key, value in report["Readiness"].items()
            if key.startswith("SAFE_FOR_")
        )
        assert all(
            report[key] is False
            for key in ("db_write", "artifact_write", "model_fit", "dataset_write")
        )


def test_report_only_absent_feature_remains_missing() -> None:
    rows = _report_value_rows([{"home_injury_count": 0}, {}, {}])
    report = filtered_matrix_report.build_filtered_feature_matrix_report(rows)
    quality = report["Feature quality"]
    assert quality["numeric_feature_count"] == 1
    assert quality["non_numeric_feature_count"] == 0
    assert quality["all_zero_feature_count"] == 0
    assert quality["high_missing_feature_count"] == 1
    assert quality["top_missing_features"][0]["non_null_count"] == 1
    assert quality["low_variance_feature_examples"] == []
    assert rows == _report_value_rows([{"home_injury_count": 0}, {}, {}])


def test_report_only_low_variance_examples_are_sorted_and_limited() -> None:
    qualifying_features = (
        "home_market_value_total",
        "home_market_value_std",
        "home_market_value_min",
        "home_market_value_max",
        "home_market_value_avg",
        "home_injury_count",
        "home_age_avg",
        "away_market_value_total",
        "away_market_value_std",
        "away_market_value_min",
        "away_market_value_max",
        "away_market_value_avg",
        "away_injury_count",
    )
    repeated_values = dict.fromkeys(qualifying_features, 0)
    rows = _report_value_rows([{**repeated_values, "age_gap": "2"}, repeated_values.copy()])
    before = deepcopy(rows)

    report = filtered_matrix_report.build_filtered_feature_matrix_report(rows)

    quality = report["Feature quality"]
    assert quality["numeric_feature_count"] == 14
    assert quality["low_variance_feature_examples"] == [
        f"golden_features.{name}" for name in sorted(qualifying_features)[:12]
    ]
    assert rows == before
