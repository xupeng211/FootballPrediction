#!/usr/bin/env python3
"""独立 Direct DeepSeek exact-HEAD runner；默认 NO_GO_FOR_LIVE。

lifecycle: permanent
owner: engineering workflow governance
"""

# 局部导入保留既有 backend/consumer 环；资格模块只从冻结 companion 加载。
# ruff: noqa: PLC0415
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.devops import direct_deepseek_source as source_contract  # noqa: E402
from scripts.devops import independent_review_receipt as receipts  # noqa: E402
from scripts.devops.claude_deepseek_independent_review import (  # noqa: E402
    DeepSeekReviewError,
    _git,
    _now,
    _sha,
    _write,
)
from scripts.devops.deepseek_review_chunks import aggregate, build_chunk_prompt, plan  # noqa: E402
from scripts.devops.independent_review_backends import direct_deepseek as backend  # noqa: E402
from scripts.devops.independent_review_protocol import (  # noqa: E402
    PROTOCOL_VERSION,
    canonical_json,
    sha256_bytes,
)
from scripts.ops.helpers.agent_workflow_contract import (  # noqa: E402
    load_mission_scope_file,
    mission_scope_relative_path,
    validate_mission_scope,
)

# 保留 Runner 原有公开接口；实现由单一来源合同模块提供。
STANDALONE_MARKER = source_contract.STANDALONE_MARKER
companion_source = source_contract.companion_source
qualification_contract = source_contract.qualification_contract
source_binding = source_contract.source_binding
standalone_config = source_contract.standalone_config


@dataclass(frozen=True)
class DirectExecutionEvidence:
    """Harness 观察的执行事实；正式 consumer 不接受离线 fixture 身份。"""

    manifest: dict
    bodies: tuple[bytes, ...]
    raw_responses: tuple[bytes, ...]
    runtime_sha256: str
    execution_mode: str


def build_plan(args: argparse.Namespace) -> tuple[dict, list[bytes], object]:
    """从 exact HEAD scope 和完整 canonical diff 冻结全部请求。"""
    root = args.repo_root.resolve()
    base, head = _sha(root, args.base_sha), _sha(root, args.head_sha)
    if _sha(root, "HEAD") != head:
        raise DeepSeekReviewError("review head is not the current exact HEAD")
    scope_file = args.mission_scope_file.resolve()
    scope = load_mission_scope_file(scope_file, repo_root=root, expected_mission_id=args.mission_id)
    scope_path = mission_scope_relative_path(scope_file, root)
    scope_bytes = _git(root, "show", f"{head}:{scope_path}", text=False)
    if scope_bytes != scope_file.read_bytes():
        raise DeepSeekReviewError("scope is not bound to HEAD")
    diff = _git(root, "diff", "--binary", "--no-ext-diff", f"{base}...{head}", text=False)
    changed_paths = _git(root, "diff", "--name-only", f"{base}...{head}").splitlines()
    if validate_mission_scope(changed_paths, scope):
        raise DeepSeekReviewError("canonical diff exceeds frozen mission scope")
    chunks = plan(
        diff,
        base_sha=base,
        head_sha=head,
        mission_id=args.mission_id,
        mission_scope_sha256=sha256_bytes(scope_bytes),
    )
    bodies = [
        backend.payload(
            build_chunk_prompt(
                chunk=c,
                source=diff[c.start : c.end],
                manifest=chunks,
                scope_sha=sha256_bytes(scope_bytes),
            )
        )
        for c in chunks.chunks
    ]
    binding = {
        "repository": "xupeng211/FootballPrediction",
        "base_sha": base,
        "head_sha": head,
        "diff_sha256": sha256_bytes(diff),
        "mission_id": args.mission_id,
        "mission_scope_path": scope_path,
        "mission_scope_sha256": sha256_bytes(scope_bytes),
    }
    manifest = {
        "version": "direct-deepseek-review/v1",
        "execution_mode": "DIRECT_HTTPS",
        "binding": binding,
        "review_identity": sha256_bytes(canonical_json(binding)),
        "chunk_manifest": chunks.payload(),
        "request_digests": [sha256_bytes(b) for b in bodies],
        "request_count": len(bodies),
        "max_http_attempts": len(bodies),
        "runtime_sha256": backend.runtime_identity(),
        "policy_sha256": backend.POLICY_SHA,
        "cost_status": "CONDITIONAL_COST_BOUND",
        "live_status": "NO_GO_FOR_LIVE",
        "reserve_micro_usd": sum(backend.request_cost(b) for b in bodies),
        "reserve_capacity_units": len(bodies)
        * (backend.POLICY["context_capacity"] + backend.POLICY["max_output"]),
    }
    if standalone_config(scope) is not None:
        return build_standalone_plan(args, scope, manifest, bodies, chunks)
    return manifest, bodies, chunks


def run_review(args: argparse.Namespace, *, transport=None, grant=None, registry=None) -> Path:  # noqa: C901, PLR0912, PLR0915
    """复用原协议运行显式 Direct backend，真实执行默认禁止。"""
    manifest, bodies, chunks = build_plan(args)
    registry = (
        registry
        if registry is not None
        else receipts.load_backend_registry(ROOT / "docs/agentic/independent_review_backends.json")
    )
    registered = registry.get(backend.BACKEND_ID, {})
    standalone = manifest.get("standalone") is not None
    if registered.get("status") != "active" and not (
        standalone and registered.get("status") == "reserved"
    ):
        raise backend.DirectError("UNAPPROVED_EXECUTOR")
    offline = transport is not None and getattr(transport, "offline_fixture", False) is True
    if not offline and not standalone and not backend.LIVE_EXECUTION_APPROVED:
        raise backend.DirectError("NO_GO_FOR_LIVE")
    if transport is not None and not offline:
        raise backend.DirectError("TRANSPORT_IDENTITY")
    manifest["execution_mode"] = "OFFLINE_FIXTURE" if offline else "DIRECT_HTTPS"
    if grant is not None and not offline:
        raise backend.DirectError("PRIVATE_AUTHORIZATION_FILE_REQUIRED")
    if grant is None:
        backend.private(args.authorization_file)
        grant = json.loads(args.authorization_file.read_bytes())
    if standalone:
        if registered.get("status") != "reserved":
            raise backend.DirectError("STANDALONE_REGISTRY_IDENTITY")
        if not offline and (
            _sha(ROOT, "HEAD") != manifest["binding"]["head_sha"]
            or _git(ROOT, "status", "--porcelain")
        ):
            raise backend.DirectError("EXECUTED_SOURCE_IDENTITY")
        if (
            registered
            != receipts.load_backend_registry(
                ROOT / "docs/agentic/independent_review_backends.json"
            )[backend.BACKEND_ID]
        ):
            raise backend.DirectError("STANDALONE_REGISTRY_IDENTITY")
        backend.validate_standalone_admission(manifest, bodies, grant, offline=offline)
        registry = {k: dict(v) for k, v in registry.items()}
        registry[backend.BACKEND_ID]["status"] = (
            "active"  # 本次准入内精确身份，不修改Registry/live。
        )
        transport = transport or backend.HttpsTransport(manifest, bodies, grant)
    root, evidence = args.repo_root.resolve(), args.evidence_dir.absolute()
    if evidence.resolve() != evidence or root == evidence or root in evidence.parents:
        raise backend.DirectError("EXTERNAL_EVIDENCE_REQUIRED")
    evidence.mkdir(mode=0o700, parents=True, exist_ok=True)
    backend.private(evidence, directory=True)
    journal = backend.Journal()
    worktree = evidence / ("direct-deepseek-worktree-" + uuid.uuid4().hex)
    receipt_path = None
    try:
        journal.reserve(manifest, bodies, grant)  # 完整审核预留，任何发送之前 commit。
        _git(root, "worktree", "add", "--detach", str(worktree), manifest["binding"]["head_sha"])
        if _git(worktree, "status", "--porcelain"):
            raise DeepSeekReviewError("worktree is not clean")
        if offline:
            secret = "OFFLINE-FAKE-KEY-NEVER-A-PROVIDER-CREDENTIAL"
        else:
            backend.private(backend.SECRET_PATH)
            secret = backend.SECRET_PATH.read_text().strip()
            if not secret:
                raise backend.DirectError("EMPTY_SECRET")
        if (
            standalone
            and sha256_bytes(secret.encode()) != manifest["standalone"]["credential_sha256"]
        ):
            raise backend.DirectError("CREDENTIAL_CHANGED")
        started = _now()
        raws, results = [], []
        for index in range(len(bodies)):
            raw, result = journal.send(
                manifest, index, transport or backend.HttpsTransport(), secret
            )
            if standalone:
                scope = load_mission_scope_file(
                    args.mission_scope_file, repo_root=root, expected_mission_id=args.mission_id
                )
                kind = manifest["standalone"]["request_kinds"][index]
                if kind.startswith("qualification:"):
                    validate_qualification(scope, index - 3, result)
                if kind in {"balance_start", "balance_end"}:
                    backend.balance_amount(result, backend.currency(manifest))
                if kind == "balance_start" and (
                    backend.balance_amount(result, backend.currency(manifest))
                    != grant[backend.money_key("balance", backend.currency(manifest))]
                ):
                    raise backend.DirectError("BALANCE_CHANGED")
                if (
                    "dispute" not in manifest["standalone"]
                    and kind.startswith(("football:", "harness:"))
                    and result["review_result"] != "PASS"
                ):
                    raise backend.DirectError("REVIEW_FAILED_STOP")
            raws.append(raw)
            if standalone and "dispute" in manifest["standalone"]:
                validate_completed_prefix(manifest, list(enumerate(raws)), len(raws))
            results.append({"chunk_index": index, "result": result})
        secret = ""
        if standalone and "dispute" in manifest["standalone"]:
            from scripts.devops.direct_deepseek_dispute import replay

            bodies = replay(manifest, bodies, raws)["actual_bodies"]
        normalized = (
            standalone_result(scope, manifest, bodies, raws)
            if standalone
            else aggregate(results, chunks)
        )
        if _sha(worktree, "HEAD") != manifest["binding"]["head_sha"] or _git(
            worktree, "status", "--porcelain"
        ):
            raise DeepSeekReviewError("worktree was mutated")
        receipt_path = _write_receipt(
            args, manifest, bodies, raws, normalized, started, offline, registry
        )
    finally:
        journal.close()
        if worktree.exists():
            result = subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=root,
                capture_output=True,
                check=False,
            )
            if result.returncode:
                if receipt_path is not None:
                    receipt_path.unlink(missing_ok=True)
                raise DeepSeekReviewError("temporary worktree cleanup failed")
    return receipt_path


def _write_receipt(args, manifest, bodies, raws, normalized, started, offline, registry):
    binding = manifest["binding"]
    run_id = uuid.uuid4().hex
    stem = f"direct-deepseek-{binding['head_sha'][:12]}-{run_id}"
    prompt = canonical_json({"manifest": manifest, "requests": [json.loads(b) for b in bodies]})
    raw = canonical_json({"responses": [r.decode("utf-8") for r in raws]})
    final = canonical_json(
        {
            "protocol_version": PROTOCOL_VERSION,
            "review_result": normalized["review_result"],
            "findings": normalized["findings"],
        }
    )
    mode = "OFFLINE_FIXTURE" if offline else "DIRECT_HTTPS"
    receipt = {
        "protocol_version": PROTOCOL_VERSION,
        "receipt_version": "independent-review-receipt/v1",
        "review_run_id": run_id,
        "review_backend": backend.BACKEND_ID,
        "review_harness": backend.HARNESS_ID,
        "provider": "deepseek",
        "requested_model": backend.MODEL,
        "resolved_model": backend.MODEL,
        **{k: v for k, v in binding.items() if k != "repository"},
        "review_prompt_sha256": sha256_bytes(prompt),
        "review_started_at": started,
        "review_completed_at": _now(),
        "review_result": normalized["review_result"],
        "finding_counts_by_severity": normalized["finding_counts_by_severity"],
        "findings": normalized["findings"],
        "raw_output_sha256": sha256_bytes(raw),
        "final_result_sha256": sha256_bytes(final),
        "isolation": {
            "fresh_process": True,
            "fresh_context": True,
            "detached_worktree": True,
            "read_only": True,
            "worktree_head_sha": binding["head_sha"],
            "worktree_clean_before": True,
            "worktree_clean_after": True,
        },
        "provenance": {
            "runner_runtime_sha256": manifest["runtime_sha256"],
            "runner_version": backend.RUNNER_VERSION,
            "provider_endpoint": backend.ENDPOINT,
            "cost_policy_sha256": backend.POLICY_SHA,
            "review_plan_sha256": sha256_bytes(canonical_json(manifest)),
            "request_count": len(bodies),
            "execution_mode": mode,
            "artifact_stem": stem,
        },
    }
    if manifest.get("standalone") is not None:
        receipt["provenance"].update(standalone_provenance(manifest, bodies, raws))
    receipt["integrity"] = {"receipt_payload_sha256": receipts.receipt_payload_sha256(receipt)}
    execution = DirectExecutionEvidence(
        manifest, tuple(bodies), tuple(raws), manifest["runtime_sha256"], mode
    )
    context = receipts.ReceiptEvidenceContext(
        repo_root=args.repo_root.resolve(),
        base_sha=binding["base_sha"],
        head_sha=binding["head_sha"],
        mission_scope_path=binding["mission_scope_path"],
        prompt_bytes=prompt,
        raw_output_bytes=raw,
        final_result_bytes=final,
        direct_execution=execution,
    )
    receipts.validate_receipt(receipt, registry=registry, evidence_context=context)
    # 原始字节不可重新序列化成 Provider 成功证据。只保存已经验证的原 bytes 字符串。
    for suffix, data in (("prompt", prompt), ("raw", raw), ("final", final)):
        _write(args.evidence_dir / f"{stem}-{suffix}.json", data)
    path = args.evidence_dir / f"{stem}-receipt.json"
    _write(path, canonical_json(receipt))  # commit-last；fixture 清楚标记且正式 consumer 拒绝。
    return path


MAX_STANDALONE_REVIEW_POSTS = 9
SHA256_HEX_LENGTH = 64


def build_standalone_plan(args, scope, manifest, primary_bodies, chunks):
    """同一整轮计划：明确控制 GET + 四个资格 + 双仓库全部 chunks + 余额证据。"""
    config = standalone_config(scope)
    if (
        manifest["binding"]["base_sha"] != config["football_base"]
        or _git(args.repo_root, "merge-base", config["football_ancestor"], args.head_sha).strip()
        != config["football_ancestor"]
    ):
        raise backend.DirectError("PRIMARY_BASE")
    primary, _ = source_binding(
        args.repo_root.resolve(),
        args.base_sha,
        args.head_sha,
        origin="git@github.com:xupeng211/FootballPrediction.git",
    )
    companion, diff = companion_source(scope)
    qualification, contract = qualification_contract(scope)
    companion_chunks = plan(
        diff,
        base_sha=companion["base"],
        head_sha=companion["head"],
        mission_id=args.mission_id,
        mission_scope_sha256=manifest["binding"]["mission_scope_sha256"],
    )
    from scripts.devops import direct_deepseek_dispute as dispute

    review_limit = (
        dispute.MAX_REVIEWS if dispute.config(scope) is not None else MAX_STANDALONE_REVIEW_POSTS
    )
    if len(chunks.chunks) + len(companion_chunks.chunks) > review_limit:
        raise backend.DirectError("STANDALONE_REVIEW_CAPACITY")
    execution_id = getattr(args, "execution_id", None)
    price_sha = getattr(args, "price_sha256", None)
    credential_sha = getattr(args, "credential_sha256", None)
    if (
        not isinstance(execution_id, str)
        or not execution_id
        or not isinstance(price_sha, str)
        or len(price_sha) != SHA256_HEX_LENGTH
        or any(c not in "0123456789abcdef" for c in price_sha)
        or not isinstance(credential_sha, str)
        or len(credential_sha) != SHA256_HEX_LENGTH
        or any(c not in "0123456789abcdef" for c in credential_sha)
    ):
        raise backend.DirectError("FINAL_EXECUTION_PLAN_REQUIRED")

    def control(kind, url):
        return canonical_json({"method": "GET", "kind": kind, "endpoint": url})

    bodies = [
        control("price", backend.price_url(getattr(args, "currency", "USD"))),
        control("models", "https://api.deepseek.com/models"),
        control("balance_start", "https://api.deepseek.com/user/balance"),
    ]
    kinds = ["price", "models", "balance_start"]
    qualifiers = [
        backend.payload(qualification.qualification_prompt(c), qualification=True)
        for c in qualification.CASES
    ]
    bodies.extend(qualifiers)
    kinds.extend("qualification:" + c.name for c in qualification.CASES)
    bodies.extend(primary_bodies)
    kinds.extend("football:" + str(c.index) for c in chunks.chunks)
    bodies.extend(
        backend.payload(
            "Harness companion source (independent review required):\n"
            + build_chunk_prompt(
                chunk=c,
                source=diff[c.start : c.end],
                manifest=companion_chunks,
                scope_sha=manifest["binding"]["mission_scope_sha256"],
            )
        )
        for c in companion_chunks.chunks
    )
    kinds.extend("harness:" + str(c.index) for c in companion_chunks.chunks)
    bodies.append(control("balance_end", "https://api.deepseek.com/user/balance"))
    kinds.append("balance_end")
    unit = getattr(args, "currency", "USD")
    snapshot = getattr(args, "price_snapshot", None)
    if unit not in {"USD", "CNY"}:
        raise backend.DirectError("CURRENCY_POLICY")
    if snapshot is not None:
        backend.validate_price_snapshot(snapshot, unit, price_sha)
    elif unit != "USD":
        raise backend.DirectError("PRICE_SNAPSHOT_REQUIRED")
    manifest.pop("reserve_micro_usd")
    manifest.update(
        {
            "version": "direct-deepseek-standalone/v1",
            "source_bindings": {"football": primary, "harness": companion},
            "companion_chunk_manifest": companion_chunks.payload(),
            "standalone": {
                "primary_root": str(args.repo_root.resolve()),
                "execution_id": execution_id,
                "price_sha256": price_sha,
                "credential_sha256": credential_sha,
                "currency": unit,
                **({"price_snapshot": snapshot, "price_redirect_limit": 1} if snapshot else {}),
                "qualification_runtime": {
                    str(Path(m.__file__).relative_to(Path(config["harness_root"]))): sha256_bytes(
                        Path(m.__file__).read_bytes()
                    )
                    for m in (qualification, contract)
                },
                "request_kinds": kinds,
                "codex_invocations": 1,
                "codex_identity": {
                    "model": "gpt-5.6-terra",
                    "effort": "medium",
                    "binary_sha256": sha256_bytes(
                        Path("/usr/lib/chatgpt/resources/codex").read_bytes()
                    ),
                },
                "physical_cost_bound": "UNPROVEN",
                "billing_risk_exception": "OWNER_APPROVAL_REQUIRED",
            },
            "request_digests": [sha256_bytes(b) for b in bodies],
            "request_count": len(bodies),
            "max_http_attempts": len(bodies),
            backend.money_key("reserve", unit): sum(
                backend.request_cost(b, snapshot) for b in bodies
            ),
            "reserve_capacity_units": sum(
                backend.POLICY["context_capacity"] + backend.POLICY["max_output"]
                for b in bodies
                if json.loads(b).get("method") != "GET"
            ),
        }
    )
    if dispute.config(scope) is not None:
        _, football_diff = source_binding(
            args.repo_root.resolve(),
            args.base_sha,
            args.head_sha,
            origin="git@github.com:xupeng211/FootballPrediction.git",
        )
        bodies = dispute.extend_plan(
            scope, manifest, bodies, {"football": football_diff, "harness": diff}
        )
        manifest["request_digests"] = [sha256_bytes(b) for b in bodies]
        manifest["request_count"] = manifest["max_http_attempts"] = len(bodies)
        manifest[backend.money_key("reserve", unit)] = sum(
            backend.request_cost(b, snapshot) for b in bodies
        )
        manifest["reserve_capacity_units"] = sum(
            backend.POLICY["context_capacity"] + backend.POLICY["max_output"]
            for b in bodies
            if json.loads(b).get("method") != "GET"
        )
    manifest["review_identity"] = sha256_bytes(
        canonical_json(
            {k: v for k, v in manifest.items() if k not in {"review_identity", "execution_mode"}}
        )
    )
    return manifest, bodies, chunks


def validate_qualification(scope, index, result):
    """原资格语义、完整 finding coverage 和源引用规则均强制执行。"""
    qualification, contract = qualification_contract(scope)
    case = qualification.CASES[index]
    expected_findings = qualification.expected_findings(case)
    bound = contract.parse_synthesis(
        json.dumps(result), expected_findings, source=case.source.encode()
    )
    expected = {
        expected_findings[int(key[1:]) - 1]["finding_id"]: value
        for key, value in case.expected.items()
    }
    if {d["finding_id"]: d["decision"] for d in bound["decisions"]} != expected or bound[
        "new_findings"
    ]:
        raise backend.DirectError("QUALIFICATION_FAILED")


def rebuild_standalone_plan(manifest):
    """从真实 exact-HEAD scope 重建预留模板，不接受调用者合成计划。"""
    binding, standalone = manifest["binding"], manifest["standalone"]
    rebuilt, bodies, chunks = build_plan(
        argparse.Namespace(
            repo_root=Path(standalone["primary_root"]),
            base_sha=binding["base_sha"],
            head_sha=binding["head_sha"],
            mission_id=binding["mission_id"],
            mission_scope_file=Path(standalone["primary_root"]) / binding["mission_scope_path"],
            execution_id=standalone["execution_id"],
            price_sha256=standalone["price_sha256"],
            credential_sha256=standalone["credential_sha256"],
            currency=backend.currency(manifest),
            price_snapshot=standalone.get("price_snapshot"),
        )
    )
    rebuilt["execution_mode"] = manifest["execution_mode"]
    if rebuilt != manifest:
        raise backend.DirectError("DISPUTE_PLAN_CHANGED")
    return rebuilt, bodies, chunks


def validate_completed_prefix(manifest, prefix, index):  # noqa: C901
    """缺少前置响应、资格失败或任一审查阻断后禁止任何后续请求。"""
    if "dispute" in manifest["standalone"]:
        from scripts.devops import direct_deepseek_dispute as dispute

        if [i for i, _ in prefix] != list(range(index)):
            raise backend.DirectError("INCOMPLETE_REQUEST_PREFIX")
        _, planned, _ = rebuild_standalone_plan(manifest)
        dispute.replay(manifest, planned, [raw for _, raw in prefix])
        return
    if [i for i, _ in prefix] != list(range(index)):
        raise backend.DirectError("INCOMPLETE_REQUEST_PREFIX")
    for i, raw in prefix:
        kind = manifest["standalone"]["request_kinds"][i]
        value = json.loads(raw) if kind != "price" else None
        if kind == "price":
            if sha256_bytes(raw) != manifest["standalone"]["price_sha256"]:
                raise backend.DirectError("PRICE_CHANGED")
            snapshot = manifest["standalone"].get("price_snapshot")
            if (
                snapshot
                and backend.parse_price_snapshot(
                    raw,
                    source_url=snapshot["source_url"],
                    unit=backend.currency(manifest),
                    observed_at=snapshot["observed_at"],
                )
                != snapshot
            ):
                raise backend.DirectError("PRICE_CHANGED")
        if kind in {"balance_start", "balance_end"}:
            backend.balance_amount(value, backend.currency(manifest))
        if kind == "balance_start" and (
            backend.balance_amount(value, backend.currency(manifest))
            < manifest[backend.money_key("reserve", backend.currency(manifest))]
        ):
            raise backend.DirectError("INSUFFICIENT_BALANCE")
        if kind.startswith(("football:", "harness:")):
            result = json.loads(value["choices"][0]["message"]["content"])
            if result["review_result"] != "PASS":
                raise backend.DirectError("REVIEW_FAILED_STOP")


def standalone_result(scope, manifest, bodies, raws):
    """Consumer 重建每个请求、四项资格和完整双源 verdict，不接受调用者 PASS。"""
    if "dispute" in manifest["standalone"]:
        from scripts.devops import direct_deepseek_dispute as dispute

        _, planned, _ = rebuild_standalone_plan(manifest)
        replayed = dispute.replay(manifest, planned, raws)
        if not replayed["complete"] or tuple(bodies) != tuple(replayed["actual_bodies"]):
            raise backend.DirectError("DISPUTE_INCOMPLETE_OR_BODY_MISMATCH")
        return replayed["normalized"]
    kinds = manifest["standalone"]["request_kinds"]
    if len(raws) != len(bodies):
        raise backend.DirectError("INCOMPLETE_STANDALONE")
    findings = []
    for i, (body, raw, kind) in enumerate(zip(bodies, raws, kinds, strict=True)):
        result = backend.decode(raw, body)
        if kind.startswith("qualification:"):
            validate_qualification(scope, i - 3, result)
        elif kind.startswith(("football:", "harness:")):
            if result["review_result"] != "PASS":
                raise backend.DirectError("REVIEW_FAILED_STOP")
            findings.extend(result["findings"])
    validate_completed_prefix(manifest, list(enumerate(raws)), len(raws))
    from scripts.devops.independent_review_protocol import validate_result

    return validate_result(
        {"protocol_version": PROTOCOL_VERSION, "review_result": "PASS", "findings": findings}
    )


def standalone_provenance(manifest, bodies, raws):
    """资格证据与 companion 绑定同一计划及原始响应。"""
    extra = {}
    if "dispute" in manifest["standalone"]:
        from scripts.devops.direct_deepseek_dispute import replay

        _, planned, _ = rebuild_standalone_plan(manifest)
        extra["dispute_audit_sha256"] = sha256_bytes(
            canonical_json(replay(manifest, planned, raws)["audits"])
        )
    return {
        **extra,
        "standalone_identity": manifest["review_identity"],
        "source_bindings_sha256": sha256_bytes(canonical_json(manifest["source_bindings"])),
        "qualification_sha256": sha256_bytes(
            canonical_json(
                [
                    sha256_bytes(raws[i])
                    for i, k in enumerate(manifest["standalone"]["request_kinds"])
                    if k.startswith("qualification:")
                ]
            )
        ),
        "control_evidence_sha256": sha256_bytes(
            canonical_json(
                [
                    sha256_bytes(raws[i])
                    for i, b in enumerate(bodies)
                    if json.loads(b).get("method") == "GET"
                ]
            )
        ),
        "financial_status": "UNKNOWN_PENDING_PROVIDER_SETTLEMENT",
    }


def codex_standalone_guard(scope, *, root, base, head, scope_hash, receipt_path, claim_run_id=None):
    """DeepSeek 全部 PASS 才可认领唯一 canonical Codex；未知/失败认领禁止重发。"""
    if standalone_config(scope) is None:
        return None
    from scripts.devops.direct_deepseek_receipt_evidence import consume_direct

    if receipt_path is None:
        raise backend.DirectError("DEEPSEEK_FIRST_REQUIRED")
    receipt_path = Path(receipt_path)
    backend.private(receipt_path)
    evidence = consume_direct(
        receipt_path,
        repo_root=root,
        expected_base=base,
        expected_head=head,
        expected_mission_id=scope.mission_id,
        expected_scope_hash=scope_hash,
    )
    if not evidence.trusted or evidence.result != "PASS" or not evidence.standalone_identity:
        raise backend.DirectError("DEEPSEEK_FIRST_REQUIRED")
    result = {
        "deepseek_receipt_path": str(receipt_path.absolute()),
        "deepseek_receipt_sha256": sha256_bytes(receipt_path.read_bytes()),
        "standalone_identity": evidence.standalone_identity,
        "source_bindings_sha256": evidence.source_bindings_sha256,
        "qualification_sha256": evidence.qualification_sha256,
    }
    journal = backend.Journal()
    try:
        saved = journal.db.execute(
            "SELECT manifest FROM reviews WHERE id=?", (evidence.standalone_identity,)
        ).fetchone()
        if not saved:
            raise backend.DirectError("STANDALONE_LEDGER_REQUIRED")
        manifest = json.loads(saved[0])
        if manifest["standalone"]["codex_identity"] != {
            "model": "gpt-5.6-terra",
            "effort": "medium",
            "binary_sha256": sha256_bytes(Path("/usr/lib/chatgpt/resources/codex").read_bytes()),
        }:
            raise backend.DirectError("CODEX_RUNTIME_CHANGED")
        if claim_run_id is not None:
            try:
                journal.db.execute(
                    "INSERT INTO codex_attempts VALUES(?,?,?)",
                    (evidence.standalone_identity, claim_run_id, result["deepseek_receipt_sha256"]),
                )
                journal.db.commit()  # 在真实 invocation 前持久化；失败/UNKNOWN 不重认领。
            except Exception:
                journal.db.rollback()
                raise backend.DirectError("CODEX_ALREADY_CLAIMED_NO_REPLAY") from None
        else:
            attempt = journal.db.execute(
                "SELECT receipt_sha256,run_id FROM codex_attempts WHERE review_id=?",
                (evidence.standalone_identity,),
            ).fetchone()
            if not attempt or attempt[0] != result["deepseek_receipt_sha256"]:
                raise backend.DirectError("CODEX_ATTEMPT_NOT_BOUND")
    finally:
        journal.close()
    result["codex_run_id"] = claim_run_id if claim_run_id is not None else attempt[1]
    return result


def validate_codex_standalone_binding(receipt, scope, root, raw_path):
    """复用同一 Direct consumer 与一次性认领，不扩展 receipt authority。"""
    provenance = receipt["provenance"]
    base, head = receipt["base_sha"].lower(), receipt["reviewed_head_sha"].lower()
    scope_hash = receipt["mission_scope_sha256"]
    if standalone_config(scope) is None:
        if "standalone" in provenance:
            raise backend.DirectError("UNEXPECTED_STANDALONE")
        return
    declared = provenance.get("standalone") or {}
    expected = codex_standalone_guard(
        scope,
        root=root,
        base=base,
        head=head,
        scope_hash=scope_hash,
        receipt_path=declared.get("deepseek_receipt_path"),
    )
    expected_raw = f"codex-review-output-{head[:12]}-{expected['codex_run_id']}.jsonl"
    if declared != expected or raw_path.name != expected_raw:
        raise backend.DirectError("STANDALONE_EVIDENCE_MISMATCH")


def standalone_evidence_fields(receipt):
    """只有已验证 receipt 的三项双审同源事实进入原 policy。"""
    value = receipt.get("provenance", {}).get("standalone", {})
    return {
        field: value.get(field)
        for field in ("standalone_identity", "source_bindings_sha256", "qualification_sha256")
    }


def main(argv=None):
    """显式 plan-only 或受阻断的 Direct CLI 入口。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    for name in ("base-sha", "head-sha", "mission-id"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--mission-scope-file", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--authorization-file", type=Path)
    parser.add_argument("--execution-id")
    parser.add_argument("--price-sha256")
    parser.add_argument("--credential-sha256")
    parser.add_argument("--currency", choices=("USD", "CNY"), default="USD")
    parser.add_argument("--price-snapshot-file", type=Path)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        args.price_snapshot = (
            json.loads(args.price_snapshot_file.read_bytes()) if args.price_snapshot_file else None
        )
        if args.plan_only:
            manifest, _, _ = build_plan(args)
            print(json.dumps({"review_plan": manifest}))
        else:
            print(json.dumps({"review_receipt": str(run_review(args)), "status": "COMPLETE"}))
    except Exception:
        print("DIRECT_DEEPSEEK_REVIEW=NO_VERDICT", file=sys.stderr)
        return 1
    else:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
