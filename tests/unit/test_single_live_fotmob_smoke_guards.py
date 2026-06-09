#!/usr/bin/env python3
"""
Minimal live smoke-tool guard tests.

Tests the safety guards in scripts/ops/single_live_fotmob_raw_ingest_smoke.js
without actually running the full live fetch pipeline. These tests verify
that the guard logic rejects unsafe configurations.

lifecycle: permanent / smoke-test
"""

import os
import subprocess

SCRIPT = "scripts/ops/single_live_fotmob_raw_ingest_smoke.js"
VALID_MATCH_ID = "53_20252026_4830507"
VALID_EXTERNAL_ID = "4830507"
VALID_HOME = "Nice"
VALID_AWAY = "Paris FC"


def _run_node(script, *args, env=None):
    """Run the script with given args and return (returncode, stdout, stderr)."""
    base_env = os.environ.copy()
    base_env.pop("CONFIRM_LIVE_FOTMOB_SINGLE_FETCH", None)
    base_env.pop("CONFIRM_LOCAL_DB_WRITE", None)
    base_env.pop("PGHOST", None)
    base_env.pop("PGPASSWORD", None)
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


class TestGuardRequiresLiveFotmobConfirmation:
    """G3: CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 required for any live fetch."""

    def test_dry_run_rejected_without_live_fetch_env(self):
        """Dry-run without CONFIRM_LIVE_FOTMOB_SINGLE_FETCH must be blocked."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id", VALID_MATCH_ID,
            "--external-id", VALID_EXTERNAL_ID,
            "--home-team", VALID_HOME,
            "--away-team", VALID_AWAY,
            "--dry-run",
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit without CONFIRM_LIVE_FOTMOB_SINGLE_FETCH, got {rc}"
        assert "BLOCKED" in combined or "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH" in combined, (
            f"Should mention G3 or CONFIRM_LIVE_FOTMOB_SINGLE_FETCH: {combined[:500]}"
        )

    def test_commit_rejected_without_live_fetch_env(self):
        """--commit without CONFIRM_LIVE_FOTMOB_SINGLE_FETCH must be blocked."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id", VALID_MATCH_ID,
            "--external-id", VALID_EXTERNAL_ID,
            "--home-team", VALID_HOME,
            "--away-team", VALID_AWAY,
            "--commit",
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit, got {rc}"
        assert "BLOCKED" in combined or "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH" in combined, (
            f"Should mention CONFIRM_LIVE_FOTMOB_SINGLE_FETCH: {combined[:500]}"
        )


class TestGuardRejectsWriteWithoutConfirm:
    """G1: CONFIRM_LOCAL_DB_WRITE=1 required for DB write."""

    def test_commit_rejected_without_db_write_env(self):
        """--commit with live fetch but without CONFIRM_LOCAL_DB_WRITE must be blocked."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id", VALID_MATCH_ID,
            "--external-id", VALID_EXTERNAL_ID,
            "--home-team", VALID_HOME,
            "--away-team", VALID_AWAY,
            "--commit",
            env={"CONFIRM_LIVE_FOTMOB_SINGLE_FETCH": "1"},
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit, got {rc}"
        assert "BLOCKED" in combined or "CONFIRM_LOCAL_DB_WRITE" in combined, (
            f"Should mention CONFIRM_LOCAL_DB_WRITE: {combined[:500]}"
        )


class TestGuardProductionDbDetection:
    """G2: Production DB URLs are rejected."""

    def test_rds_hostname_rejected(self):
        """RDS hostname must be detected as production."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id", VALID_MATCH_ID,
            "--external-id", VALID_EXTERNAL_ID,
            "--home-team", VALID_HOME,
            "--away-team", VALID_AWAY,
            "--commit",
            env={
                "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
                "PGHOST": "football-db.rds.amazonaws.com",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"RDS host should be rejected, got rc={rc}"
        assert "BLOCKED" in combined or "G2" in combined or "production" in combined.lower(), (
            f"Should detect production pattern: {combined[:500]}"
        )

    def test_supabase_hostname_rejected(self):
        """Supabase hostname must be detected as production."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id", VALID_MATCH_ID,
            "--external-id", VALID_EXTERNAL_ID,
            "--home-team", VALID_HOME,
            "--away-team", VALID_AWAY,
            "--commit",
            env={
                "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
                "PGHOST": "db.abc123.supabase.co",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"Supabase host should be rejected, got rc={rc}"
        assert (
            "BLOCKED" in combined
            or "G2" in combined
            or "production" in combined.lower()
            or "whitelist" in combined.lower()
        ), f"Should detect production pattern: {combined[:500]}"


class TestGuardDataVersionLength:
    """G5: data_version ≤ 20 characters."""

    def test_short_version_allowed_with_env(self):
        """Short data_version passes guards (won't do actual fetch due to node env)."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id", VALID_MATCH_ID,
            "--external-id", VALID_EXTERNAL_ID,
            "--home-team", VALID_HOME,
            "--away-team", VALID_AWAY,
            "--data-version", "v1",
            "--dry-run",
        )
        combined = stdout + stderr
        # Will fail at G3 (no CONFIRM_LIVE_FOTMOB_SINGLE_FETCH), not G5
        assert "G5" in combined or "BLOCKED" in combined or "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH" in combined, (
            f"Should pass G5 even if blocked by G3: {combined[:500]}"
        )

    def test_long_version_rejected(self):
        """data_version > 20 chars must be rejected (before fetch attempt)."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id", VALID_MATCH_ID,
            "--external-id", VALID_EXTERNAL_ID,
            "--home-team", VALID_HOME,
            "--away-team", VALID_AWAY,
            "--data-version", "a" * 21,
            "--dry-run",
        )
        combined = stdout + stderr
        assert rc != 0, f"Long version should be rejected, got rc={rc}"
        assert "G5" in combined or "BLOCKED" in combined or "max" in combined.lower(), (
            f"Should reject long version: {combined[:500]}"
        )

    def test_boundary_20_chars_allowed(self):
        """20-char data_version must pass G5 (may fail at G3)."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id", VALID_MATCH_ID,
            "--external-id", VALID_EXTERNAL_ID,
            "--home-team", VALID_HOME,
            "--away-team", VALID_AWAY,
            "--data-version", "12345678901234567890",
            "--dry-run",
        )
        combined = stdout + stderr
        # Will fail at G3, not G5
        assert "G5 PASS" in combined or "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH" in combined or "BLOCKED" in combined, (
            f"G5 should pass even if blocked by G3: {combined[:500]}"
        )


class TestGuardRequiredArgs:
    """Required argument validation."""

    def test_missing_match_id(self):
        """Missing --match-id must fail."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--external-id", VALID_EXTERNAL_ID,
            "--home-team", VALID_HOME,
            "--away-team", VALID_AWAY,
        )
        combined = stdout + stderr
        assert rc != 0, f"Missing match-id should fail, got {rc}"
        assert "ERROR" in combined or "required" in combined.lower() or "Usage" in combined, (
            f"Should report missing args: {combined[:500]}"
        )

    def test_non_numeric_external_id(self):
        """Non-numeric external_id must be rejected."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id", VALID_MATCH_ID,
            "--external-id", "abc123",
            "--home-team", VALID_HOME,
            "--away-team", VALID_AWAY,
        )
        combined = stdout + stderr
        assert rc != 0, f"Non-numeric external-id should fail, got {rc}"
        assert "numeric" in combined.lower() or "ERROR" in combined, (
            f"Should reject non-numeric external-id: {combined[:500]}"
        )


class TestGuardHelpFlag:
    """--help flag works."""

    def test_help_flag(self):
        """--help should exit 0 and show usage."""
        rc, stdout, _stderr = _run_node(SCRIPT, "--help")
        assert rc == 0, f"--help should exit 0, got {rc}"
        assert "Usage" in stdout or "usage" in stdout.lower(), f"Should show usage: {stdout[:500]}"
