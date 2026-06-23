#!/usr/bin/env python3
"""
Python DB Write Safety Gate — unified guard helper.

lifecycle: permanent
owner: DB write safety / ops governance

Purpose: provide a single, minimal blocking guard that Python scripts call before
executing INSERT / UPDATE / DELETE / TRUNCATE / DROP / ALTER / CREATE.  It does NOT
rewrite business logic, introduce a unified writer layer, or replace existing
script-specific safety checks.

This is the Python equivalent of ``scripts/ops/helpers/db_write_guard.js``.
Both enforce the same env-var gate model.

Required env vars (all must be "yes" / truthy for a real write-run):

Universal gates (both required):
  ALLOW_DB_WRITE=yes
  FINAL_DB_WRITE_CONFIRMATION=yes

Table-level gates (required based on operation):
  ALLOW_MATCHES_WRITE=yes           — writes to matches
  ALLOW_RAW_MATCH_DATA_WRITE=yes    — writes to raw_match_data
  ALLOW_ODDS_WRITE=yes              — writes to bookmaker_odds_history / odds_*
  ALLOW_TRAINING_WRITE=yes          — writes to training / predictions tables
  ALLOW_SCHEMA_WRITE=yes            — DELETE / TRUNCATE / DROP / ALTER / CREATE
  ALLOW_GENERIC_DB_WRITE=yes        — fallback for tables not in the standard map

Dry-run:
  DRY_RUN defaults to true.  A write-run requires DRY_RUN=false.

Production protection:
  Production-like DB hosts (RDS, Cloud SQL, Supabase, Railway, Render, Heroku,
  etc.) are hard-blocked by default — no override exists.
  Environment indicators (ENV=production, APP_ENV=production, etc.) block write.

Usage::

    from scripts.ops.helpers.python_db_write_guard import assert_db_write_allowed

    assert_db_write_allowed(
        script_name="my_script.py",
        operation="INSERT",
        target="matches",
        tables=["matches"],
    )

This module does NOT:
- Connect to any database
- Read any secrets or configuration files
- Access the network
- Execute any SQL
- Import any database driver

It ONLY checks environment variables.
"""

from __future__ import annotations

import os
import re

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

REQUIRED_UNIVERSAL_GATES: tuple[str, ...] = (
    "ALLOW_DB_WRITE",
    "FINAL_DB_WRITE_CONFIRMATION",
)

# Map table name (or prefix) to the env-var gate that must be truthy.
# Order matters: first match wins. Each entry is (regex_pattern, gate_env_var, human_label).
_TABLE_GATE_MAP: tuple[tuple[str, str, str], ...] = (
    (r"^raw_match_data$", "ALLOW_RAW_MATCH_DATA_WRITE", "raw_match_data"),
    (r"^collection_audit_logs$", "ALLOW_RAW_MATCH_DATA_WRITE", "collection_audit_logs"),
    (r"^matches$", "ALLOW_MATCHES_WRITE", "matches"),
    (r"^matches_mapping$", "ALLOW_MATCHES_WRITE", "matches_mapping"),
    (r"^bookmaker_odds_history$", "ALLOW_ODDS_WRITE", "bookmaker_odds_history (odds)"),
    (r"^prematch_features$", "ALLOW_ODDS_WRITE", "prematch_features (odds)"),
    (r"^l3_features$", "ALLOW_TRAINING_WRITE", "l3_features (training)"),
    (r"^match_features_training$", "ALLOW_TRAINING_WRITE", "match_features_training"),
    (r"^predictions$", "ALLOW_TRAINING_WRITE", "predictions (training)"),
    (r"^training_", "ALLOW_TRAINING_WRITE", "training_* (training)"),
    (r"^odds_", "ALLOW_ODDS_WRITE", "odds_* (odds)"),
    (r"^football_", "ALLOW_GENERIC_DB_WRITE", "football_* (generic)"),
)

HIGH_RISK_OPERATIONS: frozenset[str] = frozenset(
    {
        "DELETE",
        "TRUNCATE",
        "DROP",
        "ALTER",
        "CREATE",
        "GRANT",
        "REVOKE",
    }
)

PRODUCTION_DB_HOST_PATTERNS: tuple[str, ...] = (
    r"rds\.amazonaws\.com",
    r"\.rds\.amazonaws",
    r"cloudsql\.google",
    r"\.supabase\.",
    r"\.supabase\.co",
    r"\.vercel",
    r"\.fly\.dev",
    r"\.railway\.app",
    r"\.render\.com",
    r"\.heroku",
    r"prod(?:uction)?-db",
    r"db\.(?:prod|production)",
)

PRODUCTION_ENV_KEYS: tuple[str, ...] = (
    "ENV",
    "APP_ENV",
    "NODE_ENV",
    "FLASK_ENV",
    "DJANGO_ENV",
    "PYTHON_ENV",
)

PRODUCTION_ENV_VALUES: frozenset[str] = frozenset(
    {
        "production",
        "prod",
        "live",
        "prd",
    }
)


# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _normalize_bool_env(value: str | None) -> bool | None:
    """Normalize an env-var string to a boolean (or None if unset/empty)."""
    if value is None or value == "":
        return None
    s = value.strip().lower()
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    return None


def _is_truthy(name: str) -> bool:
    """Return True if the env var *name* holds a truthy value."""
    return _normalize_bool_env(os.environ.get(name)) is True


def _check_production_env() -> tuple[bool, list[str]]:
    """Check whether runtime environment indicators look like production.

    Returns (is_production, reasons).
    """
    reasons: list[str] = []
    for key in PRODUCTION_ENV_KEYS:
        value = (os.environ.get(key) or "").strip().lower()
        if value in PRODUCTION_ENV_VALUES:
            reasons.append(f"env var {key}={value} indicates production")
    return len(reasons) > 0, reasons


def _check_production_db_host() -> tuple[bool, list[str]]:
    """Check whether DB_HOST / DATABASE_URL looks like a production instance.

    Returns (suspicious, warnings).
    """
    host = (os.environ.get("DB_HOST") or os.environ.get("DATABASE_URL") or "").strip()
    warnings: list[str] = []

    if not host:
        return False, warnings

    for pattern in PRODUCTION_DB_HOST_PATTERNS:
        if re.search(pattern, host, re.IGNORECASE):
            warnings.append(
                f"HIGH-RISK: DB_HOST/DATABASE_URL ({host}) matches production pattern: {pattern}"
            )

    return len(warnings) > 0, warnings


def _get_table_gate(table: str) -> str | None:
    """Return the env-var gate name for *table*, or None."""
    for pattern, gate, _label in _TABLE_GATE_MAP:
        if re.search(pattern, table, re.IGNORECASE):
            return gate
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════


class DbWriteBlockedError(RuntimeError):
    """Raised when a DB write is blocked by the safety gate."""

    def __init__(self, message: str, missing_gates: list[str] | None = None) -> None:
        super().__init__(message)
        self.missing_gates = missing_gates or []


def assert_db_write_allowed(
    *,
    script_name: str,
    operation: str,
    target: str,
    tables: list[str] | None = None,
    db_url_env: str | None = None,
    dry_run: bool | None = None,
) -> None:
    """Assert that a DB write is allowed.  Raises :exc:`DbWriteBlockedError` if blocked.

    Parameters
    ----------
    script_name:
        Name of the calling script (for error messages only).
    operation:
        SQL operation, e.g. ``INSERT``, ``UPDATE``, ``DELETE``, ``TRUNCATE``, ``ALTER``.
    target:
        Human-readable description of the write target, e.g. table name or operation label.
        Included in error messages for context.
    tables:
        List of DB table names that will be written to.  Used to derive required
        table-level gates.
    db_url_env:
        Name of an alternate env var to check for the DB host (defaults to
        ``DB_HOST`` / ``DATABASE_URL``).  Reserved for future use.
    dry_run:
        Explicit dry-run override.  When ``True`` the function returns immediately
        (write not required).  When ``False`` all gates must be satisfied.
        Defaults to the ``DRY_RUN`` env var, which itself defaults to ``True``.

    Raises
    ------
    DbWriteBlockedError:
        If the write is blocked.  The error message tells the caller which env
        vars are missing but never leaks DB URLs or secrets.
    """
    _ = db_url_env  # reserved for future alternate DB host env var support
    tables = tables or []
    warnings: list[str] = []
    missing_gates: list[str] = []

    # ── 1. Production env detection ──────────────────────────────────────────
    is_prod_env, prod_env_reasons = _check_production_env()
    if is_prod_env:
        raise DbWriteBlockedError(
            f"[{script_name}] BLOCKED: Environment appears to be production. "
            + "; ".join(prod_env_reasons)
            + ". DB write is not allowed in production environment by default. "
            + "Set ENV=development or override explicitly if this is intentional.",
            missing_gates=[],
        )

    # ── 2. Dry-run determination ─────────────────────────────────────────────
    dry_run_env = os.environ.get("DRY_RUN")
    if dry_run is not None:
        is_dry_run_mode = dry_run
    elif dry_run_env is None or dry_run_env == "":
        is_dry_run_mode = True  # default: dry-run
    else:
        is_dry_run_mode = _normalize_bool_env(dry_run_env) is not False

    # ── 3. Production DB host detection ──────────────────────────────────────
    prod_db_suspicious, prod_db_warnings = _check_production_db_host()
    warnings.extend(prod_db_warnings)

    # ── 4. Production DB host hard block ─────────────────────────────────────
    if prod_db_suspicious:
        joined = "; ".join(prod_db_warnings)
        raise DbWriteBlockedError(
            f"[{script_name}] BLOCKED: DB_HOST / DATABASE_URL appears production-like. "
            f"Matched: {joined}. "
            "DB write to production-like hosts is blocked by default. "
            "No production override is implemented in this phase.",
            missing_gates=[],
        )

    # ── 5. Dry-run: return early ─────────────────────────────────────────────
    if is_dry_run_mode:
        # Dry-run mode — not an error, just return
        return

    # ── 6. Universal gates ───────────────────────────────────────────────────
    for gate in REQUIRED_UNIVERSAL_GATES:
        if not _is_truthy(gate):
            missing_gates.append(gate)

    # ── 7. Table-level gates ─────────────────────────────────────────────────
    required_table_gates: set[str] = set()
    for table in tables:
        gate = _get_table_gate(table)
        if gate is not None:
            required_table_gates.add(gate)

    for gate in sorted(required_table_gates):
        if not _is_truthy(gate):
            missing_gates.append(gate)

    # ── 8. Schema-level gate for high-risk operations ─────────────────────────
    op_upper = operation.upper().strip()
    if op_upper in HIGH_RISK_OPERATIONS and not _is_truthy("ALLOW_SCHEMA_WRITE"):
        missing_gates.append("ALLOW_SCHEMA_WRITE")

    # ── 9. Decision ──────────────────────────────────────────────────────────
    if missing_gates:
        gate_list = ", ".join(missing_gates)
        raise DbWriteBlockedError(
            f"[{script_name}] BLOCKED: DB write requires the following env vars "
            f"set to a truthy value (yes/1/true): {gate_list}. "
            f"Currently missing: {gate_list}. "
            "Set the missing env vars and try again.",
            missing_gates=missing_gates,
        )

    # All gates satisfied — write is allowed.


def is_dry_run() -> bool:
    """Return True if DRY_RUN mode is active (the default)."""
    dry_run_env = os.environ.get("DRY_RUN")
    if dry_run_env is None or dry_run_env == "":
        return True
    return _normalize_bool_env(dry_run_env) is not False


def describe_required_gates(
    tables: list[str] | None = None,
    operations: list[str] | None = None,
) -> dict[str, list[str]]:
    """Return the gates that would be required for the given tables and operations.

    Useful for documentation and pre-flight checks.
    """
    tables = tables or []
    operations = operations or []

    table_gates: set[str] = set()
    for table in tables:
        gate = _get_table_gate(table)
        if gate is not None:
            table_gates.add(gate)

    has_high_risk = any(op.upper().strip() in HIGH_RISK_OPERATIONS for op in operations)

    return {
        "universal": list(REQUIRED_UNIVERSAL_GATES),
        "table_level": sorted(table_gates),
        "schema_level": ["ALLOW_SCHEMA_WRITE"] if has_high_risk else [],
    }
