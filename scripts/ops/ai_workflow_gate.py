#!/usr/bin/env python3
"""AI workflow gate — CI-enforceable P0 AI/Codex risk checks.

lifecycle: permanent
"""

from __future__ import annotations

import argparse
import contextlib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

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
    "## SC-002 status",
    "## Remaining risks",
)

NEXT_TASK_MANDATORY_PHRASES: tuple[str, ...] = (
    "Do not start automatically",
    "Recommended next task only after user confirmation",
)

DANGEROUS_NETWORK_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:axios|node-fetch|aiohttp|curl_cffi)\b",
        r"""require\s*\(\s*['"]got['"]\s*\)|from\s+['"]got['"]|import\s+got\b""",
        r"\bhttps?\.request\b",
        r"\brequests\.(?:get|post|put|delete)\b",
        r"\bhttpx\.(?:get|post)\b",
        r"\bfetch\s*\(",
    )
)

DANGEROUS_BROWSER_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"""require\s*\(\s*['"](?:playwright|puppeteer|selenium-webdriver)['"]\s*\)""",
        r"""from\s+['"](?:playwright|puppeteer|selenium)['"]""",
        r"""import\s+(?:playwright|puppeteer|selenium)\b""",
        r"\bchromium\.launch\b",
        r"\b(?:browser\.new_page|page\.goto)\b",
    )
)

DANGEROUS_DB_WRITE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bINSERT\s+INTO\b",
        r"\bUPDATE\s+\w+\s+SET\b",
        r"\bDELETE\s+FROM\b",
        r"\bexecute\s*\(.*(?:INSERT|UPDATE|DELETE)",
        r"\bexecutemany\s*\(",
        r"\b(?:db|connection|cursor)\.execute\b",
        r"\.query\s*\(\s*['\"]\s*(?:INSERT|UPDATE|DELETE)",
    )
)

DANGEROUS_BYPASS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        "--no" + "-verify",
        r"\b" + "no" + r"-verify\b",
    )
)

PROXY_BYPASS_RAW_IMPORTS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        r"""require\s*\(\s*['"](?:axios|node-fetch|got)['"]\s*\)""",
        r"""from\s+['"](?:axios|node-fetch)['"]""",
        r"""import\s+axios\b""",
        r"""import\s+fetch\s+from""",
    )
)

DANGEROUS_PATTERN_GROUPS: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = (
    ("network", DANGEROUS_NETWORK_PATTERNS),
    ("browser", DANGEROUS_BROWSER_PATTERNS),
    ("DB write", DANGEROUS_DB_WRITE_PATTERNS),
    ("hook bypass", DANGEROUS_BYPASS_PATTERNS),
    ("proxy bypass", PROXY_BYPASS_RAW_IMPORTS),
)

BUSINESS_CODE_PATH_PREFIXES: tuple[str, ...] = (
    "src/",
    "database/migrations/",
    "scripts/data/",
    "models/",
    "training/",
)

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

AUTHORITATIVE_DOC_PATHS: frozenset[str] = frozenset(
    {
        "docs/PROJECT_STATUS.md",
        "docs/DOCUMENTATION_GOVERNANCE.md",
        "docs/CODEX_WORKFLOW.md",
        "docs/AGENT_WORKFLOW.md",
        "docs/DATA_SOURCE_STRATEGY.md",
        "docs/data/FOTMOB_CURRENT_STATE.md",
        "README.md",
    }
)

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

MAX_DOC_SPRAWL_NEW_FILES = 2
REPORT_ARTIFACT_PREFIX = "docs/_reports/"
REPORT_ARTIFACT_SUFFIX = ".md"
SOURCE_OF_TRUTH_REASON_LABELS: tuple[str, ...] = (
    "Source-of-truth no-update reason",
    "If not updated, explicit reason",
)
HOLLOW_NO_UPDATE_REASONS: frozenset[str] = frozenset(
    {
        "",
        "n/a",
        "na",
        "none",
        "null",
        "no",
        "not needed",
        "not applicable",
        "无",
        "无需",
        "暂不需要",
    }
)
MIN_SOURCE_OF_TRUTH_REASON_CHARS = 12

BLIND_SPOT_DIR_PREFIXES: tuple[str, ...] = ("docs/", "tests/")

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

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.ops.helpers.section_content_quality import check_section_content_quality  # noqa: E402, I001
from scripts.ops.helpers.pr_authorization_matrix import (  # noqa: E402
    narrow_blocking_errors,
    parse_task_type,
    run_pr_authorization_matrix_report_only,
    validate_authorization,
)


# Git change detection — delegated to dedicated helper
# to keep this file under the 800-line gatekeeper limit.
from scripts.ops.helpers.git_change_helpers import (  # noqa: E402
    Change,
    IncrementalScanResult,
    added_paths,
    changed_paths,
    collect_changes,
    git_output,
    parse_name_status,  # noqa: F401 — re-exported for local_pr_gate_preflight
    resolve_comparison_refs,
    scan_incremental_findings,
)


def _normalise(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_pr_body(file_path: str | None = None, *, from_stdin: bool = False) -> str:
    """Return the PR body text from a file, stdin, or git log fallback."""

    if file_path:
        return _normalise(Path(file_path).read_text(encoding="utf-8"))
    if from_stdin:
        return _normalise(sys.stdin.read())
    return _normalise(git_output(["log", "--format=%B", "-1", "HEAD"], check=False))


def section_present(pr_body: str, heading: str) -> bool:
    """Check if *heading* appears as a section title (ATX or HTML comment marker)."""
    return heading in pr_body


def section_text_between(pr_body: str, start_heading: str, next_heading: str | None = None) -> str:
    """Return text between *start_heading* and the next `##` heading (or end-of-body)."""
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


def check_required_sections(pr_body: str) -> list[str]:
    """Return missing required section headings."""

    return [heading for heading in REQUIRED_SECTIONS if not section_present(pr_body, heading)]


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


def _touches_report_artifact(changes: list[Change]) -> bool:
    return any(
        c.status != "D"
        and c.path.startswith(REPORT_ARTIFACT_PREFIX)
        and c.path.endswith(REPORT_ARTIFACT_SUFFIX)
        for c in changes
    )


def _extract_table_value(pr_body: str, labels: tuple[str, ...]) -> str:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(
        rf"^\|\s*(?:{label_pattern})\s*\|\s*(.*?)\s*\|", re.IGNORECASE | re.MULTILINE
    )
    match = pattern.search(pr_body)
    return match.group(1).strip().strip("`").strip() if match else ""


def _has_substantive_no_update_reason(pr_body: str) -> bool:
    reason = _extract_table_value(pr_body, SOURCE_OF_TRUTH_REASON_LABELS)
    normalized = re.sub(r"\s+", " ", reason).strip().strip(".:-").lower()
    return (
        len(normalized) >= MIN_SOURCE_OF_TRUTH_REASON_CHARS
        and normalized not in HOLLOW_NO_UPDATE_REASONS
    )


def check_authoritative_report_backflow(pr_body: str, changes: list[Change]) -> list[str]:
    """Require source-of-truth update or explicit reason when reports change."""

    if not _touches_report_artifact(changes):
        return []
    changed = changed_paths(changes)
    if changed & AUTHORITATIVE_DOC_PATHS:
        return []
    if _has_substantive_no_update_reason(pr_body):
        return []
    return [
        "docs/_reports/*.md changed without updating source-of-truth docs or "
        "a substantive Source-of-truth no-update reason in the PR body."
    ]


def _is_blind_spot_path(path: str) -> bool:
    """Check if *path* is under docs/ or tests/ AND is a code file."""
    if not any(path.startswith(px) for px in BLIND_SPOT_DIR_PREFIXES):
        return False
    suffix = Path(path).suffix.lower()
    return suffix in BLIND_SPOT_CODE_EXTENSIONS


def scan_dangerous_keywords_incremental(
    changes: list[Change],
    *,
    base_ref: str | None = None,
    head_ref: str | None = None,
) -> IncrementalScanResult:
    """Compare normalized dangerous findings between base and head revisions."""
    return scan_incremental_findings(
        changes,
        path_predicate=_is_blind_spot_path,
        pattern_groups=DANGEROUS_PATTERN_GROUPS,
        base_ref=base_ref,
        head_ref=head_ref,
        error_prefix="new dangerous keyword in blind-spot path",
    )


def check_dangerous_keywords_in_blind_spots(
    changed: set[str],
    *,
    changes: list[Change] | None = None,
    base_ref: str | None = None,
    head_ref: str | None = None,
    emit_summary: bool = False,
) -> list[str]:
    """Block only dangerous findings newly introduced by the current diff."""
    effective_changes = (
        changes if changes is not None else [Change("M", path) for path in sorted(changed)]
    )
    result = scan_dangerous_keywords_incremental(
        effective_changes,
        base_ref=base_ref,
        head_ref=head_ref,
    )
    if emit_summary:
        summary = result.summary
        print(
            "[AI Workflow Gate] incremental scan "
            f"base={summary.base_ref} head={summary.head_ref} "
            f"scanned_files={summary.scanned_files} "
            f"base_violations={summary.base_violations} "
            f"head_violations={summary.head_violations} "
            f"new_violations={summary.new_violations} "
            f"removed_violations={summary.removed_violations} "
            "unchanged_historical_violations="
            f"{summary.unchanged_historical_violations}"
        )
    return list(result.errors)


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

    db_declared_no = _safety_declared_no(pr_body, r"DB\s+used") or _safety_status_no(
        pr_body, r"DB\s+writes"
    )
    if db_declared_no and _touches_any(changed, DB_TOUCH_PATHS):
        touching = sorted(p for p in changed if any(p.startswith(px) for px in DB_TOUCH_PATHS))
        errors.append(
            "Safety declaration says no DB, but changed files touch DB paths: "
            + ", ".join(touching)
        )

    scraper_declared_no = _safety_declared_no(pr_body, r"Scraper\s+run") or _safety_status_no(
        pr_body, r"scraper"
    )
    if scraper_declared_no and _touches_any(changed, SCRAPER_TOUCH_PATHS):
        touching = sorted(p for p in changed if any(p.startswith(px) for px in SCRAPER_TOUCH_PATHS))
        errors.append(
            "Safety declaration says no scraper, but changed files touch scraper/data paths: "
            + ", ".join(touching)
        )

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


# Garbage prevention checks (G1 P0) — delegated to dedicated helper
# to keep this file under the 800-line gatekeeper limit.
# Agent workflow hardening checks (Phase1) — delegated to dedicated helper
# to keep this file under the 800-line gatekeeper limit.
from scripts.ci.governance_growth_gate import run_governance_growth_gate  # noqa: E402
from scripts.ops.helpers.agent_workflow_hardening_checks import (  # noqa: E402
    check_forbidden_rewrite_patterns,
    check_forbidden_safety_claims,
    check_large_risky_change,
)
from scripts.ops.helpers.dangerous_file_change_check import (  # noqa: E402
    check_dangerous_file_changes,
)
from scripts.ops.helpers.garbage_prevention_checks import (  # noqa: E402
    check_no_generated_artifacts_wrapper,
    check_report_lifecycle_required,
    check_report_restricted_task_type,
)
from scripts.ops.helpers.governance_p1_checks import (  # noqa: E402
    check_dangerous_auth_path_cross_validation,
    check_no_archive_runtime_import,
    check_script_lifecycle_requirement,
)


def validate(  # noqa: C901, PLR0912, PLR0915
    pr_body: str,
    changes: list[Change] | None = None,
    *,
    skip_body_checks: bool = False,
    block_matrix: bool = False,
    base_ref: str | None = None,
    head_ref: str | None = None,
) -> list[str]:
    """Run all AI workflow gate checks.  Returns a list of error strings.

    When *block_matrix* is True, the narrow A-L PR authorization matrix subset
    is added to errors (G1 expanded from original A-D).  Default False
    (report-only, #1651 Phase 5R8-D/G).
    """

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

    # 4b. Report artifacts require source-of-truth backflow or explicit reason
    if not skip_body_checks:
        errors.extend(check_authoritative_report_backflow(pr_body, changes))

    # 4c. Report-restricted task type: non-docs/governance PRs cannot add reports (P0-3)
    if not skip_body_checks:
        errors.extend(
            check_report_restricted_task_type(added, pr_body, skip_body_checks=skip_body_checks)
        )

    # 4d. Report lifecycle required when docs/_reports files are added (P0-3)
    if not skip_body_checks:
        errors.extend(
            check_report_lifecycle_required(added, pr_body, skip_body_checks=skip_body_checks)
        )

    # 4e. No-generated-artifacts: block temp/cache/log/build/coverage artifacts (P0-2)
    errors.extend(check_no_generated_artifacts_wrapper(added))

    # 5. Dangerous keywords in docs/tests blind spots
    errors.extend(
        check_dangerous_keywords_in_blind_spots(
            changed,
            changes=changes,
            base_ref=base_ref,
            head_ref=head_ref,
            emit_summary=True,
        )
    )

    # 6. Safety declaration consistency (only when body is available)
    if not skip_body_checks:
        errors.extend(check_safety_consistency(pr_body, changed))

    # 6b. Dangerous file path guard
    if not skip_body_checks:
        errors.extend(check_dangerous_file_changes(changed, pr_body))

    # 6c. Forbidden rewrite file patterns (new files only)
    if not skip_body_checks:
        errors.extend(check_forbidden_rewrite_patterns(added, pr_body))
    # 6d. Large risky change detection
    errors.extend(check_large_risky_change(changes, pr_body))

    # 6e. Forbidden safety claims
    if not skip_body_checks:
        errors.extend(check_forbidden_safety_claims(pr_body))
    # 7. Critical section content quality (only when body is available)
    if not skip_body_checks:
        errors.extend(
            check_section_content_quality(
                pr_body,
                lambda heading, body: section_text_between(body, heading),
            )
        )
        # 8. PR authorization matrix — report-only (#1651 Phase 5R8-D)
        with contextlib.suppress(Exception):
            run_pr_authorization_matrix_report_only(changed, pr_body)
        # 8b. optional narrow blocking (Phase 5R8-G, only when --block-matrix)
        if block_matrix:
            try:
                task_type = parse_task_type(pr_body)
                result = validate_authorization(task_type, changed, pr_body=pr_body)
                errors.extend(narrow_blocking_errors(result))
            except Exception as exc:
                errors.append(f"PR authorization matrix blocking check failed: {exc}")

    # 9. P1-1: no-archive-runtime-import (runs regardless of body checks)
    errors.extend(check_no_archive_runtime_import(changed))

    # 10. P1-2: dangerous-auth path cross-validation (requires body)
    if not skip_body_checks:
        errors.extend(check_dangerous_auth_path_cross_validation(changed, pr_body))

    # 11. P1-3: script lifecycle requirement for newly added scripts (requires body)
    if not skip_body_checks:
        errors.extend(check_script_lifecycle_requirement(added, pr_body))

    # 12. M2 Governance growth freeze gate — blocks new governance artifact growth.
    # Delegates to governance_growth_gate.py (orchestration) which uses
    # governance_reverse_dependency.py for Python AST + JS bounded scanning.
    if base_ref and head_ref:
        try:
            gov_errors = run_governance_growth_gate(ROOT, base_ref, head_ref)
            errors.extend(gov_errors)
        except Exception as exc:
            errors.append(f"GOV-GROWTH-GATE: Governance growth freeze check failed: {exc}")

    return errors


def check_db_write_guard_enforcement(changed: set[str]) -> tuple[list[str], list[str]]:
    """Run DB write guard enforcement scanner (phase2). Returns (errors, warnings)."""
    import importlib.util  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    helper = Path(__file__).resolve().parent / "helpers" / "db_write_guard_advisory_check.py"
    if not helper.exists():
        helper = Path.cwd() / "scripts" / "ops" / "helpers" / "db_write_guard_advisory_check.py"
        if not helper.exists():
            return [], []
    spec = importlib.util.spec_from_file_location("_dbga", str(helper))
    if spec is None or spec.loader is None:
        return [], []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "check_db_write_guard_enforcement", None)
    return fn(changed) if fn else ([], mod.check_db_write_guard_advisory(changed))


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for the AI workflow gate."""
    parser = argparse.ArgumentParser(description="AI workflow gate — P0 risk checks for PRs")
    body_group = parser.add_mutually_exclusive_group()
    body_group.add_argument("--pr-body-file", default=None, help="Read PR body from file")
    body_group.add_argument(
        "--pr-body-stdin", action="store_true", default=False, help="Read PR body from stdin"
    )
    parser.add_argument("--base-ref", default=None, help="Git base ref for diff")
    parser.add_argument("--head-ref", default=None, help="Git head ref for diff")
    parser.add_argument(
        "--skip-body-checks",
        action="store_true",
        default=False,
        help="Skip PR-body checks (push events)",
    )
    parser.add_argument(
        "--block-matrix",
        action="store_true",
        default=False,
        help="Enable narrow PR matrix blocking (default: report-only)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:  # noqa: C901, PLR0912
    """Run AI workflow gate checks and exit 0 (pass) or 1 (fail)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    pr_body = read_pr_body(args.pr_body_file, from_stdin=args.pr_body_stdin)
    if not pr_body.strip():
        if args.skip_body_checks:
            sys.stdout.write(
                "[AI Workflow Gate] Empty PR body — body checks skipped "
                "(--skip-body-checks). Running git-diff checks only.\n"
            )
        else:
            sys.stdout.write("FAIL: empty PR body — cannot validate AI workflow gate\n")
            return 1
    try:
        resolved_base, resolved_head = resolve_comparison_refs(args.base_ref, args.head_ref)
        changes = collect_changes(args.base_ref, args.head_ref)
    except RuntimeError as exc:
        sys.stderr.write(f"[AI Workflow Gate] {exc}\n")
        return 1
    changed = changed_paths(changes)
    errors = validate(
        pr_body,
        changes,
        skip_body_checks=args.skip_body_checks,
        block_matrix=args.block_matrix,
        base_ref=resolved_base,
        head_ref=resolved_head,
    )
    # 8. DB write guard enforcement — phase2 hard fail on changed-files violations
    try:
        db_errors, db_warnings = check_db_write_guard_enforcement(changed)
        errors.extend(db_errors)
        if db_warnings:
            sys.stdout.write(f"[DB-WRITE-GUARD ENFORCEMENT] {len(db_warnings)} note(s)\n")
            for w in db_warnings:
                sys.stdout.write(f"- {w}\n")
    except Exception as exc:
        sys.stdout.write(f"[DB-WRITE-GUARD ENFORCEMENT] scanner error: {exc}\n")
        if __import__("os").environ.get("CI") or __import__("os").environ.get("GITHUB_ACTIONS"):
            errors.append(f"[DB-WRITE-GUARD ENFORCEMENT] fail-closed in CI: {exc}")
    # 9-10. Python + SQL/migration DB write enforcement — Phase2A+2B
    _helpers = [
        ("python_db_write_enforcement_check.py", "PYTHON-DB-WRITE"),
        ("sql_migration_policy_enforcement_check.py", "SQL-MIGRATION"),
    ]
    for _hname, _label in _helpers:
        try:
            import importlib.util  # noqa: PLC0415

            _h = Path(__file__).resolve().parent / "helpers" / _hname
            if not _h.exists():
                _h = Path.cwd() / "scripts" / "ops" / "helpers" / _hname
            if _h.exists():
                _s = importlib.util.spec_from_file_location("_enf", str(_h))
                if _s and _s.loader:
                    _m = importlib.util.module_from_spec(_s)
                    _s.loader.exec_module(_m)
                    _m.run_gate_check(changed, errors)
        except Exception as exc:
            sys.stdout.write(f"[{_label} ENFORCEMENT] scanner error: {exc}\n")
            if __import__("os").environ.get("CI") or __import__("os").environ.get("GITHUB_ACTIONS"):
                errors.append(f"[{_label} ENFORCEMENT] fail-closed in CI: {exc}")
    if errors:
        sys.stdout.write(f"FAIL: {len(errors)} AI workflow gate error(s)\n")
        for error in errors:
            sys.stdout.write(f"- {error}\n")
        return 1
    sys.stdout.write("PASS: AI workflow gate checks passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
