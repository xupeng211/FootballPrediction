#!/usr/bin/env python3
"""Post-merge completion evidence check — read-only.

lifecycle: permanent

Checks that a merged PR satisfies the post-merge completion invariant. All
checks are read-only via ``gh`` CLI and local git commands. Branch/worktree
cleanup is deliberately outside this completion utility.

Usage:
  # Read-only check (default — safe)
  python scripts/devops/pr_post_merge_check.py --pr 1475 \
      --merge-commit abc1234 --branch feature/my-branch

Checks performed:
  1. PR state is MERGED
  2. Merge commit is valid and non-empty
  3. Merge commit exists in origin/main
  4. Production Gate CI workflow concluded with success on the merge commit
  5. Local main can fast-forward sync to origin/main
  6. Working tree is clean (no uncommitted changes)
  7. The supplied branch value is reported only; it never authorizes cleanup

PASS conditions (ALL must be true):
  - PR state == MERGED
  - Merge commit SHA present and exactly 40 hex characters
  - Merge commit reachable from origin/main
  - Production Gate CI run exists for merge commit
  - CI status is completed
  - CI conclusion is success
  - Local main is up-to-date or can ff-only sync
  - git status is clean

FAIL on any of:
  - PR not merged
  - Merge commit missing/invalid
  - Merge commit not in origin/main
  - CI run not found / pending / failed / cancelled
  - Local main diverged from origin/main
  - Working tree has uncommitted changes
Cleanup is not performed here. `DONE` remains the responsibility of the exact
merge-SHA main Production Gate, not this helper and not branch cleanup.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import subprocess
import sys
from typing import Any

from exact_head import ExactHeadError, assert_ci_is_current, is_full_sha, normalize_full_sha

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRODUCTION_GATE_WORKFLOW = "Production Gate"
TIMEOUT_SECONDS = 30
_AHEAD_BEHIND_COUNT_FIELDS = 2

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PostMergeResult:
    """Aggregate post-merge verdict and all evidence."""

    pr_number: int
    pr_state: str
    merge_commit: str
    branch: str
    ci_workflow: str
    ci_run_id: str | None
    ci_status: str
    ci_conclusion: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    main_ff_ok: bool = False
    status_clean: bool = False
    ci_head_sha: str | None = None

    def verdict(self) -> str:
        """Return 'PASS' or 'FAIL'."""
        return "PASS" if self.passed else "FAIL"


# ---------------------------------------------------------------------------
# gh CLI and git helpers (mocked in tests)
# ---------------------------------------------------------------------------


def run_gh(args: list[str], stdin: str | None = None) -> str:
    """Run a ``gh`` command and return stdout (or raise on failure)."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        input=stdin,
        check=False,
    )
    result.check_returncode()
    return result.stdout.strip()


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a ``git`` command and return the CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


# ---------------------------------------------------------------------------
# Data fetching (reads only — no mutations)
# ---------------------------------------------------------------------------


def fetch_pr(number: int) -> dict[str, Any]:
    """Fetch PR metadata via ``gh pr view --json``."""
    raw = run_gh(
        [
            "pr",
            "view",
            str(number),
            "--json",
            "state,mergedAt,mergeCommit",
        ]
    )
    return json.loads(raw)


def fetch_ci(commit_sha: str) -> dict[str, Any]:
    """Find the most recent Production Gate run for a commit SHA."""
    try:
        raw = run_gh(
            [
                "run",
                "list",
                "--workflow",
                PRODUCTION_GATE_WORKFLOW,
                "--commit",
                commit_sha,
                "--limit",
                "1",
                "--json",
                "name,status,conclusion,databaseId,headSha",
            ]
        )
    except subprocess.CalledProcessError:
        return {
            "found": False,
            "run_id": None,
            "status": "",
            "conclusion": "",
            "head_sha": "",
        }

    entries: list[dict[str, Any]] = json.loads(raw)
    if not entries:
        return {
            "found": False,
            "run_id": None,
            "status": "",
            "conclusion": "",
            "head_sha": "",
        }

    entry = entries[0]
    return {
        "found": True,
        "workflow": entry.get("name", PRODUCTION_GATE_WORKFLOW),
        "run_id": str(entry.get("databaseId", "")),
        "status": entry.get("status", ""),
        "conclusion": entry.get("conclusion", ""),
        "head_sha": str(entry.get("headSha") or "").lower(),
    }


# ---------------------------------------------------------------------------
# Git checks (read-only)
# ---------------------------------------------------------------------------


def merge_commit_in_origin_main(merge_commit: str) -> bool:
    """Check if merge_commit is reachable from origin/main."""
    # Fetch latest from origin to be sure
    run_git(["fetch", "origin", "main"])
    result = run_git(["branch", "-r", "--contains", merge_commit])
    return "origin/main" in result.stdout


def main_can_ff_sync() -> tuple[bool, str]:
    """Check if local main can fast-forward to origin/main.

    Returns (ok, message).
    """
    # Refresh the remote-tracking ref, but fail closed if the read fails.
    fetch_result = run_git(["fetch", "origin", "main"])
    if fetch_result.returncode != 0:
        return False, "STATE=GIT_COMMAND_FAILED: unable to fetch origin/main"

    # For ``main...origin/main``, the left count is local-only and the right
    # count is remote-only.  This distinguishes behind, ahead, and diverged
    # histories without relying on a second inverse ancestry check.
    result = run_git(["rev-list", "--left-right", "--count", "main...origin/main"])
    if result.returncode != 0:
        return False, "STATE=GIT_COMMAND_FAILED: unable to calculate main/origin/main divergence"

    counts = result.stdout.strip().split()
    if len(counts) != _AHEAD_BEHIND_COUNT_FIELDS or any(not count.isdigit() for count in counts):
        return False, "STATE=GIT_COMMAND_FAILED: invalid ahead/behind count from git"

    local_only, remote_only = (int(count) for count in counts)
    if local_only == 0 and remote_only == 0:
        return True, "STATE=UP_TO_DATE: local main equals origin/main"
    if local_only == 0:
        return (
            True,
            f"STATE=FAST_FORWARD_AVAILABLE: local main is {remote_only} commit(s) behind origin/main",
        )
    state = "LOCAL_AHEAD" if remote_only == 0 else "DIVERGED"
    if state == "LOCAL_AHEAD":
        detail = f"local main has {local_only} commit(s) not on origin/main"
    else:
        detail = f"local main has {local_only} local-only and {remote_only} remote-only commit(s)"
    return False, f"STATE={state}: {detail}"


def git_status_clean() -> tuple[bool, str]:
    """Check if working tree is clean."""
    result = run_git(["status", "--short"])
    if result.stdout.strip():
        return False, f"Working tree is dirty:\n{result.stdout}"
    return True, "Working tree is clean"


# ---------------------------------------------------------------------------
# Rule checks — each returns [] on pass, [error_message] on failure
# ---------------------------------------------------------------------------


def _check_pr_merged(pr_data: dict[str, Any]) -> list[str]:
    state = pr_data.get("state", "")
    if state.upper() != "MERGED":
        return [f"PR state is '{state}', expected 'MERGED'. PR may not be merged yet."]
    return []


def _check_merge_commit(merge_commit: str) -> list[str]:
    try:
        normalize_full_sha(merge_commit.strip(), role="merge commit SHA")
    except ExactHeadError:
        return [f"Merge commit SHA must be a full 40-hex commit SHA: '{merge_commit}'"]
    return []


def _check_merge_in_main(merge_commit: str) -> list[str]:
    if not is_full_sha(merge_commit):
        return ["Merge commit in origin/main cannot be checked without a full 40-hex SHA"]
    if not merge_commit_in_origin_main(merge_commit):
        return [f"Merge commit {merge_commit} is NOT in origin/main"]
    return []


def _check_ci(ci_data: dict[str, Any], expected_head: str | None = None) -> list[str]:
    failures: list[str] = []
    if not ci_data.get("found"):
        failures.append(f"CI workflow '{PRODUCTION_GATE_WORKFLOW}' not found for merge commit")
        return failures
    if ci_data.get("status") != "completed":
        failures.append(f"CI status is '{ci_data.get('status')}', expected 'completed'")
    if ci_data.get("conclusion") != "success":
        failures.append(f"CI conclusion is '{ci_data.get('conclusion')}', expected 'success'")
    if expected_head is not None:
        try:
            assert_ci_is_current(ci_data.get("head_sha"), expected_head)
        except ExactHeadError as exc:
            failures.append(str(exc))
    return failures


def _check_main_ff_sync() -> list[str]:
    ok, msg = main_can_ff_sync()
    if not ok:
        return [msg]
    return []


def _check_status_clean() -> list[str]:
    ok, msg = git_status_clean()
    if not ok:
        return [msg]
    return []


CHECKS: list[tuple[str, Any]] = [
    ("PR merged", None),  # placeholder — resolved dynamically
    ("Merge commit valid", None),
    ("Merge commit in origin/main", _check_merge_in_main),
    ("Production Gate CI success", None),
    ("Local main ff-only sync", _check_main_ff_sync),
    ("Working tree clean", _check_status_clean),
]


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def evaluate(
    pr_number: int,
    merge_commit: str,
    branch: str,
) -> PostMergeResult:
    """Fetch PR + CI data and run all checks, returning a verdict."""
    pr_data = fetch_pr(pr_number)
    pr_state = pr_data.get("state", "UNKNOWN")
    merge_sha = merge_commit.strip()
    ci_data = (
        fetch_ci(merge_sha)
        if is_full_sha(merge_sha)
        else {
            "found": False,
            "run_id": None,
            "status": "",
            "conclusion": "",
            "head_sha": "",
        }
    )

    # Resolve checks dynamically with captured state
    failures: list[str] = []

    # Check 1: PR merged
    failures.extend(_check_pr_merged(pr_data))

    # Check 2: Merge commit valid
    failures.extend(_check_merge_commit(merge_commit))

    # Check 3: Merge commit in origin/main
    failures.extend(_check_merge_in_main(merge_sha))

    # Check 4: CI success
    failures.extend(_check_ci(ci_data, merge_sha if is_full_sha(merge_sha) else None))

    # Check 5: Main ff-only sync
    failures.extend(_check_main_ff_sync())

    # Check 6: Working tree clean
    failures.extend(_check_status_clean())

    passed = len(failures) == 0

    main_ff_ok, _ = main_can_ff_sync()
    status_clean, _ = git_status_clean()

    return PostMergeResult(
        pr_number=pr_number,
        pr_state=pr_state,
        merge_commit=merge_sha,
        branch=branch,
        ci_workflow=ci_data.get("workflow", PRODUCTION_GATE_WORKFLOW),
        ci_run_id=ci_data.get("run_id"),
        ci_status=ci_data.get("status", ""),
        ci_conclusion=ci_data.get("conclusion", ""),
        passed=passed,
        failures=failures,
        main_ff_ok=main_ff_ok,
        status_clean=status_clean,
        ci_head_sha=ci_data.get("head_sha") or None,
    )


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_evidence(result: PostMergeResult, *, as_json: bool = False) -> str:
    """Render the post-merge check report as text or JSON."""
    if as_json:
        return json.dumps(
            {
                "pr_number": result.pr_number,
                "pr_state": result.pr_state,
                "merge_commit": result.merge_commit,
                "branch": result.branch,
                "ci_workflow": result.ci_workflow,
                "ci_run_id": result.ci_run_id,
                "ci_status": result.ci_status,
                "ci_conclusion": result.ci_conclusion,
                "ci_head_sha": result.ci_head_sha,
                "main_ff_ok": result.main_ff_ok,
                "status_clean": result.status_clean,
                "verdict": result.verdict(),
                "failures": result.failures,
            },
            indent=2,
        )

    lines = [
        "=" * 60,
        "  Post-Merge Check Evidence",
        "=" * 60,
        f"  PR Number:       {result.pr_number}",
        f"  PR State:        {result.pr_state}",
        f"  Merge Commit:    {result.merge_commit}",
        f"  Branch:          {result.branch}",
        f"  Main FF Sync:    {'OK' if result.main_ff_ok else 'FAIL'}",
        f"  Working Tree:    {'clean' if result.status_clean else 'DIRTY'}",
        "-" * 60,
        f"  CI Workflow:     {result.ci_workflow}",
        f"  CI Run ID:       {result.ci_run_id or 'NOT FOUND'}",
        f"  CI Status:       {result.ci_status or 'N/A'}",
        f"  CI Conclusion:   {result.ci_conclusion or 'N/A'}",
        f"  CI HEAD:         {result.ci_head_sha or 'N/A'}",
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
        lines.extend(f"    - {f}" for f in result.failures)

    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post-merge completion evidence check (read-only)",
    )
    parser.add_argument("--pr", type=int, required=True, help="PR number")
    parser.add_argument("--merge-commit", type=str, required=True, help="Merge commit SHA")
    parser.add_argument(
        "--branch", type=str, required=True, help="Branch name for evidence only; never deleted"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output machine-readable JSON",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the post-merge check and exit with 0 on PASS, 1 on FAIL."""
    args = _parse_args(argv)

    result = evaluate(
        args.pr,
        args.merge_commit,
        args.branch,
    )

    print(format_evidence(result, as_json=args.json))

    if not result.passed:
        print("\nPost-merge completion evidence FAILED.", file=sys.stderr)
        return 1

    # All checks passed. Cleanup is intentionally not part of this utility.
    print("\nPost-merge completion evidence passed. Branch/worktree cleanup is separate.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
