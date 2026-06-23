#!/usr/bin/env python3
"""
Python DB Write Static Enforcement Scanner.

lifecycle: permanent
owner: DB write safety / ops governance
task: python_sql_migration_enforcement_implementation_phase2A

Static scanner for Python files that detects DB write risk signals.
Reads files as text — never imports, executes, or connects to DB.

Supports:
  - Scanning individual files or full repository
  - JSON and human-readable output
  - Allowlist-based exemption for historical files
  - Changed-files enforcement mode
  - Comment/docstring-aware detection (basic heuristics)

Does NOT:
  - Import or execute target Python files
  - Connect to any database
  - Run any SQL or migration
  - Access the network
  - Read environment secrets
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

# ── Project-root resolution ──────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# ── Signal patterns ──────────────────────────────────────────────────────────

# DB client / ORM / engine signals
DB_CLIENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("psycopg_import", re.compile(r"\b(import\s+psycopg|from\s+psycopg)", re.IGNORECASE)),
    ("psycopg2_import", re.compile(r"\b(import\s+psycopg2|from\s+psycopg2)", re.IGNORECASE)),
    ("asyncpg_import", re.compile(r"\b(import\s+asyncpg|from\s+asyncpg)", re.IGNORECASE)),
    ("sqlalchemy_import", re.compile(r"\b(import\s+sqlalchemy|from\s+sqlalchemy)", re.IGNORECASE)),
    ("create_engine", re.compile(r"\bcreate_engine\s*\(", re.IGNORECASE)),
    ("sqlite3_import", re.compile(r"\b(import\s+sqlite3|from\s+sqlite3)", re.IGNORECASE)),
    ("pandas_to_sql", re.compile(r"\.to_sql\s*\(", re.IGNORECASE)),
]

# Database URL / environment variable signals
DB_ENV_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("DATABASE_URL", re.compile(r"\bDATABASE_URL\b", re.IGNORECASE)),
    ("POSTGRES_DSN", re.compile(r"\bPOSTGRES_DSN\b", re.IGNORECASE)),
    ("POSTGRES_URL", re.compile(r"\bPOSTGRES_URL\b", re.IGNORECASE)),
    ("DB_CONNECTION_STRING", re.compile(r"\bDB_CONNECTION_STRING\b", re.IGNORECASE)),
    ("DATABASE_DSN", re.compile(r"\bDATABASE_DSN\b", re.IGNORECASE)),
]

# Execution function signals
EXECUTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("cursor_execute", re.compile(r"\.execute\s*\(", re.IGNORECASE)),
    ("executemany", re.compile(r"\.executemany\s*\(", re.IGNORECASE)),
    ("execute_batch", re.compile(r"\bexecute_batch\s*\(", re.IGNORECASE)),
    ("execute_values", re.compile(r"\bexecute_values\s*\(", re.IGNORECASE)),
    ("to_sql", re.compile(r"\.to_sql\s*\(", re.IGNORECASE)),
    ("copy_expert", re.compile(r"\bcopy_expert\s*\(", re.IGNORECASE)),
    ("copy_from", re.compile(r"\.copy_from\s*\(", re.IGNORECASE)),
    ("copy_to", re.compile(r"\.copy_to\s*\(", re.IGNORECASE)),
    ("session_execute", re.compile(r"session\.execute\s*\(", re.IGNORECASE)),
]

# SQL write / DDL / DML keyword signals
WRITE_KEYWORD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("INSERT", re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE)),
    ("UPDATE", re.compile(r"\bUPDATE\s+\w+\s+SET\b", re.IGNORECASE)),
    ("DELETE", re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE)),
    ("UPSERT", re.compile(r"\bUPSERT\b", re.IGNORECASE)),
    ("ON_CONFLICT", re.compile(r"\bON\s+CONFLICT\b", re.IGNORECASE)),
    ("CREATE_TABLE", re.compile(r"\bCREATE\s+TABLE\b", re.IGNORECASE)),
    ("ALTER_TABLE", re.compile(r"\bALTER\s+TABLE\b", re.IGNORECASE)),
    ("DROP_TABLE", re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE)),
    ("TRUNCATE", re.compile(r"\bTRUNCATE\b", re.IGNORECASE)),
    ("COPY_FROM", re.compile(r"\bCOPY\b.*\bFROM\b", re.IGNORECASE)),
    ("CREATE_DATABASE", re.compile(r"\bCREATE\s+DATABASE\b", re.IGNORECASE)),
    ("DROP_DATABASE", re.compile(r"\bDROP\s+DATABASE\b", re.IGNORECASE)),
    ("GRANT", re.compile(r"\bGRANT\s+\w+\s+ON\b", re.IGNORECASE)),
    ("REVOKE", re.compile(r"\bREVOKE\s+\w+\s+ON\b", re.IGNORECASE)),
]

# ── Comment/docstring detection ──────────────────────────────────────────────

# Lines that look like comments (Python single-line comments)
COMMENT_LINE_RE = re.compile(r"^\s*#")

# Start of a multi-line comment or docstring
DOCSTRING_START_RE = re.compile(r'^\s*("""|\'\'\')')

# A standalone SQL keyword in a comment/docstring
SQL_IN_COMMENT_RE = re.compile(
    r"(?:#|docstring|comment|example|note|preview).*"
    r"(?:INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE)",
    re.IGNORECASE,
)


def _is_comment_or_docstring_context(line: str, in_docstring: bool) -> bool:
    """Detect if a line is inside a comment or docstring context."""
    stripped = line.strip()
    if COMMENT_LINE_RE.match(stripped):
        return True
    if '"""' in stripped or "'''" in stripped:
        return True
    return bool(in_docstring)


def _classify_evidence_type(
    line: str,
    match_start: int,
    in_docstring: bool,
    in_comment: bool,
) -> str:
    """Classify the evidence type of a match (executable, comment, docstring, string)."""
    if in_comment:
        return "comment_context"
    if in_docstring:
        return "docstring_context"
    # Check if match is inside a string literal
    before = line[:match_start]
    if before.count('"') % 2 == 1 or before.count("'") % 2 == 1:
        return "string_literal"
    return "executable_context"


# ── File parsing ─────────────────────────────────────────────────────────────


def _read_file_lines(file_path: Path) -> list[str]:
    """Read file as text — never import or execute."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []
    return content.splitlines()


def _scan_file_for_signals(  # noqa: C901, PLR0912, PLR0915
    file_path: Path,
) -> dict[str, Any]:
    """Scan a single Python file for DB write risk signals.

    Returns a dict with signal evidence. Complexity is inherent:
    we must check multiple signal categories across all lines.
    """
    lines = _read_file_lines(file_path)
    if not lines:
        return {
            "path": str(file_path.relative_to(REPO_ROOT)),
            "classification": "unreadable_or_binary",
            "db_client_signals": [],
            "db_env_signals": [],
            "execution_signals": [],
            "write_keyword_signals": [],
            "evidence_lines": [],
            "allowlist_status": "not_in_allowlist",
            "requires_review": False,
            "would_fail_changed_files_gate": False,
        }

    db_client_signals: list[dict] = []
    db_env_signals: list[dict] = []
    execution_signals: list[dict] = []
    write_keyword_signals: list[dict] = []

    in_docstring = False

    for line_no, line in enumerate(lines, start=1):
        # Track docstring state (simple heuristic)
        if DOCSTRING_START_RE.match(line.strip()):
            in_docstring = not in_docstring

        in_comment = bool(COMMENT_LINE_RE.match(line.strip()))

        # Check DB client signals
        for name, pattern in DB_CLIENT_PATTERNS:
            for match in pattern.finditer(line):
                evidence_type = _classify_evidence_type(
                    line, match.start(), in_docstring, in_comment
                )
                db_client_signals.append(
                    {
                        "signal": name,
                        "line": line_no,
                        "match": match.group()[:80],
                        "evidence_type": evidence_type,
                    }
                )

        # Check DB env signals
        for name, pattern in DB_ENV_PATTERNS:
            for match in pattern.finditer(line):
                evidence_type = _classify_evidence_type(
                    line, match.start(), in_docstring, in_comment
                )
                db_env_signals.append(
                    {
                        "signal": name,
                        "line": line_no,
                        "match": match.group()[:80],
                        "evidence_type": evidence_type,
                    }
                )

        # Check execution signals
        for name, pattern in EXECUTION_PATTERNS:
            for match in pattern.finditer(line):
                evidence_type = _classify_evidence_type(
                    line, match.start(), in_docstring, in_comment
                )
                execution_signals.append(
                    {
                        "signal": name,
                        "line": line_no,
                        "match": match.group()[:80],
                        "evidence_type": evidence_type,
                    }
                )

        # Check write keyword signals
        for name, pattern in WRITE_KEYWORD_PATTERNS:
            for match in pattern.finditer(line):
                evidence_type = _classify_evidence_type(
                    line, match.start(), in_docstring, in_comment
                )
                write_keyword_signals.append(
                    {
                        "signal": name,
                        "line": line_no,
                        "match": match.group()[:80],
                        "evidence_type": evidence_type,
                    }
                )

    # ── Determine classification based on signal combinations ────────────────
    has_db_client = any(s["evidence_type"] == "executable_context" for s in db_client_signals)
    has_execution = any(s["evidence_type"] == "executable_context" for s in execution_signals)
    has_write_keyword = any(
        s["evidence_type"] == "executable_context" for s in write_keyword_signals
    )
    has_db_env = any(s["evidence_type"] == "executable_context" for s in db_env_signals)
    has_any_db = has_db_client or has_db_env

    # Check for test file context
    rel_path = str(file_path.relative_to(REPO_ROOT))
    is_test_file = rel_path.startswith("tests/") or "test" in file_path.name.lower()

    # Check for static scan context (scans other files, doesn't execute SQL itself)
    is_static_scan = (
        "advisory_check" in file_path.name
        or "_check." in file_path.name
        or "static_enforcement" in file_path.name
    )

    # Determine classification
    if not has_any_db and not has_execution and not has_write_keyword:
        classification = "python_no_db_connection"
    elif is_test_file:
        classification = "python_test_fixture_signal"
    elif is_static_scan and not has_execution:
        classification = "python_static_scan_only"
    elif has_db_client and has_execution and has_write_keyword:
        classification = "python_confirmed_write_risk"
    elif (has_db_client and has_execution) or (has_db_client and has_write_keyword):
        classification = "python_possible_write_risk"
    elif has_db_client or has_db_env:
        classification = "python_db_connection_no_write_detected"
    elif has_write_keyword and not has_db_client:
        classification = "python_write_keywords_no_db_client"
    elif has_execution and not has_db_client:
        classification = "python_execution_no_db_client"
    else:
        classification = "python_no_db_connection"

    # Determine if this would fail changed-files gate
    high_risk = classification in (
        "python_confirmed_write_risk",
        "python_possible_write_risk",
    )
    would_fail = high_risk and not is_test_file

    # Evidence lines (truncated for readability)
    evidence_lines: list[dict] = []
    unique_lines = set()
    for signal_list in [db_client_signals, execution_signals, write_keyword_signals]:
        for s in signal_list:
            if s["evidence_type"] == "executable_context" and s["line"] not in unique_lines:
                unique_lines.add(s["line"])
                actual_line = lines[s["line"] - 1].strip()[:120] if s["line"] <= len(lines) else ""
                evidence_lines.append(
                    {
                        "line": s["line"],
                        "signal": s["signal"],
                        "snippet": actual_line,
                    }
                )

    return {
        "path": rel_path,
        "classification": classification,
        "db_client_signals": db_client_signals,
        "db_env_signals": db_env_signals,
        "execution_signals": execution_signals,
        "write_keyword_signals": write_keyword_signals,
        "evidence_lines": evidence_lines[:50],  # cap at 50 evidence lines
        "allowlist_status": "not_in_allowlist",
        "requires_review": classification
        in (
            "python_confirmed_write_risk",
            "python_possible_write_risk",
        ),
        "would_fail_changed_files_gate": would_fail,
        "recommended_next_action": (
            "review_and_add_to_allowlist_or_implement_guard" if would_fail else "no_action_needed"
        ),
    }


# ── Allowlist ────────────────────────────────────────────────────────────────


def _load_allowlist(allowlist_path: Path | None = None) -> dict[str, dict]:
    """Load the Python DB write allowlist JSON file."""
    if allowlist_path is None:
        allowlist_path = REPO_ROOT / "config" / "python_db_write_allowlist.json"
    if not allowlist_path.exists():
        return {}
    try:
        data = json.loads(allowlist_path.read_text(encoding="utf-8"))
        entries = data.get("entries", [])
        return {entry["path"]: entry for entry in entries}
    except (json.JSONDecodeError, KeyError):
        return {}


def _validate_allowlist_entry(entry: dict) -> list[str]:
    """Validate a single allowlist entry. Returns list of missing fields."""
    required = [
        "path",
        "classification",
        "reason",
        "evidence",
        "source_doc",
        "owner_task",
    ]
    return [f for f in required if f not in entry or not entry[f]]


def _apply_allowlist(
    results: list[dict],
    allowlist: dict[str, dict],
) -> list[dict]:
    """Apply allowlist to scan results. Returns updated results."""
    for result in results:
        path = result["path"]
        if path in allowlist:
            entry = allowlist[path]
            result["allowlist_status"] = "in_allowlist"
            result["allowlist_classification"] = entry.get("classification", "unknown")
            result["allowlist_reason"] = entry.get("reason", "")
            result["allowlist_source_doc"] = entry.get("source_doc", "")
            result["allowlist_owner_task"] = entry.get("owner_task", "")
            # Validate completeness
            missing = _validate_allowlist_entry(entry)
            result["allowlist_entry_complete"] = len(missing) == 0
            result["allowlist_missing_fields"] = missing
            # Disarm changed-files gate fail for historical baseline entries
            if result.get("would_fail_changed_files_gate"):
                cls = entry.get("classification", "")
                if cls.startswith("historical_python_"):
                    result["would_fail_changed_files_gate"] = False
                    result["recommended_next_action"] = "historical_baseline_pending_runtime_guard"
        else:
            result["allowlist_status"] = "not_in_allowlist"
    return results


# ── Main scan entrypoint ─────────────────────────────────────────────────────


def scan_files(
    file_paths: list[str],
    allowlist_path: Path | None = None,
) -> list[dict]:
    """Scan Python files for DB write risk signals.

    Args:
        file_paths: List of file paths relative to REPO_ROOT.
        allowlist_path: Optional path to the allowlist JSON file.

    Returns:
        List of scan result dicts, one per file.
    """
    allowlist = _load_allowlist(allowlist_path)
    results: list[dict] = []

    for fp in file_paths:
        full_path = REPO_ROOT / fp
        if not full_path.exists():
            results.append(
                {
                    "path": fp,
                    "classification": "file_not_found",
                    "db_client_signals": [],
                    "db_env_signals": [],
                    "execution_signals": [],
                    "write_keyword_signals": [],
                    "evidence_lines": [],
                    "allowlist_status": "not_applicable",
                    "requires_review": False,
                    "would_fail_changed_files_gate": False,
                    "recommended_next_action": "verify_file_exists",
                }
            )
            continue
        if not full_path.is_file():
            results.append(
                {
                    "path": fp,
                    "classification": "not_a_file",
                    "requires_review": False,
                    "would_fail_changed_files_gate": False,
                }
            )
            continue
        result = _scan_file_for_signals(full_path)
        results.append(result)

    return _apply_allowlist(results, allowlist)


def scan_repository(
    allowlist_path: Path | None = None,
) -> list[dict]:
    """Scan all Python files in the repository."""
    python_files: list[str] = []
    for root, dirs, files in os.walk(str(REPO_ROOT)):
        # Skip non-relevant directories
        dirs_to_skip = {
            ".git",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".claude",
            "venv",
            ".venv",
            ".tox",
            "dist",
            "build",
            "egg-info",
            ".egg-info",
        }
        dirs[:] = [d for d in dirs if d not in dirs_to_skip]
        for fname in files:
            if fname.endswith(".py"):
                full = Path(root) / fname
                rel = str(full.relative_to(REPO_ROOT))
                python_files.append(rel)
    return scan_files(python_files, allowlist_path)


# ── Changed-files enforcement ────────────────────────────────────────────────


def changed_files_check(
    changed_files: list[str],
    allowlist_path: Path | None = None,
) -> dict[str, Any]:
    """Run changed-files enforcement.

    Scans only changed Python files and reports which would fail the gate.

    Returns:
        Dict with:
          - violations: list of files that fail the gate
          - passed: list of files that pass
          - would_hard_fail: bool
          - results: full scan results
    """
    python_changed = [f for f in changed_files if f.endswith(".py")]
    if not python_changed:
        return {
            "violations": [],
            "passed": [],
            "would_hard_fail": False,
            "results": [],
            "note": "No Python files changed",
        }

    results = scan_files(python_changed, allowlist_path)
    violations: list[dict] = []
    passed: list[dict] = []

    for result in results:
        if result.get("would_fail_changed_files_gate"):
            violations.append(result)
        else:
            passed.append(result)

    return {
        "violations": violations,
        "passed": passed,
        "would_hard_fail": len(violations) > 0,
        "results": results,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Python DB Write Static Enforcement Scanner",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as JSON",
    )
    parser.add_argument(
        "--changed-files",
        default=None,
        help="Comma-separated list of changed Python files for enforcement check",
    )
    parser.add_argument(
        "--allowlist",
        default=None,
        help="Path to allowlist JSON file (default: config/python_db_write_allowlist.json)",
    )
    parser.add_argument(
        "--files",
        default=None,
        help="Comma-separated list of specific Python files to scan",
    )
    parser.add_argument(
        "--full-scan",
        action="store_true",
        default=False,
        help="Scan all Python files in the repository",
    )
    parser.add_argument(
        "--validate-allowlist",
        action="store_true",
        default=False,
        help="Validate allowlist entries for completeness",
    )
    return parser


def _format_results_human(results: list[dict]) -> str:
    """Format results for human-readable output."""
    lines: list[str] = []
    for r in results:
        path = r.get("path", "?")
        cls = r.get("classification", "?")
        allowlist = r.get("allowlist_status", "?")
        would_fail = r.get("would_fail_changed_files_gate", False)
        status = "FAIL" if would_fail else "PASS"
        lines.append(f"[{status}] {path}")
        lines.append(f"       classification={cls}  allowlist={allowlist}")
        evidence = r.get("evidence_lines", [])
        if evidence:
            lines.extend(
                f"       L{ev['line']}: [{ev['signal']}] {ev['snippet']}" for ev in evidence[:5]
            )
        lines.append("")
    return "\n".join(lines)


def _validate_allowlist_entries(allowlist_path: Path | None = None) -> dict:
    """Validate all allowlist entries. Returns dict with validation results."""
    allowlist = _load_allowlist(allowlist_path)
    valid_entries: list[dict] = []
    invalid_entries: list[dict] = []
    has_wildcards = False

    for path, entry in allowlist.items():
        if "*" in path or "?" in path:
            has_wildcards = True
        missing = _validate_allowlist_entry(entry)
        entry_with_validation = {**entry, "missing_fields": missing, "is_valid": len(missing) == 0}
        if missing:
            invalid_entries.append(entry_with_validation)
        else:
            valid_entries.append(entry_with_validation)

    return {
        "total_entries": len(allowlist),
        "valid_entries": len(valid_entries),
        "invalid_entries": len(invalid_entries),
        "has_wildcards": has_wildcards,
        "invalid_details": invalid_entries,
    }


def main(argv: list[str] | None = None) -> int:  # noqa: C901, PLR0912
    """Run the Python DB write static enforcement scanner."""
    parser = build_parser()
    args = parser.parse_args(argv)

    allowlist_path: Path | None = None
    if args.allowlist:
        allowlist_path = Path(args.allowlist)
        if not allowlist_path.is_absolute():
            allowlist_path = REPO_ROOT / allowlist_path

    # --validate-allowlist mode
    if args.validate_allowlist:
        validation = _validate_allowlist_entries(allowlist_path)
        if args.json:
            print(json.dumps(validation, indent=2))
        else:
            print(
                f"Allowlist validation: {validation['valid_entries']} valid, "
                f"{validation['invalid_entries']} invalid, "
                f"total={validation['total_entries']}, "
                f"wildcards={'YES' if validation['has_wildcards'] else 'NO'}"
            )
            if validation["invalid_details"]:
                for inv in validation["invalid_details"]:
                    print(f"  INVALID: {inv.get('path', '?')} missing: {inv['missing_fields']}")
        return 0 if not validation["invalid_details"] and not validation["has_wildcards"] else 1

    # --changed-files mode
    if args.changed_files:
        changed = [f.strip() for f in args.changed_files.split(",") if f.strip()]
        result = changed_files_check(changed, allowlist_path)
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(
                f"Python DB write changed-files enforcement: "
                f"{len(result['violations'])} violation(s), "
                f"{len(result['passed'])} passed"
            )
            if result.get("note"):
                print(f"  Note: {result['note']}")
            if result["violations"]:
                print(_format_results_human(result["violations"]))
            print(f"Would hard fail: {'YES' if result['would_hard_fail'] else 'NO'}")
        return 1 if result["would_hard_fail"] else 0

    # --files mode
    if args.files:
        file_list = [f.strip() for f in args.files.split(",") if f.strip()]
        results = scan_files(file_list, allowlist_path)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(_format_results_human(results))
        violations = [r for r in results if r.get("would_fail_changed_files_gate")]
        return 1 if violations else 0

    # --full-scan mode (default)
    results = scan_repository(allowlist_path)
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        risky = [r for r in results if r.get("requires_review")]
        safe = [r for r in results if not r.get("requires_review")]
        print(
            f"Python DB write static scan: {len(results)} files scanned, "
            f"{len(risky)} with write risk, {len(safe)} no risk detected"
        )
        if risky:
            print(_format_results_human(risky))
    return 0


if __name__ == "__main__":
    sys.exit(main())
