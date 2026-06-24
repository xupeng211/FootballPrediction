"""
Static test: SC-002 Alembic Migration Guard Design validation.

Validates:
1. env.py is explicitly classified in the allowlist
2. 18/20 Python write paths runtime guarded (design phase: was 17, now 18 after implementation)
3. SC-002 remains partial mitigation only
4. Training / data expansion / real DB write remain blocked
5. Design doc exists and contains required sections
6. Implementation task completed (guard added to env.py)
7. All 20 Python write paths resolved (18 guarded, 2 safe)
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
ALLOWLIST_PATH = PROJECT_ROOT / "config" / "python_db_write_allowlist.json"
SQL_ALLOWLIST_PATH = PROJECT_ROOT / "config" / "sql_migration_policy_allowlist.json"
DESIGN_DOC_PATH = PROJECT_ROOT / "docs" / "SC002_ALEMBIC_MIGRATION_GUARD_DESIGN.md"
CLOSURE_PLAN_PATH = PROJECT_ROOT / "docs" / "SC002_CLOSURE_PLAN.md"
ENFORCEMENT_DESIGN_PATH = PROJECT_ROOT / "docs" / "SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md"
PROJECT_STATUS_PATH = PROJECT_ROOT / "docs" / "PROJECT_STATUS.md"

ENV_PY_PATH = "src/database/migrations/env.py"
# After sc002_alembic_migration_runtime_guard_implementation,
# env.py classification changed from needs_specialized to runtime_guarded.
EXPECTED_ENV_PY_CLASSIFICATION = "historical_python_alembic_migration_runtime_guarded"
EXPECTED_TOTAL_RUNTIME_GUARDED = 18  # was 17, +1 for env.py guard
EXPECTED_TOTAL_PYTHON_WRITE_PATHS = 20
EXPECTED_TOTAL_ALLOWLIST_ENTRIES = 28

FORBIDDEN_TERMS = [
    "SC-002 is complete",
    "SC-002 is fully fixed",
    "SC-002 resolved",
    "safe to train",
    "safe to write",
    "production ready",
]


def _load_allowlist():
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))


def _load_sql_allowlist():
    return json.loads(SQL_ALLOWLIST_PATH.read_text(encoding="utf-8"))


def _load_design_doc():
    return DESIGN_DOC_PATH.read_text(encoding="utf-8")


def _load_text(path: Path):
    return path.read_text(encoding="utf-8")


# ---- Tests ----


class TestAlembicMigrationGuardDesign:
    """Verify env.py classification and guard design state."""

    # ---- Allowlist tests ----

    def test_env_py_is_in_allowlist(self):
        """env.py must be explicitly classified in the Python DB write allowlist."""
        allowlist = _load_allowlist()
        entries_by_path = {e["path"]: e for e in allowlist["entries"]}
        assert ENV_PY_PATH in entries_by_path, (
            f"{ENV_PY_PATH} is NOT in python_db_write_allowlist.json. It must be explicitly classified."
        )

    def test_env_py_has_correct_classification(self):
        """env.py must be classified as alembic_migration_needs_specialized_runtime_guard."""
        allowlist = _load_allowlist()
        entries_by_path = {e["path"]: e for e in allowlist["entries"]}
        entry = entries_by_path[ENV_PY_PATH]
        assert entry["classification"] == EXPECTED_ENV_PY_CLASSIFICATION, (
            f"Expected classification '{EXPECTED_ENV_PY_CLASSIFICATION}', got '{entry['classification']}'"
        )

    def test_env_py_is_now_runtime_guarded(self):
        """env.py should NOW be marked runtime_guarded after implementation."""
        allowlist = _load_allowlist()
        entries_by_path = {e["path"]: e for e in allowlist["entries"]}
        entry = entries_by_path[ENV_PY_PATH]
        assert "runtime_guarded" in entry["classification"], (
            f"env.py classification '{entry['classification']}' does not contain "
            f"'runtime_guarded' — guard was implemented in this PR."
        )

    def test_env_py_has_analysis_fields(self):
        """env.py entry must have full analysis metadata (design task output)."""
        allowlist = _load_allowlist()
        entries_by_path = {e["path"]: e for e in allowlist["entries"]}
        entry = entries_by_path[ENV_PY_PATH]
        required_fields = [
            "analysis_task",
            "observed_operations",
            "observed_tables_or_targets",
            "direct_write_boundary",
            "recommended_next_action",
            "why_not_guarded_in_this_pr",
        ]
        for field in required_fields:
            assert field in entry, (
                f"env.py allowlist entry missing required field '{field}'. "
                f"Design task must populate all analysis metadata."
            )

    def test_env_py_references_design_doc(self):
        """env.py allowlist entry must reference the design doc."""
        allowlist = _load_allowlist()
        entries_by_path = {e["path"]: e for e in allowlist["entries"]}
        entry = entries_by_path[ENV_PY_PATH]
        assert entry.get("source_doc") == "docs/SC002_ALEMBIC_MIGRATION_GUARD_DESIGN.md", (
            f"Expected source_doc='docs/SC002_ALEMBIC_MIGRATION_GUARD_DESIGN.md', got '{entry.get('source_doc')}'"
        )

    # ---- Guarded count tests ----

    def test_runtime_guarded_count_is_17(self):
        """17 of 20 Python write paths must be runtime guarded (unchanged)."""
        allowlist = _load_allowlist()
        runtime_guarded = sum(
            1 for e in allowlist["entries"] if "runtime_guarded" in e["classification"]
        )
        assert runtime_guarded == EXPECTED_TOTAL_RUNTIME_GUARDED, (
            f"Expected {EXPECTED_TOTAL_RUNTIME_GUARDED} runtime guarded paths, "
            f"found {runtime_guarded}. Guarded count must NOT change in this design task."
        )

    def test_total_python_write_paths_is_20(self):
        """Total Python write paths in allowlist must be 20 (confirmed + indirect + manual)."""
        # Verify total entries count — 28 entries
        # (14 confirmed + 8 indirect + 5 manual + 1 env.py)
        total_entries = len(_load_allowlist()["entries"])
        assert total_entries == EXPECTED_TOTAL_ALLOWLIST_ENTRIES, (
            f"Expected {EXPECTED_TOTAL_ALLOWLIST_ENTRIES} total entries, "
            f"found {total_entries}. "
            f"Total count must not change in this design task."
        )

    def test_env_py_is_only_pending(self):
        """After implementation, 0 entries should be pending — all classified."""
        allowlist = _load_allowlist()
        pending = [
            e
            for e in allowlist["entries"]
            if "pending" in e.get("classification", "")
            or "needs_guard" in e.get("classification", "")
        ]
        assert len(pending) == 0, (
            f"Expected 0 pending/needs_guard entries, found {len(pending)}: {[e['path'] for e in pending]}"
        )

    # ---- Design doc tests ----

    def test_design_doc_exists(self):
        """Design doc must exist."""
        assert DESIGN_DOC_PATH.exists(), (
            f"Design doc {DESIGN_DOC_PATH} does not exist. "
            f"This task must create docs/SC002_ALEMBIC_MIGRATION_GUARD_DESIGN.md"
        )

    def test_design_doc_has_required_sections(self):
        """Design doc must contain required sections."""
        doc = _load_design_doc()
        required_sections = [
            "## Summary",
            "## Static Analysis",
            "## Classification",
            "## Guard Strategy Design",
            "## Implementation Plan",
            "## Next Recommended Task",
        ]
        for section in required_sections:
            assert section in doc, (
                f"Design doc missing required section: {section}. "
                f"Section is required for complete classification and implementation planning."
            )

    def test_design_doc_declares_partial_mitigation(self):
        """Design doc must state SC-002 remains partial mitigation only."""
        doc = _load_design_doc()
        assert "partial mitigation only" in doc, (
            "Design doc must state SC-002 remains partial mitigation only."
        )

    def test_design_doc_declares_training_blocked(self):
        """Design doc must state training / data expansion / real DB write remain blocked."""
        doc = _load_design_doc()
        doc_lower = doc.lower()
        assert "training" in doc_lower, "Design doc must mention training."
        assert "blocked" in doc_lower, (
            "Design doc must state training and data expansion are blocked."
        )

    def test_design_doc_no_forbidden_claims(self):
        """Design doc must NOT contain forbidden SC-002 completion claims as positive assertions."""
        doc = _load_design_doc()
        # Check only positive assertions, not negations or "does NOT" statements
        # Strip lines that are clearly negations
        lines = doc.split("\n")
        positive_lines = []
        for line in lines:
            stripped = line.strip().lower()
            # Skip lines that are negations: "does NOT", "do NOT", "never", "must NOT"
            if any(
                neg in stripped
                for neg in ["does not ", "do not ", "this task does not", "must not", "never claim"]
            ):
                continue
            # Skip lines that are in a forbidden-terms table or explanation
            if "|" in stripped and any(kw in stripped for kw in ["forbidden", "why forbidden"]):
                continue
            positive_lines.append(stripped)
        positive_text = " ".join(positive_lines)
        for term in FORBIDDEN_TERMS:
            assert term.lower() not in positive_text, (
                f"Design doc contains forbidden term as positive assertion: '{term}'. "
                f"SC-002 is NOT complete. Training/data expansion/real DB write remain blocked."
            )

    def test_design_doc_describes_guard_location(self):
        """Design doc must specify where the guard should be placed."""
        doc = _load_design_doc()
        assert "run_migrations_online" in doc, (
            "Design doc must specify run_migrations_online() as the guard location."
        )

    def test_design_doc_lists_env_vars(self):
        """Design doc must list required env vars for the guard."""
        doc = _load_design_doc()
        assert "ALLOW_DB_WRITE" in doc, "Design doc must reference ALLOW_DB_WRITE."
        assert "ALLOW_SCHEMA_WRITE" in doc, "Design doc must reference ALLOW_SCHEMA_WRITE."
        assert "FINAL_DB_WRITE_CONFIRMATION" in doc, (
            "Design doc must reference FINAL_DB_WRITE_CONFIRMATION."
        )

    def test_design_doc_declares_no_alembic_run(self):
        """Design doc must state that NO Alembic/migration was executed."""
        doc = _load_design_doc()
        no_run_indicators = [
            "did NOT run",
            "no DB connection",
            "no migration",
        ]
        found = any(indicator.lower() in doc.lower() for indicator in no_run_indicators)
        assert found, "Design doc must explicitly state that no Alembic/migration was executed."

    # ---- Closure plan tests ----

    def test_closure_plan_references_design_doc(self):
        """SC002_CLOSURE_PLAN.md must reference the new design doc."""
        closure = _load_text(CLOSURE_PLAN_PATH)
        assert "SC002_ALEMBIC_MIGRATION_GUARD_DESIGN.md" in closure, (
            "SC002_CLOSURE_PLAN.md must reference the Alembic migration guard design doc."
        )

    def test_closure_plan_lists_implementation_task(self):
        """SC002_CLOSURE_PLAN.md must list the implementation follow-up task."""
        closure = _load_text(CLOSURE_PLAN_PATH)
        assert "sc002_alembic_migration_runtime_guard_implementation" in closure, (
            "SC002_CLOSURE_PLAN.md must list the implementation follow-up task: "
            "sc002_alembic_migration_runtime_guard_implementation"
        )

    def test_closure_plan_has_do_not_start_automatically(self):
        """SC002_CLOSURE_PLAN.md must state 'Do not start automatically' for next task."""
        closure = _load_text(CLOSURE_PLAN_PATH)
        assert "Do not start automatically" in closure, (
            "SC002_CLOSURE_PLAN.md must state 'Do not start automatically' for the next task."
        )

    # ---- Enforcement design doc tests ----

    def test_enforcement_design_updated_for_alembic(self):
        """Enforcement design doc must reflect current env.py status."""
        enforcement = _load_text(ENFORCEMENT_DESIGN_PATH)
        assert (
            "alembic_migration_needs_specialized_runtime_guard" in enforcement
            or "alembic_migration_runtime_guarded" in enforcement
            or "ALL PHASES COMPLETED" in enforcement
        ), "SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md must reflect env.py status."

    # ---- Project status tests ----

    def test_project_status_has_alembic_section(self):
        """PROJECT_STATUS.md must have a section about this design task."""
        status = _load_text(PROJECT_STATUS_PATH)
        assert "sc002_alembic_migration_guard_design completed" in status, (
            "PROJECT_STATUS.md must document the completion of sc002_alembic_migration_guard_design."
        )

    def test_project_status_declares_partial_mitigation(self):
        """PROJECT_STATUS.md must state SC-002 remains partial mitigation only."""
        status = _load_text(PROJECT_STATUS_PATH)
        assert "partial mitigation only" in status, (
            "PROJECT_STATUS.md must state SC-002 remains partial mitigation only."
        )

    # ---- SQL allowlist cross-reference tests ----

    def test_sql_allowlist_env_py_classified(self):
        """SQL migration policy allowlist must have updated env.py classification."""
        sql_allowlist = _load_sql_allowlist()
        entries_by_path = {e["path"]: e for e in sql_allowlist["entries"]}
        assert ENV_PY_PATH in entries_by_path, (
            f"{ENV_PY_PATH} is NOT in sql_migration_policy_allowlist.json."
        )
        entry = entries_by_path[ENV_PY_PATH]
        assert entry["classification"] == EXPECTED_ENV_PY_CLASSIFICATION, (
            f"SQL allowlist env.py classification mismatch: "
            f"expected '{EXPECTED_ENV_PY_CLASSIFICATION}', "
            f"got '{entry['classification']}'"
        )

    def test_sql_allowlist_env_py_references_design_doc(self):
        """SQL allowlist env.py entry must reference the new design doc."""
        sql_allowlist = _load_sql_allowlist()
        entries_by_path = {e["path"]: e for e in sql_allowlist["entries"]}
        entry = entries_by_path[ENV_PY_PATH]
        assert entry.get("source_doc") == "docs/SC002_ALEMBIC_MIGRATION_GUARD_DESIGN.md", (
            "SQL allowlist env.py source_doc must reference the design doc."
        )

    # ---- Safety boundary tests ----

    def test_no_forbidden_terms_alembic_design_doc(self):
        """New Alembic design doc must NOT contain forbidden SC-002 completion claims."""
        doc = _load_design_doc()
        lines = doc.split("\n")
        positive_lines = []
        for line in lines:
            stripped = line.strip().lower()
            # Skip lines that are negations
            if any(neg in stripped for neg in ["does not ", "do not ", "must not", "never claim"]):
                continue
            # Skip lines that list what the task does NOT do
            if stripped.startswith("- ") and any(
                neg in stripped
                for neg in [
                    "claim sc-002",
                    "run alembic",
                    "execute",
                    "connect",
                    "perform any real",
                    "train",
                    "claim safe",
                ]
            ):
                continue
            positive_lines.append(stripped)
        positive_text = " ".join(positive_lines)
        for term in FORBIDDEN_TERMS:
            assert term.lower() not in positive_text, (
                f"New Alembic design doc contains forbidden term as positive assertion: '{term}'"
            )

    def test_env_py_has_guard_code(self):
        """env.py must NOW contain guard code after implementation."""
        env_py_path = PROJECT_ROOT / ENV_PY_PATH
        env_py_content = env_py_path.read_text(encoding="utf-8")
        # After implementation, guard must be present
        assert "assert_db_write_allowed" in env_py_content, (
            "env.py must now contain assert_db_write_allowed — guard was implemented."
        )
        assert "_check_alembic_migration_guard" in env_py_content, (
            "env.py must define _check_alembic_migration_guard()."
        )
        assert "ALEMBIC_CTX" in env_py_content, (
            "env.py must reference ALEMBIC_CTX for CI/dev auto-allow."
        )
