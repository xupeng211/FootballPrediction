"""风险迁移候选的缺陷阻断、替代边界、独立性和 bootstrap 负面测试。"""

# ruff: noqa: PLR2004 -- literal budgets are intentional boundary-test expectations

from dataclasses import asdict, replace
import json

import pytest

from scripts.devops.review_policy import CandidateBinding, evaluate_review_policy, required_backends
from scripts.devops.review_recovery import (
    ISOLATION,
    ReviewerProfile,
    ValidatedAttempt,
    evaluate_recovery_candidate,
    main,
)

CANDIDATE = CandidateBinding("a" * 40, "b" * 40, "c" * 64, "MISSION", "d" * 64)
SLOTS = (("openai-primary",), ("deepseek", "openai-secondary"))


def profile(name, provider="openai", model=None):
    return ReviewerProfile(
        name,
        provider,
        model or name,
        "e" * 64,
        "QUALIFIED",
        "f" * 64,
        ("NORMAL", "STRICT", "CRITICAL"),
        10000,
        4096,
        120,
        1,
    )


def profiles():
    return {
        p.profile_id: p
        for p in [
            profile("openai-primary"),
            profile("deepseek", "deepseek"),
            profile("openai-secondary"),
        ]
    }


def result(severity=None):
    findings = (
        []
        if severity is None
        else [{"severity": severity, "title": "defect", "evidence": "code trigger"}]
    )
    return {
        "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
        "review_result": "FAIL" if severity in {"P0", "P1", "P2"} else "PASS",
        "findings": findings,
    }


def attempt(name, **changes):
    return replace(
        ValidatedAttempt(
            name,
            CANDIDATE,
            "e" * 64,
            "1" * 64,
            "session-" + name,
            "worktree-" + name,
            tuple(ISOLATION),
            True,
            True,
            1,
            500,
            300,
            CANDIDATE.diff_sha256,
            result(),
        ),
        **changes,
    )


def decide(attempts=(), roster=None, slots=SLOTS, workflow="CRITICAL"):
    decision = evaluate_recovery_candidate(
        workflow, CANDIDATE, roster or profiles(), slots, attempts, builder_session_id="builder"
    )
    assert decision.merge_ready is False
    assert decision.dispatch_authorized is False
    return decision


def test_bootstrap_cannot_enable_itself_or_change_production_policy():
    assert required_backends("CRITICAL") == ("codex-cli", "claude-code-deepseek")
    assert evaluate_review_policy("CRITICAL", CANDIDATE, []).status == "UNSATISFIED"
    completed = decide([attempt("openai-primary"), attempt("deepseek")])
    assert completed.status == "PROPOSED_EVIDENCE_COMPLETE"
    assert completed.independence == "CROSS_PROVIDER"
    assert completed.status != "SATISFIED"


@pytest.mark.parametrize("workflow", ["NORMAL", "STRICT"])
def test_one_qualified_review_for_lower_tiers(workflow):
    assert (
        decide([attempt("openai-primary")], slots=(("openai-primary",),), workflow=workflow).status
        == "PROPOSED_EVIDENCE_COMPLETE"
    )


def test_second_reviewer_is_required_for_critical():
    d = decide([attempt("openai-primary")])
    assert d.status == "PROPOSED_NEXT_REVIEW"
    assert d.next_profile_id == "deepseek"


@pytest.mark.parametrize(
    "failure", ["TIMEOUT", "OUTPUT_EXHAUSTED", "SERVICE_UNAVAILABLE", "AUTH_FAILURE", "NO_VERDICT"]
)
def test_only_known_service_failure_proposes_alternate(failure):
    failed = attempt("deepseek", result=None, failure_reason=failure)
    d = decide([attempt("openai-primary"), failed])
    assert d.status == "PROPOSED_NEXT_REVIEW"
    assert d.next_profile_id == "openai-secondary"
    completed = decide([attempt("openai-primary"), failed, attempt("openai-secondary")])
    assert completed.independence == "SAME_PROVIDER"
    assert completed.physical_attempts_observed == 3
    assert completed.reserved_input_tokens == 30000
    assert completed.evidence_sha256 == ("1" * 64,) * 3


@pytest.mark.parametrize("severity", ["P0", "P1", "P2"])
def test_any_valid_finding_blocks_even_if_other_reviews_pass(severity):
    reviews = [
        attempt("openai-primary"),
        attempt("deepseek", result=result(severity)),
        attempt("openai-secondary"),
    ]
    assert decide(reviews).status == "BLOCKED_FINDINGS"


def test_a_failure_label_cannot_hide_a_verdict():
    assert (
        decide(
            [
                attempt("openai-primary"),
                attempt("deepseek", result=result("P2"), failure_reason="TIMEOUT"),
            ]
        ).status
        == "INVALID"
    )


def test_p3_is_preserved_nonblocking():
    d = decide([attempt("openai-primary"), attempt("deepseek", result=result("P3"))])
    assert d.status == "PROPOSED_EVIDENCE_COMPLETE"
    assert d.p3_findings == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"terminal_known": False},
        {"input_tokens": None},
        {"output_tokens": None},
    ],
)
def test_unknown_stops_and_retains_full_reservation(changes):
    d = decide(
        [
            attempt("openai-primary"),
            attempt("deepseek", result=None, failure_reason="TIMEOUT", **changes),
        ]
    )
    assert d.status == "UNKNOWN"
    assert d.next_profile_id is None
    assert d.reserved_input_tokens == 20000
    assert d.reserved_output_tokens == 8192


@pytest.mark.parametrize(
    "changes",
    [
        {"candidate": replace(CANDIDATE, head_sha="9" * 40)},
        {"candidate": replace(CANDIDATE, base_sha="9" * 40)},
        {"candidate": replace(CANDIDATE, mission_scope_sha256="9" * 64)},
        {"recipe_sha256": "9" * 64},
        {"coverage_diff_sha256": "9" * 64},
        {"facts_validated": False},
        {"facts_validated": "yes"},
        {"session_id": "builder"},
        {"session_id": "session-openai-primary"},
        {"worktree_id": "worktree-openai-primary"},
        {"isolation": ()},
        {"physical_attempts": True},
        {"physical_attempts": 0},
        {"physical_attempts": 2},
        {"input_tokens": 10001},
        {"output_tokens": 4097},
        {"output_tokens": True},
    ],
)
def test_binding_identity_usage_and_independence_are_fail_closed(changes):
    assert decide([attempt("openai-primary"), attempt("deepseek", **changes)]).status == "INVALID"


@pytest.mark.parametrize(
    "changes",
    [
        {"qualification_status": "ONE_CANARY_SUCCESS"},
        {"qualification_evidence_sha256": None},
        {"physical_attempt_bound": None},
        {"physical_attempt_bound": True},
        {"output_token_bound": 16385},
        {"input_token_bound": 1048577},
        {"wall_seconds": 901},
        {"task_eligibility": ("NORMAL",)},
    ],
)
def test_unqualified_or_unbounded_profile_is_not_selected(changes):
    roster = profiles()
    roster["deepseek"] = replace(roster["deepseek"], **changes)
    d = decide([attempt("openai-primary")], roster)
    assert d.next_profile_id == "openai-secondary"


def test_no_qualified_secondary_blocks_instead_of_downgrading():
    roster = {name: replace(p, qualification_status="PENDING") for name, p in profiles().items()}
    assert decide(roster=roster).status == "QUALIFICATION_REQUIRED"


def test_same_model_two_reports_are_not_qualified_as_dual_review():
    roster = profiles()
    roster["openai-secondary"] = replace(roster["openai-secondary"], model="openai-primary")
    failed = attempt("deepseek", result=None, failure_reason="OUTPUT_EXHAUSTED")
    d = decide([attempt("openai-primary"), failed, attempt("openai-secondary")], roster)
    assert d.status == "QUALIFICATION_REQUIRED"
    assert d.independence == "SAME_PROVIDER"


def test_skip_retry_duplicate_and_verdict_shopping_are_rejected():
    assert decide([attempt("openai-primary"), attempt("openai-secondary")]).status == "INVALID"
    assert (
        decide([attempt("openai-primary"), attempt("deepseek"), attempt("openai-secondary")]).status
        == "INVALID"
    )
    assert (
        decide([attempt("openai-primary"), attempt("deepseek"), attempt("deepseek")]).status
        == "INVALID"
    )
    assert decide([attempt("openai-primary")] * 5).status == "BLOCKED_BUDGET"


def test_cli_never_returns_approval_exit_code(tmp_path, capsys):
    document = {
        "workflow_class": "CRITICAL",
        "candidate": asdict(CANDIDATE),
        "profiles": [asdict(p) for p in profiles().values()],
        "slots": SLOTS,
        "attempts": [asdict(attempt("openai-primary")), asdict(attempt("deepseek"))],
        "builder_session_id": "builder",
    }
    path = tmp_path / "preview.json"
    path.write_text(json.dumps(document))
    assert main(["--facts-file", str(path)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "PROPOSED_EVIDENCE_COMPLETE"
    assert output["merge_ready"] is False
    assert output["dispatch_authorized"] is False
    document["profiles"].append(document["profiles"][0])
    path.write_text(json.dumps(document))
    assert main(["--facts-file", str(path)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "INVALID"
