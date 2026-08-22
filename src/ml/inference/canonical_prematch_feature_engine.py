"""Pure canonical prematch feature semantics for typed runtime contexts.

lifecycle: permanent
component: Canonical / Internal (typed-context semantic engine; not a provider)

The engine deliberately accepts only already validated prior-state facts.  It
does not fetch, read a database, consult the wall clock, apply compatibility
defaults, or activate a model.  The V-next registry remains the only feature
name/order and training-decision authority.

The historical GD-A03 projection uses ``source_match_kickoff < target kickoff``
as a kickoff-reference boundary.  A real decision-time context is a stricter
mode: it must provide an explicit decision time and source availability times.
The two modes share the same numeric formulas but are never silently relabeled
as one another.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from src.ml.inference.feature_contract_registry import VNEXT_CONTRACT_ID, FeatureContractRegistry

FEATURE_CONTRACT_VERSION = "canonical_prematch/vnext/v1"
TRAINING_DECISION = "ACCEPTED_FOR_TRAINING"
KICKOFF_REFERENCE_ONLY = "KICKOFF_REFERENCE_ONLY"
DECISION_TIME_PROVEN = "DECISION_TIME_PROVEN"
FEATURE_CUTOFF_RELATION = "source_match_kickoff < feature_as_of_utc"
ROLLING_HISTORY_COUNT = 5
FATIGUE_LOOKBACK = timedelta(days=7)
HISTORY_CLOSURE_AUTHORITY = "canonical-schedule-history/v1"
HISTORY_CLOSURE_UNPROVEN = "HISTORY_CLOSURE_UNPROVEN"
SHA256_HEX_LENGTH = 64


class CanonicalPrematchFeatureError(ValueError):
    """Raised when typed prematch input cannot be evaluated fail-closed."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


def _fail(reason_code: str, message: str) -> None:
    raise CanonicalPrematchFeatureError(reason_code, message)


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        _fail("INVALID_TIMESTAMP", f"{label} must be a non-empty UTC timestamp")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        _fail("INVALID_TIMESTAMP", f"{label} is not ISO-8601")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail("INVALID_TIMESTAMP", f"{label} must include a UTC offset")
    return parsed.astimezone(UTC)


def _canonical_timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail("INVALID_TYPED_FACT", f"{label} must be non-empty text")
    return value.strip()


def _finite(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        _fail("INVALID_TYPED_FACT", f"{label} must be a finite number or null")
    return float(value)


def accepted_feature_names(registry_path: str | Path | None = None) -> tuple[str, ...]:
    """Return the accepted ordered V-next names from the canonical registry."""
    registry = FeatureContractRegistry(registry_path)
    contract = registry.get_by_contract_id(VNEXT_CONTRACT_ID)
    accepted = tuple(
        status.feature_name
        for status in contract.feature_statuses
        if status.training_decision == TRAINING_DECISION
    )
    if not accepted:
        _fail("CONTRACT_NOT_READY", "V-next registry has no accepted training features")
    return accepted


def _normalise_outcome(value: Any, label: str) -> str:
    normalized = _text(value, label).lower()
    aliases = {
        "h": "home",
        "home": "home",
        "d": "draw",
        "draw": "draw",
        "a": "away",
        "away": "away",
    }
    if normalized not in aliases:
        _fail("INVALID_TYPED_FACT", f"{label} must be home/draw/away")
    return aliases[normalized]


def _validate_context(  # noqa: C901, PLR0912, PLR0915
    context: Any,
) -> tuple[dict[str, Any], datetime, datetime, str, list[dict[str, Any]]]:
    if not isinstance(context, dict):
        _fail("INVALID_CONTEXT", "runtime context must be an object")
    required = {
        "canonical_match_id",
        "home_team",
        "away_team",
        "competition",
        "season",
        "target_kickoff_utc",
        "feature_as_of_utc",
        "model_decision_time_utc",
        "history_closure",
        "prior_matches",
    }
    if set(context) != required:
        _fail("INVALID_CONTEXT", "runtime context fields are not the canonical typed-context set")

    target_id = _text(context["canonical_match_id"], "canonical_match_id")
    home_team = _text(context["home_team"], "home_team")
    away_team = _text(context["away_team"], "away_team")
    competition = _text(context["competition"], "competition")
    season = _text(context["season"], "season")
    if home_team == away_team:
        _fail("INVALID_CONTEXT", "home_team and away_team must be distinct")
    target = _parse_utc(context["target_kickoff_utc"], "target_kickoff_utc")
    as_of = _parse_utc(context["feature_as_of_utc"], "feature_as_of_utc")
    decision_raw = context["model_decision_time_utc"]
    decision = None if decision_raw is None else _parse_utc(decision_raw, "model_decision_time_utc")
    if decision is None:
        if as_of != target:
            _fail(
                "FEATURE_AS_OF_MISMATCH",
                "kickoff-reference mode requires feature_as_of_utc == target_kickoff_utc",
            )
        mode = KICKOFF_REFERENCE_ONLY
    else:
        if decision >= target:
            _fail(
                "DECISION_TIME_NOT_PREMATCH", "model_decision_time_utc must precede target kickoff"
            )
        if as_of != decision:
            _fail(
                "FEATURE_AS_OF_MISMATCH",
                "feature_as_of_utc must equal model_decision_time_utc in decision-time mode",
            )
        mode = DECISION_TIME_PROVEN

    raw_matches = context["prior_matches"]
    if not isinstance(raw_matches, list):
        _fail("INVALID_CONTEXT", "prior_matches must be a list")
    closure = context["history_closure"]
    if not isinstance(closure, dict):
        _fail("HISTORY_CLOSURE_UNPROVEN", "history_closure must be an object")
    expected_closure_fields = {
        "status",
        "authority",
        "competition",
        "season",
        "team_names",
        "prior_match_ids",
        "source_schedule_sha256",
    }
    if set(closure) != expected_closure_fields:
        _fail("HISTORY_CLOSURE_UNPROVEN", "history_closure fields are not canonical")
    if (
        closure["status"] != "PROVEN"
        or closure["authority"] != HISTORY_CLOSURE_AUTHORITY
        or closure["competition"] != competition
        or closure["season"] != season
        or closure["team_names"] != sorted([home_team, away_team])
    ):
        _fail("HISTORY_CLOSURE_UNPROVEN", "history_closure does not bind target identity")
    if not isinstance(closure["prior_match_ids"], list) or any(
        not isinstance(match_id, str) or not match_id.strip()
        for match_id in closure["prior_match_ids"]
    ):
        _fail("HISTORY_CLOSURE_UNPROVEN", "history_closure prior IDs are invalid")
    source_schedule_sha256 = closure["source_schedule_sha256"]
    if (
        not isinstance(source_schedule_sha256, str)
        or len(source_schedule_sha256) != SHA256_HEX_LENGTH
        or any(character not in "0123456789abcdef" for character in source_schedule_sha256)
    ):
        _fail("HISTORY_CLOSURE_UNPROVEN", "history_closure source schedule binding is invalid")
    matches: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_match in enumerate(raw_matches):
        if not isinstance(raw_match, dict):
            _fail("INVALID_TYPED_FACT", f"prior_matches[{index}] must be an object")
        expected_fields = {
            "canonical_match_id",
            "kickoff_utc",
            "competition",
            "season",
            "home_team",
            "away_team",
            "home_xg",
            "away_xg",
            "outcome",
            "available_at_utc",
        }
        if set(raw_match) != expected_fields:
            _fail("INVALID_TYPED_FACT", f"prior_matches[{index}] fields are not canonical")
        match_id = _text(
            raw_match["canonical_match_id"], f"prior_matches[{index}].canonical_match_id"
        )
        if match_id in seen_ids:
            _fail("DUPLICATE_SOURCE_ID", f"prior match {match_id} is duplicated")
        if match_id == target_id:
            _fail("TARGET_MATCH_DEPENDENCY", "target match cannot be a prior source")
        seen_ids.add(match_id)
        kickoff = _parse_utc(raw_match["kickoff_utc"], f"prior_matches[{index}].kickoff_utc")
        if kickoff >= as_of:
            _fail(
                "FUTURE_SOURCE_DEPENDENCY",
                f"prior match {match_id} is not strictly before feature_as_of_utc",
            )
        source_home = _text(raw_match["home_team"], f"prior_matches[{index}].home_team")
        source_away = _text(raw_match["away_team"], f"prior_matches[{index}].away_team")
        source_competition = _text(raw_match["competition"], f"prior_matches[{index}].competition")
        source_season = _text(raw_match["season"], f"prior_matches[{index}].season")
        if source_competition != competition or source_season != season:
            _fail(
                "SOURCE_IDENTITY_UNBOUND",
                f"prior match {match_id} is outside target competition/season",
            )
        if source_home == source_away or (
            source_home not in {home_team, away_team} and source_away not in {home_team, away_team}
        ):
            _fail(
                "SOURCE_IDENTITY_UNBOUND", f"prior match {match_id} is not bound to a target team"
            )
        available_raw = raw_match["available_at_utc"]
        available = (
            None
            if available_raw is None
            else _parse_utc(available_raw, f"prior_matches[{index}].available_at_utc")
        )
        if mode == DECISION_TIME_PROVEN and (available is None or available > as_of):
            _fail(
                "SOURCE_AVAILABLE_AFTER_DECISION",
                f"prior match {match_id} lacks proof of availability by decision time",
            )
        matches.append(
            {
                "canonical_match_id": match_id,
                "kickoff": kickoff,
                "kickoff_utc": _canonical_timestamp(kickoff),
                "competition": source_competition,
                "season": source_season,
                "home_team": source_home,
                "away_team": source_away,
                "home_xg": _finite(raw_match["home_xg"], f"prior_matches[{index}].home_xg"),
                "away_xg": _finite(raw_match["away_xg"], f"prior_matches[{index}].away_xg"),
                "outcome": _normalise_outcome(
                    raw_match["outcome"], f"prior_matches[{index}].outcome"
                ),
                "available_at_utc": None if available is None else _canonical_timestamp(available),
            }
        )
    if sorted(closure["prior_match_ids"]) != sorted(seen_ids):
        _fail(
            "HISTORY_CLOSURE_MISMATCH",
            "history_closure does not account for every typed prior match",
        )
    matches.sort(key=lambda match: (match["kickoff"], match["canonical_match_id"]))
    return (
        {
            "canonical_match_id": target_id,
            "home_team": home_team,
            "away_team": away_team,
            "competition": competition,
            "season": season,
        },
        target,
        as_of,
        mode,
        matches,
    )


def _team_matches(matches: list[dict[str, Any]], team: str) -> list[dict[str, Any]]:
    return [match for match in matches if team in (match["home_team"], match["away_team"])]


def _points(match: dict[str, Any], team: str) -> int:
    if match["outcome"] == "draw":
        return 1
    home_won = match["outcome"] == "home"
    team_won = (home_won and match["home_team"] == team) or (
        not home_won and match["away_team"] == team
    )
    return 3 if team_won else 0


def _identity(match: dict[str, Any]) -> dict[str, str]:
    return {
        "canonical_match_id": match["canonical_match_id"],
        "home_team": match["home_team"],
        "away_team": match["away_team"],
        "kickoff_utc": match["kickoff_utc"],
    }


def _line(
    *,
    feature_name: str,
    value: float | int | None,
    source_matches: list[dict[str, Any]],
    as_of: datetime,
    reason_codes: list[str],
    derivation_contract: str,
    source_fields: list[str],
) -> dict[str, Any]:
    source_ids = [match["canonical_match_id"] for match in source_matches]
    source_identities = [_identity(match) for match in source_matches]
    latest = max((match["kickoff"] for match in source_matches), default=None)
    latest_text = None if latest is None else _canonical_timestamp(latest)
    availability = "AVAILABLE" if value is not None and not reason_codes else "UNAVAILABLE"
    output_value: float | int | None = value if availability == "AVAILABLE" else None
    provenance = {
        "engine": "canonical-prematch-feature-engine/v1",
        "feature_name": feature_name,
        "target_cutoff": _canonical_timestamp(as_of),
        "source_match_ids": source_ids,
        "source_fields": source_fields,
        "value": output_value,
        "availability_status": availability,
        "unavailable_reason_codes": reason_codes,
    }
    return {
        "availability_status": availability,
        "value": output_value,
        "cutoff_proof": {
            "max_source_time": latest_text,
            "passed": True,
            "relation": FEATURE_CUTOFF_RELATION,
            "source_time_basis": "MATCH_KICKOFF",
            "target_cutoff": _canonical_timestamp(as_of),
        },
        "derivation_contract": derivation_contract,
        "latest_source_kickoff": latest_text,
        "provenance_digest": _digest(provenance),
        "source_match_ids": source_ids,
        "source_identities": source_identities,
        "source_fields": source_fields,
        "unavailable_reason_codes": reason_codes,
    }


def _rolling_xg(
    feature_name: str,
    team: str,
    matches: list[dict[str, Any]],
    as_of: datetime,
) -> dict[str, Any]:
    prior = _team_matches(matches, team)
    selected = prior[-ROLLING_HISTORY_COUNT:]
    # The side is evaluated independently for every source match; a team may
    # alternate home and away and must never use a fixed target side.
    values = [
        match["home_xg"] if match["home_team"] == team else match["away_xg"] for match in selected
    ]
    reason_codes: list[str] = []
    if len(selected) < ROLLING_HISTORY_COUNT:
        reason_codes.append("INSUFFICIENT_HISTORY")
    if any(value is None for value in values):
        reason_codes.extend(["HISTORY_GAP", "NO_PROVEN_SOURCE_FACT"])
    value = None if reason_codes else sum(values) / ROLLING_HISTORY_COUNT
    return _line(
        feature_name=feature_name,
        value=value,
        source_matches=selected,
        as_of=as_of,
        reason_codes=reason_codes,
        derivation_contract="canonical-prematch/vnext/v1:mean_exact_previous_5_complete_team_xg",
        source_fields=["typed_prior_match.home_xg/away_xg by team identity"],
    )


def _points_line(
    feature_name: str,
    team: str,
    matches: list[dict[str, Any]],
    as_of: datetime,
) -> dict[str, Any]:
    prior = _team_matches(matches, team)
    reason_codes = [] if prior else [HISTORY_CLOSURE_UNPROVEN]
    value = sum(_points(match, team) for match in prior) if prior else None
    return _line(
        feature_name=feature_name,
        value=value,
        source_matches=prior,
        as_of=as_of,
        reason_codes=reason_codes,
        derivation_contract="canonical-prematch/vnext/v1:sum_prior_result_points_3_1_0",
        source_fields=["typed_prior_match.outcome"],
    )


def _form_line(team: str, matches: list[dict[str, Any]], as_of: datetime) -> dict[str, Any]:
    prior = _team_matches(matches, team)
    selected = prior[-ROLLING_HISTORY_COUNT:]
    reason_codes = [] if len(selected) == ROLLING_HISTORY_COUNT else ["INSUFFICIENT_HISTORY"]
    value = None if reason_codes else sum(_points(match, team) for match in selected)
    return _line(
        feature_name="home_recent_form_points",
        value=value,
        source_matches=selected,
        as_of=as_of,
        reason_codes=reason_codes,
        derivation_contract="canonical-prematch/vnext/v1:sum_exact_previous_5_result_points_3_1_0",
        source_fields=["typed_prior_match.outcome"],
    )


def _fatigue_line(
    feature_name: str,
    team: str,
    matches: list[dict[str, Any]],
    as_of: datetime,
) -> dict[str, Any]:
    start = as_of - FATIGUE_LOOKBACK
    selected = [
        match for match in _team_matches(matches, team) if start <= match["kickoff"] < as_of
    ]
    reason_codes = [] if matches else [HISTORY_CLOSURE_UNPROVEN]
    value = min(1.0, len(selected) / 7.0) if matches else None
    return _line(
        feature_name=feature_name,
        value=value,
        source_matches=selected,
        as_of=as_of,
        reason_codes=reason_codes,
        derivation_contract="canonical-prematch/vnext/v1:capped_prior_7_day_scheduled_match_count_divided_by_7",
        source_fields=["typed_prior_match.kickoff_utc", "typed_prior_match.team_identity"],
    )


def _merge_source_matches(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Union source matches in deterministic kickoff/identity order."""
    by_id = {match["canonical_match_id"]: match for group in groups for match in group}
    return sorted(by_id.values(), key=lambda match: (match["kickoff"], match["canonical_match_id"]))


def _difference_line(
    feature_name: str,
    left: dict[str, Any],
    right: dict[str, Any],
    source_matches: list[dict[str, Any]],
    as_of: datetime,
    derivation_contract: str,
    source_fields: list[str],
) -> dict[str, Any]:
    reasons = sorted(set(left["unavailable_reason_codes"] + right["unavailable_reason_codes"]))
    if left["value"] is None or right["value"] is None:
        reasons.append("DEPENDENCY_UNAVAILABLE")
        return _line(
            feature_name=feature_name,
            value=None,
            source_matches=source_matches,
            as_of=as_of,
            reason_codes=sorted(set(reasons)),
            derivation_contract=derivation_contract,
            source_fields=source_fields,
        )
    return _line(
        feature_name=feature_name,
        value=left["value"] - right["value"],
        source_matches=source_matches,
        as_of=as_of,
        reason_codes=reasons,
        derivation_contract=derivation_contract,
        source_fields=source_fields,
    )


def build_canonical_prematch_features(  # noqa: C901
    context: dict[str, Any],
    *,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate accepted V-next features from one explicit typed context."""
    target, target_kickoff, as_of, mode, matches = _validate_context(context)
    names = accepted_feature_names(registry_path)
    home = target["home_team"]
    away = target["away_team"]
    lines: dict[str, dict[str, Any]] = {}
    for feature_name in names:
        if feature_name == "rolling_xg_home":
            lines[feature_name] = _rolling_xg(feature_name, home, matches, as_of)
        elif feature_name == "rolling_xg_away":
            lines[feature_name] = _rolling_xg(feature_name, away, matches, as_of)
        elif feature_name == "home_points":
            lines[feature_name] = _points_line(feature_name, home, matches, as_of)
        elif feature_name == "away_points":
            lines[feature_name] = _points_line(feature_name, away, matches, as_of)
        elif feature_name == "points_diff":
            home_line = _points_line("home_points", home, matches, as_of)
            away_line = _points_line("away_points", away, matches, as_of)
            lines[feature_name] = _difference_line(
                feature_name,
                home_line,
                away_line,
                _merge_source_matches(_team_matches(matches, home), _team_matches(matches, away)),
                as_of=as_of,
                derivation_contract="canonical-prematch/vnext/v1:home_points_minus_away_points",
                source_fields=[
                    "canonical-prematch/vnext/v1:home_points",
                    "canonical-prematch/vnext/v1:away_points",
                ],
            )
        elif feature_name == "home_recent_form_points":
            lines[feature_name] = _form_line(home, matches, as_of)
        elif feature_name == "home_fatigue_index":
            lines[feature_name] = _fatigue_line(feature_name, home, matches, as_of)
        elif feature_name == "away_fatigue_index":
            lines[feature_name] = _fatigue_line(feature_name, away, matches, as_of)
        elif feature_name == "fatigue_diff":
            home_line = _fatigue_line("home_fatigue_index", home, matches, as_of)
            away_line = _fatigue_line("away_fatigue_index", away, matches, as_of)
            lines[feature_name] = _difference_line(
                feature_name,
                home_line,
                away_line,
                _merge_source_matches(_team_matches(matches, home), _team_matches(matches, away)),
                as_of=as_of,
                derivation_contract="canonical-prematch/vnext/v1:home_fatigue_minus_away_fatigue",
                source_fields=[
                    "canonical-prematch/vnext/v1:home_fatigue_index",
                    "canonical-prematch/vnext/v1:away_fatigue_index",
                ],
            )
        else:
            _fail(
                "UNSUPPORTED_ACCEPTED_FEATURE",
                f"registry accepted unsupported feature {feature_name}",
            )
    return {
        "canonical_match_id": target["canonical_match_id"],
        "home_team": home,
        "away_team": away,
        "competition": target["competition"],
        "season": target["season"],
        "target_kickoff_utc": _canonical_timestamp(target_kickoff),
        "feature_as_of_utc": _canonical_timestamp(as_of),
        "feature_as_of_status": mode,
        "model_decision_time_utc": None
        if mode == KICKOFF_REFERENCE_ONLY
        else _canonical_timestamp(as_of),
        "feature_contract_id": VNEXT_CONTRACT_ID,
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "history_closure": {
            "status": "PROVEN",
            "authority": HISTORY_CLOSURE_AUTHORITY,
            "competition": target["competition"],
            "season": target["season"],
            "team_names": sorted([home, away]),
            "prior_match_ids": [match["canonical_match_id"] for match in matches],
            "source_schedule_sha256": context["history_closure"]["source_schedule_sha256"],
        },
        "feature_names": list(names),
        "features": lines,
        "feature_vector": [lines[name]["value"] for name in names],
        "semantic_parity_binding": {
            "historical_producer": "GD-A03 prior-state feature lines under kickoff-exclusive policy",
            "runtime_producer": "src/ml/inference/canonical_prematch_feature_engine.py",
            "point_in_time_policy": FEATURE_CUTOFF_RELATION,
            "decision_time_status": mode,
        },
    }


__all__ = [
    "CANONICAL_PREMATCH_FEATURE_ENGINE",
    "DECISION_TIME_PROVEN",
    "FEATURE_CONTRACT_VERSION",
    "KICKOFF_REFERENCE_ONLY",
    "CanonicalPrematchFeatureError",
    "accepted_feature_names",
    "build_canonical_prematch_features",
]

CANONICAL_PREMATCH_FEATURE_ENGINE = "canonical-prematch-feature-engine/v1"
