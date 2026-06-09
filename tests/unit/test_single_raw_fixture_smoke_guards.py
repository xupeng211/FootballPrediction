#!/usr/bin/env python3
"""
Minimal smoke-tool guard tests.

Tests the safety guards in scripts/ops/single_raw_match_data_ingest.js
without actually running the full ingestion pipeline. These tests verify
that the guard logic rejects unsafe configurations.

lifecycle: permanent / smoke-test
"""

import os
import subprocess

SCRIPT = "scripts/ops/single_raw_match_data_ingest.js"
VALID_FIXTURE = "data/raw/fotmob/match_detail/53_20252026_4830474.payload.html"
VALID_MATCH_ID = "53_20252026_4830474"


def _run_node(script, *args, env=None):
    """Run the script with given args and return (returncode, stdout, stderr)."""
    base_env = os.environ.copy()
    base_env.pop("CONFIRM_LOCAL_DB_WRITE", None)  # ensure clean state
    base_env.pop("PGHOST", None)
    base_env.pop("PGPASSWORD", None)
    if env:
        base_env.update(env)

    # Use node from the dev container if available, else host node
    node_bin = os.environ.get("NODE_BIN", "node")

    result = subprocess.run(
        [node_bin, script, *list(args)],
        check=False, capture_output=True,
        text=True,
        env=base_env,
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


class TestGuardRejectsWriteWithoutConfirm:
    """G1: CONFIRM_LOCAL_DB_WRITE=1 required for any DB write."""

    def test_dry_run_succeeds_without_env_var(self):
        """Dry-run (default) must succeed without CONFIRM_LOCAL_DB_WRITE."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--fixture", VALID_FIXTURE,
            "--match-id", VALID_MATCH_ID,
            "--dry-run",
        )
        # Should succeed in dry-run mode
        assert rc == 0, f"dry-run failed: {stderr}"
        assert "DRY-RUN" in stdout or "No DB" in stdout

    def test_commit_rejected_without_env_var(self):
        """--commit without CONFIRM_LOCAL_DB_WRITE must be blocked."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--fixture", VALID_FIXTURE,
            "--match-id", VALID_MATCH_ID,
            "--commit",
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit, got {rc}"
        assert "BLOCKED" in combined or "CONFIRM_LOCAL_DB_WRITE" in combined, (
            f"Should mention CONFIRM_LOCAL_DB_WRITE, got: {combined[:500]}"
        )


class TestGuardProductionDbDetection:
    """G2: Production DB URLs are rejected."""

    def test_rds_hostname_rejected(self):
        """RDS hostname must be detected as production."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--fixture", VALID_FIXTURE,
            "--match-id", VALID_MATCH_ID,
            "--commit",
            env={"CONFIRM_LOCAL_DB_WRITE": "1", "PGHOST": "football-db.rds.amazonaws.com"},
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
            "--fixture", VALID_FIXTURE,
            "--match-id", VALID_MATCH_ID,
            "--commit",
            env={"CONFIRM_LOCAL_DB_WRITE": "1", "PGHOST": "db.abc123.supabase.co"},
        )
        combined = stdout + stderr
        assert rc != 0, f"Supabase host should be rejected, got rc={rc}"
        assert "BLOCKED" in combined or "G2" in combined or "production" in combined.lower() or "whitelist" in combined.lower(), (
            f"Should detect production pattern: {combined[:500]}"
        )

    def test_unknown_host_rejected_fail_closed(self):
        """Unknown host not in whitelist must be rejected (fail-closed)."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--fixture", VALID_FIXTURE,
            "--match-id", VALID_MATCH_ID,
            "--commit",
            env={"CONFIRM_LOCAL_DB_WRITE": "1", "PGHOST": "some-random-host.example.com"},
        )
        combined = stdout + stderr
        assert rc != 0, f"Unknown host should be rejected (fail-closed), got rc={rc}"
        assert "BLOCKED" in combined or "G2" in combined or "whitelist" in combined.lower(), (
            f"Should reject unknown host: {combined[:500]}"
        )


class TestGuardDataVersionLength:
    """G5: data_version ≤ 20 characters."""

    def test_short_version_allowed(self):
        """Short data_version must pass."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--fixture", VALID_FIXTURE,
            "--match-id", VALID_MATCH_ID,
            "--data-version", "v1",
            "--dry-run",
        )
        combined = stdout + stderr
        assert rc == 0, f"Short version should pass: {combined[:500]}"
        assert "G5 PASS" in combined or "data_version" in combined, (
            f"Should mention G5: {combined[:500]}"
        )

    def test_long_version_rejected(self):
        """data_version > 20 chars must be rejected."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--fixture", VALID_FIXTURE,
            "--match-id", VALID_MATCH_ID,
            "--data-version", "a" * 21,  # 21 chars
            "--dry-run",
        )
        combined = stdout + stderr
        assert rc != 0, f"Long version should be rejected, got rc={rc}"
        assert "G5" in combined or "BLOCKED" in combined or "max" in combined.lower(), (
            f"Should reject long version: {combined[:500]}"
        )

    def test_boundary_20_chars_allowed(self):
        """20-char data_version must pass (boundary)."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--fixture", VALID_FIXTURE,
            "--match-id", VALID_MATCH_ID,
            "--data-version", "12345678901234567890",  # exactly 20 chars
            "--dry-run",
        )
        combined = stdout + stderr
        assert rc == 0, f"20-char version should pass: {combined[:500]}"


class TestGuardFixturePath:
    """Fixture path guards."""

    def test_missing_fixture_fails(self):
        """Nonexistent fixture must fail."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--fixture", "/nonexistent/path/fixture.html",
            "--match-id", VALID_MATCH_ID,
            "--dry-run",
        )
        combined = stdout + stderr
        assert rc != 0, f"Missing fixture should fail: got rc={rc}"
        assert "not found" in combined.lower() or "FAIL" in combined, (
            f"Should report missing fixture: {combined[:500]}"
        )

    def test_url_fixture_rejected(self):
        """URL as fixture path must be rejected (G3 no-network)."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--fixture", "https://www.fotmob.com/match/4830474",
            "--match-id", VALID_MATCH_ID,
            "--dry-run",
        )
        combined = stdout + stderr
        assert rc != 0, f"URL fixture should be rejected, got rc={rc}"
        assert "G3" in combined or "URL" in combined or "BLOCKED" in combined or "network" in combined.lower(), (
            f"Should reject URL fixture: {combined[:500]}"
        )


class TestGuardHelpFlag:
    """--help flag works."""

    def test_help_flag(self):
        """--help should exit 0 and show usage."""
        rc, stdout, _stderr = _run_node(SCRIPT, "--help")
        assert rc == 0, f"--help should exit 0, got {rc}"
        assert "Usage" in stdout or "usage" in stdout.lower(), (
            f"Should show usage: {stdout[:500]}"
        )
