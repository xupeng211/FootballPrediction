"""Typed-context parity and leakage tests for the canonical prematch engine."""

from copy import deepcopy

import pytest

from src.ml.inference.canonical_prematch_feature_engine import (
    DECISION_TIME_PROVEN,
    KICKOFF_REFERENCE_ONLY,
    CanonicalPrematchFeatureError,
    accepted_feature_names,
    build_canonical_prematch_features,
)

EXPECTED_HOME_POINTS = 11
EXPECTED_AWAY_POINTS = 7
EXPECTED_POINTS_DIFF = 4


def _match(
    match_id,
    kickoff,
    home,
    away,
    home_xg,
    away_xg,
    outcome,
    available=None,
    competition="Premier League",
    season="2024/2025",
):
    return {
        "canonical_match_id": match_id,
        "kickoff_utc": kickoff,
        "competition": competition,
        "season": season,
        "home_team": home,
        "away_team": away,
        "home_xg": home_xg,
        "away_xg": away_xg,
        "outcome": outcome,
        "available_at_utc": available,
    }


def _context(*, decision_time=None, matches=None, closure_matches=None):
    source_matches = list(matches if matches is not None else _matches())
    closure_source = list(source_matches if closure_matches is None else closure_matches)
    return {
        "canonical_match_id": "target-001",
        "home_team": "Alpha",
        "away_team": "Beta",
        "competition": "Premier League",
        "season": "2024/2025",
        "target_kickoff_utc": "2025-01-10T12:00:00Z",
        "feature_as_of_utc": decision_time or "2025-01-10T12:00:00Z",
        "model_decision_time_utc": decision_time,
        "history_closure": {
            "status": "PROVEN",
            "authority": "canonical-schedule-history/v1",
            "competition": "Premier League",
            "season": "2024/2025",
            "team_names": ["Alpha", "Beta"],
            "prior_match_ids": [match["canonical_match_id"] for match in closure_source],
            "source_schedule_sha256": "c" * 64,
        },
        "prior_matches": source_matches,
    }


def _matches(available=None):
    return [
        _match("a1", "2025-01-01T12:00:00Z", "Alpha", "C", 1.0, 0.5, "home", available),
        _match("b1", "2025-01-01T15:00:00Z", "H", "Beta", 0.4, 1.8, "away", available),
        _match("a2", "2025-01-02T12:00:00Z", "D", "Alpha", 0.7, 1.1, "draw", available),
        _match("b2", "2025-01-02T15:00:00Z", "Beta", "I", 1.2, 0.6, "home", available),
        _match("a3", "2025-01-03T12:00:00Z", "Alpha", "E", 2.0, 0.3, "home", available),
        _match("b3", "2025-01-03T15:00:00Z", "J", "Beta", 0.9, 1.0, "draw", available),
        _match("a4", "2025-01-04T12:00:00Z", "F", "Alpha", 0.8, 1.4, "away", available),
        _match("b4", "2025-01-04T15:00:00Z", "Beta", "K", 0.5, 1.3, "away", available),
        _match("a5", "2025-01-05T12:00:00Z", "Alpha", "G", 1.5, 1.2, "draw", available),
        _match("b5", "2025-01-05T15:00:00Z", "L", "Beta", 2.0, 0.7, "home", available),
    ]


def test_registry_order_is_the_runtime_output_order() -> None:
    result = build_canonical_prematch_features(_context())

    assert tuple(result["feature_names"]) == accepted_feature_names()
    assert result["feature_as_of_status"] == KICKOFF_REFERENCE_ONLY
    assert result["model_decision_time_utc"] is None


def test_kickoff_reference_and_explicit_decision_time_share_numeric_semantics() -> None:
    kickoff_result = build_canonical_prematch_features(_context())
    decision_result = build_canonical_prematch_features(
        _context(decision_time="2025-01-10T10:00:00Z", matches=_matches("2025-01-06T00:00:00Z"))
    )

    assert decision_result["feature_as_of_status"] == DECISION_TIME_PROVEN
    assert kickoff_result["feature_names"] == decision_result["feature_names"]
    for name in kickoff_result["feature_names"]:
        assert kickoff_result["features"][name]["availability_status"] == "AVAILABLE"
        assert (
            kickoff_result["features"][name]["value"] == decision_result["features"][name]["value"]
        )

    assert kickoff_result["features"]["rolling_xg_home"]["value"] == pytest.approx(1.4)
    assert kickoff_result["features"]["rolling_xg_away"]["value"] == pytest.approx(1.04)
    assert kickoff_result["features"]["home_points"]["value"] == EXPECTED_HOME_POINTS
    assert kickoff_result["features"]["away_points"]["value"] == EXPECTED_AWAY_POINTS
    assert kickoff_result["features"]["points_diff"]["value"] == EXPECTED_POINTS_DIFF
    assert kickoff_result["features"]["home_recent_form_points"]["value"] == EXPECTED_HOME_POINTS
    assert kickoff_result["features"]["home_fatigue_index"]["value"] == pytest.approx(3 / 7)
    assert kickoff_result["features"]["away_fatigue_index"]["value"] == pytest.approx(3 / 7)
    assert kickoff_result["features"]["fatigue_diff"]["value"] == pytest.approx(0)


def test_history_gap_is_unavailable_without_imputation() -> None:
    matches = _matches()
    matches[0]["home_xg"] = None
    result = build_canonical_prematch_features(_context(matches=matches))

    for name in ("rolling_xg_home",):
        assert result["features"][name]["availability_status"] == "UNAVAILABLE"
        assert result["features"][name]["value"] is None
        assert "NO_PROVEN_SOURCE_FACT" in result["features"][name]["unavailable_reason_codes"]
    assert result["features"]["rolling_xg_away"]["availability_status"] == "AVAILABLE"
    assert result["features"]["home_points"]["value"] == EXPECTED_HOME_POINTS
    assert result["features"]["away_points"]["value"] == EXPECTED_AWAY_POINTS


def test_points_and_fatigue_require_history_closure() -> None:
    context = _context(matches=_matches()[:8], closure_matches=_matches())

    with pytest.raises(CanonicalPrematchFeatureError, match="HISTORY_CLOSURE_MISMATCH"):
        build_canonical_prematch_features(context)

    context = _context(matches=[])
    result = build_canonical_prematch_features(context)
    for name in (
        "home_points",
        "away_points",
        "points_diff",
        "home_fatigue_index",
        "away_fatigue_index",
        "fatigue_diff",
    ):
        assert result["features"][name]["availability_status"] == "UNAVAILABLE"
        assert result["features"][name]["value"] is None
        assert "HISTORY_CLOSURE_UNPROVEN" in result["features"][name]["unavailable_reason_codes"]

    del context["history_closure"]
    with pytest.raises(CanonicalPrematchFeatureError, match="INVALID_CONTEXT"):
        build_canonical_prematch_features(context)


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (
            lambda context: context["prior_matches"][0].update(kickoff_utc="2025-01-10T12:00:00Z"),
            "FUTURE_SOURCE_DEPENDENCY",
        ),
        (
            lambda context: context["prior_matches"][0].update(canonical_match_id="target-001"),
            "TARGET_MATCH_DEPENDENCY",
        ),
        (
            lambda context: context.update(feature_as_of_utc="2025-01-10T10:00:00Z"),
            "FEATURE_AS_OF_MISMATCH",
        ),
    ],
)
def test_temporal_and_target_boundaries_fail_closed(mutation, reason) -> None:
    context = _context()
    mutation(context)

    with pytest.raises(CanonicalPrematchFeatureError, match=reason):
        build_canonical_prematch_features(context)


def test_explicit_decision_mode_requires_availability_proof() -> None:
    with pytest.raises(CanonicalPrematchFeatureError, match="SOURCE_AVAILABLE_AFTER_DECISION"):
        build_canonical_prematch_features(_context(decision_time="2025-01-10T10:00:00Z"))


def test_mutating_one_source_fact_changes_runtime_value_and_provenance() -> None:
    baseline = build_canonical_prematch_features(_context())
    changed_context = deepcopy(_context())
    changed_context["prior_matches"][0]["home_xg"] = 9.0
    changed = build_canonical_prematch_features(changed_context)

    assert (
        changed["features"]["rolling_xg_home"]["value"]
        != baseline["features"]["rolling_xg_home"]["value"]
    )
    assert (
        changed["features"]["rolling_xg_home"]["provenance_digest"]
        != baseline["features"]["rolling_xg_home"]["provenance_digest"]
    )
