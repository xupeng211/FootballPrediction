"""Standalone 原 Direct runner/Journal 的断网离线准入与故障注入。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
import json
import subprocess

import pytest

from scripts.devops import direct_deepseek_independent_review as runner
from scripts.devops import direct_deepseek_receipt_evidence as consumer
from scripts.devops import independent_review_receipt as receipts
from scripts.devops.deepseek_receipt_evidence import _deepseek_receipt_evidence
from scripts.devops.independent_review_backends import direct_deepseek as backend
from scripts.devops.independent_review_protocol import (
    IndependentReviewProtocolError,
    canonical_json,
)
from scripts.devops.review_policy import ReviewEvidence
from tests.helpers.direct_harness_source import (
    portable_harness as portable_harness,  # noqa: PLC0414
)
from tests.unit.test_direct_deepseek_bound import (
    EXPECTED_CHUNK_MICROUSD,
    FakeTransport,
    case,  # noqa: F401
    git,
    no_network,  # noqa: F401
    priced_case,
    response,
)

EXPECTED_POSTS = 6
EXPECTED_HTTP = 10


@pytest.fixture
def standalone_case(request):
    args, registry = request.getfixturevalue("case")
    scope = json.loads(args.mission_scope_file.read_text())
    config = dict(request.getfixturevalue("portable_harness"))
    config["football_base"] = args.base_sha
    config["football_ancestor"] = args.base_sha
    scope["protected_invariants"] = [runner.STANDALONE_MARKER + json.dumps(config)]
    args.mission_scope_file.write_text(json.dumps(scope))
    git(
        args.repo_root,
        "config",
        "remote.origin.url",
        "git@github.com:xupeng211/FootballPrediction.git",
    )
    git(args.repo_root, "add", ".")
    git(args.repo_root, "commit", "-qm", "offline standalone scope")
    args.head_sha = git(args.repo_root, "rev-parse", "HEAD")
    args.execution_id = "offline-execution-never-approved"
    args.credential_sha256 = backend.sha256_bytes(b"OFFLINE-FAKE-KEY-NEVER-A-PROVIDER-CREDENTIAL")
    args.price_sha256 = backend.sha256_bytes(b"OFFLINE OFFICIAL PRICE FIXTURE")
    registry[backend.BACKEND_ID]["status"] = "reserved"
    return args, registry


def standalone_grant(args):
    manifest, bodies, _ = runner.build_plan(args)
    unit = backend.currency(manifest)
    grant = {
        "id": "offline-grant",
        **{k: manifest[k] for k in ("review_identity", "policy_sha256", "runtime_sha256")},
        backend.money_key("cap", unit): manifest[backend.money_key("reserve", unit)],
    }
    grant.update(
        {
            "contract": "standalone-informed-risk/v1",
            "mode": "OFFLINE_FIXTURE",
            "plan_sha256": backend.sha256_bytes(
                canonical_json({**manifest, "execution_mode": "OFFLINE_FIXTURE"})
            ),
            "execution_id": args.execution_id,
            "expires_at": "2099-01-01T00:00:00+00:00",
            "currency": unit,
            "accepted_residual_billing_risk": True,
            "standalone_authority_approved": True,
            "post_count": sum(json.loads(b).get("method") != "GET" for b in bodies),
            "http_count": len(bodies) + manifest["standalone"].get("price_redirect_limit", 0),
            "capacity_units": manifest["reserve_capacity_units"],
            "price_sha256": args.price_sha256,
            "credential_sha256": args.credential_sha256,
            backend.money_key("balance", unit): 5_000_000 if unit == "USD" else 50_000_000,
            backend.money_key("accepted_account_exposure", unit): 5_000_000
            if unit == "USD"
            else 50_000_000,
            "codex_invocations": 1,
        }
    )
    return grant


class StandaloneTransport(FakeTransport):
    def __init__(self, args, *, fail_at=None, kind="timeout"):
        super().__init__()
        self.args, self.fail_at, self.kind = args, fail_at, kind

    def send(self, _endpoint, body, secret):
        index = len(self.calls)
        self.calls.append(body)
        assert secret not in body.decode()
        if index == self.fail_at:
            if self.kind == "timeout":
                raise TimeoutError
            if self.kind == "price":
                return b"OTHER PRICE"
        descriptor = json.loads(body)
        if descriptor.get("method") == "GET":
            if descriptor["kind"] == "price":
                return getattr(self.args, "price_raw", b"OFFLINE OFFICIAL PRICE FIXTURE")
            if descriptor["kind"] == "models":
                return canonical_json({"data": [{"id": backend.MODEL}]})
            return canonical_json(
                {
                    "is_available": True,
                    "balance_infos": [
                        {
                            "currency": getattr(self.args, "currency", "USD"),
                            "total_balance": "50.00"
                            if getattr(self.args, "currency", "USD") == "CNY"
                            else "5.00",
                        }
                    ],
                }
            )
        value = json.loads(response(body))
        if descriptor["messages"][0]["content"] == backend.QUALIFICATION_SYSTEM:
            scope = runner.load_mission_scope_file(
                self.args.mission_scope_file, repo_root=self.args.repo_root
            )
            qualification, _ = runner.qualification_contract(scope)
            case = qualification.CASES[index - 3]
            findings = qualification.expected_findings(case)
            decisions = [
                {
                    "finding_id": f["finding_id"],
                    "decision": case.expected[f"F{n + 1}"],
                    "rationale": "Source establishes the exact original claimed contract.",
                    "source_quote": case.source.strip()
                    if case.expected[f"F{n + 1}"] == "DISPUTED"
                    else "",
                }
                for n, f in enumerate(findings)
            ]
            result = {
                "decisions": decisions,
                "findings": [],
                "summary": "Every supplied claim was checked against the exact fixture source.",
            }
            if index == self.fail_at and self.kind == "qualification":
                result["findings"] = [
                    {
                        "severity": "P1",
                        "title": "Unexpected fixture finding",
                        "evidence": "offline injected",
                    }
                ]
            value["choices"][0]["message"]["content"] = json.dumps(result)
        elif index == self.fail_at and self.kind == "review":
            value["choices"][0]["message"]["content"] = json.dumps(
                {
                    "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
                    "review_result": "FAIL",
                    "findings": [
                        {
                            "severity": "P1",
                            "title": "Injected blocker",
                            "evidence": "offline evidence",
                        }
                    ],
                }
            )
        return canonical_json(value)


def test_standalone_whole_round_dual_source_and_fixture_rejected(standalone_case):
    args, registry = standalone_case
    transport = StandaloneTransport(args)
    manifest, bodies, _ = runner.build_plan(args)
    assert manifest["standalone"]["request_kinds"][3:7] == [
        "qualification:" + n
        for n in ("clean", "single_blocker", "source_based_dispute", "multiple_blockers")
    ]
    assert sum(json.loads(b).get("method") != "GET" for b in bodies) == EXPECTED_POSTS
    assert len(bodies) == EXPECTED_HTTP
    assert manifest["reserve_capacity_units"] == 6 * 1_056_768
    assert manifest["reserve_micro_usd"] == 6 * EXPECTED_CHUNK_MICROUSD
    scope = runner.load_mission_scope_file(args.mission_scope_file, repo_root=args.repo_root)
    config = runner.standalone_config(scope)
    companion = subprocess.check_output(
        [
            "git",
            "diff",
            "--binary",
            "--no-ext-diff",
            f"{config['harness_base']}...{config['harness_head']}",
        ],
        cwd=config["harness_root"],
    )
    assert companion.decode() in json.loads(bodies[-2])["messages"][1]["content"]
    path = runner.run_review(
        args, transport=transport, grant=standalone_grant(args), registry=registry
    )
    assert transport.calls == bodies
    receipt = json.loads(path.read_bytes())
    assert receipt["review_result"] == "PASS"
    assert receipt["provenance"]["financial_status"] == "UNKNOWN_PENDING_PROVIDER_SETTLEMENT"
    assert not _deepseek_receipt_evidence(
        path,
        repo_root=args.repo_root,
        expected_base=args.base_sha,
        expected_head=args.head_sha,
        expected_mission_id=args.mission_id,
        expected_scope_hash=receipt["mission_scope_sha256"],
    ).trusted
    from scripts.devops.codex_review_contract import build_review_prompt  # noqa: PLC0415

    scope = runner.load_mission_scope_file(args.mission_scope_file, repo_root=args.repo_root)
    prompt = build_review_prompt(
        mission_id=args.mission_id,
        base_sha=args.base_sha,
        head_sha=args.head_sha,
        mission_scope=scope,
        mission_scope_path=receipt["mission_scope_path"],
        mission_scope_sha256=receipt["mission_scope_sha256"],
    )
    assert companion.decode() in prompt
    with pytest.raises(backend.DirectError, match="DEEPSEEK_FIRST"):
        runner.codex_standalone_guard(
            scope,
            root=args.repo_root,
            base=args.base_sha,
            head=args.head_sha,
            scope_hash=receipt["mission_scope_sha256"],
            receipt_path=path,
            claim_run_id="offline",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("currency", "CNY"),
        ("cap_micro_usd", 1),
        ("accepted_residual_billing_risk", False),
        ("standalone_authority_approved", False),
        ("execution_id", "other"),
        ("plan_sha256", "0" * 64),
        ("price_sha256", "0" * 64),
        ("credential_sha256", "0" * 64),
        ("post_count", 12),
        ("http_count", 17),
        ("capacity_units", 2_000_000),
        ("runtime_sha256", "0" * 64),
        ("expires_at", "2000-01-01T00:00:00+00:00"),
        ("expires_at", "2099-01-01T00:00:00"),
        ("mode", "PRODUCTION_AUTHORIZED"),
        ("codex_invocations", 2),
        ("accepted_account_exposure_micro_usd", 0),
    ],
)
def test_standalone_admission_tamper_zero_requests(standalone_case, field, value):
    args, registry = standalone_case
    grant = standalone_grant(args)
    grant[field] = value
    transport = StandaloneTransport(args)
    with pytest.raises(backend.DirectError):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert transport.calls == []


@pytest.mark.parametrize(
    ("index", "kind", "expected"),
    [
        (0, "price", 1),
        (2, "timeout", 3),
        (3, "qualification", 4),
        (5, "qualification", 6),
        (7, "review", 8),
        (8, "timeout", 9),
    ],
)
def test_standalone_failure_stops_no_replay(standalone_case, index, kind, expected):
    args, registry = standalone_case
    transport = StandaloneTransport(args, fail_at=index, kind=kind)
    grant = standalone_grant(args)
    with pytest.raises((backend.DirectError, ValueError)):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert len(transport.calls) == expected
    before = list(transport.calls)
    with pytest.raises((backend.DirectError, ValueError)):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert transport.calls == before
    assert list(args.evidence_dir.glob("*-receipt.json")) == []


def test_standalone_runtime_and_companion_identity_fail_closed(standalone_case):
    args, _registry = standalone_case
    scope = json.loads(args.mission_scope_file.read_text())
    config = json.loads(scope["protected_invariants"][0][len(runner.STANDALONE_MARKER) :])
    config["harness_tree"] = "0" * 40
    scope["protected_invariants"] = [runner.STANDALONE_MARKER + json.dumps(config)]
    args.mission_scope_file.write_text(json.dumps(scope))
    git(args.repo_root, "add", ".")
    git(args.repo_root, "commit", "-qm", "wrong companion identity")
    args.head_sha = git(args.repo_root, "rev-parse", "HEAD")
    with pytest.raises(backend.DirectError, match="COMPANION"):
        runner.build_plan(args)


def test_standalone_missing_live_authorization_denied(standalone_case):
    args, registry = standalone_case
    assert backend.LIVE_EXECUTION_APPROVED is False
    with pytest.raises(backend.DirectError, match="NO_GO_FOR_LIVE"):
        backend.HttpsTransport().send(backend.ENDPOINT, b"{}", "unused")
    args.authorization_file = args.repo_root.parent / "not-present-grant"
    with pytest.raises(FileNotFoundError):
        runner.run_review(args, registry=registry)


def test_standalone_qualified_policy_strict_independence(standalone_case):
    from scripts.devops.review_policy import (  # noqa: PLC0415
        CandidateBinding,
        ReviewEvidence,
        evaluate_review_policy,
    )

    args, _ = standalone_case
    manifest, _, _ = runner.build_plan(args)
    binding = manifest["binding"]
    candidate = CandidateBinding(
        binding["base_sha"],
        binding["head_sha"],
        binding["diff_sha256"],
        binding["mission_id"],
        binding["mission_scope_sha256"],
    )
    common = dict(
        trusted=True,
        result="PASS",
        **{k: v for k, v in candidate.__dict__.items() if k != "standalone_required"},
        finding_counts_by_severity={"P0": 0, "P1": 0, "P2": 0, "P3": 1},
        standalone_identity="a" * 64,
        source_bindings_sha256="b" * 64,
        qualification_sha256="c" * 64,
    )
    ds = ReviewEvidence(backend_id=backend.BACKEND_ID, **common)
    codex = ReviewEvidence(backend_id="codex-cli", **common)
    assert evaluate_review_policy("CRITICAL", candidate, [ds, codex]).status == "SATISFIED"
    assert evaluate_review_policy("CRITICAL", candidate, [ds]).status == "UNSATISFIED"
    assert evaluate_review_policy("STRICT", candidate, [ds, codex]).status == "INVALID"
    changed = dict(common, source_bindings_sha256="d" * 64)
    assert (
        evaluate_review_policy(
            "CRITICAL", candidate, [ds, ReviewEvidence(backend_id="codex-cli", **changed)]
        ).status
        == "INVALID"
    )
    unqualified = dict(common, qualification_sha256=None)
    assert (
        evaluate_review_policy(
            "CRITICAL",
            candidate,
            [ReviewEvidence(backend_id=backend.BACKEND_ID, **unqualified), codex],
        ).status
        == "INVALID"
    )


def test_standalone_provenance_and_raw_tampering_rejected(standalone_case, monkeypatch):
    args, registry = standalone_case
    priced_case(args)
    observed = []
    original = receipts.validate_receipt

    def capture(receipt, **kwargs):
        observed.append((deepcopy(receipt), kwargs))
        return original(receipt, **kwargs)

    monkeypatch.setattr(receipts, "validate_receipt", capture)
    runner.run_review(
        args, transport=StandaloneTransport(args), grant=standalone_grant(args), registry=registry
    )
    receipt, kwargs = observed[0]
    assert original(receipt, **kwargs)["review_result"] == "PASS"
    for field in (
        "qualification_sha256",
        "source_bindings_sha256",
        "review_plan_sha256",
        "standalone_identity",
    ):
        bad = deepcopy(receipt)
        bad["provenance"][field] = "0" * 64
        bad["integrity"]["receipt_payload_sha256"] = receipts.receipt_payload_sha256(bad)
        with pytest.raises(IndependentReviewProtocolError):
            original(bad, **kwargs)
    context = kwargs["evidence_context"]

    execution = replace(
        context.direct_execution, raw_responses=context.direct_execution.raw_responses[:-1]
    )
    with pytest.raises(IndependentReviewProtocolError):
        original(
            receipt,
            registry=kwargs["registry"],
            evidence_context=replace(context, direct_execution=execution),
        )


def test_standalone_codex_claim_once_unknown_never_reclaimed(standalone_case, monkeypatch):
    args, registry = standalone_case
    path = runner.run_review(
        args, transport=StandaloneTransport(args), grant=standalone_grant(args), registry=registry
    )
    receipt = json.loads(path.read_bytes())
    provenance = receipt["provenance"]
    # 仅接口故障注入；真正consumer在正向测试中已经拒绝此fixture receipt。
    fact = ReviewEvidence(
        backend.BACKEND_ID,
        True,
        "PASS",
        args.base_sha,
        args.head_sha,
        receipt["diff_sha256"],
        args.mission_id,
        receipt["mission_scope_sha256"],
        receipt["finding_counts_by_severity"],
        standalone_identity=provenance["standalone_identity"],
        source_bindings_sha256=provenance["source_bindings_sha256"],
        qualification_sha256=provenance["qualification_sha256"],
    )
    monkeypatch.setattr(consumer, "consume_direct", lambda *_a, **_k: fact)
    scope = runner.load_mission_scope_file(args.mission_scope_file, repo_root=args.repo_root)
    kwargs = {
        "root": args.repo_root,
        "base": args.base_sha,
        "head": args.head_sha,
        "scope_hash": receipt["mission_scope_sha256"],
        "receipt_path": path,
    }
    first = runner.codex_standalone_guard(scope, **kwargs, claim_run_id="a" * 32)
    assert first["codex_run_id"] == "a" * 32
    assert runner.codex_standalone_guard(scope, **kwargs) == first
    with pytest.raises(backend.DirectError, match="NO_REPLAY"):
        runner.codex_standalone_guard(scope, **kwargs, claim_run_id="b" * 32)


def test_standalone_complete_diff_over_request_limit_denied(standalone_case):
    args, _ = standalone_case
    (args.repo_root / "example.py").write_text("changed UTF8 中文 source\n" * 16000)
    git(args.repo_root, "add", ".")
    git(args.repo_root, "commit", "-qm", "full source exceeds bounded plan")
    args.head_sha = git(args.repo_root, "rev-parse", "HEAD")
    with pytest.raises(backend.DirectError, match="REVIEW_CAPACITY"):
        runner.build_plan(args)


def test_standalone_new_transport_cannot_replay_durable_http_slot(standalone_case, monkeypatch):
    args, _ = standalone_case
    priced_case(args)
    manifest, bodies, _ = runner.build_plan(args)
    grant = standalone_grant(args)
    grant["mode"] = "PRODUCTION_AUTHORIZED"  # 临时账本、假密钥、假HTTPS；不是实际付费grant。
    grant["plan_sha256"] = backend.sha256_bytes(canonical_json(manifest))
    sends = []

    class Connection:
        def __init__(self, *_args, **_kwargs):
            pass

        def request(self, *argv, **_kwargs):
            sends.append(argv)

        def getresponse(self):
            return type("Reply", (), {"status": 200, "read": lambda *_a: args.price_raw})()

        def close(self):
            pass

    monkeypatch.setattr(backend.http.client, "HTTPSConnection", Connection)
    key = "OFFLINE-FAKE-KEY-NEVER-A-PROVIDER-CREDENTIAL"
    unreserved = backend.HttpsTransport(manifest, bodies, grant)
    with pytest.raises(backend.DirectError, match="NO_REPLAY"):
        unreserved.send(backend.ENDPOINT, bodies[0], key)
    assert sends == []
    journal = backend.Journal()
    try:
        journal.reserve(manifest, bodies, grant)
        first = backend.HttpsTransport(manifest, bodies, grant)
        journal.send(manifest, 0, first, key)
        with pytest.raises(backend.DirectError, match="NO_REPLAY"):
            backend.HttpsTransport(manifest, bodies, grant).send(backend.ENDPOINT, bodies[0], key)
        assert len(sends) == 1
        assert journal.db.execute("SELECT COUNT(*) FROM http_attempts").fetchone()[0] == 1
    finally:
        journal.close()


def test_standalone_live_dict_injection_is_not_user_authorization(standalone_case):
    args, registry = standalone_case
    grant = standalone_grant(args)
    grant["mode"] = "PRODUCTION_AUTHORIZED"
    manifest, _, _ = runner.build_plan(args)
    grant["plan_sha256"] = backend.sha256_bytes(canonical_json(manifest))
    with pytest.raises(backend.DirectError, match="PRIVATE_AUTHORIZATION_FILE_REQUIRED"):
        runner.run_review(args, grant=grant, registry=registry)


def test_standalone_production_receipt_requires_each_physical_http_claim(
    standalone_case, monkeypatch, tmp_path
):
    args, registry = standalone_case
    priced_case(args)
    observed = []
    original = receipts.validate_receipt

    def capture(receipt, **kwargs):
        observed.append((deepcopy(receipt), kwargs))
        return original(receipt, **kwargs)

    monkeypatch.setattr(receipts, "validate_receipt", capture)
    runner.run_review(
        args, transport=StandaloneTransport(args), grant=standalone_grant(args), registry=registry
    )
    receipt, kwargs = observed[0]
    context = kwargs["evidence_context"]
    execution = context.direct_execution
    manifest = deepcopy(execution.manifest)
    manifest["execution_mode"] = "DIRECT_HTTPS"
    grant = standalone_grant(args)
    grant["mode"] = "PRODUCTION_AUTHORIZED"  # 故障注入；仍是假账户、假HTTPS、临时authority。
    grant["plan_sha256"] = backend.sha256_bytes(canonical_json(manifest))
    monkeypatch.setattr(backend, "STATE_DIR", tmp_path / "missing-physical-claim-authority")
    journal = backend.Journal()
    try:
        journal.reserve(manifest, list(execution.bodies), grant)
        fixture = StandaloneTransport(args)
        for i in range(len(execution.bodies)):
            journal.send(manifest, i, fixture, "OFFLINE-FAKE-KEY-NEVER-A-PROVIDER-CREDENTIAL")
        assert journal.db.execute("SELECT COUNT(*) FROM completed").fetchone()[0] == len(
            execution.bodies
        )
        assert journal.db.execute("SELECT COUNT(*) FROM http_attempts").fetchone()[0] == 0
    finally:
        journal.close()
    prompt = canonical_json(
        {"manifest": manifest, "requests": [json.loads(b) for b in execution.bodies]}
    )
    receipt["provenance"]["execution_mode"] = "DIRECT_HTTPS"
    receipt["provenance"]["review_plan_sha256"] = backend.sha256_bytes(canonical_json(manifest))
    receipt["review_prompt_sha256"] = backend.sha256_bytes(prompt)
    receipt["integrity"]["receipt_payload_sha256"] = receipts.receipt_payload_sha256(receipt)
    changed = replace(
        context,
        prompt_bytes=prompt,
        direct_execution=replace(execution, manifest=manifest, execution_mode="DIRECT_HTTPS"),
    )
    with pytest.raises(IndependentReviewProtocolError, match="Direct runtime"):
        original(receipt, registry=kwargs["registry"], evidence_context=changed)


@pytest.mark.parametrize("unit", ["CNY", "USD"])
def test_priced_currency_real_runner_consumer_and_ledger(standalone_case, unit):
    args, registry = standalone_case
    priced_case(args, unit)
    grant = standalone_grant(args)
    transport = StandaloneTransport(args)
    path = runner.run_review(args, transport=transport, grant=grant, registry=registry)
    receipt = json.loads(path.read_bytes())
    assert receipt["review_result"] == "PASS"
    manifest, bodies, _ = runner.build_plan(args)
    reserve = sum(backend.request_cost(b, args.price_snapshot) for b in bodies)
    assert reserve == manifest[backend.money_key("reserve", unit)]
    assert len(transport.calls) == EXPECTED_HTTP
    assert grant["http_count"] == EXPECTED_HTTP + 1
    journal = backend.Journal()
    try:
        assert journal.db.execute("SELECT reserved FROM grants").fetchone()[0] == reserve
        stored = json.loads(journal.db.execute("SELECT grant FROM admissions").fetchone()[0])
        assert stored["currency"] == unit
    finally:
        journal.close()


@pytest.mark.parametrize("bad", ["EUR", "USD", "", None])
def test_cny_wrong_grant_currency_never_sends(standalone_case, bad):
    args, registry = standalone_case
    priced_case(args, "CNY")
    grant = standalone_grant(args)
    grant["currency"] = bad
    transport = StandaloneTransport(args)
    with pytest.raises(backend.DirectError):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert transport.calls == []


@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity", "1.0000001", "", None, True])
def test_currency_invalid_amount_denied(value):
    with pytest.raises(backend.DirectError):
        backend.balance_amount(
            {"is_available": True, "balance_infos": [{"currency": "CNY", "total_balance": value}]},
            "CNY",
        )


@pytest.mark.parametrize("unit", ["USD", "EUR", None])
def test_balance_never_converts_or_merges(unit):
    with pytest.raises(backend.DirectError):
        backend.balance_amount(
            {
                "is_available": True,
                "balance_infos": [{"currency": "CNY", "total_balance": "68.72"}],
            },
            unit,
        )


@pytest.mark.parametrize(
    "fault",
    [
        "price_missing",
        "price_currency",
        "price_model",
        "price_expired",
        "insufficient",
        "unknown_currency",
    ],
)
def test_cny_priced_admission_rejects_before_http(standalone_case, fault):
    args, registry = standalone_case
    priced_case(args, "CNY")
    grant = standalone_grant(args)
    if fault == "insufficient":
        grant["cap_micro_cny"] = 1
    elif fault == "price_missing":
        args.price_snapshot = None
    elif fault == "unknown_currency":
        args.currency = "EUR"
    else:
        key, value = {
            "price_currency": ("currency", "USD"),
            "price_model": ("model", "other"),
            "price_expired": ("observed_at", "2000-01-01T00:00:00+00:00"),
        }[fault]
        args.price_snapshot[key] = value
    transport = StandaloneTransport(args)
    with pytest.raises(backend.DirectError):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert transport.calls == []


@pytest.mark.parametrize(
    "fault", ["wrong_model", "missing_rate", "wrong_currency", "wrong_source", "wrong_scale"]
)
def test_official_price_content_fail_closed(standalone_case, fault):
    args, _ = standalone_case
    priced_case(args, "CNY")
    raw, url = args.price_raw, backend.price_url("CNY")
    if fault == "wrong_model":
        raw = raw.replace(backend.MODEL.encode(), b"other")
    elif fault == "missing_rate":
        raw = raw.replace(b"OFF-PEAK", b"NO-TIER")
    elif fault == "wrong_currency":
        raw = raw.replace(b"CNY", b"USD")
    elif fault == "wrong_scale":
        raw = raw.replace(b"1M", b"1K")
    else:
        url = "https://other.invalid/pricing"
    with pytest.raises(backend.DirectError):
        backend.parse_price_snapshot(
            raw, source_url=url, unit="CNY", observed_at=datetime.now(UTC).isoformat()
        )


@pytest.mark.parametrize("unit", ["USD", "CNY"])
@pytest.mark.parametrize(
    ("target", "second_status"),
    [
        (backend.PRICE_URL + "/", 200),
        (backend.PRICE_URL + "/", 302),
        ("https://evil.invalid/", 200),
        ("http://api-docs.deepseek.com/quick_start/pricing", 200),
        (backend.PRICE_URL + "?next=evil", 200),
        ("https://api-docs.deepseek.com/other", 200),
    ],
)
def test_price_redirect_real_https_boundary_durable_limit(
    standalone_case, monkeypatch, target, second_status, unit
):
    args, _ = standalone_case
    target = target.replace(backend.PRICE_URL, backend.price_url(unit))
    priced_case(args, unit, backend.price_url(unit) + "/")
    manifest, bodies, _ = runner.build_plan(args)
    grant = standalone_grant(args)
    grant["mode"] = "PRODUCTION_AUTHORIZED"  # TEST_ONLY authority in temporary directory.
    grant["plan_sha256"] = backend.sha256_bytes(canonical_json(manifest))
    sent = []

    class Connection:
        def __init__(self, host, *_a, **_kw):
            self.host = host

        def request(self, method, path, **kw):
            sent.append((self.host, method, path, kw))
            assert "Authorization" not in kw["headers"]

        def getresponse(self):
            n = len(sent)
            return type(
                "Reply",
                (),
                {
                    "status": 302 if n == 1 else second_status,
                    "getheader": lambda *_a: target,
                    "read": lambda *_a: args.price_raw,
                },
            )()

        def close(self):
            pass

    monkeypatch.setattr(backend.http.client, "HTTPSConnection", Connection)
    journal = backend.Journal()
    try:
        journal.reserve(manifest, bodies, grant)
        transport = backend.HttpsTransport(manifest, bodies, grant)
        if target == backend.price_url(unit) + "/" and second_status == backend.HTTP_OK:
            journal.send(manifest, 0, transport, "OFFLINE-FAKE-KEY-NEVER-A-PROVIDER-CREDENTIAL")
            assert len(sent) == 1 + backend.MAX_PRICE_REDIRECTS
            assert journal.db.execute("SELECT target FROM price_redirects").fetchall() == [
                (target,)
            ]
        else:
            with pytest.raises(backend.DirectError):
                journal.send(manifest, 0, transport, "OFFLINE-FAKE-KEY-NEVER-A-PROVIDER-CREDENTIAL")
            expected = 1 + (target == backend.price_url(unit) + "/")
            assert len(sent) == expected
            with pytest.raises(backend.DirectError):
                journal.send(
                    manifest,
                    0,
                    backend.HttpsTransport(manifest, bodies, grant),
                    "OFFLINE-FAKE-KEY-NEVER-A-PROVIDER-CREDENTIAL",
                )
            assert len(sent) == expected
    finally:
        journal.close()


@pytest.mark.parametrize(
    "infos",
    [
        [],
        [{"currency": "EUR", "total_balance": "1"}],
        [{"currency": "CNY", "total_balance": "1"}] * 2,
    ],
)
def test_balance_missing_unknown_duplicate_denied(infos):
    with pytest.raises(backend.DirectError):
        backend.balance_amount({"is_available": True, "balance_infos": infos}, "CNY")


def test_cny_unknown_stops_whole_round(standalone_case):
    args, registry = standalone_case
    priced_case(args, "CNY")
    transport = StandaloneTransport(args, fail_at=3)
    grant = standalone_grant(args)
    with pytest.raises(backend.DirectError):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    count = len(transport.calls)
    with pytest.raises(backend.DirectError):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert len(transport.calls) == count
    journal = backend.Journal()
    try:
        assert (
            journal.db.execute("SELECT reserved FROM grants").fetchone()[0]
            == grant["cap_micro_cny"]
        )
    finally:
        journal.close()
