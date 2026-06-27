"""Tests for optional --block-matrix flag in AI Workflow Gate.

lifecycle: test-fixture

Validates that:
  - default (block_matrix=False) does NOT add matrix errors to gate errors
  - block_matrix=True adds ONLY narrow A-D subset to errors
  - unknown path category is NOT blocked even with block_matrix=True
  - high-risk without Dangerous File Authorization is NOT in narrow subset
  - helper narrow_blocking_errors returns correct errors for each A-D rule
"""

from __future__ import annotations

import io
from pathlib import Path
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))

from helpers.pr_authorization_matrix import (  # noqa: E402
    TASK_TYPE_DOCS_ONLY,
    TASK_TYPE_SOURCE_CODE,
    TASK_TYPE_TEST_ONLY,
    TASK_TYPE_UNKNOWN,
    TASK_TYPE_WORKFLOW_GOVERNANCE,
    narrow_blocking_errors,
    validate_authorization,
)

sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from ai_workflow_gate import Change, validate  # noqa: E402

# ---------------------------------------------------------------------------
# narrow_blocking_errors — unit tests for the pure selector
# ---------------------------------------------------------------------------


def test_narrow_blocking_unknown_task_type():
    result = validate_authorization(TASK_TYPE_UNKNOWN, ["docs/x.md"], pr_body="")
    errors = narrow_blocking_errors(result)
    assert len(errors) >= 1
    assert any("unknown task type" in e.lower() for e in errors)


def test_narrow_blocking_env_secret():
    result = validate_authorization(
        TASK_TYPE_DOCS_ONLY, [".env"], pr_body="| Task type | docs-only |"
    )
    errors = narrow_blocking_errors(result)
    assert len(errors) >= 1
    assert any("env-secret" in e.lower() for e in errors)


def test_narrow_blocking_docs_only_touching_src():
    result = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        ["docs/x.md", "src/foo.py"],
        pr_body="| Task type | docs-only |",
    )
    errors = narrow_blocking_errors(result)
    assert len(errors) >= 1
    assert any("docs-only" in e.lower() and "source" in e.lower() for e in errors)


def test_narrow_blocking_test_only_touching_src():
    result = validate_authorization(
        TASK_TYPE_TEST_ONLY,
        ["tests/x.py", "src/foo.py"],
        pr_body="| Task type | test-only |",
    )
    errors = narrow_blocking_errors(result)
    assert len(errors) >= 1
    assert any("test-only" in e.lower() and "source" in e.lower() for e in errors)


def test_narrow_blocking_excludes_full_result_errors():
    """narrow_blocking_errors must not return all result.errors — only A-D."""
    # A docs-only PR touching src and missing dangerous auth — result has multiple errors
    result = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        ["docs/x.md", "src/foo.py"],
        pr_body="| Task type | docs-only |",
    )
    # result.errors has the "docs-only allows only" error from full matrix
    # but narrow_blocking_errors should only return the A-D subset
    errors = narrow_blocking_errors(result)
    # Must contain the docs+touching src blocking error
    assert any("docs-only" in e.lower() for e in errors)
    # Must NOT contain dangerous-auth errors (not in A-D subset)
    for e in errors:
        assert "dangerous file authorization" not in e.lower(), (
            f"Narrow blocking leaked non-A-D error: {e}"
        )


def test_narrow_blocking_does_not_block_unknown_category():
    """Unknown path category must never produce narrow blocking errors."""
    # Source-code task with src file + unknown category from CI transient
    result = validate_authorization(
        TASK_TYPE_SOURCE_CODE,
        ["src/foo.py", ".eslintcache"],
        pr_body="| Task type | source-code |",
    )
    # Matrix may have errors/warnings about unknown, but narrow should not flag it
    errors = narrow_blocking_errors(result)
    # No errors expected — source-code + src is valid, .eslintcache is unknown-excluded
    assert len(errors) == 0, f"Unexpected narrow blocking errors: {errors}"


def test_narrow_blocking_excludes_high_risk_no_auth():
    """workflow-governance without Dangerous File Auth is NOT in A-D subset."""
    result = validate_authorization(
        TASK_TYPE_WORKFLOW_GOVERNANCE,
        ["scripts/ops/ai_workflow_gate.py"],
        pr_body="| Task type | workflow-governance |",
    )
    errors = narrow_blocking_errors(result)
    # No A-D rule matches — workflow-governance with its own category is valid here
    assert len(errors) == 0, f"Unexpected narrow blocking errors: {errors}"


def test_narrow_blocking_valid_input_returns_empty():
    result = validate_authorization(
        TASK_TYPE_SOURCE_CODE,
        ["src/foo.py", "tests/unit/bar.py"],
        pr_body="| Task type | source-code |",
    )
    assert narrow_blocking_errors(result) == ()


# ---------------------------------------------------------------------------
# validate() with block_matrix flag — integration tests
# ---------------------------------------------------------------------------


def _complete_pr_body(task_type: str = "docs-only") -> str:
    """Return a minimal but complete PR body that passes body checks."""
    return textwrap.dedent(f"""\
        ## Summary
        Test PR.

        ## Scope
        | Task type | {task_type} |

        ## Documentation Impact
        | Item | Value |
        |---|---|
        | Source-of-truth docs updated | no |
        | If not updated, explicit reason | Test-only PR body, no real documentation impact to explain. |

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
        - What the validation proves: nothing in this test.
        - What the validation does not prove: nothing in this test.

        ## No deletion / no move / no rename confirmation
        | Item | Value |
        |---|---|
        | Deleted files | 0 |
        | Moved files | 0 |
        | Renamed files | 0 |

        ## Rollback Plan
        Revert the merge commit. This is a test PR with no persistence impact.

        ## Next Recommended Task
        Do not start automatically.
        Recommended next task only after user confirmation.

        ## SC-002 status
        SC-002 is partial mitigation only.
        This PR does not change SC-002 guard coverage.
    """)


def test_validate_default_off_does_not_block_unknown_task_type():
    """block_matrix=False: unknown task type does NOT produce gate errors."""
    body = _complete_pr_body("non-existent-type")
    changes_list = [Change("M", "docs/x.md")]
    errors = validate(body, changes_list, block_matrix=False)
    # No matrix blocking errors expected
    matrix_errors = [e for e in errors if "matrix" in e.lower()]
    assert len(matrix_errors) == 0, f"Default-off leaked matrix errors: {matrix_errors}"


def test_validate_default_off_does_not_block_env_secret():
    """block_matrix=False: env-secret does NOT produce gate errors from matrix."""
    body = _complete_pr_body("docs-only")
    changes_list = [Change("M", ".env")]
    errors = validate(body, changes_list, block_matrix=False)
    matrix_errors = [e for e in errors if "authorization matrix" in e.lower()]
    assert len(matrix_errors) == 0, f"Default-off leaked matrix errors: {matrix_errors}"


def test_validate_block_matrix_on_blocks_unknown_task_type():
    """block_matrix=True: unknown task type IS a blocking error."""
    body = _complete_pr_body("non-existent-type")
    changes_list = [Change("M", "docs/x.md")]
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        errors = validate(body, changes_list, block_matrix=True)
    finally:
        sys.stdout = old_stdout

    matrix_errors = [e for e in errors if "authorization matrix" in e.lower()]
    assert any("unknown task type" in e.lower() for e in matrix_errors), (
        f"Expected unknown task type blocking error, got: {matrix_errors}"
    )


def test_validate_block_matrix_on_blocks_env_secret():
    """block_matrix=True: env-secret IS a blocking error."""
    body = _complete_pr_body("source-code")
    changes_list = [Change("M", ".env")]
    errors = validate(body, changes_list, block_matrix=True)
    matrix_errors = [e for e in errors if "authorization matrix" in e.lower()]
    assert any("env-secret" in e.lower() for e in matrix_errors), (
        f"Expected env-secret blocking error, got: {matrix_errors}"
    )


def test_validate_block_matrix_on_blocks_docs_only_with_src():
    """block_matrix=True: docs-only touching src IS a blocking error."""
    body = _complete_pr_body("docs-only")
    changes_list = [Change("M", "docs/x.md"), Change("M", "src/foo.py")]
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        errors = validate(body, changes_list, block_matrix=True)
    finally:
        sys.stdout = old_stdout

    matrix_errors = [e for e in errors if "authorization matrix" in e.lower()]
    assert any("docs-only" in e.lower() and "source" in e.lower() for e in matrix_errors), (
        f"Expected docs-only blocking error, got: {matrix_errors}"
    )


def test_validate_block_matrix_on_blocks_test_only_with_src():
    """block_matrix=True: test-only touching src IS a blocking error."""
    body = _complete_pr_body("test-only")
    changes_list = [Change("M", "tests/x.py"), Change("M", "src/foo.py")]
    errors = validate(body, changes_list, block_matrix=True)
    matrix_errors = [e for e in errors if "authorization matrix" in e.lower()]
    assert any("test-only" in e.lower() and "source" in e.lower() for e in matrix_errors), (
        f"Expected test-only blocking error, got: {matrix_errors}"
    )


def test_validate_block_matrix_on_does_not_block_unknown_category():
    """block_matrix=True: unknown path category is NOT blocked."""
    body = _complete_pr_body("source-code")
    changes_list = [Change("M", "src/foo.py"), Change("M", ".eslintcache")]
    errors = validate(body, changes_list, block_matrix=True)
    matrix_errors = [e for e in errors if "authorization matrix" in e.lower()]
    assert len(matrix_errors) == 0, f"Unknown category should not block, got: {matrix_errors}"


def test_validate_block_matrix_on_does_not_block_high_risk_no_auth():
    """block_matrix=True: high-risk without Dangerous Auth is NOT in narrow subset."""
    body = _complete_pr_body("workflow-governance")
    changes_list = [Change("M", "scripts/ops/ai_workflow_gate.py")]
    errors = validate(body, changes_list, block_matrix=True)
    matrix_errors = [e for e in errors if "authorization matrix" in e.lower()]
    assert len(matrix_errors) == 0, (
        f"High-risk-no-auth should not be in narrow blocking, got: {matrix_errors}"
    )


def test_validate_block_matrix_on_with_valid_matrix_passes():
    """block_matrix=True: a valid PR should not get matrix blocking errors."""
    body = _complete_pr_body("source-code")
    changes_list = [Change("M", "src/foo.py"), Change("M", "tests/unit/bar.py")]
    errors = validate(body, changes_list, block_matrix=True)
    matrix_errors = [e for e in errors if "authorization matrix" in e.lower()]
    assert len(matrix_errors) == 0, (
        f"Valid PR should not get matrix blocking errors, got: {matrix_errors}"
    )


def test_validate_block_matrix_skip_body_checks_skips_matrix_blocking():
    """skip_body_checks=True skips matrix even with block_matrix=True."""
    body = _complete_pr_body("non-existent-type")
    changes_list = [Change("M", ".env")]
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        errors = validate(body, changes_list, skip_body_checks=True, block_matrix=True)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    matrix_errors = [e for e in errors if "authorization matrix" in e.lower()]
    assert len(matrix_errors) == 0, f"skip_body_checks should skip matrix, got: {matrix_errors}"
    assert "[PR Authorization Matrix]" not in output
