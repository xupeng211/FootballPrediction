"""Tests for agent workflow hardening checks (Phase1).

lifecycle: test-fixture

Covers: forbidden rewrite patterns, large risky change detection,
forbidden safety claims, documentation compliance, and new required
PR sections introduced in agent_workflow_rules_hardening_phase1.
"""

from __future__ import annotations

from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[2]

import sys  # noqa: E402

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/ops"))
import ai_workflow_gate as gate  # noqa: E402

from scripts.ops.helpers.agent_workflow_hardening_checks import (  # noqa: E402
    _pr_declares_cleanup_task,
    _pr_declares_scanner_phase,
    check_forbidden_rewrite_patterns,
    check_forbidden_safety_claims,
    check_large_risky_change,
)


def _valid_pr_body() -> str:
    """A minimal-valid PR body with all required sections including new ones."""
    return textwrap.dedent(
        """\
    ## Summary

    - Test PR for AI workflow gate validation.

    ## Scope

    | Item | Value |
    |---|---|
    | Task type | governance-only |
    | One task / one branch / one PR | yes |
    | Business code changed | no |

    ## Documentation Impact

    | Source-of-truth no-update reason | Governance hardening phase, no functional doc changes |
    | New docs added | 0 |

    ## Safety Impact

    | Item | Value |
    |---|---|
    | DB used | n/a |
    | Browser automation used | no |
    | Scraper run | no |

    ## Validation

    Unit tests (pytest): 131 passed, 0 failed. Gate CLI smoke: passed.

    ## CI Gate Scope

    - What the validation proves: CI passes.
    - What the validation does not prove: runtime correctness.

    ## No deletion / no move / no rename confirmation

    | Item | Value |
    |---|---|
    | Deleted files | 0 |

    ## Rollback Plan

    - Revert this commit via `git revert <merge-commit-sha>`.
    - No database or runtime changes involved.

    ## SC-002 status

    - SC-002 is partial mitigation only.
    - This PR does not change SC-002 guard coverage.
    - training / data expansion / real DB write remain blocked.

    ## Remaining risks

    - No remaining risks for this governance-only change.

    ## Next Recommended Task

    Do not start automatically.

    Recommended next task only after user confirmation:

    - TBD
    """
    )


# ---------------------------------------------------------------------------
# Missing new required sections
# ---------------------------------------------------------------------------


def test_missing_sc002_status_fails():
    body = _valid_pr_body().replace("## SC-002 status", "## Removed")
    missing = gate.check_required_sections(body)
    assert "## SC-002 status" in missing


def test_missing_remaining_risks_fails():
    body = _valid_pr_body().replace("## Remaining risks", "## Removed")
    missing = gate.check_required_sections(body)
    assert "## Remaining risks" in missing


# ---------------------------------------------------------------------------
# Forbidden safety claims
# ---------------------------------------------------------------------------


def test_forbidden_claim_safe_to_train_fails():
    body = _valid_pr_body() + "\nsafe to train\n"
    errors = check_forbidden_safety_claims(body)
    assert len(errors) >= 1
    assert "safe to train" in errors[0]


def test_forbidden_claim_sc002_fully_fixed_fails():
    body = _valid_pr_body() + "\nSC-002 fully fixed\n"
    errors = check_forbidden_safety_claims(body)
    assert len(errors) >= 1
    assert "SC-002 fully fixed" in errors[0]


def test_forbidden_claim_production_ready_fails():
    body = _valid_pr_body() + "\nproduction ready\n"
    errors = check_forbidden_safety_claims(body)
    assert len(errors) >= 1
    assert "production ready" in errors[0]


def test_forbidden_claim_training_unblocked_fails():
    body = _valid_pr_body() + "\ntraining unblocked\n"
    errors = check_forbidden_safety_claims(body)
    assert len(errors) >= 1
    assert "training unblocked" in errors[0]


def test_forbidden_claim_data_expansion_ready_fails():
    body = _valid_pr_body() + "\ndata expansion ready\n"
    errors = check_forbidden_safety_claims(body)
    assert len(errors) >= 1
    assert "data expansion ready" in errors[0]


def test_clean_body_no_forbidden_claims_passes():
    body = _valid_pr_body()
    errors = check_forbidden_safety_claims(body)
    assert errors == []


# ---------------------------------------------------------------------------
# Forbidden rewrite file patterns
# ---------------------------------------------------------------------------


def test_added_foo_v2_py_fails():
    added = {"src/prediction/foo_v2.py"}
    body = _valid_pr_body()
    errors = check_forbidden_rewrite_patterns(added, body)
    assert len(errors) >= 1
    assert "foo_v2.py" in errors[0]


def test_added_foo_final_js_fails():
    added = {"scripts/ops/foo_final.js"}
    body = _valid_pr_body()
    errors = check_forbidden_rewrite_patterns(added, body)
    assert len(errors) >= 1
    assert "foo_final.js" in errors[0]


def test_added_foo_rewritten_py_fails():
    added = {"src/ml/foo_rewritten.py"}
    body = _valid_pr_body()
    errors = check_forbidden_rewrite_patterns(added, body)
    assert len(errors) >= 1
    assert "foo_rewritten.py" in errors[0]


def test_added_foo_new_js_fails():
    added = {"scripts/foo_new.js"}
    body = _valid_pr_body()
    errors = check_forbidden_rewrite_patterns(added, body)
    assert len(errors) >= 1
    assert "foo_new.js" in errors[0]


def test_added_foo_replacement_py_fails():
    added = {"src/foo_replacement.py"}
    body = _valid_pr_body()
    errors = check_forbidden_rewrite_patterns(added, body)
    assert len(errors) >= 1
    assert "foo_replacement.py" in errors[0]


def test_added_foo_backup_js_fails():
    added = {"scripts/ops/foo_backup.js"}
    body = _valid_pr_body()
    errors = check_forbidden_rewrite_patterns(added, body)
    assert len(errors) >= 1
    assert "foo_backup.js" in errors[0]


def test_docs_v2_mention_not_flagged_as_rewrite_pattern():
    """Files under docs/ are exempt from rewrite pattern checks."""
    added = {"docs/v2_migration_guide.py"}
    body = _valid_pr_body()
    errors = check_forbidden_rewrite_patterns(added, body)
    assert errors == []


def test_alembic_migration_not_flagged():
    """Alembic migration version files are exempt from rewrite pattern checks."""
    added = {"database/migrations/versions/v2_something.py"}
    body = _valid_pr_body()
    errors = check_forbidden_rewrite_patterns(added, body)
    assert errors == []


def test_cleanup_task_with_rewrite_pattern_passes():
    """Cleanup task with explicit declaration allows rewrite patterns."""
    added = {"src/foo_v2.py"}
    body = _valid_pr_body().replace(
        "| Task type | governance-only |",
        "| Task type | cleanup phase |",
    )
    errors = check_forbidden_rewrite_patterns(added, body)
    assert errors == []


def test_normal_file_not_flagged():
    """Normal file names without forbidden patterns pass."""
    added = {"src/prediction/new_model.py", "scripts/ops/data_check.py"}
    body = _valid_pr_body()
    errors = check_forbidden_rewrite_patterns(added, body)
    assert errors == []


# ---------------------------------------------------------------------------
# Large risky change detection
# ---------------------------------------------------------------------------


def test_normal_small_pr_passes_large_change_check():
    body = _valid_pr_body()
    changes = [
        gate.Change("M", "docs/CODEX_WORKFLOW.md"),
        gate.Change("A", "scripts/ops/helper.py"),
    ]
    errors = check_large_risky_change(changes, body)
    assert errors == []


def test_cleanup_task_with_deletions_passes():
    body = _valid_pr_body().replace(
        "| Task type | governance-only |",
        "| Task type | cleanup phase |",
    )
    changes = [
        gate.Change("D", "old_file_1.py"),
        gate.Change("D", "old_file_2.py"),
        gate.Change("D", "old_file_3.py"),
    ]
    errors = check_large_risky_change(changes, body)
    assert errors == []


def test_deletion_without_cleanup_fails():
    """3+ deletions without cleanup task declaration should fail."""
    body = _valid_pr_body()
    changes = [
        gate.Change("D", "src/old_a.py"),
        gate.Change("D", "src/old_b.py"),
        gate.Change("D", "src/old_c.py"),
        gate.Change("M", "src/other.py"),
    ]
    errors = check_large_risky_change(changes, body)
    assert len(errors) >= 1
    assert "deletion" in errors[0].lower()
    assert "3" in errors[0]


def test_rename_without_cleanup_fails():
    """3+ renames without cleanup task declaration should fail."""
    body = _valid_pr_body()
    changes = [
        gate.Change("R", "src/new_a.py", "src/old_a.py"),
        gate.Change("R", "src/new_b.py", "src/old_b.py"),
        gate.Change("R", "src/new_c.py", "src/old_c.py"),
    ]
    errors = check_large_risky_change(changes, body)
    assert len(errors) >= 1
    assert "rename" in errors[0].lower()
    assert "3" in errors[0]


def test_two_deletions_without_cleanup_passes():
    """2 deletions is below threshold, should pass."""
    body = _valid_pr_body()
    changes = [
        gate.Change("D", "src/old_a.py"),
        gate.Change("D", "src/old_b.py"),
    ]
    errors = check_large_risky_change(changes, body)
    assert errors == []


def test_scanner_phase_with_one_scanner_passes():
    body = _valid_pr_body().replace(
        "| Task type | governance-only |",
        "| Task type | scanner phase |",
    )
    changes = [
        gate.Change("A", "scripts/ops/new_scanner.py"),
    ]
    errors = check_large_risky_change(changes, body)
    assert errors == []


def test_multiple_scanners_without_scanner_phase_fails():
    body = _valid_pr_body()
    changes = [
        gate.Change("A", "scripts/ops/foo_scanner.py"),
        gate.Change("A", "scripts/ops/bar_enforcement.py"),
    ]
    errors = check_large_risky_change(changes, body)
    assert len(errors) >= 1
    assert "scanner" in errors[0].lower()


def test_scanner_phase_with_multiple_scanners_passes():
    body = _valid_pr_body().replace(
        "| Task type | governance-only |",
        "| Task type | scanner phase |",
    )
    changes = [
        gate.Change("A", "scripts/ops/foo_scanner.py"),
        gate.Change("A", "scripts/ops/bar_enforcement.py"),
    ]
    errors = check_large_risky_change(changes, body)
    assert errors == []


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


def test_pr_declares_cleanup_task_detected():
    body = _valid_pr_body().replace(
        "| Task type | governance-only |",
        "| Task type | cleanup phase |",
    )
    assert _pr_declares_cleanup_task(body) is True


def test_pr_declares_cleanup_task_not_detected():
    body = _valid_pr_body()
    assert _pr_declares_cleanup_task(body) is False


def test_pr_declares_scanner_phase_detected():
    body = _valid_pr_body().replace(
        "| Task type | governance-only |",
        "| Task type | scanner phase |",
    )
    assert _pr_declares_scanner_phase(body) is True


def test_pr_declares_scanner_phase_not_detected():
    body = _valid_pr_body()
    assert _pr_declares_scanner_phase(body) is False


# ---------------------------------------------------------------------------
# Full validate integration tests
# ---------------------------------------------------------------------------


def test_validate_with_forbidden_rewrite_fails():
    body = _valid_pr_body()
    changes = [
        gate.Change("M", "docs/CODEX_WORKFLOW.md"),
        gate.Change("A", "src/ml/predictor_v2.py"),
    ]
    errors = gate.validate(body, changes)
    assert any("Forbidden rewrite file pattern" in e for e in errors)


def test_validate_with_forbidden_claim_fails():
    body = _valid_pr_body() + "\nThis makes training unblocked.\n"
    changes = [gate.Change("M", "docs/CODEX_WORKFLOW.md")]
    errors = gate.validate(body, changes)
    assert any("training unblocked" in e for e in errors)


def test_validate_cleanup_with_deletions_passes():
    body = _valid_pr_body().replace(
        "| Task type | governance-only |",
        "| Task type | cleanup phase |",
    )
    changes = [
        gate.Change("D", "src/old_a.py"),
        gate.Change("D", "src/old_b.py"),
        gate.Change("D", "src/old_c.py"),
        gate.Change("M", "docs/CODEX_WORKFLOW.md"),
    ]
    errors = gate.validate(body, changes)
    assert not any("deletion" in e.lower() for e in errors)


def test_missing_sc002_status_in_validate_fails():
    body = _valid_pr_body().replace("## SC-002 status", "## Removed")
    changes: list[gate.Change] = []
    errors = gate.validate(body, changes)
    assert any("## SC-002 status" in e for e in errors)


def test_missing_remaining_risks_in_validate_fails():
    body = _valid_pr_body().replace("## Remaining risks", "## Removed")
    changes: list[gate.Change] = []
    errors = gate.validate(body, changes)
    assert any("## Remaining risks" in e for e in errors)


# ---------------------------------------------------------------------------
# Existing gates still enforced (regression)
# ---------------------------------------------------------------------------


def test_existing_sections_still_required():
    """New sections don't weaken existing requirements."""
    body = _valid_pr_body().replace("## Safety Impact", "")
    missing = gate.check_required_sections(body)
    assert "## Safety Impact" in missing


def test_existing_db_write_gate_still_enforced():
    """Safety consistency for DB paths still enforced."""
    body = _valid_pr_body().replace("| DB used | n/a |", "| DB used | no |")
    changed = {"database/migrations/v2.sql"}
    errors = gate.check_safety_consistency(body, changed)
    assert len(errors) >= 1
    assert "DB" in errors[0]


def test_existing_mixed_governance_business_still_fails():
    changed = {
        "AGENTS.md",
        "src/data/loader.py",
    }
    errors = gate.check_mixed_governance_business(changed)
    assert len(errors) >= 1


# ---------------------------------------------------------------------------
# Documentation / rule file compliance tests
# ---------------------------------------------------------------------------


def test_pr_template_exists():
    template = ROOT / ".github" / "pull_request_template.md"
    assert template.exists(), f"PR template missing: {template}"


def test_pr_template_contains_required_sections():
    template = ROOT / ".github" / "pull_request_template.md"
    body = template.read_text(encoding="utf-8")
    required = [
        "## Summary",
        "## Scope",
        "## Safety Impact",
        "## Validation",
        "## SC-002 status",
        "## Remaining risks",
        "## Next Recommended Task",
        "Agent Workflow Hardening Checklist",
    ]
    for section in required:
        assert section in body, f"PR template missing: {section}"


def test_claude_md_exists():
    claude_md = ROOT / "CLAUDE.md"
    assert claude_md.exists(), f"CLAUDE.md missing: {claude_md}"


def test_claude_md_contains_non_negotiable_rules():
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    required_rules = [
        "Never work directly on main",
        "SC-002 is partial mitigation",
        "Do not create V2 / FINAL / rewritten",
        "Post-merge main Production Gate must be green",
        "Do not run DB write scripts",
        "Do not run scraper / browser / Playwright",
    ]
    for rule in required_rules:
        assert rule.lower() in body.lower(), f"CLAUDE.md missing rule: {rule}"


def test_rules_doc_allowlist_not_safety_approval():
    """Rules must clearly state allowlist is not safety approval."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "not safety approval" in body or "not authorize execution" in body, (
        "Rules must state allowlist is not safety approval"
    )


def test_rules_doc_post_merge_gate_required():
    """Rules must state post-merge main Gate is required."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "post-merge main" in body.lower(), "Rules must require post-merge main Gate verification"


def test_rules_doc_no_main_direct_work():
    """Rules must explicitly prohibit direct work on main."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "never work directly on main" in body.lower(), "Rules must prohibit direct work on main"


def test_rules_doc_no_v2_rewritten_replacement():
    """Rules must explicitly prohibit V2/rewritten/replacement patterns."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "V2" in body, "Rules must prohibit V2 naming patterns"
    assert "rewritten" in body, "Rules must prohibit rewritten patterns"
    assert "replacement" in body, "Rules must prohibit replacement patterns"


def test_pr_template_checklist_contains_deletion_rule():
    template = ROOT / ".github" / "pull_request_template.md"
    body = template.read_text(encoding="utf-8")
    assert "I did not delete or move historical code" in body


# -- Relocated from test_ai_workflow_gate.py (file length limit) --


def test_clean_docs_file_passes():
    """Docs files are excluded from blind-spot scans (they document policy)."""
    changed = {"docs/CODEX_WORKFLOW.md"}
    errors = gate.check_dangerous_keywords_in_blind_spots(changed)
    assert errors == []
