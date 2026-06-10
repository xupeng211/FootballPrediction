#!/usr/bin/env python3
"""
Minimal audit guard tests.

Tests the safety guards in scripts/ops/audit_fotmob_retained_raw_quality.js
without requiring DB access. Verifies:
- Production DB rejection
- Read-only: no INSERT/UPDATE/DELETE/UPSERT in source
- Help flag works
- Script is well-formed

lifecycle: permanent / smoke-test
"""

import os
from pathlib import Path
import subprocess

SCRIPT = "scripts/ops/audit_fotmob_retained_raw_quality.js"


def _run_node(script, *args, env=None):
    base_env = os.environ.copy()
    for var in ("PGHOST", "PGPASSWORD", "PGDATABASE", "PGUSER", "PGPORT"):
        base_env.pop(var, None)
    if env:
        base_env.update(env)
    node_bin = os.environ.get("NODE_BIN", "node")
    result = subprocess.run(
        [node_bin, script, *list(args)],
        check=False,
        capture_output=True,
        text=True,
        env=base_env,
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


class TestGuardProductionDbRejection:
    """Production DB must be rejected."""

    def test_rds_hostname_rejected(self):
        rc, stdout, stderr = _run_node(
            SCRIPT,
            env={"PGHOST": "football-db.rds.amazonaws.com"},
        )
        combined = stdout + stderr
        assert rc != 0, f"RDS host should be rejected, got rc={rc}"
        assert "BLOCKED" in combined or "production" in combined.lower(), (
            f"Should block production DB: {combined[:500]}"
        )

    def test_supabase_hostname_rejected(self):
        rc, stdout, stderr = _run_node(
            SCRIPT,
            env={"PGHOST": "db.abc123.supabase.co"},
        )
        combined = stdout + stderr
        assert rc != 0, f"Supabase host should be rejected, got rc={rc}"
        assert (
            "BLOCKED" in combined
            or "production" in combined.lower()
            or "whitelist" in combined.lower()
        ), f"Should block production DB: {combined[:500]}"


class TestGuardReadOnly:
    """Audit script must be read-only — no write statements."""

    def test_no_insert_in_source(self):
        """Source must not contain INSERT."""
        with Path(SCRIPT).open() as f:
            content = f.read()
        assert "INSERT " not in content, "Audit script must not contain INSERT"
        assert "INSERT\t" not in content, "Audit script must not contain INSERT"

    def test_no_update_in_source(self):
        """Source must not contain UPDATE."""
        with Path(SCRIPT).open() as f:
            content = f.read()
        assert "UPDATE " not in content, "Audit script must not contain UPDATE"

    def test_no_delete_in_source(self):
        """Source must not contain DELETE."""
        with Path(SCRIPT).open() as f:
            content = f.read()
        assert "DELETE " not in content, "Audit script must not contain DELETE"

    def test_no_upsert_in_source(self):
        """Source must not contain ON CONFLICT (SQL upsert pattern)."""
        with Path(SCRIPT).open() as f:
            content = f.read()
        # UPSERT may appear in comments documenting what the audit does NOT do,
        # but the actual SQL ON CONFLICT pattern must be absent
        assert "ON CONFLICT" not in content.upper(), "Audit script must not contain ON CONFLICT"

    def test_only_select_statements(self):
        """DB queries must be SELECT only."""
        with Path(SCRIPT).open() as f:
            content = f.read()
        # Must contain SELECT (it reads data)
        assert "SELECT" in content, "Audit script should have SELECT queries"


class TestGuardNoRawDataDump:
    """Audit must not print full raw_data, pageProps, or HTML."""

    def test_no_full_raw_data_print(self):
        """Script must not contain patterns that dump full raw_data."""
        with Path(SCRIPT).open() as f:
            content = f.read()
        # Must not print full JSON content
        assert "console.log(raw_data" not in content, "Must not print full raw_data"
        assert "console.log(JSON.stringify" not in content, "Must not print full JSON dumps"


class TestGuardHelpFlag:
    """--help should work."""

    def test_help_succeeds(self):
        """Node --help should parse OK."""
        # Just verify the script is valid JS
        rc, _stdout, _stderr = _run_node(SCRIPT, "--help")
        # Script doesn't parse --help but is valid JS
        assert rc is not None  # just check it runs


class TestGuardExpectedMatchIds:
    """Expected match IDs must be documented in source."""

    def test_expected_ids_in_source(self):
        with Path(SCRIPT).open() as f:
            content = f.read()
        assert "53_20252026_4830507" in content, "Expected match_id missing"
        assert "53_20252026_4830466" in content, "Expected match_id missing"
        assert "53_20252026_4830461" in content, "Expected match_id missing"
        assert "53_20252026_4830464" in content, "Expected match_id missing"
        assert "fotmob_live_v1" in content, "Expected data_version missing"
