"""Protocol contract loading, validation and hashing for VALUE_MVP-1.

The protocol is a machine-readable research-integrity contract frozen BEFORE
any real out-of-sample evaluation (config/value_mvp_1_evaluation_protocol.json).
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


CLASS_LABELS: tuple[str, ...] = ("home", "draw", "away")

FEATURE_NAMES: tuple[str, ...] = (
    "home_elo_pre",
    "away_elo_pre",
    "elo_diff",
    "home_last5_ppg",
    "away_last5_ppg",
    "home_last5_goals_for",
    "away_last5_goals_for",
    "home_last5_goals_against",
    "away_last5_goals_against",
    "home_last5_home_ppg",
    "away_last5_away_ppg",
    "home_matches_seen",
    "away_matches_seen",
)

FORBIDDEN_FEATURE_KEYWORDS: tuple[str, ...] = (
    "odds",
    "market",
    "closing",
    "close",
    "first_collection",
    "result",
    "ftr",
    "fthg",
    "ftag",
    "score",
    "shots",
    "corners",
    "cards",
    "postmatch",
)

PROTOCOL_SCHEMA: str = "value-mvp-1-evaluation-protocol/v1"

_SEASON_RULE_START_MONTH = 8

_REQUIRED_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "schema_version",
    "task",
    "claim_boundary",
    "population_policy",
    "season_assignment_rule",
    "season_split_policy",
    "feature_contract",
    "elo_contract",
    "rolling_window",
    "model_family",
    "model_hyperparameters",
    "imputer_policy",
    "scaler_policy",
    "market_no_vig_method",
    "market_consensus_method",
    "minimum_bookmaker_count",
    "primary_metric",
    "secondary_metrics",
    "statistical_inference_method",
    "bootstrap",
    "claim_classification",
    "forbidden_features",
    "forbidden_claims",
)


def load_protocol(path: Path) -> dict:
    """Load and structurally validate the protocol contract from a JSON file."""
    with path.open("r", encoding="utf-8") as handle:
        protocol = json.load(handle)
    validate_protocol(protocol)
    return protocol


def validate_protocol(protocol: dict) -> None:
    """Raise ValueError when the protocol is missing required fields."""
    for key in _REQUIRED_TOP_LEVEL_KEYS:
        if key not in protocol:
            raise ValueError(f"protocol missing required key: {key}")
    if protocol.get("schema_version") != PROTOCOL_SCHEMA:
        raise ValueError(f"protocol schema_version mismatch: {protocol.get('schema_version')}")
    features = protocol.get("feature_contract", {}).get("features", [])
    if tuple(features) != FEATURE_NAMES:
        raise ValueError(f"feature_contract mismatch: {features}")
    split = protocol.get("season_split_policy", {})
    for fold in ("fold1", "fold2"):
        if not isinstance(split.get(fold), dict):
            raise TypeError(f"season_split_policy missing fold: {fold}")
    if protocol.get("primary_metric") != "multiclass_log_loss":
        raise ValueError("primary metric must be multiclass_log_loss (pre-registered)")


def _canonical_json(obj: dict) -> str:
    """Canonical JSON serialization: sorted keys, no whitespace, ascii."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def protocol_sha256(protocol: dict) -> str:
    """Deterministic SHA256 of the protocol's canonical JSON (no wall-clock)."""
    return hashlib.sha256(_canonical_json(protocol).encode("utf-8")).hexdigest()


def feature_contract_violations(protocol: dict) -> list[str]:
    """Return feature-contract violations (forbidden keyword hits)."""
    violations: list[str] = []
    features = protocol.get("feature_contract", {}).get("features", [])
    forbidden = [item.lower() for item in protocol.get("forbidden_features", [])]
    violations.extend(
        f"{feature} contains forbidden keyword {keyword}"
        for feature in features
        for keyword in forbidden
        if keyword in feature.lower()
    )
    return violations


_SEASON_RULE_PREFIX = "kickoff_at month >= 8 -> YYYY/YYYY+1 else (YYYY-1)/YYYY"


def season_of_kickoff(kickoff_at: str, rule: str) -> str:
    """Assign season from an ISO kickoff string using the protocol rule."""
    year = int(kickoff_at[:4])
    month = int(kickoff_at[5:7])
    if rule.startswith(_SEASON_RULE_PREFIX):
        start = year if month >= _SEASON_RULE_START_MONTH else year - 1
    else:
        raise ValueError(f"unrecognized season rule: {rule}")
    return f"{start}/{str(start + 1)[-2:]}"
