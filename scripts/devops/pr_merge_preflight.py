#!/usr/bin/env python3
"""PR merge preflight evidence check — read-only, no-merge, no-write.

lifecycle: permanent

Produces auditable PASS/FAIL evidence before merging a PR. All data is
fetched read-only via the ``gh`` CLI. No GitHub API token mutation scope
is required beyond what ``gh pr view`` and ``gh run list`` already grant.

Usage:
  python scripts/devops/pr_merge_preflight.py --pr 1474
  python scripts/devops/pr_merge_preflight.py --pr 1474 --json   # machine-readable

Output fields (always emitted):
  PR number, PR title, state, draft status, base branch, head branch,
  head SHA, mergeable status, changed files, additions/deletions,
  CI workflow name, CI run id, CI status, CI conclusion, final PASS/FAIL.

PASS conditions (ALL must be true):
  - PR is open
  - PR is NOT a draft
  - base ref is main
  - mergeable is true / clean / mergeable
  - a Production Gate CI run exists for the head SHA
  - Production Gate status is completed
  - Production Gate conclusion is success

FAIL on any of:
  - PR closed
  - PR is draft
  - mergeable unknown / false
  - CI missing / pending / failed / cancelled
  - head SHA could not be confirmed
  - Production Gate could not be found
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRODUCTION_GATE_WORKFLOW = "Production Gate"
TIMEOUT_SECONDS = 30

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PrInfo:
    """Normalised PR metadata extracted from ``gh pr view --json``."""

    number: int
    title: str
    state: str  # OPEN / CLOSED / MERGED
    is_draft: bool
    base_ref_name: str
    head_ref_name: str
    head_ref_oid: str  # head SHA
    mergeable: str  # MERGEABLE / CONFLICTING / UNKNOWN
    changed_files: int
    additions: int
    deletions: int

    @classmethod
    def from_gh_json(cls, number: int, data: dict[str, Any]) -> PrInfo:
        return cls(
            number=number,
            title=data.get("title", ""),
            state=data.get("state", "UNKNOWN"),
            is_draft=data.get("isDraft", False),
            base_ref_name=data.get("baseRefName", ""),
            head_ref_name=data.get("headRefName", ""),
            head_ref_oid=data.get("headRefOid", ""),
            mergeable=data.get("mergeable", "UNKNOWN"),
            changed_files=data.get("changedFiles", 0),
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
        )


@dataclass
class CiInfo:
    """CI check result extracted from ``gh run list --json``."""

    workflow_name: str
    run_id: str | None
    status: str  # completed / in_progress / pending / queued
    conclusion: str  # success / failure / cancelled / skipped / ""

    @classmethod
    def empty(cls) -> CiInfo:
        return cls(workflow_name=PRODUCTION_GATE_WORKFLOW, run_id=None, status="", conclusion="")


@dataclass
class PreflightResult:
    """Aggregate preflight verdict and all evidence."""

    pr: PrInfo
    ci: CiInfo
    passed: bool
    failures: list[str] = field(default_factory=list)

    def verdict(self) -> str:
        return "PASS" if self.passed else "FAIL"


# ---------------------------------------------------------------------------
# gh CLI helpers (mocked in tests)
# ---------------------------------------------------------------------------


def run_gh(args: list[str], stdin: str | None = None) -> str:
    """Run a ``gh`` command and return stdout (or raise on failure)."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        input=stdin,
    )
    result.check_returncode()
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Data fetching (reads only — no mutations)
# ---------------------------------------------------------------------------


def fetch_pr(number: int) -> PrInfo:
    """Fetch PR metadata via ``gh pr view --json``."""
    raw = run_gh(
        [
            "pr",
            "view",
            str(number),
            "--json",
            "title,state,isDraft,baseRefName,headRefName,headRefOid,mergeable,changedFiles,additions,deletions",
        ]
    )
    data = json.loads(raw)
    return PrInfo.from_gh_json(number, data)


def fetch_ci(head_sha: str) -> CiInfo:
    """Find the most recent Production Gate run for *head_sha*."""
    try:
        raw = run_gh(
            [
                "run",
                "list",
                "--workflow",
                PRODUCTION_GATE_WORKFLOW,
                "--commit",
                head_sha,
                "--limit",
                "1",
                "--json",
                "name,status,conclusion,databaseId",
            ]
        )
    except subprocess.CalledProcessError:
        return CiInfo.empty()

    entries: list[dict[str, Any]] = json.loads(raw)
    if not entries:
        return CiInfo.empty()

    entry = entries[0]
    return CiInfo(
        workflow_name=entry.get("name", PRODUCTION_GATE_WORKFLOW),
        run_id=str(entry.get("databaseId", "")),
        status=entry.get("status", ""),
        conclusion=entry.get("conclusion", ""),
    )


# ---------------------------------------------------------------------------
# Rule checks — each returns [] on pass, [error_message] on failure
# ---------------------------------------------------------------------------


def _check_pr_open(pr: PrInfo) -> list[str]:
    if pr.state.upper() != "OPEN":
        return [f"PR state is '{pr.state}', expected 'OPEN'"]
    return []


def _check_not_draft(pr: PrInfo) -> list[str]:
    if pr.is_draft:
        return ["PR is a draft"]
    return []


def _check_base_main(pr: PrInfo) -> list[str]:
    if pr.base_ref_name != "main":
        return [f"Base branch is '{pr.base_ref_name}', expected 'main'"]
    return []


def _check_mergeable(pr: PrInfo) -> list[str]:
    if pr.mergeable.upper() not in {"MERGEABLE", "CLEAN"}:
        return [f"Mergeable is '{pr.mergeable}', expected 'MERGEABLE'"]
    return []


def _check_head_sha(pr: PrInfo) -> list[str]:
    if not pr.head_ref_oid or len(pr.head_ref_oid) < 7:
        return ["Head SHA is empty or too short"]
    return []


def _check_ci(ci: CiInfo) -> list[str]:
    failures: list[str] = []
    if ci.run_id is None:
        failures.append(f"CI workflow '{PRODUCTION_GATE_WORKFLOW}' not found for head SHA")
        return failures
    if ci.status != "completed":
        failures.append(f"CI status is '{ci.status}', expected 'completed'")
    if ci.conclusion != "success":
        failures.append(f"CI conclusion is '{ci.conclusion}', expected 'success'")
    return failures


CHECKS = (
    ("PR open", _check_pr_open),
    ("PR not draft", _check_not_draft),
    ("Base is main", _check_base_main),
    ("Mergeable", _check_mergeable),
    ("Head SHA present", _check_head_sha),
    ("CI complete + success", _check_ci),
)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def evaluate(pr_number: int) -> PreflightResult:
    """Fetch PR + CI data and run all checks, returning a verdict."""
    pr = fetch_pr(pr_number)
    ci = fetch_ci(pr.head_ref_oid)

    failures: list[str] = []
    for label, check_fn in CHECKS:
        if check_fn is _check_ci:
            result = check_fn(ci)
        else:
            result = check_fn(pr)
        failures.extend(result)

    return PreflightResult(
        pr=pr,
        ci=ci,
        passed=len(failures) == 0,
        failures=failures,
    )


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_evidence(result: PreflightResult, *, as_json: bool = False) -> str:
    """Render the preflight report as text or JSON."""
    if as_json:
        return json.dumps(
            {
                "pr_number": result.pr.number,
                "pr_title": result.pr.title,
                "state": result.pr.state,
                "draft": result.pr.is_draft,
                "base_branch": result.pr.base_ref_name,
                "head_branch": result.pr.head_ref_name,
                "head_sha": result.pr.head_ref_oid,
                "mergeable": result.pr.mergeable,
                "changed_files": result.pr.changed_files,
                "additions": result.pr.additions,
                "deletions": result.pr.deletions,
                "ci_workflow": result.ci.workflow_name,
                "ci_run_id": result.ci.run_id,
                "ci_status": result.ci.status,
                "ci_conclusion": result.ci.conclusion,
                "verdict": result.verdict(),
                "failures": result.failures,
            },
            indent=2,
        )

    lines = [
        "=" * 60,
        "  PR Merge Preflight Evidence",
        "=" * 60,
        f"  PR Number:       {result.pr.number}",
        f"  PR Title:        {result.pr.title}",
        f"  State:           {result.pr.state}",
        f"  Draft:           {'yes' if result.pr.is_draft else 'no'}",
        f"  Base Branch:     {result.pr.base_ref_name}",
        f"  Head Branch:     {result.pr.head_ref_name}",
        f"  Head SHA:        {result.pr.head_ref_oid}",
        f"  Mergeable:       {result.pr.mergeable}",
        f"  Changed Files:   {result.pr.changed_files}",
        f"  Additions:       {result.pr.additions}",
        f"  Deletions:       {result.pr.deletions}",
        "-" * 60,
        f"  CI Workflow:     {result.ci.workflow_name}",
        f"  CI Run ID:       {result.ci.run_id or 'NOT FOUND'}",
        f"  CI Status:       {result.ci.status or 'N/A'}",
        f"  CI Conclusion:   {result.ci.conclusion or 'N/A'}",
        "-" * 60,
    ]

    verdict = result.verdict()
    if result.passed:
        lines.append(f"  VERDICT:         \033[0;32m{verdict}\033[0m")
    else:
        lines.append(f"  VERDICT:         \033[0;31m{verdict}\033[0m")

    if result.failures:
        lines.append("-" * 60)
        lines.append("  Failures:")
        for f in result.failures:
            lines.append(f"    - {f}")

    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PR merge preflight evidence check (read-only)",
    )
    parser.add_argument("--pr", type=int, required=True, help="PR number to evaluate")
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output machine-readable JSON instead of formatted text",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = evaluate(args.pr)
    print(format_evidence(result, as_json=args.json))
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
