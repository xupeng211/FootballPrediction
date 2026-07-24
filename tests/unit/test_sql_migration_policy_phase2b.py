#!/usr/bin/env python3
"""Tests for SQL Migration Policy Phase2B."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

_R = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_R / "scripts" / "ops"))
import sql_migration_policy_static_enforcement as policy_scanner  # noqa: E402
from sql_migration_policy_static_enforcement import (  # noqa: E402
    REVIEWED_SANDBOX_CLASSIFICATION,
    UNCONDITIONALLY_FORBIDDEN_OPERATIONS,
    _load_al,
    _reviewed_sandbox_policy_passes,
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
        assert any(
            marker in r["classification"]
            for marker in ("seed", "dml", "needs_policy_review")
        )

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


class TestReviewedSandboxPolicy:
    PATHS = [
        "database/sandbox/m3_odds_staging/bootstrap_roles.sql",
        "database/sandbox/m3_odds_staging/finalize_staging_grants.sql",
    ]

    def test_exact_reviewed_entries_pass(self):
        result = changed_files_check(self.PATHS)
        assert not result["would_hard_fail"]
        assert {r["recommended_next_action"] for r in result["passed"]} == {
            "reviewed_sandbox_policy"
        }

    def test_entry_metadata_is_complete_and_nonhistorical(self):
        allowlist = _load_al()
        for path in self.PATHS:
            entry = allowlist[path]
            assert entry["classification"] == REVIEWED_SANDBOX_CLASSIFICATION
            assert not entry["classification"].startswith("historical_sql_")
            assert entry["environment_scope"] == "local_nonproduction_sandbox_only"
            assert entry["execution_authorized"] is False
            assert entry["review_status"] == "explicitly_reviewed"

    @pytest.mark.parametrize("operation", sorted(UNCONDITIONALLY_FORBIDDEN_OPERATIONS))
    def test_forbidden_operation_fails_closed(self, operation):
        result = {
            "path": self.PATHS[0],
            "file_type": "sql_other",
            "ddl_signals": [],
            "dml_signals": [],
            "privilege_signals": [],
            "destructive_signals": [{"signal": operation, "evidence_type": "executable_context"}],
            "migration_api_signals": [],
        }
        assert not _reviewed_sandbox_policy_passes(result, _load_al()[self.PATHS[0]])

    def test_unlisted_operation_fails_closed(self):
        result = {
            "path": self.PATHS[1], "file_type": "sql_other", "ddl_signals": [],
            "dml_signals": [], "destructive_signals": [], "migration_api_signals": [],
            "privilege_signals": [{"signal": "CREATE_ROLE", "evidence_type": "executable_context"}],
        }
        assert not _reviewed_sandbox_policy_passes(result, _load_al()[self.PATHS[1]])

    @pytest.mark.parametrize(
        "path",
        [
            "database/migrations/V99.9__not_allowed.sql",
            "deploy/docker/not_allowed.sql",
        ],
    )
    def test_reviewed_entry_cannot_escape_sandbox_path(self, path):
        entry = dict(_load_al()[self.PATHS[0]])
        result = _scan(_R / self.PATHS[0])
        result["path"] = path
        assert not _reviewed_sandbox_policy_passes(result, entry)

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("environment_scope", None),
            ("execution_authorized", True),
            ("review_status", "pending"),
        ],
    )
    def test_required_review_metadata_fails_closed(self, field, value):
        entry = dict(_load_al()[self.PATHS[0]])
        result = _scan(_R / self.PATHS[0])
        entry[field] = value
        assert not _reviewed_sandbox_policy_passes(result, entry)

    def test_third_unreviewed_sandbox_file_does_not_pass_by_directory(self, tmp_path, monkeypatch):
        relative_path = "database/sandbox/m3_odds_staging/unreviewed_policy_probe.sql"
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True)
        path.write_text("REVOKE ALL PRIVILEGES ON TABLE probe_table FROM PUBLIC;\n")
        allowlist = tmp_path / "allowlist.json"
        allowlist.write_text("{}\n")
        monkeypatch.setattr(policy_scanner, "REPO_ROOT", tmp_path)

        result = policy_scanner.changed_files_check([relative_path], ap=allowlist)

        assert result["would_hard_fail"]
        assert result["violations"][0]["allowlist_status"] == "not_in_allowlist"


class TestDocs:
    def test_not_complete(self):
        assert "SC-002 is fully fixed" not in (_R / "docs/SC002_CLOSURE_PLAN.md").read_text()

    def test_blocked(self):
        assert "blocked" in (_R / "docs/PROJECT_STATUS.md").read_text().lower()


class TestCLI:
    def test_validate(self):
        p = subprocess.run(
            [
                sys.executable,
                str(_R / "scripts/ops/sql_migration_policy_static_enforcement.py"),
                "--validate-allowlist",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert p.returncode == 0, p.stdout
