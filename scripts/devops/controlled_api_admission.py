"""校验新通道的完整离线证据，准备迁移；不授予资格或生成正式 Receipt。

lifecycle: permanent
owner: engineering workflow governance
复用 exact source、结果合同及正式 policy，禁止把 Mock 或完整传输当成独立审核。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat

from scripts.devops.codex_review_verdict import assert_owner_only_directory
from scripts.devops.controlled_api_binding import (
    HTTPS_CHANNEL,
    bind_source,
    qualification_requirements,
)
from scripts.devops.controlled_api_budget import STATE_FILE_MODE, Budget
from scripts.devops.controlled_api_policy import PROFILES, ControlError, source_identity
from scripts.devops.controlled_api_runner import MAX_RESPONSE_BYTES, _decode
from scripts.devops.independent_review_protocol import (
    PROTOCOL_VERSION,
    canonical_json,
    sha256_bytes,
    validate_result,
)
from scripts.devops.review_policy import CandidateBinding, evaluate_review_policy

ARTIFACT_FIELDS = {
    "schema",
    "channel",
    "reviewer_identity",
    "provider",
    "qualification_status",
    "source",
    "execution",
    "slot",
    "request_sha256",
    "policy_sha256",
    "model",
    "response_sha256",
    "result",
    "current_approval_eligible",
    "qualification_required",
}


def _read_private(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != STATE_FILE_MODE
            or info.st_nlink != 1
            or info.st_size > MAX_RESPONSE_BYTES
        ):
            raise ControlError("UNSAFE_CANDIDATE_RESULT")
        raw = stream.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ControlError("CANDIDATE_RESULT_TOO_LARGE")
    return raw


def _artifact(budget: Budget, evidence: dict, slot: dict) -> dict:
    raw = _read_private(budget.root / f"result-{evidence['identity']}-{slot['slot']}.json")
    artifact = _decode(raw)
    provider = slot["provider"]
    if provider not in PROFILES or slot["model"] != PROFILES[provider].model:
        raise ControlError("UNKNOWN_REVIEWER_MODEL")
    expected = {
        "schema": "controlled-api-unqualified-result/v1",
        "channel": HTTPS_CHANNEL,
        "reviewer_identity": f"{HTTPS_CHANNEL}/{provider}",
        "provider": provider,
        "qualification_status": "NOT_RUN",
        "source": evidence["source"],
        "execution": evidence["execution"],
        "slot": slot["slot"],
        "request_sha256": slot["request_sha256"],
        "policy_sha256": slot["policy_sha256"],
        "model": slot["model"],
        "response_sha256": slot["response_sha256"],
        "current_approval_eligible": False,
        "qualification_required": True,
    }
    if not isinstance(artifact, dict) or set(artifact) != ARTIFACT_FIELDS:
        raise ControlError("INVALID_CANDIDATE_RESULT")
    if canonical_json({k: artifact[k] for k in expected}) != canonical_json(expected):
        raise ControlError("CANDIDATE_RESULT_BINDING_MISMATCH")
    result = artifact["result"]
    normalized = validate_result(
        {
            "protocol_version": PROTOCOL_VERSION,
            "review_result": result["review_result"],
            "findings": result["findings"],
        }
    )
    if canonical_json(normalized) != canonical_json(result):
        raise ControlError("CANDIDATE_RESULT_COUNTS_MISMATCH")
    return {
        "slot": slot["slot"],
        "reviewer_identity": expected["reviewer_identity"],
        "model": slot["model"],
        "artifact_sha256": sha256_bytes(raw),
        "result": normalized,
    }


def prepare_admission(
    project: Path, base: str, head: str, mission: str, scope_path: str, budget: Budget, task: str
) -> dict:
    """只读验证同一 exact source 的所有槽；缺块/UNKNOWN/换身份均拒绝准备。

    完整结果也永远不作为 ReviewEvidence 交给 policy；不存在 caller-supplied trusted 开关。
    本地 hash 仅提供完整性，不提供独立身份或 hostile-builder resistance。
    """
    source = bind_source(project, base, head, mission, scope_path)
    if task != source_identity(source):
        raise ControlError("CANDIDATE_TASK_MISMATCH")
    evidence = budget.evidence(task)
    if evidence["source"] != source:
        raise ControlError("CANDIDATE_SOURCE_MISMATCH")
    slots = evidence["slots"]
    if not slots or any(
        slot["state"] != "COMPLETE" or slot["category"] != "VALID_LOCAL_TLS_RESPONSE"
        for slot in slots
    ):
        raise ControlError("INCOMPLETE_CANDIDATE_RESULTS")
    if {slot["provider"] for slot in slots} != {"openai", "deepseek"}:
        raise ControlError("TWO_PROVIDER_RESULTS_REQUIRED")
    observed = [_artifact(budget, evidence, slot) for slot in slots]
    binding = CandidateBinding(
        base_sha=source["base"],
        head_sha=source["head"],
        diff_sha256=source["diff_sha256"],
        mission_id=source["mission"],
        mission_scope_sha256=source["scope_sha256"],
    )
    return {
        "schema": "controlled-api-admission-preparation/v1",
        "source": source,
        "candidate_binding": vars(binding),
        "execution": evidence["execution"],
        "execution_evidence_sha256": sha256_bytes(canonical_json(evidence)),
        "observed_results": observed,
        "offline_conformance": "COMPLETE_NOT_INDEPENDENT_REVIEW",
        "reviewer_requirements": [qualification_requirements(p) for p in ("openai", "deepseek")],
        "formal_policy": evaluate_review_policy("CRITICAL", binding, ()).to_dict(),
        "formal_receipt_status": "NOT_SUPPORTED_PENDING_APPROVED_MIGRATION",
        "qualification_status": "NOT_RUN",
        "physical_cost_hard_bound": "NOT_PROVEN",
        "current_approval_eligible": False,
        "ready_for_real_review": False,
    }


def save_preparation(bundle: dict, output: Path, *, project: Path) -> None:
    """只新建仓库外 owner-only 迁移工件，绝不覆盖正式或历史证据。"""
    if (
        bundle.get("schema") != "controlled-api-admission-preparation/v1"
        or bundle.get("current_approval_eligible") is not False
        or bundle.get("ready_for_real_review") is not False
        or bundle.get("qualification_status") != "NOT_RUN"
    ):
        raise ControlError("NONAUTHORIZING_PREPARATION_REQUIRED")
    output = output.absolute()
    if project.resolve() == output.resolve() or project.resolve() in output.resolve().parents:
        raise ControlError("EXTERNAL_PREPARATION_REQUIRED")
    if any(p.is_symlink() for p in (output.parent, *output.parent.parents)):
        raise ControlError("UNSAFE_PREPARATION_PATH")
    assert_owner_only_directory(output.parent)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical_json(bundle))
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> int:
    """零 Provider 的 Controller 准备入口，exit 0仅表示准备完成，不表示审核通过。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--mission", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        bundle = prepare_admission(
            args.project,
            args.base,
            args.head,
            args.mission,
            args.scope,
            Budget(args.state_root),
            args.task,
        )
        save_preparation(bundle, args.output, project=args.project)
    except Exception:
        print("ADMISSION_PREPARATION_REJECTED")
        return 1
    print("PREPARATION_SAVED_NOT_APPROVAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
