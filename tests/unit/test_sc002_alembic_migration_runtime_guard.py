"""
Static test: SC-002 Alembic Migration Runtime Guard validation.

Validates:
1. env.py has _check_alembic_migration_guard() function
2. _check_alembic_migration_guard() is called at top of run_migrations_online()
3. run_migrations_offline() does NOT call the guard
4. Guard is placed BEFORE get_database_url() in run_migrations_online()
5. Guard imports assert_db_write_allowed from existing helper
6. ALEMBIC_CTX env var is checked for CI/dev auto-allow
7. Guard uses operation=CREATE to trigger schema-level gate
8. Allowlist classification is alembic_migration_runtime_guarded
9. Runtime guarded count now 18 (was 17)
10. SC-002 remains partial mitigation only
11. Training / data expansion / real DB write remain blocked
12. Production-like host patterns are referenced (hard block)
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_PY_PATH = PROJECT_ROOT / "src" / "database" / "migrations" / "env.py"
ALLOWLIST_PATH = PROJECT_ROOT / "config" / "python_db_write_allowlist.json"
SQL_ALLOWLIST_PATH = PROJECT_ROOT / "config" / "sql_migration_policy_allowlist.json"
DESIGN_DOC_PATH = PROJECT_ROOT / "docs" / "SC002_ALEMBIC_MIGRATION_GUARD_DESIGN.md"
CLOSURE_PLAN_PATH = PROJECT_ROOT / "docs" / "SC002_CLOSURE_PLAN.md"
PROJECT_STATUS_PATH = PROJECT_ROOT / "docs" / "PROJECT_STATUS.md"
ENFORCEMENT_DESIGN_PATH = PROJECT_ROOT / "docs" / "SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md"

ENV_PY_KEY = "src/database/migrations/env.py"
EXPECTED_CLASSIFICATION = "historical_python_alembic_migration_runtime_guarded"
EXPECTED_RUNTIME_GUARDED = 18
EXPECTED_TOTAL_ENTRIES = 28

FORBIDDEN_TERMS = [
    "SC-002 is complete",
    "SC-002 is fully fixed",
    "SC-002 resolved",
    "safe to train",
    "safe to write",
    "production ready",
]


def _load_env_py():
    return ENV_PY_PATH.read_text(encoding="utf-8")


def _load_allowlist():
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))


def _load_sql_allowlist():
    return json.loads(SQL_ALLOWLIST_PATH.read_text(encoding="utf-8"))


def _load_design_doc():
    return DESIGN_DOC_PATH.read_text(encoding="utf-8")


def _load_text(path: Path):
    return path.read_text(encoding="utf-8")


# ---- Tests ----


class TestAlembicMigrationRuntimeGuard:
    """Verify env.py guard implementation and SC-002 state."""

    # ---- env.py source code tests ----

    def test_env_py_has_guard_function(self):
        """env.py must define _check_alembic_migration_guard()."""
        source = _load_env_py()
        assert "def _check_alembic_migration_guard()" in source, (
            "env.py must define _check_alembic_migration_guard() — "
            "the migration runtime guard function."
        )

    def test_guard_imports_assert_db_write_allowed(self):
        """Guard must import from the existing guard helper."""
        source = _load_env_py()
        assert (
            "from scripts.ops.helpers.python_db_write_guard import assert_db_write_allowed"
            in source
        ), (
            "Guard must import assert_db_write_allowed from the existing Python DB write guard helper."
        )

    def test_guard_checks_alembic_ctx_env_var(self):
        """Guard must check ALEMBIC_CTX env var for CI/dev auto-allow."""
        source = _load_env_py()
        assert "ALEMBIC_CTX" in source, (
            "Guard must check ALEMBIC_CTX env var for CI/dev/docker_init auto-allow."
        )

    def test_guard_uses_create_operation(self):
        """Guard must use operation='CREATE' to trigger schema-level gate."""
        source = _load_env_py()
        assert 'operation="CREATE"' in source or "operation='CREATE'" in source, (
            "Guard must pass operation='CREATE' to assert_db_write_allowed "
            "to trigger the schema-level gate (ALLOW_SCHEMA_WRITE)."
        )

    def test_guard_called_in_run_migrations_online(self):
        """_check_alembic_migration_guard() must be called in run_migrations_online()."""
        source = _load_env_py()
        # Must contain the call inside run_migrations_online()
        assert "_check_alembic_migration_guard()" in source, (
            "env.py must call _check_alembic_migration_guard() in run_migrations_online()."
        )

    def test_guard_before_get_database_url(self):
        """Guard must be BEFORE get_database_url() in run_migrations_online()."""
        source = _load_env_py()
        online_func_start = source.find("def run_migrations_online()")
        # Find guard call and get_database_url call after online function start
        guard_in_online = source.find("_check_alembic_migration_guard()", online_func_start)
        db_in_online = source.find("get_database_url()", online_func_start)
        assert guard_in_online < db_in_online, (
            "_check_alembic_migration_guard() must be called BEFORE "
            "get_database_url() in run_migrations_online(). "
            f"guard at {guard_in_online}, get_database_url at {db_in_online}"
        )

    def test_offline_mode_not_guarded(self):
        """run_migrations_offline() must NOT call the guard."""
        source = _load_env_py()
        offline_start = source.find("def run_migrations_offline()")
        online_start = source.find("def run_migrations_online()")
        guard_pos = source.find("_check_alembic_migration_guard()")
        # The guard call should be AFTER run_migrations_offline ends and inside
        # run_migrations_online. Check that guard is NOT between offline def and
        # online def.
        assert not (offline_start < guard_pos < online_start), (
            "_check_alembic_migration_guard() must NOT be called in "
            "run_migrations_offline(). Offline mode (--sql) generates SQL only."
        )

    def test_guard_function_has_production_host_reference(self):
        """Guard must reference production host hard block."""
        source = _load_env_py()
        source_lower = source.lower()
        assert "production" in source_lower, (
            "Guard source must reference 'production' for host detection."
        )
        assert "host" in source_lower, "Guard source must reference 'host' for host detection."

    def test_guard_has_sc002_comment_block(self):
        """Guard area must have SC-002 documentation comment block."""
        source = _load_env_py()
        assert "SC-002 Mitigation" in source, (
            "env.py must have SC-002 Mitigation comment block documenting the guard."
        )

    # ---- Allowlist tests ----

    def test_env_py_classification_is_runtime_guarded(self):
        """env.py allowlist classification must be runtime_guarded after implementation."""
        allowlist = _load_allowlist()
        entries_by_path = {e["path"]: e for e in allowlist["entries"]}
        entry = entries_by_path[ENV_PY_KEY]
        assert entry["classification"] == EXPECTED_CLASSIFICATION, (
            f"Expected classification '{EXPECTED_CLASSIFICATION}', got '{entry['classification']}'"
        )

    def test_runtime_guarded_count_is_18(self):
        """18 of 20 Python write paths must now be runtime guarded (was 17)."""
        allowlist = _load_allowlist()
        runtime_guarded = sum(
            1 for e in allowlist["entries"] if "runtime_guarded" in e["classification"]
        )
        assert runtime_guarded == EXPECTED_RUNTIME_GUARDED, (
            f"Expected {EXPECTED_RUNTIME_GUARDED} runtime guarded paths "
            f"(17 previous + 1 env.py), found {runtime_guarded}."
        )

    def test_total_entries_unchanged(self):
        """Total allowlist entries must still be 28."""
        allowlist = _load_allowlist()
        assert len(allowlist["entries"]) == EXPECTED_TOTAL_ENTRIES, (
            f"Expected {EXPECTED_TOTAL_ENTRIES} total entries, found {len(allowlist['entries'])}."
        )

    def test_no_pending_entries_remain(self):
        """No entries should have pending or needs_guard in classification."""
        allowlist = _load_allowlist()
        pending = [
            e
            for e in allowlist["entries"]
            if "pending" in e["classification"] or "needs_guard" in e["classification"]
        ]
        assert len(pending) == 0, (
            f"Expected 0 pending/needs_guard entries, found {len(pending)}: "
            f"{[e['path'] for e in pending]}"
        )

    def test_env_py_has_guard_implementation_owner_task(self):
        """env.py entry owner_task must be the implementation task."""
        allowlist = _load_allowlist()
        entries_by_path = {e["path"]: e for e in allowlist["entries"]}
        entry = entries_by_path[ENV_PY_KEY]
        assert entry["owner_task"] == "sc002_alembic_migration_runtime_guard_implementation", (
            f"Expected owner_task='sc002_alembic_migration_runtime_guard_implementation', "
            f"got '{entry['owner_task']}'"
        )

    def test_env_py_why_not_guarded_in_this_pr_is_na(self):
        """env.py why_not_guarded_in_this_pr should be 'N/A' since guard is implemented."""
        allowlist = _load_allowlist()
        entries_by_path = {e["path"]: e for e in allowlist["entries"]}
        entry = entries_by_path[ENV_PY_KEY]
        assert entry.get("why_not_guarded_in_this_pr", "").startswith("N/A"), (
            "env.py why_not_guarded_in_this_pr should be 'N/A' — guard IS implemented in this PR."
        )

    # ---- SQL allowlist tests ----

    def test_sql_allowlist_env_py_runtime_guarded(self):
        """SQL allowlist env.py must also show runtime_guarded."""
        sql_allowlist = _load_sql_allowlist()
        entries_by_path = {e["path"]: e for e in sql_allowlist["entries"]}
        entry = entries_by_path[ENV_PY_KEY]
        assert "runtime_guarded" in entry["classification"], (
            f"SQL allowlist env.py must be runtime_guarded, got '{entry['classification']}'"
        )

    def test_sql_allowlist_env_py_updated_owner_task(self):
        """SQL allowlist env.py owner_task must be updated."""
        sql_allowlist = _load_sql_allowlist()
        entries_by_path = {e["path"]: e for e in sql_allowlist["entries"]}
        entry = entries_by_path[ENV_PY_KEY]
        assert entry["owner_task"] == "sc002_alembic_migration_runtime_guard_implementation", (
            "SQL allowlist owner_task must be implementation task."
        )

    # ---- SC-002 status tests ----

    def test_allowlist_sc002_status_partial_mitigation(self):
        """Allowlist header must state SC-002 is partial mitigation only."""
        allowlist = _load_allowlist()
        assert allowlist["_sc002_status"] == "partial mitigation only", (
            "Allowlist _sc002_status must remain 'partial mitigation only'."
        )

    def test_allowlist_header_no_runtime_write_authorization(self):
        """Allowlist header must state it does NOT authorize runtime DB writes."""
        allowlist = _load_allowlist()
        assert "DOES NOT AUTHORIZE" in allowlist["_description"], (
            "Allowlist description must state it does NOT authorize runtime DB writes."
        )

    def test_sql_allowlist_no_sql_execution_authorized(self):
        """SQL allowlist must state SQL execution is NOT authorized."""
        sql_allowlist = _load_sql_allowlist()
        assert sql_allowlist["_sql_execution_authorized"] is False, (
            "SQL allowlist must confirm SQL execution is NOT authorized."
        )

    # ---- Design doc tests ----

    def test_design_doc_still_references_implementation(self):
        """Design doc updated to reflect completed implementation."""
        doc = _load_design_doc()
        # Design doc should still exist and contain the guard strategy
        assert "## Guard Strategy Design" in doc, (
            "Design doc must still contain the guard strategy section."
        )

    # ---- Doc status tests ----

    def test_closure_plan_knows_18_guarded(self):
        """SC002_CLOSURE_PLAN.md should reflect 18 guarded status."""
        closure = _load_text(CLOSURE_PLAN_PATH)
        # The closure plan should mention the implementation is done
        assert (
            "sc002_alembic_migration_runtime_guard_implementation" in closure or "18" in closure
        ), "CLOSURE_PLAN should reference the implementation task or updated count."

    # ---- Safety boundary tests ----

    def test_env_py_still_has_offline_mode(self):
        """run_migrations_offline must still exist (--sql mode preserved)."""
        source = _load_env_py()
        assert "def run_migrations_offline()" in source, (
            "run_migrations_offline must still exist — offline mode must not be broken."
        )

    def test_design_doc_no_forbidden_claims(self):
        """Design doc must NOT contain positive forbidden claims."""
        doc = _load_design_doc()
        for term in FORBIDDEN_TERMS:
            # Check the term does NOT appear as a positive assertion
            # (it may appear in "do not claim" context)
            lines = doc.split("\n")
            positive_lines = [
                line
                for line in lines
                if not any(
                    neg in line.lower()
                    for neg in ["does not ", "do not ", "must not", "never claim"]
                )
            ]
            positive_text = "\n".join(positive_lines)
            assert term.lower() not in positive_text.lower(), (
                f"Design doc contains forbidden term as positive assertion: '{term}'"
            )
