"""Fail-closed validation for versioned canonical feature-contract boundaries.

lifecycle: permanent
component: Specialized / Internal (registry validation helper; not a feature authority)

The git-tracked JSON registry remains the semantic authority. This module only
enforces the frozen shape and values before a consumer can bind to it.
"""

from typing import Any

_RAW_ELO_PARAMETER_COUNT = 11
_SOT_NEXT_SCOPE_COUNT = 5


def validate_v2_decision_boundaries(  # noqa: C901, PLR0912, PLR0915
    payload: dict[str, Any], error_type: type[ValueError]
) -> None:
    """Reject drift in the frozen decision-boundary values."""
    boundaries = payload.get("decision_boundaries")
    if not isinstance(boundaries, dict):
        raise error_type("feature contract decision boundaries malformed")
    required_boundary_names = {
        "raw_elo",
        "standings",
        "sot",
        "possession",
        "shared_engine",
        "activation",
        "legacy_proxy_policy",
    }
    if set(boundaries) != required_boundary_names:
        raise error_type("feature contract decision boundaries incomplete")

    def exact_object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) != fields:
            raise error_type(f"{label} malformed")
        return value

    def text(value: Any, label: str, expected: str | None = None) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
            or (expected is not None and value != expected)
        ):
            raise error_type(f"{label} malformed")
        return value

    def text_fields(value: dict[str, Any], fields: set[str], label: str) -> None:
        for field in fields:
            text(value[field], f"{label}.{field}")

    raw_elo = exact_object(
        boundaries["raw_elo"],
        {
            "direction",
            "retained_in_v_next",
            "semantic_status",
            "training_eligible",
            "runtime_eligible",
            "parameter_sheet",
        },
        "raw ELO decision boundary",
    )
    for field, expected in {
        "direction": "BOUNDED_START",
        "retained_in_v_next": "YES",
        "semantic_status": "OWNER_PARAMETER_DECISION_REQUIRED",
        "training_eligible": "NO",
        "runtime_eligible": "NO",
    }.items():
        text(raw_elo[field], f"raw ELO decision boundary.{field}", expected)
    parameter_sheet = raw_elo["parameter_sheet"]
    if not isinstance(parameter_sheet, list) or len(parameter_sheet) != _RAW_ELO_PARAMETER_COUNT:
        raise error_type("raw ELO parameter sheet malformed")
    for index, entry in enumerate(parameter_sheet, start=1):
        parameter = exact_object(
            entry,
            {"id", "parameter", "candidate_contract", "owner_decision_required"},
            f"raw ELO parameter E{index}",
        )
        text(parameter["id"], f"raw ELO parameter E{index}.id", f"E{index}")
        text_fields(
            parameter,
            {"parameter", "candidate_contract", "owner_decision_required"},
            f"raw ELO parameter E{index}",
        )
        text(
            parameter["owner_decision_required"],
            f"raw ELO parameter E{index}.owner_decision_required",
            "YES",
        )

    standings = exact_object(
        boundaries["standings"],
        {
            "retained_in_v_next",
            "semantic_direction",
            "cutoff",
            "same_kickoff_fixtures",
            "training_eligible",
            "runtime_eligible",
            "rule_history_closure_required",
            "unresolved_evidence",
        },
        "standings decision boundary",
    )
    for field, expected in {
        "retained_in_v_next": "YES",
        "semantic_direction": "OFFICIAL_POINT_IN_TIME_STANDINGS",
        "cutoff": "source_kickoff < target_kickoff",
        "same_kickoff_fixtures": "EXCLUDED",
        "training_eligible": "NO",
        "runtime_eligible": "NO",
        "rule_history_closure_required": "YES",
    }.items():
        text(standings[field], f"standings decision boundary.{field}", expected)
    if (
        not isinstance(standings["unresolved_evidence"], list)
        or not standings["unresolved_evidence"]
        or any(
            not isinstance(item, str) or not item.strip()
            for item in standings["unresolved_evidence"]
        )
    ):
        raise error_type("standings unresolved evidence malformed")

    sot = exact_object(
        boundaries["sot"],
        {
            "retained_in_v_next",
            "inventory_mode",
            "existing_source_repair_feasible",
            "new_acquisition_required",
            "training_eligible",
            "runtime_eligible",
            "evidence",
            "evidence_provenance",
            "bounded_next_scope",
        },
        "SOT decision boundary",
    )
    for field, expected in {
        "retained_in_v_next": "YES",
        "inventory_mode": "READ_ONLY_EXISTING_FROZEN_SOURCES",
        "existing_source_repair_feasible": "NO",
        "new_acquisition_required": "YES",
        "training_eligible": "NO",
        "runtime_eligible": "NO",
    }.items():
        text(sot[field], f"SOT decision boundary.{field}", expected)
    evidence = exact_object(
        sot["evidence"],
        {
            "formal_payloads",
            "shotmap_payloads",
            "payloads_with_is_on_target",
            "payloads_with_is_own_goal",
            "payloads_with_own_goal_true",
            "normalized_team_identity_pairs",
            "independent_observed_home_away_team_pairs",
            "blocker",
        },
        "SOT evidence",
    )
    expected_counts = {
        "formal_payloads": 812,
        "shotmap_payloads": 812,
        "payloads_with_is_on_target": 812,
        "payloads_with_is_own_goal": 812,
        "payloads_with_own_goal_true": 90,
        "normalized_team_identity_pairs": 812,
        "independent_observed_home_away_team_pairs": 0,
    }
    for field, expected_count in expected_counts.items():
        if (
            evidence[field] != expected_count
            or isinstance(evidence[field], bool)
            or not isinstance(evidence[field], int)
        ):
            raise error_type(f"SOT evidence.{field} malformed")
    text(
        evidence["blocker"],
        "SOT evidence.blocker",
        "Frozen captures do not prove independent home/away shot-team binding.",
    )
    provenance = exact_object(
        sot["evidence_provenance"],
        {"authority", "memo_sha256", "inventory_scope", "reproducibility"},
        "SOT evidence provenance",
    )
    text(
        provenance["authority"],
        "SOT evidence provenance.authority",
        "OSD-V1 final decision memo",
    )
    text(
        provenance["memo_sha256"],
        "SOT evidence provenance.memo_sha256",
        "21eab8eedb31688488850d47833b2f86a2b765abadc49562050a81ebeaf78e2f",
    )
    text_fields(
        provenance,
        {"inventory_scope", "reproducibility"},
        "SOT evidence provenance",
    )
    if (
        not isinstance(sot["bounded_next_scope"], list)
        or len(sot["bounded_next_scope"]) != _SOT_NEXT_SCOPE_COUNT
        or any(not isinstance(item, str) or not item.strip() for item in sot["bounded_next_scope"])
    ):
        raise error_type("SOT bounded next scope malformed")

    possession = exact_object(
        boundaries["possession"],
        {
            "retained_in_v_next",
            "historical_source_status",
            "runtime_source_status",
            "training_eligible",
            "runtime_eligible",
            "fallbacks_forbidden",
        },
        "possession decision boundary",
    )
    for field, expected in {
        "retained_in_v_next": "YES",
        "historical_source_status": "UNAVAILABLE",
        "runtime_source_status": "UNAVAILABLE",
        "training_eligible": "NO",
        "runtime_eligible": "NO",
    }.items():
        text(possession[field], f"possession decision boundary.{field}", expected)
    if possession["fallbacks_forbidden"] != [
        "50/50",
        "55/45",
        "team average",
        "league average",
        "forward fill",
        "interpolation",
        "estimated possession",
    ]:
        raise error_type("possession forbidden fallback policy malformed")

    shared_engine = exact_object(
        boundaries["shared_engine"],
        {
            "architecture_approved",
            "implementation_started",
            "canonical_semantic_engine",
            "historical_source_adapter",
            "runtime_source_adapter",
        },
        "shared semantic engine boundary",
    )
    text(
        shared_engine["architecture_approved"],
        "shared semantic engine architecture_approved",
        "YES",
    )
    text(
        shared_engine["implementation_started"],
        "shared semantic engine implementation_started",
        "NO",
    )
    canonical_engine = exact_object(
        shared_engine["canonical_semantic_engine"],
        {"input", "output", "prohibitions"},
        "canonical semantic engine boundary",
    )
    text_fields(canonical_engine, {"input", "output"}, "canonical semantic engine boundary")
    if canonical_engine["prohibitions"] != [
        "network fetch",
        "provider query",
        "database query",
        "database write",
        "historical/runtime path branching",
        "compatibility proxy defaults",
        "silent unavailable-field defaults",
    ]:
        raise error_type("canonical semantic engine prohibitions malformed")
    text_fields(
        shared_engine,
        {"historical_source_adapter", "runtime_source_adapter"},
        "shared semantic engine boundary",
    )

    activation = exact_object(
        boundaries["activation"],
        {
            "v_next_defined",
            "v_next_default_activated",
            "training_default_switched",
            "runtime_default_switched",
            "model_schema_switched",
            "feature_frame_readiness",
            "real_training_readiness",
            "train_inference_numeric_parity",
            "golden_dataset_complete",
        },
        "activation boundary",
    )
    for field, expected in {
        "v_next_defined": "YES",
        "v_next_default_activated": "NO",
        "training_default_switched": "NO",
        "runtime_default_switched": "NO",
        "model_schema_switched": "NO",
        "feature_frame_readiness": "NOT_READY",
        "real_training_readiness": "NOT_READY",
        "train_inference_numeric_parity": "NOT_PROVEN",
        "golden_dataset_complete": "NO",
    }.items():
        text(activation[field], f"activation boundary.{field}", expected)

    legacy = exact_object(
        boundaries["legacy_proxy_policy"],
        {"canonical_v_next_reachability", "proxies_rejected", "compatibility_behavior"},
        "legacy proxy policy",
    )
    text(
        legacy["canonical_v_next_reachability"],
        "legacy proxy policy.canonical_v_next_reachability",
        "NO",
    )
    if legacy["proxies_rejected"] != [
        "goals proxy for xG",
        "goals*3+2 SOT",
        "55/45 possession",
        "estimated standings",
        "default or implicit cold-start ELO",
        "fatigue 0.5 fallback",
        "compatibility team rating",
        "raw_elo_gap * 0.1 adjusted ELO",
    ]:
        raise error_type("legacy proxy rejection policy malformed")
    text_fields(legacy, {"compatibility_behavior"}, "legacy proxy policy")
