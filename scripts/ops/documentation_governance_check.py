#!/usr/bin/env python3
"""Check documentation governance rules for documentation cleanup PRs.

lifecycle: permanent
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

ROOT = Path(__file__).resolve().parents[2]
MAX_ADDED_FILES = 5
NAME_STATUS_PATH_PARTS = 2
NAME_STATUS_RENAME_PARTS = 3
PHASE1_MAX_ADDED_FILES = 1
PHASE2_MAX_ADDED_FILES = 1
PHASE3A_MAX_ADDED_FILES = 1
AI_AUDIT_MAX_ADDED_FILES = 1
TEST_DEBT_AUDIT_MAX_ADDED_FILES = 1
WILDCARD_CHARS = frozenset("*?[]")

PHASE0_ALLOWED_ADDED = frozenset(
    {
        "docs/DOCUMENTATION_GOVERNANCE.md",
        "docs/CODEX_WORKFLOW.md",
        "docs/_reports/DOCUMENTATION_GOVERNANCE_AUDIT_NO_DELETION.md",
        "scripts/ops/documentation_governance_check.py",
        "tests/unit/test_documentation_governance_check.py",
    }
)

PHASE1_ALLOWED_ADDED = frozenset(
    {
        "docs/_reports/DOCUMENTATION_CLEANUP_PHASE1_SOURCE_OF_TRUTH_NO_DELETION.md",
    }
)

PHASE2_ALLOWED_ADDED = frozenset(
    {
        "docs/_reports/DOCUMENTATION_CLEANUP_PHASE2_ARCHIVE_CANDIDATE_MARKING_NO_MOVE.md",
    }
)

PHASE3A_ALLOWED_ADDED = frozenset(
    {
        "docs/_reports/DOCUMENTATION_CLEANUP_PHASE3A_ARCHIVE_MOVE_PLAN_NO_DELETION_NO_MOVE.md",
    }
)

AI_AUDIT_ALLOWED_ADDED = frozenset(
    {
        "docs/_reports/AI_WORKFLOW_AND_TECH_DEBT_AUDIT_NO_CODE_CHANGES.md",
    }
)

TEST_DEBT_AUDIT_ALLOWED_ADDED = frozenset(
    {
        "docs/_reports/TEST_DEBT_AUDIT_NO_RUNTIME_CHANGE.md",
    }
)

SOURCE_OF_TRUTH_ALLOWED_CHANGED = frozenset(
    {
        # Permanent workflow / source-of-truth instruction files.
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".claude/README.md",
        ".eslintrc.json",
        ".github/pull_request_template.md",
        "README.md",
        "package.json",
        "package-lock.json",
        "docs/PROJECT_STATUS.md",
        "docs/CAPABILITY_INDEX.md",
        "docs/ACTIVE_MILESTONE.md",
        "docs/MODEL_ARTIFACTS.md",
        "docs/DATA_SOURCE_STRATEGY.md",
        "docs/data/FOTMOB_CURRENT_STATE.md",
        "docs/CANONICAL_MATCH_SCHEMA.md",
        "docs/DOCUMENTATION_GOVERNANCE.md",
        "docs/CODEX_WORKFLOW.md",
        "docs/AGENT_WORKFLOW.md",
        "docs/CLAUDE_JS_TOOLS.md",
        "docs/TESTING_GUIDE.md",
        "docs/troubleshooting.md",
        "docs/architecture/L1_DATA_CONTRACT.md",
        "docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md",
        "docs/GITHUB_ACTIONS_AUDIT_REPORT.md",
        "docs/PROJECT_MAP.md",
        "docs/PROJECT_VISION.md",
        "Makefile",
        "docs/AI_AGENT_WORKFLOW_HARDENING.md",
        "docs/engineering/AI_AGENT_WORKFLOW.md",
        "docs/WORKFLOW_TOOLCHAIN_INVENTORY.md",
        "CONTRIBUTING.md",
        ".github/CODEOWNERS",
        "scripts/ops/ai_workflow_gate.py",
        "scripts/ops/documentation_governance_check.py",
        "scripts/ops/helpers/documentation_backflow.py",
        "scripts/ci/l3_changed_file_classifier.py",
        "scripts/devops/pr_body_check.py",
        "scripts/devops/pr_merge_preflight.py",
        "scripts/devops/pr_post_merge_check.py",
        "scripts/ops/helpers/ai_gate_event_refs.py",
        "scripts/ops/helpers/section_content_quality.py",
        "scripts/ops/helpers/pr_authorization_matrix.py",
        "scripts/ops/helpers/dangerous_file_change_check.py",
        "scripts/ops/helpers/strict_review_evidence.py",
        "scripts/devops/validation_profiles.py",
        "scripts/devops/pr_ready_check.py",
        "scripts/devops/exact_head.py",
        ".github/workflows/production-gate.yml",
        "scripts/devops/static_quality_changed_lines.py",
        "tests/unit/test_agent_workflow_hardening.py",
        "tests/unit/test_ai_workflow_gate.py",
        "tests/unit/test_ai_workflow_gate_enforcement.py",
        "tests/unit/test_local_pr_gate_preflight.py",
        "tests/unit/test_strict_review_evidence.py",
        "tests/unit/test_documentation_governance_check.py",
        "tests/unit/test_project_knowledge_convergence.py",
        "tests/unit/test_agent_workflow_hardening_phase1_ci_rules.py",
        "tests/unit/test_dangerous_file_change_check.py",
        "tests/unit/test_validation_profiles.py",
        "tests/unit/test_pr_ready_check.py",
        "tests/unit/test_exact_head.py",
        "tests/unit/test_pr_body_check.py",
        "tests/unit/test_pr_merge_preflight.py",
        "tests/unit/test_pr_post_merge_check.py",
        "tests/unit/test_pr_post_merge_check_protected.py",
    }
)

# Agent host configuration is allowed only as these exact paths.  These files
# do not become project authority merely because the governance checker knows
# how to permit a bounded reality-reconciliation change.
AGENT_CONFIG_ALLOWED_CHANGED = frozenset(
    {
        ".claude/settings.json",
        ".claude/mcp-config.json",
    }
)

AGENT_CONFIG_RELATIVE_PATHS: tuple[str, ...] = (
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/mcp-config.json",
)
INLINE_USERINFO_URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^/\s?#@]+@[^/\s?#]+(?:[/\?#]|$)")


def _iter_json_string_values(
    value: object, field_path: tuple[str, ...] = ()
) -> Iterable[tuple[str, str]]:
    """Yield JSON string values with redaction-safe field paths."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _iter_json_string_values(child, (*field_path, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_json_string_values(child, (*field_path, str(index)))
    elif isinstance(value, str):
        yield ".".join(field_path), value


def scan_tracked_claude_config_credentials(root: Path | None = None) -> list[str]:
    """Fail closed on inline userinfo in the exact tracked Claude config paths.

    The JSON is parsed before scalar values are inspected. Findings contain only
    a repository-relative path, JSON field path, and violation type; values are
    deliberately never included in the result.
    """
    workspace = root if root is not None else ROOT
    findings: list[str] = []
    for relative_path in AGENT_CONFIG_RELATIVE_PATHS:
        config_path = workspace / relative_path
        if not config_path.is_file():
            continue
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            findings.append(f"{relative_path}:INVALID_JSON")
            continue

        for field_path, value in _iter_json_string_values(payload):
            if INLINE_USERINFO_URI.match(value):
                safe_field_path = field_path or "<root>"
                findings.append(f"{relative_path}:{safe_field_path}:INLINE_USERINFO_URI")
    return findings


# WF01 intentionally removes the second pull-request template. WF05 also
# removes the obsolete CI setup note after proving that it has no supported
# caller or current workflow reference. The bounded retirements below remove
# only exact audited legacy Claude skill assets and the obsolete history-rewrite
# notice template; other deletion or rename remains prohibited by this checker.
ALLOWED_DELETED = frozenset(
    {
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ci-setup.md",
        "tests/setup.js",
        ".claude/skills/api-testing/SKILL.md",
        ".claude/skills/data-collection/SKILL.md",
        ".claude/skills/data-engineering/SKILL.md",
        ".claude/skills/data-engineering/README.md",
        ".claude/skills/database-operations/SKILL.md",
        ".claude/skills/deployment-management/SKILL.md",
        ".claude/skills/deployment-operations/SKILL.md",
        ".claude/skills/docker-devops/SKILL.md",
        ".claude/skills/performance-monitoring/SKILL.md",
        ".claude/skills/report-generation/SKILL.md",
        ".claude/skills/football-prediction/SKILL.md",
        ".claude/skills/feature-engineering/SKILL.md",
        ".claude/skills/machine-learning-engineering/SKILL.md",
        ".claude/skills/machine-learning-engineering/README.md",
        ".claude/skills/fastapi-development/SKILL.md",
        ".claude/skills/fastapi-development/README.md",
        ".claude/skills/v26-harvest/SKILL.md",
        ".claude/architecture_boundary.skill.md",
        ".claude/change_impact.skill.md",
        ".claude/context_lock.skill.md",
        ".claude/minimal_change.skill.md",
        ".claude/skills/async_testing.md",
        ".claude/skills/code-quality/SKILL.md",
        ".claude/skills/custom/__init__.py",
        ".claude/skills/custom/data_collection.py",
        ".claude/skills/data-engineering/examples/data_integration_example.py",
        ".claude/skills/data-engineering/scripts/cache_strategy_manager.py",
        ".claude/skills/data-engineering/scripts/database_connection_optimizer.py",
        ".claude/skills/dependency_injection_mock.md",
        ".claude/skills/deployment-operations/deployment_operations.py",
        ".claude/skills/docker-devops/examples/deployment_integration_example.py",
        ".claude/skills/docker-devops/scripts/docker_optimizer.py",
        ".claude/skills/fastapi-development/examples/api_integration_example.py",
        ".claude/skills/fastapi-development/scripts/api_performance_optimizer.py",
        ".claude/skills/fastapi-development/templates/performance_middleware.py",
        ".claude/skills/machine-learning-engineering/examples/integration_example.py",
        ".claude/skills/machine-learning-engineering/scripts/feature_engineering_analyzer.py",
        ".claude/skills/machine-learning-engineering/scripts/xgboost_optimizer.py",
        ".claude/skills/machine-learning-engineering/templates/model_training_pipeline.py",
        ".claude/skills/naming_convention.md",
        ".claude/test_guard.skill.md",
        "docs/templates/HISTORY_REWRITE_COLLABORATOR_NOTICE.md",
        "scripts/test_gui.js",
    }
)

# These patterns cover only the completed historical-report categories audited
# in Batch 02. They are consulted for DELETE status only; they are deliberately
# not part of ALLOWED_CHANGED, so a future ADD/MODIFY of a retired category is
# still rejected. The alternatives avoid allowing the neighboring live or
# unresolved data-operation reports in the same directories.
RETIRED_HISTORY_DELETE_ONLY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^docs/_manifests/"
        r"fotmob_pageprops_v2_ligue1_2025_2026_profile_001\."
        r"architecture_decision_gate\.phase521\.json$"
    ),
    re.compile(
        r"^docs/_reports/(?:"
        r"ACQUISITION_ENGINE_RATIONALIZATION_PHASE4_55C|"
        r"ACQUISITION_ENGINE_REGISTRY_PHASE4_54|"
        r"ACQUISITION_GATE_NO_NETWORK_TESTS_PHASE4_55B|"
        r"ACQUISITION_REGISTRY_GOVERNANCE_PHASE4_56C|"
        r"ADAPTER_CANDIDATE_READINESS_CLOSURE_PHASE4_60C|"
        r"DATASET_STATUS_AUDIT_GATE_PHASE4_36|"
        r"DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3B|"
        r"FETCH_ADAPT_EURO_LEAGUES_NO_NETWORK_PHASE4_57C|"
        r"FINISHED_CSV_DRY_RUN_GATE_PHASE4_38|"
        r"FINISHED_MATCH_SOURCE_AUDIT_PHASE4_37|"
        r"FOOTBALL_DATA_ADAPTER_EXTRACTION_PLAN_PHASE4_61C|"
        r"FOOTBALL_DATA_LOCAL_CSV_PARSER_COVERAGE_HOTFIX_PHASE4_62C|"
        r"FOOTBALL_DATA_PACKET_FILE_AUTH_PACKET_DRAFT_PHASE4_74C|"
        r"FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW_CONSOLIDATION_PHASE4_75C|"
        r"FOOTBALL_DATA_PACKET_FILE_READINESS_PHASE4_73C|"
        r"FOTMOB_ADG60_RAW_PAYLOAD_STORAGE_REVIEW_NO_DB|"
        r"FOTMOB_IDENTITY_ARCHITECTURE_DECISION_GATE_PHASE5_21|"
        r"FOTMOB_LIGUE1_ADG60_LIVE_FETCH_FINAL_BATCH_NO_WRITE_REVIEW|"
        r"FOTMOB_LIGUE1_SOURCE_INVENTORY_INVERSION_CORRECTION_IMPLEMENTATION_ADG14|"
        r"FOTMOB_LIGUE1_SOURCE_INVENTORY_INVERSION_CORRECTION_PLAN_ADG13|"
        r"FOTMOB_OBSERVED_IDENTITY_EVIDENCE_ACQUISITION_PLAN_ADG11|"
        r"FOTMOB_RAW_DETAIL_FETCHER_CONSOLIDATION_PHASE5_20L2A|"
        r"FOTMOB_RAW_DETAIL_HASH_STABILITY_AUDIT_PHASE5_20L2D|"
        r"FOTMOB_URL_HASH_DETAIL_IDENTITY_PROPAGATION_IMPLEMENTATION_ADG3|"
        r"L3H_WARNING_ONLY_CLASSIFIER_VISIBILITY_CALIBRATION_REPORT|"
        r"L3_FEATURES_LOCAL_WRITE_GATE_PHASE4_26|"
        r"LARGE_SCALE_TARGET_INVENTORY_SCHEMA_READINESS_AUDIT_PHASE5_21L2R|"
        r"LOCAL_HTML_ODDS_COMMIT_PHASE4_16|"
        r"MATCH_FEATURES_TRAINING_GATE_PHASE4_30|"
        r"MATCH_SEED_RUNBOOK_PHASE4_12|"
        r"ODDS_HARVEST_PIPELINE_NO_NETWORK_PHASE4_59C|"
        r"PREDICTION_WRITE_GATE_PHASE4_32|"
        r"REAL_DATA_SOURCE_STRATEGY_PHASE4_51|"
        r"REAL_FINISHED_CSV_STAGING_DRY_RUN_PHASE4_52|"
        r"RECON_LEAGUE_DICTIONARY_FLOW_MAIN_CI_HOTFIX|"
        r"SINGLE_TARGET_ACQUISITION_RUNTIME_SCAFFOLD_PHASE4_79D|"
        r"SYNTHETIC_L3_PREFLIGHT_PHASE4_44|"
        r"SYNTHETIC_PREDICTION_PREFLIGHT_PHASE4_48|"
        r"SYNTHETIC_RAW_FIXTURE_PHASE4_42|"
        r"authoritative_workflow_enforcement_dry_run_20260621"
        r")\.md$"
    ),
    re.compile(
        r"^docs/_reports/fotmob_l2_(?:"
        r"(?:first|second)_guarded_reconciliation_(?:execution_plan|"
        r"execution_verification|post_execution_audit)_20260615"
        r"|third_guarded_reconciliation_(?:(?:execution_plan|"
        r"execution_verification)_20260615|post_execution_audit_20260616)"
        r"|(?:fourth|fifth|sixth)_guarded_reconciliation_(?:execution_plan|"
        r"execution_verification|post_execution_audit)_20260616"
        r"|(?:seventh|eighth)_guarded_reconciliation_(?:execution_plan|"
        r"execution_verification|post_execution_audit)_20260617"
        r"|(?:ninth|tenth)_guarded_reconciliation_(?:execution_plan|"
        r"execution_verification|post_execution_audit)_20260618"
        r"|guarded_reconciliation_limit10_change_20260616"
        r"|guarded_reconciliation_write_draft_20260615"
        r"|limit10_selection_investigation_20260616"
        r")\.md$"
    ),
    re.compile(
        r"^docs/_reports/(?:"
        r"fotmob_null_id_event_shape_audit_20260611|"
        r"fotmob_parser_dry_run_4_retained_rerun_20260611|"
        r"fotmob_parser_dry_run_after_synthetic_id_policy_20260612|"
        r"fotmob_parser_expanded_retained_dry_run_20260612|"
        r"fotmob_raw_parser_stage_gate_20260612"
        r")\.md$"
    ),
    re.compile(
        r"^docs/_reports/(?:"
        r"matches_labeling_backfill_write_verification_20260619|"
        r"matches_labeling_post_backfill_audit_20260619|"
        r"matches_labeling_schema_design_proposal_20260619|"
        r"matches_labeling_schema_migration_verification_20260619|"
        r"score_backfill_dry_run_20260619|"
        r"score_backfill_write_verification_20260619|"
        r"score_fields_result_label_audit_20260619|"
        r"smoke_training_dataset_dry_run_20260619|"
        r"training_eligibility_after_score_dry_run_20260619|"
        r"training_eligibility_dry_run_20260619|"
        r"training_eligibility_write_verification_20260619|"
        r"training_pipeline_smoke_dry_run_20260619"
        r")\.md$"
    ),
    re.compile(
        r"^docs/_reports/REPO_SLIMMING_PHASE(?:"
        r"2_5_MODEL_ARTIFACT_RECOVERY|2_INDEX_CLEANUP|3_1_DRY_RUN|"
        r"3_2_NARROW_DRY_RUN|3_3_MANUAL_DRY_RUN|3_4_GO_NO_GO|3_HISTORY_AUDIT"
        r")\.md$"
    ),
    re.compile(r"^docs/(?:FORENSIC_AUDIT_REPORT|REPO_HISTORY_REWRITE_GO_NO_GO)\.md$"),
    re.compile(r"^docs/V26_7_STRESS_TEST_20260107_111453\.txt$"),
    re.compile(r"^docs/architecture/DEEP_CLEAN_TECH_DEBT_MAP\.md$"),
    re.compile(r"^docs/audit/yield_audit_20251223_182617\.txt$"),
)


def is_delete_allowed(path: str) -> bool:
    """Return whether a path is in an exact or audited delete-only retirement set."""

    return path in ALLOWED_DELETED or any(
        pattern.fullmatch(path) for pattern in RETIRED_HISTORY_DELETE_ONLY_PATTERNS
    )


ALLOWED_ADDED = (
    PHASE0_ALLOWED_ADDED
    | PHASE1_ALLOWED_ADDED
    | PHASE2_ALLOWED_ADDED
    | PHASE3A_ALLOWED_ADDED
    | AI_AUDIT_ALLOWED_ADDED
    | TEST_DEBT_AUDIT_ALLOWED_ADDED
)
ALLOWED_CHANGED = ALLOWED_ADDED | SOURCE_OF_TRUTH_ALLOWED_CHANGED | AGENT_CONFIG_ALLOWED_CHANGED

REQUIRED_DOCS = (
    "AGENTS.md",
    "docs/AGENT_WORKFLOW.md",
    "docs/DOCUMENTATION_GOVERNANCE.md",
    "docs/_reports/DOCUMENTATION_GOVERNANCE_AUDIT_NO_DELETION.md",
)

GOVERNANCE_SECTIONS = (
    "Document Classes",
    "Documentation Budget",
    "Documentation Impact Requirement",
    "Source of Truth Rule",
    "Report Lifecycle",
    "Codex Documentation Rules",
)

WORKFLOW_SECTIONS = {
    "AGENTS.md": (
        "NORMAL",
        "STRICT",
        "make verify-pr",
        "exact-head",
        "DONE",
    ),
    "docs/AGENT_WORKFLOW.md": (
        "TEST",
        "CI",
        "REVIEW",
        "OWNER",
        "exact-head",
    ),
}

AUDIT_SECTIONS = (
    "Inventory",
    "Top Problem Areas",
    "Proposed Source of Truth Docs",
    "Archive Candidates",
    "Phase 1 Cleanup Proposal",
)

ALLOWLIST_GROUPS = (
    PHASE0_ALLOWED_ADDED,
    PHASE1_ALLOWED_ADDED,
    PHASE2_ALLOWED_ADDED,
    PHASE3A_ALLOWED_ADDED,
    AI_AUDIT_ALLOWED_ADDED,
    TEST_DEBT_AUDIT_ALLOWED_ADDED,
)


@dataclass(frozen=True)
class Change:
    """A normalized Git change entry."""

    status: str
    path: str
    old_path: str | None = None


def git_output(args: list[str], *, check: bool = True) -> str:
    """Run a local Git command and return stdout."""

    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def find_base_ref() -> str:
    """Find a local base ref without fetching from the network."""

    for ref in ("origin/main", "main"):
        result = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return ref
    return "HEAD"


def parse_name_status(output: str) -> list[Change]:
    """Parse git diff --name-status output."""

    changes: list[Change] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= NAME_STATUS_RENAME_PARTS:
            changes.append(Change("R", parts[2], parts[1]))
            continue
        if status.startswith("D") and len(parts) >= NAME_STATUS_PATH_PARTS:
            changes.append(Change("D", parts[1]))
            continue
        if status.startswith("A") and len(parts) >= NAME_STATUS_PATH_PARTS:
            changes.append(Change("A", parts[1]))
            continue
        if len(parts) >= NAME_STATUS_PATH_PARTS:
            changes.append(Change("M", parts[1]))
    return changes


def parse_porcelain(output: str) -> list[Change]:
    """Parse git status --porcelain output."""

    changes: list[Change] = []
    for line in output.splitlines():
        if not line:
            continue
        code = line[:2]
        path = line[3:]
        if " -> " in path:
            old_path, new_path = path.split(" -> ", 1)
            changes.append(Change("R", new_path, old_path))
        elif code == "??" or "A" in code:
            changes.append(Change("A", path))
        elif "D" in code:
            changes.append(Change("D", path))
        else:
            changes.append(Change("M", path))
    return changes


def collect_changes(base_ref: str | None = None) -> list[Change]:
    """Collect committed and uncommitted changes for the branch."""

    base = base_ref or find_base_ref()
    diff_output = git_output(["diff", "--name-status", f"{base}...HEAD"])
    status_output = git_output(["status", "--porcelain"])
    unique: dict[tuple[str, str, str | None], Change] = {}
    for change in [*parse_name_status(diff_output), *parse_porcelain(status_output)]:
        unique[(change.status, change.path, change.old_path)] = change
    return list(unique.values())


def added_paths(changes: list[Change]) -> set[str]:
    """Return paths added by the current branch or working tree."""

    return {change.path for change in changes if change.status == "A"}


def changed_paths(changes: list[Change]) -> set[str]:
    """Return all changed paths, including old rename paths."""

    paths = {change.path for change in changes}
    paths.update(change.old_path for change in changes if change.old_path)
    return paths


def read_text(path: str) -> str:
    """Read a repository file as UTF-8 text."""

    return (ROOT / path).read_text(encoding="utf-8")


def iter_allowlist_paths() -> Iterable[str]:
    """Yield all exact paths from governance allowlists."""

    yield from ALLOWED_ADDED
    yield from SOURCE_OF_TRUTH_ALLOWED_CHANGED


def validate_required_files(errors: list[str]) -> None:
    """Validate required governance files and sections."""

    errors.extend(
        f"missing required file: {path}" for path in REQUIRED_DOCS if not (ROOT / path).exists()
    )

    section_sets = (
        *WORKFLOW_SECTIONS.items(),
        ("docs/DOCUMENTATION_GOVERNANCE.md", GOVERNANCE_SECTIONS),
        ("docs/_reports/DOCUMENTATION_GOVERNANCE_AUDIT_NO_DELETION.md", AUDIT_SECTIONS),
    )
    for path, sections in section_sets:
        file_path = ROOT / path
        if not file_path.exists():
            continue
        text = read_text(path)
        errors.extend(
            f"{path} missing section: {section}" for section in sections if section not in text
        )


def validate_exact_allowlist_paths(errors: list[str]) -> None:
    """Validate that allowlist paths are exact and do not target archives."""
    for path in sorted(iter_allowlist_paths()):
        if any(char in path for char in WILDCARD_CHARS):
            errors.append(f"allowlist path must be exact, not wildcard: {path}")
        if path.startswith("docs/_archive/"):
            errors.append(f"archive allowlist path is prohibited: {path}")


def validate_added_allowlist_paths(errors: list[str]) -> None:
    """Validate that added-file allowlists do not permit governance sprawl."""
    for path in sorted(ALLOWED_ADDED):
        lower = path.lower()
        if path.startswith("docs/_manifests/"):
            errors.append(f"manifest allowlist path is prohibited: {path}")
        if "next_plan" in lower or "next-plan" in lower:
            errors.append(f"next-plan allowlist path is prohibited: {path}")
        if path.startswith("docs/_reports/") and "review" in lower:
            errors.append(f"review report allowlist path is prohibited: {path}")
        if path.startswith("docs/_reports/") and "decision" in lower:
            errors.append(f"decision report allowlist path is prohibited: {path}")


def validate_allowlist_budgets(errors: list[str]) -> None:
    """Validate that phase allowlist groups stay within the file budget."""
    if any(len(group) > MAX_ADDED_FILES for group in ALLOWLIST_GROUPS):
        errors.append("allowlist group exceeds maximum added-file budget")


def validate_allowlist_hardening(errors: list[str]) -> None:
    """Validate that governance allowlists stay exact and non-destructive."""
    validate_exact_allowlist_paths(errors)
    validate_added_allowlist_paths(errors)
    validate_allowlist_budgets(errors)


def max_added_files_for(added: set[str]) -> int:
    """Return the added-file budget for the current documentation governance phase."""

    if PHASE1_ALLOWED_ADDED & added:
        return PHASE1_MAX_ADDED_FILES
    if PHASE2_ALLOWED_ADDED & added:
        return PHASE2_MAX_ADDED_FILES
    if PHASE3A_ALLOWED_ADDED & added:
        return PHASE3A_MAX_ADDED_FILES
    if AI_AUDIT_ALLOWED_ADDED & added:
        return AI_AUDIT_MAX_ADDED_FILES
    if TEST_DEBT_AUDIT_ALLOWED_ADDED & added:
        return TEST_DEBT_AUDIT_MAX_ADDED_FILES
    return MAX_ADDED_FILES


def validate_change_budget(changes: list[Change], errors: list[str]) -> None:
    """Validate file budget and allowed paths."""

    added = added_paths(changes)
    changed = changed_paths(changes)
    max_added = max_added_files_for(added)
    allowed_deleted = {
        change.path for change in changes if change.status == "D" and is_delete_allowed(change.path)
    }
    unexpected = sorted(changed - (ALLOWED_CHANGED | allowed_deleted))
    missing = sorted(ALLOWED_ADDED - {path for path in ALLOWED_ADDED if (ROOT / path).exists()})

    if len(added) > max_added:
        errors.append(f"added file budget exceeded: {len(added)} > {max_added}")
    if unexpected:
        errors.append(f"unexpected changed paths: {', '.join(unexpected)}")
    if missing:
        errors.append(f"allowed governance files missing: {', '.join(missing)}")


def validate_prohibited_files(changes: list[Change], errors: list[str]) -> None:
    """Validate prohibited file patterns and destructive operations."""

    added = added_paths(changes)
    for path in sorted(added):
        lower = path.lower()
        if path.startswith("docs/_manifests/"):
            errors.append(f"new manifest is prohibited: {path}")
        if "next_plan" in lower or "next-plan" in lower:
            errors.append(f"new next-plan is prohibited: {path}")
        if path.startswith("docs/_reports/") and "review" in lower:
            errors.append(f"new review report is prohibited: {path}")
        if path.startswith("docs/_reports/") and "decision" in lower:
            errors.append(f"new decision report is prohibited: {path}")

    for change in changes:
        if change.status == "D" and not is_delete_allowed(change.path):
            errors.append(f"deleted file is prohibited: {change.path}")
        if change.status == "R":
            errors.append(
                f"moved or renamed file is prohibited: {change.old_path} -> {change.path}"
            )
        if change.path.startswith("docs/_archive/"):
            errors.append(f"archive operation is prohibited: {change.path}")


def validate() -> list[str]:
    """Return all documentation governance validation errors."""

    errors: list[str] = []
    changes = collect_changes()
    validate_required_files(errors)
    validate_allowlist_hardening(errors)
    validate_change_budget(changes, errors)
    validate_prohibited_files(changes, errors)
    return errors


def main() -> int:
    """Run the checker CLI."""

    errors = validate()
    if errors:
        sys.stdout.write(f"FAIL: {len(errors)} documentation governance error(s)\n")
        for error in errors:
            sys.stdout.write(f"- {error}\n")
        return 1
    sys.stdout.write("PASS: documentation governance checks passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
