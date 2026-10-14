"""人民币费用估算/准入定点回归；只使用临时Git、临时Ledger和合成响应。"""

# 费用/容量验收值独立于实现常量；模块属性绑定保留原 pytest fixture 对象。
# 延迟导入保留冻结资格模块加载顺序；fake runtime 保留实际接口参数。
# ruff: noqa: PLR2004, PLC0414, PLC0415

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.devops import direct_deepseek_dispute as dispute
from scripts.devops import direct_deepseek_independent_review as runner
from scripts.devops.independent_review_backends import direct_deepseek as backend
from scripts.devops.independent_review_protocol import canonical_json
from tests.helpers.direct_harness_source import harness_source
from tests.helpers.direct_harness_source import portable_harness as portable_harness
from tests.unit import test_direct_deepseek_bound as bound_fixtures
from tests.unit import test_direct_deepseek_dispute as dispute_fixtures
from tests.unit.test_direct_deepseek_bound import (
    FakeTransport,
    capacity_candidate,
    git,
    grant_for,
    response,
)
from tests.unit.test_direct_deepseek_bound import no_network as no_network
from tests.unit.test_direct_deepseek_dispute import DisputeTransport
from tests.unit.test_direct_deepseek_dispute import grant_for as dispute_grant
from tests.unit.test_direct_deepseek_standalone import standalone_case as standalone_case

case = bound_fixtures.case
integrated = dispute_fixtures.integrated


@pytest.mark.parametrize("character", ["x", "中", '"', "\\", "\x00"])
def test_full_serialized_body_boundary_including_json_escaping(character):
    empty = json.loads(backend.payload(""))

    def encoded_size(count):
        body = deepcopy(empty)
        body["messages"][1]["content"] = character * count
        return len(canonical_json(body))

    low, high = 0, 40_001
    while low + 1 < high:
        middle = (low + high) // 2
        if encoded_size(middle) <= 40_000:
            low = middle
        else:
            high = middle
    body = backend.payload(character * low)
    assert len(body) <= 40_000 < encoded_size(low + 1)
    assert json.loads(body)["messages"][1]["content"] == character * low
    with pytest.raises(backend.DirectError, match="CAPACITY"):
        backend.payload(character * (low + 1))
    assert backend.request_cost(body) == 21_832  # integer microUSD, rounded up


@pytest.mark.parametrize("maximum", [0, 8193, True])
def test_output_limit_cannot_expand_estimate(maximum):
    with pytest.raises(backend.DirectError, match="OUTPUT_CAPACITY"):
        backend.payload("json", maximum)


def test_small_output_and_price_change_are_integer_estimates(integrated):
    args, _ = integrated
    body = backend.payload("json", 1)
    assert backend.request_cost(body, args.price_snapshot) == 80_014
    higher = deepcopy(args.price_snapshot)
    higher["rates_micro_per_million"]["peak:input_cache_miss"] *= 2
    higher["rates_micro_per_million"]["peak:output"] *= 2
    assert backend.request_cost(body, higher) == 160_028
    assert backend.POLICY["context_capacity"] == 1_048_576
    assert backend.POLICY["budget_estimate_kind"] == "ENGINEERING_ESTIMATE_NOT_PROVIDER_CAP"
    assert backend.POLICY["cost_status"] == "CONDITIONAL_COST_BOUND"
    assert (
        backend.POLICY["ordinary_dispatch_ceiling_micro_cny"]
        + backend.POLICY["unallocated_safety_reserve_micro_cny"]
        == backend.POLICY["total_task_budget_micro_cny"]
        == 50_000_000
    )
    assert backend.LIVE_EXECUTION_APPROVED is False


@pytest.mark.parametrize(
    ("primary_chunks", "posts", "reserve"), [(11, 29, 4_220_718), (15, 37, 5_385_054)]
)
def test_complete_v2_scope_estimate_preserves_all_stages(
    integrated, primary_chunks, posts, reserve
):
    args, registry = integrated
    capacity_candidate(args, primary_chunks)
    scope = json.loads(args.mission_scope_file.read_bytes())
    groups = {
        f"football:{i}": [{"source": "football", "start": 0, "end": 256}]
        for i in range(primary_chunks)
    }
    groups["harness:0"] = [{"source": "harness", "start": 0, "end": 256}]
    scope["protected_invariants"] = [
        value for value in scope["protected_invariants"] if not value.startswith(dispute.MARKER)
    ]
    scope["protected_invariants"].append(
        dispute.MARKER + json.dumps({"version": dispute.VERSION, "groups": groups})
    )
    args.mission_scope_file.write_text(json.dumps(scope))
    git(args.repo_root, "add", ".")
    git(args.repo_root, "commit", "-qm", "TEST_ONLY frozen cost scope")
    args.head_sha = git(args.repo_root, "rev-parse", "HEAD")
    manifest, bodies, _ = runner.build_plan(args)
    kinds = manifest["standalone"]["request_kinds"]
    assert sum(kind.startswith("qualification:") for kind in kinds) == 4
    assert sum(kind.startswith(("football:", "harness:")) for kind in kinds) == primary_chunks + 1
    assert sum(kind.startswith("dispute:") for kind in kinds) == primary_chunks + 2
    assert kinds.count("dispute:cross-group") == 1
    assert len(bodies) == posts + 4
    assert manifest["reserve_micro_cny"] == reserve
    assert manifest["reserve_capacity_units"] == posts * 1_056_768
    transport = DisputeTransport(args, finding=False)
    path = runner.run_review(
        args, transport=transport, grant=dispute_grant(args), registry=registry
    )
    receipt = json.loads(path.read_bytes())
    assert receipt["review_result"] == "PASS"
    assert receipt["provenance"]["financial_status"] == "UNKNOWN_PENDING_PROVIDER_SETTLEMENT"
    assert len(transport.calls) == posts + 4
    assert all(len(body) <= 40_000 for body in transport.calls)


@pytest.mark.parametrize("cap", [40_000_001, 50_000_000])
def test_cny_grant_cannot_spend_unallocated_safety_reserve(integrated, cap):
    args, registry = integrated
    grant = dispute_grant(args)
    grant["cap_micro_cny"] = cap
    transport = DisputeTransport(args)
    with pytest.raises(backend.DirectError, match="CNY_ORDINARY_DISPATCH_CEILING"):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert not transport.calls
    manifest, bodies, _ = runner.build_plan(args)
    manifest["execution_mode"] = "OFFLINE_FIXTURE"
    with pytest.raises(backend.DirectError, match="CNY_ORDINARY_DISPATCH_CEILING"):
        backend.validate_standalone_admission(manifest, bodies, grant, offline=True)


def test_cny_ordinary_ceiling_does_not_change_balance_or_resource_contract(integrated):
    args, _ = integrated
    manifest, bodies, _ = runner.build_plan(args)
    manifest["execution_mode"] = "OFFLINE_FIXTURE"
    grant = dispute_grant(args)
    grant["cap_micro_cny"] = 40_000_000
    backend.validate_standalone_admission(manifest, bodies, grant, offline=True)
    assert grant["balance_micro_cny"] == 50_000_000
    assert manifest["reserve_capacity_units"] == 23 * 1_056_768


def test_usage_above_estimate_stops_without_refund_or_replay(case):
    args, registry = case
    capacity_candidate(args, 2)

    class UnexpectedUsage(FakeTransport):
        def send(self, endpoint, body, secret):
            super().send(endpoint, body, secret)
            return response(
                body,
                usage={
                    "prompt_tokens": 40_004,
                    "completion_tokens": 10,
                    "total_tokens": 40_014,
                    "prompt_cache_hit_tokens": 0,
                    "prompt_cache_miss_tokens": 40_004,
                },
            )

    manifest, bodies, _ = runner.build_plan(args)
    grant = grant_for(args)
    transport = UnexpectedUsage()
    with pytest.raises(backend.DirectError, match="REQUEST_OUTCOME_UNKNOWN"):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert len(transport.calls) == 1 < len(bodies)
    journal = backend.Journal()
    try:
        assert (
            journal.db.execute("SELECT reserved FROM grants").fetchone()[0]
            == manifest["reserve_micro_usd"]
        )
    finally:
        journal.close()
    with pytest.raises(backend.DirectError, match="UNKNOWN_NO_REPLAY"):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert len(transport.calls) == 1


def offline_harness_root():
    return harness_source()


def task_grant(args, tmp_path):
    """真实共享 SQLite 与真实 V2 manifest；仅 HTTP Provider 使用 fixture。"""
    import importlib.util

    location = offline_harness_root() / "src/harness/factory_budget.py"
    spec = importlib.util.spec_from_file_location("offline_task_budget", location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    budget_type, policy, route, budget_digest = (
        module.TaskBudget,
        module.TASK_POLICY,
        module.TASK_ROUTE,
        module.budget_digest,
    )
    root = tmp_path / "controller-task-budget"
    root.mkdir(mode=0o700)
    approval = {
        "id": "explicit-user-task",
        "approval_reference": "TEST_ONLY_USER_INSTRUCTION",
        "task_sha256": "a" * 64,
        "route": route,
        "expires_at": 4102444800,
        "policy": policy,
        "stages": ["review"],
        "user_approved": True,
        "authority": str(root / "authority.sqlite"),
    }
    file = root / "approval.json"
    file.write_text(json.dumps(approval))
    file.chmod(0o600)
    path = root / "authority.sqlite"
    budget_type.initialize(path, file)
    authority = budget_type(path, approval["id"], approval["task_sha256"])
    manifest, _, _ = runner.build_plan(args)
    manifest["execution_mode"] = "OFFLINE_FIXTURE"
    grant = dispute_grant(args)
    grant["contract"] = "task-bound/dispute-v2/v1"
    direct = {
        "grant_id": grant["id"],
        "manifest_sha256": grant["plan_sha256"],
        "review_identity": manifest["review_identity"],
        "source": manifest["binding"],
        "price_sha256": manifest["standalone"]["price_sha256"],
        "toolchain": {
            "root": str(args.repo_root),
            "head": args.head_sha,
            "runtime_sha256": manifest["runtime_sha256"],
        },
    }
    binding = {"direct": direct}
    ticket = authority.claim(
        {"stage": "review", "lane": "second_reviewer", "round": 0, "step": 0},
        binding,
        manifest["reserve_micro_cny"],
        None,
    )
    assert ticket["binding_sha256"] == budget_digest(binding)
    grant["task_budget"] = {"ticket": ticket, "binding": binding}
    return grant, authority


def test_task_bound_full_v2_no_double_debit_and_permanent_claim(integrated, tmp_path):
    args, registry = integrated
    grant, authority = task_grant(args, tmp_path)
    try:
        transport = DisputeTransport(args, finding=False)
        receipt = runner.run_review(args, transport=transport, grant=grant, registry=registry)
        assert json.loads(receipt.read_bytes())["review_result"] == "PASS"
        assert len(transport.calls) == 27  # 23 POST + 4 GET;全部资格和 dispute。
        amount = authority.summary()["committed_micro_cny"]
        assert amount == grant["cap_micro_cny"]
        runner.run_review(
            args, transport=DisputeTransport(args, finding=False), grant=grant, registry=registry
        )
        assert authority.summary()["committed_micro_cny"] == amount
        mutated = deepcopy(grant)
        mutated["id"] = "new-grant-cannot-refresh-budget"
        with pytest.raises(backend.DirectError):
            runner.run_review(
                args, transport=DisputeTransport(args), grant=mutated, registry=registry
            )
    finally:
        authority.close()


@pytest.mark.parametrize("field", ["source", "toolchain", "price_sha256", "grant_id", "exposure"])
def test_task_bound_identity_cannot_rebind(integrated, tmp_path, field):
    args, registry = integrated
    grant, authority = task_grant(args, tmp_path)
    try:
        mutated = deepcopy(grant)
        if field == "exposure":
            mutated["accepted_account_exposure_micro_cny"] = 50_000_001
        else:
            mutated["task_budget"]["binding"]["direct"][field] = "wrong"
        transport = DisputeTransport(args)
        with pytest.raises(backend.DirectError):
            runner.run_review(args, transport=transport, grant=mutated, registry=registry)
        assert not transport.calls
    finally:
        authority.close()


def test_task_bound_timeout_holds_shared_money(integrated, tmp_path):
    args, registry = integrated
    grant, authority = task_grant(args, tmp_path)
    try:
        with pytest.raises(backend.DirectError):
            runner.run_review(
                args,
                transport=DisputeTransport(args, fail_stage="football:0"),
                grant=grant,
                registry=registry,
            )
        authority.finish(grant["task_budget"]["ticket"], "UNKNOWN", {"fixture": "timeout"})
        assert authority.summary()["committed_micro_cny"] == grant["cap_micro_cny"]
        transport = DisputeTransport(args)
        with pytest.raises(backend.DirectError):
            runner.run_review(args, transport=transport, grant=grant, registry=registry)
        assert not transport.calls
    finally:
        authority.close()


@pytest.mark.parametrize("fault", [None, "workspace", "plan", "account", "credits", "expiry"])
def test_task_canonical_plus_binding_fail_closed_without_inference(tmp_path, monkeypatch, fault):
    import hashlib

    from scripts.devops import codex_reviewer_isolation as isolation
    from scripts.devops.codex_review_provenance import ReviewReceiptError

    home = tmp_path / "fake-home"
    binding = {
        "codex_home": str(home),
        "expires_at": 4102444800,
        "workspace_id": "approved-workspace",
        "account_sha256": hashlib.sha256(b"fixture@example.invalid").hexdigest(),
        "user_confirmed_no_credits_no_topup": True,
    }
    account = {
        "type": "chatgpt",
        "planType": "plus",
        "email": "fixture@example.invalid",
        "workspaceId": "approved-workspace",
    }
    if fault == "workspace":
        account.pop("workspaceId")
    elif fault == "plan":
        account["planType"] = "business"
    elif fault == "account":
        account["email"] = "different@example.invalid"
    elif fault == "credits":
        binding["user_confirmed_no_credits_no_topup"] = False
    elif fault == "expiry":
        binding["expires_at"] = 1
    path = tmp_path / "nonsecret-billing.json"
    path.write_text(json.dumps(binding))
    path.chmod(0o600)
    monkeypatch.setattr(isolation, "CANONICAL_CODEX_HOME", home)
    monkeypatch.setattr(isolation, "_task_billing_account", lambda *_a, **_kw: account)
    monkeypatch.setattr(
        isolation.subprocess, "Popen", lambda *_a, **_kw: pytest.fail("real Codex forbidden")
    )
    if fault:
        with pytest.raises(ReviewReceiptError, match="BINDING_PENDING"):
            isolation._verify_task_plus_binding(path, Path("/never-start-codex"), {})
    else:
        isolation._verify_task_plus_binding(path, Path("/never-start-codex"), {})
