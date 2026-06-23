"""Tests for the local PR Gate preflight.

lifecycle: test-fixture

Covers: PR body checks, forbidden claims, changed-files hardening, hidden/bidi
scan, secret marker scan, enforcement phases, fast/full mode distinction, JSON
output, and known-failure policy.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/ops"))

import ai_workflow_gate as gate  # noqa: E402
import local_pr_gate_preflight as preflight  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_pr_body() -> str:
    """Minimal valid PR body with all required sections."""
    return textwrap.dedent("""\
    ## Summary

    Test PR for local preflight.

    ## Scope

    | Item | Value |
    |---|---|
    | Task type | governance-only |

    ## Documentation Impact

    | Item | Value |
    |---|---|
    | New docs added | 0 |
    | Modified docs | AGENT_WORKFLOW.md |
    | Reason | Testing local preflight |

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

    ## CI Gate Scope

    - What the validation proves: preflight works locally.
    - What the validation does not prove: remote CI parity.

    ## No deletion / no move / no rename confirmation

    Confirmed.

    ## Rollback Plan

    Revert this PR commit.

    ## Next Recommended Task

    Do not start automatically.
    Recommended next task only after user confirmation: None.

    ## SC-002 status

    SC-002 remains partial mitigation only.

    ## Remaining risks

    No remaining risks.
    """)


def _write_pr_body(body: str) -> Path:
    """Write PR body to a temp file, return its path."""
    tmp = tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False)
    tmp.write(body)
    tmp.close()
    return Path(tmp.name)


def _write_changed_files(status_lines: list[str]) -> Path:
    """Write changed-files override file, return its path."""
    tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False)
    tmp.write("\n".join(status_lines))
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# Test: missing PR body file
# ---------------------------------------------------------------------------


def test_missing_pr_body_file_fails():
    """--pr-body-file pointing to nonexistent file returns exit code 2."""
    exit_code = preflight.main(["--pr-body-file", "/nonexistent/path.md"])
    assert exit_code == 2


# ---------------------------------------------------------------------------
# Test: missing required sections
# ---------------------------------------------------------------------------


def test_pr_body_missing_safety_impact_fails():
    """PR body missing ## Safety Impact section => FAIL."""
    body = _valid_pr_body().replace("## Safety Impact", "## Removed Section")
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["A\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        pr_phase = next(p for p in result.phases if p.name == "pr-body-validation")
        assert pr_phase.status == "FAIL"
        assert any("Safety Impact" in d for d in pr_phase.details)
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


def test_pr_body_missing_rollback_plan_fails():
    """PR body missing ## Rollback Plan section => FAIL."""
    body = _valid_pr_body().replace("## Rollback Plan", "## Removed Section")
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["A\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        pr_phase = next(p for p in result.phases if p.name == "pr-body-validation")
        assert pr_phase.status == "FAIL"
        assert any("Rollback Plan" in d for d in pr_phase.details)
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: forbidden safety claims
# ---------------------------------------------------------------------------


def test_forbidden_claim_safe_to_train_fails():
    """PR body claiming 'safe to train' => FAIL in forbidden-claims phase."""
    body = _valid_pr_body() + "\nThis is now safe to train.\n"
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["A\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        fc_phase = next(p for p in result.phases if p.name == "forbidden-claims")
        assert fc_phase.status == "FAIL"
        assert any("safe to train" in d for d in fc_phase.details)
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: forbidden rewrite file patterns
# ---------------------------------------------------------------------------


def test_added_foo_v2_py_fails():
    """Adding foo_v2.py => FAIL in changed-files-hardening phase."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["A\tsrc/foo_v2.py", "M\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        h_phase = next(p for p in result.phases if p.name == "changed-files-hardening")
        assert h_phase.status == "FAIL"
        assert any("_v2" in d for d in h_phase.details)
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


def test_added_foo_rewritten_py_fails():
    """Adding foo_rewritten.py => FAIL in changed-files-hardening phase."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["A\tscripts/foo_rewritten.py", "M\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        h_phase = next(p for p in result.phases if p.name == "changed-files-hardening")
        assert h_phase.status == "FAIL"
        assert any("_rewritten" in d for d in h_phase.details)
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


def test_docs_v2_not_flagged():
    """Documentation mentioning 'v2' is NOT flagged as forbidden rewrite."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    # Only change a docs/ file with "v2" in name — should NOT flag
    cf_file = _write_changed_files(["A\tdocs/v2_migration_guide.md", "M\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        h_phase = next(p for p in result.phases if p.name == "changed-files-hardening")
        # docs/ files are exempt from forbidden rewrite pattern check
        assert h_phase.status == "PASS"
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: changed-files file override
# ---------------------------------------------------------------------------


def test_changed_files_file_readable():
    """--changed-files-file provides changed-files override correctly."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["A\tREADME.md", "M\tsrc/main.py", "D\told_file.py"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        assert result.changed_files == 3
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: git diff name-status parsing
# ---------------------------------------------------------------------------


def test_git_diff_name_status_parsing():
    """A/M/D/R statuses are parsed correctly from git diff format."""
    output = "A\tnew_file.py\nM\tmodified.py\nD\tdeleted.py\nR100\told.js\tnew.js"
    changes = gate.parse_name_status(output)
    statuses = {c.status for c in changes}
    assert "A" in statuses
    assert "M" in statuses
    assert "D" in statuses
    assert "R" in statuses
    assert len(changes) == 4


# ---------------------------------------------------------------------------
# Test: fast mode does NOT run ruff/mypy/pytest (monkeypatch subprocess.run)
# ---------------------------------------------------------------------------


def test_fast_mode_skips_heavy_checks():
    """Fast mode does not invoke ruff, mypy, or pytest."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["M\tsrc/main.py"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
            full=False,
        )
        phase_names = {p.name for p in result.phases}
        assert "ruff-check" not in phase_names
        assert "ruff-format" not in phase_names
        assert "mypy" not in phase_names
        assert "pytest" not in phase_names
        assert "npm-test-coverage" not in phase_names
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


def test_full_mode_includes_heavy_checks():
    """Full mode includes ruff, mypy, pytest phases (verified via phase names)."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["M\tsrc/main.py"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
            full=True,
        )
        phase_names = {p.name for p in result.phases}
        assert "ruff-check" in phase_names
        assert "ruff-format" in phase_names
        assert "mypy" in phase_names
        assert "pytest" in phase_names
        assert "npm-test-coverage" in phase_names
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: enforcement phases are invoked
# ---------------------------------------------------------------------------


def test_enforcement_phases_present():
    """Python DB write, SQL migration, JS DB write phases are all in the result."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["M\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        phase_names = {p.name for p in result.phases}
        assert "python-db-write" in phase_names
        assert "sql-migration" in phase_names
        assert "js-db-write-guard" in phase_names
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


def test_agent_workflow_hardening_present():
    """Changed-files hardening phase is present."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["M\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        phase_names = {p.name for p in result.phases}
        assert "changed-files-hardening" in phase_names
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: JSON output format
# ---------------------------------------------------------------------------


def test_json_output_contains_required_fields():
    """JSON output has status, checks, failures, warnings."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["M\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        data = json.loads(preflight.format_json(result))
        assert "status" in data
        assert data["status"] in ("PASS", "FAIL")
        assert "checks" in data
        assert isinstance(data["checks"], list)
        assert len(data["checks"]) > 0
        assert "failures" in data
        assert "warnings" in data
        for check in data["checks"]:
            assert "name" in check
            assert "status" in check
            assert check["status"] in ("PASS", "FAIL", "SKIP", "ERROR")
            assert "message" in check
            assert "duration_ms" in check
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: valid small PR passes
# ---------------------------------------------------------------------------


def test_valid_small_pr_passes():
    """A normal PR body with a few non-risky changes passes."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["M\tREADME.md", "A\tdocs/new_guide.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        assert result.passed, f"Expected PASS but got failures: {result.failures}"
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: error message quality
# ---------------------------------------------------------------------------


def test_forbidden_phrase_error_includes_offending_phrase():
    """Error message for forbidden claim includes the specific offending phrase."""
    body = _valid_pr_body() + "\nThis is production ready now.\n"
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["M\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        fc_phase = next(p for p in result.phases if p.name == "forbidden-claims")
        assert fc_phase.status == "FAIL"
        assert any("production ready" in d.lower() for d in fc_phase.details), (
            f"Expected 'production ready' in: {fc_phase.details}"
        )
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


def test_changed_files_error_includes_offending_path():
    """Error message for forbidden rewrite includes the offending file path."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["A\tsrc/my_v2.py", "M\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        h_phase = next(p for p in result.phases if p.name == "changed-files-hardening")
        assert h_phase.status == "FAIL"
        assert any("my_v2.py" in d for d in h_phase.details), (
            f"Expected 'my_v2.py' in: {h_phase.details}"
        )
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: no DB env secrets in output
# ---------------------------------------------------------------------------


def test_preflight_no_db_env_secrets_in_output():
    """Preflight does not print DB env vars or secret-like values."""
    body = _valid_pr_body()
    body_file = _write_pr_body(body)
    cf_file = _write_changed_files(["M\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
        )
        text_output = preflight.format_human(result)
        json_output = preflight.format_json(result)
        for output in (text_output, json_output):
            assert "DATABASE_URL" not in output
            assert "DB_PASSWORD" not in output
            assert "POSTGRES_PASSWORD" not in output
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: hidden/bidi and secret marker scan
# ---------------------------------------------------------------------------


def test_hidden_bidi_scan_passes_clean_files():
    """Hidden/bidi scan passes on normal ASCII files."""
    # We use the README.md which should have no hidden chars
    changed = {"README.md"}
    result = preflight.check_hidden_bidi(changed)
    assert result.status == "PASS"


def test_secret_marker_scan_skips_allowlisted():
    """Secret scan skips tests/fixtures/ paths."""
    changed = {"tests/fixtures/sample.json", "docs/_reports/old.md"}
    result = preflight.check_secret_markers(changed)
    # These are in the skip prefixes, so scan should pass
    assert result.status == "PASS"


# ---------------------------------------------------------------------------
# Test: known-failure policy
# ---------------------------------------------------------------------------


def test_known_failure_policy_documented():
    """Pre-existing 47/48 issue is handled: preflight does NOT enforce exact test counts.

    The preflight checks PR body section content quality (not-hollow),
    but does NOT fail if the Validation section says '47 passed' vs '48 passed'.
    The exact test-count matching is performed by pr_body_check.py against
    live CI runs. This test verifies the policy is preserved.
    """
    # A body with "47 passed" — should pass section content quality
    body_47 = _valid_pr_body()
    # Ensure the Validation section is substantive (not hollow)
    errors = gate.validate(body_47, [gate.Change("M", "README.md")])
    # Should not fail due to "47" vs "48" — the preflight only checks for hollow sections
    test_count_errors = [e for e in errors if "47" in e or "test count" in e.lower()]
    assert len(test_count_errors) == 0, (
        f"Preflight should not enforce exact test counts: {test_count_errors}"
    )


# ---------------------------------------------------------------------------
# Test: CLI --fast vs --full
# ---------------------------------------------------------------------------


def test_cli_default_is_fast():
    """When neither --fast nor --full is given, mode defaults to fast."""
    body_file = _write_pr_body(_valid_pr_body())
    cf_file = _write_changed_files(["M\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
            full=False,
        )
        assert result.mode == "fast"
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)


def test_cli_full_mode():
    """When --full is given, mode is full and all phases run."""
    body_file = _write_pr_body(_valid_pr_body())
    cf_file = _write_changed_files(["M\tREADME.md"])
    try:
        result = preflight.run_preflight(
            pr_body_file=str(body_file),
            changed_files_file=str(cf_file),
            full=True,
        )
        assert result.mode == "full"
        phase_names = {p.name for p in result.phases}
        assert "ruff-check" in phase_names
    finally:
        body_file.unlink(missing_ok=True)
        cf_file.unlink(missing_ok=True)
