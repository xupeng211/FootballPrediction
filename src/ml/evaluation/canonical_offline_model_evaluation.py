"""Canonical one-time offline evaluation facade.

The implementation is split into three boundaries: immutable input contracts,
metrics, and external evidence.  The public sequence remains
``prepare -> freeze -> infer -> open outcomes -> write evidence``.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import InitVar, dataclass
from pathlib import Path
import subprocess
from typing import Any

import numpy as np

from . import canonical_offline_model_evaluation_contract as _contract
from .canonical_offline_model_evaluation_artifacts import (
    JOURNAL_FILENAME,
    _append_evaluation_journal_event_with_capability,
    _consume_journal_capability,
    append_evaluation_journal_event,
    build_evaluation_artifact,
    build_evaluation_receipt,
    write_evaluation_outputs,
)
from .canonical_offline_model_evaluation_contract import (
    ARTIFACT_SCHEMA_VERSION,
    BOOTSTRAP_CONFIDENCE_LEVEL,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    CALIBRATION_BIN_EDGES,
    CALIBRATION_MIN_NONEMPTY_BIN_COUNT,
    CLASS_COUNT,
    CLASS_NAMES,
    CLASS_ORDER,
    EVALUATION_ID,
    EVALUATION_TASK,
    EXPECTED_CANDIDATE_ARTIFACT_SHA256,
    EXPECTED_CANDIDATE_ID,
    EXPECTED_CANDIDATE_METADATA_SHA256,
    EXPECTED_CANDIDATE_SOURCE_REVISION,
    EXPECTED_FRAME_ARTIFACT_SHA256,
    EXPECTED_FRAME_BUSINESS_SHA256,
    EXPECTED_FRAME_CODE_REVISION,
    EXPECTED_FRAME_RECEIPT_SHA256,
    EXPECTED_RESERVED_ROW_ID_SHA256,
    EXPECTED_TRAINING_ROW_ID_SHA256,
    FEATURE_COUNT,
    FEATURE_ORDER,
    FRAME_ELIGIBLE_ROWS,
    FRAME_INELIGIBLE_ROWS,
    PROBABILITY_COLUMN_ORDER,
    PROBABILITY_MATRIX_DIMENSIONS,
    PROBABILITY_SUM_ATOL,
    PROTOCOL_SCHEMA_VERSION,
    RECEIPT_SCHEMA_VERSION,
    RESERVED_ROWS,
    RESERVED_STATUS_AFTER,
    RESERVED_STATUS_BEFORE,
    TRAINING_CLASS_COUNTS,
    TRAINING_CLASS_DISTRIBUTION,
    TRAINING_ROWS,
    EvaluationContractError,
    EvaluationPopulation,
    EvaluationRow,
    VerifiedCandidate,
    _assert_git_sha,
    _assert_sha256,
    _load_population,
    _OpaqueOutcome,
    _parse_json,
    _parse_opened_at,
    _repository_root,
    load_protocol,
    load_verified_candidate,
    protocol_sha256,
    validate_candidate_metadata_binding,
    validate_population_binding,
    validate_protocol,
)
from .canonical_offline_model_evaluation_metrics import (
    _bootstrap_intervals,
    _calibration_summary,
    _quality_status,
    build_baselines,
    metric_bundle,
    validate_probability_matrix,
)

_PREPARED_EVALUATION_FACTORY_TOKEN = object()


def current_git_head(repository_root: Path | None = None) -> str:
    """Return the full source HEAD used to execute the evaluation."""
    root = repository_root or _repository_root()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise EvaluationContractError("evaluation source HEAD is unavailable") from exc
    if result.returncode != 0:
        raise EvaluationContractError("evaluation source HEAD is unavailable")
    return _assert_git_sha(result.stdout.strip(), "evaluation source HEAD")


def assert_clean_worktree(repository_root: Path | None = None) -> None:
    """Require a source tree with no tracked or untracked changes."""
    root = repository_root or _repository_root()
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise EvaluationContractError("evaluation worktree status is unavailable") from exc
    if result.returncode != 0:
        raise EvaluationContractError("evaluation worktree status is unavailable")
    if result.stdout.strip():
        raise EvaluationContractError("evaluation source worktree is dirty")


def _git_check(repository_root: Path, args: list[str], label: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repository_root,
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise EvaluationContractError(f"{label} is unavailable") from exc
    if result.returncode != 0:
        raise EvaluationContractError(f"{label} is invalid")
    return result.stdout


def _assert_protocol_git_binding(
    protocol_path: str | Path,
    protocol_digest: str,
    *,
    source_head: str,
    protocol_freeze_sha: str,
) -> None:
    """Bind protocol to a real ancestor commit and the current source HEAD."""
    canonical_path = (
        _repository_root() / "config" / "canonical_offline_model_evaluation_protocol.json"
    ).resolve()
    if Path(protocol_path).resolve() != canonical_path:
        raise EvaluationContractError("protocol path is not the canonical checked-in path")
    _assert_sha256(protocol_digest, "protocol hash")
    _assert_git_sha(source_head, "evaluation source HEAD")
    _assert_git_sha(protocol_freeze_sha, "protocol freeze SHA")
    actual_head = current_git_head()
    if actual_head != source_head:
        raise EvaluationContractError("evaluation source HEAD is not the current worktree HEAD")
    root = _repository_root()
    _git_check(
        root,
        ["cat-file", "-e", f"{protocol_freeze_sha}^{{commit}}"],
        "protocol freeze commit",
    )
    _git_check(
        root,
        ["cat-file", "-e", f"{source_head}^{{commit}}"],
        "evaluation source commit",
    )
    try:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", protocol_freeze_sha, source_head],
            cwd=root,
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise EvaluationContractError("protocol ancestry check is unavailable") from exc
    if ancestor.returncode != 0:
        raise EvaluationContractError("protocol freeze SHA is not an ancestor of source HEAD")

    protocol_relative_path = "config/canonical_offline_model_evaluation_protocol.json"
    for revision, label in (
        (protocol_freeze_sha, "protocol freeze commit protocol"),
        (source_head, "source HEAD protocol"),
    ):
        frozen_bytes = _git_check(
            root,
            ["show", f"{revision}:{protocol_relative_path}"],
            label,
        )
        frozen_protocol = _parse_json(frozen_bytes, label)
        if protocol_sha256(frozen_protocol) != protocol_digest:
            raise EvaluationContractError(f"{label} does not match the loaded protocol")


class OutcomeAccessGate:
    """One-way gate for the first semantic read of reserved outcomes."""

    def __init__(
        self,
        population: EvaluationPopulation,
        *,
        expected_reserved_row_id_hash: str | None = None,
    ):
        self._population = population
        self._expected_reserved_row_id_hash = expected_reserved_row_id_hash
        self._journal_token = object()
        self._journal_path: Path | None = None
        self.protocol_frozen = False
        self.outcomes_opened = False
        self.outcome_access_started = False
        self.protocol_sha256: str | None = None
        self.protocol_freeze_sha: str | None = None

    def freeze(self, protocol_sha256_value: str, protocol_freeze_sha: str) -> None:
        """Record the frozen protocol identity before allowing outcome access."""
        if self.outcome_access_started:
            raise EvaluationContractError("protocol cannot be frozen after outcome access")
        _assert_sha256(protocol_sha256_value, "protocol hash")
        _assert_git_sha(protocol_freeze_sha, "protocol freeze SHA")
        if self.protocol_frozen:
            if (
                self.protocol_sha256 == protocol_sha256_value
                and self.protocol_freeze_sha == protocol_freeze_sha
            ):
                raise EvaluationContractError("protocol was already frozen")
            raise EvaluationContractError("protocol freeze identity cannot change")
        self.protocol_sha256 = protocol_sha256_value
        self.protocol_freeze_sha = protocol_freeze_sha
        self.protocol_frozen = True

    def _authorize_journal(self, capability: object) -> object:
        """Create private authorization from a one-use post-fsync capability."""
        journal_path = _consume_journal_capability(
            capability,
            evaluation_id=EVALUATION_ID,
            protocol_sha256=self.protocol_sha256,
            protocol_freeze_sha=self.protocol_freeze_sha,
            reserved_row_count=len(self._population.reserved_ids),
            reserved_row_id_hash=self._expected_reserved_row_id_hash,
        )
        self._journal_path = journal_path
        return self._journal_token

    def open_reserved_outcomes(
        self,
        opened_at: str,
        *,
        journal_path: Path | None = None,
        authorization: object | None = None,
    ) -> np.ndarray[Any, Any]:
        """Open exactly the reserved labels once, after the freeze marker exists."""
        if not self.protocol_frozen:
            raise EvaluationContractError("reserved outcomes are forbidden before protocol freeze")
        if self.outcomes_opened or self.outcome_access_started:
            raise EvaluationContractError(
                "reserved outcomes may only be opened once per evaluation"
            )
        if (
            authorization is not self._journal_token
            or journal_path is None
            or journal_path != self._journal_path
            or not journal_path.is_file()
            or journal_path.is_symlink()
        ):
            raise EvaluationContractError(
                "reserved outcomes require a durable evaluation journal authorization"
            )
        _parse_opened_at(opened_at)
        self.outcome_access_started = True
        labels: list[int] = []
        for row_id in self._population.reserved_ids:
            label = self._population.labels_by_id.get(row_id)
            if label is None:
                raise EvaluationContractError("reserved row label binding is missing")
            labels.append(label.open(_contract._OUTCOME_ACCESS_TOKEN))
        self.outcomes_opened = True
        return np.asarray(labels, dtype=int)


@dataclass
class PreparedEvaluation:
    """Prepared candidate and population state awaiting the one-way gate."""

    protocol: dict[str, Any]
    protocol_sha256: str
    candidate: VerifiedCandidate
    population: EvaluationPopulation
    gate: OutcomeAccessGate
    protocol_path: Path
    _factory_token: InitVar[object]
    source_head: str | None = None
    protocol_freeze_sha: str | None = None
    probabilities: np.ndarray[Any, Any] | None = None
    opened_at: str | None = None
    opened_labels: np.ndarray[Any, Any] | None = None

    def __post_init__(self, factory_token: object) -> None:
        if factory_token is not _PREPARED_EVALUATION_FACTORY_TOKEN:
            raise EvaluationContractError(
                "PreparedEvaluation must be created by the canonical preparation factory"
            )

    def _validate_frozen_inputs(self) -> None:
        """Recheck every immutable input binding immediately before inference."""
        validate_protocol(self.protocol)
        if protocol_sha256(self.protocol) != self.protocol_sha256:
            raise EvaluationContractError("prepared protocol hash binding mismatch")
        validate_candidate_metadata_binding(
            self.candidate.metadata,
            artifact_sha256=self.candidate.artifact_sha256,
            metadata_sha256=self.candidate.metadata_sha256,
            protocol=self.protocol,
        )
        if (
            self.candidate.feature_names != FEATURE_ORDER
            or self.candidate.class_order != CLASS_ORDER
        ):
            raise EvaluationContractError("prepared candidate contract binding mismatch")
        validate_population_binding(self.population, self.protocol)
        if self.gate._population is not self.population:
            raise EvaluationContractError("prepared outcome gate population binding mismatch")
        if (
            self.gate._expected_reserved_row_id_hash
            != self.protocol["population"]["reserved_evaluation_row_id_hash"]
        ):
            raise EvaluationContractError("prepared outcome gate row binding mismatch")

    def freeze_protocol(self, *, source_head: str, protocol_freeze_sha: str) -> None:
        """Bind the evaluation source HEAD and protocol freeze SHA."""
        _assert_git_sha(source_head, "evaluation source HEAD")
        _assert_git_sha(protocol_freeze_sha, "protocol freeze SHA")
        if not isinstance(self.protocol_path, Path):
            raise EvaluationContractError("canonical protocol path binding is required")
        self._validate_frozen_inputs()
        _assert_protocol_git_binding(
            self.protocol_path,
            self.protocol_sha256,
            source_head=source_head,
            protocol_freeze_sha=protocol_freeze_sha,
        )
        self.source_head = source_head
        self.protocol_freeze_sha = protocol_freeze_sha
        self.gate.freeze(self.protocol_sha256, protocol_freeze_sha)

    def infer_reserved(self) -> np.ndarray[Any, Any]:
        """Run candidate inference without reading any outcome value."""
        if not self.gate.protocol_frozen:
            raise EvaluationContractError("protocol must be frozen before inference")
        matrix = np.asarray(
            [
                self.population.rows_by_id[row_id].features
                for row_id in self.population.reserved_ids
            ],
            dtype=float,
        )
        try:
            transformed = self.candidate.scaler.transform(matrix)
            probabilities = np.asarray(self.candidate.model.predict_proba(transformed), dtype=float)
        except Exception as exc:
            raise EvaluationContractError("candidate probability inference failed") from exc
        validate_probability_matrix(probabilities, expected_rows=len(self.population.reserved_ids))
        self.probabilities = probabilities
        return probabilities.copy()

    def open_outcomes(
        self,
        opened_at: str,
        *,
        journal_output_dir: str | Path | None = None,
    ) -> np.ndarray[Any, Any]:
        """Durably record opening intent, then open outcomes through the gate."""
        if self.probabilities is None:
            raise EvaluationContractError("candidate inference must complete before outcome access")
        if self.source_head is None or self.protocol_freeze_sha is None:
            raise EvaluationContractError("evaluation Git binding is incomplete")
        if journal_output_dir is None:
            raise EvaluationContractError(
                "reserved outcomes require an external durable attempt journal directory"
            )
        _parse_opened_at(opened_at)
        journal_path, journal_capability = _append_evaluation_journal_event_with_capability(
            journal_output_dir,
            event_type="OUTCOME_OPENING_STARTED",
            event_at=opened_at,
            fields={
                "evaluation_protocol_version": self.protocol["schema_version"],
                "evaluation_protocol_sha256": self.protocol_sha256,
                "protocol_freeze_sha": self.protocol_freeze_sha,
                "evaluation_source_head": self.source_head,
                "candidate_id": self.candidate.identity()["candidate_id"],
                "candidate_artifact_sha256": self.candidate.artifact_sha256,
                "candidate_metadata_sha256": self.candidate.metadata_sha256,
                "frame_artifact_sha256": self.population.frame_binding.artifact_sha256,
                "frame_receipt_sha256": self.population.frame_binding.receipt_sha256,
                "reserved_row_count": len(self.population.reserved_ids),
                "reserved_row_id_hash": self.protocol["population"][
                    "reserved_evaluation_row_id_hash"
                ],
                "holdout_status_before": RESERVED_STATUS_BEFORE,
            },
        )
        authorization = self.gate._authorize_journal(journal_capability)
        self.opened_at = opened_at
        labels = self.gate.open_reserved_outcomes(
            opened_at,
            journal_path=journal_path,
            authorization=authorization,
        )
        self.opened_labels = labels.copy()
        append_evaluation_journal_event(
            journal_output_dir,
            event_type="OUTCOMES_OPENED",
            event_at=opened_at,
            fields={
                "evaluation_protocol_sha256": self.protocol_sha256,
                "protocol_freeze_sha": self.protocol_freeze_sha,
                "evaluation_source_head": self.source_head,
                "reserved_row_count": len(labels),
                "holdout_status_after": RESERVED_STATUS_AFTER,
            },
        )
        return labels.copy()


def prepare_evaluation(
    *,
    candidate_path: str | Path,
    metadata_path: str | Path,
    frame_path: str | Path,
    receipt_path: str | Path,
    protocol_path: str | Path,
) -> PreparedEvaluation:
    """Prepare all identity evidence without opening a reserved outcome."""
    protocol, protocol_hash, checked_in_protocol_path = load_protocol(protocol_path)
    candidate = load_verified_candidate(candidate_path, metadata_path, protocol)
    population = _load_population(frame_path, receipt_path, protocol)
    validate_population_binding(population, protocol)
    return _make_prepared_evaluation(
        protocol=protocol,
        protocol_sha256=protocol_hash,
        candidate=candidate,
        population=population,
        gate=OutcomeAccessGate(
            population,
            expected_reserved_row_id_hash=protocol["population"]["reserved_evaluation_row_id_hash"],
        ),
        protocol_path=checked_in_protocol_path,
    )


def _make_prepared_evaluation(
    *,
    protocol: dict[str, Any],
    protocol_sha256: str,
    candidate: VerifiedCandidate,
    population: EvaluationPopulation,
    gate: OutcomeAccessGate,
    protocol_path: Path,
) -> PreparedEvaluation:
    """Construct only through the private canonical preparation factory."""
    return PreparedEvaluation(
        protocol=protocol,
        protocol_sha256=protocol_sha256,
        candidate=candidate,
        population=population,
        gate=gate,
        protocol_path=protocol_path,
        _factory_token=_PREPARED_EVALUATION_FACTORY_TOKEN,
    )


def run_evaluation(
    *,
    candidate_path: str | Path,
    metadata_path: str | Path,
    frame_path: str | Path,
    receipt_path: str | Path,
    protocol_path: str | Path,
    source_head: str,
    protocol_freeze_sha: str,
    outcome_opened_at: str,
    journal_output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Execute the exact one-way evaluation sequence and return its artifact."""
    if journal_output_dir is None:
        raise EvaluationContractError(
            "real evaluation requires an external durable attempt journal directory"
        )
    prepared: PreparedEvaluation | None = None
    artifact_built = False
    try:
        prepared = prepare_evaluation(
            candidate_path=candidate_path,
            metadata_path=metadata_path,
            frame_path=frame_path,
            receipt_path=receipt_path,
            protocol_path=protocol_path,
        )
        prepared.freeze_protocol(source_head=source_head, protocol_freeze_sha=protocol_freeze_sha)
        prepared.infer_reserved()
        labels = prepared.open_outcomes(
            outcome_opened_at,
            journal_output_dir=journal_output_dir,
        )
        artifact = build_evaluation_artifact(prepared, labels)
        if journal_output_dir is not None:
            append_evaluation_journal_event(
                journal_output_dir,
                event_type="EVALUATION_ARTIFACT_BUILT",
                event_at=outcome_opened_at,
                fields={
                    "evaluation_protocol_sha256": prepared.protocol_sha256,
                    "protocol_freeze_sha": prepared.protocol_freeze_sha,
                    "evaluation_source_head": prepared.source_head,
                    "holdout_status_after": RESERVED_STATUS_AFTER,
                },
            )
        artifact_built = True
    except Exception as exc:
        if (
            journal_output_dir is not None
            and prepared is not None
            and prepared.gate.outcome_access_started
            and not artifact_built
        ):
            with suppress(EvaluationContractError):
                append_evaluation_journal_event(
                    journal_output_dir,
                    event_type="EVALUATION_ATTEMPT_INVALIDATED",
                    event_at=outcome_opened_at,
                    fields={
                        "evaluation_protocol_sha256": prepared.protocol_sha256,
                        "protocol_freeze_sha": prepared.protocol_freeze_sha,
                        "evaluation_source_head": prepared.source_head,
                        "error_type": type(exc).__name__,
                        "holdout_status_after": RESERVED_STATUS_AFTER,
                    },
                )
        raise
    return artifact


__all__ = [
    "ARTIFACT_SCHEMA_VERSION",
    "BOOTSTRAP_CONFIDENCE_LEVEL",
    "BOOTSTRAP_RESAMPLES",
    "BOOTSTRAP_SEED",
    "CALIBRATION_BIN_EDGES",
    "CALIBRATION_MIN_NONEMPTY_BIN_COUNT",
    "CLASS_COUNT",
    "CLASS_NAMES",
    "CLASS_ORDER",
    "EVALUATION_ID",
    "EVALUATION_TASK",
    "EXPECTED_CANDIDATE_ARTIFACT_SHA256",
    "EXPECTED_CANDIDATE_ID",
    "EXPECTED_CANDIDATE_METADATA_SHA256",
    "EXPECTED_CANDIDATE_SOURCE_REVISION",
    "EXPECTED_FRAME_ARTIFACT_SHA256",
    "EXPECTED_FRAME_BUSINESS_SHA256",
    "EXPECTED_FRAME_CODE_REVISION",
    "EXPECTED_FRAME_RECEIPT_SHA256",
    "EXPECTED_RESERVED_ROW_ID_SHA256",
    "EXPECTED_TRAINING_ROW_ID_SHA256",
    "FEATURE_COUNT",
    "FEATURE_ORDER",
    "FRAME_ELIGIBLE_ROWS",
    "FRAME_INELIGIBLE_ROWS",
    "JOURNAL_FILENAME",
    "PROBABILITY_COLUMN_ORDER",
    "PROBABILITY_MATRIX_DIMENSIONS",
    "PROBABILITY_SUM_ATOL",
    "PROTOCOL_SCHEMA_VERSION",
    "RECEIPT_SCHEMA_VERSION",
    "RESERVED_ROWS",
    "RESERVED_STATUS_AFTER",
    "RESERVED_STATUS_BEFORE",
    "TRAINING_CLASS_COUNTS",
    "TRAINING_CLASS_DISTRIBUTION",
    "TRAINING_ROWS",
    "EvaluationContractError",
    "EvaluationPopulation",
    "EvaluationRow",
    "OutcomeAccessGate",
    "PreparedEvaluation",
    "VerifiedCandidate",
    "_OpaqueOutcome",
    "_bootstrap_intervals",
    "_calibration_summary",
    "_quality_status",
    "append_evaluation_journal_event",
    "assert_clean_worktree",
    "build_baselines",
    "build_evaluation_artifact",
    "build_evaluation_receipt",
    "current_git_head",
    "load_protocol",
    "load_verified_candidate",
    "metric_bundle",
    "prepare_evaluation",
    "protocol_sha256",
    "run_evaluation",
    "validate_candidate_metadata_binding",
    "validate_population_binding",
    "validate_probability_matrix",
    "validate_protocol",
    "write_evaluation_outputs",
]
