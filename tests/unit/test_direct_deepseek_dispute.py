"""V2 适配定点测试；仅合成响应，网络与生产凭据均禁止。"""

# 这些数字是验收清单中的精确边界断言，不用实现常量替代独立预期。
# ruff: noqa: PLR2004
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil

import pytest

from scripts.devops import direct_deepseek_dispute as dispute
from scripts.devops import direct_deepseek_independent_review as runner
from scripts.devops import direct_deepseek_receipt_evidence as consumer
from scripts.devops.independent_review_backends import direct_deepseek as backend
from scripts.devops.independent_review_protocol import canonical_json
from tests.helpers.direct_harness_source import (
    portable_harness as portable_harness,  # noqa: PLC0414
)
from tests.unit.test_direct_deepseek_bound import capacity_candidate, git, priced_case, response
from tests.unit.test_direct_deepseek_bound import case as case  # noqa: PLC0414
from tests.unit.test_direct_deepseek_bound import no_network as no_network  # noqa: PLC0414
from tests.unit.test_direct_deepseek_standalone import StandaloneTransport, standalone_grant
from tests.unit.test_direct_deepseek_standalone import (
    standalone_case as standalone_case,  # noqa: PLC0414
)


@pytest.fixture
def integrated(request, monkeypatch):
    args, registry = request.getfixturevalue("standalone_case")
    capacity_candidate(args, 8)
    scope = json.loads(args.mission_scope_file.read_bytes())
    groups = {f"football:{i}": [{"source": "football", "start": 0, "end": 256}] for i in range(8)}
    groups["harness:0"] = [{"source": "harness", "start": 0, "end": 256}]
    # 组内可以引用其他已批准 chunk 的 bytes；不可将未批准的整个文件作为来源。
    groups["football:0"].append({"source": "football", "start": 70_000, "end": 70_512})
    scope["protected_invariants"].append(
        dispute.MARKER + json.dumps({"version": dispute.VERSION, "groups": groups})
    )
    args.mission_scope_file.write_text(json.dumps(scope))
    git(args.repo_root, "add", ".")
    git(args.repo_root, "commit", "-qm", "TEST_ONLY explicit source groups")
    args.head_sha = git(args.repo_root, "rev-parse", "HEAD")
    priced_case(args, "CNY")
    original_read = Path.read_text

    def protected_read(path, *a, **kw):
        if path == backend.SECRET_PATH:
            raise AssertionError("production credential must not be read")
        return original_read(path, *a, **kw)

    monkeypatch.setattr(Path, "read_text", protected_read)
    return args, registry


def grant_for(args):
    grant = standalone_grant(args)
    grant.update(contract="standalone-informed-risk/dispute-v2", dispute_authority_approved=True)
    return grant


class DisputeTransport(StandaloneTransport):
    def __init__(self, args, *, finding=True, decision="DISPUTED", corrupt=None, fail_stage=None):
        super().__init__(args)
        self.finding, self.decision, self.corrupt, self.fail_stage = (
            finding,
            decision,
            corrupt,
            fail_stage,
        )
        self.manifest, self.planned, _ = runner.build_plan(args)
        self.raws = []

    def send(self, endpoint, body, secret):
        kind = self.manifest["standalone"]["request_kinds"][len(self.calls)]
        if kind == self.fail_stage:
            self.calls.append(body)
            raise TimeoutError("SYNTHETIC UNKNOWN")
        if kind.startswith("dispute:"):
            self.calls.append(body)
            before = dispute.replay(self.manifest, self.planned, self.raws)
            aggregate = kind == "dispute:cross-group"
            expected = (
                [f for a in before["audits"] for f in a["carried"]]
                if aggregate
                else before["audits"][-1]["original"]
            )
            decisions = []
            for finding in expected:
                if finding["severity"] == "P3":
                    continue
                entry = {
                    "finding_id": finding["finding_id"],
                    "decision": "UPHELD" if aggregate else self.decision,
                    "rationale": "Synthetic independent judgment against the exact approved code source.",
                    "source_quote": "",
                    "source_id": "",
                    "quote_start": 0,
                    "quote_end": 0,
                }
                if entry["decision"] == "DISPUTED":
                    group = self.manifest["standalone"]["dispute"]["groups"][
                        kind[len("dispute:") :]
                    ]
                    span = group["spans"][-1]
                    start = span["quote_start"]
                    source = group["source"].encode()
                    entry.update(
                        source_id=group["source_id"],
                        quote_start=start,
                        quote_end=start + 32,
                        source_quote=source[start : start + 32].decode(),
                    )
                if self.corrupt:
                    self.corrupt(entry, self.manifest)
                decisions.append(entry)
            result = {
                "findings": [],
                "decisions": decisions,
                "summary": "Synthetic full evidence adjudication, not a real Provider or formal approval.",
            }
            value = json.loads(response(body))
            value["choices"][0]["message"]["content"] = json.dumps(result)
            raw = canonical_json(value)
        else:
            raw = super().send(endpoint, body, secret)
            if kind == "football:0" and self.finding:
                value = json.loads(raw)
                value["choices"][0]["message"]["content"] = json.dumps(
                    {
                        "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
                        "review_result": "FAIL",
                        "findings": [
                            {
                                "severity": "P1",
                                "title": "Synthetic cross-chunk claim",
                                "evidence": "Synthetic claim requires independent exact source verification.",
                            }
                        ],
                    }
                )
                raw = canonical_json(value)
        self.raws.append(raw)
        return raw


def run(args, registry, **kwargs):
    transport = DisputeTransport(args, **kwargs)
    path = runner.run_review(args, transport=transport, grant=grant_for(args), registry=registry)
    return path, transport


@pytest.mark.parametrize("finding", [False, True], ids=["TEST_01_clean", "TEST_03_disputed"])
def test_complete_synthetic_consumer_and_coverage(integrated, finding):
    args, registry = integrated
    path, transport = run(args, registry, finding=finding)
    receipt = json.loads(path.read_bytes())
    assert receipt["review_result"] == "PASS"
    assert receipt["provenance"]["execution_mode"] == "OFFLINE_FIXTURE"
    assert receipt["provenance"]["dispute_audit_sha256"]
    assert len(transport.calls) == 27  # 23 POST + 4 GET，redirect 上限另计。
    replayed = dispute.replay(transport.manifest, transport.planned, transport.raws)
    assert len(replayed["audits"]) == 9
    assert {a["kind"] for a in replayed["audits"]} == {
        *(f"football:{i}" for i in range(8)),
        "harness:0",
    }
    assert transport.calls == replayed["actual_bodies"]
    if finding:
        audit = replayed["audits"][0]
        assert audit["raw_findings"][0]["severity"] == "P1"
        assert audit["original"][0]["finding"]["title"] == "Synthetic cross-chunk claim"
        assert audit["raw_response_sha256"] == backend.sha256_bytes(transport.raws[7])
        assert audit["result"]["decisions"][0]["decision"] == "DISPUTED"
    journal = backend.Journal()
    assert journal.db.execute("SELECT COUNT(*) FROM materialized").fetchone()[0] == 27
    assert journal.db.execute("SELECT COUNT(*) FROM completed").fetchone()[0] == 27
    journal.close()
    # 正式 consumer 必须继续拒绝模拟身份；run_review 的真实 receipt validator 已验证合成完整证据。
    evidence = consumer.consume_direct(
        path,
        repo_root=args.repo_root,
        expected_base=args.base_sha,
        expected_head=args.head_sha,
        expected_mission_id=args.mission_id,
        expected_scope_hash=receipt["mission_scope_sha256"],
    )
    assert not evidence.trusted
    if destination := os.environ.get("DIRECT_DISPUTE_TEST_EVIDENCE_DIR"):
        target = Path(destination) / ("synthetic-disputed" if finding else "synthetic-clean")
        target.mkdir(mode=0o700, parents=True, exist_ok=True)
        for artifact in args.evidence_dir.glob("*.json"):
            shutil.copyfile(artifact, target / artifact.name)
        (target / "audit.json").write_bytes(canonical_json(replayed["audits"]))
        (target / "validation.json").write_bytes(
            canonical_json(
                {
                    "fixture_only": True,
                    "production_validate_receipt": "PASS_WITH_OFFLINE_CONTEXT",
                    "production_consume_direct_trusted": False,
                    "review_coverage": [a["kind"] for a in replayed["audits"]],
                    "actual_POST": 23,
                    "actual_HTTP": 27,
                }
            )
        )


@pytest.mark.parametrize(
    "decision", ["UPHELD", "UNDETERMINED"], ids=["TEST_02_confirmed", "TEST_04_unknown_judgment"]
)
def test_blocking_decisions_stop(integrated, decision):
    args, registry = integrated
    transport = DisputeTransport(args, decision=decision)
    with pytest.raises((backend.DirectError, ValueError)):
        runner.run_review(args, transport=transport, grant=grant_for(args), registry=registry)
    assert len(transport.calls) == 9
    assert not list(args.evidence_dir.glob("*-receipt.json"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("finding_id", "C999F999"),
        ("source_id", "0" * 64),
        ("quote_start", -1),
        ("quote_end", 9_000_000),
    ],
)
def test_forged_reference_rejected(integrated, field, value):
    args, registry = integrated
    transport = DisputeTransport(args, corrupt=lambda e, _: e.update({field: value}))
    with pytest.raises((backend.DirectError, ValueError)):
        runner.run_review(args, transport=transport, grant=grant_for(args), registry=registry)
    assert len(transport.calls) == 9


def test_cross_group_source_rejected(integrated):
    args, registry = integrated
    transport = DisputeTransport(
        args,
        corrupt=lambda e, m: e.update(
            source_id=m["standalone"]["dispute"]["groups"]["harness:0"]["source_id"]
        ),
    )
    with pytest.raises((backend.DirectError, ValueError)):
        runner.run_review(args, transport=transport, grant=grant_for(args), registry=registry)
    assert len(transport.calls) == 9


@pytest.mark.parametrize(
    "mutation", ["budget", "request_count", "authority", "old_grant", "runtime", "registry"]
)
def test_admission_fail_closed(integrated, mutation):
    args, registry = integrated
    grant = grant_for(args)
    if mutation == "budget":
        grant["cap_micro_cny"] = 1
    elif mutation == "request_count":
        grant["post_count"] = 13
    elif mutation == "authority":
        grant["dispute_authority_approved"] = False
    elif mutation == "old_grant":
        grant.pop("dispute_authority_approved")
        grant["contract"] = "standalone-informed-risk/v1"
    elif mutation == "runtime":
        grant["runtime_sha256"] = "0" * 64
    else:
        registry[backend.BACKEND_ID]["minimum_harness_version"] = "0.0.0"
    transport = DisputeTransport(args)
    with pytest.raises(backend.DirectError):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert not transport.calls


def test_unknown_no_retry(integrated):
    args, registry = integrated
    transport = DisputeTransport(args, fail_stage="dispute:football:0")
    grant = grant_for(args)
    with pytest.raises(backend.DirectError):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    before = len(transport.calls)
    with pytest.raises(backend.DirectError):
        runner.run_review(args, transport=transport, grant=grant, registry=registry)
    assert len(transport.calls) == before == 9


def test_new_plan_bounds_and_old_identity_rejected(integrated):
    args, _ = integrated
    manifest, bodies, _ = runner.build_plan(args)
    assert sum(json.loads(b).get("method") != "GET" for b in bodies) == 23
    assert len(bodies) + 1 == 28
    assert manifest["reserve_capacity_units"] == 23 * 1_056_768
    assert all(len(b) <= 40_000 for b in bodies)
    assert dispute.MAX_POSTS == 37
    assert dispute.MAX_HTTP == 42
    old = deepcopy(manifest)
    old["standalone"]["execution_id"] = "HISTORICAL-FAIL"
    with pytest.raises(backend.DirectError, match="DISPUTE_PLAN_CHANGED"):
        runner.rebuild_standalone_plan(old)


@pytest.mark.parametrize("fault", ["source", "head", "scope_hash", "group_missing", "extra_slot"])
def test_identity_and_coverage_tamper_rejected(integrated, fault):
    args, _ = integrated
    manifest, _, _ = runner.build_plan(args)
    manifest["execution_mode"] = "OFFLINE_FIXTURE"
    changed = deepcopy(manifest)
    if fault == "source":
        changed["standalone"]["dispute"]["groups"]["football:0"]["source"] += "forged"
    elif fault == "head":
        changed["binding"]["head_sha"] = "0" * 40
    elif fault == "scope_hash":
        changed["binding"]["mission_scope_sha256"] = "0" * 64
    elif fault == "group_missing":
        del changed["standalone"]["dispute"]["groups"]["harness:0"]
    else:
        changed["standalone"]["request_kinds"].append("dispute:unapproved")
    with pytest.raises((backend.DirectError, runner.DeepSeekReviewError)):
        runner.rebuild_standalone_plan(changed)


def test_disputed_reference_cannot_quote_identity_header(integrated):
    args, registry = integrated

    def forge(entry, manifest):
        source = manifest["standalone"]["dispute"]["groups"]["football:0"]["source"].encode()
        entry.update(quote_start=0, quote_end=32, source_quote=source[:32].decode())

    transport = DisputeTransport(args, corrupt=forge)
    with pytest.raises(backend.DirectError, match="DISPUTE_NOT_CODE_REFERENCE"):
        runner.run_review(args, transport=transport, grant=grant_for(args), registry=registry)
    assert len(transport.calls) == 9


def test_payload_overflow_and_post_ceiling_never_hidden(integrated):
    args, _ = integrated
    manifest, planned, _ = runner.build_plan(args)
    with pytest.raises(backend.DirectError, match="CAPACITY"):
        backend.payload("x" * 40_001, synthesis=True)
    # 将 aggregate 输入膨胀不能触发第二个请求/续写，而是发送前拒绝。
    with pytest.raises(backend.DirectError, match="CAPACITY"):
        dispute.stage_body(
            manifest,
            "dispute:cross-group",
            [
                {
                    "kind": "football:0",
                    "original": [{"finding": "x" * 40_001}],
                    "raw_response_sha256": "0" * 64,
                    "result": {},
                    "carried": [],
                }
            ],
        )
    assert len(planned) < backend.POLICY["max_requests"]


def test_raw_hash_and_materialization_enforced_by_receipt_validator(integrated):
    args, registry = integrated
    path, transport = run(args, registry, finding=True)
    receipt = json.loads(path.read_bytes())
    stem = path.name.removesuffix("-receipt.json")
    prompt = (path.parent / (stem + "-prompt.json")).read_bytes()
    raw = (path.parent / (stem + "-raw.json")).read_bytes()
    final = (path.parent / (stem + "-final.json")).read_bytes()
    evidence = runner.DirectExecutionEvidence(
        transport.manifest,
        tuple(transport.calls),
        tuple(transport.raws),
        backend.runtime_identity(),
        "OFFLINE_FIXTURE",
    )
    # build_plan 返回的 mode 是 DIRECT_HTTPS；fixture 验证只能明确选择 OFFLINE_FIXTURE。
    evidence.manifest["execution_mode"] = "OFFLINE_FIXTURE"
    context = runner.receipts.ReceiptEvidenceContext(
        repo_root=args.repo_root,
        base_sha=args.base_sha,
        head_sha=args.head_sha,
        mission_scope_path=receipt["mission_scope_path"],
        prompt_bytes=prompt,
        raw_output_bytes=raw,
        final_result_bytes=final,
        direct_execution=evidence,
    )
    registry = deepcopy(registry)
    registry[backend.BACKEND_ID]["status"] = "active"
    runner.receipts.validate_receipt(receipt, registry=registry, evidence_context=context)
    corrupted = deepcopy(context)
    object.__setattr__(
        corrupted.direct_execution,
        "raw_responses",
        (*transport.raws[:7], transport.raws[7] + b" ", *transport.raws[8:]),
    )
    with pytest.raises(runner.receipts.IndependentReviewProtocolError):
        runner.receipts.validate_receipt(receipt, registry=registry, evidence_context=corrupted)


def test_dynamic_physical_claim_exact_body_and_no_extra_attempt(integrated):
    """物理认领在本地模拟；实际网络始终关闭。"""
    args, registry = integrated
    grant = grant_for(args)

    class ClaimedTransport(DisputeTransport):
        def send(self, endpoint, body, secret):
            journal = backend.Journal()
            try:
                journal.claim_http_attempt(self.manifest, body, grant)
            finally:
                journal.close()
            return super().send(endpoint, body, secret)

    transport = ClaimedTransport(args)
    transport.manifest["execution_mode"] = "OFFLINE_FIXTURE"
    runner.run_review(args, transport=transport, grant=grant, registry=registry)
    journal = backend.Journal()
    try:
        assert journal.db.execute("SELECT COUNT(*) FROM http_attempts").fetchone()[0] == 27
        with pytest.raises(backend.DirectError, match="HTTP_ATTEMPT_NO_REPLAY"):
            journal.claim_http_attempt(transport.manifest, transport.calls[8] + b" ", grant)
        with pytest.raises(backend.DirectError, match="HTTP_ATTEMPT_NO_REPLAY"):
            journal.claim_http_attempt(transport.manifest, transport.calls[8], grant)
        assert journal.db.execute("SELECT COUNT(*) FROM http_attempts").fetchone()[0] == 27
    finally:
        journal.close()


def test_reserved_template_mutation_rejected_before_send(integrated):
    """模拟未发送账本槽异常；仍不得交付未经准入的正文。"""
    args, _ = integrated
    manifest, bodies, _ = runner.build_plan(args)
    manifest["execution_mode"] = "OFFLINE_FIXTURE"
    journal = backend.Journal()
    try:
        journal.reserve(manifest, bodies, grant_for(args))
        journal.db.execute(
            "UPDATE requests SET body=? WHERE review_id=? AND idx=0",
            (bodies[0] + b" ", manifest["review_identity"]),
        )
        journal.db.commit()
        transport = DisputeTransport(args)
        with pytest.raises(backend.DirectError, match="DISPUTE_TEMPLATE_CHANGED"):
            journal.send(manifest, 0, transport, "OFFLINE-FAKE-KEY-NEVER-A-PROVIDER-CREDENTIAL")
        assert not transport.calls
        assert journal.db.execute("SELECT COUNT(*) FROM materialized").fetchone()[0] == 0
    finally:
        journal.close()


def test_head_blob_support_uses_frozen_content_and_v2_quote(integrated):
    """跨 chunk 支持来源可含未改动行；工作树文本不能替代冻结 blob。"""
    args, registry = integrated
    scope = json.loads(args.mission_scope_file.read_bytes())
    settings = json.loads(scope["protected_invariants"][-1][len(dispute.MARKER) :])
    settings["groups"]["football:0"] = [
        {"source": "football", "path": "example.py", "start": 70_000, "end": 70_512}
    ]
    scope["protected_invariants"][-1] = dispute.MARKER + json.dumps(settings)
    args.mission_scope_file.write_text(json.dumps(scope))
    git(args.repo_root, "add", ".")
    git(args.repo_root, "commit", "-qm", "TEST_ONLY frozen blob reference")
    args.head_sha = git(args.repo_root, "rev-parse", "HEAD")
    manifest, _, _ = runner.build_plan(args)
    reference = settings["groups"]["football:0"][0]
    frozen = dispute.reference_source(manifest, {}, reference)
    (args.repo_root / "example.py").write_text("untrusted local replacement")
    assert dispute.reference_source(manifest, {}, reference) == frozen
    (args.repo_root / "example.py").write_bytes(frozen)
    path, transport = run(args, registry, finding=True)
    assert json.loads(path.read_bytes())["review_result"] == "PASS"
    assert (
        dispute.replay(transport.manifest, transport.planned, transport.raws)["audits"][0][
            "result"
        ]["decisions"][0]["decision"]
        == "DISPUTED"
    )


@pytest.mark.parametrize("fault", ["path", "family", "blob", "range", "capacity"])
def test_head_blob_support_invalid_identity_or_capacity_rejected(integrated, fault):
    args, _ = integrated
    manifest, _, _ = runner.build_plan(args)
    reference = {"source": "football", "path": "example.py", "start": 0, "end": 32}
    if fault == "path":
        reference["path"] = "../unapproved.py"
    elif fault == "family":
        reference["source"] = "other-task"
    elif fault == "blob":
        manifest["source_bindings"]["football"]["files"]["example.py"] = "100644 blob forged"
    if fault in {"path", "family", "blob"}:
        with pytest.raises(backend.DirectError, match="DISPUTE_SOURCE"):
            dispute.reference_source(manifest, {}, reference)
        return
    scope = json.loads(args.mission_scope_file.read_bytes())
    settings = json.loads(scope["protected_invariants"][-1][len(dispute.MARKER) :])
    reference["end"] = 9_000_000 if fault == "range" else 16_000
    settings["groups"]["football:0"] = [reference]
    scope["protected_invariants"][-1] = dispute.MARKER + json.dumps(settings)
    args.mission_scope_file.write_text(json.dumps(scope))
    git(args.repo_root, "add", ".")
    git(args.repo_root, "commit", "-qm", "TEST_ONLY invalid reference")
    args.head_sha = git(args.repo_root, "rev-parse", "HEAD")
    with pytest.raises(backend.DirectError, match=r"DISPUTE_SOURCE_(RANGE|CAPACITY)"):
        runner.build_plan(args)
