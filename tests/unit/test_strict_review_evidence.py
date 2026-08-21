"""Tests for the minimal STRICT review evidence contract.

lifecycle: test-fixture
"""

from __future__ import annotations

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
    if workflow_class == "STRICT" and reviewed_sha is not None:
        evidence = f"""

## Strict Review Evidence

| Field | Value |
| --- | --- |
| Version | 1 |
| Task type | STRICT |
| Provider | local-codex-review |
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


def test_normal_high_risk_path_cannot_waive_strict_review():
    errors = validate_strict_review_evidence(
        _body("NORMAL", reviewed_sha=None, task_type="db-migration-sql"),
        CURRENT_SHA,
        changed_paths=["database/migrations/001.sql"],
        task_type="db-migration-sql",
    )
    assert any("STRICT_REVIEW_CLASSIFICATION_REQUIRED" in error for error in errors)


def test_normal_without_review_evidence_passes():
    assert validate_strict_review_evidence(_body("NORMAL", reviewed_sha=None), CURRENT_SHA) == []


def test_strict_valid_current_full_sha_passes():
    assert validate_strict_review_evidence(_body("STRICT"), CURRENT_SHA) == []


def test_strict_without_evidence_fails_closed():
    errors = validate_strict_review_evidence(_body("STRICT", reviewed_sha=None), CURRENT_SHA)
    assert any("STRICT_REVIEW_MISSING" in error for error in errors)


def test_strict_old_head_is_stale():
    errors = validate_strict_review_evidence(_body("STRICT", reviewed_sha=OLD_SHA), CURRENT_SHA)
    assert any("STRICT_REVIEW_STALE" in error for error in errors)


def test_same_short_prefix_does_not_authorize_different_full_head():
    reviewed = "a" * 7 + "c" * 33
    errors = validate_strict_review_evidence(
        _body("STRICT", reviewed_sha=reviewed), SAME_PREFIX_SHA
    )
    assert any("STRICT_REVIEW_STALE" in error for error in errors)


def test_malformed_evidence_fails():
    body = _body("STRICT").replace("| Version | 1 |", "| Version | two |")
    body = body.replace("| Result | PASS |", "| Result | APPROVE |")
    body = body.replace("| Timestamp | 2026-08-21T12:00:00Z |", "| Timestamp | yesterday |")
    errors = validate_strict_review_evidence(body, CURRENT_SHA)
    assert any("STRICT_REVIEW_INVALID" in error for error in errors)


def test_source_change_after_review_invalidates_old_evidence():
    errors = validate_strict_review_evidence(_body("STRICT", reviewed_sha=CURRENT_SHA), OLD_SHA)
    assert any("STRICT_REVIEW_STALE" in error for error in errors)


def test_fake_scope_inside_fenced_code_block_cannot_downgrade_strict_pr():
    body = """```markdown
## Scope

| Workflow class | NORMAL |
```

""" + _body("STRICT", reviewed_sha=None)
    errors = validate_strict_review_evidence(body, CURRENT_SHA)
    assert any("STRICT_REVIEW_MISSING" in error for error in errors)


def test_duplicate_scope_sections_fail_closed():
    body = _body("STRICT") + "\n## Scope\n\n| Workflow class | NORMAL |\n"
    errors = validate_strict_review_evidence(body, CURRENT_SHA)
    assert any("STRICT_REVIEW_CLASSIFICATION_INVALID" in error for error in errors)


def test_duplicate_evidence_sections_fail_closed():
    first = _body("STRICT")
    duplicate = first.split("## Strict Review Evidence", 1)[1]
    body = first + "\n## Strict Review Evidence" + duplicate
    errors = validate_strict_review_evidence(body, CURRENT_SHA)
    assert any("STRICT_REVIEW_INVALID" in error for error in errors)


def test_duplicate_evidence_field_fails_closed():
    body = _body("STRICT") + "| Reviewed full SHA | " + CURRENT_SHA + " |\n"
    errors = validate_strict_review_evidence(body, CURRENT_SHA)
    assert any("must appear once" in error for error in errors)


def test_evidence_row_with_extra_column_fails_closed():
    body = _body("STRICT").replace(
        f"| Reviewed full SHA | {CURRENT_SHA} |",
        f"| Reviewed full SHA | {CURRENT_SHA} | extra |",
    )
    errors = validate_strict_review_evidence(body, CURRENT_SHA)
    assert any("exactly two columns" in error for error in errors)
