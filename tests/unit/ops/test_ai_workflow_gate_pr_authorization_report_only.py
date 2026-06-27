"""Tests for report-only PR authorization matrix wiring in AI Workflow Gate.

lifecycle: test-fixture

Validates that:
  - report-only matrix findings are printed but never added to blocking errors
  - the gate validate() returns same errors with or without matrix findings
  - matrix exceptions are printed but don't crash the gate
  - existing gate errors remain blocking
"""

from __future__ import annotations

import io
from pathlib import Path
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))

# Import gate functions after path setup — only need _print_matrix_result from gate,
# but since it's now in the helper, import from there
from helpers.pr_authorization_matrix import (  # noqa: E402
    TASK_TYPE_DOCS_ONLY,
    TASK_TYPE_UNKNOWN,
    _print_matrix_result,
    run_pr_authorization_matrix_report_only,
    validate_authorization,
)

sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from ai_workflow_gate import Change, validate  # noqa: E402

# ---------------------------------------------------------------------------
# run_pr_authorization_matrix_report_only — basic behaviour
# ---------------------------------------------------------------------------


def test_report_only_prints_but_does_not_raise():
    """Report-only should run without exception on valid input."""
    pr_body = textwrap.dedent("""\
        ## Scope
        | Task type | docs-only |
    """)
    changed = {"docs/readme.md"}
    # Should not raise
    run_pr_authorization_matrix_report_only(changed, pr_body)


def test_report_only_does_nothing_on_empty_input():
    """Empty changed or PR body should be a no-op."""
    # Empty changed
    run_pr_authorization_matrix_report_only(set(), "some body")
    # Empty body
    run_pr_authorization_matrix_report_only({"docs/x.md"}, "")
    # Both empty
    run_pr_authorization_matrix_report_only(set(), "")


def test_report_only_prints_task_type_and_categories():
    """Report-only output should include task type and detected categories."""
    pr_body = textwrap.dedent("""\
        ## Scope
        | Task type | source-code |
    """)
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        run_pr_authorization_matrix_report_only(
            {"src/foo.py", "tests/unit/bar.py", "docs/x.md"}, pr_body
        )
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "task_type=source-code" in output
    assert "source" in output or "categories" in output


def test_report_only_prints_matrix_errors_without_blocking():
    """When matrix finds errors, they should be printed but NOT in error list."""
    pr_body = textwrap.dedent("""\
        ## Scope
        | Task type | docs-only |
    """)
    # docs-only PR touching src/ — matrix should flag this
    changed = {"docs/readme.md", "src/foo.py"}

    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        run_pr_authorization_matrix_report_only(changed, pr_body)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "[PR Authorization Matrix][report-only][error]" in output
    assert "matrix errors are currently non-blocking" in output.lower()


def test_report_only_docker_deploy_with_auth_passes():
    """Docker-deploy with proper dangerous auth should show pass."""
    pr_body = textwrap.dedent("""\
        ## Scope
        | Task type | docker-deploy |

        ## Dangerous File Authorization

        User authorized changes to docker-compose.yml.
        Rollback: revert the PR.
    """)
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        run_pr_authorization_matrix_report_only({"docker-compose.yml"}, pr_body)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "task_type=docker-deploy" in output
    assert "Dangerous" in output


def test_report_only_unknown_task_type_shows_warning():
    """Unknown task type should produce a warning but not crash."""
    pr_body = textwrap.dedent("""\
        ## Scope
        No task type declared.
    """)
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        run_pr_authorization_matrix_report_only({"docs/x.md"}, pr_body)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "unknown" in output.lower()


def test_report_only_without_pr_body_is_no_op():
    """Empty PR body means no task type parsing — should not crash."""
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        run_pr_authorization_matrix_report_only({"docs/x.md"}, "")
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    # No output expected for empty body
    assert output == ""


def test_report_only_prints_non_blocking_message():
    """Every report-only run should print the non-blocking disclaimer."""
    pr_body = textwrap.dedent("""\
        ## Scope
        | Task type | test-only |
    """)
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        run_pr_authorization_matrix_report_only({"tests/unit/x.py"}, pr_body)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "non-blocking" in output.lower()


# ---------------------------------------------------------------------------
# Integration: validate() does NOT add matrix errors to gate errors
# ---------------------------------------------------------------------------


def test_validate_matrix_errors_not_in_gate_errors():
    """Even when matrix finds errors, validate() must not include them."""
    pr_body = textwrap.dedent("""\
        ## Summary
        Fix a bug

        ## Scope
        | Task type | docs-only |

        ## Documentation Impact
        | Item | Value |
        |---|---|
        | Source-of-truth docs updated | no |
        | If not updated, explicit reason | This is a test PR with no real doc impact. |

        ## Safety Impact
        | Item | Value |
        |---|---|
        | Existing files deleted | 0 |
        | Existing files moved | 0 |
        | Existing files renamed | 0 |

        ## Validation
        | Validation | Result |
        |---|---|
        | Host validation | passed |

        ## CI Gate Scope
        - What the validation proves: nothing
        - What the validation does not prove: everything

        ## No deletion / no move / no rename confirmation
        | Item | Value |
        |---|---|
        | Deleted files | 0 |
        | Moved files | 0 |
        | Renamed files | 0 |

        ## Rollback Plan
        Revert the merge commit.

        ## Next Recommended Task
        Do not start automatically.
        Recommended next task only after user confirmation.

        ## SC-002 status
        SC-002 is partial mitigation only.
        This PR does not change SC-002 guard coverage.
    """)
    # docs-only PR but touches src — matrix should flag, gate should NOT include
    changes_list = [
        Change("M", "docs/readme.md"),
        Change("M", "src/foo.py"),
    ]
    captured = io.StringIO()
    old_stdout = sys.stdout
    errors = []
    try:
        sys.stdout = captured
        errors = validate(pr_body, changes_list)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    # Matrix should have printed errors (docs-only touching src)
    assert "[PR Authorization Matrix][report-only][error]" in output
    # But validate() errors should NOT contain matrix errors
    matrix_errors_in_return = any("matrix" in e.lower() or "PR Authorization" in e for e in errors)
    assert not matrix_errors_in_return, f"Matrix errors leaked into gate errors: {errors}"


def test_validate_matrix_positive_passes_normally():
    """Valid matrix input should not affect gate errors list at all."""
    pr_body = textwrap.dedent("""\
        ## Summary
        Doc update

        ## Scope
        | Task type | docs-only |

        ## Documentation Impact
        | Item | Value |
        |---|---|
        | Source-of-truth docs updated | no |
        | If not updated, explicit reason | Test-only PR, no real documentation impact. |

        ## Safety Impact
        | Item | Value |
        |---|---|
        | Existing files deleted | 0 |
        | Existing files moved | 0 |
        | Existing files renamed | 0 |

        ## Validation
        | Validation | Result |
        |---|---|
        | Host validation | n/a |
        | Container validation | n/a |

        ## CI Gate Scope
        - What the validation proves: nothing
        - What the validation does not prove: nothing

        ## No deletion / no move / no rename confirmation
        | Item | Value |
        |---|---|
        | Deleted files | 0 |
        | Moved files | 0 |
        | Renamed files | 0 |

        ## Rollback Plan
        Revert the merge commit.

        ## Next Recommended Task
        Do not start automatically.
        Recommended next task only after user confirmation.

        ## SC-002 status
        SC-002 is partial mitigation only.
        This PR does not change SC-002 guard coverage.
    """)
    changes_list = [
        Change("M", "docs/readme.md"),
    ]
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        _ = validate(pr_body, changes_list)
    finally:
        sys.stdout = old_stdout

    # No body-check errors expected for a complete PR body
    output = captured.getvalue()
    assert "[PR Authorization Matrix][report-only]" in output
    # Matrix should pass (docs-only with docs files)
    assert "matrix validation result: pass" in output.lower()


def test_validate_skip_body_checks_skips_matrix():
    """When skip_body_checks=True, matrix should not run."""
    pr_body = textwrap.dedent("""\
        ## Scope
        | Task type | docs-only |
    """)
    changes_list = [Change("M", "src/foo.py")]
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        validate(pr_body, changes_list, skip_body_checks=True)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "[PR Authorization Matrix]" not in output


def test_existing_gate_errors_still_blocking():
    """When validate() finds real errors (not matrix), they must still appear."""
    pr_body = textwrap.dedent("""\
        ## Scope
        | Task type | docs-only |
    """)
    # Missing many required sections
    changes_list = [Change("M", "docs/x.md")]
    errors = validate(pr_body, changes_list)
    # Should have body-check errors (missing required sections)
    assert len(errors) > 0, "Expected gate body-check errors for incomplete PR body"


# ---------------------------------------------------------------------------
# Exception safety
# ---------------------------------------------------------------------------


def test_report_only_survives_helper_exception():
    """If the helper raises, report-only should catch and print it."""

    def _raise(*_a, **_kw):
        raise RuntimeError("simulated helper crash")

    import helpers.pr_authorization_matrix as _mod  # noqa: PLC0415

    _original = _mod.validate_authorization
    _mod.validate_authorization = _raise
    try:
        pr_body = textwrap.dedent("""\
            ## Scope
            | Task type | docs-only |
        """)
        captured = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = captured
            run_pr_authorization_matrix_report_only({"docs/x.md"}, pr_body)
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        assert "[internal-error]" in output.lower()
        assert "non-blocking" in output.lower()
    finally:
        _mod.validate_authorization = _original


def test_matrix_internal_error_does_not_affect_validate_errors():
    """Even if helper crashes inside validate(), gate errors are unaffected."""

    def _raise(*_a, **_kw):
        raise RuntimeError("simulated helper crash")

    import helpers.pr_authorization_matrix as _mod  # noqa: PLC0415

    import scripts.ops.helpers.pr_authorization_matrix as _mod_full  # noqa: PLC0415

    _original = _mod.validate_authorization
    _original_full = _mod_full.validate_authorization
    _mod.validate_authorization = _raise
    _mod_full.validate_authorization = _raise
    try:
        pr_body = textwrap.dedent("""\
            ## Summary
            Test

            ## Scope
            | Task type | docs-only |

            ## Documentation Impact
            | Item | Value |
            |---|---|
            | Source-of-truth docs updated | no |
            | If not updated, explicit reason | Test-only PR body for exception testing. |

            ## Safety Impact
            | Item | Value |
            |---|---|
            | Existing files deleted | 0 |
            | Existing files moved | 0 |
            | Existing files renamed | 0 |

            ## Validation
            | Validation | Result |
            |---|---|
            | Host validation | n/a |
            | Container validation | n/a |

            ## CI Gate Scope
            - What the validation proves: nothing
            - What the validation does not prove: nothing

            ## No deletion / no move / no rename confirmation
            | Item | Value |
            |---|---|
            | Deleted files | 0 |
            | Moved files | 0 |
            | Renamed files | 0 |

            ## Rollback Plan
            Revert the merge commit.

            ## Next Recommended Task
            Do not start automatically.
            Recommended next task only after user confirmation.

            ## SC-002 status
            SC-002 is partial mitigation only.
            This PR does not change SC-002 guard coverage.
        """)
        changes_list = [Change("M", "docs/x.md")]
        captured = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = captured
            errors = validate(pr_body, changes_list)
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        assert "[internal-error]" in output.lower()
        # Gate errors should NOT contain matrix errors
        matrix_refs = any("[PR Authorization Matrix]" in e or "matrix" in e.lower() for e in errors)
        assert not matrix_refs, f"Matrix errors leaked: {errors}"
    finally:
        _mod.validate_authorization = _original
        _mod_full.validate_authorization = _original_full


# ---------------------------------------------------------------------------
# _print_matrix_result direct tests
# ---------------------------------------------------------------------------


def test_print_matrix_result_valid():
    """Print a valid result — should show pass."""
    result = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        ["docs/readme.md"],
        pr_body="| Task type | docs-only |",
    )
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        _print_matrix_result(result)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "task_type=docs-only" in output
    assert "non-blocking" in output.lower()


def test_print_matrix_result_invalid():
    """Print a failing result — should show errors and non-blocking message."""
    result = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        ["src/foo.py"],
        pr_body="| Task type | docs-only |",
    )
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        _print_matrix_result(result)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "[error]" in output
    assert "non-blocking" in output.lower()


def test_print_matrix_result_unknown():
    """Print unknown task type result — should show warning."""
    result = validate_authorization(
        TASK_TYPE_UNKNOWN,
        ["docs/readme.md"],
        pr_body="",
    )
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        _print_matrix_result(result)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "[warning]" in output
    assert "unknown" in output.lower()
