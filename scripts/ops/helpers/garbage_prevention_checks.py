#!/usr/bin/env python3
"""Garbage prevention checks — P0 blocking rules for TECHDEBT-G1.

lifecycle: permanent

Contains:
- Report sprawl tightening (P0-3): restricted task types, lifecycle requirement
- Generated artifact detection (P0-2): integration with check_no_generated_artifacts

Extracted from ai_workflow_gate.py to keep gate file under 800-line limit.

Usage:
  from scripts.ops.helpers.garbage_prevention_checks import (
      check_report_restricted_task_type,
      check_report_lifecycle_required,
      check_no_generated_artifacts_wrapper,
  )
"""

from __future__ import annotations

import re
import sys

# Task types that are allowed to add new docs/_reports files.
# All other task types are blocked from adding committed reports.
_REPORT_ALLOWED_TASK_TYPES: frozenset[str] = frozenset(
    {
        "docs-only",
        "workflow-governance",
        "audit-only",
    }
)


def _parse_task_type_from_body(pr_body: str) -> str:
    """Lightweight task type extraction from PR body without importing full parser."""
    match = re.search(r"\|\s*Task\s+type\s*\|\s*([^\s|]+)\s*\|", pr_body, re.IGNORECASE)
    if match:
        return match.group(1).strip().lower()
    return "unknown"


def check_report_restricted_task_type(
    added: set[str],
    pr_body: str,
    *,
    skip_body_checks: bool = False,
) -> list[str]:
    """Block non-docs/governance/audit task types from adding docs/_reports.

    Reports should be written to /tmp by default.  Only task types that
    explicitly deal with documentation or governance may commit report files.
    """
    if skip_body_checks:
        return []

    report_added = sorted(p for p in added if p.startswith("docs/_reports/") and p.endswith(".md"))
    if not report_added:
        return []

    task_type = _parse_task_type_from_body(pr_body)
    if task_type in _REPORT_ALLOWED_TASK_TYPES:
        return []

    return [
        f"Report sprawl blocked: task type '{task_type}' must not add committed "
        f"report files to docs/_reports/. Reports should be written to /tmp. "
        f"Use docs-only, workflow-governance, or audit-only task type for "
        f"committed report files. Affected files: {', '.join(report_added)}"
    ]


def check_report_lifecycle_required(
    added: set[str],
    pr_body: str,
    *,
    skip_body_checks: bool = False,
) -> list[str]:
    """Require ## Report Lifecycle section when new docs/_reports files are added."""
    if skip_body_checks:
        return []

    report_added = sorted(p for p in added if p.startswith("docs/_reports/") and p.endswith(".md"))
    if not report_added:
        return []

    has_lifecycle = "## Report Lifecycle" in pr_body or "## Report Retention" in pr_body
    if has_lifecycle:
        return []

    return [
        f"Report lifecycle required: {len(report_added)} new docs/_reports file(s) "
        f"added but no '## Report Lifecycle' section found in PR body. "
        f"Explain: lifecycle (permanent/temporary), retention plan, and why the "
        f"report is committed rather than kept in /tmp. "
        f"Affected files: {', '.join(report_added)}"
    ]


def check_no_generated_artifacts_wrapper(added: set[str]) -> list[str]:
    """Check newly-added files for generated artifacts (P0-2).

    Delegates to the dedicated check_no_generated_artifacts module.
    Only checks newly-added files to avoid false positives from pre-existing
    tracked files.
    """
    if not added:
        return []

    try:
        from scripts.devops.check_no_generated_artifacts import check_added_files  # noqa: PLC0415

        errors, warnings = check_added_files(added)
        # Warnings are printed to stdout for visibility but not blocking.
        if warnings:
            sys.stdout.write(
                f"[AI Workflow Gate][no-generated-artifacts] "
                f"{len(warnings)} suspicious file(s) detected:\n"
            )
            for w in warnings:
                sys.stdout.write(f"  {w}\n")
        return errors  # noqa: TRY300
    except ImportError:
        sys.stdout.write(
            "[AI Workflow Gate] WARN: check_no_generated_artifacts module not found. "
            "Skipping generated artifact check.\n"
        )
        return []
