#!/usr/bin/env python3
"""PR body and CI evidence check - read-only, no merge, no write.

lifecycle: permanent

Fetches the live PR body from GitHub, validates it with the AI workflow gate,
and verifies that the body records current-head CI evidence.

Usage:
  python3 scripts/devops/pr_body_check.py --pr 1476

PASS conditions (ALL must be true):
  - PR exists and is open
  - PR body is fetched from GitHub
  - AI workflow gate passes against the fetched body
  - Body does not contain obvious stale pending/test-count evidence
  - Body contains the current head SHA prefix
  - Body contains the changed files count
  - Body contains the latest Production Gate run id for the current head SHA
  - Production Gate run is for the current head SHA
  - Production Gate status is completed and conclusion is success
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_GATE_WORKFLOW = "Production Gate"
TIMEOUT_SECONDS = 30
MIN_SHA_LENGTH = 7

STALE_BODY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"GitHub\s+Production\s+Gate\s*\|\s*pending", re.IGNORECASE),
        "PR body still says 'GitHub Production Gate | pending'",
    ),
    (
        re.compile(r"(?<!GitHub\s)Production\s+Gate\s*\|\s*pending", re.IGNORECASE),
        "PR body still says 'Production Gate | pending'",
    ),
    (
        re.compile(r"pytest\s*:\s*50\s+passed", re.IGNORECASE),
        "PR body still contains stale 'pytest: 50 passed' evidence",
    ),
)


@dataclass
class PrInfo:
    """Normalized PR metadata extracted from ``gh pr view --json``."""

    number: int
    title: str
    state: str
    head_sha: str
    changed_files: int
    body: str | None

    @property
    def short_sha(self) -> str:
        """Return the short SHA used in PR body evidence."""
        return self.head_sha[:MIN_SHA_LENGTH] if self.head_sha else ""

    @classmethod
    def from_gh_json(cls, number: int, data: dict[str, Any]) -> PrInfo:
        """Construct PrInfo from ``gh pr view --json`` output."""
        return cls(
            number=number,
            title=data.get("title", ""),
            state=data.get("state", "UNKNOWN"),
            head_sha=data.get("headRefOid", ""),
            changed_files=int(data.get("changedFiles", 0) or 0),
            body=data.get("body"),
        )

    @classmethod
    def missing(cls, number: int) -> PrInfo:
        """Return placeholder PR info when GitHub fetch fails."""
        return cls(
            number=number, title="", state="UNKNOWN", head_sha="", changed_files=0, body=None
        )


@dataclass
class CiInfo:
    """Production Gate result extracted from ``gh run list --json``."""

    workflow_name: str
    run_id: str | None
    status: str
    conclusion: str
    head_sha: str

    @classmethod
    def empty(cls) -> CiInfo:
        """Return a CiInfo representing a missing CI run."""
        return cls(
            workflow_name=PRODUCTION_GATE_WORKFLOW,
            run_id=None,
            status="",
            conclusion="",
            head_sha="",
        )


@dataclass
class AIWorkflowGateResult:
    """Result of running scripts/ops/ai_workflow_gate.py against the PR body."""

    passed: bool
    exit_code: int | None
    summary: str
    stdout: str = ""
    stderr: str = ""

    @classmethod
    def skipped(cls, reason: str) -> AIWorkflowGateResult:
        """Return a skipped AI workflow gate result."""
        return cls(passed=False, exit_code=None, summary=f"SKIPPED: {reason}")


@dataclass
class PrBodyCheckResult:
    """Aggregate PR body check verdict and evidence."""

    pr: PrInfo
    ci: CiInfo
    ai_gate: AIWorkflowGateResult
    passed: bool
    failures: list[str] = field(default_factory=list)

    def verdict(self) -> str:
        """Return 'PASS' or 'FAIL'."""
        return "PASS" if self.passed else "FAIL"


def run_gh(args: list[str]) -> str:
    """Run a read-only ``gh`` command and return stdout."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    result.check_returncode()
    return result.stdout.strip()


def fetch_pr(number: int) -> PrInfo:
    """Fetch PR metadata and live body via ``gh pr view --json``."""
    raw = run_gh(
        [
            "pr",
            "view",
            str(number),
            "--json",
            "title,state,headRefOid,changedFiles,body",
        ]
    )
    return PrInfo.from_gh_json(number, json.loads(raw))


def fetch_ci(head_sha: str) -> CiInfo:
    """Find the most recent Production Gate run for ``head_sha``."""
    if not head_sha:
        return CiInfo.empty()

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
                "name,status,conclusion,databaseId,headSha",
            ]
        )
    except subprocess.CalledProcessError:
        return CiInfo.empty()

    entries: list[dict[str, Any]] = json.loads(raw)
    if not entries:
        return CiInfo.empty()

    entry = entries[0]
    run_id = entry.get("databaseId")
    return CiInfo(
        workflow_name=entry.get("name", PRODUCTION_GATE_WORKFLOW),
        run_id=str(run_id) if run_id is not None else None,
        status=entry.get("status", ""),
        conclusion=entry.get("conclusion", ""),
        head_sha=entry.get("headSha", ""),
    )


def _first_nonempty_line(text: str) -> str:
    """Return the first non-empty line from text, or an empty string."""
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def run_ai_workflow_gate(body: str) -> AIWorkflowGateResult:
    """Run the existing AI workflow gate against fetched PR body text."""
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as tmp:
            tmp.write(body)
            tmp_path = Path(tmp.name)

        result = subprocess.run(
            [
                "python3",
                "scripts/ops/ai_workflow_gate.py",
                "--pr-body-file",
                str(tmp_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    summary = _first_nonempty_line(result.stdout) or _first_nonempty_line(result.stderr)
    if not summary:
        summary = "PASS" if result.returncode == 0 else "FAIL"
    return AIWorkflowGateResult(
        passed=result.returncode == 0,
        exit_code=result.returncode,
        summary=summary,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _body_contains_changed_files_count(body: str, changed_files: int) -> bool:
    """Return true if body contains changed-files evidence for the current count."""
    count = re.escape(str(changed_files))
    patterns = (
        rf"changed[\s_-]+files?\s*[:=|]\s*{count}\b",
        rf"\b{count}\s+changed[\s_-]+files?\b",
        rf"\b{count}\s+files?\s+changed\b",
    )
    return any(re.search(pattern, body, re.IGNORECASE) for pattern in patterns)


def _check_pr(pr: PrInfo) -> list[str]:
    failures: list[str] = []
    if pr.body is None:
        failures.append("PR does not exist or PR body could not be fetched from GitHub")
    if pr.state.upper() != "OPEN":
        failures.append(f"PR state is '{pr.state}', expected 'OPEN'")
    if not pr.head_sha or len(pr.head_sha) < MIN_SHA_LENGTH:
        failures.append("Head SHA is empty or too short")
    return failures


def _check_ci(ci: CiInfo, expected_head_sha: str) -> list[str]:
    failures: list[str] = []
    if ci.run_id is None:
        failures.append(f"Production Gate run not found for head SHA {expected_head_sha or 'N/A'}")
        return failures
    if ci.head_sha != expected_head_sha:
        failures.append(
            f"Production Gate run head SHA is '{ci.head_sha or 'N/A'}', expected '{expected_head_sha}'"
        )
    if ci.status != "completed":
        failures.append(f"Production Gate status is '{ci.status}', expected 'completed'")
    if ci.conclusion != "success":
        failures.append(f"Production Gate conclusion is '{ci.conclusion}', expected 'success'")
    return failures


def _check_body_evidence(pr: PrInfo, ci: CiInfo) -> list[str]:
    failures: list[str] = []
    body = pr.body or ""

    if not body.strip():
        failures.append("PR body is empty")

    for pattern, message in STALE_BODY_PATTERNS:
        if pattern.search(body):
            failures.append(message)

    if pr.short_sha and pr.short_sha not in body:
        failures.append(f"PR body does not contain current head SHA prefix {pr.short_sha}")

    if not _body_contains_changed_files_count(body, pr.changed_files):
        failures.append(f"PR body does not contain changed files count {pr.changed_files}")

    if ci.run_id is not None and ci.run_id not in body:
        failures.append(f"PR body does not contain latest Production Gate run id {ci.run_id}")

    return failures


def evaluate(pr_number: int) -> PrBodyCheckResult:
    """Fetch live PR body + CI evidence and return a verdict."""
    failures: list[str] = []

    try:
        pr = fetch_pr(pr_number)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        pr = PrInfo.missing(pr_number)
        ci = CiInfo.empty()
        ai_gate = AIWorkflowGateResult.skipped("PR body unavailable")
        failures.append(f"PR fetch failed: {exc}")
        failures.extend(_check_pr(pr))
        return PrBodyCheckResult(pr=pr, ci=ci, ai_gate=ai_gate, passed=False, failures=failures)

    failures.extend(_check_pr(pr))
    ci = fetch_ci(pr.head_sha)
    failures.extend(_check_ci(ci, pr.head_sha))

    if pr.body is None:
        ai_gate = AIWorkflowGateResult.skipped("PR body unavailable")
    else:
        ai_gate = run_ai_workflow_gate(pr.body)
        if not ai_gate.passed:
            failures.append(f"AI workflow gate failed: {ai_gate.summary}")

    failures.extend(_check_body_evidence(pr, ci))

    return PrBodyCheckResult(
        pr=pr,
        ci=ci,
        ai_gate=ai_gate,
        passed=len(failures) == 0,
        failures=failures,
    )


def format_evidence(result: PrBodyCheckResult) -> str:
    """Render a human-readable evidence report."""
    lines = [
        "=" * 60,
        "  PR Body Check Evidence",
        "=" * 60,
        f"  PR Number:                    {result.pr.number}",
        f"  PR Title:                     {result.pr.title or 'N/A'}",
        f"  PR State:                     {result.pr.state}",
        f"  Head SHA:                     {result.pr.head_sha or 'N/A'}",
        f"  Changed Files:                {result.pr.changed_files}",
        "-" * 60,
        f"  Production Gate Run ID:       {result.ci.run_id or 'NOT FOUND'}",
        f"  Production Gate Head SHA:     {result.ci.head_sha or 'N/A'}",
        f"  Production Gate Status:       {result.ci.status or 'N/A'}",
        f"  Production Gate Conclusion:   {result.ci.conclusion or 'N/A'}",
        "-" * 60,
        f"  AI Workflow Gate Result:      {result.ai_gate.summary}",
        "-" * 60,
        f"  Final Verdict:                {result.verdict()}",
    ]

    if result.failures:
        lines.append("-" * 60)
        lines.append("  Failures:")
        lines.extend(f"    - {failure}" for failure in result.failures)

    lines.append("=" * 60)
    return "\n".join(lines)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PR body and CI evidence check (read-only)")
    parser.add_argument("--pr", type=int, required=True, help="PR number to evaluate")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the PR body check and exit with 0 on PASS, 1 on FAIL."""
    args = _parse_args(argv)
    result = evaluate(args.pr)
    print(format_evidence(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
