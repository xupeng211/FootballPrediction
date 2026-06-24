"""
SQL Migration Policy Enforcement — Gate integration helper.

lifecycle: permanent
owner: DB write safety / ops governance
task: sql_migration_policy_implementation_phase2B

Provides `run_sql_migration_policy_gate_check()` for use by ai_workflow_gate.py.
Runs the SQL/migration policy scanner in changed-files enforcement mode.
Does NOT execute SQL, connect to DB, or run migrations.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
from typing import Any


def _is_ci_environment() -> bool:
    return bool(
        os.environ.get("CI")
        or os.environ.get("GITHUB_ACTIONS")
        or os.environ.get("PRODUCTION_GATE")
    )


def _find_scanner_path() -> str | None:
    candidates = [
        Path(__file__).resolve().parent.parent / "sql_migration_policy_static_enforcement.py",
        Path.cwd() / "scripts" / "ops" / "sql_migration_policy_static_enforcement.py",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def run_sql_migration_policy_gate_check(changed: set[str], errors: list[str]) -> None:  # noqa: C901, PLR0912
    """Called from ai_workflow_gate.py main() — mutates errors list in-place."""
    scanner_path = _find_scanner_path()
    if scanner_path is None:
        return

    is_ci = _is_ci_environment()

    try:
        spec = importlib.util.spec_from_file_location("_sqlenf", scanner_path)
        if spec is None or spec.loader is None:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result: dict[str, Any] = mod.changed_files_check(list(changed))
    except Exception as exc:
        sys.stdout.write(f"[SQL-MIGRATION ENFORCEMENT] scanner error: {exc}\n")
        if is_ci:
            errors.append(f"[SQL-MIGRATION ENFORCEMENT] fail-closed in CI: {exc}")
        return

    violations = result.get("violations", [])
    passed = result.get("passed", [])
    note = result.get("note", "")

    if note:
        sys.stdout.write(f"[SQL-MIGRATION ENFORCEMENT] {note}\n")

    if not violations:
        if passed:
            sys.stdout.write(
                f"[SQL-MIGRATION ENFORCEMENT] OK: {len(passed)} SQL/migration file(s) checked, 0 violations.\n"
            )
        return

    for v in violations:
        path = v.get("path", "?")
        cls = v.get("classification", "?")
        allowlist_status = v.get("allowlist_status", "not_in_allowlist")
        has_destructive = any(
            s["evidence_type"] == "executable_context" for s in v.get("destructive_signals", [])
        )
        signals_list = v.get("evidence_lines", [])
        signals = (
            ", ".join(sorted({e["signal"] for e in signals_list[:5]})) if signals_list else "none"
        )

        would_fail = v.get("would_fail_changed_files_gate", True)
        if has_destructive and would_fail:
            errors.append(
                f"[SQL-MIGRATION ENFORCEMENT] FAIL: {path}: DESTRUCTIVE SQL detected. "
                f"Signals: {signals}. Classification: {cls}. "
                f"Destructive operations (DROP DATABASE, DROP TABLE, TRUNCATE, etc.) "
                f"require explicit policy review. SC-002 remains partial mitigation only."
            )
        elif has_destructive and not would_fail:
            # File is in allowlist with proper classification — would_fail is False.
            sys.stdout.write(
                f"[SQL-MIGRATION ENFORCEMENT] {path}: {cls} — "
                f"in allowlist (historical baseline). Destructive signals: {signals}. "
                f"Changed-files gate exempt. Allowlist does NOT authorize execution.\n"
            )
        elif allowlist_status == "in_allowlist":
            sys.stdout.write(
                f"[SQL-MIGRATION ENFORCEMENT] {path}: {cls} — "
                f"in allowlist (historical baseline). Signals: {signals}. "
                f"Allowlist does NOT authorize SQL/migration execution.\n"
            )
        elif allowlist_status == "not_in_allowlist":
            allowlist_complete = v.get("allowlist_entry_complete", True)
            missing = v.get("allowlist_missing_fields", [])
            if not allowlist_complete and missing:
                errors.append(
                    f"[SQL-MIGRATION ENFORCEMENT] {path}: {cls} — "
                    f"in allowlist but entry INCOMPLETE. "
                    f"Missing fields: {', '.join(missing)}."
                )
            else:
                errors.append(
                    f"[SQL-MIGRATION ENFORCEMENT] FAIL: {path}: {cls} — "
                    f"NOT in allowlist and has SQL/migration risk. "
                    f"Signals: {signals}. "
                    f"Add to config/sql_migration_policy_allowlist.json "
                    f"with complete classification. "
                    f"SC-002 remains partial mitigation only."
                )


def check_sql_migration_policy_enforcement(
    changed: set[str],
) -> tuple[list[str], list[str]]:
    """Standalone check returning (errors, warnings). Used by tests."""
    scanner_path = _find_scanner_path()
    if scanner_path is None:
        return [], []

    try:
        spec = importlib.util.spec_from_file_location("_sqlenf", scanner_path)
        if spec is None or spec.loader is None:
            return [], []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result: dict[str, Any] = mod.changed_files_check(list(changed))
    except Exception as exc:
        return [f"[SQL-MIGRATION ENFORCEMENT] scanner error: {exc}"], []

    violations = result.get("violations", [])
    passed = result.get("passed", [])
    errors: list[str] = []
    warnings: list[str] = []

    if result.get("note"):
        warnings.append(f"[SQL-MIGRATION ENFORCEMENT] {result['note']}")

    for v in violations:
        path = v.get("path", "?")
        cls = v.get("classification", "?")
        signals_list = v.get("evidence_lines", [])
        signals = (
            ", ".join(sorted({e["signal"] for e in signals_list[:5]})) if signals_list else "none"
        )
        has_destructive = any(
            s["evidence_type"] == "executable_context" for s in v.get("destructive_signals", [])
        )
        would_fail = v.get("would_fail_changed_files_gate", True)
        if has_destructive and would_fail:
            errors.append(f"DESTRUCTIVE: {path} — {cls} — Signals: {signals}")
        elif has_destructive and not would_fail:
            # Allowlisted file with proper classification — gate exempt.
            warnings.append(
                f"ALLOWLISTED-DESTRUCTIVE: {path} — {cls} — Signals: {signals} (gate exempt)"
            )
        else:
            errors.append(f"FAIL: {path} — {cls} — Signals: {signals}")

    if passed and not violations:
        warnings.append(f"OK: {len(passed)} SQL/migration file(s) checked, 0 violations.")

    return errors, warnings


run_gate_check = run_sql_migration_policy_gate_check
