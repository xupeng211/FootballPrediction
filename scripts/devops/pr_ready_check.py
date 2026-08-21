#!/usr/bin/env python3
"""Canonical, read-only PR readiness state check.

lifecycle: permanent

This command answers one governance question: does the current local feature
worktree and its GitHub PR represent the same, mergeable, fully checked
commit?  It deliberately does not run tests, invoke an AI reviewer, inspect
PR prose as workflow state, modify GitHub, merge, or clean a branch.

Usage::

    python3 scripts/devops/pr_ready_check.py --pr 1866
    python3 scripts/devops/pr_ready_check.py --pr 1866 --json

The check fails closed when GitHub ruleset or check-run evidence is missing.
All freshness and authorization-sensitive comparisons use complete SHA-1
values; abbreviated SHA values are never accepted.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

try:
    from .exact_head import get_current_head, is_full_sha, same_exact_head
except ImportError:  # direct ``python scripts/devops/pr_ready_check.py`` entrypoint
    from exact_head import get_current_head, is_full_sha, same_exact_head

ROOT = Path(__file__).resolve().parents[2]
ACTIVE_ENFORCEMENT = "active"
PASS_CONCLUSIONS = {"success"}
MERGEABLE_STATES = {"MERGEABLE", "CLEAN"}


class PreflightError(RuntimeError):
    """Raised when read-only Git/GitHub evidence cannot be collected."""


@dataclass(frozen=True)
class RepoInfo:
    """Repository identity and default branch obtained from GitHub."""

    name_with_owner: str
    default_branch: str


@dataclass(frozen=True)
class PrInfo:
    """PR metadata used for readiness checks."""

    number: int
    title: str
    state: str
    is_draft: bool
    base_branch: str
    head_branch: str
    head_sha: str
    mergeable: str
    body_present: bool


@dataclass(frozen=True)
class LocalInfo:
    """Local branch, full HEAD, and uncommitted path evidence."""

    branch: str
    head_sha: str
    dirty_paths: tuple[str, ...]


@dataclass(frozen=True)
class CheckRun:
    """One GitHub Actions check run attached to a commit."""

    name: str
    status: str
    conclusion: str
    head_sha: str
    details_url: str = ""


@dataclass(frozen=True)
class Finding:
    """One pass/fail governance finding."""

    name: str
    passed: bool
    message: str


@dataclass
class PreflightResult:
    """Collected evidence and findings for one PR readiness evaluation."""

    repo: RepoInfo
    pr: PrInfo
    local: LocalInfo
    required_checks: tuple[str, ...]
    check_runs: tuple[CheckRun, ...]
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return whether every readiness finding passed."""
        return all(finding.passed for finding in self.findings)

    @property
    def verdict(self) -> str:
        """Return the human-readable aggregate verdict."""
        return "PASS" if self.passed else "FAIL"


def _run(command: list[str]) -> str:
    """Run one read-only command and return stdout, failing closed."""
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreflightError(f"command failed: {' '.join(command)}: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        raise PreflightError(f"command exited {result.returncode}: {' '.join(command)}{suffix}")
    return result.stdout.strip()


def run_gh(args: list[str]) -> str:
    """Run a read-only ``gh`` command."""
    return _run(["gh", *args])


def run_git(args: list[str]) -> str:
    """Run a read-only ``git`` command."""
    return _run(["git", *args])


def _load_json(raw: str, description: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PreflightError(f"{description} returned invalid JSON: {exc}") from exc


def _page_items(payload: Any, key: str | None = None) -> list[Any]:
    """Flatten ``gh api --paginate --slurp`` output without assuming one page."""
    pages = payload if isinstance(payload, list) else [payload]
    items: list[Any] = []
    for page in pages:
        if key is None:
            if isinstance(page, list):
                items.extend(page)
            else:
                items.append(page)
        elif isinstance(page, dict):
            values = page.get(key, [])
            if isinstance(values, list):
                items.extend(values)
    return items


def _is_full_sha(value: str) -> bool:
    return is_full_sha(value)


def fetch_repo() -> RepoInfo:
    """Read repository name and default branch from GitHub."""
    data = _load_json(
        run_gh(["repo", "view", "--json", "nameWithOwner,defaultBranchRef"]),
        "gh repo view",
    )
    default_ref = data.get("defaultBranchRef") or {}
    name_with_owner = str(data.get("nameWithOwner") or "")
    default_branch = str(default_ref.get("name") or "")
    if not name_with_owner or not default_branch:
        raise PreflightError("repository name or default branch is missing")
    return RepoInfo(name_with_owner=name_with_owner, default_branch=default_branch)


def fetch_pr(number: int) -> PrInfo:
    """Read the current metadata and head SHA for a pull request."""
    data = _load_json(
        run_gh(
            [
                "pr",
                "view",
                str(number),
                "--json",
                "title,state,isDraft,baseRefName,headRefName,headRefOid,mergeable,body",
            ]
        ),
        "gh pr view",
    )
    return PrInfo(
        number=number,
        title=str(data.get("title") or ""),
        state=str(data.get("state") or "UNKNOWN"),
        is_draft=bool(data.get("isDraft")),
        base_branch=str(data.get("baseRefName") or ""),
        head_branch=str(data.get("headRefName") or ""),
        head_sha=str(data.get("headRefOid") or "").lower(),
        mergeable=str(data.get("mergeable") or "UNKNOWN"),
        body_present=bool(str(data.get("body") or "").strip()),
    )


def fetch_local() -> LocalInfo:
    """Read current local branch, full HEAD, and porcelain status."""
    branch = run_git(["branch", "--show-current"])
    head_sha = get_current_head(run_git)
    status = run_git(["status", "--porcelain=v1", "--untracked-files=all"])
    dirty_paths = tuple(line for line in status.splitlines() if line.strip())
    return LocalInfo(branch=branch, head_sha=head_sha, dirty_paths=dirty_paths)


def _ruleset_applies_to_default_branch(detail: dict[str, Any], default_branch: str) -> bool:
    if detail.get("enforcement") != ACTIVE_ENFORCEMENT:
        return False
    if detail.get("target") not in (None, "branch"):
        return False
    include = ((detail.get("conditions") or {}).get("ref_name") or {}).get("include") or []
    if not include:
        return True
    return any(
        value in {"~DEFAULT_BRANCH", default_branch, f"refs/heads/{default_branch}"}
        for value in include
    )


def fetch_required_checks(repo: RepoInfo) -> tuple[str, ...]:
    """Read active default-branch required status checks from rulesets."""
    summaries = _page_items(
        _load_json(
            run_gh(["api", f"repos/{repo.name_with_owner}/rulesets?per_page=100"]),
            "GitHub ruleset list",
        )
    )
    required: set[str] = set()
    for summary in summaries:
        if not isinstance(summary, dict) or not summary.get("id"):
            continue
        detail = _load_json(
            run_gh(
                [
                    "api",
                    f"repos/{repo.name_with_owner}/rulesets/{summary['id']}",
                ]
            ),
            f"GitHub ruleset {summary['id']}",
        )
        if not isinstance(detail, dict) or not _ruleset_applies_to_default_branch(
            detail, repo.default_branch
        ):
            continue
        for rule in detail.get("rules") or []:
            if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
                continue
            parameters = rule.get("parameters") or {}
            for check in parameters.get("required_status_checks") or []:
                context = check.get("context") if isinstance(check, dict) else None
                if context:
                    required.add(str(context))
    if not required:
        raise PreflightError(
            f"no active required status checks found for default branch {repo.default_branch}"
        )
    return tuple(sorted(required))


def fetch_check_runs(repo: RepoInfo, head_sha: str) -> tuple[CheckRun, ...]:
    """Read check runs attached to one complete commit SHA."""
    if not _is_full_sha(head_sha):
        return ()
    payload = _load_json(
        run_gh(
            [
                "api",
                f"repos/{repo.name_with_owner}/commits/{head_sha}/check-runs?per_page=100",
            ]
        ),
        f"check runs for {head_sha}",
    )
    runs: list[CheckRun] = []
    for entry in _page_items(payload, key="check_runs"):
        if not isinstance(entry, dict):
            continue
        runs.append(
            CheckRun(
                name=str(entry.get("name") or ""),
                status=str(entry.get("status") or ""),
                conclusion=str(entry.get("conclusion") or ""),
                head_sha=str(entry.get("head_sha") or "").lower(),
                details_url=str(entry.get("html_url") or entry.get("details_url") or ""),
            )
        )
    return tuple(runs)


def _finding(name: str, passed: bool, message: str) -> Finding:
    return Finding(name=name, passed=passed, message=message)


def evaluate(pr_number: int) -> PreflightResult:
    """Collect current state and return one read-only readiness verdict."""
    repo = fetch_repo()
    pr = fetch_pr(pr_number)
    local = fetch_local()
    required_checks = fetch_required_checks(repo)
    check_runs = fetch_check_runs(repo, pr.head_sha)
    findings: list[Finding] = []

    findings.append(
        _finding(
            "pr-open",
            pr.state.upper() == "OPEN",
            f"PR state={pr.state}; expected OPEN",
        )
    )
    findings.append(_finding("pr-not-draft", not pr.is_draft, f"draft={pr.is_draft}"))
    findings.append(
        _finding(
            "base-is-default-branch",
            pr.base_branch == repo.default_branch,
            f"base={pr.base_branch or 'MISSING'}; expected {repo.default_branch}",
        )
    )
    findings.append(_finding("title-present", bool(pr.title.strip()), "PR title is present"))
    findings.append(_finding("body-present", pr.body_present, "PR body is present"))
    findings.append(
        _finding(
            "head-is-full-sha",
            _is_full_sha(pr.head_sha),
            f"PR head={pr.head_sha or 'MISSING'}; full 40-character SHA required",
        )
    )
    findings.append(
        _finding(
            "mergeable",
            pr.mergeable.upper() in MERGEABLE_STATES,
            f"mergeable={pr.mergeable}; expected one of {sorted(MERGEABLE_STATES)}",
        )
    )
    findings.append(
        _finding(
            "feature-branch",
            bool(local.branch) and local.branch != repo.default_branch,
            f"local branch={local.branch or 'DETACHED'}; direct default-branch work is forbidden",
        )
    )
    findings.append(
        _finding(
            "local-branch-matches-pr",
            local.branch == pr.head_branch,
            f"local={local.branch or 'DETACHED'}; PR={pr.head_branch or 'MISSING'}",
        )
    )
    findings.append(
        _finding(
            "local-head-matches-pr-head",
            _is_full_sha(local.head_sha)
            and _is_full_sha(pr.head_sha)
            and local.head_sha == pr.head_sha,
            f"local HEAD={local.head_sha}; PR HEAD={pr.head_sha}",
        )
    )
    findings.append(
        _finding(
            "worktree-clean",
            not local.dirty_paths,
            "no uncommitted paths" if not local.dirty_paths else f"dirty={list(local.dirty_paths)}",
        )
    )

    for required in required_checks:
        matching = next(
            (
                run
                for run in check_runs
                if run.name == required and same_exact_head(pr.head_sha, run.head_sha)
            ),
            None,
        )
        passed = bool(
            matching and matching.status == "completed" and matching.conclusion in PASS_CONCLUSIONS
        )
        if matching is None:
            message = f"{required}: no run for exact HEAD {pr.head_sha}"
        else:
            message = (
                f"{required}: status={matching.status}, conclusion={matching.conclusion}, "
                f"head={matching.head_sha}"
            )
        findings.append(_finding(f"required-check:{required}", passed, message))

    return PreflightResult(
        repo=repo,
        pr=pr,
        local=local,
        required_checks=required_checks,
        check_runs=check_runs,
        findings=findings,
    )


def format_json(result: PreflightResult) -> str:
    """Render readiness evidence as machine-readable JSON."""
    return json.dumps(
        {
            "verdict": result.verdict,
            "repository": result.repo.name_with_owner,
            "default_branch": result.repo.default_branch,
            "pr": {
                "number": result.pr.number,
                "state": result.pr.state,
                "draft": result.pr.is_draft,
                "base_branch": result.pr.base_branch,
                "head_branch": result.pr.head_branch,
                "head_sha": result.pr.head_sha,
                "mergeable": result.pr.mergeable,
                "title_present": bool(result.pr.title.strip()),
                "body_present": result.pr.body_present,
            },
            "local": {
                "branch": result.local.branch,
                "head_sha": result.local.head_sha,
                "dirty_paths": list(result.local.dirty_paths),
            },
            "required_checks": list(result.required_checks),
            "findings": [
                {"name": finding.name, "passed": finding.passed, "message": finding.message}
                for finding in result.findings
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


def format_human(result: PreflightResult) -> str:
    """Render readiness evidence for a human operator."""
    lines = [
        "=" * 72,
        "  Canonical PR Ready Check (read-only)",
        "=" * 72,
        f"  Repository:       {result.repo.name_with_owner}",
        f"  PR:               #{result.pr.number} {result.pr.head_branch}",
        f"  PR HEAD:          {result.pr.head_sha}",
        f"  Local branch:      {result.local.branch or 'DETACHED'}",
        f"  Local HEAD:        {result.local.head_sha}",
        f"  Required checks:   {', '.join(result.required_checks)}",
        "-" * 72,
    ]
    for finding in result.findings:
        marker = "PASS" if finding.passed else "FAIL"
        lines.append(f"  [{marker}] {finding.name}: {finding.message}")
    lines.extend(("-" * 72, f"  VERDICT:           {result.verdict}", "=" * 72))
    return "\n".join(lines)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canonical read-only PR ready check")
    parser.add_argument("--pr", type=int, required=True, help="PR number to evaluate")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the read-only check and return 0, 1, or 2."""
    args = _parse_args(argv)
    try:
        result = evaluate(args.pr)
    except (PreflightError, ValueError) as exc:
        print(f"ERROR: PR ready evidence unavailable: {exc}", file=sys.stderr)
        return 2
    print(format_json(result) if args.json else format_human(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
