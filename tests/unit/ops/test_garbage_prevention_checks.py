"""Tests for garbage prevention checks — P0-3 G1 hardening.

lifecycle: test-fixture

Covers: check_report_restricted_task_type, check_report_lifecycle_required.
"""

from __future__ import annotations

from pathlib import Path
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.ops.helpers.garbage_prevention_checks import (  # noqa: E402
    check_report_lifecycle_required,
    check_report_restricted_task_type,
)

# ---------------------------------------------------------------------------
# check_report_restricted_task_type
# ---------------------------------------------------------------------------


def test_report_restricted_docs_only_allowed():
    """docs-only task type may add docs/_reports files."""
    body = textwrap.dedent("""\
        ## Scope
        | Task type | docs-only |
    """)
    errors = check_report_restricted_task_type(
        {"docs/_reports/audit.md"},
        body,
    )
    assert len(errors) == 0


def test_report_restricted_workflow_governance_allowed():
    """workflow-governance task type may add docs/_reports files."""
    body = textwrap.dedent("""\
        ## Scope
        | Task type | workflow-governance |
    """)
    errors = check_report_restricted_task_type(
        {"docs/_reports/governance.md"},
        body,
    )
    assert len(errors) == 0


def test_report_restricted_audit_only_allowed():
    """audit-only task type may add docs/_reports files."""
    body = textwrap.dedent("""\
        ## Scope
        | Task type | audit-only |
    """)
    errors = check_report_restricted_task_type(
        {"docs/_reports/audit_findings.md"},
        body,
    )
    assert len(errors) == 0


def test_report_restricted_source_code_blocked():
    """source-code task type must not add docs/_reports files."""
    body = textwrap.dedent("""\
        ## Scope
        | Task type | source-code |
    """)
    errors = check_report_restricted_task_type(
        {"docs/_reports/fix_summary.md"},
        body,
    )
    assert len(errors) >= 1
    assert any("source-code" in e.lower() for e in errors)


def test_report_restricted_test_only_blocked():
    """test-only task type must not add docs/_reports files."""
    body = textwrap.dedent("""\
        ## Scope
        | Task type | test-only |
    """)
    errors = check_report_restricted_task_type(
        {"docs/_reports/test_results.md"},
        body,
    )
    assert len(errors) >= 1


def test_report_restricted_no_reports_added():
    """No errors when no docs/_reports files are added."""
    body = textwrap.dedent("""\
        ## Scope
        | Task type | source-code |
    """)
    errors = check_report_restricted_task_type(
        {"src/foo.py"},
        body,
    )
    assert len(errors) == 0


def test_report_restricted_skip_body_checks():
    """skip_body_checks returns no errors."""
    errors = check_report_restricted_task_type(
        {"docs/_reports/fix_summary.md"},
        "",
        skip_body_checks=True,
    )
    assert len(errors) == 0


# ---------------------------------------------------------------------------
# check_report_lifecycle_required
# ---------------------------------------------------------------------------


def test_report_lifecycle_present_passes():
    """PR body with ## Report Lifecycle section passes."""
    body = textwrap.dedent("""\
        ## Report Lifecycle

        This report is a permanent governance artifact.
        Retention: keep until superseded by next audit.
    """)
    errors = check_report_lifecycle_required(
        {"docs/_reports/governance_audit.md"},
        body,
    )
    assert len(errors) == 0


def test_report_lifecycle_retention_alias_passes():
    """PR body with ## Report Retention section passes."""
    body = textwrap.dedent("""\
        ## Report Retention

        Temporary report, delete after 30 days.
    """)
    errors = check_report_lifecycle_required(
        {"docs/_reports/temp_audit.md"},
        body,
    )
    assert len(errors) == 0


def test_report_lifecycle_missing_fails():
    """Missing ## Report Lifecycle section when reports added should fail."""
    body = textwrap.dedent("""\
        ## Summary
        Some PR without a lifecycle section.
    """)
    errors = check_report_lifecycle_required(
        {"docs/_reports/audit.md"},
        body,
    )
    assert len(errors) >= 1
    assert any("Report Lifecycle" in e for e in errors)


def test_report_lifecycle_no_reports_added():
    """No errors when no docs/_reports files are added."""
    body = textwrap.dedent("""\
        ## Summary
        No reports here.
    """)
    errors = check_report_lifecycle_required(
        {"src/foo.py"},
        body,
    )
    assert len(errors) == 0


def test_report_lifecycle_skip_body_checks():
    """skip_body_checks returns no errors."""
    errors = check_report_lifecycle_required(
        {"docs/_reports/audit.md"},
        "",
        skip_body_checks=True,
    )
    assert len(errors) == 0


def test_report_lifecycle_multiple_files_one_error():
    """Multiple report files should produce a single error listing all."""
    body = textwrap.dedent("""\
        ## Summary
        Multiple reports without lifecycle.
    """)
    errors = check_report_lifecycle_required(
        {"docs/_reports/a.md", "docs/_reports/b.md"},
        body,
    )
    assert len(errors) >= 1
    # Should mention both files
    assert any("a.md" in e for e in errors)
    assert any("b.md" in e for e in errors)
