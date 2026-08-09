"""Protocol contract tests: loading, validation, hashing, season rule."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from src.ml.value_mvp.protocol import (
    FEATURE_NAMES,
    PROTOCOL_SCHEMA,
    feature_contract_violations,
    load_protocol,
    protocol_sha256,
    season_of_kickoff,
    validate_protocol,
)
from tests.unit.ml.value_mvp._helpers import synthetic_protocol

REPO_ROOT = Path(__file__).resolve().parents[4]
FROZEN_PROTOCOL_PATH = REPO_ROOT / "config" / "value_mvp_1_evaluation_protocol.json"


def test_frozen_protocol_contract_loads_and_validates():
    """The checked-in protocol contract must load and validate."""
    protocol = load_protocol(FROZEN_PROTOCOL_PATH)
    assert protocol["schema_version"] == PROTOCOL_SCHEMA
    assert protocol["task"] == "VALUE_MVP_1_BASELINE_VS_CLOSING_MARKET"
    assert protocol["primary_metric"] == "multiclass_log_loss"
    assert protocol["feature_contract"]["feature_count"] == 13


def test_frozen_protocol_contains_expected_population_gate():
    """The pre-registered data-gate constants must be present."""
    protocol = load_protocol(FROZEN_PROTOCOL_PATH)
    expected = protocol["population_policy"]["expected_population"]
    assert expected["total"] == 888
    assert expected["per_season"] == {"2022/23": 377, "2023/24": 379, "2024/25": 132}


def test_validate_protocol_rejects_missing_key():
    protocol = synthetic_protocol()
    del protocol["minimum_bookmaker_count"]
    with pytest.raises(ValueError, match="minimum_bookmaker_count"):
        validate_protocol(protocol)


def test_validate_protocol_rejects_feature_mismatch():
    protocol = synthetic_protocol()
    protocol["feature_contract"]["features"] = list(FEATURE_NAMES[:-1])
    with pytest.raises(ValueError, match="feature_contract"):
        validate_protocol(protocol)


def test_validate_protocol_rejects_primary_metric_change():
    protocol = synthetic_protocol()
    protocol["primary_metric"] = "accuracy"
    with pytest.raises(ValueError, match="primary metric"):
        validate_protocol(protocol)


def test_protocol_sha256_deterministic_and_key_order_invariant():
    protocol = synthetic_protocol()
    first = protocol_sha256(protocol)
    reordered = json_reorder(deepcopy(protocol))
    assert protocol_sha256(reordered) == first
    altered = deepcopy(protocol)
    altered["minimum_bookmaker_count"] = 3
    assert protocol_sha256(altered) != first


def test_feature_contract_violations_detect_forbidden_keyword():
    protocol = synthetic_protocol()
    assert feature_contract_violations(protocol) == []
    protocol["feature_contract"]["features"] = ["home_odds_x"]
    violations = feature_contract_violations(protocol)
    assert len(violations) == 1
    assert "odds" in violations[0]


@pytest.mark.parametrize(
    ("kickoff", "expected"),
    [
        ("2022-08-05T19:00:00+01:00", "2022/23"),
        ("2023-01-15T15:00:00+00:00", "2022/23"),
        ("2023-08-06T14:00:00+01:00", "2023/24"),
        ("2024-05-19T16:00:00+01:00", "2023/24"),
    ],
)
def test_season_of_kickoff_rule(kickoff, expected):
    rule = "kickoff_at month >= 8 -> YYYY/YYYY+1 else (YYYY-1)/YYYY"
    assert season_of_kickoff(kickoff, rule) == expected


def test_season_of_kickoff_rejects_unknown_rule():
    with pytest.raises(ValueError, match="unrecognized season rule"):
        season_of_kickoff("2023-08-05T14:00:00+01:00", "bogus")


def json_reorder(obj):
    """Recursively reorder dict keys to verify canonical serialization."""
    if isinstance(obj, dict):
        return {key: json_reorder(value) for key, value in sorted(obj.items(), reverse=True)}
    if isinstance(obj, list):
        return [json_reorder(value) for value in obj]
    return obj
