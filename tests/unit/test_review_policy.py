"""Adversarial contract tests for the canonical multi-review policy."""

from __future__ import annotations

from scripts.devops.review_policy import (
    BACKEND_CODEX,
    BACKEND_DEEPSEEK,
    CandidateBinding,
    ReviewEvidence,
    evaluate_review_policy,
)


def _candidate() -> CandidateBinding:
    return CandidateBinding("a" * 40, "b" * 40, "c" * 64, "MISSION", "d" * 64)


def _receipt(backend: str, **overrides: object) -> ReviewEvidence:
    value: dict[str, object] = {
        "backend_id": backend,
        "trusted": True,
        "result": "PASS",
        "base_sha": "a" * 40,
        "head_sha": "b" * 40,
        "diff_sha256": "c" * 64,
        "mission_id": "MISSION",
        "mission_scope_sha256": "d" * 64,
        "finding_counts_by_severity": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
    }
    value.update(overrides)
    return ReviewEvidence(**value)  # type: ignore[arg-type]


def test_normal_defaults_to_deepseek_only():
    result = evaluate_review_policy("NORMAL", _candidate(), [_receipt(BACKEND_DEEPSEEK)])
    assert result.status == "SATISFIED"
    assert result.required_backends == (BACKEND_DEEPSEEK,)


def test_normal_explicit_codex_is_allowed_but_not_implicit():
    receipt = _receipt(BACKEND_CODEX)
    assert evaluate_review_policy("NORMAL", _candidate(), [receipt]).status == "UNSATISFIED"
    assert (
        evaluate_review_policy(
            "NORMAL", _candidate(), [receipt], selected_backend=BACKEND_CODEX
        ).status
        == "SATISFIED"
    )


def test_deepseek_infrastructure_failure_never_falls_back():
    result = evaluate_review_policy(
        "NORMAL", _candidate(), [_receipt(BACKEND_DEEPSEEK, infrastructure_failure=True)]
    )
    assert result.status == "UNSATISFIED"
    assert "REVIEW_INFRASTRUCTURE_BLOCK" in result.reasons


def test_strict_requires_codex_even_with_deepseek():
    result = evaluate_review_policy("STRICT", _candidate(), [_receipt(BACKEND_DEEPSEEK)])
    assert result.status == "UNSATISFIED"
    assert result.required_backends == (BACKEND_CODEX,)


def test_strict_codex_satisfies_without_deepseek_cost():
    result = evaluate_review_policy("STRICT", _candidate(), [_receipt(BACKEND_CODEX)])
    assert result.status == "SATISFIED"


def test_strict_ignores_advisory_deepseek_evidence():
    result = evaluate_review_policy(
        "STRICT",
        _candidate(),
        [_receipt(BACKEND_CODEX), _receipt(BACKEND_DEEPSEEK, trusted=False)],
    )
    assert result.status == "SATISFIED"


def test_required_backend_must_be_eligible_in_active_registry():
    result = evaluate_review_policy(
        "STRICT",
        _candidate(),
        [_receipt(BACKEND_CODEX)],
        backend_eligibility={BACKEND_CODEX: frozenset({"NORMAL"})},
    )
    assert result.status == "INVALID"
    assert result.reasons == ("BACKEND_NOT_ELIGIBLE",)


def test_critical_requires_both_independent_backends():
    result = evaluate_review_policy(
        "CRITICAL", _candidate(), [_receipt(BACKEND_CODEX), _receipt(BACKEND_DEEPSEEK)]
    )
    assert result.status == "SATISFIED"
    assert result.required_backends == (BACKEND_CODEX, BACKEND_DEEPSEEK)


def test_critical_one_backend_is_unsatisfied():
    result = evaluate_review_policy("CRITICAL", _candidate(), [_receipt(BACKEND_CODEX)])
    assert result.status == "UNSATISFIED"


def test_critical_rejects_different_head_or_scope():
    wrong_head = _receipt(BACKEND_DEEPSEEK, head_sha="e" * 40)
    result = evaluate_review_policy("CRITICAL", _candidate(), [_receipt(BACKEND_CODEX), wrong_head])
    assert result.status == "INVALID"
    assert "SAME_CANDIDATE_BINDING_MISMATCH" in result.reasons


def test_blocking_finding_blocks_but_p3_is_surfaced_nonblocking():
    p3 = _receipt(BACKEND_DEEPSEEK, finding_counts_by_severity={"P0": 0, "P1": 0, "P2": 0, "P3": 2})
    assert evaluate_review_policy("NORMAL", _candidate(), [p3]).status == "SATISFIED"
    blocked = _receipt(
        BACKEND_DEEPSEEK, finding_counts_by_severity={"P0": 0, "P1": 0, "P2": 1, "P3": 0}
    )
    assert evaluate_review_policy("NORMAL", _candidate(), [blocked]).status == "UNSATISFIED"


def test_unknown_class_and_backend_confusion_fail_closed():
    assert evaluate_review_policy("UNKNOWN", _candidate(), []).status == "INVALID"
    confused = _receipt(BACKEND_CODEX, trusted=False)
    assert evaluate_review_policy("STRICT", _candidate(), [confused]).status == "INVALID"


def test_infrastructure_failure_is_not_misreported_as_binding_tamper():
    result = evaluate_review_policy(
        "NORMAL",
        _candidate(),
        [
            _receipt(
                BACKEND_DEEPSEEK,
                trusted=False,
                infrastructure_failure=True,
                base_sha="",
                head_sha="",
                diff_sha256="",
                mission_id="",
                mission_scope_sha256="",
            )
        ],
    )
    assert result.status == "UNSATISFIED"
    assert result.reasons == ("REVIEW_INFRASTRUCTURE_BLOCK",)


def test_critical_rejects_duplicate_backend_and_override():
    result = evaluate_review_policy(
        "CRITICAL", _candidate(), [_receipt(BACKEND_CODEX), _receipt(BACKEND_CODEX)]
    )
    assert result.status == "INVALID"
    assert (
        evaluate_review_policy("CRITICAL", _candidate(), [], selected_backend=BACKEND_CODEX).status
        == "INVALID"
    )
