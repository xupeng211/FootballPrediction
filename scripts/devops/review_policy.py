#!/usr/bin/env python3
"""Canonical, fail-closed multi-backend independent-review policy.

The evaluator intentionally receives only already validated receipt facts.  It
does not invoke a provider and it never treats a runtime failure as a review
verdict.  Callers must validate Codex/Claude evidence with their respective
receipt validators before constructing ``ReviewEvidence``.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

from scripts.devops.independent_review_receipt import load_backend_registry

BACKEND_CODEX = "codex-cli"
BACKEND_DEEPSEEK = "claude-code-deepseek"
WORKFLOW_NORMAL = "NORMAL"
WORKFLOW_STRICT = "STRICT"
WORKFLOW_CRITICAL = "CRITICAL"
WORKFLOW_CLASSES = frozenset({WORKFLOW_NORMAL, WORKFLOW_STRICT, WORKFLOW_CRITICAL})
BLOCKING_SEVERITIES = ("P0", "P1", "P2")
BACKEND_REGISTRY_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "agentic" / "independent_review_backends.json"
)
VALIDATED_FACTS_MARKER = "independent-review-receipt-validator/v1"


@dataclass(frozen=True)
class CandidateBinding:
    """Exact candidate identity shared by every trusted review receipt."""

    base_sha: str
    head_sha: str
    diff_sha256: str
    mission_id: str
    mission_scope_sha256: str


@dataclass(frozen=True)
class ReviewEvidence:
    """A receipt fact set that a backend-specific validator already trusted."""

    backend_id: str
    trusted: bool
    result: str
    base_sha: str
    head_sha: str
    diff_sha256: str
    mission_id: str
    mission_scope_sha256: str
    finding_counts_by_severity: dict[str, int]
    infrastructure_failure: bool = False
    # Backend validators may expose the model that produced this trusted
    # evidence. The policy evaluator itself remains backend-neutral.
    review_model: str | None = None


@dataclass(frozen=True)
class PolicyResult:
    """Fail-closed evaluation result for one candidate and risk tier."""

    status: str
    reasons: tuple[str, ...]
    required_backends: tuple[str, ...]
    satisfied_backends: tuple[str, ...]
    p3_findings: int
    fallback_policy: str = "EXPLICIT_ONLY"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable policy result."""

        return asdict(self)


def required_backends(
    workflow_class: str, *, selected_backend: str | None = None
) -> tuple[str, ...]:
    """Return policy-owned backends; no registry ordering or environment is read."""

    if workflow_class == WORKFLOW_NORMAL:
        if selected_backend is None:
            return (BACKEND_DEEPSEEK,)
        if selected_backend not in {BACKEND_DEEPSEEK, BACKEND_CODEX}:
            raise ValueError("BACKEND_NOT_ALLOWED")
        return (selected_backend,)
    if workflow_class == WORKFLOW_STRICT:
        if selected_backend not in {None, BACKEND_CODEX}:
            raise ValueError("BACKEND_NOT_ALLOWED")
        return (BACKEND_CODEX,)
    if workflow_class == WORKFLOW_CRITICAL:
        if selected_backend is not None:
            raise ValueError("CRITICAL_BACKEND_OVERRIDE_FORBIDDEN")
        return (BACKEND_CODEX, BACKEND_DEEPSEEK)
    raise ValueError("UNKNOWN_WORKFLOW_CLASS")


def load_active_backend_eligibility(path: Path) -> dict[str, frozenset[str]]:
    """Return eligibility from the repository-controlled active registry."""

    return {
        backend_id: frozenset(value["task_eligibility"])
        for backend_id, value in load_backend_registry(path).items()
        if value["status"] == "active"
    }


def _counts(value: object) -> tuple[int, int]:
    if (
        not isinstance(value, dict)
        or set(value) != {"P0", "P1", "P2", "P3"}
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in value.values()
        )
    ):
        raise ValueError("INVALID_FINDING_COUNTS")
    return sum(value[level] for level in BLOCKING_SEVERITIES), value["P3"]


def evaluate_review_policy(  # noqa: C901, PLR0912, PLR0915
    workflow_class: str,
    candidate: CandidateBinding,
    available_receipts: Iterable[ReviewEvidence],
    *,
    selected_backend: str | None = None,
    backend_eligibility: Mapping[str, frozenset[str]] | None = None,
) -> PolicyResult:
    """Aggregate independent validated receipts for one exact candidate.

    Receipt facts that are malformed, untrusted, mismatched, or duplicated are
    invalid evidence.  Missing/infrastructure/negative review outcomes are
    unsatisfied policy, never an invitation to fall back silently.
    """

    try:
        required = required_backends(workflow_class, selected_backend=selected_backend)
    except ValueError as exc:
        return PolicyResult("INVALID", (str(exc),), (), (), 0)
    if backend_eligibility is None:
        try:
            eligibility = load_active_backend_eligibility(BACKEND_REGISTRY_PATH)
        except (OSError, TypeError, ValueError):
            # The repository registry is the policy authority.  A missing or
            # malformed registry must never resurrect a hardcoded allow-list.
            eligibility = {}
    else:
        eligibility = backend_eligibility
    if any(workflow_class not in eligibility.get(backend, frozenset()) for backend in required):
        return PolicyResult("INVALID", ("BACKEND_NOT_ELIGIBLE",), required, (), 0)
    receipts = tuple(available_receipts)
    by_backend: dict[str, ReviewEvidence] = {}
    seen_backends: set[str] = set()
    reasons: list[str] = []
    p3 = 0
    for receipt in receipts:
        if receipt.backend_id not in {BACKEND_CODEX, BACKEND_DEEPSEEK}:
            reasons.append("BACKEND_NOT_ALLOWED")
            continue
        # Advisory receipts are recorded separately, but only policy-owned
        # backends may affect merge readiness.  A DeepSeek advisory receipt
        # cannot invalidate STRICT's required Codex approval.
        if receipt.backend_id not in required:
            continue
        duplicate = receipt.backend_id in seen_backends
        seen_backends.add(receipt.backend_id)
        try:
            blocking, receipt_p3 = _counts(receipt.finding_counts_by_severity)
        except ValueError as exc:
            reasons.append(str(exc))
            if duplicate:
                reasons.append("DUPLICATE_BACKEND_RECEIPT")
            continue
        if duplicate:
            reasons.append("DUPLICATE_BACKEND_RECEIPT")
            continue
        by_backend[receipt.backend_id] = receipt
        p3 += receipt_p3
        if receipt.infrastructure_failure:
            reasons.append("REVIEW_INFRASTRUCTURE_BLOCK")
            continue
        if not receipt.trusted:
            reasons.append("INVALID_PROVENANCE")
        if (
            receipt.base_sha,
            receipt.head_sha,
            receipt.diff_sha256,
            receipt.mission_id,
            receipt.mission_scope_sha256,
        ) != (
            candidate.base_sha,
            candidate.head_sha,
            candidate.diff_sha256,
            candidate.mission_id,
            candidate.mission_scope_sha256,
        ):
            reasons.append("SAME_CANDIDATE_BINDING_MISMATCH")
        if receipt.result != "PASS" or blocking:
            reasons.append("REVIEW_FINDINGS_BLOCK")
    if reasons:
        return PolicyResult(
            "INVALID"
            if any(
                reason.startswith("INVALID")
                or reason
                in {
                    "BACKEND_NOT_ALLOWED",
                    "DUPLICATE_BACKEND_RECEIPT",
                    "SAME_CANDIDATE_BINDING_MISMATCH",
                }
                for reason in reasons
            )
            else "UNSATISFIED",
            tuple(sorted(set(reasons))),
            required,
            (),
            p3,
        )

    satisfied: list[str] = []
    for backend in required:
        receipt = by_backend.get(backend)
        if receipt is None:
            reasons.append(f"MISSING_{backend.upper().replace('-', '_')}_RECEIPT")
        else:
            satisfied.append(backend)
    if reasons:
        return PolicyResult(
            "UNSATISFIED", tuple(sorted(set(reasons))), required, tuple(satisfied), p3
        )
    return PolicyResult("SATISFIED", (), required, tuple(satisfied), p3)


def _evidence(value: object) -> ReviewEvidence:
    if not isinstance(value, dict):
        raise TypeError("INVALID_RECEIPT_FACTS")
    if value.get("validated_by") != VALIDATED_FACTS_MARKER:
        raise ValueError("UNVALIDATED_RECEIPT_FACTS")
    return ReviewEvidence(
        backend_id=str(value.get("backend_id", "")),
        trusted=value.get("trusted") is True,
        result=str(value.get("result", "")),
        base_sha=str(value.get("base_sha", "")),
        head_sha=str(value.get("head_sha", "")),
        diff_sha256=str(value.get("diff_sha256", "")),
        mission_id=str(value.get("mission_id", "")),
        mission_scope_sha256=str(value.get("mission_scope_sha256", "")),
        finding_counts_by_severity=value.get("finding_counts_by_severity", {}),
        infrastructure_failure=value.get("infrastructure_failure") is True,
    )


def _policy_object(value: object) -> dict[str, Any]:
    """Require one JSON object before constructing trusted policy facts."""

    if not isinstance(value, dict):
        raise TypeError("INVALID_POLICY_INPUT")
    return value


def _policy_list(value: object) -> list[object]:
    """Require the receipt JSON envelope to be an array."""

    if not isinstance(value, list):
        raise TypeError("INVALID_POLICY_INPUT")
    return value


def main(argv: list[str] | None = None) -> int:
    """Evaluate receipt facts supplied by the command-line policy harness."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-class", required=True)
    parser.add_argument("--candidate-json", required=True)
    parser.add_argument("--receipts-json", required=True)
    parser.add_argument("--selected-backend")
    args = parser.parse_args(argv)
    try:
        candidate_value = json.loads(args.candidate_json)
        receipts_value = json.loads(args.receipts_json)
        candidate = CandidateBinding(**_policy_object(candidate_value))
        receipts = [_evidence(value) for value in _policy_list(receipts_value)]
        result = evaluate_review_policy(
            args.workflow_class, candidate, receipts, selected_backend=args.selected_backend
        )
    except (KeyError, TypeError, ValueError) as exc:
        result = PolicyResult("INVALID", (str(exc),), (), (), 0)
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0 if result.status == "SATISFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
