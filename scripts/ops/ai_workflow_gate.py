#!/usr/bin/env python3
"""AI workflow gate — minimal CI-enforceable checks for P0 AI/Codex risks.

lifecycle: permanent

Checks enforced:
  1. PR body must contain all required sections (Scope, Documentation Impact,
     Safety Impact, Validation, CI Gate Scope, No-deletion/move/rename
     confirmation, Rollback Plan, Next Recommended Task).
  2. "Next Recommended Task" section must include both
     "Do not start automatically" and "Recommended next task only after user
     confirmation".
  3. PRs that modify both governance docs AND src/ business code in the same
     diff are blocked (mixed-governance detection).
  4. New docs/_reports, docs/_manifests, next-plan, review, or decision files
     beyond the allowed budget are blocked.
  5. Dangerous network / browser / DB-write / hook bypass / proxy-bypass
     keywords in new or modified files under docs/ or tests/ are flagged.
  6. Safety declarations of "no DB / no scraper / no browser" that contradict
     actually-changed file paths are blocked.
  7. Three critical sections (Documentation Impact, Validation, Rollback Plan)
     must contain substantive content — hollow placeholders such as "N/A",
     "none", "passed", or "revert PR" are rejected.

Usage:
  python scripts/ops/ai_workflow_gate.py --pr-body-file /tmp/pr_body.txt
  python scripts/ops/ai_workflow_gate.py --pr-body-stdin
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Required PR body sections (checked by heading text)
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS: tuple[str, ...] = (
    "## Summary",
    "## Scope",
    "## Documentation Impact",
    "## Safety Impact",
    "## Validation",
    "## CI Gate Scope",
    "## No deletion / no move / no rename confirmation",
    "## Rollback Plan",
    "## Next Recommended Task",
)

# ---------------------------------------------------------------------------
# Next Recommended Task mandatory phrases
# ---------------------------------------------------------------------------

NEXT_TASK_MANDATORY_PHRASES: tuple[str, ...] = (
    "Do not start automatically",
    "Recommended next task only after user confirmation",
)

# ---------------------------------------------------------------------------
# Dangerous keywords scanned inside docs/ and tests/ directories
# ---------------------------------------------------------------------------

DANGEROUS_NETWORK_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\baxios\b",
        r"\bnode-fetch\b",
        r"""require\s*\(\s*['"]got['"]\s*\)""",
        r"""from\s+['"]got['"]""",
        r"""import\s+got\b""",
        r"\bhttp\.request\b",
        r"\bhttps\.request\b",
        r"\brequests\.get\b",
        r"\brequests\.post\b",
        r"\brequests\.put\b",
        r"\brequests\.delete\b",
        r"\bhttpx\.get\b",
        r"\bhttpx\.post\b",
        r"\baiohttp\b",
        r"\bcurl_cffi\b",
        r"\bfetch\s*\(",
    )
)

DANGEROUS_BROWSER_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"""require\s*\(\s*['"]playwright['"]\s*\)""",
        r"""from\s+['"]playwright['"]""",
        r"""import\s+playwright\b""",
        r"""require\s*\(\s*['"]puppeteer['"]\s*\)""",
        r"""from\s+['"]puppeteer['"]""",
        r"""import\s+puppeteer\b""",
        r"""require\s*\(\s*['"]selenium-webdriver['"]\s*\)""",
        r"""from\s+['"]selenium['"]""",
        r"""import\s+selenium\b""",
        r"\bchromium\.launch\b",
        r"\bbrowser\.new_page\b",
        r"\bpage\.goto\b",
    )
)

DANGEROUS_DB_WRITE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bINSERT\s+INTO\b",
        r"\bUPDATE\s+\w+\s+SET\b",
        r"\bDELETE\s+FROM\b",
        r"\bexecute\s*\(.*INSERT",
        r"\bexecute\s*\(.*UPDATE",
        r"\bexecute\s*\(.*DELETE",
        r"\bexecutemany\s*\(",
        r"\bdb\.write\b",
        r"\bdb\.execute\b",
        r"\bconnection\.execute\b",
        r"\bcursor\.execute\b",
        r"\.query\s*\(\s*['\"]\s*INSERT",
        r"\.query\s*\(\s*['\"]\s*UPDATE",
        r"\.query\s*\(\s*['\"]\s*DELETE",
    )
)

DANGEROUS_BYPASS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        "--no" + "-verify",
        r"\b" + "no" + r"-verify\b",
    )
)

# Proxy-bypass: raw network imports without ProxyProvider in JS/TS files
PROXY_BYPASS_RAW_IMPORTS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        r"""require\s*\(\s*['"]axios['"]\s*\)""",
        r"""require\s*\(\s*['"]node-fetch['"]\s*\)""",
        r"""require\s*\(\s*['"]got['"]\s*\)""",
        r"""from\s+['"]axios['"]""",
        r"""from\s+['"]node-fetch['"]""",
        r"""import\s+axios\b""",
        r"""import\s+fetch\s+from""",
    )
)

# ---------------------------------------------------------------------------
# Path classification
# ---------------------------------------------------------------------------

# Paths considered "business code" (runtime behaviour)
BUSINESS_CODE_PATH_PREFIXES: tuple[str, ...] = (
    "src/",
    "database/migrations/",
    "scripts/data/",
    "models/",
    "training/",
)

# Paths considered "governance docs" — modifying these together with business
# code in the same PR is prohibited
GOVERNANCE_DOC_PATHS: frozenset[str] = frozenset(
    {
        "docs/CODEX_WORKFLOW.md",
        "docs/DOCUMENTATION_GOVERNANCE.md",
        "docs/AGENT_WORKFLOW.md",
        "docs/INGESTION_CONVERGENCE_GATE.md",
        ".github/pull_request_template.md",
        "AGENTS.md",
        "CLAUDE.md",
        "scripts/ops/documentation_governance_check.py",
        "scripts/ops/ai_workflow_gate.py",
        ".github/workflows/production-gate.yml",
    }
)

# High-risk paths used for safety-declaration cross-check
DB_TOUCH_PATHS: tuple[str, ...] = (
    "src/db/",
    "database/",
    "src/data/db_",
    "src/infrastructure/db_",
    "scripts/ops/db_",
)
SCRAPER_TOUCH_PATHS: tuple[str, ...] = (
    "src/scraper/",
    "src/data/scraper/",
    "scripts/scraper/",
    "src/data/fotmob",
    "scripts/ops/fotmob",
)
BROWSER_TOUCH_PATHS: tuple[str, ...] = (
    "src/browser/",
    "playwright",
    "chromium",
    "stealth",
)

# Doc-sprawl detection
DOC_SPRAWL_PREFIXES: tuple[str, ...] = (
    "docs/_reports/",
    "docs/_manifests/",
)
DOC_SPRAWL_NAME_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r".*next[_-]plan.*",
        r".*review.*report.*",
        r".*decision.*report.*",
    )
)

MAX_DOC_SPRAWL_NEW_FILES = 5

# Docs/tests directories subject to blind-spot keyword scanning
BLIND_SPOT_DIR_PREFIXES: tuple[str, ...] = ("docs/", "tests/")

# Only scan code file extensions for dangerous keywords.
# Markdown files in docs/ legitimately mention tool names as policy.
BLIND_SPOT_CODE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".sh",
        ".bash",
    }
)


# ---------------------------------------------------------------------------
# Check 7: critical section content quality (anti-hollow-compliance)
# Implemented in scripts/ops/helpers/section_content_quality.py to stay
# under the 800-line architecture limit enforced by gatekeeper.sh.
# ---------------------------------------------------------------------------

# Check 7 implementation lives in a helper module to stay under the 800-line
# architecture limit enforced by gatekeeper.sh.  Ensure the project root is
# on sys.path so the absolute import works in subprocess / CLI invocations.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.ops.helpers.section_content_quality import check_section_content_quality  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Change:
    """A single git change entry."""

    status: str  # A, M, D, R
    path: str
    old_path: str | None = None


NAME_STATUS_PATH_PARTS = 2
NAME_STATUS_RENAME_PARTS = 3


def git_output(args: list[str], *, check: bool = True) -> str:
    """Run a local Git command and return stdout."""

    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def find_base_ref() -> str:
    """Find a local base ref without network access."""

    for ref in ("origin/main", "main"):
        res = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if res.returncode == 0:
            return ref
    return "HEAD"


def parse_name_status(output: str) -> list[Change]:
    """Parse 'git diff --name-status' output."""

    changes: list[Change] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= NAME_STATUS_RENAME_PARTS:
            changes.append(Change("R", parts[2], parts[1]))
            continue
        if status.startswith("D") and len(parts) >= NAME_STATUS_PATH_PARTS:
            changes.append(Change("D", parts[1]))
            continue
        if status.startswith("A") and len(parts) >= NAME_STATUS_PATH_PARTS:
            changes.append(Change("A", parts[1]))
            continue
        if len(parts) >= NAME_STATUS_PATH_PARTS:
            changes.append(Change("M", parts[1]))
    return changes


def parse_porcelain(output: str) -> list[Change]:
    """Parse 'git status --porcelain' output."""

    changes: list[Change] = []
    for line in output.splitlines():
        if not line:
            continue
        code = line[:2]
        path = line[3:]
        if " -> " in path:
            old_path, new_path = path.split(" -> ", 1)
            changes.append(Change("R", new_path, old_path))
        elif code == "??" or "A" in code:
            changes.append(Change("A", path))
        elif "D" in code:
            changes.append(Change("D", path))
        else:
            changes.append(Change("M", path))
    return changes


def _unique_changes(changes: list[Change]) -> list[Change]:
    """Deduplicate changes by (status, path, old_path)."""

    seen: dict[tuple[str, str, str | None], Change] = {}
    for c in changes:
        key = (c.status, c.path, c.old_path)
        seen[key] = c
    return list(seen.values())


def collect_changes(base_ref: str | None = None) -> list[Change]:
    """Return all committed + uncommitted changes on the current branch."""

    base = base_ref or find_base_ref()
    diff_out = git_output(["diff", "--name-status", f"{base}...HEAD"])
    status_out = git_output(["status", "--porcelain"])
    return _unique_changes(
        [
            *parse_name_status(diff_out),
            *parse_porcelain(status_out),
        ]
    )


def added_paths(changes: list[Change]) -> set[str]:
    """Return the set of newly-added paths."""
    return {c.path for c in changes if c.status == "A"}


def changed_paths(changes: list[Change]) -> set[str]:
    """Return all changed paths (modified, added, renamed, deleted)."""

    paths = {c.path for c in changes}
    paths.update(c.old_path for c in changes if c.old_path)
    return paths


# ---------------------------------------------------------------------------
# PR body helpers
# ---------------------------------------------------------------------------


def _normalise(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_pr_body(file_path: str | None = None, *, from_stdin: bool = False) -> str:
    """Return the PR body text from a file, stdin, or git log fallback."""

    if file_path:
        return _normalise(Path(file_path).read_text(encoding="utf-8"))
    if from_stdin:
        return _normalise(sys.stdin.read())
    # Local fallback: read body of HEAD commit (best-effort)
    return _normalise(git_output(["log", "--format=%B", "-1", "HEAD"], check=False))


def section_present(pr_body: str, heading: str) -> bool:
    """Check whether *heading* appears as a section title in the PR body.

    Matches both ATX-style (`## Heading`) and the equivalent HTML comment
    marker that GitHub sometimes inserts.
    """
    return heading in pr_body


def section_text_between(pr_body: str, start_heading: str, next_heading: str | None = None) -> str:
    """Return the body text between *start_heading* and the next `##` heading.

    When *next_heading* is None the text from *start_heading* to end-of-body
    is returned.
    """
    idx = pr_body.find(start_heading)
    if idx == -1:
        return ""
    start = idx + len(start_heading)
    suffix = pr_body[start:]

    if next_heading is not None:
        end = suffix.find(next_heading)
        if end != -1:
            suffix = suffix[:end]
        return suffix

    # Stop at the next top-level/second-level heading or end-of-string
    end_marker = re.search(r"\n##\s", suffix)
    if end_marker:
        suffix = suffix[: end_marker.start()]
    return suffix


# ---------------------------------------------------------------------------
# Check 1: required PR body sections
# ---------------------------------------------------------------------------


def check_required_sections(pr_body: str) -> list[str]:
    """Return missing required section headings."""

    return [heading for heading in REQUIRED_SECTIONS if not section_present(pr_body, heading)]


# ---------------------------------------------------------------------------
# Check 2: "Do not start automatically" enforcement
# ---------------------------------------------------------------------------


def check_next_task_stop_phrase(pr_body: str) -> list[str]:
    """Verify the Next Recommended Task section contains mandatory phrases."""

    section = section_text_between(
        pr_body,
        "## Next Recommended Task",
    )
    if not section:
        return ["## Next Recommended Task section not found or empty"]

    return [
        f"## Next Recommended Task missing phrase: '{phrase}'"
        for phrase in NEXT_TASK_MANDATORY_PHRASES
        if phrase not in section
    ]


# ---------------------------------------------------------------------------
# Check 3: mixed governance + business code detection
# ---------------------------------------------------------------------------


def _touches_any(changed: set[str], prefixes: tuple[str, ...]) -> bool:
    return any(p.startswith(prefix) for p in changed for prefix in prefixes)


def _touches_governance_docs(changed: set[str]) -> bool:
    return bool(changed & GOVERNANCE_DOC_PATHS)


def _touches_business_code(changed: set[str]) -> bool:
    return _touches_any(changed, BUSINESS_CODE_PATH_PREFIXES)


def check_mixed_governance_business(changed: set[str]) -> list[str]:
    """Fail if the PR touches both governance docs and business source paths."""

    gov = _touches_governance_docs(changed)
    biz = _touches_business_code(changed)
    if gov and biz:
        gov_files = sorted(changed & GOVERNANCE_DOC_PATHS)
        biz_files = sorted(
            p for p in changed if any(p.startswith(px) for px in BUSINESS_CODE_PATH_PREFIXES)
        )
        return [
            "Mixed governance + business code in one PR is prohibited. "
            f"Governance: {', '.join(gov_files)}. "
            f"Business: {', '.join(biz_files)}"
        ]
    return []


# ---------------------------------------------------------------------------
# Check 4: document sprawl detection
# ---------------------------------------------------------------------------


def _count_doc_sprawl_new_files(added: set[str]) -> int:
    count = 0
    for path in added:
        if any(path.startswith(px) for px in DOC_SPRAWL_PREFIXES) or any(
            pat.match(path) for pat in DOC_SPRAWL_NAME_PATTERNS
        ):
            count += 1
    return count


def check_doc_sprawl(added: set[str]) -> list[str]:
    """Fail if too many report/manifest/plan files are added."""

    count = _count_doc_sprawl_new_files(added)
    if count > MAX_DOC_SPRAWL_NEW_FILES:
        return [
            f"Document sprawl detected: {count} new report/manifest/plan files "
            f"exceed the budget of {MAX_DOC_SPRAWL_NEW_FILES}"
        ]
    return []


# ---------------------------------------------------------------------------
# Check 5: dangerous keywords in docs/ and tests/ directories
# ---------------------------------------------------------------------------


def _is_blind_spot_path(path: str) -> bool:
    """Check if *path* is under docs/ or tests/ AND is a code file."""
    if not any(path.startswith(px) for px in BLIND_SPOT_DIR_PREFIXES):
        return False
    suffix = Path(path).suffix.lower()
    return suffix in BLIND_SPOT_CODE_EXTENSIONS


def _scan_file_for_patterns(file_path: Path, patterns: tuple[re.Pattern[str], ...]) -> list[str]:
    """Return matched patterns found in *file_path*."""

    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []
    hits: list[str] = []
    for pat in patterns:
        for m in pat.finditer(text):
            # Truncate match for readable error message
            snippet = m.group()[:80]
            hits.append(
                f"{file_path.relative_to(ROOT)}: pattern '{pat.pattern}' matched '{snippet}'"
            )
    return hits


def check_dangerous_keywords_in_blind_spots(
    changed: set[str],
) -> list[str]:
    """Flag dangerous keywords in new/modified files under docs/ or tests/."""

    errors: list[str] = []
    blind_spot_files = sorted(p for p in changed if _is_blind_spot_path(p))

    for rel_path in blind_spot_files:
        abs_path = ROOT / rel_path
        if not abs_path.is_file():
            continue

        for label, patterns in (
            ("network", DANGEROUS_NETWORK_PATTERNS),
            ("browser", DANGEROUS_BROWSER_PATTERNS),
            ("DB write", DANGEROUS_DB_WRITE_PATTERNS),
            ("hook bypass", DANGEROUS_BYPASS_PATTERNS),
            ("proxy bypass", PROXY_BYPASS_RAW_IMPORTS),
        ):
            hits = _scan_file_for_patterns(abs_path, patterns)
            errors.extend(f"[{label}] dangerous keyword in blind-spot path: {hit}" for hit in hits)

    return errors


# ---------------------------------------------------------------------------
# Check 6: safety declaration vs actual file changes consistency
# ---------------------------------------------------------------------------


def _safety_declared_no(pr_body: str, label: str) -> bool:
    """Check if the PR body declares a specific safety category as 'no'.

    Looks inside the Safety Impact and Safety Status sections for patterns
    like '| DB used | no' or '- no DB writes: yes'.
    """
    return bool(
        re.search(rf"\|\s*{label}\s*\|\s*no\b", pr_body, re.IGNORECASE)
        or re.search(rf"-\s*no\s+{label}\s*:\s*yes", pr_body, re.IGNORECASE)
    )


def _safety_status_no(pr_body: str, label: str) -> bool:
    """Check the Safety Status section for a 'yes' on a no-* line."""

    return bool(re.search(rf"-\s*no\s+{label}\s*:\s*yes", pr_body, re.IGNORECASE))


def check_safety_consistency(pr_body: str, changed: set[str]) -> list[str]:
    """Fail if safety declarations contradict the files actually changed."""

    errors: list[str] = []

    # DB check
    db_declared_no = _safety_declared_no(pr_body, r"DB\s+used") or _safety_status_no(
        pr_body, r"DB\s+writes"
    )
    if db_declared_no and _touches_any(changed, DB_TOUCH_PATHS):
        touching = sorted(p for p in changed if any(p.startswith(px) for px in DB_TOUCH_PATHS))
        errors.append(
            "Safety declaration says no DB, but changed files touch DB paths: "
            + ", ".join(touching)
        )

    # Scraper check
    scraper_declared_no = _safety_declared_no(pr_body, r"Scraper\s+run") or _safety_status_no(
        pr_body, r"scraper"
    )
    if scraper_declared_no and _touches_any(changed, SCRAPER_TOUCH_PATHS):
        touching = sorted(p for p in changed if any(p.startswith(px) for px in SCRAPER_TOUCH_PATHS))
        errors.append(
            "Safety declaration says no scraper, but changed files touch "
            "scraper/data paths: " + ", ".join(touching)
        )

    # Browser check
    browser_declared_no = _safety_declared_no(
        pr_body, r"Browser\s+automation\s+used"
    ) or _safety_status_no(pr_body, r"browser")
    if browser_declared_no and _touches_any(changed, BROWSER_TOUCH_PATHS):
        touching = sorted(p for p in changed if any(p.startswith(px) for px in BROWSER_TOUCH_PATHS))
        errors.append(
            "Safety declaration says no browser, but changed files touch "
            "browser/automation paths: " + ", ".join(touching)
        )

    return errors


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def validate(
    pr_body: str,
    changes: list[Change] | None = None,
    *,
    skip_body_checks: bool = False,
) -> list[str]:
    """Run all AI workflow gate checks.  Returns a list of error strings."""

    if changes is None:
        changes = collect_changes()

    added = added_paths(changes)
    changed = changed_paths(changes)

    errors: list[str] = []

    if not skip_body_checks:
        # 1. Required sections
        missing = check_required_sections(pr_body)
        if missing:
            errors.append(f"Missing required PR body sections: {', '.join(missing)}")

        # 2. Do not start automatically
        errors.extend(check_next_task_stop_phrase(pr_body))

    # 3. Mixed governance + business code
    errors.extend(check_mixed_governance_business(changed))

    # 4. Document sprawl
    errors.extend(check_doc_sprawl(added))

    # 5. Dangerous keywords in docs/tests blind spots
    errors.extend(check_dangerous_keywords_in_blind_spots(changed))

    # 6. Safety declaration consistency (only when body is available)
    if not skip_body_checks:
        errors.extend(check_safety_consistency(pr_body, changed))

    # 7. Critical section content quality (only when body is available)
    if not skip_body_checks:
        # Pass section_text_between to avoid circular import from helper.
        errors.extend(
            check_section_content_quality(
                pr_body,
                lambda heading, body: section_text_between(body, heading),
            )
        )

    return errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for the AI workflow gate."""
    parser = argparse.ArgumentParser(
        description="AI workflow gate — P0 risk checks for PRs",
    )
    body_group = parser.add_mutually_exclusive_group()
    body_group.add_argument(
        "--pr-body-file",
        default=None,
        help="Read PR body from this file path",
    )
    body_group.add_argument(
        "--pr-body-stdin",
        action="store_true",
        default=False,
        help="Read PR body from stdin",
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help="Git base ref for diff (default: auto-detect origin/main or main)",
    )
    parser.add_argument(
        "--skip-body-checks",
        action="store_true",
        default=False,
        help="Skip PR-body-specific checks (useful for push events)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run AI workflow gate checks and exit 0 (pass) or 1 (fail)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Read PR body
    pr_body = read_pr_body(
        args.pr_body_file,
        from_stdin=args.pr_body_stdin,
    )

    if not pr_body.strip():
        if args.skip_body_checks:
            sys.stdout.write(
                "[AI Workflow Gate] Empty PR body — body checks skipped "
                "(--skip-body-checks). Running git-diff checks only.\n"
            )
        else:
            sys.stdout.write("FAIL: empty PR body — cannot validate AI workflow gate\n")
            return 1

    # Collect git changes (optional base ref override)
    changes = collect_changes(args.base_ref)

    errors = validate(
        pr_body,
        changes,
        skip_body_checks=args.skip_body_checks,
    )

    if errors:
        sys.stdout.write(f"FAIL: {len(errors)} AI workflow gate error(s)\n")
        for error in errors:
            sys.stdout.write(f"- {error}\n")
        return 1

    sys.stdout.write("PASS: AI workflow gate checks passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
