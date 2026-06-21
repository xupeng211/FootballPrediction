"""
DB Write Guard Static Enforcement — Enforcement Check helper.

lifecycle: permanent
owner: DB write safety / ops governance

Provides `check_db_write_guard_enforcement()` for use by ai_workflow_gate.py.
Runs the JS scanner in changed-files enforcement mode and returns
(errors, warnings) — errors cause CI hard fail, warnings are advisory only.

Phase2: upgraded from advisory-only to hard-fail for new/modified unguarded
scripts/ops JS files. Historical full-scan candidates remain exempt.
"""

import json
import os
from pathlib import Path
import subprocess


def _is_ci_environment() -> bool:
    """Detect whether we are running in a CI / P0 gate environment."""
    return bool(
        os.environ.get("CI")
        or os.environ.get("GITHUB_ACTIONS")
        or os.environ.get("PRODUCTION_GATE")
        or os.environ.get("P0_GATE")
    )


def _emit_violation_errors(violations: list[dict]) -> list[str]:
    """Build error messages from violation entries."""
    errors: list[str] = []
    errors.append(
        "[DB-WRITE-GUARD ENFORCEMENT] FAIL: "
        f"{len(violations)} changed scripts/ops JS file(s) have unguarded "
        "DB write risk. Add assertDbWriteAllowed or request explicit "
        "allowlist classification."
    )
    for v in violations:
        path = v.get("path", "?")
        ops = ", ".join(v.get("writeOps", []))
        tables = ", ".join(v.get("tables", []))
        risk = v.get("riskLevel", "?")
        why = v.get("whyNotSkipped", "")
        errors.append(
            f"[DB-WRITE-GUARD ENFORCEMENT] {path}: "
            f"DB write risk ({ops}) on tables ({tables}) risk={risk} "
            f"— no db_write_guard detected. {why}"
        )
        suggested = v.get("suggestedFix", "")
        if suggested:
            errors.extend(f"  {line.strip()}" for line in suggested.split("\n") if line.strip())
    errors.append(
        "[DB-WRITE-GUARD ENFORCEMENT] SC-002 is NOT fully fixed. "
        "Historical full-scan candidates are exempt from this hard fail. "
        "This enforcement only applies to changed files in this diff."
    )
    return errors


def _emit_violation_warnings(violations: list[dict]) -> list[str]:
    """Build advisory warnings from violation entries (should_fail=false edge case)."""
    return [f"  {v.get('path', '?')}: {v.get('reason', '?')}" for v in violations]


def check_db_write_guard_enforcement(  # noqa: C901, PLR0912
    changed: set[str],
) -> tuple[list[str], list[str]]:
    """Run DB write guard static enforcement scanner in changed-files mode.

    Returns (errors, warnings):
      - errors: cause CI hard fail (unguarded changed-files violations)
      - warnings: advisory only, do NOT cause CI failure

    Complexity is inherent: this function orchestrates scanner invocation,
    JSON parsing, error/warning branching, and CI vs non-CI policy.
    """
    errors: list[str] = []
    warnings: list[str] = []

    js_ops_changed = [p for p in changed if p.startswith("scripts/ops/") and p.endswith(".js")]
    if not js_ops_changed:
        return errors, warnings

    scanner = str(
        Path(__file__).resolve().parent.parent / "db_write_guard_static_enforcement_dry_run.js"
    )

    try:
        proc = subprocess.run(
            ["node", scanner, "--json", "--changed-files", ",".join(js_ops_changed)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception as exc:
        msg = f"[DB-WRITE-GUARD ENFORCEMENT] scanner error: {exc}"
        if _is_ci_environment():
            errors.append(
                msg + " — fail-closed in CI/P0 gate environment. "
                "Investigate scanner failure before proceeding."
            )
        else:
            warnings.append(msg + " — advisory only (non-CI environment).")
        return errors, warnings

    if proc.returncode != 0:
        msg = (
            "[DB-WRITE-GUARD ENFORCEMENT] scanner execution failed (exit code "
            f"{proc.returncode}) — cannot verify guard coverage on changed "
            "scripts/ops JS files"
        )
        if _is_ci_environment():
            errors.append(
                msg + " — fail-closed in CI/P0 gate environment. "
                "Investigate scanner failure before proceeding."
            )
        else:
            warnings.append(msg + " — advisory only (non-CI environment).")
        return errors, warnings

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        msg = f"[DB-WRITE-GUARD ENFORCEMENT] scanner JSON parse error: {exc}"
        if _is_ci_environment():
            errors.append(msg + " — fail-closed in CI/P0 gate.")
        else:
            warnings.append(msg + " — advisory only (non-CI).")
        return errors, warnings

    should_fail = data.get("should_fail", False)
    violations = data.get("violations", [])

    if should_fail and violations:
        errors.extend(_emit_violation_errors(violations))
    elif violations:
        warnings.append(
            f"[DB-WRITE-GUARD ENFORCEMENT] {len(violations)} violation(s) found "
            "but should_fail is false — checking enforcement logic."
        )
        warnings.extend(_emit_violation_warnings(violations))
    else:
        guarded = data.get("guarded_changed_js_ops", [])
        fp_count = len(data.get("false_positive_changed", []))
        if guarded:
            warnings.append(
                f"[DB-WRITE-GUARD ENFORCEMENT] OK: {len(guarded)} guarded "
                f"changed scripts/ops JS file(s), {fp_count} skipped."
            )

    historical_note = data.get("historical_debt_note", "")
    if historical_note:
        warnings.append(f"[DB-WRITE-GUARD ENFORCEMENT] {historical_note}")

    return errors, warnings


# Backward-compatible alias for existing callers
def check_db_write_guard_advisory(changed: set[str]) -> list[str]:
    """Backward-compatible wrapper: returns warnings only (no hard fail).

    Deprecated: use check_db_write_guard_enforcement() for full enforcement.
    """
    _errors, warnings = check_db_write_guard_enforcement(changed)
    return warnings
