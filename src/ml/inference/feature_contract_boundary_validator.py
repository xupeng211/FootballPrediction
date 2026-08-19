"""Fail-closed validation for versioned canonical feature-contract boundaries.

lifecycle: permanent
component: Specialized / Internal (registry validation helper; not a feature authority)

The git-tracked JSON registry remains the semantic authority. This module only
enforces the frozen shape and values before a consumer can bind to it.
"""

from collections.abc import Mapping
from typing import Any

from src.ml.inference.model_asof_contract import (
    MODEL_ASOF_AVAILABILITY_FORMS,
    MODEL_ASOF_CONTRACT_ID,
    MODEL_ASOF_CONTRACT_VERSION,
    MODEL_ASOF_FIELD_DESCRIPTIONS,
    MODEL_ASOF_FIELD_NAMES,
    ModelAsOfValidationError,
    validate_model_as_of_context,
    validate_model_asof_registry_boundary,
)
from src.ml.inference.runtime_capture_contract import validate_runtime_capture_registry_boundary
from src.ml.inference.standings_asof_engine_consumer_registry_validator import (
    validate_standings_asof_engine_consumer_registry_boundary,
)
from src.ml.inference.standings_asof_engine_input_registry_validator import (
    validate_standings_asof_engine_input_registry_boundary,
)
from src.ml.inference.standings_asof_runtime_source_normalization_registry_validator import (
    validate_standings_asof_runtime_source_normalization_registry_boundary as validate_normalization_registry,
)

__all__ = [
    "MODEL_ASOF_AVAILABILITY_FORMS",
    "MODEL_ASOF_CONTRACT_ID",
    "MODEL_ASOF_CONTRACT_VERSION",
    "MODEL_ASOF_FIELD_DESCRIPTIONS",
    "MODEL_ASOF_FIELD_NAMES",
    "ModelAsOfValidationError",
    "validate_model_as_of_context",
    "validate_runtime_capture_manifest_against_canonical_registry",
    "validate_standings_asof_engine_consumer_registry_boundary",
    "validate_standings_asof_engine_input_registry_boundary",
    "validate_v2_decision_boundaries",
]

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
        "model_as_of",
        "runtime_capture",
        "standings_asof_engine_input",
        "standings_asof_engine_consumer",
        "raw_elo",
        "standings",
        "sot",
        "possession",
        "shared_engine",
        "activation",
        "legacy_proxy_policy",
    } | {"standings_asof_runtime_source_normalization"}
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

    def text_list(value: Any, label: str, expected: list[str] | None = None) -> list[str]:
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise error_type(f"{label} malformed")
        if expected is not None and value != expected:
            raise error_type(f"{label} malformed")
        return value

    def integer(value: Any, label: str, expected: int | None = None) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or (expected is not None and value != expected)
        ):
            raise error_type(f"{label} malformed")
        return value

    validate_model_asof_registry_boundary(boundaries["model_as_of"], error_type)
    validate_runtime_capture_registry_boundary(boundaries["runtime_capture"], error_type)
    validate_standings_asof_engine_input_registry_boundary(
        boundaries["standings_asof_engine_input"], error_type
    )
    validate_standings_asof_engine_consumer_registry_boundary(
        boundaries["standings_asof_engine_consumer"], error_type
    )
    normalization_boundary = boundaries["standings_asof_runtime_source_normalization"]
    validate_normalization_registry(normalization_boundary, error_type)

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
            "semantic_contract_status",
            "historical_evidence_status",
            "contract",
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
        "rule_history_closure_required": "NO",
        "semantic_contract_status": "FROZEN",
        "historical_evidence_status": "EVIDENCE_CLOSED_FOR_FROZEN_SCOPE",
    }.items():
        text(standings[field], f"standings decision boundary.{field}", expected)
    text_list(standings["unresolved_evidence"], "standings unresolved evidence", [])

    standings_contract = exact_object(
        standings["contract"],
        {
            "contract_id",
            "version",
            "feature_bindings",
            "competition_scope",
            "season_rule_bindings",
            "points_rule",
            "ordering_rules",
            "tie_representation",
            "table_position_diff_rule",
            "strict_cutoff_rule",
            "same_kickoff_rule",
            "postponed_rule",
            "exception_rule",
            "administrative_adjustment_rule",
            "season_boundary_rule",
            "result_state_requirements",
            "missing_history_policy",
            "source_authority",
            "lineage_requirements",
            "source_conflict_policy",
            "fail_closed_reason_codes",
            "evidence_provenance",
        },
        "standings semantic contract",
    )
    text(
        standings_contract["contract_id"],
        "standings contract id",
        "standings/premier-league-point-in-time/v1",
    )
    text(standings_contract["version"], "standings contract version", "v1")
    text_list(
        standings_contract["feature_bindings"],
        "standings feature bindings",
        ["home_table_position", "away_table_position", "table_position_diff"],
    )

    scope = exact_object(
        standings_contract["competition_scope"],
        {"competition", "league_id", "frozen_seasons", "target_population"},
        "standings competition scope",
    )
    text(scope["competition"], "standings competition", "Premier League")
    integer(scope["league_id"], "standings league id", 47)
    text_list(
        scope["frozen_seasons"],
        "standings frozen seasons",
        ["2022/2023", "2023/2024", "2024/2025"],
    )
    integer(scope["target_population"], "standings target population", 888)

    expected_rule_bindings = [
        {
            "season": "2022/2023",
            "document_title": "Premier League Handbook 2022/23",
            "source_url": "https://resources.premierleague.com/premierleague/document/2022/07/19/40085fed-1e9e-4c33-9f14-0bcf57857da2/PL_Handbook_2022-23_DIGITAL_18.07.pdf",
            "rule_identifier": "C.1-C.7,C.17,C.18,C.25-C.30",
        },
        {
            "season": "2023/2024",
            "document_title": "Premier League Handbook 2023/24 v3",
            "source_url": "https://resources.premierleague.com/premierleague/document/2024/03/04/0910e1b3-f94a-41a5-9818-6e1b5c961a9a/PL_Handbook_2023-24_DIGITAL_26.02.24-v3.pdf",
            "rule_identifier": "C.1-C.7,C.17,C.18,C.25-C.30",
        },
        {
            "season": "2024/2025",
            "document_title": "Premier League Handbook and Collateral 2024/25 V2",
            "source_url": "https://resources.premierleague.com/premierleague/document/2024/07/26/e6332e5a-4ca6-4411-bf01-9f8ab76c6fb4/TM1534-PL_Handbook-and-Collateral-2024-25_25.07_V2.pdf",
            "rule_identifier": "C.1-C.7,C.17,C.18,C.25-C.30",
        },
    ]
    bindings = standings_contract["season_rule_bindings"]
    if not isinstance(bindings, list) or bindings != expected_rule_bindings:
        raise error_type("standings season rule bindings malformed")

    points_rule = exact_object(
        standings_contract["points_rule"], {"win", "draw", "loss"}, "standings points rule"
    )
    for field, expected in {"win": 3, "draw": 1, "loss": 0}.items():
        integer(points_rule[field], f"standings points rule.{field}", expected)
    text_list(
        standings_contract["ordering_rules"],
        "standings ordering rules",
        ["points", "goal_difference", "goals_scored"],
    )

    tie = exact_object(
        standings_contract["tie_representation"],
        {"mode", "definition", "examples", "forbidden_tie_breakers"},
        "standings tie representation",
    )
    text(
        tie["mode"],
        "standings tie representation.mode",
        "COMPETITION_RANKING_SHARED_POSITION_WITH_GAPS",
    )
    text(
        tie["definition"],
        "standings tie representation.definition",
        "1 + number of clubs strictly ahead under the applicable ordinary ranking criteria.",
    )
    text_list(tie["examples"], "standings tie representation.examples", ["1,1,3", "4,5,5,7"])
    text_list(
        tie["forbidden_tie_breakers"],
        "standings tie representation.forbidden_tie_breakers",
        [
            "alphabetical club name",
            "team ID",
            "provider order",
            "match ID",
            "database order",
            "filesystem order",
            "ingestion order",
        ],
    )

    position_diff = exact_object(
        standings_contract["table_position_diff_rule"],
        {"orientation", "formula", "requires_both_positions", "unavailable_if_either_missing"},
        "standings table position diff rule",
    )
    text(
        position_diff["orientation"],
        "standings table position diff orientation",
        "HOME_POSITION_MINUS_AWAY_POSITION",
    )
    text(
        position_diff["formula"],
        "standings table position diff formula",
        "home_table_position - away_table_position",
    )
    text(
        position_diff["requires_both_positions"], "standings table position diff dependency", "YES"
    )
    text(
        position_diff["unavailable_if_either_missing"],
        "standings table position diff missing policy",
        "YES",
    )

    for field, expected in {
        "strict_cutoff_rule": "SOURCE_EVENT_TIME_LT_TARGET_KICKOFF",
        "same_kickoff_rule": "EXCLUDED",
        "postponed_rule": "ACTUAL_PLAYED_EVENT_TIME_ONLY",
        "season_boundary_rule": "EXACT_COMPETITION_SEASON_CLUB_UNIVERSE_ONLY",
    }.items():
        text(standings_contract[field], f"standings contract.{field}", expected)

    exception_rule = exact_object(
        standings_contract["exception_rule"],
        {"abandoned", "awarded", "replayed", "void", "unknown_status"},
        "standings exception rule",
    )
    for field, expected in {
        "abandoned": "NOT_TABLE_ELIGIBLE",
        "awarded": "OFFICIAL_TABLE_ELIGIBILITY_REQUIRED",
        "replayed": "OFFICIAL_DISPOSITION_WITHOUT_DOUBLE_COUNT",
        "void": "NOT_TABLE_ELIGIBLE",
        "unknown_status": "FAIL_CLOSED",
    }.items():
        text(exception_rule[field], f"standings exception rule.{field}", expected)

    adjustment_rule = exact_object(
        standings_contract["administrative_adjustment_rule"],
        {
            "point_layer",
            "retroactive_allowed",
            "exact_timestamp",
            "date_only",
            "before_interval",
            "after_interval",
            "overlap",
            "overlap_reason_code",
        },
        "standings administrative adjustment rule",
    )
    for field, expected in {
        "point_layer": "MATCH_EARNED_POINTS_PLUS_EFFECTIVE_ADMINISTRATIVE_ADJUSTMENTS",
        "retroactive_allowed": "NO",
        "exact_timestamp": "USE_EXACT_TIMESTAMP",
        "date_only": "UNCERTAIN_DAY_INTERVAL",
        "before_interval": "NOT_EFFECTIVE",
        "after_interval": "EFFECTIVE",
        "overlap": "UNAVAILABLE",
        "overlap_reason_code": "ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS",
    }.items():
        text(adjustment_rule[field], f"standings administrative adjustment rule.{field}", expected)

    text_list(
        standings_contract["result_state_requirements"],
        "standings result state requirements",
        [
            "canonical_match_identity",
            "canonical_team_identity",
            "proven_eligible_result_status",
            "actual_eligible_event_time",
            "final_score",
            "source_lineage",
        ],
    )
    missing_history = exact_object(
        standings_contract["missing_history_policy"],
        {"action", "reason_code", "fallbacks_forbidden"},
        "standings missing history policy",
    )
    text(missing_history["action"], "standings missing history action", "UNAVAILABLE")
    text(
        missing_history["reason_code"],
        "standings missing history reason",
        "MISSING_PRIOR_RESULT_EVIDENCE",
    )
    text_list(
        missing_history["fallbacks_forbidden"],
        "standings missing history fallbacks",
        [
            "skip match",
            "forward fill",
            "final table",
            "later standings",
            "provider current table",
            "fabricated score",
        ],
    )

    text_list(
        standings_contract["source_authority"],
        "standings source authority",
        [
            "Season-specific official Premier League handbook/rules.",
            "Official Premier League administrative and fixture-status decisions.",
            "Canonical schedule identity and GD-A02 validated result facts.",
        ],
    )
    text_list(
        standings_contract["lineage_requirements"],
        "standings lineage requirements",
        [
            "canonical competition and season membership",
            "canonical match and team identity",
            "actual eligible event time",
            "final eligible result status and score",
            "exception disposition",
            "administrative adjustment state and effective-time evidence",
            "strict target kickoff cutoff",
        ],
    )

    conflict_policy = exact_object(
        standings_contract["source_conflict_policy"],
        {"action", "reason_codes", "majority_vote", "provider_priority"},
        "standings source conflict policy",
    )
    text(conflict_policy["action"], "standings source conflict action", "FAIL_CLOSED")
    text_list(
        conflict_policy["reason_codes"],
        "standings source conflict reason codes",
        [
            "RESULT_IDENTITY_CONFLICT",
            "RESULT_SCORE_CONFLICT",
            "EVENT_TIME_CONFLICT",
            "FIXTURE_STATUS_CONFLICT",
            "ADMIN_ADJUSTMENT_CONFLICT",
        ],
    )
    text(conflict_policy["majority_vote"], "standings source conflict majority vote", "FORBIDDEN")
    text(
        conflict_policy["provider_priority"],
        "standings source conflict provider priority",
        "FORBIDDEN_WITHOUT_EXPLICIT_AUTHORITY",
    )
    text_list(
        standings_contract["fail_closed_reason_codes"],
        "standings fail-closed reason codes",
        [
            "MISSING_PRIOR_RESULT_EVIDENCE",
            "RESULT_IDENTITY_CONFLICT",
            "RESULT_SCORE_CONFLICT",
            "EVENT_TIME_CONFLICT",
            "FIXTURE_STATUS_CONFLICT",
            "ADMIN_ADJUSTMENT_CONFLICT",
            "ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS",
            "POSTPONED_EVENT_TIME_UNPROVEN",
            "EXCEPTION_STATUS_UNPROVEN",
            "RULE_VERSION_UNPROVEN",
            "SAME_KICKOFF_NOT_ELIGIBLE",
            "STANDINGS_POSITION_UNAVAILABLE",
            "DEPENDENCY_UNAVAILABLE",
        ],
    )

    evidence_provenance = exact_object(
        standings_contract["evidence_provenance"],
        {
            "task_id",
            "memo_sha256",
            "target_population",
            "target_row_evidence_coverage",
            "expected_fail_closed_target_rows",
            "expected_unavailable_targets",
            "evidence_status",
        },
        "standings evidence provenance",
    )
    text(
        evidence_provenance["task_id"],
        "standings evidence task",
        "STANDINGS-HISTORY-EVIDENCE-REMEDIATION-V1",
    )
    text(
        evidence_provenance["memo_sha256"],
        "standings evidence memo sha256",
        "e09a80735f26d3fe3f949fcc115c853354c3f449dcf1ca6e9da7954846dbb357",
    )
    integer(evidence_provenance["target_population"], "standings evidence target population", 888)
    text(
        evidence_provenance["target_row_evidence_coverage"],
        "standings evidence coverage",
        "887/888",
    )
    integer(
        evidence_provenance["expected_fail_closed_target_rows"],
        "standings expected unavailable count",
        1,
    )
    text_list(
        evidence_provenance["expected_unavailable_targets"],
        "standings expected unavailable targets",
        ["47_20232024_4193789"],
    )
    text(
        evidence_provenance["evidence_status"],
        "standings evidence status",
        "SEMANTIC_CONTRACT_EVIDENCE_READY",
    )

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


def validate_runtime_capture_manifest_against_canonical_registry(
    manifest: dict[str, Any], payloads: Mapping[str, bytes]
) -> dict[str, Any]:
    """Add canonical feature authority only after exact registry resolution."""
    from src.ml.inference.feature_contract_registry import (  # noqa: PLC0415
        FeatureContractRegistryError,
        load_feature_contract_registry,
    )
    from src.ml.inference.runtime_capture_contract import (  # noqa: PLC0415
        RuntimeCaptureValidationError,
        validate_runtime_capture_manifest,
    )

    if not isinstance(manifest, dict) or not isinstance(manifest.get("PREDICTION_CONTEXT"), dict):
        raise RuntimeCaptureValidationError(
            "CAPTURE_SCHEMA_MISMATCH", "prediction context must be an object"
        )
    context = manifest["PREDICTION_CONTEXT"]
    feature_contract_id = context.get("FEATURE_CONTRACT_ID")
    feature_contract_version = context.get("FEATURE_CONTRACT_VERSION")
    if not isinstance(feature_contract_id, str) or not isinstance(feature_contract_version, str):
        raise RuntimeCaptureValidationError(
            "CAPTURE_SCHEMA_MISMATCH", "feature contract reference is malformed"
        )

    registry = load_feature_contract_registry()
    try:
        contract = registry.get_by_contract_id(feature_contract_id)
    except FeatureContractRegistryError as exc:
        raise RuntimeCaptureValidationError(
            "FEATURE_CONTRACT_AUTHORITY_UNAVAILABLE",
            "canonical feature contract ID is not registered",
        ) from exc
    if contract.feature_contract_version != feature_contract_version:
        raise RuntimeCaptureValidationError(
            "CONTRACT_VERSION_MISMATCH",
            "canonical feature contract version does not match the registry",
        )

    result = validate_runtime_capture_manifest(
        manifest,
        payloads,
        feature_contract_binding=registry.validated_feature_contract_binding(feature_contract_id),
    )
    if result["canonical_feature_contract_authority"] != "NOT_PROVEN_BY_CORE_VALIDATOR":
        raise RuntimeCaptureValidationError(
            "FEATURE_CONTRACT_AUTHORITY_BOUNDARY_MISMATCH",
            "core validator returned an unexpected authority result",
        )
    integrated_result = dict(result)
    integrated_result["feature_contract_reference"] = (
        "FEATURE_CONTRACT_REFERENCE_MATCHED_TO_CANONICAL_REGISTRY"
    )
    integrated_result["canonical_feature_contract_authority"] = (
        "CANONICAL_FEATURE_CONTRACT_AUTHORITY_PROVEN"
    )
    return integrated_result
