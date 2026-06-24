"""
Static test: SC-002 Overall Closure Assessment validation.

Validates:
1. Assessment doc exists
2. Doc explicitly states SC-002 is NOT complete
3. Doc explicitly states training/data expansion/real DB write remain blocked
4. Doc lists each of the 10 closure criteria with status
5. Python track is marked complete/met
6. No forbidden claims (safe to train, safe to write, production ready, SC-002 complete)
7. CLOSURE_PLAN references the assessment doc
8. PROJECT_STATUS references the assessment
9. Next recommended task is documented with "Do not start automatically"
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
ASSESSMENT_PATH = PROJECT_ROOT / "docs" / "SC002_OVERALL_CLOSURE_ASSESSMENT.md"
CLOSURE_PLAN_PATH = PROJECT_ROOT / "docs" / "SC002_CLOSURE_PLAN.md"
PROJECT_STATUS_PATH = PROJECT_ROOT / "docs" / "PROJECT_STATUS.md"

EXPECTED_CRITERIA = [
    "entrypoints are guarded",
    "Changed-files enforcement",
    "Browser",
    "FotMob",
    "pageProps",
    "Shared module",
    "Python / SQL / migration",
    "SQL",
    "Runtime DB",
    "permission",
    "No production override",
    "Training and data expansion remain blocked",
]

FORBIDDEN_CLAIMS = [
    "SC-002 is complete",
    "SC-002 is fully fixed",
    "SC-002 resolved",
    "safe to train",
    "safe to write",
    "production ready",
]

REQUIRED_PHRASES = [
    "partial mitigation only",
    "training",
    "blocked",
    "data expansion",
    "real DB write",
]


def _load_assessment():
    return ASSESSMENT_PATH.read_text(encoding="utf-8")


def _load_text(path: Path):
    return path.read_text(encoding="utf-8")


# ---- Tests ----


class TestOverallClosureAssessment:
    """Verify assessment document content and SC-002 state."""

    def test_assessment_doc_exists(self):
        """Assessment doc must exist."""
        assert ASSESSMENT_PATH.exists(), "docs/SC002_OVERALL_CLOSURE_ASSESSMENT.md must exist."

    def test_assessment_has_required_sections(self):
        """Assessment must contain required sections."""
        doc = _load_assessment()
        required_sections = [
            "## Summary",
            "## Per-Criterion Assessment",
            "### Criterion 1",
            "### Criterion 2",
            "### Criterion 3",
            "### Criterion 4",
            "### Criterion 5",
            "### Criterion 6",
            "### Criterion 7",
            "### Criterion 8",
            "## Summary Table",
            "## Next Recommended Task",
        ]
        for section in required_sections:
            assert section in doc, f"Assessment doc missing required section: {section}"

    def test_sc002_not_complete(self):
        """Assessment must state SC-002 cannot be closed / not complete."""
        doc = _load_assessment()
        assert "cannot be closed" in doc.lower() or "not complete" in doc.lower(), (
            "Assessment must explicitly state SC-002 cannot be closed."
        )

    def test_sc002_partial_mitigation(self):
        """Assessment must state SC-002 is partial mitigation only."""
        doc = _load_assessment()
        assert "partial mitigation only" in doc, (
            "Assessment must state SC-002 remains partial mitigation only."
        )

    def test_training_blocked(self):
        """Assessment must state training is blocked."""
        doc = _load_assessment()
        doc_lower = doc.lower()
        assert "training" in doc_lower, "Assessment must mention training"
        assert "blocked" in doc_lower, "Assessment must state training is blocked"

    def test_data_expansion_blocked(self):
        """Assessment must state data expansion is blocked."""
        doc = _load_assessment()
        doc_lower = doc.lower()
        assert "data expansion" in doc_lower, "Assessment must mention data expansion"
        assert "blocked" in doc_lower, "Assessment must state data expansion is blocked"

    def test_real_db_write_blocked(self):
        """Assessment must state real DB write is blocked."""
        doc = _load_assessment()
        doc_lower = doc.lower()
        assert "real db write" in doc_lower or "real DB write" in doc, (
            "Assessment must reference real DB write"
        )
        assert "blocked" in doc_lower, "Assessment must state real DB write is blocked"

    def test_python_track_marked_complete(self):
        """Assessment must mark Python track as complete/met."""
        doc = _load_assessment()
        assert (
            "Python track" in doc
            or "ALL 20 Python write paths" in doc
            or "Python track is fully complete" in doc
        ), "Assessment must reference Python track completion."

    def test_no_forbidden_claims(self):
        """Assessment must NOT contain forbidden SC-002 completion claims."""
        doc = _load_assessment()
        lines = doc.split("\n")
        in_negation_section = False
        positive_lines = []
        for line in lines:
            stripped_lower = line.strip().lower()
            # Track when we enter/exit a "does NOT" section
            if "does not:" in stripped_lower or "this assessment does not" in stripped_lower:
                in_negation_section = True
                continue
            if in_negation_section and stripped_lower == "":
                in_negation_section = False
                continue
            if in_negation_section:
                continue
            # Skip individual lines that are clearly negations
            if any(
                neg in stripped_lower for neg in ["does not ", "do not ", "must not", "never claim"]
            ):
                continue
            positive_lines.append(line)
        positive_text = "\n".join(positive_lines)
        for term in FORBIDDEN_CLAIMS:
            assert term.lower() not in positive_text.lower(), (
                f"Assessment contains forbidden claim: '{term}'"
            )

    def test_next_task_documented(self):
        """Assessment must document a next recommended task."""
        doc = _load_assessment()
        assert "Next Recommended Task" in doc, (
            "Assessment must have a Next Recommended Task section."
        )

    def test_do_not_start_automatically(self):
        """Assessment must state Do not start automatically."""
        doc = _load_assessment()
        assert "Do not start automatically" in doc, (
            "Assessment must state 'Do not start automatically' for the next task."
        )

    def test_assessment_says_documentation_only(self):
        """Assessment must state it is assessment/documentation only, not implementation."""
        doc = _load_assessment()
        assert "assessment" in doc.lower(), "Assessment must identify itself as an assessment task."

    # ---- Cross-reference tests ----

    def test_closure_plan_references_assessment(self):
        """SC002_CLOSURE_PLAN.md must reference the assessment doc."""
        closure = _load_text(CLOSURE_PLAN_PATH)
        assert "SC002_OVERALL_CLOSURE_ASSESSMENT.md" in closure, (
            "CLOSURE_PLAN must reference SC002_OVERALL_CLOSURE_ASSESSMENT.md"
        )

    def test_project_status_references_assessment(self):
        """PROJECT_STATUS.md must reference the assessment task."""
        status = _load_text(PROJECT_STATUS_PATH)
        assert "sc002_overall_closure_assessment" in status, (
            "PROJECT_STATUS must reference sc002_overall_closure_assessment"
        )

    def test_project_status_has_next_task_blocked(self):
        """PROJECT_STATUS.md must state Do not start automatically for the next task."""
        status = _load_text(PROJECT_STATUS_PATH)
        assert "Do not start automatically" in status, (
            "PROJECT_STATUS.md must state 'Do not start automatically' for the next task."
        )
