#!/usr/bin/env python3
"""Integrity and registry helpers for additive generic review receipts.

lifecycle: permanent
owner: engineering workflow governance
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from scripts.devops.codex_review_contract import (
    REVIEW_REASONING_EFFORT_PINNED,
    reviewer_selectors_from_command,
)
from scripts.devops.codex_review_output import (
    assert_successful_completion,
    parse_json_lines,
    reviewer_invocation_id,
)
from scripts.devops.codex_review_provenance import ReviewReceiptError
from scripts.devops.independent_review_protocol import (
    PROTOCOL_VERSION,
    RECEIPT_VERSION,
    IndependentReviewProtocolError,
    canonical_json,
    sha256_bytes,
    validate_result,
    validate_sha,
)
from scripts.devops.deepseek_review_chunks import ChunkReviewError, plan, validate_manifest
from scripts.ops.helpers.agent_workflow_contract import (
    MissionScopeError,
    MissionScopeReferenceError,
)
from scripts.ops.helpers.agent_workflow_scope_context import (
    load_mission_scope_blob,
    validate_mission_scope_reference_path,
)

ROOT = Path(__file__).resolve().parents[2]
RECEIPT_SCHEMA_PATH = ROOT / "schemas" / "agentic" / "independent_review_receipt.schema.json"
_MISSION_ID_RE = __import__("re").compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_CODEX_THREAD_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{4,256}$")
_CODEX_EXEC_MINIMUM_ARGV_LENGTH = 2
_CLAUDE_DEEPSEEK_ENDPOINT = "https://api.deepseek.com/anthropic"
_CLAUDE_DEEPSEEK_MODEL = "deepseek-flash"
_CLAUDE_MINIMUM_VERSION = (2, 1, 276)
_CLAUDE_RESTRICTED_TOOLS = frozenset(
    {"Bash", "Edit", "Write", "Read", "Glob", "Grep", "WebFetch", "WebSearch"}
)


@dataclass(frozen=True)
class CodexExecutionEvidence:
    """Trusted execution facts captured by the Codex review harness.

    These values deliberately do not come from the receipt. The generic
    receipt can claim provenance, but a caller must supply the facts observed
    while invoking the backend before that claim can be accepted.
    """

    reviewer_command: tuple[str, ...]
    resolved_model: str
    codex_cli_version: str
    codex_binary_sha256: str
    thread_id: str


@dataclass(frozen=True)
class ClaudeDeepSeekExecutionEvidence:
    """Harness-observed facts for one isolated Claude/DeepSeek turn."""

    reviewer_command: tuple[str, ...]
    resolved_model: str
    claude_cli_version: str
    claude_binary_sha256: str
    settings_sha256: str
    provider_endpoint: str
    session_id: str


@dataclass(frozen=True)
class ReceiptEvidenceContext:
    """Harness-owned immutable facts required to validate a generic receipt."""

    repo_root: Path
    base_sha: str
    head_sha: str
    mission_scope_path: str
    prompt_bytes: bytes
    raw_output_bytes: bytes
    final_result_bytes: bytes
    codex_execution: CodexExecutionEvidence | None = None
    claude_deepseek_execution: ClaudeDeepSeekExecutionEvidence | None = None
    chunked_claude_evidence: tuple[dict[str, Any], ...] = ()


SECRET_FIELD_TOKENS = (
    "api_key",
    "token",
    "cookie",
    "authorization",
    "email",
    "credential",
    "account_id",
    "refresh",
)


def _reject_secret_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if any(token in str(key).casefold() for token in SECRET_FIELD_TOKENS):
                raise IndependentReviewProtocolError(f"forbidden secret-bearing field: {key}")
            _reject_secret_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_secret_keys(nested)


def receipt_payload_sha256(receipt: dict[str, Any]) -> str:
    """Hash the receipt excluding its self-referential integrity object."""
    payload = dict(receipt)
    payload.pop("integrity", None)
    return sha256_bytes(canonical_json(payload))


def _schema_validator() -> Draft202012Validator:
    """Load the tracked generic receipt schema for runtime fail-closed validation."""
    try:
        schema = json.loads(RECEIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IndependentReviewProtocolError(f"cannot load receipt schema: {exc}") from exc
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_schema(receipt: object) -> None:
    errors = sorted(_schema_validator().iter_errors(receipt), key=lambda error: list(error.path))
    if errors:
        raise IndependentReviewProtocolError(f"generic receipt schema invalid: {errors[0].message}")


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise IndependentReviewProtocolError(f"{field} must be a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IndependentReviewProtocolError(f"{field} is invalid") from exc
    if parsed.tzinfo is None:
        raise IndependentReviewProtocolError(f"{field} must include timezone")
    return parsed


def _actual_diff_sha256(context: ReceiptEvidenceContext) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--binary",
                "--no-ext-diff",
                f"{context.base_sha}...{context.head_sha}",
            ],
            cwd=context.repo_root,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise IndependentReviewProtocolError(f"cannot calculate reviewed diff: {exc}") from exc
    if result.returncode != 0:
        raise IndependentReviewProtocolError("cannot calculate reviewed diff")
    return sha256_bytes(result.stdout)


def _scope_bytes_at_reviewed_head(context: ReceiptEvidenceContext, scope_path: str) -> bytes:
    """Read one validated scope blob from the reviewed immutable Git object."""
    try:
        commit = subprocess.run(
            ["git", "cat-file", "-e", f"{context.head_sha}^{{commit}}"],
            cwd=context.repo_root,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise IndependentReviewProtocolError(
            f"cannot read reviewed mission scope blob: {exc}"
        ) from exc
    if commit.returncode != 0:
        raise IndependentReviewProtocolError("reviewed head is not an available commit")
    try:
        tree_entry = subprocess.run(
            ["git", "ls-tree", "-z", context.head_sha, "--", scope_path],
            cwd=context.repo_root,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise IndependentReviewProtocolError(
            f"cannot inspect reviewed mission scope blob: {exc}"
        ) from exc
    entry = tree_entry.stdout.split(b"\0", 1)[0]
    if tree_entry.returncode != 0 or not entry.startswith((b"100644 blob ", b"100755 blob ")):
        raise IndependentReviewProtocolError(
            "reviewed head does not contain a regular mission scope blob"
        )
    try:
        result = subprocess.run(
            ["git", "show", f"{context.head_sha}:{scope_path}"],
            cwd=context.repo_root,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise IndependentReviewProtocolError(
            f"cannot read reviewed mission scope blob: {exc}"
        ) from exc
    if result.returncode != 0:
        raise IndependentReviewProtocolError("reviewed head does not contain mission scope blob")
    return result.stdout


def _validate_external_bindings(  # noqa: C901
    receipt: dict[str, Any], context: ReceiptEvidenceContext
) -> None:
    """Bind receipt declarations to harness-owned bytes and exact Git facts."""
    base = validate_sha(context.base_sha, name="evidence base_sha", length=40)
    head = validate_sha(context.head_sha, name="evidence head_sha", length=40)
    if receipt["base_sha"].lower() != base or receipt["head_sha"].lower() != head:
        raise IndependentReviewProtocolError("receipt base/head do not match trusted evidence")
    try:
        scope_path = validate_mission_scope_reference_path(context.mission_scope_path)
    except MissionScopeReferenceError as exc:
        raise IndependentReviewProtocolError("trusted mission scope path is invalid") from exc
    if receipt["mission_scope_path"] != scope_path:
        raise IndependentReviewProtocolError("receipt scope path does not match trusted evidence")
    scope_bytes = _scope_bytes_at_reviewed_head(context, scope_path)
    try:
        scope_contract, scope_digest = load_mission_scope_blob(context.repo_root, head, scope_path)
    except (MissionScopeError, OSError) as exc:
        raise IndependentReviewProtocolError("reviewed mission scope contract is invalid") from exc
    if scope_contract.mission_id != receipt["mission_id"]:
        raise IndependentReviewProtocolError("receipt mission_id does not match reviewed scope")
    if (
        scope_digest != sha256_bytes(scope_bytes)
        or scope_digest != receipt["mission_scope_sha256"].lower()
    ):
        raise IndependentReviewProtocolError(
            "receipt mission scope hash does not match trusted bytes"
        )
    if _actual_diff_sha256(context) != receipt["diff_sha256"].lower():
        raise IndependentReviewProtocolError("receipt diff hash does not match reviewed diff")
    for field, evidence in (
        ("review_prompt_sha256", context.prompt_bytes),
        ("raw_output_sha256", context.raw_output_bytes),
        ("final_result_sha256", context.final_result_bytes),
    ):
        if sha256_bytes(evidence) != receipt[field].lower():
            raise IndependentReviewProtocolError(f"receipt {field} does not match trusted evidence")
    try:
        final_result = json.loads(context.final_result_bytes)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise IndependentReviewProtocolError("trusted final result is not JSON") from exc
    expected_final = {
        "protocol_version": PROTOCOL_VERSION,
        "review_result": receipt["review_result"],
        "findings": receipt["findings"],
    }
    if (
        context.final_result_bytes != canonical_json(expected_final)
        or final_result != expected_final
    ):
        raise IndependentReviewProtocolError("trusted final result is not canonical receipt result")


def validate_backend_registry(registry: object) -> dict[str, dict[str, Any]]:
    """Validate and index the repository-controlled approved-backend registry."""
    if (
        not isinstance(registry, dict)
        or registry.get("registry_version") != "independent-review-backends/v1"
    ):
        raise IndependentReviewProtocolError("invalid backend registry version")
    entries = registry.get("backends")
    if not isinstance(entries, list) or not entries:
        raise IndependentReviewProtocolError("backend registry must contain backends")
    indexed: dict[str, dict[str, Any]] = {}
    required = {
        "backend_id",
        "harness_id",
        "provider_id",
        "status",
        "allowed_requested_models",
        "minimum_harness_version",
        "required_provenance_fields",
        "isolation_requirements",
        "transport_policy",
        "task_eligibility",
        "no_silent_fallback",
    }
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != required:
            raise IndependentReviewProtocolError("backend registry entry fields are invalid")
        backend = entry["backend_id"]
        if (
            not isinstance(backend, str)
            or backend in indexed
            or entry["status"] not in {"active", "reserved", "disabled"}
        ):
            raise IndependentReviewProtocolError("backend registry entry is invalid")
        if (
            not isinstance(entry["allowed_requested_models"], list)
            or not entry["allowed_requested_models"]
            or not all(
                isinstance(model, str) and model for model in entry["allowed_requested_models"]
            )
            or len(set(entry["allowed_requested_models"])) != len(entry["allowed_requested_models"])
        ):
            raise IndependentReviewProtocolError("backend allowed models are required")
        if (
            entry["no_silent_fallback"] is not True
            or not isinstance(entry["required_provenance_fields"], list)
            or not entry["required_provenance_fields"]
            or not all(
                isinstance(field, str) and field for field in entry["required_provenance_fields"]
            )
            or len(set(entry["required_provenance_fields"]))
            != len(entry["required_provenance_fields"])
        ):
            raise IndependentReviewProtocolError("backend provenance/fallback policy is invalid")
        eligibility = entry["task_eligibility"]
        if (
            not isinstance(eligibility, list)
            or not eligibility
            or not all(isinstance(value, str) for value in eligibility)
            or len(set(eligibility)) != len(eligibility)
            or not all(value in {"NORMAL", "STRICT", "CRITICAL"} for value in eligibility)
        ):
            raise IndependentReviewProtocolError("backend task eligibility is invalid")
        indexed[backend] = entry
    return indexed


def load_backend_registry(path: Path) -> dict[str, dict[str, Any]]:
    """Read a non-secret backend registry and validate its protocol shape."""
    try:
        return validate_backend_registry(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise IndependentReviewProtocolError(f"cannot load backend registry: {exc}") from exc


def _validate_codex_provenance(  # noqa: C901, PLR0912, PLR0915
    receipt: dict[str, Any], backend: dict[str, Any], context: ReceiptEvidenceContext
) -> None:
    """Bind Codex receipt claims to harness-observed execution facts.

    ``no_silent_fallback`` is meaningful only when the resolved model is an
    externally supplied fact. Comparing receipt fields with one another would
    merely make a self-consistent forgery.
    """
    if backend["backend_id"] != "codex-cli":
        return
    execution = context.codex_execution
    if execution is None:
        raise IndependentReviewProtocolError("trusted Codex execution evidence is required")
    if (
        not isinstance(execution.reviewer_command, tuple)
        or not execution.reviewer_command
        or not all(isinstance(part, str) and part for part in execution.reviewer_command)
        or not isinstance(execution.resolved_model, str)
        or not execution.resolved_model
        or not isinstance(execution.codex_cli_version, str)
        or not execution.codex_cli_version.strip()
        or not isinstance(execution.thread_id, str)
        or not _CODEX_THREAD_ID_RE.fullmatch(execution.thread_id)
    ):
        raise IndependentReviewProtocolError("trusted Codex execution evidence is malformed")
    trusted_binary_sha = validate_sha(
        execution.codex_binary_sha256, name="trusted codex binary sha", length=64
    )
    provenance = receipt["provenance"]
    if receipt["resolved_model"] != execution.resolved_model:
        raise IndependentReviewProtocolError(
            "receipt resolved model does not match trusted evidence"
        )
    if receipt["resolved_model"] != receipt["requested_model"]:
        raise IndependentReviewProtocolError("receipt resolved model is an unapproved fallback")
    command = provenance.get("reviewer_command")
    if not isinstance(command, list) or not all(isinstance(part, str) and part for part in command):
        raise IndependentReviewProtocolError("receipt reviewer command is invalid")
    if tuple(command) != execution.reviewer_command:
        raise IndependentReviewProtocolError(
            "receipt reviewer command does not match trusted evidence"
        )
    if (
        len(command) < _CODEX_EXEC_MINIMUM_ARGV_LENGTH
        or command[1] != "exec"
        or command.count("-m") != 1
        or command.count("-c") != 1
        or command.count("--sandbox") != 1
        or command.count("--json") != 1
        or command.count("--output-schema") != 1
        or command.count("--output-last-message") != 1
        or "--ignore-user-config" not in command
        or "--ephemeral" not in command
        or "--sandbox" not in command
        or command[command.index("--sandbox") + 1 : command.index("--sandbox") + 2] != ["read-only"]
    ):
        raise IndependentReviewProtocolError(
            "receipt reviewer command is not canonical isolated Codex"
        )
    if provenance.get("command_sha256") != sha256_bytes(canonical_json(command)):
        raise IndependentReviewProtocolError("receipt command hash does not match reviewer command")
    if provenance.get("codex_binary_sha256", "").lower() != trusted_binary_sha:
        raise IndependentReviewProtocolError("receipt binary hash does not match trusted evidence")
    if provenance.get("codex_cli_version") != execution.codex_cli_version:
        raise IndependentReviewProtocolError("receipt CLI version does not match trusted evidence")
    try:
        command_model, command_effort = reviewer_selectors_from_command(command)
    except ReviewReceiptError as exc:
        raise IndependentReviewProtocolError(
            "receipt reviewer command lacks pinned selectors"
        ) from exc
    if command_model != receipt["requested_model"] or command_model != receipt["resolved_model"]:
        raise IndependentReviewProtocolError(
            "receipt reviewer command model does not match receipt"
        )
    if command_effort != REVIEW_REASONING_EFFORT_PINNED:
        raise IndependentReviewProtocolError(
            "receipt reviewer command reasoning effort is not approved"
        )
    for flag in ("--output-schema", "--output-last-message"):
        flag_index = command.index(flag)
        if not command[flag_index + 1 : flag_index + 2] or not command[flag_index + 1]:
            raise IndependentReviewProtocolError(
                "receipt reviewer command output evidence is incomplete"
            )
    try:
        final_text = context.final_result_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IndependentReviewProtocolError("trusted final result is not UTF-8") from exc
    if not final_text.endswith("\n"):
        raise IndependentReviewProtocolError("trusted final result is not canonical JSON bytes")
    try:
        events = parse_json_lines(context.raw_output_bytes)
        if any("item" in event and not isinstance(event["item"], dict) for event in events):
            raise IndependentReviewProtocolError("raw output item event is malformed")
        if sum(event.get("type") == "thread.started" for event in events) != 1:
            raise IndependentReviewProtocolError(
                "raw output must contain exactly one thread.started"
            )
        if (
            sum(
                event.get("type") == "item.completed"
                and event.get("item", {}).get("type") == "agent_message"
                for event in events
            )
            != 1
        ):
            raise IndependentReviewProtocolError(
                "raw output must contain exactly one completed agent message"
            )
        if reviewer_invocation_id(events, _CODEX_THREAD_ID_RE) != execution.thread_id:
            raise IndependentReviewProtocolError(
                "raw output thread does not match trusted execution"
            )
        assert_successful_completion(events, final_text[:-1])
    except ReviewReceiptError as exc:
        raise IndependentReviewProtocolError("raw output completion evidence is invalid") from exc


def _validate_claude_deepseek_provenance(  # noqa: C901
    receipt: dict[str, Any], backend: dict[str, Any], context: ReceiptEvidenceContext
) -> None:
    if backend["backend_id"] != "claude-code-deepseek":
        return
    if receipt["provenance"].get("chunked_review") is True:
        _validate_chunked_claude_evidence(receipt, context)
        return
    execution = context.claude_deepseek_execution
    if execution is None:
        raise IndependentReviewProtocolError(
            "trusted Claude/DeepSeek execution evidence is required"
        )
    endpoint = _CLAUDE_DEEPSEEK_ENDPOINT
    values = (
        execution.reviewer_command,
        execution.resolved_model,
        execution.claude_cli_version,
        execution.settings_sha256,
        execution.provider_endpoint,
        execution.session_id,
    )
    if (
        not execution.reviewer_command
        or not all(isinstance(value, str) and value for value in values[1:])
        or execution.provider_endpoint != endpoint
    ):
        raise IndependentReviewProtocolError(
            "trusted Claude/DeepSeek execution evidence is malformed"
        )
    version = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", execution.claude_cli_version)
    if not version or tuple(map(int, version.groups())) < _CLAUDE_MINIMUM_VERSION:
        raise IndependentReviewProtocolError(
            "trusted Claude CLI version is below the approved baseline"
        )
    provenance = receipt["provenance"]
    expected = {
        "reviewer_command": list(execution.reviewer_command),
        "claude_cli_version": execution.claude_cli_version,
        "claude_binary_sha256": execution.claude_binary_sha256,
        "settings_sha256": execution.settings_sha256,
        "provider_endpoint": endpoint,
        "session_id": execution.session_id,
    }
    if any(provenance.get(key) != value for key, value in expected.items()):
        raise IndependentReviewProtocolError(
            "receipt Claude/DeepSeek provenance does not match trusted evidence"
        )
    if provenance.get("command_sha256") != sha256_bytes(
        canonical_json(expected["reviewer_command"])
    ):
        raise IndependentReviewProtocolError("receipt Claude/DeepSeek command hash does not match")
    command = list(execution.reviewer_command)
    if (
        "--bare" not in command
        or "--print" not in command
        or command.count("--model") != 1
        or command[command.index("--model") + 1 : command.index("--model") + 2]
        != [_CLAUDE_DEEPSEEK_MODEL]
        or command.count("--settings") != 1
        or not command[command.index("--settings") + 1 : command.index("--settings") + 2]
        or "--strict-mcp-config" not in command
        or "--restricted" not in command
        or command.count("--tools") != 1
        or command[command.index("--tools") + 1 : command.index("--tools") + 2] != [""]
        or command.count("--disallowed-tools") != 1
        or not _CLAUDE_RESTRICTED_TOOLS.issubset(
            set(command[command.index("--disallowed-tools") + 1].split(","))
        )
        or command.count("--output-format") != 1
        or command[command.index("--output-format") + 1 : command.index("--output-format") + 2]
        != ["json"]
        or command.count("--json-schema") != 1
        or not command[command.index("--json-schema") + 1 : command.index("--json-schema") + 2]
        or any(part in {"--resume", "--continue"} for part in command)
    ):
        raise IndependentReviewProtocolError(
            "receipt Claude command is not canonical isolated DeepSeek"
        )
    if (
        receipt["requested_model"] != _CLAUDE_DEEPSEEK_MODEL
        or receipt["resolved_model"] != receipt["requested_model"]
        or execution.resolved_model != receipt["requested_model"]
    ):
        raise IndependentReviewProtocolError(
            "receipt Claude/DeepSeek model is an unapproved fallback"
        )
    for digest in (execution.claude_binary_sha256, execution.settings_sha256):
        validate_sha(digest, name="trusted Claude provenance digest", length=64)
    try:
        event = json.loads(context.raw_output_bytes)
    except (ValueError, json.JSONDecodeError) as exc:
        raise IndependentReviewProtocolError("raw Claude output is not one JSON result") from exc
    if (
        event.get("is_error") is not False
        or event.get("session_id") != execution.session_id
        or event.get("structured_output") != json.loads(context.final_result_bytes)
    ):
        raise IndependentReviewProtocolError("raw Claude completion evidence is invalid")


from scripts.devops.deepseek_chunk_receipt_validation import (
    _validate_chunked_claude_evidence as _validate_chunked_evidence,
)


def _validate_chunked_claude_evidence(
    receipt: dict[str, Any], context: ReceiptEvidenceContext
) -> None:
    _validate_chunked_evidence(receipt, context)


def validate_receipt(  # noqa: C901, PLR0912
    receipt: object,
    *,
    registry: dict[str, dict[str, Any]],
    evidence_context: ReceiptEvidenceContext,
) -> dict[str, Any]:
    """Validate a newly-issued generic receipt; legacy receipts use an adapter."""

    if not isinstance(receipt, dict):
        raise IndependentReviewProtocolError("receipt must be an object")
    _validate_schema(receipt)
    _reject_secret_keys(receipt)
    required = {
        "protocol_version",
        "receipt_version",
        "review_run_id",
        "review_backend",
        "review_harness",
        "provider",
        "requested_model",
        "base_sha",
        "head_sha",
        "diff_sha256",
        "mission_id",
        "mission_scope_path",
        "mission_scope_sha256",
        "review_prompt_sha256",
        "review_started_at",
        "review_completed_at",
        "review_result",
        "finding_counts_by_severity",
        "findings",
        "raw_output_sha256",
        "final_result_sha256",
        "isolation",
        "provenance",
        "integrity",
    }
    if set(receipt) - (required | {"resolved_model"}) or not (
        required | {"resolved_model"}
    ).issubset(receipt):
        raise IndependentReviewProtocolError("receipt fields are invalid")
    if (
        receipt["protocol_version"] != PROTOCOL_VERSION
        or receipt["receipt_version"] != RECEIPT_VERSION
    ):
        raise IndependentReviewProtocolError("receipt protocol/version mismatch")
    if not _MISSION_ID_RE.fullmatch(receipt["mission_id"]):
        raise IndependentReviewProtocolError("receipt mission_id is invalid")
    started = _parse_timestamp(receipt["review_started_at"], "review_started_at")
    completed = _parse_timestamp(receipt["review_completed_at"], "review_completed_at")
    if completed < started:
        raise IndependentReviewProtocolError("receipt completed timestamp precedes start")
    backend = registry.get(receipt["review_backend"])
    if backend is None or backend["status"] != "active":
        raise IndependentReviewProtocolError("receipt backend is not active")
    if (
        receipt["provider"] != backend["provider_id"]
        or receipt["review_harness"] != backend["harness_id"]
    ):
        raise IndependentReviewProtocolError("receipt backend provenance mismatch")
    if receipt["requested_model"] not in backend["allowed_requested_models"]:
        raise IndependentReviewProtocolError("receipt requested model is not approved")
    for field, length in (
        ("base_sha", 40),
        ("head_sha", 40),
        ("diff_sha256", 64),
        ("mission_scope_sha256", 64),
        ("review_prompt_sha256", 64),
        ("raw_output_sha256", 64),
        ("final_result_sha256", 64),
    ):
        validate_sha(receipt.get(field), name=field, length=length)
    result = validate_result(
        {
            "protocol_version": PROTOCOL_VERSION,
            "review_result": receipt["review_result"],
            "findings": receipt["findings"],
        }
    )
    if receipt["finding_counts_by_severity"] != result["finding_counts_by_severity"]:
        raise IndependentReviewProtocolError("receipt finding counts do not match findings")
    isolation = receipt["isolation"]
    if not isinstance(isolation, dict) or any(
        isolation.get(field) is not True
        for field in (
            "fresh_process",
            "fresh_context",
            "detached_worktree",
            "read_only",
            "worktree_clean_before",
            "worktree_clean_after",
        )
    ):
        raise IndependentReviewProtocolError("receipt isolation facts are incomplete")
    if isolation.get("worktree_head_sha", "").lower() != receipt["head_sha"].lower():
        raise IndependentReviewProtocolError("receipt worktree head does not match reviewed head")
    if not isinstance(receipt["provenance"], dict) or not set(
        backend["required_provenance_fields"]
    ).issubset(receipt["provenance"]):
        raise IndependentReviewProtocolError("receipt required backend provenance is missing")
    _validate_codex_provenance(receipt, backend, evidence_context)
    _validate_claude_deepseek_provenance(receipt, backend, evidence_context)
    _validate_external_bindings(receipt, evidence_context)
    integrity = receipt["integrity"]
    if not isinstance(integrity, dict) or integrity.get(
        "receipt_payload_sha256"
    ) != receipt_payload_sha256(receipt):
        raise IndependentReviewProtocolError("receipt payload hash mismatch")
    return result
