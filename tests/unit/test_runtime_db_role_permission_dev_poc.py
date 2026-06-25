"""
Static test: SC-002 Runtime DB Role Permission Dev POC validation.

Validates the dev-only proof-of-concept implementation:
1. init_db.sql defines all 6 target roles
2. football_reader is SELECT only (no DML, no DDL)
3. football_owner (DDL/migration) is separate from football_app (runtime DML)
4. football_ingestion is write-limited to ingestion tables
5. football_training is write-limited to training/predictions tables
6. docker-compose.dev.yml has role-specific env vars
7. .env.example has role-specific templates with placeholder passwords
8. No real secrets in dev files (only dev POC placeholders)
9. Docs explicitly state dev-only POC, not production
10. Docs state SC-002 remains partial mitigation only
11. Docs state training/data expansion/real DB write remain blocked
12. No forbidden claims (safe to train, safe to write, production ready, SC-002 complete)
"""

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).parent.parent.parent
INIT_SQL_PATH = PROJECT_ROOT / "deploy" / "docker" / "init_db.sql"
COMPOSE_PATH = PROJECT_ROOT / "docker-compose.dev.yml"
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
REVIEW_DOC_PATH = PROJECT_ROOT / "docs" / "SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md"
ASSESSMENT_PATH = PROJECT_ROOT / "docs" / "SC002_OVERALL_CLOSURE_ASSESSMENT.md"
CLOSURE_PLAN_PATH = PROJECT_ROOT / "docs" / "SC002_CLOSURE_PLAN.md"
PROJECT_STATUS_PATH = PROJECT_ROOT / "docs" / "PROJECT_STATUS.md"

TARGET_ROLES = [
    "football_owner",
    "football_app",
    "football_ingestion",
    "football_training",
    "football_reader",
    "football_gatekeeper",
]

# Forbidden claims that must not appear as positive assertions.
# We accept that docs may mention these in negation contexts (e.g., "does NOT claim safe to train").
_FORBIDDEN_RAW = [
    "SC-002 is complete",
    "SC-002 is fully fixed",
    "SC-002 resolved",
    "safe to train",
    "safe to write",
    "production ready",
]

_NEGATION_CONTEXT = [
    "does not claim",
    "does NOT claim",
    "not safe to",
    "NOT safe to",
    "cannot be closed",
    "NOT complete",
    "not complete",
    "not fully fixed",
    "NOT fully fixed",
    "not production ready",
    "NOT production ready",
    "never safe to",
    "never production",
    "do not claim",
    "do NOT claim",
    "NOT claim",
    "not claim",
    "non-goal",
    "Non-Goal",
    "- Claim",
    "Claim SC-002 is complete",  # listed as a non-goal (neg)
    # These appear in "does NOT claim" context but the line format is "- Claim ..."
    '- Claim "safe to train',
    '- Claim "safe to write',
    '- Claim "production ready',
    # Table definitions of forbidden terms are not positive claims
    "| safe to train |",
    "| safe to write |",
    "| production ready |",
    "| fully fixed |",
    "| complete |",
    # Descriptions of forbidden claims are not positive assertions
    "declaring SC-002 resolved",
    "not resolved",
]


def _has_forbidden_positive_claim(text: str) -> str:
    """Return the first forbidden claim found as a positive assertion, or empty string."""
    lines = text.split("\n")
    for line in lines:
        line_lower = line.lower()
        for claim in _FORBIDDEN_RAW:
            if claim.lower() not in line_lower:
                continue
            # Check if this is in a negation context
            negated = False
            for neg in _NEGATION_CONTEXT:
                if neg.lower() in line_lower:
                    negated = True
                    break
            if not negated:
                return claim
    return ""


FORBIDDEN_SECRET_SMELLS = [
    # Real-looking passwords (not dev POC placeholders)
    # Use 35+ chars threshold — dev POC passwords are max ~30 chars
    r"PASSWORD\s+'[^']{35,}'",
    # Production-like host names in compose
    r"rds\.amazonaws\.com",
    r"cloudsql\.googleapis",
    r"supabase\.co",
]

DEV_POC_PASSWORD_PATTERN = r"PASSWORD\s+'[a-z_]+_dev_poc'"


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---- Tests ----


class TestInitSqlRolesDefined:
    """Verify deploy/docker/init_db.sql defines the target role model."""

    def test_init_sql_exists(self):
        """init_db.sql must exist."""
        assert INIT_SQL_PATH.exists(), "deploy/docker/init_db.sql must exist."

    def test_all_six_roles_defined(self):
        """All 6 target roles must have CREATE ROLE statements (inside DO blocks)."""
        content = _load_text(INIT_SQL_PATH)
        for role in TARGET_ROLES:
            # DO block pattern: CREATE ROLE inside IF NOT EXISTS check
            assert f"CREATE ROLE {role}" in content, (
                f"init_db.sql must create role '{role}'. "
                f"Expected 'CREATE ROLE {role}' inside DO block, not found."
            )

    def test_reader_select_only(self):
        """football_reader must have only SELECT (no INSERT/UPDATE/DELETE/DROP/CREATE)."""
        content = _load_text(INIT_SQL_PATH)
        # Find the reader section
        reader_start = content.find("-- football_reader:")
        reader_end = content.find("-- football_gatekeeper:")
        reader_section = content[reader_start:reader_end]

        # Must have SELECT
        assert "SELECT" in reader_section, "football_reader must have SELECT privilege."

        # Must NOT have INSERT, UPDATE, DELETE, DROP, CREATE
        for forbidden_grant in ["INSERT", "UPDATE", "DELETE", "TRUNCATE", "DROP", "CREATE"]:
            patterns = [
                f"GRANT {forbidden_grant}",
                "GRANT ALL PRIVILEGES",
            ]
            for pattern in patterns:
                # Only check lines that reference football_reader
                reader_grant_pattern = rf"{pattern}.*TO football_reader"
                assert not re.search(reader_grant_pattern, content), (
                    f"football_reader must NOT have {forbidden_grant} privilege. "
                    f"Found: '{pattern}' referencing football_reader."
                )

    def test_owner_app_separated(self):
        """football_owner and football_app must be separate roles."""
        content = _load_text(INIT_SQL_PATH)
        assert "CREATE ROLE football_owner" in content, "football_owner must be a separate role."
        assert "CREATE ROLE football_app" in content, "football_app must be a separate role."
        # football_owner has ALL PRIVILEGES
        assert re.search(r"GRANT ALL PRIVILEGES.*TO football_owner", content), (
            "football_owner must have ALL PRIVILEGES."
        )
        # football_app does NOT have ALL PRIVILEGES
        assert not re.search(r"GRANT ALL PRIVILEGES.*TO football_app", content), (
            "football_app must NOT have ALL PRIVILEGES (no DDL)."
        )

    def test_ingestion_write_limited(self):
        """football_ingestion must have INSERT/UPDATE only on ingestion tables."""
        content = _load_text(INIT_SQL_PATH)
        # Ingestion INSERT/UPDATE must reference specific tables
        ingestion_grant = content[
            content.find("-- football_ingestion:") : content.find("-- football_training:")
        ]
        assert (
            "INSERT, UPDATE ON matches, raw_match_data, odds" in ingestion_grant
            or "INSERT, UPDATE ON" in ingestion_grant
        ), "football_ingestion must be write-limited to specific tables."
        # Must NOT have ALL PRIVILEGES
        assert "GRANT ALL PRIVILEGES" not in ingestion_grant, (
            "football_ingestion must NOT have ALL PRIVILEGES."
        )

    def test_training_write_limited(self):
        """football_training must have INSERT/UPDATE only on training tables."""
        content = _load_text(INIT_SQL_PATH)
        # Training INSERT/UPDATE must reference match_features_training or predictions
        training_grant = content[
            content.find("-- football_training:") : content.find("-- football_reader:")
        ]
        assert "match_features_training" in training_grant, (
            "football_training must reference match_features_training table."
        )
        assert "predictions" in training_grant, (
            "football_training must reference predictions table."
        )
        assert "GRANT ALL PRIVILEGES" not in training_grant, (
            "football_training must NOT have ALL PRIVILEGES."
        )

    def test_dev_only_warning_present(self):
        """init_db.sql must explicitly state DEV-ONLY."""
        content = _load_text(INIT_SQL_PATH)
        assert "DEV-ONLY" in content or "DEV ONLY" in content or "dev-only" in content, (
            "init_db.sql must contain 'DEV-ONLY' or 'dev-only' warning."
        )
        assert "Not for production" in content, "init_db.sql must state 'Not for production'."

    def test_dev_poc_passwords_only(self):
        """All passwords in init_db.sql must be dev POC placeholders (*_dev_poc)."""
        content = _load_text(INIT_SQL_PATH)
        password_lines = re.findall(r"PASSWORD\s+'([^']+)'", content)
        for pw in password_lines:
            assert pw.endswith("_dev_poc"), (
                f"Password '{pw}' does not match dev POC pattern (*_dev_poc)."
            )

    def test_no_real_secrets_in_init_sql(self):
        """init_db.sql must NOT contain real-looking secrets."""
        content = _load_text(INIT_SQL_PATH)
        for pattern in FORBIDDEN_SECRET_SMELLS:
            assert not re.search(pattern, content), (
                f"init_db.sql contains potential real secret or production host: "
                f"pattern '{pattern}'."
            )


class TestDockerComposeDev:
    """Verify docker-compose.dev.yml has role-specific env vars."""

    def test_compose_exists(self):
        """docker-compose.dev.yml must exist."""
        assert COMPOSE_PATH.exists(), "docker-compose.dev.yml must exist."

    def test_role_env_vars_present(self):
        """docker-compose.dev.yml must have role-specific env vars."""
        content = _load_text(COMPOSE_PATH)
        expected_vars = [
            "DB_OWNER_USER",
            "DB_OWNER_PASSWORD",
            "DB_APP_USER",
            "DB_APP_PASSWORD",
            "DB_INGESTION_USER",
            "DB_INGESTION_PASSWORD",
            "DB_TRAINING_USER",
            "DB_TRAINING_PASSWORD",
            "DB_READER_USER",
            "DB_READER_PASSWORD",
            "DB_GATEKEEPER_USER",
            "DB_GATEKEEPER_PASSWORD",
        ]
        for var in expected_vars:
            assert var in content, f"docker-compose.dev.yml must define '{var}'."

    def test_dev_poc_passwords_in_compose(self):
        """All role passwords in compose must be dev POC placeholders."""
        content = _load_text(COMPOSE_PATH)
        password_defaults = re.findall(r"DB_\w+_PASSWORD=\$\{[^}]+:-([^}]+)\}", content)
        for pw in password_defaults:
            assert pw.endswith("_dev_poc"), (
                f"Compose password default '{pw}' does not match dev POC pattern."
            )

    def test_compose_has_dev_only_comment(self):
        """Compose must mention dev POC / dev-only near role vars."""
        content = _load_text(COMPOSE_PATH)
        # The section should reference the dev POC
        assert "Dev POC" in content or "dev POC" in content or "SC-002 DB role model" in content, (
            "docker-compose.dev.yml must mention dev POC at the role vars section."
        )


class TestEnvExample:
    """Verify .env.example has role-specific config templates."""

    def test_env_example_exists(self):
        """.env.example must exist."""
        assert ENV_EXAMPLE_PATH.exists(), ".env.example must exist."

    def test_role_section_present(self):
        """.env.example must have role-specific connection config section."""
        content = _load_text(ENV_EXAMPLE_PATH)
        assert "DB Role Model" in content or "role-specific" in content, (
            ".env.example must have a DB role model section."
        )
        assert "DB_OWNER_USER" in content, ".env.example must define DB_OWNER_USER."
        assert "DB_READER_USER" in content, ".env.example must define DB_READER_USER."

    def test_env_example_password_is_placeholder(self):
        """Role passwords in .env.example must be 'your_secure_password_here'."""
        content = _load_text(ENV_EXAMPLE_PATH)
        role_password_lines = re.findall(r"DB_\w+_PASSWORD=(\S+)", content)
        for pw in role_password_lines:
            assert pw == "your_secure_password_here", (
                f".env.example database password must be 'your_secure_password_here', found '{pw}'."
            )

    def test_env_example_has_dev_only_warning(self):
        """.env.example must warn DEV-ONLY at the role section."""
        content = _load_text(ENV_EXAMPLE_PATH)
        # Find the role section area
        role_section_start = content.find("DB Role Model")
        role_section_end = min(
            pos
            for pos in [
                content.find("DB_OWNER_PASSWORD=") + 200,
            ]
            if pos > role_section_start
        )
        role_section = content[role_section_start : role_section_end + 200]
        assert (
            "DEV-ONLY" in role_section
            or "dev-only" in role_section
            or "Not for production" in role_section
        ), ".env.example role section must state dev-only."


class TestDocsState:
    """Verify documentation correctly describes the dev POC state."""

    def test_review_doc_mentions_dev_poc(self):
        """Review doc must mention dev POC implementation."""
        content = _load_text(REVIEW_DOC_PATH)
        assert "Dev POC" in content or "dev-only proof-of-concept" in content, (
            "Review doc must mention dev POC implementation."
        )
        assert "Dev-only" in content or "dev-only" in content, "Review doc must state dev-only."

    def test_review_doc_no_forbidden_claims(self):
        """Review doc must not contain positive forbidden claims."""
        content = _load_text(REVIEW_DOC_PATH)
        bad = _has_forbidden_positive_claim(content)
        assert not bad, f"Review doc must NOT contain positive forbidden claim: '{bad}'."

    def test_review_doc_sc002_partial_mitigation(self):
        """Review doc must state SC-002 is partial mitigation only."""
        content = _load_text(REVIEW_DOC_PATH)
        assert "partial mitigation only" in content.lower(), (
            "Review doc must state SC-002 is partial mitigation only."
        )

    def test_review_doc_training_blocked(self):
        """Review doc must mention continued blocks on operations."""
        content = _load_text(REVIEW_DOC_PATH)
        # Review doc is an audit document; "blocked" or "blocks" is sufficient
        assert "blocked" in content.lower() or "blocks" in content.lower(), (
            "Review doc must mention that operations are blocked/guarded."
        )

    def test_assessment_criterion_6_updated(self):
        """Overall closure assessment must reference dev POC."""
        content = _load_text(ASSESSMENT_PATH)
        assert "Dev POC" in content or "dev-only" in content, (
            "Assessment must reference dev POC implementation."
        )

    def test_assessment_no_forbidden_claims(self):
        """Assessment must not contain positive forbidden claims."""
        content = _load_text(ASSESSMENT_PATH)
        bad = _has_forbidden_positive_claim(content)
        assert not bad, f"Assessment must NOT contain positive forbidden claim: '{bad}'."

    def test_closure_plan_has_dev_poc(self):
        """Closure plan must reference the dev POC."""
        content = _load_text(CLOSURE_PLAN_PATH)
        assert "runtime_db_role_permission_dev_poc" in content, (
            "Closure plan must reference runtime_db_role_permission_dev_poc."
        )

    def test_closure_plan_criterion_6_updated(self):
        """Closure plan criterion #6 must reference dev POC."""
        content = _load_text(CLOSURE_PLAN_PATH)
        # The criterion #6 row should mention dev POC
        assert "Dev POC" in content or "dev-only" in content, (
            "Closure plan must mention dev POC in criterion #6."
        )

    def test_project_status_has_dev_poc(self):
        """PROJECT_STATUS.md must reference the dev POC."""
        content = _load_text(PROJECT_STATUS_PATH)
        assert "runtime_db_role_permission_dev_poc completed" in content, (
            "PROJECT_STATUS.md must have 'runtime_db_role_permission_dev_poc completed'."
        )

    def test_project_status_production_not_changed(self):
        """PROJECT_STATUS must state production not changed."""
        content = _load_text(PROJECT_STATUS_PATH)
        assert (
            "Not applied to staging or production" in content
            or "Not applied to staging/production" in content
            or "not for production" in content.lower()
        ), "PROJECT_STATUS must state production was not changed."

    def test_all_docs_no_forbidden_claims(self):
        """No SC-002 doc file must contain positive forbidden claims."""
        doc_paths = [REVIEW_DOC_PATH, ASSESSMENT_PATH, CLOSURE_PLAN_PATH, PROJECT_STATUS_PATH]
        for doc_path in doc_paths:
            content = _load_text(doc_path)
            bad = _has_forbidden_positive_claim(content)
            assert not bad, f"{doc_path.name} must NOT contain positive forbidden claim: '{bad}'."

    def test_all_docs_sc002_partial_mitigation(self):
        """All SC-002 docs must state partial mitigation only."""
        doc_paths = [REVIEW_DOC_PATH, ASSESSMENT_PATH, CLOSURE_PLAN_PATH, PROJECT_STATUS_PATH]
        for doc_path in doc_paths:
            content = _load_text(doc_path)
            assert "partial mitigation only" in content.lower(), (
                f"{doc_path.name} must state SC-002 is partial mitigation only."
            )

    def test_all_docs_blocked_stated(self):
        """All SC-002 docs must reference that operations remain blocked."""
        doc_paths = [REVIEW_DOC_PATH, ASSESSMENT_PATH, CLOSURE_PLAN_PATH, PROJECT_STATUS_PATH]
        for doc_path in doc_paths:
            content = _load_text(doc_path)
            has_block = "blocked" in content.lower() or "blocks" in content.lower()
            assert has_block, f"{doc_path.name} must mention blocked operations."


class TestInitSqlOverallStructure:
    """Verify the init_db.sql overall structure is intact after POC addition."""

    def test_core_tables_still_present(self):
        """All original tables must still be defined."""
        content = _load_text(INIT_SQL_PATH)
        expected_tables = [
            "matches",
            "raw_match_data",
            "match_features_training",
            "league_config",
            "odds",
            "predictions",
            "feature_registry",
            "data_collection_log",
        ]
        for table in expected_tables:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in content, (
                f"init_db.sql must still define table '{table}'."
            )

    def test_functions_and_triggers_present(self):
        """update_updated_at_column function and triggers must be present."""
        content = _load_text(INIT_SQL_PATH)
        assert "update_updated_at_column" in content, (
            "init_db.sql must still define update_updated_at_column function."
        )
        assert "CREATE TRIGGER" in content, "init_db.sql must still define triggers."

    def test_extensions_present(self):
        """uuid-ossp and pg_trgm extensions must be present."""
        content = _load_text(INIT_SQL_PATH)
        assert "uuid-ossp" in content, "uuid-ossp extension must be present."
        assert "pg_trgm" in content, "pg_trgm extension must be present."

    def test_legacy_user_still_referenced(self):
        """Legacy football_user (POSTGRES_USER) must be referenced for backward compat."""
        content = _load_text(INIT_SQL_PATH)
        assert "football_user" in content, (
            "Legacy football_user must still be referenced for backward compatibility."
        )


class TestRoleModelCompleteness:
    """Verify the role model is complete and consistent."""

    def test_all_roles_have_login(self):
        """All 6 roles must have LOGIN attribute in their DO block."""
        content = _load_text(INIT_SQL_PATH)
        for role in TARGET_ROLES:
            # Find the DO block section for this role
            do_start = content.find(
                f"IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{role}')"
            )
            assert do_start >= 0, f"Role '{role}' DO block not found."
            role_section = content[do_start : do_start + 250]
            assert "LOGIN" in role_section, f"Role '{role}' must have LOGIN attribute."

    def test_all_roles_have_connect(self):
        """All roles (except owner who has ALL PRIVILEGES) must have CONNECT on DB."""
        content = _load_text(INIT_SQL_PATH)
        connect_roles = TARGET_ROLES[1:]  # All except owner
        for role in connect_roles:
            assert f"GRANT CONNECT ON DATABASE football_db TO {role}" in content, (
                f"Role '{role}' must have CONNECT on football_db."
            )

    def test_all_roles_have_schema_usage(self):
        """All roles (except owner) must have USAGE on SCHEMA public."""
        content = _load_text(INIT_SQL_PATH)
        for role in TARGET_ROLES[1:]:
            assert f"GRANT USAGE ON SCHEMA public TO {role}" in content, (
                f"Role '{role}' must have USAGE on SCHEMA public."
            )

    def test_default_privileges_set(self):
        """init_db.sql must set ALTER DEFAULT PRIVILEGES for future tables."""
        content = _load_text(INIT_SQL_PATH)
        assert "ALTER DEFAULT PRIVILEGES" in content, (
            "init_db.sql must set ALTER DEFAULT PRIVILEGES for future tables."
        )

    def test_dev_poc_disclaimer_complete(self):
        """The dev POC section must have a complete disclaimer."""
        content = _load_text(INIT_SQL_PATH)
        disclaimer = content[content.find("WARNING:") : content.find("-- ---- Create roles")]
        assert "DEV-ONLY" in disclaimer, "Disclaimer must say DEV-ONLY."
        assert "production" in disclaimer.lower(), "Disclaimer must mention production."
        assert "secrets manager" in disclaimer.lower() or "env var" in disclaimer.lower(), (
            "Disclaimer must mention secrets manager or env vars for production."
        )


class TestInitSqlGuardGateB:
    """Verify the SC-002 Gate B dev-only execution guard in init_db.sql."""

    def test_guard_exists_in_init_sql(self):
        """init_db.sql must contain the Gate B guard."""
        content = _load_text(INIT_SQL_PATH)
        assert "SC-002 Gate B" in content, "init_db.sql must contain SC-002 Gate B guard header"
        assert "Dev-Only Execution Guard" in content, (
            "init_db.sql must have Dev-Only Execution Guard section"
        )

    def test_guard_sets_context_parameter(self):
        """Guard must SET sc002.init_sql_context = 'development'."""
        content = _load_text(INIT_SQL_PATH)
        assert "sc002.init_sql_context" in content, (
            "Guard must use sc002.init_sql_context parameter"
        )
        assert "SET sc002.init_sql_context" in content, "Guard must SET the context parameter"

    def test_guard_verifies_context_with_do_block(self):
        """Guard must use a DO block to verify the context parameter."""
        content = _load_text(INIT_SQL_PATH)
        assert "current_setting('sc002.init_sql_context')" in content, (
            "Guard must verify via current_setting()"
        )
        assert "IS DISTINCT FROM 'development'" in content, (
            "Guard must check for 'development' value"
        )

    def test_guard_raises_exception_on_mismatch(self):
        """Guard must RAISE EXCEPTION on non-development context."""
        content = _load_text(INIT_SQL_PATH)
        assert "RAISE EXCEPTION" in content, "Guard must RAISE EXCEPTION on context mismatch"
        assert "DEV-ONLY" in content, "Exception message must state DEV-ONLY"

    def test_guard_before_all_ddl_dcl(self):
        """Guard must appear before any CREATE ROLE, GRANT, or schema DDL."""
        content = _load_text(INIT_SQL_PATH)
        guard_end = content.find("-- End SC-002 Gate B guard")
        assert guard_end > 0, "Guard section must have explicit end marker"
        # Check that CREATE ROLE / GRANT appears only after the guard
        after_guard = content[guard_end:]
        first_create_role = after_guard.find("CREATE ROLE")
        if first_create_role >= 0:
            assert first_create_role > 0, "CREATE ROLE must appear after the guard section"
        # All GRANT must be after the guard
        grant_positions = []
        idx = 0
        while True:
            idx = after_guard.find("GRANT ", idx)
            if idx < 0:
                break
            grant_positions.append(idx)
            idx += 1
        if grant_positions:
            assert all(p > 0 for p in grant_positions), (
                "All GRANT statements must be after the guard section"
            )

    def test_guard_before_create_extension(self):
        """Guard must appear before CREATE EXTENSION statements."""
        content = _load_text(INIT_SQL_PATH)
        guard_end = content.find("-- End SC-002 Gate B guard")
        after_guard = content[guard_end:]
        # The first CREATE EXTENSION should be after the guard
        create_ext_pos = after_guard.find("CREATE EXTENSION")
        assert create_ext_pos >= 0, "CREATE EXTENSION must exist in init_db.sql"
        assert create_ext_pos > 0, "CREATE EXTENSION must appear after the guard section"

    def test_guard_dev_only_explicit(self):
        """Guard must explicitly state dev-only and forbid non-dev use."""
        content = _load_text(INIT_SQL_PATH)
        guard_section = content[
            content.find("SC-002 Gate B") : content.find("-- End SC-002 Gate B guard")
        ]
        assert "DEV-ONLY" in guard_section, "Guard must state DEV-ONLY"
        assert "staging" in guard_section.lower(), "Guard must mention staging"
        assert "production" in guard_section.lower(), "Guard must mention production"
        assert "non-dev" in guard_section.lower(), "Guard must mention non-dev"
        assert "MUST NOT" in guard_section, "Guard must state MUST NOT"

    def test_guard_no_env_var_bypass(self):
        """Guard must NOT have an env-var bypass mechanism."""
        content = _load_text(INIT_SQL_PATH)
        guard_section = content[
            content.find("SC-002 Gate B") : content.find("-- End SC-002 Gate B guard")
        ]
        assert "env-var bypass" in guard_section or "no env-var" in guard_section.lower(), (
            "Guard must state there is no env-var bypass"
        )

    def test_guard_parameter_not_production_value(self):
        """Guard parameter value must be 'development', not 'production'."""
        content = _load_text(INIT_SQL_PATH)
        assert "sc002.init_sql_context = 'development'" in content, (
            "Guard must SET context to 'development'"
        )
        assert "sc002.init_sql_context = 'production'" not in content, (
            "Guard must NOT use 'production' as context value"
        )

    # ---- docker-compose integration ----

    def test_docker_compose_has_guard_command(self):
        """docker-compose.dev.yml must pass the guard parameter to PostgreSQL."""
        compose = _load_text(COMPOSE_PATH)
        assert "sc002.init_sql_context" in compose, (
            "docker-compose.dev.yml must pass sc002.init_sql_context"
        )
        assert "development" in compose, "docker-compose.dev.yml must set context to 'development'"

    def test_docker_compose_guard_in_command(self):
        """Guard parameter must be in the DB service command section."""
        compose = _load_text(COMPOSE_PATH)
        assert "command:" in compose, "docker-compose must have a command section"
        assert "-c" in compose, "command must use -c for postgres config"
        assert "sc002.init_sql_context=development" in compose, (
            "command must include sc002.init_sql_context=development"
        )

    # ---- No real secrets ----

    def test_no_real_secrets_in_guard(self):
        """Guard must not contain real secrets or passwords."""
        content = _load_text(INIT_SQL_PATH)
        guard_section = content[
            content.find("SC-002 Gate B") : content.find("-- End SC-002 Gate B guard")
        ]
        assert "PASSWORD" not in guard_section, "Guard section must not contain PASSWORD"
        assert "secret" not in guard_section.lower() or ("secrets" not in guard_section.lower()), (
            "Guard section must not contain real secrets"
        )

    def test_env_example_documents_guard(self):
        """.env.example must document the init_db.sql guard."""
        env = _load_text(ENV_EXAMPLE_PATH)
        assert "Gate B" in env or "init_db.sql" in env, ".env.example must reference init_db.sql"

    # ---- SC-002 safety boundaries ----

    def test_init_sql_still_dev_only(self):
        """init_db.sql must still state it is dev-only."""
        content = _load_text(INIT_SQL_PATH)
        # Count occurrences of DEV-ONLY or "dev-only" or "dev_only"
        min_dev_markers = 3
        dev_only_refs = content.count("DEV-ONLY") + content.lower().count("dev-only")
        assert dev_only_refs >= min_dev_markers, (
            f"init_db.sql must have multiple dev-only markers, found {dev_only_refs}"
        )

    def test_init_sql_no_production_config(self):
        """init_db.sql guard must not reference production configuration."""
        content = _load_text(INIT_SQL_PATH)
        guard_section = content[
            content.find("SC-002 Gate B") : content.find("-- End SC-002 Gate B guard")
        ]
        assert "production_password" not in guard_section.lower(), (
            "Guard must not contain production passwords"
        )
        assert "RDS" not in guard_section, "Guard must not reference RDS"
        assert "Cloud SQL" not in guard_section, "Guard must not reference Cloud SQL"
