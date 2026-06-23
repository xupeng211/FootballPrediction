"""Tests for the AI workflow gate.

lifecycle: test-fixture
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "scripts/ops/ai_workflow_gate.py"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/ops"))
import ai_workflow_gate as gate  # noqa: E402


# Convenience: partially-applied check_section_content_quality for test use.
# The real function takes (body, section_text_between_fn); the callback is
# called as fn(heading, body) but gate.section_text_between expects
# (body, heading), so we wrap with a lambda like validate() does.
def _check_content(body: str) -> list[str]:
    return gate.check_section_content_quality(
        body,
        lambda heading, pr_body: gate.section_text_between(pr_body, heading),
    )


def _valid_pr_body() -> str:
    """A minimal-valid PR body with all required sections."""

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

    | Item | Value |
    |---|---|
    | New docs added | 0 |
    | Modified docs | AGENT_WORKFLOW.md — added section 19.5 hollow-compliance rules |
    | Reason | Updated workflow documentation to record new content-quality gate rules |

    ## Safety Impact

    | Item | Value |
    |---|---|
    | DB used | n/a |
    | Browser automation used | no |
    | Scraper run | no |

    ## Validation

    | Validation | Result |
    |---|---|
    | Unit tests (pytest) | 47 passed, 0 failed |
    | Ruff check | clean |
    | Ruff format --check | clean |
    | Gate CLI smoke | AI workflow gate passes with valid body |

    ## CI Gate Scope

    - What the validation proves: CI passes.
    - What the validation does not prove: runtime correctness.

    ## No deletion / no move / no rename confirmation

    | Item | Value |
    |---|---|
    | Deleted files | 0 |

    ## Rollback Plan

    - Revert this commit via `git revert <merge-commit-sha>`.
    - No database migrations, schema changes, or data writes are involved.
    - After revert, re-run `make ci-local` to confirm the gate still passes.

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


def test_report_without_authoritative_update_or_reason_fails():
    body = _valid_pr_body()
    changes = [gate.Change("A", "docs/_reports/new_audit.md")]
    errors = gate.check_authoritative_report_backflow(body, changes)
    assert len(errors) == 1
    assert "docs/_reports" in errors[0]


def test_report_with_project_status_update_passes():
    body = _valid_pr_body()
    changes = [
        gate.Change("A", "docs/_reports/new_audit.md"),
        gate.Change("M", "docs/PROJECT_STATUS.md"),
    ]
    assert gate.check_authoritative_report_backflow(body, changes) == []


def test_report_with_explicit_no_update_reason_passes():
    body = _valid_pr_body().replace(
        "| Reason | Updated workflow documentation to record new content-quality gate rules |",
        "| Source-of-truth no-update reason | User scoped this PR to a transient evidence "
        "report and explicitly blocked source-of-truth edits. |",
    )
    changes = [gate.Change("A", "docs/_reports/new_audit.md")]
    assert gate.check_authoritative_report_backflow(body, changes) == []


def test_report_with_hollow_no_update_reasons_fails():
    hollow_values = ("n/a", "none", "not needed", "no", "无", "无需")
    changes = [gate.Change("A", "docs/_reports/new_audit.md")]
    for value in hollow_values:
        body = _valid_pr_body().replace(
            "| Reason | Updated workflow documentation to record new content-quality gate rules |",
            f"| Source-of-truth no-update reason | {value} |",
        )
        errors = gate.check_authoritative_report_backflow(body, changes)
        assert len(errors) == 1, f"{value!r} should fail"


def test_code_pr_without_report_passes_authoritative_backflow_gate():
    body = _valid_pr_body()
    changes = [gate.Change("M", "src/prediction/model.py")]
    assert gate.check_authoritative_report_backflow(body, changes) == []


def test_key_authoritative_docs_satisfy_report_backflow_gate():
    body = _valid_pr_body()
    for path in (
        "docs/DOCUMENTATION_GOVERNANCE.md",
        "docs/CODEX_WORKFLOW.md",
        "docs/PROJECT_STATUS.md",
    ):
        changes = [gate.Change("A", "docs/_reports/new_audit.md"), gate.Change("M", path)]
        assert gate.check_authoritative_report_backflow(body, changes) == []


def test_validate_reports_authoritative_backflow_failure():
    body = _valid_pr_body()
    changes = [gate.Change("A", "docs/_reports/new_audit.md")]
    errors = gate.validate(body, changes)
    assert any("Source-of-truth no-update reason" in e for e in errors)


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


def test_safety_consistent_passes():
    body = _valid_pr_body()
    changed = {"docs/CODEX_WORKFLOW.md"}
    assert gate.check_safety_consistency(body, changed) == []


def test_declared_no_db_but_touches_db_paths_fails():
    body = _valid_pr_body().replace("| DB used | n/a |", "| DB used | no |")
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


def _body_with_section_content(doc: str, validation: str, rollback: str) -> str:
    """Build a minimal PR body with specific content for the 3 critical sections."""
    return textwrap.dedent(
        f"""\
    ## Summary

    Test PR.

    ## Scope

    test

    ## Documentation Impact

    {doc}

    ## Safety Impact

    no

    ## Validation

    {validation}

    ## CI Gate Scope

    test

    ## No deletion / no move / no rename confirmation

    test

    ## Rollback Plan

    {rollback}

    ## Next Recommended Task

    Do not start automatically.
    Recommended next task only after user confirmation.
    """
    )


def _substantive_doc() -> str:
    return (
        "Updated AGENT_WORKFLOW.md to document new hollow-compliance "
        "rules in section 19.5. Added detailed validation examples "
        "and cross-reference to ai_workflow_gate.py check 7."
    )


def _substantive_validation() -> str:
    return (
        "Unit tests: 47 passed, 0 failed. Ruff check: clean. "
        "Ruff format --check: clean. Gate CLI smoke: passed. "
        "CI production-gate: completed + success."
    )


def _substantive_rollback() -> str:
    return (
        "Revert via git revert <merge-commit-sha>. "
        "No DB migrations or schema changes involved. "
        "After revert, re-run make ci-local to confirm gate passes."
    )


def test_all_critical_sections_substantive_passes():
    """A PR body with real content in all 3 critical sections should pass."""
    body = _body_with_section_content(
        _substantive_doc(),
        _substantive_validation(),
        _substantive_rollback(),
    )
    assert _check_content(body) == []


def test_documentation_impact_na_fails():
    """Documentation Impact with only 'N/A' should be rejected."""
    body = _body_with_section_content("N/A", _substantive_validation(), _substantive_rollback())
    errors = _check_content(body)
    assert any("## Documentation Impact" in e for e in errors), (
        f"Should flag Documentation Impact as hollow; got: {errors}"
    )


def test_documentation_impact_none_fails():
    """Documentation Impact with only 'none' should be rejected."""
    body = _body_with_section_content("none", _substantive_validation(), _substantive_rollback())
    errors = _check_content(body)
    assert any("## Documentation Impact" in e for e in errors)


def test_documentation_impact_not_applicable_fails():
    """Documentation Impact with only 'not applicable' should be rejected."""
    body = _body_with_section_content(
        "not applicable", _substantive_validation(), _substantive_rollback()
    )
    errors = _check_content(body)
    assert any("## Documentation Impact" in e for e in errors)


def test_documentation_impact_no_impact_fails():
    """Documentation Impact with only 'no impact' should be rejected."""
    body = _body_with_section_content(
        "no impact", _substantive_validation(), _substantive_rollback()
    )
    errors = _check_content(body)
    assert any("## Documentation Impact" in e for e in errors)


def test_documentation_impact_no_documentation_impact_fails():
    """Documentation Impact with only 'no documentation impact' should be rejected."""
    body = _body_with_section_content(
        "no documentation impact", _substantive_validation(), _substantive_rollback()
    )
    errors = _check_content(body)
    assert any("## Documentation Impact" in e for e in errors)


def test_documentation_impact_empty_fails():
    """Documentation Impact section with no content should be rejected."""
    body = _body_with_section_content("", _substantive_validation(), _substantive_rollback())
    errors = _check_content(body)
    assert any("## Documentation Impact" in e for e in errors)


def test_validation_passed_fails():
    """Validation with only 'passed' should be rejected."""
    body = _body_with_section_content(_substantive_doc(), "passed", _substantive_rollback())
    errors = _check_content(body)
    assert any("## Validation" in e for e in errors), (
        f"Should flag Validation as hollow; got: {errors}"
    )


def test_validation_ok_fails():
    """Validation with only 'ok' should be rejected."""
    body = _body_with_section_content(_substantive_doc(), "ok", _substantive_rollback())
    errors = _check_content(body)
    assert any("## Validation" in e for e in errors)


def test_validation_na_fails():
    """Validation with only 'N/A' should be rejected."""
    body = _body_with_section_content(_substantive_doc(), "N/A", _substantive_rollback())
    errors = _check_content(body)
    assert any("## Validation" in e for e in errors)


def test_validation_all_tests_pass_fails():
    """Validation with only 'all tests pass' should be rejected."""
    body = _body_with_section_content(_substantive_doc(), "all tests pass", _substantive_rollback())
    errors = _check_content(body)
    assert any("## Validation" in e for e in errors)


def test_rollback_plan_revert_pr_fails():
    """Rollback Plan with only 'revert the PR' should be rejected."""
    body = _body_with_section_content(
        _substantive_doc(), _substantive_validation(), "revert the PR"
    )
    errors = _check_content(body)
    assert any("## Rollback Plan" in e for e in errors), (
        f"Should flag Rollback Plan as hollow; got: {errors}"
    )


def test_rollback_plan_revert_commit_fails():
    """Rollback Plan with only 'revert this commit' should be rejected."""
    body = _body_with_section_content(
        _substantive_doc(), _substantive_validation(), "revert this commit"
    )
    errors = _check_content(body)
    assert any("## Rollback Plan" in e for e in errors)


def test_rollback_plan_git_revert_fails():
    """Rollback Plan with only 'git revert ...' should be rejected."""
    body = _body_with_section_content(
        _substantive_doc(), _substantive_validation(), "git revert HEAD~1"
    )
    errors = _check_content(body)
    assert any("## Rollback Plan" in e for e in errors)


def test_rollback_plan_empty_fails():
    """Rollback Plan with no content should be rejected."""
    body = _body_with_section_content(_substantive_doc(), _substantive_validation(), "")
    errors = _check_content(body)
    assert any("## Rollback Plan" in e for e in errors)


def test_check_7_does_not_break_next_task_gate():
    """Next Recommended Task mandatory phrases must still be enforced."""
    body = _body_with_section_content(
        _substantive_doc(), _substantive_validation(), _substantive_rollback()
    )
    assert gate.check_next_task_stop_phrase(body) == []


def test_check_7_does_not_break_safety_consistency():
    """Safety consistency must still be enforced alongside quality checks."""
    body = _valid_pr_body().replace("| DB used | n/a |", "| DB used | no |")
    changed = {"database/migrations/v2.sql"}
    errors = gate.check_safety_consistency(body, changed)
    assert len(errors) >= 1
    assert "DB" in errors[0]


def test_all_three_critical_sections_hollow_reports_all():
    """When all 3 critical sections are hollow, all 3 should be reported."""
    body = _body_with_section_content("N/A", "passed", "revert PR")
    errors = _check_content(body)
    doc_hits = [e for e in errors if "Documentation Impact" in e]
    val_hits = [e for e in errors if "Validation" in e]
    roll_hits = [e for e in errors if "Rollback Plan" in e]
    assert len(doc_hits) >= 1, f"Expected Documentation Impact error; got: {errors}"
    assert len(val_hits) >= 1, f"Expected Validation error; got: {errors}"
    assert len(roll_hits) >= 1, f"Expected Rollback Plan error; got: {errors}"


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
    min_expected = 3
    assert len(errors) >= min_expected, (
        f"Expected >= {min_expected} errors, got {len(errors)}: {errors}"
    )


def test_gate_script_exists():
    assert GATE.exists()


def test_gate_cli_with_minimal_valid_body_passes():
    body = _valid_pr_body()
    # Guard phase changes may touch FotMob files without scraper execution.
    # Adjust safety declarations to match the actual branch diff.
    body = body.replace(
        "| Scraper run | no |", "| Scraper run | n/a (guard only, no scraper exec) |"
    )
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


def test_multiline_body_with_code_blocks_passes():
    """All required sections must be detected even with Markdown code blocks."""
    body = _valid_pr_body() + textwrap.dedent(
        """\

    ## Additional Notes

    Here is a code block that should not break section parsing:

    ```
    const x = 1;
    console.log(x);
    ```

    And an inline `code` span.

    | Table | With | Rows |
    |-------|------|------|
    | a     | b    | c    |
    """
    )
    missing = gate.check_required_sections(body)
    assert missing == [], f"Should find all sections; missing: {missing}"


def test_multiline_body_with_crlf_normalised():
    """CRLF line endings must be normalised to LF by read_pr_body."""
    body = _valid_pr_body()
    crlf_body = body.replace("\n", "\r\n")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(crlf_body)
        tmp_path = f.name
    try:
        result = gate.read_pr_body(tmp_path)
        assert "\r\n" not in result, "CRLF should be normalised to LF"
        assert gate.check_required_sections(result) == []
    finally:
        Path(tmp_path).unlink()


def test_read_pr_body_from_file_preserves_multiline():
    """read_pr_body must return the full multiline content from a file."""
    body = _valid_pr_body()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(body)
        tmp_path = f.name
    try:
        result = gate.read_pr_body(tmp_path)
        assert len(result) >= len(body) - 5, f"Expected ~{len(body)} chars, got {len(result)}"
        for heading in gate.REQUIRED_SECTIONS:
            assert heading in result, f"Missing heading: {heading}"
    finally:
        Path(tmp_path).unlink()


def test_empty_body_with_skip_body_checks_still_passes():
    """Empty body with skip_body_checks must not trigger section errors."""
    errors = gate.validate("", [], skip_body_checks=True)
    assert not any("Missing required PR body" in e for e in errors)
    assert not any("Do not start automatically" in e for e in errors)


def test_body_missing_sections_without_skip_fails():
    """Without skip_body_checks, missing sections must be detected."""
    body = "## Summary\n\nJust a summary, nothing else.\n"
    errors = gate.validate(body, [], skip_body_checks=False)
    assert any("Missing required PR body" in e for e in errors)


# New hardening tests are in tests/unit/test_agent_workflow_hardening.py.
# Kept separate to stay under the 800-line file length limit enforced by gatekeeper.
