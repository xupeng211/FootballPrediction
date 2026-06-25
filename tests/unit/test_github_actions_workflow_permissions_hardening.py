"""Static tests for GitHub Actions workflow permissions hardening.

lifecycle: test-fixture
created: 2026-06-25
task: github_actions_workflow_permissions_hardening

Validates that production-gate.yml has explicit least-privilege permissions
without write scopes, and that workflow behavior/triggers/jobs are unchanged.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_FILE = ROOT / ".github" / "workflows" / "production-gate.yml"
INVENTORY_DOC = ROOT / "docs" / "GITHUB_ACTIONS_WORKFLOW_INVENTORY_PHASE1.md"
PROJECT_STATUS = ROOT / "docs" / "PROJECT_STATUS.md"

# Known-good baseline values from inventory phase1 (pre-hardening)
EXPECTED_WORKFLOW_NAME = "Production Gate"
EXPECTED_JOB_NAMES = ["production-gate", "docker-build"]
EXPECTED_TRIGGERS = ["push", "pull_request"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_workflow() -> dict:
    """Parse the production-gate.yml workflow."""
    with WORKFLOW_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _workflow_raw_text() -> str:
    """Return raw YAML text of the workflow file."""
    return WORKFLOW_FILE.read_text(encoding="utf-8")


def _doc_text(path: Path) -> str:
    """Return the full document text."""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: Explicit top-level permissions block exists
# ---------------------------------------------------------------------------


def test_permissions_block_exists():
    """production-gate.yml must have a top-level permissions block."""
    wf = _parse_workflow()
    assert "permissions" in wf, "production-gate.yml must have a top-level permissions block"
    assert isinstance(wf["permissions"], dict), (
        "permissions block must be a mapping (dict), not a string"
    )


# ---------------------------------------------------------------------------
# Test 2: permissions includes contents: read
# ---------------------------------------------------------------------------


def test_permissions_has_contents_read():
    """permissions block must include contents: read."""
    wf = _parse_workflow()
    perms = wf["permissions"]
    assert perms.get("contents") == "read", (
        f"permissions must have contents: read, got: {perms.get('contents')}"
    )


# ---------------------------------------------------------------------------
# Test 3-7: No write permissions
# ---------------------------------------------------------------------------


def test_permissions_no_contents_write():
    """permissions must NOT include contents: write."""
    raw = _workflow_raw_text()
    assert "contents: write" not in raw, "permissions must NOT grant contents: write"


def test_permissions_no_pull_requests_write():
    """permissions must NOT include pull-requests: write."""
    raw = _workflow_raw_text()
    assert "pull-requests: write" not in raw, "permissions must NOT grant pull-requests: write"


def test_permissions_no_issues_write():
    """permissions must NOT include issues: write."""
    raw = _workflow_raw_text()
    assert "issues: write" not in raw, "permissions must NOT grant issues: write"


def test_permissions_no_deployments_write():
    """permissions must NOT include deployments: write."""
    raw = _workflow_raw_text()
    assert "deployments: write" not in raw, "permissions must NOT grant deployments: write"


def test_permissions_no_packages_write():
    """permissions must NOT include packages: write."""
    raw = _workflow_raw_text()
    assert "packages: write" not in raw, "permissions must NOT grant packages: write"


# ---------------------------------------------------------------------------
# Test 8: No id-token: write (unless explicitly justified)
# ---------------------------------------------------------------------------


def test_permissions_no_id_token_write():
    """permissions must NOT include id-token: write without explicit justification."""
    raw = _workflow_raw_text()
    assert "id-token: write" not in raw, "permissions must NOT grant id-token: write"


# ---------------------------------------------------------------------------
# Test 9: Workflow triggers unchanged
# ---------------------------------------------------------------------------


def test_triggers_unchanged():
    """Workflow triggers must not have changed from baseline."""
    wf = _parse_workflow()
    # PyYAML parses "on:" as boolean True (YAML 1.1 spec)
    triggers = wf.get("on") or wf.get(True)
    assert triggers is not None, "Workflow must have 'on' trigger definition"
    assert isinstance(triggers, dict), "triggers must be a dict"
    for expected_trigger in EXPECTED_TRIGGERS:
        assert expected_trigger in triggers, (
            f"Expected trigger '{expected_trigger}' not found in workflow"
        )


def test_push_trigger_targets_main():
    """push trigger must still target main branch."""
    wf = _parse_workflow()
    triggers = wf.get("on") or wf.get(True)
    push_cfg = triggers["push"]
    if isinstance(push_cfg, dict) and "branches" in push_cfg:
        branches = push_cfg["branches"]
        assert "main" in branches, "push trigger must still target main branch"


def test_pull_request_trigger_exists():
    """pull_request trigger must still be present."""
    wf = _parse_workflow()
    triggers = wf.get("on") or wf.get(True)
    assert "pull_request" in triggers, "pull_request trigger must still be present"


# ---------------------------------------------------------------------------
# Test 10: Job names unchanged
# ---------------------------------------------------------------------------


def test_job_names_unchanged():
    """Workflow must still contain expected job names."""
    wf = _parse_workflow()
    jobs = wf.get("jobs", {})
    for expected_job in EXPECTED_JOB_NAMES:
        assert expected_job in jobs, (
            f"Expected job '{expected_job}' not found. Jobs: {list(jobs.keys())}"
        )


# ---------------------------------------------------------------------------
# Test 11: Workflow still contains key CI gate jobs
# ---------------------------------------------------------------------------


def test_production_gate_job_present():
    """production-gate job must still be the CI gate."""
    wf = _parse_workflow()
    job = wf["jobs"]["production-gate"]
    assert job["runs-on"] == "ubuntu-latest", "production-gate job must still run on ubuntu-latest"


def test_docker_build_job_present():
    """docker-build job must still be present and depend on production-gate."""
    wf = _parse_workflow()
    job = wf["jobs"]["docker-build"]
    assert "needs" in job, "docker-build job must have 'needs'"
    assert "production-gate" in job["needs"], "docker-build must depend on production-gate job"


# ---------------------------------------------------------------------------
# Test 12: Inventory document records permissions hardening
# ---------------------------------------------------------------------------


def test_inventory_doc_records_hardening():
    """Inventory document must reference permissions hardening."""
    doc = _doc_text(INVENTORY_DOC)
    hardening_terms = [
        "permissions hardening",
        "permissions_hardening",
        "least-privilege",
        "explicit permissions",
        "permissions block",
    ]
    found = any(term.lower() in doc.lower() for term in hardening_terms)
    assert found, "Inventory document must record that permissions hardening was applied"


# ---------------------------------------------------------------------------
# Test 13: PROJECT_STATUS.md records task
# ---------------------------------------------------------------------------


def test_project_status_records_hardening():
    """PROJECT_STATUS.md must record the hardening task."""
    doc = _doc_text(PROJECT_STATUS)
    assert "github_actions_workflow_permissions_hardening" in doc, (
        "PROJECT_STATUS.md must record permissions hardening task"
    )


# ---------------------------------------------------------------------------
# Test 14: No forbidden safety claims in docs
# ---------------------------------------------------------------------------


def test_inventory_no_safe_to_train():
    """Inventory document must not claim 'safe to train'."""
    doc = _doc_text(INVENTORY_DOC)
    assert "safe to train" not in doc.lower(), "Inventory doc must NOT claim 'safe to train'"


def test_inventory_no_safe_to_write():
    """Inventory document must not claim 'safe to write'."""
    doc = _doc_text(INVENTORY_DOC)
    assert "safe to write" not in doc.lower(), "Inventory doc must NOT claim 'safe to write'"


def test_inventory_no_production_ready():
    """Inventory document must not claim 'production ready'."""
    doc = _doc_text(INVENTORY_DOC)
    assert "production ready" not in doc.lower(), "Inventory doc must NOT claim 'production ready'"


def test_project_status_no_safe_to_train():
    """PROJECT_STATUS.md must not claim 'safe to train' for this task."""
    doc = _doc_text(PROJECT_STATUS)
    assert "safe to train" not in doc.lower(), "PROJECT_STATUS.md must NOT claim 'safe to train'"


# ---------------------------------------------------------------------------
# Test 15: Docs explicitly state training/DB remain blocked
# ---------------------------------------------------------------------------


def test_inventory_states_training_blocked():
    """Inventory doc must state training/data expansion/real DB write remain blocked."""
    doc = _doc_text(INVENTORY_DOC)
    blocked_phrases = [
        "training / data expansion / real DB write remain blocked",
        "Training / data expansion / real DB write remain blocked",
    ]
    found = any(phrase in doc for phrase in blocked_phrases)
    assert found, "Inventory doc must state training/data expansion/real DB write remain blocked"


def test_project_status_states_blocked():
    """PROJECT_STATUS.md must state training/data expansion/real DB write remain blocked."""
    doc = _doc_text(PROJECT_STATUS)
    blocked_phrases = [
        "training / data expansion / real DB write remain blocked",
        "Training / data expansion / real DB write remain blocked",
    ]
    found = any(phrase in doc for phrase in blocked_phrases)
    assert found, (
        "PROJECT_STATUS.md must state training/data expansion/real DB write remain blocked"
    )


# ---------------------------------------------------------------------------
# Additional: Cache and PR access permissions
# ---------------------------------------------------------------------------


def test_permissions_includes_actions_write():
    """permissions should include actions: write for cache save (documented rationale)."""
    wf = _parse_workflow()
    perms = wf["permissions"]
    assert perms.get("actions") == "write", (
        f"permissions must have actions: write for cache operations, got: {perms.get('actions')}"
    )


def test_permissions_includes_pull_requests_read():
    """permissions should include pull-requests: read for gh pr view."""
    wf = _parse_workflow()
    perms = wf["permissions"]
    assert perms.get("pull-requests") == "read", (
        f"permissions must have pull-requests: read for gh pr view, got: {perms.get('pull-requests')}"
    )


# ---------------------------------------------------------------------------
# Workflow name unchanged
# ---------------------------------------------------------------------------


def test_workflow_name_unchanged():
    """Workflow name must not have changed."""
    wf = _parse_workflow()
    assert wf.get("name") == EXPECTED_WORKFLOW_NAME, (
        f"Workflow name must be '{EXPECTED_WORKFLOW_NAME}', got: '{wf.get('name')}'"
    )


# ---------------------------------------------------------------------------
# No secrets or tokens in the permissions block itself
# ---------------------------------------------------------------------------


def test_no_hardcoded_secrets_in_permissions():
    """permissions block and surrounding context must not contain hardcoded tokens."""
    raw = _workflow_raw_text()
    # The permissions block is just scope declarations, not secrets
    # But we verify no actual token strings leaked
    dangerous = ["ghp_", "ghs_", "github_pat_"]
    for token_prefix in dangerous:
        assert token_prefix not in raw, (
            f"Workflow must not contain hardcoded token prefix: {token_prefix}"
        )
