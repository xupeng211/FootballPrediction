"""新身份、完整分块和未授权 Receipt 迁移的离线正负验收。"""

from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from scripts.devops import controlled_api_admission as module
from scripts.devops.controlled_api_admission import prepare_admission, save_preparation
from scripts.devops.controlled_api_binding import bind_source
from scripts.devops.controlled_api_broker import Broker
from scripts.devops.controlled_api_budget import STATE_FILE_MODE, Budget
from scripts.devops.controlled_api_https import Credential
from scripts.devops.controlled_api_policy import ControlError, prepare
from scripts.devops.independent_review_protocol import (
    IndependentReviewProtocolError,
    canonical_json,
)
from scripts.devops.independent_review_receipt import ReceiptEvidenceContext, validate_receipt
from scripts.devops.review_policy import CandidateBinding, ReviewEvidence, evaluate_review_policy
from tests.unit.controlled_api_tls_fixture import make_tls_site
from tests.unit.test_controlled_api_binding import MISSION, SCOPE, source_repo  # noqa: F401
from tests.unit.test_controlled_api_runner import response

PROJECT = Path(__file__).resolve().parents[2]
TOTAL_SLOTS = 3


@pytest.fixture
def completed(request, tmp_path_factory):
    project, base, head, _git = request.getfixturevalue("source_repo")
    state = tmp_path_factory.mktemp("admission")
    source = bind_source(project, base, head, MISSION, SCOPE)
    plans = [
        prepare(p, "检查完整候选和跨文件风险", 100) for p in ("openai", "deepseek", "deepseek")
    ]
    budget = Budget(state / "state", initialize=True)
    task = budget.create(
        source,
        plans,
        requests=3,
        tokens=sum(p["reserve_tokens"] for p in plans),
        nano_usd=sum(p["reserve_nano_usd"] for p in plans),
    )
    tls_site = make_tls_site(state)
    for slot, plan in enumerate(plans, 1):
        provider = plan["policy"]["provider"]
        review = getattr(request, "param", "FAIL") if slot == TOTAL_SLOTS else "PASS"
        with tls_site(response(provider, review=review)) as (
            tls,
            calls,
        ):
            broker = Broker(budget, task, plans, Credential("fixture-no-real-key"), tls)
            broker.execute({"task": task, "slot": slot})
            assert len(calls) == 1
    args = (project, base, head, MISSION, SCOPE, budget, task)
    return args, state, plans


def artifact_path(args, slot=1):
    return args[-2].root / f"result-{args[-1]}-{slot}.json"


def test_two_identities_all_chunks_and_real_p2_preserved(completed):
    args, _, _ = completed
    prepared = prepare_admission(*args)
    assert len(prepared["observed_results"]) == TOTAL_SLOTS
    assert [item["result"]["review_result"] for item in prepared["observed_results"]] == [
        "PASS",
        "PASS",
        "FAIL",
    ]
    finding = prepared["observed_results"][-1]["result"]["findings"][0]
    assert finding["severity"] == "P2"
    assert "file" not in finding
    assert prepared["current_approval_eligible"] is False
    assert prepared["ready_for_real_review"] is False
    assert prepared["qualification_status"] == "NOT_RUN"
    assert prepared["formal_policy"]["status"] != "SATISFIED"
    assert prepared["formal_policy"]["satisfied_backends"] == ()
    assert set(prepared["formal_policy"]["required_backends"]) == {
        "codex-cli",
        "claude-code-deepseek",
    }
    assert prepared["physical_cost_hard_bound"] == "NOT_PROVEN"
    assert prepared["candidate_binding"]["head_sha"] == args[2]


@pytest.mark.parametrize("completed", ["PASS"], indirect=True)
def test_all_mock_pass_still_does_not_qualify_or_authorize(completed):
    args, _, _ = completed
    prepared = prepare_admission(*args)
    assert all(r["result"]["review_result"] == "PASS" for r in prepared["observed_results"])
    assert prepared["current_approval_eligible"] is False
    assert prepared["qualification_status"] == "NOT_RUN"
    assert not prepared["formal_policy"]["satisfied_backends"]


@pytest.mark.parametrize(
    "field",
    [
        "source",
        "execution",
        "reviewer_identity",
        "model",
        "provider",
        "slot",
        "request_sha256",
        "policy_sha256",
        "response_sha256",
        "qualification_status",
        "channel",
        "current_approval_eligible",
        "qualification_required",
    ],
)
def test_qualification_inheritance_and_binding_forgery_rejected(completed, field):
    args, _, _ = completed
    path = artifact_path(args)
    value = json.loads(path.read_bytes())
    value[field] = True if field in {"slot", "current_approval_eligible"} else "legacy-or-other"
    path.write_bytes(canonical_json(value))
    with pytest.raises(ControlError, match="BINDING_MISMATCH"):
        prepare_admission(*args)


@pytest.mark.parametrize(
    "change", ["missing", "public", "symlink", "hardlink", "duplicate", "counts"]
)
def test_unsafe_or_incomplete_artifacts_fail_closed(completed, change):
    args, state, _ = completed
    path = artifact_path(args, 3)
    if change == "missing":
        path.unlink()
    elif change == "public":
        path.chmod(0o644)
    elif change == "symlink":
        moved = state / "moved.json"
        path.rename(moved)
        path.symlink_to(moved)
    elif change == "hardlink":
        os.link(path, state / "link.json")
    elif change == "duplicate":
        path.write_bytes(path.read_bytes().rstrip()[:-1] + b',"slot":3}\n')
    else:
        value = json.loads(path.read_bytes())
        value["result"]["finding_counts_by_severity"]["P2"] = 0
        path.write_bytes(canonical_json(value))
    with pytest.raises((ControlError, OSError)):
        prepare_admission(*args)


@pytest.mark.parametrize("state", ["PLANNED", "CLAIMED", "UNKNOWN"])
def test_partial_chunk_or_unknown_billing_never_forms_complete_bundle(
    completed, monkeypatch, state
):
    args, _, _ = completed
    budget = args[-2]
    evidence = deepcopy(budget.evidence(args[-1]))
    evidence["slots"][1]["state"] = state
    monkeypatch.setattr(budget, "evidence", lambda _task: evidence)
    with pytest.raises(ControlError, match="INCOMPLETE"):
        prepare_admission(*args)


def test_wrong_source_task_and_missing_reviewer_rejected(completed, monkeypatch):
    args, _, _ = completed
    with pytest.raises(ControlError, match="TASK_MISMATCH"):
        prepare_admission(*args[:-1], "../other")
    budget = args[-2]
    evidence = deepcopy(budget.evidence(args[-1]))
    evidence["source"]["scope_sha256"] = "f" * 64
    monkeypatch.setattr(budget, "evidence", lambda _task: evidence)
    with pytest.raises(ControlError, match="SOURCE_MISMATCH"):
        prepare_admission(*args)
    evidence["source"]["scope_sha256"] = bind_source(*args[:5])["scope_sha256"]
    evidence["slots"] = evidence["slots"][1:]
    with pytest.raises(ControlError, match="TWO_PROVIDER"):
        prepare_admission(*args)


def test_preparation_and_forged_new_identity_cannot_satisfy_existing_contract(completed):
    args, _, _ = completed
    bundle = prepare_admission(*args)
    context = ReceiptEvidenceContext(
        repo_root=args[0],
        base_sha=args[1],
        head_sha=args[2],
        mission_scope_path=SCOPE,
        prompt_bytes=b"",
        raw_output_bytes=b"",
        final_result_bytes=b"",
    )
    with pytest.raises(IndependentReviewProtocolError, match="schema invalid"):
        validate_receipt(bundle, registry={}, evidence_context=context)
    binding = CandidateBinding(**bundle["candidate_binding"])
    facts = [
        ReviewEvidence(
            backend_id=item["execution_identity"],
            trusted=True,
            result="PASS",
            **vars(binding),
            finding_counts_by_severity=dict.fromkeys(("P0", "P1", "P2", "P3"), 0),
        )
        for item in bundle["reviewer_requirements"]
    ]
    policy = evaluate_review_policy("CRITICAL", binding, facts)
    assert policy.status != "SATISFIED"
    assert "BACKEND_NOT_ALLOWED" in policy.reasons
    assert not policy.satisfied_backends


def test_only_new_external_private_bundle_is_saved(completed):
    args, state, _ = completed
    bundle = prepare_admission(*args)
    output_dir = state / "external"
    output_dir.mkdir(mode=0o700)
    output = output_dir / "preparation.json"
    save_preparation(bundle, output, project=args[0])
    assert stat.S_IMODE(output.stat().st_mode) == STATE_FILE_MODE
    assert json.loads(output.read_bytes())["current_approval_eligible"] is False
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        save_preparation(bundle, output, project=args[0])
    assert output.read_bytes() == before
    with pytest.raises(ControlError, match="EXTERNAL"):
        save_preparation(bundle, args[0] / "fake-receipt.json", project=args[0])
    bundle["current_approval_eligible"] = True
    with pytest.raises(ControlError, match="NONAUTHORIZING"):
        save_preparation(bundle, output_dir / "fake.json", project=args[0])


def test_cli_missing_results_fails_safely_without_provider_or_output(completed):
    args, state, _ = completed
    artifact_path(args).unlink()
    output = state / "missing.json"
    result = run_cli(args, output)
    assert result.returncode == 1
    assert result.stdout.strip() == "ADMISSION_PREPARATION_REJECTED"
    assert not output.exists()
    assert "Traceback" not in result.stderr


def run_cli(args, output):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.devops.controlled_api_admission",
            "--project",
            str(args[0]),
            "--base",
            args[1],
            "--head",
            args[2],
            "--mission",
            MISSION,
            "--scope",
            SCOPE,
            "--state-root",
            str(args[-2].root),
            "--task",
            args[-1],
            "--output",
            str(output),
        ],
        cwd=PROJECT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_prepares_once_and_never_resets_execution_budget(completed):
    args, state, _ = completed
    output_dir = state / "external"
    output_dir.mkdir(mode=0o700)
    output = output_dir / "prepared.json"
    before = args[-2].evidence(args[-1])
    result = run_cli(args, output)
    assert result.returncode == 0
    assert result.stdout.strip() == "PREPARATION_SAVED_NOT_APPROVAL"
    assert json.loads(output.read_bytes())["qualification_status"] == "NOT_RUN"
    assert run_cli(args, output).returncode == 1
    assert args[-2].evidence(args[-1]) == before


def test_persistence_failure_never_refunds_or_changes_results(completed, monkeypatch):
    args, state, _ = completed
    bundle = prepare_admission(*args)
    before = args[-2].evidence(args[-1])
    output_dir = state / "external"
    output_dir.mkdir(mode=0o700)
    monkeypatch.setattr(module.os, "fsync", lambda _fd: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError, match="disk"):
        save_preparation(bundle, output_dir / "new.json", project=args[0])
    assert args[-2].evidence(args[-1]) == before
    assert bundle["current_approval_eligible"] is False
