"""
Python DB Write Static Enforcement — Gate integration helper.

lifecycle: permanent
owner: DB write safety / ops governance
task: python_sql_migration_enforcement_implementation_phase2A

Provides `check_python_db_write_enforcement()` for use by ai_workflow_gate.py.
Runs the Python DB write static scanner in changed-files enforcement mode and
returns (errors, warnings) — errors cause CI hard fail, warnings are advisory only.

Does NOT: import/execute target Python files, connect to DB, run SQL/migration.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
from typing import Any


def _is_ci_environment() -> bool:
    """Detect whether we are running in a CI / P0 gate environment."""
    return bool(
        os.environ.get("CI")
        or os.environ.get("GITHUB_ACTIONS")
        or os.environ.get("PRODUCTION_GATE")
        or os.environ.get("P0_GATE")
    )


def _find_scanner_path() -> str | None:
    """Locate the Python DB write static enforcement scanner."""
    candidates = [
        Path(__file__).resolve().parent.parent / "python_db_write_static_enforcement.py",
        Path.cwd() / "scripts" / "ops" / "python_db_write_static_enforcement.py",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _build_violation_errors(violations: list[dict]) -> list[str]:
    """Build CI hard-fail error messages from scanner violations."""
    errors: list[str] = [
        "[PYTHON-DB-WRITE ENFORCEMENT] FAIL: "
        f"{len(violations)} changed Python file(s) have unguarded "
        "DB write risk signals. Add to config/python_db_write_allowlist.json "
        "with complete classification or implement runtime guard."
    ]
    for v in violations:
        path = v.get("path", "?")
        cls = v.get("classification", "?")
        signals_list = v.get("evidence_lines", [])
        signals = (
            ", ".join(sorted({e["signal"] for e in signals_list[:5]})) if signals_list else "none"
        )
        errors.append(
            f"[PYTHON-DB-WRITE ENFORCEMENT] {path}: {cls} — "
            f"NOT in allowlist. Signals: {signals}. "
            f"Either add to config/python_db_write_allowlist.json "
            f"with complete classification or implement runtime guard."
        )
    errors.append(
        "[PYTHON-DB-WRITE ENFORCEMENT] SC-002 remains partial mitigation only. "
        "Historical baseline files are exempt via allowlist. "
        "Python runtime guard is NOT yet implemented."
    )
    return errors


def _build_violation_warnings(
    violations: list[dict],
    passed: list[dict],
    note: str,
) -> list[str]:
    """Build advisory warnings."""
    warnings: list[str] = []
    if note:
        warnings.append(f"[PYTHON-DB-WRITE ENFORCEMENT] {note}")
    if passed and not violations:
        warnings.append(
            f"[PYTHON-DB-WRITE ENFORCEMENT] OK: {len(passed)} changed Python "
            f"file(s) checked, 0 violations."
        )
    return warnings


def run_python_db_write_gate_check(changed: set[str], errors: list[str]) -> None:
    """Called from ai_workflow_gate.py main() — mutates errors list in-place."""
    try:
        py_errors, py_warnings = check_python_db_write_enforcement(changed)
        errors.extend(py_errors)
        for w in py_warnings:
            sys.stdout.write(f"- {w}\n")
    except Exception as exc:
        sys.stdout.write(f"[PYTHON-DB-WRITE ENFORCEMENT] scanner error: {exc}\n")
        if _is_ci_environment():
            errors.append(f"[PYTHON-DB-WRITE ENFORCEMENT] fail-closed in CI: {exc}")


def check_python_db_write_enforcement(
    changed: set[str],
) -> tuple[list[str], list[str]]:
    """Run Python DB write static enforcement scanner. Returns (errors, warnings).

    Phase2A: scans changed Python files for DB write risk signals.
    Files in the allowlist pass; manual_review in allowlist pass with baseline
    status; confirmed write risk files without complete allowlist entry fail.
    Does NOT import or execute target files. Does NOT connect to DB.
    """
    scanner_path = _find_scanner_path()
    if scanner_path is None:
        return [], []

    errors: list[str] = []
    warnings: list[str] = []
    is_ci = _is_ci_environment()

    try:
        spec = importlib.util.spec_from_file_location("_pydbse", scanner_path)
        if spec is None or spec.loader is None:
            return [], []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        changed_list = list(changed)
        result: dict[str, Any] = mod.changed_files_check(changed_list)
    except Exception as exc:
        msg = f"[PYTHON-DB-WRITE ENFORCEMENT] scanner error: {exc}"
        if is_ci:
            errors.append(msg + " — fail-closed in CI/P0 gate. Investigate scanner failure.")
        else:
            warnings.append(msg + " — advisory only (non-CI).")
        return errors, warnings

    violations = result.get("violations", [])
    passed = result.get("passed", [])
    note = result.get("note", "")

    if not violations:
        warnings.extend(_build_violation_warnings(violations, passed, note))
        return errors, warnings

    for v in violations:
        path = v.get("path", "?")
        cls = v.get("classification", "?")
        allowlist_status = v.get("allowlist_status", "not_in_allowlist")
        evidence = v.get("evidence_lines", [])
        signals = ", ".join(sorted({e["signal"] for e in evidence[:5]})) if evidence else "none"

        if allowlist_status == "in_allowlist":
            warnings.append(
                f"[PYTHON-DB-WRITE ENFORCEMENT] {path}: {cls} — "
                f"in allowlist (historical baseline). Signals: {signals}. "
                f"Allowlist does NOT authorize runtime DB writes. "
                f"Runtime guard NOT implemented."
            )
        elif allowlist_status == "not_in_allowlist":
            allowlist_complete = v.get("allowlist_entry_complete", True)
            missing = v.get("allowlist_missing_fields", [])
            if not allowlist_complete and missing:
                errors.append(
                    f"[PYTHON-DB-WRITE ENFORCEMENT] {path}: {cls} — "
                    f"in allowlist but entry INCOMPLETE. "
                    f"Missing fields: {', '.join(missing)}. "
                    f"Add missing fields to config/python_db_write_allowlist.json."
                )
            else:
                errors.append(
                    f"[PYTHON-DB-WRITE ENFORCEMENT] FAIL: {path}: {cls} — "
                    f"NOT in allowlist and has DB write risk. "
                    f"Signals: {signals}. "
                    f"Either add to config/python_db_write_allowlist.json "
                    f"with complete classification or implement runtime guard. "
                    f"SC-002 remains partial mitigation only."
                )

    return errors, warnings
