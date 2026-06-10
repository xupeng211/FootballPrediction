#!/usr/bin/env python3
"""
Minimal N=3 retain guard tests.

Tests the safety guards in scripts/ops/n3_live_fotmob_raw_retain.js
without performing live fetches. Verifies that:
- Missing CONFIRM env vars are blocked
- N > 3 is rejected
- Production DB is rejected
- Dry-run is the default
- Help text includes safety info

lifecycle: permanent / smoke-test
"""

import os
import subprocess

SCRIPT = "scripts/ops/n3_live_fotmob_raw_retain.js"
VALID_CONFIG = "configs/data/fotmob_n3_raw_retain_candidates.json"


def _run_node(script, *args, env=None):
    """Run the script with given args and return (returncode, stdout, stderr)."""
    base_env = os.environ.copy()
    for var in (
        "CONFIRM_LIVE_FOTMOB_SMALL_BATCH",
        "CONFIRM_LOCAL_DB_WRITE",
        "CONFIRM_RETAIN_RAW_DATA",
        "CONFIRM_MAX_MATCHES",
        "PGHOST",
        "PGPASSWORD",
    ):
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


class TestGuardRequiresLiveFotmobSmallBatch:
    """G3: CONFIRM_LIVE_FOTMOB_SMALL_BATCH=1 required for live fetch."""

    def test_dry_run_rejected_without_env(self):
        """Dry-run without CONFIRM_LIVE_FOTMOB_SMALL_BATCH blocked."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            VALID_CONFIG,
            "--dry-run",
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit without env, got {rc}"
        assert "BLOCKED" in combined or "CONFIRM_LIVE_FOTMOB_SMALL_BATCH" in combined, (
            f"Should mention CONFIRM_LIVE_FOTMOB_SMALL_BATCH: {combined[:500]}"
        )


class TestGuardRejectsWriteWithoutConfirm:
    """G1: CONFIRM_LOCAL_DB_WRITE=1 required."""

    def test_commit_rejected_without_db_env(self):
        """--commit without CONFIRM_LOCAL_DB_WRITE blocked."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            VALID_CONFIG,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LIVE_FOTMOB_SMALL_BATCH": "1",
                "CONFIRM_RETAIN_RAW_DATA": "1",
                "CONFIRM_MAX_MATCHES": "3",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit, got {rc}"
        assert "BLOCKED" in combined or "CONFIRM_LOCAL_DB_WRITE" in combined, (
            f"Should mention CONFIRM_LOCAL_DB_WRITE: {combined[:500]}"
        )


class TestGuardRejectsWithoutRetain:
    """G4: CONFIRM_RETAIN_RAW_DATA=1 required."""

    def test_commit_rejected_without_retain_env(self):
        """--retain without CONFIRM_RETAIN_RAW_DATA blocked."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            VALID_CONFIG,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LIVE_FOTMOB_SMALL_BATCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
                "CONFIRM_MAX_MATCHES": "3",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit, got {rc}"
        assert "BLOCKED" in combined or "CONFIRM_RETAIN_RAW_DATA" in combined, (
            f"Should mention CONFIRM_RETAIN_RAW_DATA: {combined[:500]}"
        )


class TestGuardRejectsWrongMaxMatches:
    """G5: CONFIRM_MAX_MATCHES must be exactly 3."""

    def test_max_matches_4_rejected(self):
        """CONFIRM_MAX_MATCHES=4 must be rejected."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            VALID_CONFIG,
            "--dry-run",
            env={
                "CONFIRM_LIVE_FOTMOB_SMALL_BATCH": "1",
                "CONFIRM_MAX_MATCHES": "4",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit, got {rc}"
        assert "BLOCKED" in combined or "G5" in combined or "MAX_MATCHES" in combined, (
            f"Should block MAX_MATCHES=4: {combined[:500]}"
        )

    def test_max_matches_2_rejected(self):
        """CONFIRM_MAX_MATCHES=2 must be rejected."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            VALID_CONFIG,
            "--dry-run",
            env={
                "CONFIRM_LIVE_FOTMOB_SMALL_BATCH": "1",
                "CONFIRM_MAX_MATCHES": "2",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit, got {rc}"
        assert "BLOCKED" in combined or "G5" in combined or "MAX_MATCHES" in combined, (
            f"Should block MAX_MATCHES=2: {combined[:500]}"
        )

    def test_max_matches_empty_rejected(self):
        """Missing CONFIRM_MAX_MATCHES must be rejected."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            VALID_CONFIG,
            "--dry-run",
            env={
                "CONFIRM_LIVE_FOTMOB_SMALL_BATCH": "1",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit, got {rc}"
        assert "BLOCKED" in combined or "G5" in combined or "MAX_MATCHES" in combined, (
            f"Should block missing MAX_MATCHES: {combined[:500]}"
        )


class TestGuardProductionDbDetection:
    """G2: Production DB URLs are rejected."""

    def test_rds_hostname_rejected(self):
        """RDS hostname must be detected as production."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            VALID_CONFIG,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LIVE_FOTMOB_SMALL_BATCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
                "CONFIRM_RETAIN_RAW_DATA": "1",
                "CONFIRM_MAX_MATCHES": "3",
                "PGHOST": "football-db.rds.amazonaws.com",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"RDS host should be rejected, got rc={rc}"
        assert "BLOCKED" in combined or "G2" in combined or "production" in combined.lower(), (
            f"Should detect production: {combined[:500]}"
        )

    def test_supabase_hostname_rejected(self):
        """Supabase hostname must be detected as production."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            VALID_CONFIG,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LIVE_FOTMOB_SMALL_BATCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
                "CONFIRM_RETAIN_RAW_DATA": "1",
                "CONFIRM_MAX_MATCHES": "3",
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
        ), f"Should detect production: {combined[:500]}"


class TestGuardDryRunIsDefault:
    """Default mode is dry-run (no DB writes, no network without confirm)."""

    def test_no_commit_flag_is_dry_run(self):
        """Without --commit, script exits after dry-run (fail at G3 is ok)."""
        _rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            VALID_CONFIG,
        )
        combined = stdout + stderr
        # Should either fail at G3 (no env) or complete dry-run
        is_dry_run_or_blocked = "DRY-RUN" in combined or "BLOCKED" in combined or "G3" in combined
        assert is_dry_run_or_blocked, (
            f"Should be dry-run or blocked (safety-first): {combined[:500]}"
        )


class TestGuardHelpFlag:
    """--help flag works and includes safety info."""

    def test_help_flag(self):
        """--help should exit 0 and show usage."""
        rc, stdout, _stderr = _run_node(SCRIPT, "--help")
        assert rc == 0, f"--help should exit 0, got {rc}"
        assert "Usage" in stdout or "usage" in stdout.lower(), f"Should show usage: {stdout[:500]}"

    def test_help_mentions_n3(self):
        """--help should mention exactly 3 matches batch info."""
        rc, stdout, _stderr = _run_node(SCRIPT, "--help")
        assert rc == 0
        assert "Exactly 3 matches" in stdout or "3 matches" in stdout, (
            f"Help should mention 3-match batch: {stdout[:500]}"
        )

    def test_help_mentions_safety_env_vars(self):
        """--help should mention required CONFIRM env vars."""
        rc, stdout, _stderr = _run_node(SCRIPT, "--help")
        assert rc == 0
        combined = stdout
        assert (
            "CONFIRM_LIVE_FOTMOB_SMALL_BATCH" in combined
            or "CONFIRM_LOCAL_DB_WRITE" in combined
            or "CONFIRM_RETAIN_RAW_DATA" in combined
            or "CONFIRM_MAX_MATCHES" in combined
        ), f"Help should mention safety env vars: {combined[:500]}"


class TestGuardDataVersionLength:
    """G6: data_version ≤ 20 chars."""

    def test_long_version_rejected(self):
        """data_version > 20 must be rejected."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            VALID_CONFIG,
            "--data-version",
            "a" * 21,
            "--dry-run",
        )
        combined = stdout + stderr
        assert rc != 0, f"Long version should be rejected, got {rc}"
        assert "G6" in combined or "BLOCKED" in combined or "max" in combined.lower(), (
            f"Should reject long version: {combined[:500]}"
        )


class TestGuardConfigFile:
    """Config file validation."""

    def test_missing_config_file(self):
        """Missing config file must error."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            "nonexistent.json",
            "--dry-run",
        )
        combined = stdout + stderr
        assert rc != 0, f"Missing config should fail, got {rc}"
        assert "ERROR" in combined or "not found" in combined.lower(), (
            f"Should report missing config: {combined[:500]}"
        )


class TestGuardNoRawPayloadDump:
    """Script must not print full raw payload or pageProps."""

    def test_dry_run_does_not_dump_raw_payload(self):
        """Dry-run must not contain raw_data content dumps."""
        _rc, stdout, stderr = _run_node(
            SCRIPT,
            "--config",
            VALID_CONFIG,
            "--dry-run",
            env={
                "CONFIRM_LIVE_FOTMOB_SMALL_BATCH": "1",
                "CONFIRM_MAX_MATCHES": "3",
            },
        )
        combined = stdout + stderr
        # Dry-run summary must NOT contain raw JSON content
        assert '"matchId"' not in combined, "Should not print raw payload JSON in dry-run"
        assert '"pageProps"' not in combined, "Should not print pageProps in dry-run"
