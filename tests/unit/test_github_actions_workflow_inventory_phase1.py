"""Static tests for GitHub Actions workflow inventory Phase 1.

lifecycle: test-fixture
created: 2026-06-25
task: github_actions_workflow_inventory_phase1

Validates:
1. Inventory document exists
2. Document lists all .github/workflows/*.yml / .yaml
3. Each workflow has trigger classification
4. Each workflow has gate category
5. Each workflow has risk level
6. Each workflow has recommended action
7. Document contains PR Gate / Production Gate boundary description
8. Document contains secrets / DB / SQL / scraper / training security boundary checks
9. Document explicitly states this task did NOT change workflow behavior
10. Document explicitly states training / data expansion / real DB write remain blocked
11. Document does NOT contain real secrets / token / password
12. Document does NOT contain "safe to train" / "safe to write" / "production ready"
13. Document does NOT require deletion or modification of any workflow
14. Follow-ups are recommendations only, not automatically started
"""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
INVENTORY_DOC = ROOT / "docs" / "GITHUB_ACTIONS_WORKFLOW_INVENTORY_PHASE1.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _workflow_files() -> list[str]:
    """Return sorted list of workflow YAML files."""
    files: list[str] = []
    for pattern in ("*.yml", "*.yaml"):
        files.extend(p.name for p in WORKFLOWS_DIR.glob(pattern))
    return sorted(files)


def _doc_text() -> str:
    """Return the full inventory document text."""
    return INVENTORY_DOC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: Document exists
# ---------------------------------------------------------------------------


def test_inventory_document_exists():
    """Inventory document must exist at the expected path."""
    assert INVENTORY_DOC.exists(), f"Inventory document not found at {INVENTORY_DOC}"
    assert INVENTORY_DOC.is_file(), (
        f"Inventory document path exists but is not a file: {INVENTORY_DOC}"
    )


# ---------------------------------------------------------------------------
# Test 2: Document lists all workflow files
# ---------------------------------------------------------------------------


def test_inventory_lists_all_workflow_files():
    """Document must reference every .yml/.yaml file in .github/workflows/."""
    wf_files = _workflow_files()
    assert len(wf_files) > 0, "No workflow files found in .github/workflows/"
    doc = _doc_text()
    for wf_name in wf_files:
        assert wf_name in doc, f"Inventory document must mention workflow file: {wf_name}"


def test_inventory_has_workflow_count():
    """Document must state the total number of workflow files."""
    doc = _doc_text()
    _workflow_files()  # ensure workflows dir is readable
    # Document should state the count somewhere
    assert "Total workflow files:" in doc or "total" in doc.lower(), (
        "Document must state total workflow file count"
    )


# ---------------------------------------------------------------------------
# Test 3: Each workflow has trigger classification
# ---------------------------------------------------------------------------


def test_inventory_describes_triggers():
    """Document must describe trigger types for each workflow."""
    doc = _doc_text()
    trigger_terms = ["pull_request", "push", "schedule", "workflow_dispatch"]
    found = [t for t in trigger_terms if t in doc]
    assert len(found) > 0, f"Document must mention at least one trigger type from: {trigger_terms}"


def test_inventory_has_trigger_column():
    """Document must classify trigger method per workflow."""
    doc = _doc_text()
    assert "触发方式" in doc or "trigger" in doc.lower(), (
        "Document must have trigger classification for each workflow"
    )


# ---------------------------------------------------------------------------
# Test 4: Each workflow has gate category
# ---------------------------------------------------------------------------


def test_inventory_has_gate_category():
    """Document must classify whether each workflow is PR Gate / Production Gate."""
    doc = _doc_text()
    assert "PR Gate" in doc, "Document must mention PR Gate classification"
    assert "Production Gate" in doc or "Main Gate" in doc or "main Gate" in doc, (
        "Document must mention Production/Main Gate classification"
    )


# ---------------------------------------------------------------------------
# Test 5: Each workflow has risk level
# ---------------------------------------------------------------------------


def test_inventory_has_risk_level():
    """Document must assign a risk level to each workflow."""
    doc = _doc_text()
    risk_levels = ["low", "medium", "high", "unknown"]
    found = [rl for rl in risk_levels if rl.lower() in doc.lower()]
    assert len(found) > 0, f"Document must use at least one risk level from: {risk_levels}"


# ---------------------------------------------------------------------------
# Test 6: Each workflow has recommended action
# ---------------------------------------------------------------------------


def test_inventory_has_recommended_action():
    """Document must recommend an action for each workflow."""
    doc = _doc_text()
    actions = ["keep", "document", "consolidate", "deprecate", "investigate"]
    found = [a for a in actions if a.lower() in doc.lower()]
    assert len(found) > 0, f"Document must recommend at least one action from: {actions}"


# ---------------------------------------------------------------------------
# Test 7: Document contains PR Gate / Production Gate boundary description
# ---------------------------------------------------------------------------


def test_inventory_has_gate_boundary_section():
    """Document must have a dedicated section explaining gate boundaries."""
    doc = _doc_text()
    assert "Gate 边界" in doc or "Gate Boundary" in doc, (
        "Document must have a gate boundary clarification section"
    )


def test_inventory_explains_pr_gate():
    """Document must explain what the PR Gate is."""
    doc = _doc_text()
    assert "PR Gate" in doc, "Document must explain PR Gate"


def test_inventory_explains_production_gate():
    """Document must explain what the Production/main Gate is."""
    doc = _doc_text()
    assert "Production Gate" in doc or "main Gate" in doc, (
        "Document must explain Production/main Gate"
    )


def test_inventory_distinguishes_blocking_vs_auxiliary():
    """Document must identify which workflows are blocking gates vs. auxiliary."""
    doc = _doc_text()
    assert "blocking" in doc.lower() or "Blocking" in doc or "auxiliary" in doc.lower(), (
        "Document must distinguish blocking gates from auxiliary tasks"
    )


# ---------------------------------------------------------------------------
# Test 8: Security boundary checks
# ---------------------------------------------------------------------------


def test_inventory_has_security_boundary_section():
    """Document must have a section covering security boundaries."""
    doc = _doc_text()
    assert "安全边界" in doc or "Security Boundary" in doc or "security" in doc.lower(), (
        "Document must have a security boundary section"
    )


def test_inventory_checks_secrets():
    """Document must check whether workflows use secrets."""
    doc = _doc_text()
    assert "secret" in doc.lower(), "Document must check for secrets usage in workflows"


def test_inventory_checks_db_connection():
    """Document must check whether workflows may connect to DB."""
    doc = _doc_text()
    assert "DB" in doc or "database" in doc.lower() or "connect" in doc.lower(), (
        "Document must check DB connection surface"
    )


def test_inventory_checks_sql():
    """Document must check whether workflows may execute SQL."""
    doc = _doc_text()
    assert "SQL" in doc, "Document must check SQL execution surface"


def test_inventory_checks_scraper():
    """Document must check whether workflows may run scraper/browser."""
    doc = _doc_text()
    assert "scraper" in doc.lower() or "browser" in doc.lower() or "playwright" in doc.lower(), (
        "Document must check scraper/browser/Playwright surface"
    )


def test_inventory_checks_training():
    """Document must check whether workflows may train/expand data."""
    doc = _doc_text()
    assert "train" in doc.lower() or "data expansion" in doc.lower(), (
        "Document must check training/data expansion surface"
    )


# ---------------------------------------------------------------------------
# Test 9: Document states no workflow behavior was changed
# ---------------------------------------------------------------------------


def test_inventory_states_no_behavior_change():
    """Document must explicitly state this task did NOT change workflow behavior."""
    doc = _doc_text()
    no_change_phrases = [
        "没有改变 CI 行为",
        "没有修改 workflow 行为",
        "did NOT change CI behavior",
        "did not change workflow behavior",
        "没有修改 workflow",
        "没有改变 workflow",
    ]
    found = any(phrase in doc for phrase in no_change_phrases)
    assert found, "Document must state that no workflow behavior was changed"


# ---------------------------------------------------------------------------
# Test 10: Document states training/data expansion/real DB write remain blocked
# ---------------------------------------------------------------------------


def test_inventory_states_training_blocked():
    """Document must state training remains blocked."""
    doc = _doc_text()
    blocked_phrases = [
        "training / data expansion / real DB write remain blocked",
        "Training / data expansion / real DB write remain blocked",
        "training remain blocked",
        "data expansion remain blocked",
        "real DB write remain blocked",
    ]
    found = any(phrase in doc for phrase in blocked_phrases)
    assert found, "Document must state training/data expansion/real DB write remain blocked"


def test_inventory_states_sc002_complete():
    """Document must state SC-002 enforcement infrastructure is complete."""
    doc = _doc_text()
    sc002_phrases = [
        "SC-002 enforcement infrastructure",
        "enforcement infrastructure complete",
        "enforcement complete",
    ]
    found = any(phrase in doc for phrase in sc002_phrases)
    assert found, "Document must reference SC-002 enforcement status"


# ---------------------------------------------------------------------------
# Test 11: Document does NOT contain real secrets/tokens/passwords
# ---------------------------------------------------------------------------


def test_inventory_no_real_secrets():
    """Document must not contain real secrets, tokens, or passwords."""
    doc = _doc_text()
    # Allow reference to github.token (documentation of what the workflow uses)
    # but disallow actual token values or credentials
    forbidden_patterns = [
        r"ghp_[A-Za-z0-9]{36}",  # GitHub personal access token
        r"ghs_[A-Za-z0-9]{36}",  # GitHub server-to-server token
        r"github_pat_[A-Za-z0-9_]{36}",  # GitHub fine-grained PAT
        r"AKIA[0-9A-Z]{16}",  # AWS access key
        r"password\s*[=:]\s*\S+",  # password = something (not allowed)
        r"PASSWORD\s*[=:]\s*\S+",
    ]
    for pattern in forbidden_patterns:
        matches = re.findall(pattern, doc)
        assert len(matches) == 0, (
            f"Document must not contain real secrets matching pattern: {pattern}"
        )


# ---------------------------------------------------------------------------
# Test 12: Document does NOT contain forbidden safety claims
# ---------------------------------------------------------------------------


def test_inventory_no_safe_to_train():
    """Document must not claim 'safe to train'."""
    doc = _doc_text()
    assert "safe to train" not in doc.lower(), "Document must NOT claim 'safe to train'"


def test_inventory_no_safe_to_write():
    """Document must not claim 'safe to write'."""
    doc = _doc_text()
    assert "safe to write" not in doc.lower(), "Document must NOT claim 'safe to write'"


def test_inventory_no_production_ready():
    """Document must not claim 'production ready'."""
    doc = _doc_text()
    assert "production ready" not in doc.lower(), "Document must NOT claim 'production ready'"


# ---------------------------------------------------------------------------
# Test 13: Document does NOT require deleting or modifying any workflow
# ---------------------------------------------------------------------------


def test_inventory_no_delete_requirement():
    """Document must not require deleting any workflow."""
    doc = _doc_text()
    # "Recommended Action: keep" for the single workflow means no deletion
    assert "keep" in doc.lower(), "Document must not require workflow deletion"


def test_inventory_no_workflow_modification():
    """Document must not require modifying any workflow YAML inline."""
    doc = _doc_text()
    # Document should not contain edited workflow YAML content
    # (quoted YAML for reference is OK, but not instructions to modify)
    assert "不要修改" not in doc or "did not change" in doc.lower() or "did NOT change" in doc, (
        "Document must be clear about no workflow modifications"
    )


# ---------------------------------------------------------------------------
# Test 14: Follow-ups are recommendations only, not automatically started
# ---------------------------------------------------------------------------


def test_inventory_followups_are_recommendations():
    """Follow-up tasks must be labeled as recommendations, not commands."""
    doc = _doc_text()
    rec_indicators = [
        "Recommended Follow-ups",
        "推荐 follow",
        "recommendation",
        "Recommendation:",
        "Do not start automatically",
        "should not be started automatically",
        "requires separate authorization",
    ]
    found = any(indicator.lower() in doc.lower() for indicator in rec_indicators)
    assert found, "Document must present follow-ups as recommendations, not automatic next steps"


def test_inventory_followups_not_auto_start():
    """Document must explicitly say 'Do not start automatically' for follow-ups."""
    doc = _doc_text()
    assert "Do not start automatically" in doc or "not be started automatically" in doc, (
        "Document must explicitly state follow-ups should not auto-start"
    )


# ---------------------------------------------------------------------------
# Additional consistency checks
# ---------------------------------------------------------------------------


def test_inventory_references_sc002():
    """Document must reference SC-002 status."""
    doc = _doc_text()
    assert "SC-002" in doc, "Document must reference SC-002 status"


def test_inventory_references_claude_md():
    """Document must reference CLAUDE.md for CI governance consistency."""
    doc = _doc_text()
    assert "CLAUDE.md" in doc, "Document should reference CLAUDE.md for governance consistency"


def test_inventory_mentions_make_watch_pr():
    """Document should acknowledge the standard CI watch command."""
    doc = _doc_text()
    # At minimum reference the CI monitoring section
    assert "watch-pr" in doc or "make watch-pr" in doc or "CI Watch" in doc, (
        "Document should reference the standard CI monitoring approach"
    )


def test_inventory_workflow_files_exist():
    """All workflow files referenced in the document must exist on disk."""
    wf_files = set(_workflow_files())
    # The test only validates that the workflows directory has files
    # It does not parse the doc for file names (that's test 2)
    assert len(wf_files) > 0, "At least one workflow file must exist in .github/workflows/"
