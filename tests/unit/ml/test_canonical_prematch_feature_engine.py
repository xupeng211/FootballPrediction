"""Typed-context parity and leakage tests for the canonical prematch engine."""

from copy import deepcopy
from hashlib import sha256
import json

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
    canonical_schedule = _canonical_schedule(closure_source)
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
            "canonical_schedule": canonical_schedule,
            "source_schedule_sha256": _schedule_hash(canonical_schedule),
        },
        "prior_matches": source_matches,
    }


def _canonical_schedule(matches):
    schedule = [
        {
            "canonical_match_id": match["canonical_match_id"],
            "kickoff_utc": match["kickoff_utc"],
            "competition": match["competition"],
            "season": match["season"],
            "home_team": match["home_team"],
            "away_team": match["away_team"],
        }
        for match in matches
    ]
    schedule.append(
        {
            "canonical_match_id": "target-001",
            "kickoff_utc": "2025-01-10T12:00:00Z",
            "competition": "Premier League",
            "season": "2024/2025",
            "home_team": "Alpha",
            "away_team": "Beta",
        }
    )
    return sorted(schedule, key=lambda match: (match["kickoff_utc"], match["canonical_match_id"]))


def _schedule_hash(schedule):
    encoded = json.dumps(schedule, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


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


def test_missing_outcome_preserves_context_and_propagates_only_result_dependencies() -> None:
    matches = _matches()
    matches[0]["outcome"] = None

    result = build_canonical_prematch_features(_context(matches=matches))

    assert result["features"]["rolling_xg_home"]["availability_status"] == "AVAILABLE"
    assert result["features"]["rolling_xg_away"]["availability_status"] == "AVAILABLE"
    assert result["features"]["home_fatigue_index"]["availability_status"] == "AVAILABLE"
    assert result["features"]["away_fatigue_index"]["availability_status"] == "AVAILABLE"
    assert result["features"]["away_points"]["availability_status"] == "AVAILABLE"

    for name in ("home_points", "points_diff", "home_recent_form_points"):
        line = result["features"][name]
        assert line["availability_status"] == "UNAVAILABLE"
        assert line["value"] is None
    assert result["features"]["home_points"]["unavailable_reason_codes"] == [
        "HISTORY_GAP",
        "STANDINGS_HISTORY_GAP",
    ]
    assert result["features"]["home_recent_form_points"]["unavailable_reason_codes"] == [
        "HISTORY_GAP",
    ]
    assert "a1" in result["features"]["home_points"]["source_match_ids"]


@pytest.mark.parametrize("field", ["home_xg", "away_xg"])
def test_negative_xg_is_rejected_by_runtime_semantics(field: str) -> None:
    context = _context()
    context["prior_matches"][0][field] = -0.1

    with pytest.raises(CanonicalPrematchFeatureError, match="must be non-negative"):
        build_canonical_prematch_features(context)


def test_zero_xg_is_valid_and_null_xg_remains_unavailable() -> None:
    zero_context = _context()
    zero_context["prior_matches"][0]["home_xg"] = 0
    zero_result = build_canonical_prematch_features(zero_context)
    assert zero_result["features"]["rolling_xg_home"]["availability_status"] == "AVAILABLE"

    null_context = _context()
    null_context["prior_matches"][0]["home_xg"] = None
    null_result = build_canonical_prematch_features(null_context)
    assert null_result["features"]["rolling_xg_home"]["availability_status"] == "UNAVAILABLE"


def test_points_and_fatigue_use_proven_cold_start_zero_when_history_is_empty() -> None:
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
        assert result["features"][name]["availability_status"] == "AVAILABLE"
        assert result["features"][name]["value"] == 0
        assert result["features"][name]["unavailable_reason_codes"] == []

    del context["history_closure"]
    with pytest.raises(CanonicalPrematchFeatureError, match="INVALID_CONTEXT"):
        build_canonical_prematch_features(context)


def test_history_closure_digest_is_bound_to_canonical_schedule() -> None:
    context = _context()
    context["history_closure"]["source_schedule_sha256"] = "0" * 64

    with pytest.raises(CanonicalPrematchFeatureError, match="HISTORY_CLOSURE_UNPROVEN"):
        build_canonical_prematch_features(context)

    context = _context(matches=_matches()[:-1])
    context["history_closure"]["canonical_schedule"] = _canonical_schedule(_matches())
    context["history_closure"]["source_schedule_sha256"] = _schedule_hash(
        context["history_closure"]["canonical_schedule"]
    )
    with pytest.raises(CanonicalPrematchFeatureError, match="HISTORY_CLOSURE_MISMATCH"):
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
