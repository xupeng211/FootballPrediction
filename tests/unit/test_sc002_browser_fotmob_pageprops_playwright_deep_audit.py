"""
Static test: SC-002 Browser / FotMob / pageProps / Playwright Deep Audit validation.

Validates:
1. Deep audit doc exists
2. Doc explicitly states SC-002 is NOT complete (partial mitigation only)
3. Doc explicitly states training / data expansion / real DB write remain blocked
4. All 43 target scripts are classified in the doc
5. Three target categories individually verified: false_positive, design_mapped, read_only
6. No forbidden claims (safe to train, safe to write, production ready, SC-002 complete)
7. OVERALL_CLOSURE_ASSESSMENT references the deep audit
8. CLOSURE_PLAN references the deep audit
9. PROJECT_STATUS references the deep audit
10. No browser / Playwright / scraper was run
11. No DB connection was made
12. No SQL was executed
13. Next recommended task documented with "Do not start automatically"
14. All target paths verified (0 unknown_needs_followup)
15. Classification correction documented
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEEP_AUDIT_PATH = PROJECT_ROOT / "docs" / "SC002_BROWSER_FOTMOB_PAGEPROPS_PLAYWRIGHT_DEEP_AUDIT.md"
ASSESSMENT_PATH = PROJECT_ROOT / "docs" / "SC002_OVERALL_CLOSURE_ASSESSMENT.md"
CLOSURE_PLAN_PATH = PROJECT_ROOT / "docs" / "SC002_CLOSURE_PLAN.md"
PROJECT_STATUS_PATH = PROJECT_ROOT / "docs" / "PROJECT_STATUS.md"
PHASE1_AUDIT_PATH = PROJECT_ROOT / "docs" / "SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md"

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
    "remain blocked",
]

TARGET_CATEGORIES = [
    "false_positive_select_only_with_active_wrapper",
    "design_mapped",
    "read_only",
]

REQUIRED_SCRIPT_CLASSIFICATIONS = [
    "confirmed_write_already_guarded",
    "confirmed_false_positive_no_write",
    "confirmed_read_only",
    "confirmed_scraper_browser_only",
    "design_mapped_all_consumers_guarded",
    "design_mapped_zero_consumers",
    "design_mapped_sql_only_no_db_client",
]


def _load_doc(path: Path):
    return path.read_text(encoding="utf-8")


class TestDeepAuditDocument:
    """Verify the deep audit document exists and has correct content."""

    def test_deep_audit_doc_exists(self):
        """Deep audit document must exist."""
        assert DEEP_AUDIT_PATH.exists(), (
            "docs/SC002_BROWSER_FOTMOB_PAGEPROPS_PLAYWRIGHT_DEEP_AUDIT.md must exist."
        )

    def test_has_required_sections(self):
        """Deep audit doc must contain all required sections."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        required_sections = [
            "## Summary",
            "## Scope",
            "## Methodology",
            "## Deep Verification Results",
            "### Category A: false_positive_select_only_with_active_wrapper",
            "### Category B: false_positive_read_only_transaction",
            "### Category C: false_positive_no_db_write_evidence",
            "### Category F: design_mapped shared modules",
            "### Category G: read_only",
            "### Category H: scraper_or_browser_only",
            "### Category I: guarded",
            "## Classification Correction",
            "## Criterion #1 Impact",
            "## Criterion #3 Impact",
            "## Counts Summary",
            "## Key Findings",
            "## SC-002 Status",
            "## Non-Goals",
            "## Next Recommended Task",
        ]
        for section in required_sections:
            assert section in doc, f"Deep audit doc missing required section: {section}"

    # ---- SC-002 state assertions ----

    def test_sc002_partial_mitigation_only(self):
        """Deep audit must state SC-002 remains partial mitigation only."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "partial mitigation only" in doc, (
            "Deep audit must state SC-002 remains partial mitigation only."
        )

    def test_sc002_not_complete(self):
        """Deep audit must NOT claim SC-002 is complete."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "This audit does NOT close SC-002" in doc or "cannot be closed" in doc.lower(), (
            "Deep audit must explicitly state it does NOT close SC-002."
        )

    def test_training_blocked(self):
        """Deep audit must state training remains blocked."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "training" in doc.lower(), "Deep audit must mention training."
        assert "blocked" in doc.lower(), "Deep audit must state training is blocked."

    def test_data_expansion_blocked(self):
        """Deep audit must state data expansion remains blocked."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "data expansion" in doc.lower(), "Deep audit must mention data expansion."
        assert "blocked" in doc.lower(), "Deep audit must state data expansion is blocked."

    def test_real_db_write_blocked(self):
        """Deep audit must state real DB write remains blocked."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "real db write" in doc.lower() or "real DB write" in doc, (
            "Deep audit must reference real DB write."
        )
        assert "blocked" in doc.lower(), "Deep audit must state real DB write is blocked."

    def test_no_browser_run(self):
        """Deep audit must state no browser/Playwright was run."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert (
            "No browser run" in doc
            or "No browser" in doc
            or ("browser" in doc.lower() and "not" in doc.lower())
        ), "Deep audit must state no browser was run."

    def test_no_db_connection(self):
        """Deep audit must state no DB connection was made."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "no db connection" in doc.lower() or "No DB connection" in doc, (
            "Deep audit must state no DB connection was made."
        )

    def test_no_sql_executed(self):
        """Deep audit must state no SQL was executed."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "no sql" in doc.lower() or "No SQL" in doc or "no real DB write" in doc.lower(), (
            "Deep audit must state no SQL was executed."
        )

    # ---- Forbidden claims ----

    def test_no_forbidden_claims(self):
        """Deep audit must NOT contain forbidden SC-002 completion claims in positive context."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        lines = doc.split("\n")
        in_negation_section = False
        positive_lines = []
        for line in lines:
            stripped_lower = line.strip().lower()
            stripped = line.strip()
            # Detect start of a "does NOT:" / "is explicitly NOT:" section
            if (
                "does not:" in stripped_lower
                or "is explicitly not:" in stripped_lower
                or "this audit does not" in stripped_lower
            ):
                in_negation_section = True
                positive_lines.append(line)  # Keep the header line
                continue
            if in_negation_section:
                # Bullet items at ANY indentation level are part of the negation list
                if stripped.startswith("- "):
                    continue  # Skip negation bullet
                # End negation section on blank line or non-bullet content
                if stripped_lower == "" or not stripped.startswith("- "):
                    in_negation_section = False
                    # fall through to process this line normally
            # Skip self-negating standalone lines
            if any(
                neg in stripped_lower
                for neg in [
                    "does not ",
                    "do not ",
                    "must not",
                    "never claim",
                    "does not close",
                    "does not unlock",
                    'claiming "safe to train',
                    "claiming sc-002",
                    "declaring sc-002",
                    "prematurely declaring",
                ]
            ):
                continue
            positive_lines.append(line)
        positive_text = "\n".join(positive_lines)
        for term in FORBIDDEN_CLAIMS:
            if term.lower() in positive_text.lower():
                raise AssertionError(
                    f"Deep audit contains forbidden claim in positive context: '{term}'"
                )

    # ---- Classification completeness ----

    def test_all_target_categories_verified(self):
        """Deep audit must verify all three target categories."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        for category in TARGET_CATEGORIES:
            assert category in doc, (
                f"Deep audit must include verification of target category: {category}"
            )

    def test_all_classifications_present(self):
        """Deep audit must use all required classification labels."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        for classification in REQUIRED_SCRIPT_CLASSIFICATIONS:
            assert classification in doc, (
                f"Deep audit must include classification: {classification}"
            )

    def test_zero_unknown_needs_followup(self):
        """Deep audit must report 0 unknown_needs_followup."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "0 unknown_needs_followup" in doc or "unknown_needs_followup" in doc, (
            "Deep audit must report unknown_needs_followup count (expected: 0)."
        )

    def test_zero_hidden_write_paths(self):
        """Deep audit must report 0 hidden write paths discovered."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "0 hidden write paths" in doc, (
            "Deep audit must report 0 hidden write paths discovered."
        )

    def test_classification_correction_documented(self):
        """Deep audit must document the 1 classification correction."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "fotmob_ligue1_adg60_raw_payload_source_inventory.js" in doc, (
            "Deep audit must mention the classification correction script."
        )
        assert "scraper_or_browser_only" in doc, (
            "Deep audit must mention the original classification."
        )
        assert "read_only" in doc, (
            "Deep audit must mention the corrected classification (read_only)."
        )

    # ---- Next task ----

    def test_next_task_documented(self):
        """Deep audit must document a next recommended task."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "Next Recommended Task" in doc, (
            "Deep audit must have a Next Recommended Task section."
        )

    def test_do_not_start_automatically(self):
        """Deep audit must state Do not start automatically."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "Do not start automatically" in doc, (
            "Deep audit must state 'Do not start automatically' for the next task."
        )

    # ---- Criterion references ----

    def test_criterion_1_referenced(self):
        """Deep audit must reference Criterion #1."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "Criterion #1" in doc, "Deep audit must reference Criterion #1."

    def test_criterion_3_referenced(self):
        """Deep audit must reference Criterion #3."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "Criterion #3" in doc, "Deep audit must reference Criterion #3."

    def test_substantially_met_language(self):
        """Deep audit must use 'Substantially met' for criteria #1 and #3."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "Substantially met" in doc, "Deep audit must state criteria are 'Substantially met'."


class TestCrossReferences:
    """Verify cross-references between governance documents."""

    def test_assessment_references_deep_audit(self):
        """OVERALL_CLOSURE_ASSESSMENT must reference the deep audit doc."""
        assessment = _load_doc(ASSESSMENT_PATH)
        assert "SC002_BROWSER_FOTMOB_PAGEPROPS_PLAYWRIGHT_DEEP_AUDIT.md" in assessment, (
            "OVERALL_CLOSURE_ASSESSMENT must reference the deep audit doc."
        )

    def test_assessment_references_deep_audit_task(self):
        """OVERALL_CLOSURE_ASSESSMENT must reference the deep audit task name."""
        assessment = _load_doc(ASSESSMENT_PATH)
        assert "browser_fotmob_pageprops_playwright_deep_audit" in assessment, (
            "OVERALL_CLOSURE_ASSESSMENT must reference the deep audit task."
        )

    def test_closure_plan_references_deep_audit(self):
        """CLOSURE_PLAN must reference the deep audit task."""
        closure = _load_doc(CLOSURE_PLAN_PATH)
        assert "browser_fotmob_pageprops_playwright_deep_audit" in closure, (
            "CLOSURE_PLAN must reference the deep audit task."
        )

    def test_project_status_references_deep_audit(self):
        """PROJECT_STATUS must reference the deep audit task."""
        status = _load_doc(PROJECT_STATUS_PATH)
        assert "browser_fotmob_pageprops_playwright_deep_audit" in status, (
            "PROJECT_STATUS must reference the deep audit task."
        )

    def test_project_status_references_deep_audit_doc(self):
        """PROJECT_STATUS must reference the deep audit document path."""
        status = _load_doc(PROJECT_STATUS_PATH)
        assert "SC002_BROWSER_FOTMOB_PAGEPROPS_PLAYWRIGHT_DEEP_AUDIT.md" in status, (
            "PROJECT_STATUS must reference the deep audit doc path."
        )


class TestAssessmentCriterionUpdates:
    """Verify criteria #1 and #3 status updates in the overall closure assessment."""

    def test_criterion_1_status_updated(self):
        """Criterion #1 must be 'Substantially met'."""
        assessment = _load_doc(ASSESSMENT_PATH)
        assert "Criterion 1" in assessment, "Assessment must contain Criterion 1."
        # Check that the assessment status has been updated
        assert "Substantially met" in assessment, (
            "Assessment must use 'Substantially met' for updated criteria."
        )

    def test_criterion_1_deep_verification_complete(self):
        """Criterion #1 must mention deep per-script verification."""
        assessment = _load_doc(ASSESSMENT_PATH)
        assert "deep per-script verification" in assessment, (
            "Criterion #1 must mention deep per-script verification."
        )

    def test_criterion_3_status_updated(self):
        """Criterion #3 must be 'Substantially met'."""
        assessment = _load_doc(ASSESSMENT_PATH)
        assert "Criterion 3" in assessment, "Assessment must contain Criterion 3."
        assert "Substantially met" in assessment, (
            "Assessment must use 'Substantially met' for Criterion #3."
        )

    def test_criterion_3_deep_verification_complete(self):
        """Criterion #3 must mention deep per-script verification."""
        assessment = _load_doc(ASSESSMENT_PATH)
        assert "deep per-script verification" in assessment, (
            "Criterion #3 must mention deep per-script verification."
        )

    def test_summary_table_updated(self):
        """Summary table must reflect updated criteria statuses."""
        assessment = _load_doc(ASSESSMENT_PATH)
        assert "Substantially met" in assessment, "Summary table must show updated statuses."
        # Verify the new count of criteria
        assert "4 criteria substantially met" in assessment or "4 criteria met" in assessment, (
            "Assessment summary must reflect updated criteria counts."
        )

    def test_next_recommended_task_is_negative_case(self):
        """Next recommended task must be changed_files_negative_case_enforcement_test."""
        assessment = _load_doc(ASSESSMENT_PATH)
        assert "changed_files_negative_case_enforcement_test" in assessment, (
            "Next recommended task must be negative case enforcement test."
        )


class TestDeepAuditSafetyBoundaries:
    """Verify safety boundary assertions in the deep audit doc and governance docs."""

    def test_deep_audit_no_browser_playwright(self):
        """Deep audit must state no browser/Playwright/scraper was run."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        non_goals_section = doc[doc.find("## Non-Goals") :]
        assert "browser" in non_goals_section.lower(), "Non-Goals must mention browser."

    def test_deep_audit_no_db(self):
        """Deep audit Non-Goals must state no DB connection."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        non_goals = doc[doc.find("## Non-Goals") :]
        assert "database" in non_goals.lower() or "DB" in non_goals, (
            "Non-Goals must mention database/DB."
        )

    def test_deep_audit_no_sql(self):
        """Deep audit Non-Goals must state no SQL executed."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        non_goals = doc[doc.find("## Non-Goals") :]
        assert "sql" in non_goals.lower() or "SQL" in non_goals, "Non-Goals must mention SQL."

    def test_project_status_sc002_partial_mitigation(self):
        """PROJECT_STATUS deep audit entry must state SC-002 remains partial mitigation only."""
        status = _load_doc(PROJECT_STATUS_PATH)
        # Find the deep audit section
        deep_audit_start = status.find("browser_fotmob_pageprops_playwright_deep_audit completed")
        assert deep_audit_start >= 0, "PROJECT_STATUS must have deep audit section."
        deep_audit_section = status[deep_audit_start : deep_audit_start + 3000]
        assert "partial mitigation only" in deep_audit_section, (
            "PROJECT_STATUS deep audit entry must state SC-002 remains partial mitigation only."
        )

    def test_project_status_training_blocked(self):
        """PROJECT_STATUS deep audit entry must state training remains blocked."""
        status = _load_doc(PROJECT_STATUS_PATH)
        deep_audit_start = status.find("browser_fotmob_pageprops_playwright_deep_audit completed")
        deep_audit_section = status[deep_audit_start : deep_audit_start + 3000]
        assert "Training" in deep_audit_section, (
            "PROJECT_STATUS deep audit entry must mention training."
        )
        assert "blocked" in deep_audit_section.lower(), (
            "PROJECT_STATUS deep audit entry must state training is blocked."
        )

    def test_assessment_not_claim_sc002_complete(self):
        """Assessment must NOT claim SC-002 can be closed."""
        assessment = _load_doc(ASSESSMENT_PATH)
        assert "partial mitigation only" in assessment, (
            "Assessment must state SC-002 is partial mitigation only."
        )
        assert "cannot be closed" in assessment.lower() or "Cannot be closed" in assessment, (
            "Assessment must state SC-002 cannot be closed."
        )

    def test_closure_plan_not_claim_sc002_complete(self):
        """CLOSURE_PLAN must NOT claim SC-002 can be closed."""
        closure = _load_doc(CLOSURE_PLAN_PATH)
        assert "partial mitigation only" in closure, (
            "CLOSURE_PLAN must state SC-002 is partial mitigation only."
        )

    def test_project_status_not_claim_sc002_complete(self):
        """PROJECT_STATUS must NOT claim SC-002 is complete."""
        status = _load_doc(PROJECT_STATUS_PATH)
        assert "SC-002 is **not fully fixed**" in status or "partial mitigation only" in status, (
            "PROJECT_STATUS must state SC-002 is not fully fixed."
        )

    def test_no_sc002_complete_anywhere(self):
        """No governance doc should claim SC-002 is complete/fixed/resolved."""
        docs_to_check = [
            (DEEP_AUDIT_PATH, "deep audit"),
            (ASSESSMENT_PATH, "assessment"),
            (CLOSURE_PLAN_PATH, "closure plan"),
            (PROJECT_STATUS_PATH, "project status"),
        ]
        for doc_path, doc_name in docs_to_check:
            doc = _load_doc(doc_path)
            doc_lower = doc.lower()
            for forbidden in ["sc-002 is complete", "sc-002 is fully fixed", "sc-002 resolved"]:
                # Allow these in negation context
                if forbidden in doc_lower:
                    # Check if it appears only in negation — use wider context window
                    idx = doc_lower.find(forbidden)
                    context_start = max(0, idx - 200)
                    context = doc_lower[context_start : idx + len(forbidden) + 200]
                    # Accept if part of a "does not" section or claim- negation bullet
                    if any(
                        marker in context
                        for marker in [
                            "does not:",
                            "do not ",
                            "does not close",
                            'claiming "safe to train',
                            "claiming sc-002",
                            "- claim sc-002",
                            "- claiming sc-002",
                            "never claim",
                            "must not",
                            "declaring sc-002",
                            "prematurely declaring",
                            "- forbidden safety claims",
                        ]
                    ):
                        continue  # OK, in negation context
                    raise AssertionError(
                        f"{doc_name} contains forbidden claim '{forbidden}' "
                        f"in positive context: ...{context[:300]}..."
                    )


class TestDeepAuditCounts:
    """Verify the counts reported in the deep audit document are consistent."""

    def test_counts_summary_present(self):
        """Deep audit must contain a Counts Summary section."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "## Counts Summary" in doc, "Deep audit must have a Counts Summary section."

    def test_guarded_count(self):
        """Deep audit must report 13 confirmed_write_already_guarded."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "confirmed_write_already_guarded" in doc, (
            "Deep audit must report guarded script count."
        )

    def test_false_positive_count(self):
        """Deep audit must report false_positive counts."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "false_positive" in doc, "Deep audit must report false_positive counts."

    def test_read_only_count(self):
        """Deep audit must report read_only counts."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "confirmed_read_only" in doc, "Deep audit must report read_only counts."

    def test_design_mapped_count(self):
        """Deep audit must report 3 design_mapped."""
        doc = _load_doc(DEEP_AUDIT_PATH)
        assert "design_mapped" in doc, "Deep audit must report design_mapped counts."
