#!/usr/bin/env python3
"""
Minimal retain-mode guard tests.

Tests the --retain safety guards added to
scripts/ops/single_live_fotmob_raw_ingest_smoke.js without actually
performing live fetches.  These tests verify that the G11 guard
(CONFIRM_RETAIN_RAW_DATA=1) and related safety boundaries work.

lifecycle: permanent / smoke-test
"""

import os
import subprocess

SCRIPT = "scripts/ops/single_live_fotmob_raw_ingest_smoke.js"
VALID_MATCH_ID = "53_20252026_4830507"
VALID_EXTERNAL_ID = "4830507"
VALID_HOME = "Nice"
VALID_AWAY = "Paris FC"
VALID_DATA_VERSION = "fotmob_live_v1"


def _run_node(script, *args, env=None):
    """Run the script with given args and return (returncode, stdout, stderr)."""
    base_env = os.environ.copy()
    base_env.pop("CONFIRM_LIVE_FOTMOB_SINGLE_FETCH", None)
    base_env.pop("CONFIRM_LOCAL_DB_WRITE", None)
    base_env.pop("CONFIRM_RETAIN_RAW_DATA", None)
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


class TestGuardRetainRequiresConfirmation:
    """G11: CONFIRM_RETAIN_RAW_DATA=1 required for --retain mode."""

    def test_retain_without_confirm_env_is_blocked(self):
        """--retain without CONFIRM_RETAIN_RAW_DATA must be blocked."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id",
            VALID_MATCH_ID,
            "--external-id",
            VALID_EXTERNAL_ID,
            "--home-team",
            VALID_HOME,
            "--away-team",
            VALID_AWAY,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit without CONFIRM_RETAIN_RAW_DATA, got {rc}"
        assert (
            "BLOCKED" in combined or "G11" in combined or "CONFIRM_RETAIN_RAW_DATA" in combined
        ), f"Should mention G11 or CONFIRM_RETAIN_RAW_DATA: {combined[:500]}"

    def test_retain_with_confirm_env_proceeds_past_g11(self):
        """--retain with CONFIRM_RETAIN_RAW_DATA=1 passes G11 (may fail later at G2)."""
        _rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id",
            VALID_MATCH_ID,
            "--external-id",
            VALID_EXTERNAL_ID,
            "--home-team",
            VALID_HOME,
            "--away-team",
            VALID_AWAY,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
                "CONFIRM_RETAIN_RAW_DATA": "1",
            },
        )
        combined = stdout + stderr
        # Will pass G11 but likely fail at G2 (no DB host whitelisted),
        # G6 (no FK), or at the live fetch stage. The key is G11 should
        # NOT be the blocker.
        assert "G11" not in combined or "G11 PASS" in combined, (
            f"G11 should not be the blocker: {combined[:500]}"
        )

    def test_retain_with_confirm_but_no_live_fetch_env_is_blocked(self):
        """--retain without CONFIRM_LIVE_FOTMOB_SINGLE_FETCH blocked at G3."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id",
            VALID_MATCH_ID,
            "--external-id",
            VALID_EXTERNAL_ID,
            "--home-team",
            VALID_HOME,
            "--away-team",
            VALID_AWAY,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LOCAL_DB_WRITE": "1",
                "CONFIRM_RETAIN_RAW_DATA": "1",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit without live fetch env, got {rc}"
        assert (
            "BLOCKED" in combined
            or "G3" in combined
            or "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH" in combined
        ), f"Should block at G3, not later: {combined[:500]}"


class TestGuardRetainStillRejectsProductionDb:
    """G2 applies to retain mode as well."""

    def test_retain_with_rds_hostname_rejected(self):
        """RDS host must be rejected even in retain mode."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id",
            VALID_MATCH_ID,
            "--external-id",
            VALID_EXTERNAL_ID,
            "--home-team",
            VALID_HOME,
            "--away-team",
            VALID_AWAY,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
                "CONFIRM_RETAIN_RAW_DATA": "1",
                "PGHOST": "football-db.rds.amazonaws.com",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"RDS host should be rejected, got rc={rc}"
        assert "BLOCKED" in combined or "G2" in combined or "production" in combined.lower(), (
            f"Should detect production pattern: {combined[:500]}"
        )

    def test_retain_with_supabase_hostname_rejected(self):
        """Supabase host must be rejected even in retain mode."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id",
            VALID_MATCH_ID,
            "--external-id",
            VALID_EXTERNAL_ID,
            "--home-team",
            VALID_HOME,
            "--away-team",
            VALID_AWAY,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
                "CONFIRM_RETAIN_RAW_DATA": "1",
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


class TestGuardDataVersionLengthInRetainMode:
    """G5: data_version ≤ 20 also applies in retain mode."""

    def test_retain_with_long_version_rejected(self):
        """data_version > 20 chars must be rejected even with --retain."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id",
            VALID_MATCH_ID,
            "--external-id",
            VALID_EXTERNAL_ID,
            "--home-team",
            VALID_HOME,
            "--away-team",
            VALID_AWAY,
            "--data-version",
            "a" * 21,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
                "CONFIRM_RETAIN_RAW_DATA": "1",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"Long version should be rejected, got rc={rc}"
        assert "G5" in combined or "BLOCKED" in combined or "max" in combined.lower(), (
            f"Should reject long version: {combined[:500]}"
        )

    def test_retain_with_valid_version_passes_g5(self):
        """fotmob_live_v1 (14 chars) passes G5."""
        _rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id",
            VALID_MATCH_ID,
            "--external-id",
            VALID_EXTERNAL_ID,
            "--home-team",
            VALID_HOME,
            "--away-team",
            VALID_AWAY,
            "--data-version",
            VALID_DATA_VERSION,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
                "CONFIRM_RETAIN_RAW_DATA": "1",
            },
        )
        combined = stdout + stderr
        assert "G5 PASS" in combined, f"fotmob_live_v1 (14 chars) should pass G5: {combined[:500]}"


class TestSmokeModeUnchangedByRetainFeature:
    """Default smoke mode must still clean up. Retain feature must not break it."""

    def test_smoke_mode_does_not_require_retain_env(self):
        """Default smoke mode (no --retain) must NOT require CONFIRM_RETAIN_RAW_DATA."""
        _rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id",
            VALID_MATCH_ID,
            "--external-id",
            VALID_EXTERNAL_ID,
            "--home-team",
            VALID_HOME,
            "--away-team",
            VALID_AWAY,
            "--commit",
            env={
                "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH": "1",
                "CONFIRM_LOCAL_DB_WRITE": "1",
            },
        )
        combined = stdout + stderr
        # Should NOT block on G11 (retain guard) since --retain was not passed.
        assert "G11" not in combined or "G11 PASS" in combined, (
            f"Smoke mode should not trigger G11 guard: {combined[:500]}"
        )


class TestGuardHelpIncludesRetainInfo:
    """--help text must mention retain mode and its risks."""

    def test_help_mentions_retain(self):
        """--help should document --retain flag."""
        rc, stdout, _stderr = _run_node(SCRIPT, "--help")
        assert rc == 0, f"--help should exit 0, got {rc}"
        assert "--retain" in stdout, f"Help should mention --retain flag: {stdout[:500]}"

    def test_help_mentions_retain_risk(self):
        """--help should mention retain risk / CONFIRM_RETAIN_RAW_DATA."""
        rc, stdout, _stderr = _run_node(SCRIPT, "--help")
        assert rc == 0, f"--help should exit 0, got {rc}"
        combined_lower = stdout.lower()
        has_retain = "retain" in combined_lower
        has_confirm = (
            "confirm_retain_raw_data" in combined_lower
            or "keep" in combined_lower
            or "permanent" in combined_lower
        )
        assert has_retain, f"Help should mention retain: {stdout[:500]}"
        assert has_confirm, f"Help should warn about retain permanence: {stdout[:500]}"


class TestGuardRetainWithDbWriteWithoutConfirm:
    """G1: retain without CONFIRM_LOCAL_DB_WRITE=1 is blocked."""

    def test_retain_without_db_write_env_is_blocked(self):
        """--retain --commit without CONFIRM_LOCAL_DB_WRITE blocked at G1."""
        rc, stdout, stderr = _run_node(
            SCRIPT,
            "--match-id",
            VALID_MATCH_ID,
            "--external-id",
            VALID_EXTERNAL_ID,
            "--home-team",
            VALID_HOME,
            "--away-team",
            VALID_AWAY,
            "--commit",
            "--retain",
            env={
                "CONFIRM_LIVE_FOTMOB_SINGLE_FETCH": "1",
                "CONFIRM_RETAIN_RAW_DATA": "1",
            },
        )
        combined = stdout + stderr
        assert rc != 0, f"Expected non-zero exit without CONFIRM_LOCAL_DB_WRITE, got {rc}"
        assert "BLOCKED" in combined or "CONFIRM_LOCAL_DB_WRITE" in combined, (
            f"Should mention CONFIRM_LOCAL_DB_WRITE: {combined[:500]}"
        )
