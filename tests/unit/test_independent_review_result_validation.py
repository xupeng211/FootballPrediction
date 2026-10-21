"""独立审核结果的语义校验与占位字段拒绝测试。

lifecycle: permanent
"""

from __future__ import annotations

import json

import pytest

from scripts.devops.independent_review_protocol import (
    PROTOCOL_VERSION,
    IndependentReviewProtocolError,
    validate_result,
)


def _result(verdict: str = "PASS", findings: list[dict] | None = None) -> dict:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "review_result": verdict,
        "findings": findings or [],
    }


def test_valid_generic_pass_result():
    result = validate_result(_result())
    assert result["review_result"] == "PASS"
    assert result["blocking_findings"] == 0


def test_p1_fail_and_p3_only_pass_semantics():
    finding = {"severity": "P1", "title": "bug", "evidence": "proof"}
    assert validate_result(_result("FAIL", [finding]))["blocking_findings"] == 1
    p3 = {"severity": "P3", "title": "note", "evidence": "proof"}
    assert validate_result(_result("PASS", [p3]))["blocking_findings"] == 0


@pytest.mark.parametrize(
    "result",
    [
        _result("PASS", [{"severity": "P0", "title": "bad", "evidence": "proof"}]),
        _result("FAIL", []),
        _result("PASS", [{"severity": "P9", "title": "bad", "evidence": "proof"}]),
        _result("PASS", [{"severity": "P3", "title": "", "evidence": "proof"}]),
        {"protocol_version": PROTOCOL_VERSION, "review_result": "PASS"},
        _result("FAIL", [{"severity": "P2", "title": "missing evidence"}]),
    ],
)
def test_invalid_result_semantics_rejected(result):
    with pytest.raises(IndependentReviewProtocolError):
        validate_result(result)


@pytest.mark.parametrize(
    ("title", "evidence"),
    [
        ("placeholder", "placeholder"),
        (" [ToDo] ", "proof"),
        ("TBD", "proof"),
        ("risk", "N/A"),
        ("待补充", "待填写"),
        ("...", "---"),
        ("placeholder", "A concrete trigger bypasses the guard"),
        ("A guard is bypassed", "placeholder"),
    ],
)
def test_blocker_rejects_sentinel_fields(title, evidence):
    for severity in ("P0", "P1", "P2"):
        value = _result("FAIL", [{"severity": severity, "title": title, "evidence": evidence}])
        before = json.dumps(value)
        with pytest.raises(IndependentReviewProtocolError, match="INVALID_FINDING_EVIDENCE"):
            validate_result(value)
        assert json.dumps(value) == before


@pytest.mark.parametrize(
    "location", [{"file": "guard.py", "line": 4}, {}, {"symbol": "TODO_guard"}]
)
def test_meaningful_blocker_without_required_location(location):
    finding = {
        "severity": "P2",
        "title": "The TODO branch bypasses the shared write guard",
        "evidence": "When the CLI sends an empty lock token, writer.py accepts it because guard.py only rejects None; unauthorized writes can proceed.",
        **location,
    }
    normalized = validate_result(_result("FAIL", [finding]))
    assert normalized["findings"] == [finding]
    assert normalized["blocking_findings"] == 1
    assert normalized["review_result"] == "FAIL"
