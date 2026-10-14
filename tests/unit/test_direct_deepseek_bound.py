"""完整 Direct runner 离线测试；fixture receipt 绝不能充当生产审批。"""

from __future__ import annotations

from argparse import Namespace
from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
from unittest.mock import Mock

import pytest

from scripts.devops import direct_deepseek_independent_review as runner
from scripts.devops import independent_review_receipt as receipts
from scripts.devops.deepseek_receipt_evidence import _deepseek_receipt_evidence
from scripts.devops.independent_review_backends import direct_deepseek as backend
from scripts.devops.independent_review_protocol import (
    IndependentReviewProtocolError,
    canonical_json,
)
from tests.helpers.direct_harness_source import (
    portable_harness as portable_harness,  # noqa: PLC0414
)

EXPECTED_CHUNK_MICROUSD = 21832
EXPECTED_MAX_OUTPUT = 8192
EXPECTED_REQUEST_BODY_BYTES = 40_000
EXPECTED_STANDALONE_MAX_HTTP = 18
ROOT = Path(__file__).resolve().parents[2]


def git(root, *argv):
    return subprocess.check_output(["git", *argv], cwd=root, text=True).strip()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError("tests must not connect to Provider")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "STATE_DIR", tmp_path / "authority")
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Offline Test")
    git(root, "config", "user.email", "offline@example.invalid")
    scope = json.loads(
        (
            ROOT / "docs/agentic/missions/CLAUDE_CODE_DEEPSEEK_INDEPENDENT_REVIEW_BACKEND.json"
        ).read_text()
    )
    scope["mission_id"] = "DIRECT_BOUND_TEST"
    scope["workflow_class"] = "CRITICAL"
    scope["authorized_paths"] = ["example.py", "docs/agentic/missions/DIRECT_BOUND_TEST.json"]
    scope_file = root / "docs/agentic/missions/DIRECT_BOUND_TEST.json"
    scope_file.parent.mkdir(parents=True)
    scope_file.write_text(json.dumps(scope))
    (root / "example.py").write_text("old\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    (root / "example.py").write_text("new\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "candidate")
    args = Namespace(
        repo_root=root,
        base_sha=base,
        head_sha=git(root, "rev-parse", "HEAD"),
        mission_id=scope["mission_id"],
        mission_scope_file=scope_file,
        evidence_dir=tmp_path / "evidence",
    )
    registry = receipts.load_backend_registry(
        ROOT / "docs/agentic/independent_review_backends.json"
    )
    # 仅本测试内存 registry；不修改 production approval 文件。
    registry[backend.BACKEND_ID]["status"] = "active"
    return args, registry


def grant_for(args):
    manifest, _, _ = runner.build_plan(args)
    return {
        "id": "offline-grant",
        "review_identity": manifest["review_identity"],
        "policy_sha256": manifest["policy_sha256"],
        "runtime_sha256": manifest["runtime_sha256"],
        "cap_micro_usd": manifest["reserve_micro_usd"],
    }


def response(_body, **changes):
    result = {
        "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
        "review_result": "PASS",
        "findings": [],
    }
    value = {
        "model": backend.MODEL,
        "id": "offline-response-only",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": json.dumps(result)},
            }
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
            "prompt_cache_hit_tokens": 0,
            "prompt_cache_miss_tokens": 20,
        },
    }
    value.update(changes)
    return canonical_json(value)


class FakeTransport:
    offline_fixture = True

    def __init__(self, failure=None):
        self.calls = []
        self.failure = failure

    def send(self, endpoint, body, secret):
        assert endpoint == backend.ENDPOINT
        # 使用另一个连接证明事务已提交且整轮预留已存在。
        db = sqlite3.connect(backend.STATE_DIR / "requests.sqlite3")
        try:
            requests = db.execute("SELECT idx,status FROM requests ORDER BY idx").fetchall()
            assert any(state == "UNKNOWN" for _, state in requests)
            assert db.execute("SELECT reserved FROM grants").fetchone()[0] > 0
            assert len(requests) >= len(self.calls) + 1
        finally:
            db.close()
        self.calls.append(body)
        assert secret not in body.decode()
        if self.failure:
            raise self.failure
        return response(body)


def test_single_full_path_fixture_cannot_be_production_approval(case):
    args, registry = case
    transport = FakeTransport()
    path = runner.run_review(args, transport=transport, grant=grant_for(args), registry=registry)
    receipt = json.loads(path.read_bytes())
    assert len(transport.calls) == 1
    assert receipt["review_backend"] == backend.BACKEND_ID
    assert receipt["review_harness"] != "claude-code"
    assert receipt["provenance"]["execution_mode"] == "OFFLINE_FIXTURE"
    body = json.loads(transport.calls[0])
    assert body["max_tokens"] == backend.POLICY["max_output"]
    assert body["thinking"] == {"type": "disabled"}
    assert body["reasoning_effort"] == "none"
    assert not body.get("tools")
    evidence = _deepseek_receipt_evidence(
        path,
        repo_root=args.repo_root,
        expected_base=args.base_sha,
        expected_head=args.head_sha,
        expected_mission_id=args.mission_id,
        expected_scope_hash=receipt["mission_scope_sha256"],
    )
    assert not evidence.trusted
    assert not list(args.evidence_dir.glob("*worktree*"))


def test_multiple_chunks_resume_uses_completed_raw_without_http(case):
    args, registry = case
    (args.repo_root / "example.py").write_text("change\n" * 12000)
    git(args.repo_root, "add", ".")
    git(args.repo_root, "commit", "-qm", "large candidate")
    args.head_sha = git(args.repo_root, "rev-parse", "HEAD")
    manifest, bodies, _ = runner.build_plan(args)
    assert len(bodies) > 1
    first = FakeTransport()
    runner.run_review(args, transport=first, grant=grant_for(args), registry=registry)
    assert len(first.calls) == manifest["max_http_attempts"]
    second = FakeTransport()
    runner.run_review(args, transport=second, grant=grant_for(args), registry=registry)
    assert second.calls == []
    journal = backend.Journal()
    assert (
        journal.db.execute("SELECT reserved FROM grants").fetchone()[0]
        == manifest["reserve_micro_usd"]
    )
    with pytest.raises(backend.DirectError):
        journal.send(manifest, len(bodies), second, "fake-key")
    journal.close()


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError("secret"),
        ConnectionResetError("secret"),
        KeyboardInterrupt("secret"),
        RuntimeError("response lost"),
    ],
)
def test_unknown_cannot_resume_or_obtain_new_grant(case, failure):
    args, registry = case
    grant = grant_for(args)
    first = FakeTransport(failure)
    with pytest.raises(backend.DirectError, match="REQUEST_OUTCOME_UNKNOWN"):
        runner.run_review(args, transport=first, grant=grant, registry=registry)
    second = FakeTransport()
    grant["id"] = "new-authorization"
    grant["cap_micro_usd"] *= 100
    with pytest.raises(backend.DirectError, match="UNKNOWN_NO_REPLAY"):
        runner.run_review(args, transport=second, grant=grant, registry=registry)
    assert len(first.calls) == 1
    assert second.calls == []
    assert not list(args.evidence_dir.glob("*-receipt.json"))
    journal = backend.Journal()
    assert journal.db.execute("SELECT status FROM requests").fetchone()[0] == "UNKNOWN"
    assert journal.db.execute("SELECT reserved FROM grants").fetchone()[0] > 0
    journal.close()


def test_insufficient_budget_never_sends(case):
    args, registry = case
    grant = grant_for(args)
    grant["cap_micro_usd"] -= 1
    transport = FakeTransport()
    with pytest.raises(backend.DirectError, match="INSUFFICIENT_BUDGET"):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert transport.calls == []


def test_crash_after_reservation_before_send_can_restore_exact_identity(case):
    args, registry = case
    manifest, bodies, _ = runner.build_plan(args)
    manifest["execution_mode"] = "OFFLINE_FIXTURE"
    journal = backend.Journal()
    journal.reserve(manifest, bodies, grant_for(args))
    journal.close()
    transport = FakeTransport()
    runner.run_review(args, transport=transport, grant=grant_for(args), registry=registry)
    assert len(transport.calls) == 1


@pytest.mark.parametrize("field", ["policy_sha256", "runtime_sha256", "review_identity"])
def test_rebind_grant_or_manifest_rejected_before_send(case, field):
    args, registry = case
    grant = grant_for(args)
    grant[field] = "0" * 64
    transport = FakeTransport()
    with pytest.raises(backend.DirectError, match="AUTHORIZATION_BINDING"):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert transport.calls == []


def test_request_count_capacity_and_complete_payload(case, monkeypatch):
    args, _ = case
    manifest, bodies, _ = runner.build_plan(args)
    journal = backend.Journal()
    bad = deepcopy(manifest)
    bad["request_digests"] = [b"x"] * 65
    with pytest.raises(backend.DirectError, match="MANIFEST_POLICY"):
        journal.reserve(bad, bodies * 65, grant_for(args))
    journal.close()
    for limit in (0, True, backend.POLICY["max_output"] + 1, 393217):
        with pytest.raises(backend.DirectError):
            backend.payload("hello", limit)
    with pytest.raises(backend.DirectError):
        backend.payload("x" * 40001)
    body = json.loads(bodies[0])
    body["tools"] = [{"type": "function"}]
    with pytest.raises(backend.DirectError):
        backend.request_cost(canonical_json(body))
    monkeypatch.setitem(backend.POLICY, "version", "price-or-alias-changed")
    with pytest.raises(backend.DirectError, match="POLICY_CHANGED"):
        backend.request_cost(bodies[0])


def test_default_registry_and_transport_always_block_live(case):
    args, _ = case
    with pytest.raises(backend.DirectError, match="UNAPPROVED_EXECUTOR"):
        runner.run_review(args, transport=FakeTransport(), grant=grant_for(args))
    with pytest.raises(backend.DirectError, match="NO_GO_FOR_LIVE"):
        backend.HttpsTransport().send(backend.ENDPOINT, backend.payload("hello"), "never-real")


@pytest.mark.parametrize("status", [301, 302, 307, 308, 429, 500])
def test_https_never_retries_redirects_or_falls_back(monkeypatch, status):
    connection = Mock()
    connection.getresponse.return_value.status = status
    constructor = Mock(return_value=connection)
    monkeypatch.setattr(backend, "LIVE_EXECUTION_APPROVED", True)  # fake HTTPS class only
    monkeypatch.setattr(backend.http.client, "HTTPSConnection", constructor)
    with pytest.raises(backend.DirectError):
        backend.HttpsTransport().send(backend.ENDPOINT, backend.payload("hello"), "not-a-key")
    assert constructor.call_count == connection.request.call_count == 1
    assert connection.request.call_args.args[:2] == ("POST", "/chat/completions")
    assert connection.close.call_count == 1
    with pytest.raises(backend.DirectError, match="ENDPOINT_POLICY"):
        backend.HttpsTransport().send("http://evil.invalid", b"{}", "not-a-key")
    assert constructor.call_count == 1


@pytest.mark.parametrize("corruption", ["model", "capacity", "reasoning", "length", "secret"])
def test_invalid_provider_output_is_unknown_no_format_repair(case, corruption):
    args, registry = case

    class Bad(FakeTransport):
        def send(self, endpoint, body, secret):
            raw = json.loads(super().send(endpoint, body, secret))
            if corruption == "model":
                raw["model"] = "another-model"
            elif corruption == "capacity":
                raw["usage"]["completion_tokens"] = 999999
            elif corruption == "reasoning":
                raw["choices"][0]["message"]["reasoning_content"] = "unexpected thinking"
            elif corruption == "length":
                raw["choices"][0]["finish_reason"] = "length"
            else:
                raw["choices"][0]["message"]["content"] = secret
                return (
                    json.dumps(raw, ensure_ascii=True).replace("OFFLINE", "\\u004fFFLINE").encode()
                )
            return canonical_json(raw)

    transport = Bad()
    with pytest.raises(backend.DirectError, match="REQUEST_OUTCOME_UNKNOWN") as error:
        runner.run_review(args, transport=transport, grant=grant_for(args), registry=registry)
    assert "OFFLINE-FAKE-KEY" not in str(error.value)
    assert len(transport.calls) == 1
    assert not list(args.evidence_dir.glob("*-raw.json"))


def test_receipt_runtime_source_head_and_cli_identity_fail_closed(case, monkeypatch):
    args, registry = case
    observed = []
    original = receipts.validate_receipt

    def capture(receipt, **kwargs):
        observed.append((deepcopy(receipt), kwargs["evidence_context"]))
        return original(receipt, **kwargs)

    monkeypatch.setattr(receipts, "validate_receipt", capture)
    runner.run_review(args, transport=FakeTransport(), grant=grant_for(args), registry=registry)
    receipt, context = observed[0]
    assert original(receipt, registry=registry, evidence_context=context)["review_result"] == "PASS"
    for field, changed in (
        ("head_sha", "0" * 40),
        ("diff_sha256", "0" * 64),
        ("mission_scope_sha256", "0" * 64),
        ("requested_model", "wrong"),
        ("review_backend", "claude-code-deepseek"),
        ("review_harness", "claude-code"),
    ):
        bad = deepcopy(receipt)
        bad[field] = changed
        bad["integrity"]["receipt_payload_sha256"] = receipts.receipt_payload_sha256(bad)
        with pytest.raises(IndependentReviewProtocolError):
            original(bad, registry=registry, evidence_context=context)
    bad = deepcopy(receipt)
    bad["provenance"]["runner_runtime_sha256"] = "0" * 64
    bad["integrity"]["receipt_payload_sha256"] = receipts.receipt_payload_sha256(bad)
    with pytest.raises(IndependentReviewProtocolError):
        original(bad, registry=registry, evidence_context=context)
    reserved = receipts.load_backend_registry(
        ROOT / "docs/agentic/independent_review_backends.json"
    )
    with pytest.raises(IndependentReviewProtocolError, match="not active"):
        original(receipt, registry=reserved, evidence_context=context)


def test_concurrent_process_cannot_send_same_request_twice(case):
    args, registry = case

    class Concurrent(FakeTransport):
        def send(self, endpoint, body, secret):
            manifest, _, _ = runner.build_plan(args)
            manifest["execution_mode"] = "OFFLINE_FIXTURE"
            competitor = backend.Journal()
            try:
                with pytest.raises(backend.DirectError, match="SEND_BINDING_OR_REPLAY"):
                    competitor.send(manifest, 0, FakeTransport(), secret)
            finally:
                competitor.close()
            return super().send(endpoint, body, secret)

    transport = Concurrent()
    runner.run_review(args, transport=transport, grant=grant_for(args), registry=registry)
    assert len(transport.calls) == 1


def test_changed_price_between_reserve_and_send_is_rejected(case, monkeypatch):
    args, _ = case
    manifest, bodies, _ = runner.build_plan(args)
    journal = backend.Journal()
    journal.reserve(manifest, bodies, grant_for(args))
    transport = FakeTransport()
    monkeypatch.setitem(backend.POLICY, "input_micro_usd_per_million", 600000)
    with pytest.raises(backend.DirectError, match="SEND_BINDING_OR_REPLAY"):
        journal.send(manifest, 0, transport, "fake-key")
    assert transport.calls == []
    assert journal.db.execute("SELECT status FROM requests").fetchone()[0] == "RESERVED"
    journal.close()


def test_completed_fixture_mode_cannot_be_rebound_to_live_or_new_grant(case):
    args, registry = case
    grant = grant_for(args)
    runner.run_review(args, transport=FakeTransport(), grant=grant, registry=registry)
    manifest, bodies, _ = runner.build_plan(args)  # DIRECT_HTTPS 不能复用 OFFLINE_FIXTURE 记录。
    journal = backend.Journal()
    with pytest.raises(backend.DirectError, match="REVIEW_REBINDING"):
        journal.reserve(manifest, bodies, grant)
    manifest["execution_mode"] = "OFFLINE_FIXTURE"
    increased = {**grant, "cap_micro_usd": grant["cap_micro_usd"] + 1}
    with pytest.raises(backend.DirectError, match="AUTHORIZATION_CHANGED"):
        journal.reserve(manifest, bodies, increased)
    journal.close()


def test_engineering_fee_estimate_is_separate_from_context_at_peak_miss(case):
    args, _ = case
    manifest, bodies, _ = runner.build_plan(args)
    assert (
        backend.request_cost(bodies[0]) == EXPECTED_CHUNK_MICROUSD
    )  # microUSD，向上取整；不是无条件 Provider 美元硬帽。
    assert manifest["reserve_micro_usd"] == len(bodies) * EXPECTED_CHUNK_MICROUSD
    assert manifest["cost_status"] == "CONDITIONAL_COST_BOUND"
    assert backend.POLICY["context_capacity"] == 1_048_576  # noqa: PLR2004
    assert backend.POLICY["budget_estimated_input_tokens"] == 40_003  # noqa: PLR2004
    assert backend.POLICY["budget_estimate_kind"] == "ENGINEERING_ESTIMATE_NOT_PROVIDER_CAP"


def test_real_https_boundary_one_successful_post_with_provider_output_cap(monkeypatch):
    body = backend.payload("offline JSON review")
    connection = Mock()
    connection.getresponse.return_value.status = 200
    connection.getresponse.return_value.read.return_value = response(body)
    constructor = Mock(return_value=connection)
    monkeypatch.setattr(backend, "LIVE_EXECUTION_APPROVED", True)
    monkeypatch.setattr(backend.http.client, "HTTPSConnection", constructor)
    raw = backend.HttpsTransport().send(backend.ENDPOINT, body, "offline-test-key")
    assert backend.decode(raw, body)["review_result"] == "PASS"
    assert constructor.call_count == 1
    assert connection.request.call_count == 1
    actual = json.loads(connection.request.call_args.kwargs["body"])
    assert actual["max_tokens"] == EXPECTED_MAX_OUTPUT
    assert actual["stream"] is False
    assert constructor.call_args.args == ("api.deepseek.com", 443)


def test_full_runner_through_https_boundary_uses_only_fake_connection(case, monkeypatch):
    args, registry = case
    observed = []
    connection = Mock()

    def request(_method, _path, *, body, headers):
        db = sqlite3.connect(backend.STATE_DIR / "requests.sqlite3")
        assert db.execute("SELECT status FROM requests").fetchone()[0] == "UNKNOWN"
        db.close()
        observed.append(body)
        assert headers["Authorization"].startswith("Bearer OFFLINE-")

    connection.request.side_effect = request
    connection.getresponse.return_value.status = 200
    connection.getresponse.return_value.read.side_effect = lambda _n: response(observed[-1])
    constructor = Mock(return_value=connection)
    monkeypatch.setattr(backend, "LIVE_EXECUTION_APPROVED", True)
    monkeypatch.setattr(backend.http.client, "HTTPSConnection", constructor)

    class FixtureHttps(backend.HttpsTransport):
        offline_fixture = True

    path = runner.run_review(
        args, transport=FixtureHttps(), grant=grant_for(args), registry=registry
    )
    assert json.loads(path.read_bytes())["review_result"] == "PASS"
    assert constructor.call_count == 1
    assert connection.request.call_count == 1
    assert json.loads(observed[0])["max_tokens"] == EXPECTED_MAX_OUTPUT


def test_partial_multi_chunk_recovery_only_sends_never_sent_rows(case):
    args, registry = case
    (args.repo_root / "example.py").write_text("change\n" * 12000)
    git(args.repo_root, "add", ".")
    git(args.repo_root, "commit", "-qm", "multi chunk candidate")
    args.head_sha = git(args.repo_root, "rev-parse", "HEAD")
    manifest, bodies, _ = runner.build_plan(args)
    manifest["execution_mode"] = "OFFLINE_FIXTURE"
    journal = backend.Journal()
    journal.reserve(manifest, bodies, grant_for(args))
    journal.send(manifest, 0, FakeTransport(), "offline-key")
    journal.close()  # 模拟第一个成功 chunk 与第二个发送动作之间中断。
    resumed = FakeTransport()
    runner.run_review(args, transport=resumed, grant=grant_for(args), registry=registry)
    assert len(resumed.calls) == len(bodies) - 1


# TEST_ONLY 价格完全为构造夹具，不是当前人民币官方报价。
def priced_case(args, unit="USD", target=None):
    target = target or backend.price_url(unit)
    symbol, miss, output = ("$", "0.30", "1.20") if unit == "USD" else ("CNY", "2.00", "8.00")
    rows = [
        f"<tr><td>MODEL</td><td>{backend.MODEL}</td></tr>",
        f"<tr><td>MODEL VERSION</td><td>{backend.POLICY['model_version']}</td></tr>",
    ]
    for category, value in [
        ("INPUT TOKENS (CACHE HIT)", "0.001"),
        ("INPUT TOKENS (CACHE MISS)", miss),
        ("OUTPUT TOKENS", output),
    ]:
        rows.extend(
            f"<tr><td>1M {category}</td><td>{tier}</td><td>{symbol}{value}</td></tr>"
            for tier in ("OFF-PEAK", "PEAK")
        )
    args.price_raw = (
        "<!-- TEST_ONLY NEVER PRODUCTION PRICE --><table>" + "".join(rows) + "</table>"
    ).encode()
    args.currency = unit
    args.price_sha256 = backend.sha256_bytes(args.price_raw)
    args.price_snapshot = backend.parse_price_snapshot(
        args.price_raw, source_url=target, unit=unit, observed_at=datetime.now(UTC).isoformat()
    )
    return args


@pytest.fixture
def capacity_case(request):
    from tests.unit.test_direct_deepseek_standalone import standalone_case  # noqa: PLC0415

    return standalone_case.__wrapped__(request)


def capacity_candidate(args, primary_chunks):
    # 保持实际 canonical 分块规则；只在隔离 Git fixture 增加完整源码 diff。
    target = (primary_chunks - 1) * 32_000 + 12_000
    (args.repo_root / "example.py").write_text("source line\n" * (target // 13))
    git(args.repo_root, "add", ".")
    git(args.repo_root, "commit", "-qm", "TEST_ONLY capacity source")
    args.head_sha = git(args.repo_root, "rev-parse", "HEAD")


@pytest.mark.parametrize("primary_chunks", [7, 8])
@pytest.mark.parametrize("unit", ["USD", "CNY"])
def test_capacity_whole_round_real_runner_and_validator(capacity_case, primary_chunks, unit):
    from tests.unit.test_direct_deepseek_standalone import (  # noqa: PLC0415
        StandaloneTransport,
        standalone_grant,
    )

    args, registry = capacity_case
    capacity_candidate(args, primary_chunks)
    priced_case(args, unit)
    manifest, bodies, chunks = runner.build_plan(args)
    assert len(chunks.chunks) == primary_chunks
    assert len(manifest["companion_chunk_manifest"]["chunks"]) == 1
    assert len(bodies) == primary_chunks + 9
    assert manifest["reserve_capacity_units"] == (primary_chunks + 5) * 1_056_768
    assert manifest["standalone"]["request_kinds"] == [
        "price",
        "models",
        "balance_start",
        *[
            "qualification:" + name
            for name in ("clean", "single_blocker", "source_based_dispute", "multiple_blockers")
        ],
        *["football:" + str(i) for i in range(primary_chunks)],
        "harness:0",
        "balance_end",
    ]
    post_bodies = [b for b in bodies if json.loads(b).get("method") != "GET"]
    assert len(post_bodies) == primary_chunks + 5
    assert all(
        len(b) <= EXPECTED_REQUEST_BODY_BYTES and json.loads(b)["max_tokens"] == EXPECTED_MAX_OUTPUT
        for b in post_bodies
    )
    diff = subprocess.check_output(
        ["git", "diff", "--binary", "--no-ext-diff", args.base_sha + "..." + args.head_sha],
        cwd=args.repo_root,
    )
    sources = b"".join(
        json.loads(b)["messages"][1]["content"].split("Canonical chunk diff:\n", 1)[1].encode()
        for b in bodies[7 : 7 + primary_chunks]
    )
    assert sources == diff
    transport = StandaloneTransport(args)
    grant = standalone_grant(args)
    assert grant["http_count"] == len(bodies) + 1 <= EXPECTED_STANDALONE_MAX_HTTP
    path = runner.run_review(args, transport=transport, grant=grant, registry=registry)
    receipt = json.loads(path.read_bytes())  # runner 使用真实 Direct provenance/receipt validator。
    assert receipt["review_result"] == "PASS"
    assert receipt["provenance"]["execution_mode"] == "OFFLINE_FIXTURE"
    assert receipt["provenance"]["financial_status"] == "UNKNOWN_PENDING_PROVIDER_SETTLEMENT"
    assert transport.calls == bodies
    journal = backend.Journal()
    assert journal.db.execute("SELECT COUNT(*) FROM admissions").fetchone()[0] == 1
    assert (
        journal.db.execute("SELECT reserved FROM grants").fetchone()[0]
        == manifest[backend.money_key("reserve", unit)]
    )
    journal.close()


def test_capacity_fourteen_posts_canonical_planner_refused(capacity_case):
    args, _ = capacity_case
    capacity_candidate(args, 9)
    priced_case(args, "CNY")
    with pytest.raises(backend.DirectError, match="STANDALONE_REVIEW_CAPACITY"):
        runner.build_plan(args)


@pytest.mark.parametrize(
    "fault",
    [
        "purpose",
        "qualification_missing",
        "companion_missing",
        "body_overflow",
        "capacity",
        "currency",
        "budget",
        "http_count",
        "post_count",
    ],
)
def test_capacity_fixed_plan_tampering_refused(capacity_case, fault):
    from tests.unit.test_direct_deepseek_standalone import standalone_grant  # noqa: PLC0415

    args, _ = capacity_case
    capacity_candidate(args, 8)
    priced_case(args, "CNY")
    manifest, bodies, _ = runner.build_plan(args)
    manifest["execution_mode"] = "OFFLINE_FIXTURE"
    grant = standalone_grant(args)
    if fault == "purpose":
        bodies[0] = canonical_json(
            {"method": "GET", "kind": "unapproved", "endpoint": backend.ENDPOINT}
        )
    elif fault == "qualification_missing":
        del bodies[3]
    elif fault == "companion_missing":
        del bodies[-2]
    elif fault == "body_overflow":
        with pytest.raises(backend.DirectError, match="PROMPT_BYTE_CAPACITY"):
            backend.payload("x" * 40_001)
        with pytest.raises(backend.DirectError, match="REQUEST_BODY_CAPACITY"):
            backend.payload("x" * EXPECTED_REQUEST_BODY_BYTES)
        return
    else:
        key, value = {
            "capacity": ("capacity_units", 12 * 1_056_768),
            "currency": ("currency", "USD"),
            "budget": ("cap_micro_cny", 1),
            "http_count": ("http_count", 19),
            "post_count": ("post_count", 14),
        }[fault]
        grant[key] = value
    journal = backend.Journal()
    with pytest.raises(backend.DirectError):
        journal.reserve(manifest, bodies, grant)
    assert journal.db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 0
    journal.close()


def test_capacity_nineteen_physical_http_even_rebound_refused(capacity_case):
    from tests.unit.test_direct_deepseek_standalone import standalone_grant  # noqa: PLC0415

    args, _ = capacity_case
    capacity_candidate(args, 8)
    priced_case(args, "CNY")
    manifest, bodies, _ = runner.build_plan(args)
    manifest["execution_mode"] = "OFFLINE_FIXTURE"
    grant = standalone_grant(args)
    bodies.append(bodies[0])  # 18 logical + 1 redirect；即使重绑身份，也不得扩容。
    manifest["request_count"] = manifest["max_http_attempts"] = len(bodies)
    manifest["request_digests"] = [backend.sha256_bytes(b) for b in bodies]
    manifest["review_identity"] = backend.sha256_bytes(canonical_json(manifest))
    grant.update(
        review_identity=manifest["review_identity"],
        http_count=19,
        plan_sha256=backend.sha256_bytes(canonical_json(manifest)),
    )
    journal = backend.Journal()
    with pytest.raises(backend.DirectError, match="STANDALONE_AUTHORIZATION_DENIED"):
        journal.reserve(manifest, bodies, grant)
    journal.close()


def test_capacity_thirteen_posts_unknown_never_replayed(capacity_case):
    from tests.unit.test_direct_deepseek_standalone import (  # noqa: PLC0415
        StandaloneTransport,
        standalone_grant,
    )

    args, registry = capacity_case
    capacity_candidate(args, 8)
    priced_case(args, "CNY")
    grant = standalone_grant(args)
    failed = StandaloneTransport(args, fail_at=7)
    with pytest.raises(backend.DirectError):
        runner.run_review(args, transport=failed, grant=grant, registry=registry)
    assert len(failed.calls) == failed.fail_at + 1
    resumed = StandaloneTransport(args)
    with pytest.raises(backend.DirectError, match="UNKNOWN_NO_REPLAY"):
        runner.run_review(args, transport=resumed, grant=grant, registry=registry)
    assert resumed.calls == []
    assert backend.LIVE_EXECUTION_APPROVED is False
    journal = backend.Journal()
    assert journal.db.execute("SELECT reserved FROM grants").fetchone()[0] == grant["cap_micro_cny"]
    journal.close()


@pytest.mark.parametrize(
    "fault", [None, "model", "version", "currency", "url", "missing", "scale", "price", "source"]
)
def test_chinese_native_price_real_admission_and_identity(capacity_case, fault):
    from tests.unit.test_direct_deepseek_standalone import (  # noqa: PLC0415
        StandaloneTransport,
        standalone_grant,
    )

    args, registry = capacity_case
    raw = (
        "<!-- TEST_ONLY: structure of official Chinese table; not live pricing -->"
        f"<table><tr><td>模型</td><td>{backend.MODEL} (1)</td><td>other-model</td></tr>"
        f"<tr><td>模型版本</td><td>{backend.POLICY['model_version']}</td><td>other-version</td></tr>"
        "<tr><td rowspan='6'>价格</td><td rowspan='2'>百万tokens输入（缓存命中）</td>"
        "<td>空闲时段</td><td>0.01元</td><td>99元</td></tr>"
        "<tr><td>高峰时段</td><td>0.02元</td><td>99元</td></tr>"
        "<tr><td rowspan='2'>百万tokens输入（缓存未命中）</td><td>空闲时段</td>"
        "<td>1元</td><td>99元</td></tr><tr><td>高峰时段</td><td>2元</td><td>99元</td></tr>"
        "<tr><td rowspan='2'>百万tokens输出</td><td>空闲时段</td><td>4元</td><td>99元</td></tr>"
        "<tr><td>高峰时段</td><td>8元</td><td>99元</td></tr></table>"
    )
    url = backend.price_url("CNY")
    if fault in {"model", "version", "currency", "missing", "scale"}:
        old, new = {
            "model": (backend.MODEL, "wrong-model"),
            "version": (backend.POLICY["model_version"], "wrong-version"),
            "currency": ("元", "USD"),
            "missing": ("空闲时段", "未知时段"),
            "scale": ("百万", "千"),
        }[fault]
        raw = raw.replace(old, new)
    elif fault == "url":
        url = backend.PRICE_URL
    args.currency, args.price_raw = "CNY", raw.encode()
    args.price_sha256 = backend.sha256_bytes(args.price_raw)
    if fault in {"model", "version", "currency", "url", "missing", "scale"}:
        with pytest.raises(backend.DirectError):
            backend.parse_price_snapshot(
                args.price_raw,
                source_url=url,
                unit="CNY",
                observed_at=datetime.now(UTC).isoformat(),
            )
        return
    args.price_snapshot = backend.parse_price_snapshot(
        args.price_raw, source_url=url, unit="CNY", observed_at=datetime.now(UTC).isoformat()
    )
    backend.validate_price_snapshot(args.price_snapshot, "CNY", args.price_sha256)
    _, bodies, _ = runner.build_plan(args)
    assert json.loads(bodies[0])["endpoint"] == url
    assert args.price_snapshot["rates_micro_per_million"]["peak:output"] == backend.money_amount(
        "8"
    )
    grant, transport = standalone_grant(args), StandaloneTransport(args)
    if fault:
        if fault == "price":
            args.price_snapshot["rates_micro_per_million"]["peak:output"] += 1
        else:
            args.price_snapshot["source_url"] += "/"
        with pytest.raises(backend.DirectError):
            runner.run_review(args, transport=transport, grant=grant, registry=registry)
        assert transport.calls == []
    else:
        path = runner.run_review(args, transport=transport, grant=grant, registry=registry)
        assert json.loads(path.read_bytes())["review_result"] == "PASS"
        assert transport.calls == bodies
        assert backend.LIVE_EXECUTION_APPROVED is False
