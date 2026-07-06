#!/usr/bin/env python3
# ruff: noqa: PLR2004
"""Tests for report-only filtered feature matrix stats.

lifecycle: permanent
scope: GOLD-AUDIT-2AE report-only matrix validation
"""

from __future__ import annotations

import importlib.util
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
