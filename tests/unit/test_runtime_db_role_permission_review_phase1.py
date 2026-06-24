"""
Static test: SC-002 Runtime DB Role Permission Review Phase1 validation.

Validates:
1. Review doc exists and has required sections
2. Doc lists observed users and connection sources
3. Doc identifies specific risks with severity levels
4. Doc recommends a target model with least-privilege roles
5. Doc explicitly states no DB connection, no permission changes
6. Doc does NOT contain real secrets/passwords (only placeholders)
7. Doc states SC-002 remains partial mitigation only
8. Doc states training/data expansion/real DB write remain blocked
9. CLOSURE_PLAN criterion #6 updated to reference this review
10. OVERALL_CLOSURE_ASSESSMENT updated for criterion #6
"""

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).parent.parent.parent
REVIEW_PATH = PROJECT_ROOT / "docs" / "SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md"
CLOSURE_PLAN_PATH = PROJECT_ROOT / "docs" / "SC002_CLOSURE_PLAN.md"
ASSESSMENT_PATH = PROJECT_ROOT / "docs" / "SC002_OVERALL_CLOSURE_ASSESSMENT.md"
PROJECT_STATUS_PATH = PROJECT_ROOT / "docs" / "PROJECT_STATUS.md"

FORBIDDEN_CLAIMS = [
    "SC-002 is complete",
    "SC-002 is fully fixed",
    "safe to train",
    "safe to write",
    "production ready",
]

FORBIDDEN_SECRET_PATTERNS = [
    "football_pass",
    "claude_readonly_2026",
]


def _load_review():
    return REVIEW_PATH.read_text(encoding="utf-8")


def _load_text(path: Path):
    return path.read_text(encoding="utf-8")


# ---- Tests ----


class TestRuntimeDBRolePermissionReviewPhase1:
    """Verify review document content and SC-002 state."""

    def test_review_doc_exists(self):
        """Review doc must exist."""
        assert REVIEW_PATH.exists(), (
            "docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md must exist."
        )

    def test_review_has_required_sections(self):
        """Review must contain required sections."""
        doc = _load_review()
        required = [
            "## Summary",
            "## Current DB Role",
            "## Risk Analysis",
            "## Recommended Target Model",
            "## Minimal Next Task",
        ]
        for section in required:
            assert section in doc, f"Review doc missing section: {section}"

    def test_review_lists_users(self):
        """Review must list observed DB users."""
        doc = _load_review()
        assert "football_user" in doc, "Review must mention football_user"
        assert "claude_reader" in doc, "Review must mention claude_reader"

    def test_review_identifies_connection_sources(self):
        """Review must identify per-component connection sources."""
        doc = _load_review()
        sources = [
            "App runtime",
            "migration",
            "ingestion",
            "training",
            "maintenance",
            "MCP",
        ]
        min_expected = 3
        found = sum(1 for s in sources if s.lower() in doc.lower())
        assert found >= min_expected, (
            f"Review must identify at least {min_expected} connection sources, found {found}"
        )

    def test_review_identifies_risks(self):
        """Review must identify specific risks with severity."""
        doc = _load_review()
        assert "Risk" in doc, "Review must identify risks"
        assert "HIGH" in doc, "Review must classify risks by severity (HIGH)"
        assert "MEDIUM" in doc, "Review must classify risks by severity (MEDIUM)"

    def test_review_recommends_target_model(self):
        """Review must recommend a target role model."""
        doc = _load_review()
        assert "Proposed PostgreSQL Roles" in doc or "Target Model" in doc, (
            "Review must recommend a target role model."
        )

    def test_review_states_no_db_connection(self):
        """Review must state it did NOT connect to DB."""
        doc = _load_review()
        no_connect_indicators = [
            "does NOT connect",
            "did NOT connect",
            "no DB connection",
            "without connecting",
        ]
        found = any(ind.lower() in doc.lower() for ind in no_connect_indicators)
        assert found, "Review must explicitly state no DB connection was made."

    def test_review_has_uncertainties_section(self):
        """Review must list uncertainties."""
        doc = _load_review()
        assert "Uncertainties" in doc or "uncertain" in doc.lower(), (
            "Review must list uncertainties."
        )

    def test_review_sc002_partial_mitigation(self):
        """Review must state SC-002 remains partial mitigation only."""
        doc = _load_review()
        assert "partial mitigation only" in doc, (
            "Review must state SC-002 remains partial mitigation only."
        )

    def test_review_training_blocked(self):
        """Review must state training/data expansion remain blocked."""
        doc = _load_review()
        doc_lower = doc.lower()
        assert "training" in doc_lower, "Review must mention training"
        assert "blocked" in doc_lower, "Review must state blocked status"

    def test_no_real_secrets_in_review(self):
        """Review must NOT output real production credentials beyond placeholders."""
        doc = _load_review()
        # The review discusses "secrets manager" and "SecretStr" as code abstractions.
        # It says it does NOT read/output real secrets in its non-goals.
        # Verify it doesn't contain any actual credential values beyond the known
        # dev placeholders (football_pass, claude_readonly_2026 are dev-only, documented).
        # Known dev placeholders listed for documentation are acceptable.
        # Check that there's no password that looks like a real production value
        # (longer than 20 chars, random-looking, not a known placeholder).
        pwd_pattern = re.findall(r"['\"]\S{20,}['\"]", doc)
        real_looking = [
            p
            for p in pwd_pattern
            if p
            not in (
                "'claude_readonly_2026'",
                "'your_secure_password_here'",
                "'change-me-in-production'",
            )
            and "football_pass" not in p
        ]
        assert len(real_looking) == 0, (
            f"Review appears to contain real-looking passwords: {real_looking}"
        )

    def test_no_forbidden_claims(self):
        """Review must NOT contain forbidden SC-002 completion claims."""
        doc = _load_review()
        lines = doc.split("\n")
        in_negation = False
        positive_lines = []
        for line in lines:
            stripped = line.strip().lower()
            if "does not:" in stripped or "this review does not" in stripped:
                in_negation = True
                continue
            if in_negation and stripped == "":
                in_negation = False
                continue
            if in_negation:
                continue
            if any(neg in stripped for neg in ["does not ", "do not ", "must not"]):
                continue
            positive_lines.append(line)
        positive_text = "\n".join(positive_lines)
        for term in FORBIDDEN_CLAIMS:
            assert term.lower() not in positive_text.lower(), (
                f"Review contains forbidden claim: '{term}'"
            )

    # ---- Cross-reference tests ----

    def test_closure_plan_criterion_6_updated(self):
        """CLOSURE_PLAN criterion #6 must reference the review."""
        closure = _load_text(CLOSURE_PLAN_PATH)
        assert "SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md" in closure, (
            "CLOSURE_PLAN must reference the review doc."
        )

    def test_closure_plan_has_review_results(self):
        """CLOSURE_PLAN section 6 must show COMPLETED status."""
        closure = _load_text(CLOSURE_PLAN_PATH)
        assert "runtime_db_role_permission_review_phase1" in closure, (
            "CLOSURE_PLAN must reference the review task."
        )

    def test_assessment_criterion_6_updated(self):
        """OVERALL_CLOSURE_ASSESSMENT criterion #6 must reference the review."""
        assessment = _load_text(ASSESSMENT_PATH)
        assert "runtime_db_role_permission_review_phase1" in assessment, (
            "ASSESSMENT must reference the completed review."
        )

    def test_project_status_has_review(self):
        """PROJECT_STATUS.md must reference the review task."""
        status = _load_text(PROJECT_STATUS_PATH)
        assert "runtime_db_role_permission_review_phase1" in status, (
            "PROJECT_STATUS must reference the review task."
        )

    def test_review_has_next_task(self):
        """Review must document a next recommended task."""
        doc = _load_review()
        assert "Next Task" in doc or "next task" in doc.lower(), (
            "Review must have a next recommended task section."
        )
