#!/usr/bin/env python3
"""Post-merge check / cleanup gate — read-only by default, no auto-delete.

lifecycle: permanent

Checks that a merged PR satisfies all post-merge safety gates before
allowing branch cleanup. All checks are read-only via ``gh`` CLI and
local git commands. Branch deletion requires an explicit opt-in flag.

Usage:
  # Read-only check (default — safe)
  python scripts/devops/pr_post_merge_check.py --pr 1475 \
      --merge-commit abc1234 --branch feature/my-branch

  # With cleanup (explicit opt-in required)
  python scripts/devops/pr_post_merge_check.py --pr 1475 \
      --merge-commit abc1234 --branch feature/my-branch --confirm-cleanup

Checks performed:
  1. PR state is MERGED
  2. Merge commit is valid and non-empty
  3. Merge commit exists in origin/main
  4. Production Gate CI workflow concluded with success on the merge commit
  5. Local main can fast-forward sync to origin/main
  6. Working tree is clean (no uncommitted changes)
  7. Branch is not protected (main/master/current branch)

PASS conditions (ALL must be true):
  - PR state == MERGED
  - Merge commit SHA present and >= 7 chars
  - Merge commit reachable from origin/main
  - Production Gate CI run exists for merge commit
  - CI status is completed
  - CI conclusion is success
  - Local main is up-to-date or can ff-only sync
  - git status is clean
  - Branch is not protected (main/master/origin/main/origin/master/current)

FAIL on any of:
  - PR not merged
  - Merge commit missing/invalid
  - Merge commit not in origin/main
  - CI run not found / pending / failed / cancelled
  - Local main diverged from origin/main
  - Working tree has uncommitted changes
  - Branch is protected or is the current branch

Cleanup (only with --confirm-cleanup):
  - Delete remote branch
  - Delete local branch (if it exists)
  - Requires all checks to PASS first
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import subprocess
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRODUCTION_GATE_WORKFLOW = "Production Gate"
TIMEOUT_SECONDS = 30
MIN_SHA_LENGTH = 7

PROTECTED_BRANCHES: frozenset[str] = frozenset({"main", "master", "origin/main", "origin/master"})

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
                "name,status,conclusion,databaseId",
            ]
        )
    except subprocess.CalledProcessError:
        return {"found": False, "run_id": None, "status": "", "conclusion": ""}

    entries: list[dict[str, Any]] = json.loads(raw)
    if not entries:
        return {"found": False, "run_id": None, "status": "", "conclusion": ""}

    entry = entries[0]
    return {
        "found": True,
        "workflow": entry.get("name", PRODUCTION_GATE_WORKFLOW),
        "run_id": str(entry.get("databaseId", "")),
        "status": entry.get("status", ""),
        "conclusion": entry.get("conclusion", ""),
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
    # Ensure we have latest
    run_git(["fetch", "origin", "main"])

    # Check if origin/main is ahead of or equal to local main
    result = run_git(["merge-base", "--is-ancestor", "main", "origin/main"])
    if result.returncode != 0:
        return False, "Local main is NOT an ancestor of origin/main — history has diverged"

    # Check if local main is behind origin/main
    result2 = run_git(["merge-base", "--is-ancestor", "origin/main", "main"])
    if result2.returncode == 0:
        # origin/main is ancestor of main => they're equal or local is ahead
        behind_result = run_git(["rev-list", "--count", "main..origin/main"])
        if behind_result.returncode == 0:
            count = behind_result.stdout.strip()
            if count and count != "0":
                return (
                    True,
                    f"Local main is {count} commit(s) behind origin/main — ff-only sync possible",
                )
        return True, "Local main is up-to-date with origin/main"
    # origin/main is NOT ancestor of main => local main is ahead (has extra commits)
    return False, "Local main has commits not on origin/main — cannot ff-only sync"


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
    if not merge_commit or len(merge_commit.strip()) < MIN_SHA_LENGTH:
        return [f"Merge commit SHA is empty or too short: '{merge_commit}'"]
    return []


def _check_merge_in_main(merge_commit: str) -> list[str]:
    if not merge_commit_in_origin_main(merge_commit):
        return [f"Merge commit {merge_commit} is NOT in origin/main"]
    return []


def _check_ci(ci_data: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not ci_data.get("found"):
        failures.append(f"CI workflow '{PRODUCTION_GATE_WORKFLOW}' not found for merge commit")
        return failures
    if ci_data.get("status") != "completed":
        failures.append(f"CI status is '{ci_data.get('status')}', expected 'completed'")
    if ci_data.get("conclusion") != "success":
        failures.append(f"CI conclusion is '{ci_data.get('conclusion')}', expected 'success'")
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
    ("Branch not protected", None),
]


# ---------------------------------------------------------------------------
# Branch protection
# ---------------------------------------------------------------------------


def get_current_branch() -> str:
    """Return the current git branch name, or empty string on failure."""
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _check_branch_not_protected(branch: str) -> list[str]:
    """Check that *branch* is not a protected branch and is not the current branch.

    Returns [] on pass, [error_message] on failure.
    """
    failures: list[str] = []

    if branch in PROTECTED_BRANCHES:
        failures.append(
            f"Branch '{branch}' is a protected branch — cleanup is forbidden. "
            f"Protected branches: {', '.join(sorted(PROTECTED_BRANCHES))}"
        )

    current = get_current_branch()
    if current and branch == current:
        failures.append(
            f"Branch '{branch}' is the currently checked-out branch — "
            f"cannot delete the branch you are on."
        )

    return failures


# ---------------------------------------------------------------------------
# Branch cleanup (only with explicit opt-in)
# ---------------------------------------------------------------------------


def cleanup_branch(branch: str, dry_run: bool = False) -> list[str]:
    """Delete remote and local branch. Returns log messages.

    Only called when --confirm-cleanup is set and all checks pass.
    """
    log: list[str] = []

    # Belt-and-suspenders: refuse to touch protected branches
    protected = _check_branch_not_protected(branch)
    if protected:
        log.append(f"REFUSED: {protected[0]}")
        return log

    if dry_run:
        log.append(f"[DRY RUN] Would delete remote branch: origin/{branch}")
        log.append(f"[DRY RUN] Would delete local branch: {branch}")
        return log

    # Delete remote branch
    try:
        result = run_git(["push", "origin", "--delete", branch])
        if result.returncode == 0:
            log.append(f"Deleted remote branch: origin/{branch}")
        else:
            log.append(f"Failed to delete remote branch: {result.stderr.strip()}")
    except Exception as exc:
        log.append(f"Error deleting remote branch: {exc}")

    # Delete local branch (if it exists)
    try:
        result = run_git(["branch", "-d", branch])
        if result.returncode == 0:
            log.append(f"Deleted local branch: {branch}")
        else:
            stderr = result.stderr.strip()
            if "not found" in stderr.lower():
                log.append(f"Local branch '{branch}' not found — nothing to delete")
            else:
                log.append(f"Failed to delete local branch: {stderr}")
    except Exception as exc:
        log.append(f"Error deleting local branch: {exc}")

    return log


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
    ci_data = fetch_ci(merge_commit.strip())

    # Resolve checks dynamically with captured state
    failures: list[str] = []

    # Check 1: PR merged
    failures.extend(_check_pr_merged(pr_data))

    # Check 2: Merge commit valid
    failures.extend(_check_merge_commit(merge_commit))

    # Check 3: Merge commit in origin/main
    failures.extend(_check_merge_in_main(merge_commit.strip()))

    # Check 4: CI success
    failures.extend(_check_ci(ci_data))

    # Check 5: Main ff-only sync
    failures.extend(_check_main_ff_sync())

    # Check 6: Working tree clean
    failures.extend(_check_status_clean())

    # Check 7: Branch not protected (blocks cleanup of main/master/current)
    failures.extend(_check_branch_not_protected(branch))

    passed = len(failures) == 0

    main_ff_ok, _ = main_can_ff_sync()
    status_clean, _ = git_status_clean()

    return PostMergeResult(
        pr_number=pr_number,
        pr_state=pr_state,
        merge_commit=merge_commit.strip(),
        branch=branch,
        ci_workflow=ci_data.get("workflow", PRODUCTION_GATE_WORKFLOW),
        ci_run_id=ci_data.get("run_id"),
        ci_status=ci_data.get("status", ""),
        ci_conclusion=ci_data.get("conclusion", ""),
        passed=passed,
        failures=failures,
        main_ff_ok=main_ff_ok,
        status_clean=status_clean,
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
        description="Post-merge check / cleanup gate (read-only by default)",
    )
    parser.add_argument("--pr", type=int, required=True, help="PR number")
    parser.add_argument("--merge-commit", type=str, required=True, help="Merge commit SHA")
    parser.add_argument(
        "--branch", type=str, required=True, help="Branch name (for potential cleanup)"
    )
    parser.add_argument(
        "--confirm-cleanup",
        action="store_true",
        default=False,
        help="Enable branch deletion (remote + local). Requires all checks to PASS.",
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
        print("\nPost-merge check FAILED. Branch cleanup is NOT safe.", file=sys.stderr)
        return 1

    # All checks passed
    if args.confirm_cleanup:
        print("\nAll checks passed. Proceeding with branch cleanup...")
        logs = cleanup_branch(args.branch, dry_run=False)
        for log_line in logs:
            print(f"  {log_line}")
        print("Cleanup complete.")
    else:
        print(
            "\nAll checks passed. Branch cleanup requires --confirm-cleanup flag.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
