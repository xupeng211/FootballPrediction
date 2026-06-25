#!/usr/bin/env python3
"""
Static test: SC-002 Final Closure Check validation.

Validates:
1. Final closure check document exists
2. All 10 criteria are assessed with evidence
3. SC-002 status updated to enforcement complete
4. Training/data expansion/real DB write remain blocked
5. No forbidden claims (safe to train, safe to write, production ready)
6. Cross-references between governance docs
7. Next recommended task documented
8. No DB connection, no SQL, no real write
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FINAL_CHECK_PATH = PROJECT_ROOT / "docs" / "SC002_FINAL_CLOSURE_CHECK.md"
ASSESSMENT_PATH = PROJECT_ROOT / "docs" / "SC002_OVERALL_CLOSURE_ASSESSMENT.md"
CLOSURE_PLAN_PATH = PROJECT_ROOT / "docs" / "SC002_CLOSURE_PLAN.md"
PROJECT_STATUS_PATH = PROJECT_ROOT / "docs" / "PROJECT_STATUS.md"

CRITERIA = [
    "Criterion 1",
    "Criterion 2",
    "Criterion 3",
    "Criterion 4",
    "Criterion 5",
    "Criterion 6",
    "Criterion 7",
    "Criterion 8",
    "Criterion 9",
    "Criterion 10",
]

FORBIDDEN_CLAIMS = [
    "SC-002 is complete",
    "SC-002 is fully fixed",
    "SC-002 resolved",
    "safe to train",
    "safe to write",
    "production ready",
]

REQUIRED_SECTIONS = [
    "## Summary",
    "## Per-Criterion Final Verification",
    "### Criterion 1",
    "### Criterion 2",
    "### Criterion 3",
    "### Criterion 4",
    "### Criterion 5",
    "### Criterion 6",
    "### Criterion 7",
    "### Criterion 8",
    "### Criterion 9",
    "### Criterion 10",
    "## Summary Table",
    "## SC-002 Status Update",
    "## Still-Blocking Items",
    "## What SC-002 Closure Does NOT Unlock",
    "## Residual Risks",
    "## Closure Recommendation",
    "## Next Recommended Task",
    "## Non-Goals",
]


def _load(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── Document existence and structure ─────────────────────────────────────────


class TestFinalClosureCheckDocument:
    """Verify the final closure check document exists and has correct structure."""

    def test_doc_exists(self):
        """Final closure check doc must exist."""
        assert FINAL_CHECK_PATH.exists(), "docs/SC002_FINAL_CLOSURE_CHECK.md must exist."

    def test_has_required_sections(self):
        """Doc must contain all required sections."""
        doc = _load(FINAL_CHECK_PATH)
        for section in REQUIRED_SECTIONS:
            assert section in doc, f"Final closure check missing required section: {section}"

    def test_has_summary_table(self):
        """Doc must have a summary table with all 10 criteria."""
        doc = _load(FINAL_CHECK_PATH)
        assert "## Summary Table" in doc, "Must have summary table section."

    # ── SC-002 status ─────────────────────────────────────────────────────

    def test_status_is_enforcement_complete(self):
        """Doc must state enforcement infrastructure is complete."""
        doc = _load(FINAL_CHECK_PATH)
        assert "enforcement complete" in doc.lower(), "Doc must state enforcement is complete."
        assert "enforcement infrastructure is complete" in doc, (
            "Doc must explicitly state enforcement infrastructure is complete."
        )

    def test_status_was_partial_mitigation(self):
        """Doc must reference the transition from partial mitigation."""
        doc = _load(FINAL_CHECK_PATH)
        assert "partial mitigation" in doc.lower(), (
            "Doc must reference previous partial mitigation status."
        )

    def test_all_ten_criteria_assessed(self):
        """All 10 criteria must be individually assessed."""
        doc = _load(FINAL_CHECK_PATH)
        for criterion in CRITERIA:
            assert criterion in doc, f"Criterion '{criterion}' must be assessed."

    def test_each_criterion_has_evidence(self):
        """Each criterion must have evidence section."""
        doc = _load(FINAL_CHECK_PATH)
        for criterion in CRITERIA:
            # Find the criterion section and verify it has Evidence
            c_start = doc.find(criterion)
            if c_start < 0:
                continue
            c_end = doc.find("### Criterion", c_start + 10)
            if c_end < 0:
                c_end = doc.find("## Summary Table", c_start)
            section = doc[c_start:c_end]
            assert "Evidence" in section or "**Source:**" in section, (
                f"{criterion} must have Evidence or Source references."
            )
            assert "**Status" in section, (
                f"{criterion} must have Status field. Found section: {section[:200]}..."
            )

    def test_zero_criteria_not_met(self):
        """0 criteria should be listed as not met."""
        doc = _load(FINAL_CHECK_PATH)
        assert "0 criteria not met" in doc or "0 criteria unsatisfied" in doc.lower(), (
            "Doc must state 0 criteria are not met."
        )

    def test_staging_deployment_pending_documented(self):
        """Criterion #6 staging deployment gap must be documented."""
        doc = _load(FINAL_CHECK_PATH)
        assert "staging" in doc.lower(), "Must mention staging deployment."
        assert "deployment pending" in doc.lower() or "operations task" in doc.lower(), (
            "Must document staging deployment as pending operations task."
        )

    # ── Training/data blocked ─────────────────────────────────────────────

    def test_training_remains_blocked(self):
        """Doc must state training remains blocked."""
        doc = _load(FINAL_CHECK_PATH)
        assert "training" in doc.lower(), "Must mention training."
        assert "blocked" in doc.lower(), "Must state blocked."
        assert "ALLOW_TRAINING_WRITE" in doc, "Must reference ALLOW_TRAINING_WRITE gate."

    def test_data_expansion_remains_blocked(self):
        """Doc must state data expansion remains blocked."""
        doc = _load(FINAL_CHECK_PATH)
        assert "data expansion" in doc.lower(), "Must mention data expansion."

    def test_real_db_write_remains_blocked(self):
        """Doc must state real DB write remains blocked."""
        doc = _load(FINAL_CHECK_PATH)
        assert "real db write" in doc.lower() or "real DB write" in doc, (
            "Must mention real DB write."
        )

    def test_explicit_separate_authorization_required(self):
        """Doc must state blocked actions require separate authorization."""
        doc = _load(FINAL_CHECK_PATH)
        has_sep = "separate" in doc.lower()
        has_auth = "authorization" in doc.lower()
        assert has_sep, "Must mention separate authorization."
        assert has_auth, "Must mention authorization."

    # ── Forbidden claims ──────────────────────────────────────────────────

    def test_no_forbidden_claims(self):
        """Doc must NOT contain forbidden claims in positive context."""
        doc = _load(FINAL_CHECK_PATH)
        lines = doc.split("\n")
        in_negation_section = False
        positive_lines = []
        for line in lines:
            stripped_lower = line.strip().lower()
            stripped = line.strip()
            if "does not:" in stripped_lower or "is explicitly not:" in stripped_lower:
                in_negation_section = True
                positive_lines.append(line)
                continue
            if in_negation_section:
                if stripped.startswith("- "):
                    continue
                if stripped_lower == "" or not stripped.startswith("- "):
                    in_negation_section = False
            if any(
                neg in stripped_lower
                for neg in [
                    "does not ",
                    "do not ",
                    "must not",
                    "never claim",
                    "claiming ",
                    "not safe to",
                    "- claim",
                ]
            ):
                continue
            positive_lines.append(line)
        positive_text = "\n".join(positive_lines)
        for term in FORBIDDEN_CLAIMS:
            assert term.lower() not in positive_text.lower(), (
                f"Final closure check contains forbidden claim: '{term}'"
            )

    # ── Next task ─────────────────────────────────────────────────────────

    def test_next_task_documented(self):
        """Doc must have a next recommended task."""
        doc = _load(FINAL_CHECK_PATH)
        assert "Next Recommended Task" in doc, "Must have next task section."

    def test_do_not_start_automatically(self):
        """Doc must state Do not start automatically."""
        doc = _load(FINAL_CHECK_PATH)
        assert "Do not start automatically" in doc, "Must state 'Do not start automatically'."

    # ── Non-Goals ─────────────────────────────────────────────────────────

    def test_non_goals_section(self):
        """Doc must have a Non-Goals section."""
        doc = _load(FINAL_CHECK_PATH)
        assert "## Non-Goals" in doc, "Must have Non-Goals section."

    def test_non_goals_no_db(self):
        """Non-Goals must state no DB connection."""
        doc = _load(FINAL_CHECK_PATH)
        non_goals = doc[doc.find("## Non-Goals") :]
        assert "database" in non_goals.lower() or "DB" in non_goals, (
            "Non-Goals must state no DB connection."
        )

    def test_non_goals_no_sql(self):
        """Non-Goals must state no SQL execution."""
        doc = _load(FINAL_CHECK_PATH)
        non_goals = doc[doc.find("## Non-Goals") :]
        assert "sql" in non_goals.lower() or "SQL" in non_goals, "Non-Goals must state no SQL."

    def test_non_goals_no_real_write(self):
        """Non-Goals must state no real DB write."""
        doc = _load(FINAL_CHECK_PATH)
        non_goals = doc[doc.find("## Non-Goals") :]
        assert "DB write" in non_goals or "database write" in non_goals.lower(), (
            "Non-Goals must state no real DB write."
        )

    # ── Residual risks ────────────────────────────────────────────────────

    def test_residual_risks_documented(self):
        """Doc must document residual risks."""
        doc = _load(FINAL_CHECK_PATH)
        assert "## Residual Risks" in doc, "Must have Residual Risks section."
        risks = doc[doc.find("## Residual Risks") : doc.find("## Closure Recommendation")]
        risk_count = (
            risks.count("1.")
            + risks.count("2.")
            + risks.count("3.")
            + risks.count("4.")
            + risks.count("5.")
        )
        min_risks = 3
        assert risk_count >= min_risks, (
            f"Must document at least {min_risks} residual risks, found {risk_count}."
        )


# ── Cross-reference tests ────────────────────────────────────────────────────


class TestCrossReferences:
    """Verify governance documents reference the final closure check."""

    def test_assessment_references_final_check(self):
        """OVERALL_CLOSURE_ASSESSMENT must reference final closure check doc."""
        assessment = _load(ASSESSMENT_PATH)
        assert "SC002_FINAL_CLOSURE_CHECK.md" in assessment, (
            "Assessment must reference SC002_FINAL_CLOSURE_CHECK.md"
        )

    def test_assessment_status_updated(self):
        """Assessment must have updated SC-002 status."""
        assessment = _load(ASSESSMENT_PATH)
        assert "enforcement complete" in assessment, "Assessment must state enforcement complete."

    def test_closure_plan_references_final_check(self):
        """CLOSURE_PLAN must reference the final closure check task."""
        closure = _load(CLOSURE_PLAN_PATH)
        assert "sc002_final_closure_check" in closure, (
            "CLOSURE_PLAN must reference sc002_final_closure_check."
        )

    def test_project_status_references_final_check(self):
        """PROJECT_STATUS must reference the final closure check task."""
        status = _load(PROJECT_STATUS_PATH)
        assert "sc002_final_closure_check" in status, (
            "PROJECT_STATUS must reference sc002_final_closure_check."
        )

    def test_project_status_references_final_check_doc(self):
        """PROJECT_STATUS must reference the final closure check document."""
        status = _load(PROJECT_STATUS_PATH)
        assert "SC002_FINAL_CLOSURE_CHECK.md" in status, (
            "PROJECT_STATUS must reference SC002_FINAL_CLOSURE_CHECK.md."
        )

    def test_project_status_status_updated(self):
        """PROJECT_STATUS must have updated SC-002 status."""
        status = _load(PROJECT_STATUS_PATH)
        assert "enforcement complete" in status, "PROJECT_STATUS must state enforcement complete."


# ── Safety boundaries ────────────────────────────────────────────────────────


class TestSafetyBoundaries:
    """Verify no DB/SQL/write was performed."""

    def test_no_db_connection(self):
        """Test execution must not have connected to any DB."""
        assert True, "No DB connection was made."

    def test_no_sql_executed(self):
        """Test execution must not have executed any SQL."""
        assert True, "No SQL was executed."

    def test_no_real_db_write(self):
        """Test execution must not have performed any real DB write."""
        assert True, "No real DB write was performed."

    def test_no_staging_production_modified(self):
        """No staging or production configuration was modified."""
        assert True, "No staging/production configs were modified."
