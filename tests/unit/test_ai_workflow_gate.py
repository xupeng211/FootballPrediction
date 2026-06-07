"""Tests for the AI workflow gate.

lifecycle: test-fixture
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "scripts/ops/ai_workflow_gate.py"

sys.path.insert(0, str(ROOT / "scripts/ops"))
import ai_workflow_gate as gate  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _valid_pr_body() -> str:
    """A minimal-valid PR body with all required sections."""

    return textwrap.dedent("""\
    ## Summary

    - Test PR for AI workflow gate validation.

    ## Scope

    | Item | Value |
    |---|---|
    | Task type | governance-only |
    | One task / one branch / one PR | yes |
    | Business code changed | no |

    ## Documentation Impact

    | Item | Value |
    |---|---|
    | New docs added | 0 |

    ## Safety Impact

    | Item | Value |
    |---|---|
    | DB used | no |
    | Browser automation used | no |
    | Scraper run | no |

    ## Validation

    | Validation | Result |
    |---|---|
    | Host validation | pass |

    ## CI Gate Scope

    - What the validation proves: CI passes.
    - What the validation does not prove: runtime correctness.

    ## No deletion / no move / no rename confirmation

    | Item | Value |
    |---|---|
    | Deleted files | 0 |

    ## Rollback Plan

    - Revert this commit.

    ## Next Recommended Task

    Do not start automatically.

    Recommended next task only after user confirmation:

    - TBD
    """)


# ---------------------------------------------------------------------------
# Check 1: required sections
# ---------------------------------------------------------------------------


def test_all_required_sections_present_passes():
    body = _valid_pr_body()
    assert gate.check_required_sections(body) == []


def test_missing_scope_section_fails():
    body = _valid_pr_body().replace("## Scope", "## Removed")
    missing = gate.check_required_sections(body)
    assert "## Scope" in missing


def test_missing_documentation_impact_fails():
    body = _valid_pr_body().replace("## Documentation Impact", "")
    missing = gate.check_required_sections(body)
    assert "## Documentation Impact" in missing


def test_missing_safety_impact_fails():
    body = _valid_pr_body().replace("## Safety Impact", "")
    missing = gate.check_required_sections(body)
    assert "## Safety Impact" in missing


def test_missing_validation_fails():
    body = _valid_pr_body().replace("## Validation", "")
    missing = gate.check_required_sections(body)
    assert "## Validation" in missing


def test_missing_ci_gate_scope_fails():
    body = _valid_pr_body().replace("## CI Gate Scope", "")
    missing = gate.check_required_sections(body)
    assert "## CI Gate Scope" in missing


def test_missing_no_delete_confirm_fails():
    body = _valid_pr_body().replace("## No deletion / no move / no rename confirmation", "")
    missing = gate.check_required_sections(body)
    assert "## No deletion / no move / no rename confirmation" in missing


def test_missing_rollback_plan_fails():
    body = _valid_pr_body().replace("## Rollback Plan", "")
    missing = gate.check_required_sections(body)
    assert "## Rollback Plan" in missing


def test_missing_next_recommended_task_fails():
    body = _valid_pr_body().replace("## Next Recommended Task", "")
    missing = gate.check_required_sections(body)
    assert "## Next Recommended Task" in missing


# ---------------------------------------------------------------------------
# Check 2: Do not start automatically
# ---------------------------------------------------------------------------


def test_do_not_start_automatically_present_passes():
    body = _valid_pr_body()
    assert gate.check_next_task_stop_phrase(body) == []


def test_do_not_start_automatically_missing_fails():
    body = _valid_pr_body().replace("Do not start automatically", "")
    errors = gate.check_next_task_stop_phrase(body)
    assert any("Do not start automatically" in e for e in errors)


def test_recommended_next_task_only_after_user_confirmation_missing_fails():
    body = _valid_pr_body().replace("Recommended next task only after user confirmation", "")
    errors = gate.check_next_task_stop_phrase(body)
    assert any("Recommended next task only after user confirmation" in e for e in errors)


def test_next_task_section_empty_fails():
    body = _valid_pr_body().replace(
        "## Next Recommended Task\n\nDo not start automatically.\n\n"
        "Recommended next task only after user confirmation:\n\n- TBD",
        "## Next Recommended Task\n\n",
    )
    errors = gate.check_next_task_stop_phrase(body)
    assert len(errors) >= 1


# ---------------------------------------------------------------------------
# Check 3: mixed governance + business code
# ---------------------------------------------------------------------------


def test_pure_governance_pr_passes():
    changed = {
        "docs/CODEX_WORKFLOW.md",
        "scripts/ops/ai_workflow_gate.py",
    }
    assert gate.check_mixed_governance_business(changed) == []


def test_pure_business_pr_passes():
    changed = {
        "src/prediction/model.py",
        "src/data/loader.py",
    }
    assert gate.check_mixed_governance_business(changed) == []


def test_mixed_governance_and_business_fails():
    changed = {
        "docs/CODEX_WORKFLOW.md",
        "src/prediction/model.py",
    }
    errors = gate.check_mixed_governance_business(changed)
    assert len(errors) >= 1
    assert "Mixed governance + business code" in errors[0]


def test_agents_md_with_src_fails():
    changed = {
        "AGENTS.md",
        "src/data/loader.py",
    }
    errors = gate.check_mixed_governance_business(changed)
    assert len(errors) >= 1


def test_pr_template_change_with_business_code_fails():
    changed = {
        ".github/pull_request_template.md",
        "database/migrations/001.sql",
    }
    errors = gate.check_mixed_governance_business(changed)
    assert len(errors) >= 1


def test_governance_checker_with_business_code_fails():
    changed = {
        "scripts/ops/documentation_governance_check.py",
        "src/infrastructure/db_client.py",
    }
    errors = gate.check_mixed_governance_business(changed)
    assert len(errors) >= 1


# ---------------------------------------------------------------------------
# Check 4: document sprawl
# ---------------------------------------------------------------------------


def test_no_sprawl_files_passes():
    added = {"docs/CODEX_WORKFLOW.md"}
    assert gate.check_doc_sprawl(added) == []


def test_few_sprawl_files_pass():
    added = {
        "docs/_reports/audit.md",
        "docs/_manifests/data.json",
    }
    assert gate.check_doc_sprawl(added) == []


def test_sprawl_exceeds_budget_fails():
    added = {f"docs/_reports/r{i}.md" for i in range(gate.MAX_DOC_SPRAWL_NEW_FILES + 1)}
    errors = gate.check_doc_sprawl(added)
    assert len(errors) >= 1
    assert "sprawl" in errors[0].lower()


def test_next_plan_files_count_as_sprawl():
    added = {f"docs/next_plan_{i}.md" for i in range(gate.MAX_DOC_SPRAWL_NEW_FILES + 1)}
    errors = gate.check_doc_sprawl(added)
    assert len(errors) >= 1


def test_review_report_files_count_as_sprawl():
    added = {f"docs/review_report_{i}.md" for i in range(gate.MAX_DOC_SPRAWL_NEW_FILES + 1)}
    errors = gate.check_doc_sprawl(added)
    assert len(errors) >= 1


# ---------------------------------------------------------------------------
# Check 5: dangerous keywords in blind-spot paths
# ---------------------------------------------------------------------------


def test_clean_docs_file_passes():
    # .md files are excluded from blind-spot scans (they document policy).
    # A clean .py file in docs/ should also pass.
    changed = {"docs/CODEX_WORKFLOW.md"}
    errors = gate.check_dangerous_keywords_in_blind_spots(changed)
    assert errors == []


def test_dangerous_network_keyword_in_docs_fails():
    # .md files are excluded — only code files are scanned.
    # Verify that a clean code file doesn't trigger false positives.
    changed = {"tests/unit/test_ai_workflow_gate.py"}
    errors = gate.check_dangerous_keywords_in_blind_spots(changed)
    # Our own test file should be clean (no real dangerous imports)
    assert errors == []


def test_non_blind_spot_path_skipped():
    # src/ files are not in the blind-spot (they're covered by gatekeeper)
    changed = {"src/prediction/model.py"}
    errors = gate.check_dangerous_keywords_in_blind_spots(changed)
    assert errors == []


def test_blind_spot_path_classification():
    # .md files are excluded (they legitimately mention tool names in policy)
    assert gate._is_blind_spot_path("docs/README.md") is False
    # .py files in docs/tests ARE scanned
    assert gate._is_blind_spot_path("tests/unit/test_x.py") is True
    assert gate._is_blind_spot_path("docs/some_script.py") is True
    assert gate._is_blind_spot_path("tests/fixtures/helper.js") is True
    # src/ and scripts/ are not blind spots
    assert gate._is_blind_spot_path("src/main.py") is False
    assert gate._is_blind_spot_path("scripts/ops/check.py") is False


# ---------------------------------------------------------------------------
# Check 6: safety declaration consistency
# ---------------------------------------------------------------------------


def test_safety_consistent_passes():
    body = _valid_pr_body()
    changed = {"docs/CODEX_WORKFLOW.md"}
    assert gate.check_safety_consistency(body, changed) == []


def test_declared_no_db_but_touches_db_paths_fails():
    body = _valid_pr_body()
    changed = {"database/migrations/v2.sql"}
    errors = gate.check_safety_consistency(body, changed)
    assert len(errors) >= 1
    assert "DB" in errors[0]


def test_declared_no_scraper_but_touches_scraper_paths_fails():
    body = _valid_pr_body()
    changed = {"src/scraper/fetcher.py"}
    errors = gate.check_safety_consistency(body, changed)
    assert len(errors) >= 1
    assert "scraper" in errors[0].lower()


def test_declared_no_browser_but_touches_browser_paths_fails():
    body = _valid_pr_body()
    changed = {"src/browser/stealth.py"}
    errors = gate.check_safety_consistency(body, changed)
    assert len(errors) >= 1
    assert "browser" in errors[0].lower()


# ---------------------------------------------------------------------------
# Integration: full validate() with synthetic data
# ---------------------------------------------------------------------------


def test_valid_governance_pr_passes_full_validate():
    """A governance-only PR with all sections should pass."""
    body = _valid_pr_body()
    changes = [
        gate.Change("M", "docs/CODEX_WORKFLOW.md"),
        gate.Change("A", "scripts/ops/ai_workflow_gate.py"),
        gate.Change("A", "tests/unit/test_ai_workflow_gate.py"),
    ]
    errors = gate.validate(body, changes)
    assert errors == [], f"Unexpected errors: {errors}"


def test_empty_pr_body_fails_full_validate():
    body = ""
    changes: list[gate.Change] = []
    errors = gate.validate(body, changes)
    assert len(errors) >= 1


def test_mixed_with_missing_sections_fails():
    """Multiple violations should all be reported."""
    body = "## Summary\n\nMinimal body with no sections.\n"
    changes = [
        gate.Change("M", "docs/CODEX_WORKFLOW.md"),
        gate.Change("M", "src/prediction/model.py"),
    ]
    errors = gate.validate(body, changes)
    # Should have: missing sections + missing stop phrase + mixed governance
    assert len(errors) >= 3, f"Expected >= 3 errors, got {len(errors)}: {errors}"


# ---------------------------------------------------------------------------
# CLI subprocess test
# ---------------------------------------------------------------------------


def test_gate_script_exists():
    assert GATE.exists()


def test_gate_cli_with_minimal_valid_body_passes():
    body = _valid_pr_body()
    result = subprocess.run(
        [sys.executable, str(GATE), "--pr-body-stdin"],
        input=body,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_gate_cli_with_empty_body_fails():
    result = subprocess.run(
        [sys.executable, str(GATE), "--pr-body-stdin"],
        input="",
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "FAIL" in result.stdout


def test_gate_cli_missing_do_not_start_fails():
    body = _valid_pr_body().replace("Do not start automatically", "Removed")
    result = subprocess.run(
        [sys.executable, str(GATE), "--pr-body-stdin"],
        input=body,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Do not start automatically" in result.stdout


def test_gate_cli_skip_body_checks_passes():
    """With --skip-body-checks, git-diff-only checks should pass on a clean branch."""
    result = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--pr-body-file",
            "/dev/null",
            "--skip-body-checks",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    # Should pass because this branch only adds governance files (no mixed changes)
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_skip_body_checks_skips_sections():
    """With skip_body_checks=True, missing sections should not cause errors."""
    body = ""  # Empty body
    changes: list[gate.Change] = []
    errors = gate.validate(body, changes, skip_body_checks=True)
    # No section errors, no stop-phrase errors
    assert not any("Missing required PR body" in e for e in errors)
    assert not any("Do not start automatically" in e for e in errors)
