"""未启用的风险审核迁移候选；只规划，不发请求、不签 receipt、不授权合并。

Lifecycle: permanent
Owner: engineering workflow governance

输入是未来 backend validator 的可信观察事实，绝不是 provider 自报的 JSON。
现行 review_policy/agent-merge-ready 保持唯一生产 authority。即使候选评价成功，
本模块的 merge_ready 和 dispatch_authorized 仍恒为 False。
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any, TypeGuard, cast

from scripts.devops.independent_review_protocol import validate_result
from scripts.devops.review_policy import CandidateBinding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

QUALIFIED = "QUALIFIED"
FAILURE_REASONS = frozenset(
    {"TIMEOUT", "OUTPUT_EXHAUSTED", "SERVICE_UNAVAILABLE", "AUTH_FAILURE", "NO_VERDICT"}
)
ISOLATION = frozenset(
    {"fresh_process", "fresh_session", "detached_read_only_worktree", "no_other_review_results"}
)
CRITICAL_SLOT_COUNT = 2
MAX_OPTIONS_PER_SLOT = 2
MAX_PHYSICAL_ATTEMPTS = 4
MAX_OUTPUT_TOKENS = 16_384
MAX_INPUT_TOKENS = 1_048_576
MAX_WALL_SECONDS = 900
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True)
class ReviewerProfile:
    """资格证据须绑定准确 recipe，而非仅记录厂商名称。"""

    profile_id: str
    provider_id: str
    model: str
    recipe_sha256: str
    qualification_status: str
    qualification_evidence_sha256: str | None
    task_eligibility: tuple[str, ...]
    input_token_bound: int | None
    output_token_bound: int | None
    wall_seconds: int | None
    physical_attempt_bound: int | None


@dataclass(frozen=True)
class ValidatedAttempt:
    """包含失败的原始证据引用；UNKNOWN 从不释放 reservation。"""

    profile_id: str
    candidate: CandidateBinding
    recipe_sha256: str
    evidence_sha256: str
    session_id: str
    worktree_id: str
    isolation: tuple[str, ...]
    facts_validated: bool
    terminal_known: bool
    physical_attempts: int
    input_tokens: int | None
    output_tokens: int | None
    coverage_diff_sha256: str
    result: dict[str, Any] | None
    failure_reason: str | None = None


@dataclass(frozen=True)
class RecoveryDecision:
    """候选结果不能被旧 Gate 误认作 SATISFIED/PASS。"""

    status: str
    reason: str
    next_profile_id: str | None = None
    independence: str = "NOT_ESTABLISHED"
    physical_attempts_observed: int = 0
    reserved_input_tokens: int = 0
    reserved_output_tokens: int = 0
    evidence_sha256: tuple[str, ...] = ()
    p3_findings: int = 0
    dispatch_authorized: bool = False
    merge_ready: bool = False
    manual_approval_required: bool = True


def _positive(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _qualified(profile: ReviewerProfile, workflow_class: str) -> bool:
    return (
        profile.qualification_status == QUALIFIED
        and bool(profile.qualification_evidence_sha256)
        and HEX64.fullmatch(profile.qualification_evidence_sha256 or "") is not None
        and HEX64.fullmatch(profile.recipe_sha256) is not None
        and bool(profile.provider_id and profile.model)
        and workflow_class in profile.task_eligibility
        and _positive(profile.physical_attempt_bound)
        and profile.physical_attempt_bound == 1
        and _positive(profile.input_token_bound)
        and profile.input_token_bound <= MAX_INPUT_TOKENS
        and _positive(profile.output_token_bound)
        and profile.output_token_bound <= MAX_OUTPUT_TOKENS
        and _positive(profile.wall_seconds)
        and profile.wall_seconds <= MAX_WALL_SECONDS
    )


def evaluate_recovery_candidate(  # noqa: C901, PLR0911, PLR0912, PLR0915
    workflow_class: str,
    candidate: CandidateBinding,
    profiles: Mapping[str, ReviewerProfile],
    slots: Sequence[Sequence[str]],
    attempts: Sequence[ValidatedAttempt],
    *,
    builder_session_id: str,
) -> RecoveryDecision:
    """每个 slot 最多一次已知故障替代；任意有效 finding 先于选模处理。

    slot 顺序来自预先审阅的候选策略。不能因 FAIL 更换 profile，不能重复同一
    profile，也不能把一个 session/worktree 的结果用于两个 slot。尚未资格的
    profile 不参与 dispatch 建议。敏感路径的人工批准不在这个模块授予。
    """

    observed = sum(a.physical_attempts for a in attempts if _positive(a.physical_attempts))
    evidence = tuple(a.evidence_sha256 for a in attempts)
    reserved_input = 0
    reserved_output = 0
    p3 = 0

    def decision(
        status: str, reason: str, next_id: str | None = None, independence: str = "NOT_ESTABLISHED"
    ) -> RecoveryDecision:
        return RecoveryDecision(
            status,
            reason,
            next_id,
            independence,
            observed,
            reserved_input,
            reserved_output,
            evidence,
            p3,
        )

    if (
        workflow_class not in {"NORMAL", "STRICT", "CRITICAL"}
        or not builder_session_id.strip()
        or not HEX40.fullmatch(candidate.base_sha)
        or not HEX40.fullmatch(candidate.head_sha)
        or not HEX64.fullmatch(candidate.diff_sha256)
        or not HEX64.fullmatch(candidate.mission_scope_sha256)
        or not candidate.mission_id.strip()
        or len(slots) != (CRITICAL_SLOT_COUNT if workflow_class == "CRITICAL" else 1)
        or any(not slot or len(slot) > MAX_OPTIONS_PER_SLOT for slot in slots)
    ):
        return decision("INVALID", "INVALID_RISK_OR_BINDING_OR_SLOT_PLAN")
    planned = [name for slot in slots for name in slot]
    if len(set(planned)) != len(planned) or any(name not in profiles for name in planned):
        return decision("INVALID", "AMBIGUOUS_OR_UNKNOWN_PROFILE_PLAN")
    if len(attempts) > MAX_PHYSICAL_ATTEMPTS or observed > MAX_PHYSICAL_ATTEMPTS:
        return decision("BLOCKED_BUDGET", "PHYSICAL_ATTEMPT_LIMIT")
    used: dict[str, ValidatedAttempt] = {}
    sessions: set[str] = set()
    worktrees: set[str] = set()
    findings = False
    for attempt in attempts:
        profile = profiles.get(attempt.profile_id)
        if (
            profile is None
            or attempt.profile_id not in planned
            or attempt.profile_id in used
            or attempt.facts_validated is not True
            or attempt.candidate != candidate
            or attempt.recipe_sha256 != profile.recipe_sha256
            or not HEX64.fullmatch(attempt.evidence_sha256)
            or attempt.coverage_diff_sha256 != candidate.diff_sha256
            or not _qualified(profile, workflow_class)
            or not _positive(attempt.physical_attempts)
            or attempt.physical_attempts != 1
            or not attempt.session_id.strip()
            or attempt.session_id == builder_session_id
            or attempt.session_id in sessions
            or not attempt.worktree_id.strip()
            or attempt.worktree_id in worktrees
            or set(attempt.isolation) != ISOLATION
        ):
            return decision("INVALID", "INVALID_PROVENANCE_BINDING_COVERAGE_OR_INDEPENDENCE")
        used[attempt.profile_id] = attempt
        sessions.add(attempt.session_id)
        worktrees.add(attempt.worktree_id)
        reserved_input += cast("int", profile.input_token_bound)
        reserved_output += cast("int", profile.output_token_bound)
        if attempt.result is not None:
            try:
                result = validate_result(attempt.result)
            except ValueError:
                return decision("INVALID", "INVALID_VERDICT")
            findings |= result["blocking_findings"] > 0
            p3 += result["finding_counts_by_severity"]["P3"]
            if attempt.failure_reason is not None:
                return decision("INVALID", "FAILURE_CANNOT_DISGUISE_A_VERDICT")
        elif attempt.failure_reason not in FAILURE_REASONS:
            return decision("INVALID", "UNSUPPORTED_FAILURE_TRIGGER")
    # Every valid P0/P1/P2 is retained even when its slot is not ultimately used.
    if findings:
        return decision("BLOCKED_FINDINGS", "FIX_AND_REVIEW_NEW_HEAD; NO_VERDICT_SHOPPING")
    for attempt in attempts:
        profile = profiles[attempt.profile_id]
        if (
            attempt.terminal_known is not True
            or attempt.input_tokens is None
            or attempt.output_tokens is None
        ):
            return decision("UNKNOWN", "RETAIN_ALL_RESERVATIONS; STOP")
        if (
            any(
                isinstance(t, bool) or not isinstance(t, int) or t < 0
                for t in (attempt.input_tokens, attempt.output_tokens)
            )
            or attempt.input_tokens > cast("int", profile.input_token_bound)
            or attempt.output_tokens > cast("int", profile.output_token_bound)
        ):
            return decision("INVALID", "USAGE_BOUND_VIOLATION")
    completed: list[ReviewerProfile] = []
    position = 0
    for slot in slots:
        eligible = [name for name in slot if _qualified(profiles[name], workflow_class)]
        if not eligible:
            return decision("QUALIFICATION_REQUIRED", "NO_QUALIFIED_PROFILE_FOR_SLOT")
        satisfied = False
        for name in eligible:
            slot_attempt = used.get(name)
            if slot_attempt is None:
                if position != len(attempts):
                    return decision("INVALID", "OUT_OF_ORDER_OR_UNAPPROVED_SUBSTITUTION")
                return decision(
                    "PROPOSED_NEXT_REVIEW", "OWNER_ADOPTION_REQUIRED; NO_DISPATCH", name
                )
            if attempts[position].profile_id != name:
                return decision("INVALID", "OUT_OF_ORDER_OR_UNAPPROVED_SUBSTITUTION")
            position += 1
            if slot_attempt.result is not None:
                completed.append(profiles[name])
                satisfied = True
                break
        if not satisfied:
            return decision("NO_VERDICT", "APPROVED_SLOT_OPTIONS_EXHAUSTED; STOP")
    if position != len(attempts):
        return decision("INVALID", "EXTRA_OR_VERDICT_SHOPPING_ATTEMPTS")
    independence = "SINGLE_REVIEW"
    if len(completed) == CRITICAL_SLOT_COUNT:
        independence = (
            "CROSS_PROVIDER"
            if completed[0].provider_id != completed[1].provider_id
            else "SAME_PROVIDER"
        )
        if independence == "SAME_PROVIDER" and completed[0].model == completed[1].model:
            return decision(
                "QUALIFICATION_REQUIRED",
                "SAME_MODEL_DUAL_REVIEW_NOT_QUALIFIED",
                independence=independence,
            )
    return decision(
        "PROPOSED_EVIDENCE_COMPLETE",
        "OWNER_ADOPTION_AND_EXISTING_GATES_REQUIRED",
        independence=independence,
    )


def main(argv: list[str] | None = None) -> int:
    """只读 preview；无 activation flag，永不返回可当作 approval 的 exit 0。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts-file", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.facts_file.read_text())
        candidate = CandidateBinding(**data["candidate"])
        profiles = {p["profile_id"]: ReviewerProfile(**p) for p in data["profiles"]}
        if len(profiles) != len(data["profiles"]):
            raise ValueError("DUPLICATE_PROFILE")  # noqa: TRY301
        attempts = [
            ValidatedAttempt(**{**a, "candidate": CandidateBinding(**a["candidate"])})
            for a in data["attempts"]
        ]
        result = evaluate_recovery_candidate(
            data["workflow_class"],
            candidate,
            profiles,
            data["slots"],
            attempts,
            builder_session_id=data["builder_session_id"],
        )
        output = asdict(result)
    except (KeyError, TypeError, ValueError, OSError):
        output = {
            "status": "INVALID",
            "reason": "INVALID_PREVIEW_INPUT",
            "merge_ready": False,
            "dispatch_authorized": False,
        }
    print(json.dumps(output, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
