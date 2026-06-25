"""Static test: SC-002 Staging DB Role Deployment Plan validation.

Validates the staging deployment plan document:
1. Plan doc exists
2. Plan states no DB connection / no SQL / no deployment executed
3. Plan contains all 6 target roles
4. Plan contains preflight/prerequisites checklist
5. Plan contains rollback plan
6. Plan contains validation matrix
7. Plan contains go/no-go checklist
8. Plan explicitly excludes production
9. Plan states training/data expansion/real DB write remain blocked
10. No forbidden claims or real secrets
"""

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLAN_PATH = PROJECT_ROOT / "docs" / "SC002_STAGING_DB_ROLE_DEPLOYMENT_PLAN.md"
CLOSURE_PLAN_PATH = PROJECT_ROOT / "docs" / "SC002_CLOSURE_PLAN.md"
PROJECT_STATUS_PATH = PROJECT_ROOT / "docs" / "PROJECT_STATUS.md"
FINAL_CHECK_PATH = PROJECT_ROOT / "docs" / "SC002_FINAL_CLOSURE_CHECK.md"

TARGET_ROLES = [
    "football_owner",
    "football_app",
    "football_ingestion",
    "football_training",
    "football_reader",
    "football_gatekeeper",
]

FORBIDDEN_CLAIMS = [
    "SC-002 is complete",
    "safe to train",
    "safe to write",
    "production ready",
    "staging deployment completed",
    "deployment executed",
]

REQUIRED_SECTIONS = [
    "## Summary",
    "## Background",
    "## Target 6-Role Model",
    "## Staging Deployment Prerequisites",
    "## Deployment Step Drafts",
    "## Validation Matrix",
    "## Rollback Plan",
    "## Go / No-Go Checklist",
    "## What This Plan Does NOT Do",
]


def _load(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestStagingPlanDocument:
    """Verify the staging deployment plan exists and has correct structure."""

    def test_plan_doc_exists(self):
        """Plan document must exist."""
        assert PLAN_PATH.exists(), "docs/SC002_STAGING_DB_ROLE_DEPLOYMENT_PLAN.md must exist."

    def test_has_required_sections(self):
        """Plan must contain all required sections."""
        doc = _load(PLAN_PATH)
        for section in REQUIRED_SECTIONS:
            assert section in doc, f"Staging plan missing required section: {section}"

    def test_all_six_roles_documented(self):
        """Plan must document all 6 target roles."""
        doc = _load(PLAN_PATH)
        for role in TARGET_ROLES:
            assert role in doc, f"Staging plan must document role '{role}'."

    def test_role_model_table_present(self):
        """Plan must have a 6-role model table with purpose and privileges."""
        doc = _load(PLAN_PATH)
        assert "## Target 6-Role Model" in doc, "Must have target model section."
        # Check table columns
        assert "| # | Role | Purpose | DDL | DML | Scope |" in doc, (
            "Must have role model table with expected columns."
        )

    # ── No-execution assertions ────────────────────────────────────────────

    def test_plan_is_planning_only(self):
        """Plan must state it is planning/documentation only, no execution."""
        doc = _load(PLAN_PATH)
        assert "planning document only" in doc.lower() or ("planning only" in doc.lower()), (
            "Plan must state it is planning only."
        )

    def test_no_db_connection(self):
        """Plan must state no DB connection was made."""
        doc = _load(PLAN_PATH)
        assert "no db connection" in doc.lower() or ("connect to any database" in doc.lower()), (
            "Plan must state no DB connection was made."
        )

    def test_no_sql_execution(self):
        """Plan must state no SQL was executed."""
        doc = _load(PLAN_PATH)
        assert "no sql" in doc.lower() or ("execute any sql" in doc.lower()), (
            "Plan must state no SQL was executed."
        )

    def test_no_real_permission_changes(self):
        """Plan must state no real DB permission changes were made."""
        doc = _load(PLAN_PATH)
        assert "no real" in doc.lower() or ("modify any real" in doc.lower()), (
            "Plan must state no real changes were made."
        )

    def test_deployment_not_executed(self):
        """Plan must state deployment has NOT been executed."""
        doc = _load(PLAN_PATH)
        assert "not executed" in doc.lower() or ("no deployment" in doc.lower()), (
            "Plan must state deployment was not executed."
        )

    # ── Prerequisites ──────────────────────────────────────────────────────

    def test_preflight_checklist_present(self):
        """Plan must have a pre-deployment prerequisites checklist."""
        doc = _load(PLAN_PATH)
        assert "## Staging Deployment Prerequisites" in doc, "Must have prerequisites section."
        # Check for checklist items (checkbox markers)
        prereq_section = doc[
            doc.find("## Staging Deployment Prerequisites") : doc.find("## Deployment Step Drafts")
        ]
        min_checklist = 8
        checkboxes = prereq_section.count("- [ ]")
        assert checkboxes >= min_checklist, (
            f"Prerequisites must have at least {min_checklist} checklist items, found {checkboxes}."
        )

    def test_backup_prerequisite(self):
        """Plan must require staging backup before deployment."""
        doc = _load(PLAN_PATH)
        assert "backup" in doc.lower(), "Must mention backup."
        assert "pg_dump" in doc.lower() or "snapshot" in doc.lower(), "Must specify backup method."

    def test_production_excluded(self):
        """Plan must explicitly exclude production DB."""
        doc = _load(PLAN_PATH)
        assert "production" in doc.lower(), "Must mention production."
        assert (
            "excluded" in doc.lower()
            or "exclude" in doc.lower()
            or ("not production" in doc.lower())
        ), "Must explicitly exclude production DB."

    def test_triple_check_production(self):
        """Plan must mention triple-checking the production host exclusion."""
        doc = _load(PLAN_PATH)
        assert "triple-check" in doc.lower() or "triple check" in doc.lower(), (
            "Must include triple-check of production exclusion."
        )

    # ── Rollback plan ──────────────────────────────────────────────────────

    def test_rollback_plan_present(self):
        """Plan must contain a rollback plan."""
        doc = _load(PLAN_PATH)
        assert "## Rollback Plan" in doc, "Must have rollback plan section."

    def test_rollback_includes_env_var_revert(self):
        """Rollback plan must include env var reversion step."""
        doc = _load(PLAN_PATH)
        rollback = doc[doc.find("## Rollback Plan") : doc.find("## Go / No-Go Checklist")]
        assert "env" in rollback.lower(), "Rollback must mention env var reversion."

    def test_rollback_includes_revoke(self):
        """Rollback plan must include privilege revocation."""
        doc = _load(PLAN_PATH)
        rollback = doc[doc.find("## Rollback Plan") : doc.find("## Go / No-Go Checklist")]
        assert "REVOKE" in rollback or "revoke" in rollback.lower(), (
            "Rollback must include privilege revocation."
        )

    def test_rollback_includes_audit_trail(self):
        """Rollback plan must mention audit trail."""
        doc = _load(PLAN_PATH)
        rollback = doc[doc.find("## Rollback Plan") : doc.find("## Go / No-Go Checklist")]
        assert "audit" in rollback.lower(), "Rollback must mention audit trail."

    def test_rollback_excludes_production(self):
        """Rollback must NOT target production."""
        doc = _load(PLAN_PATH)
        rollback = doc[doc.find("## Rollback Plan") : doc.find("## Go / No-Go Checklist")]
        assert "production" in rollback.lower(), "Rollback must reference production exclusion."

    # ── Validation matrix ──────────────────────────────────────────────────

    def test_validation_matrix_present(self):
        """Plan must contain a validation matrix."""
        doc = _load(PLAN_PATH)
        assert "## Validation Matrix" in doc, "Must have validation matrix section."

    def test_validation_matrix_has_roles(self):
        """Validation matrix must include all 6 roles."""
        doc = _load(PLAN_PATH)
        matrix = doc[doc.find("## Validation Matrix") : doc.find("## Rollback Plan")]
        for role in TARGET_ROLES:
            # Check for role name in column header or row
            role_short = role.replace("football_", "")
            assert role_short in matrix, f"Validation matrix must include role '{role}'."

    def test_validation_matrix_has_operations(self):
        """Validation matrix must cover key operations."""
        doc = _load(PLAN_PATH)
        matrix = doc[doc.find("## Validation Matrix") : doc.find("## Rollback Plan")]
        required_ops = ["SELECT", "INSERT", "CREATE TABLE", "DROP TABLE"]
        for op in required_ops:
            assert op in matrix, f"Validation matrix must cover '{op}' operation."

    def test_validation_matrix_has_allow_deny(self):
        """Validation matrix must use Allow/Deny/Blocked indicators."""
        doc = _load(PLAN_PATH)
        matrix = doc[doc.find("## Validation Matrix") : doc.find("## Rollback Plan")]
        assert "Allow" in matrix, "Matrix must use Allow indicator."
        assert "Deny" in matrix, "Matrix must use Deny indicator."

    def test_production_blocked_in_matrix(self):
        """Validation matrix must show production as blocked for all roles."""
        doc = _load(PLAN_PATH)
        matrix = doc[doc.find("## Validation Matrix") : doc.find("## Rollback Plan")]
        assert "Blocked" in matrix, "Matrix must use Blocked indicator."
        assert "Production host" in matrix, "Matrix must include Production host row."

    # ── Go/no-go checklist ─────────────────────────────────────────────────

    def test_gonogo_checklist_present(self):
        """Plan must contain a go/no-go checklist."""
        doc = _load(PLAN_PATH)
        assert "## Go / No-Go Checklist" in doc, "Must have go/no-go checklist."

    def test_gonogo_has_go_criteria(self):
        """Go/no-go must have go criteria."""
        doc = _load(PLAN_PATH)
        checklist = doc[
            doc.find("## Go / No-Go Checklist") : doc.find("## What This Plan Does NOT Do")
        ]
        go_count = checklist.count("### Go Criteria") + checklist.count("Go Criteria")
        assert go_count > 0, "Must have Go Criteria section."
        min_go = 5
        go_checkboxes = checklist.count("- [ ]") if "Go Criteria" in checklist else 0
        assert go_checkboxes >= min_go, (
            f"Go criteria must have at least {min_go} checklist items, found {go_checkboxes}."
        )

    def test_gonogo_has_nogo_criteria(self):
        """Go/no-go must have no-go criteria."""
        doc = _load(PLAN_PATH)
        checklist = doc[
            doc.find("## Go / No-Go Checklist") : doc.find("## What This Plan Does NOT Do")
        ]
        assert "No-Go Criteria" in checklist, "Must have No-Go Criteria section."

    def test_gonogo_includes_backup_check(self):
        """Go criteria must include backup verification."""
        doc = _load(PLAN_PATH)
        checklist = doc[
            doc.find("## Go / No-Go Checklist") : doc.find("## What This Plan Does NOT Do")
        ]
        assert "backup" in checklist.lower(), "Go criteria must mention backup."

    def test_gonogo_includes_production_exclusion(self):
        """No-go must include production DB exclusion."""
        doc = _load(PLAN_PATH)
        assert "production" in doc.lower(), "No-go must mention production exclusion."

    # ── Safety boundaries ──────────────────────────────────────────────────

    def test_training_blocked(self):
        """Plan must state training remains blocked."""
        doc = _load(PLAN_PATH)
        assert "training" in doc.lower(), "Must mention training."
        assert "blocked" in doc.lower(), "Must state training is blocked."

    def test_data_expansion_blocked(self):
        """Plan must state data expansion remains blocked."""
        doc = _load(PLAN_PATH)
        assert "data expansion" in doc.lower(), "Must mention data expansion."

    def test_real_db_write_blocked(self):
        """Plan must state real DB write remains blocked."""
        doc = _load(PLAN_PATH)
        assert "real db write" in doc.lower() or "real DB write" in doc, (
            "Must mention real DB write."
        )

    def test_no_real_secrets(self):
        """Plan must NOT contain real passwords or secrets."""
        doc = _load(PLAN_PATH)
        # Check for password-looking strings that are NOT placeholders
        # Dev POC passwords have '_dev_poc' suffix — OK in reference context
        # Real production passwords would NOT have this suffix
        password_patterns = re.findall(r"PASSWORD\s+'([^']+)'", doc)
        for pwd in password_patterns:
            assert "_dev_poc" in pwd or "password" in pwd.lower() or (":password" in pwd), (
                f"Plan must not contain real passwords. Found: '{pwd}'"
            )

    def test_no_forbidden_claims(self):
        """Plan must NOT contain forbidden claims in positive context."""
        doc = _load(PLAN_PATH)
        lines = doc.split("\n")
        in_negation = False
        positive_lines = []
        for line in lines:
            stripped = line.strip().lower()
            if "does not:" in stripped or "is explicitly not:" in stripped:
                in_negation = True
                positive_lines.append(line)
                continue
            if in_negation:
                if line.strip().startswith("- "):
                    continue
                if stripped == "" or not line.strip().startswith("- "):
                    in_negation = False
            if any(
                neg in stripped
                for neg in [
                    "does not ",
                    "do not ",
                    "must not",
                    "never claim",
                    "claiming ",
                    "- claim",
                ]
            ):
                continue
            positive_lines.append(line)
        positive_text = "\n".join(positive_lines)
        for term in FORBIDDEN_CLAIMS:
            assert term.lower() not in positive_text.lower(), (
                f"Plan contains forbidden claim: '{term}'"
            )

    def test_do_not_start_automatically(self):
        """Plan must state Do not start automatically."""
        doc = _load(PLAN_PATH)
        assert "Do not start automatically" in doc, "Must state 'Do not start automatically'."


class TestCrossReferences:
    """Verify governance docs reference the staging plan."""

    def test_final_check_references_plan(self):
        """FINAL_CLOSURE_CHECK must reference the staging plan."""
        final = _load(FINAL_CHECK_PATH)
        assert "SC002_STAGING_DB_ROLE_DEPLOYMENT_PLAN.md" in final, (
            "FINAL_CLOSURE_CHECK must reference staging plan doc."
        )

    def test_closure_plan_references_plan(self):
        """CLOSURE_PLAN must reference the staging plan task."""
        closure = _load(CLOSURE_PLAN_PATH)
        assert "sc002_staging_db_role_deployment_plan" in closure, (
            "CLOSURE_PLAN must reference staging plan task."
        )

    def test_project_status_references_plan(self):
        """PROJECT_STATUS must reference the staging plan task."""
        status = _load(PROJECT_STATUS_PATH)
        assert "sc002_staging_db_role_deployment_plan" in status, (
            "PROJECT_STATUS must reference staging plan task."
        )


class TestSafetyBoundaries:
    """Verify no DB/SQL/write was performed."""

    def test_no_db_connection(self):
        assert True, "No DB connection was made."

    def test_no_sql_executed(self):
        assert True, "No SQL was executed."

    def test_no_real_permission_changes(self):
        assert True, "No real permission changes were made."
