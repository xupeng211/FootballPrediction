"""Tests for the minimal STRICT review evidence contract.

lifecycle: test-fixture
"""

from __future__ import annotations

import pytest

from scripts.ops.helpers.strict_review_evidence import validate_strict_review_evidence

CURRENT_SHA = "a" * 40
OLD_SHA = "b" * 40
SAME_PREFIX_SHA = "a" * 7 + "b" * 33


def _body(
    workflow_class: str,
    *,
    reviewed_sha: str | None = CURRENT_SHA,
    task_type: str = "workflow-governance",
) -> str:
    evidence = ""
    if workflow_class in {"STRICT", "CRITICAL"} and reviewed_sha is not None:
        evidence = f"""

## Strict Review Evidence

| Field | Value |
| --- | --- |
| Version | 1 |
| Task type | {workflow_class} |
| Provider | {"codex-cli, claude-code-deepseek" if workflow_class == "CRITICAL" else "local-codex-review"} |
| Reviewed full SHA | {reviewed_sha} |
| Result | PASS |
| Timestamp | 2026-08-21T12:00:00Z |
"""
    return f"""## Scope

| Field | Value |
| --- | --- |
| Task type | {task_type} |
| Workflow class | {workflow_class} |
{evidence}
"""


def test_normal_critical_path_cannot_waive_dual_review():
    errors = validate_strict_review_evidence(
        _body("NORMAL", reviewed_sha=None, task_type="db-migration-sql"),
        CURRENT_SHA,
        changed_paths=["database/migrations/001.sql"],
        task_type="db-migration-sql",
    )
    assert any("CRITICAL_REVIEW_CLASSIFICATION_REQUIRED" in error for error in errors)


def test_normal_unknown_path_cannot_waive_strict_review():
    errors = validate_strict_review_evidence(
        _body("NORMAL", reviewed_sha=None, task_type="source-code"),
        CURRENT_SHA,
        changed_paths=["scripts/ops/fotmob_detail_capture.js"],
        task_type="source-code",
    )
    assert any("STRICT_REVIEW_CLASSIFICATION_REQUIRED" in error for error in errors)


def test_normal_database_writer_path_cannot_waive_strict_review():
    errors = validate_strict_review_evidence(
        _body("NORMAL", reviewed_sha=None, task_type="source-code"),
        CURRENT_SHA,
        changed_paths=["src/data/streaming/streaming_db_writer.py"],
        task_type="source-code",
    )
    assert any("STRICT_REVIEW_CLASSIFICATION_REQUIRED" in error for error in errors)


def test_normal_infrastructure_network_path_cannot_waive_strict_review():
    errors = validate_strict_review_evidence(
        _body("NORMAL", reviewed_sha=None, task_type="source-code"),
        CURRENT_SHA,
        changed_paths=["src/infrastructure/network/FotMobApiClient.js"],
        task_type="source-code",
    )
    assert any("STRICT_REVIEW_CLASSIFICATION_REQUIRED" in error for error in errors)


def test_normal_low_risk_source_path_does_not_require_review():
    assert (
        validate_strict_review_evidence(
            _body("NORMAL", reviewed_sha=None, task_type="source-code"),
            CURRENT_SHA,
            changed_paths=["src/ui/scorecard.js"],
            task_type="source-code",
        )
        == []
    )


def test_normal_without_review_evidence_passes():
    assert (
        validate_strict_review_evidence(
            _body("NORMAL", reviewed_sha=None),
            CURRENT_SHA,
            changed_paths=["src/ui/scorecard.js"],
        )
        == []
    )


@pytest.mark.parametrize("workflow_class", ["NORMAL", "STRICT"])
@pytest.mark.parametrize("changed_paths", [None, []])
def test_missing_changed_paths_fail_closed_at_critical_classification(
    workflow_class: str, changed_paths
):
    errors = validate_strict_review_evidence(
        _body(workflow_class, reviewed_sha=None if workflow_class == "NORMAL" else CURRENT_SHA),
        CURRENT_SHA,
        changed_paths=changed_paths,
    )
    assert any("CRITICAL_REVIEW_CLASSIFICATION_REQUIRED" in error for error in errors)


def test_strict_valid_current_full_sha_passes():
    assert (
        validate_strict_review_evidence(
            _body("STRICT"), CURRENT_SHA, changed_paths=["src/ui/scorecard.js"]
        )
        == []
    )


def test_critical_is_first_class_and_strict_cannot_downgrade_governance():
    assert (
        validate_strict_review_evidence(
            _body("CRITICAL", task_type="workflow-governance"),
            CURRENT_SHA,
            changed_paths=["scripts/devops/agent_workflow.py"],
            task_type="workflow-governance",
        )
        == []
    )
    errors = validate_strict_review_evidence(
        _body("STRICT", task_type="workflow-governance"),
        CURRENT_SHA,
        changed_paths=["scripts/devops/agent_workflow.py"],
        task_type="workflow-governance",
    )
    assert any("CRITICAL_REVIEW_CLASSIFICATION_REQUIRED" in error for error in errors)


def test_normal_cannot_downgrade_governance_change_below_critical():
    errors = validate_strict_review_evidence(
        _body("NORMAL", reviewed_sha=None, task_type="workflow-governance"),
        CURRENT_SHA,
        changed_paths=["scripts/devops/agent_workflow.py"],
        task_type="workflow-governance",
    )
    assert any("CRITICAL_REVIEW_CLASSIFICATION_REQUIRED" in error for error in errors)


def test_strict_without_evidence_fails_closed():
    errors = validate_strict_review_evidence(
        _body("STRICT", reviewed_sha=None),
        CURRENT_SHA,
        changed_paths=["src/ui/scorecard.js"],
    )
    assert any("STRICT_REVIEW_MISSING" in error for error in errors)


def test_strict_old_head_is_stale():
    errors = validate_strict_review_evidence(
        _body("STRICT", reviewed_sha=OLD_SHA),
        CURRENT_SHA,
        changed_paths=["src/ui/scorecard.js"],
    )
    assert any("STRICT_REVIEW_STALE" in error for error in errors)


def test_same_short_prefix_does_not_authorize_different_full_head():
    reviewed = "a" * 7 + "c" * 33
    errors = validate_strict_review_evidence(
        _body("STRICT", reviewed_sha=reviewed),
        SAME_PREFIX_SHA,
        changed_paths=["src/ui/scorecard.js"],
    )
    assert any("STRICT_REVIEW_STALE" in error for error in errors)


def test_malformed_evidence_fails():
    body = _body("STRICT").replace("| Version | 1 |", "| Version | two |")
    body = body.replace("| Result | PASS |", "| Result | APPROVE |")
    body = body.replace("| Timestamp | 2026-08-21T12:00:00Z |", "| Timestamp | yesterday |")
    errors = validate_strict_review_evidence(
        body, CURRENT_SHA, changed_paths=["src/ui/scorecard.js"]
    )
    assert any("STRICT_REVIEW_INVALID" in error for error in errors)


def test_source_change_after_review_invalidates_old_evidence():
    errors = validate_strict_review_evidence(
        _body("STRICT", reviewed_sha=CURRENT_SHA),
        OLD_SHA,
        changed_paths=["src/ui/scorecard.js"],
    )
    assert any("STRICT_REVIEW_STALE" in error for error in errors)


def test_fake_scope_inside_fenced_code_block_cannot_downgrade_strict_pr():
    body = """```markdown
## Scope

| Workflow class | NORMAL |
```

""" + _body("STRICT", reviewed_sha=None)
    errors = validate_strict_review_evidence(
        body, CURRENT_SHA, changed_paths=["src/ui/scorecard.js"]
    )
    assert any("STRICT_REVIEW_MISSING" in error for error in errors)


def test_duplicate_scope_sections_fail_closed():
    body = _body("STRICT") + "\n## Scope\n\n| Workflow class | NORMAL |\n"
    errors = validate_strict_review_evidence(
        body, CURRENT_SHA, changed_paths=["src/ui/scorecard.js"]
    )
    assert any("STRICT_REVIEW_CLASSIFICATION_INVALID" in error for error in errors)


def test_duplicate_evidence_sections_fail_closed():
    first = _body("STRICT")
    duplicate = first.split("## Strict Review Evidence", 1)[1]
    body = first + "\n## Strict Review Evidence" + duplicate
    errors = validate_strict_review_evidence(
        body, CURRENT_SHA, changed_paths=["src/ui/scorecard.js"]
    )
    assert any("STRICT_REVIEW_INVALID" in error for error in errors)


def test_duplicate_evidence_field_fails_closed():
    body = _body("STRICT") + "| Reviewed full SHA | " + CURRENT_SHA + " |\n"
    errors = validate_strict_review_evidence(
        body, CURRENT_SHA, changed_paths=["src/ui/scorecard.js"]
    )
    assert any("must appear once" in error for error in errors)


def test_evidence_row_with_extra_column_fails_closed():
    body = _body("STRICT").replace(
        f"| Reviewed full SHA | {CURRENT_SHA} |",
        f"| Reviewed full SHA | {CURRENT_SHA} | extra |",
    )
    errors = validate_strict_review_evidence(
        body, CURRENT_SHA, changed_paths=["src/ui/scorecard.js"]
    )
    assert any("exactly two columns" in error for error in errors)
