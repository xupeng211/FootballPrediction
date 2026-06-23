#!/usr/bin/env python3
"""Tests for SQL Migration Policy Phase2B."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

_R = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_R / "scripts" / "ops"))
from sql_migration_policy_static_enforcement import (  # noqa: E402
    _load_al,
    _scan,
    _validate_entry,
    changed_files_check,
    scan_files,
)


class TestScanner:
    def test_schema(self):
        r = _scan(_R / "database/migrations/V12.4__create_matches_oddsportal_mapping.sql")
        assert r["classification"] == "sql_schema_definition"

    def test_seed(self):
        r = _scan(_R / "deploy/docker/init_db.sql")
        assert "seed" in r["classification"] or "dml" in r["classification"]

    def test_alembic(self):
        p = _R / "src/database/migrations/versions/001_initial_migration.py"
        if p.exists():
            assert _scan(p)["file_type"] == "alembic_migration"

    def test_docs(self):
        r = _scan(_R / "docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN_SQL_PREVIEW.sql")
        assert r["classification"] == "sql_docs_or_example_only"

    def test_no_exec(self):
        assert (
            "psycopg"
            not in (_R / "scripts/ops/sql_migration_policy_static_enforcement.py").read_text()
        )

    def test_allowlist(self):
        assert (
            scan_files(["database/migrations/V6.6__hardened_l2_raw_storage.sql"])[0][
                "allowlist_status"
            ]
            == "in_allowlist"
        )


class TestAllowlist:
    @pytest.fixture(autouse=True)
    def _a(self):
        p = _R / "config/sql_migration_policy_allowlist.json"
        self.al = _load_al(p) if p.exists() else {}

    def test_entries(self):
        assert len(self.al) >= 21  # noqa: PLR2004

    def test_complete(self):
        for p, e in self.al.items():
            assert not _validate_entry(e), p

    def test_no_wildcards(self):
        for p in self.al:
            assert "*" not in p

    def test_seed_not_safe(self):
        for e in self.al.values():
            if "seed" in e.get("classification", ""):
                assert "needs_gate" in e["classification"]

    def test_disclaims(self):
        assert (
            "DOES NOT AUTHORIZE" in (_R / "config/sql_migration_policy_allowlist.json").read_text()
        )


class TestChangedFiles:
    def test_allowlisted(self):
        assert not changed_files_check(
            ["database/migrations/V12.2__add_matches_pipeline_status.sql"]
        )["would_hard_fail"]

    def test_docs(self):
        assert changed_files_check(["docs/README.md"]).get("note") is not None


class TestDocs:
    def test_not_complete(self):
        assert "SC-002 is fully fixed" not in (_R / "docs/SC002_CLOSURE_PLAN.md").read_text()

    def test_blocked(self):
        assert "blocked" in (_R / "docs/PROJECT_STATUS.md").read_text().lower()


class TestCLI:
    def test_validate(self):
        p = subprocess.run(
            [
                "python",
                str(_R / "scripts/ops/sql_migration_policy_static_enforcement.py"),
                "--validate-allowlist",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert p.returncode == 0, p.stdout
