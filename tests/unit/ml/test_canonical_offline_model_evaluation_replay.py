"""Tests for truthful consumed-holdout reproducibility replay evidence."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from src.ml.evaluation import canonical_offline_model_evaluation as evaluation
from src.ml.evaluation import canonical_offline_model_evaluation_artifacts as artifacts
from tests.unit.ml import test_canonical_offline_model_evaluation as base

if TYPE_CHECKING:
    from pathlib import Path


def test_consumed_holdout_replay_is_explicitly_marked(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol, protocol_hash, _ = evaluation.load_protocol(base.PROTOCOL_PATH)
    base._allow_synthetic_bindings(monkeypatch)
    population = base._population()
    prepared = evaluation._make_prepared_evaluation(
        protocol=protocol,
        protocol_sha256=protocol_hash,
        candidate=base._candidate(),
        population=population,
        gate=evaluation.OutcomeAccessGate(
            population,
            expected_reserved_row_id_hash=evaluation.EXPECTED_RESERVED_ROW_ID_SHA256,
        ),
        protocol_path=base.PROTOCOL_PATH,
        replay_of_consumed_holdout=True,
    )
    prepared.freeze_protocol(
        source_head=evaluation.current_git_head(),
        protocol_freeze_sha=base.PROTOCOL_FREEZE_SHA,
    )
    prepared.infer_reserved()
    labels = prepared.open_outcomes(
        "2026-08-23T00:00:00Z",
        output_destination=base._output_destination(tmp_path, "replay"),
    )
    artifact = evaluation.build_evaluation_artifact(prepared, labels)

    assert artifact["evaluation_attempt"] == ("REPRODUCIBILITY_REPLAY_OF_CONSUMED_HOLDOUT")
    assert artifact["holdout"]["status_before"] == "CONSUMED_FOR_OFFLINE_EVALUATION"
    assert "UNTOUCHED" not in json.dumps(artifact, sort_keys=True)


def test_claimed_destination_rejects_journal_appearing_before_first_event(
    tmp_path: Path,
) -> None:
    destination = evaluation.prepare_evaluation_output_destination(tmp_path / "journal-race")
    destination.journal_path.write_text("sentinel\n", encoding="utf-8")

    with pytest.raises(evaluation.EvaluationContractError, match="journal"):
        evaluation.append_evaluation_journal_event(
            destination,
            event_type="OUTCOME_OPENING_STARTED",
            event_at="2026-08-23T00:00:00Z",
            fields={},
        )


def test_atomic_output_claim_does_not_replace_racing_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "artifact.json"
    real_link = artifacts.os.link

    def race_link(source: Path, target: Path) -> None:
        target.write_text("raced-target", encoding="utf-8")
        real_link(source, target)

    monkeypatch.setattr(artifacts.os, "link", race_link)
    with pytest.raises(evaluation.EvaluationContractError, match="already exists"):
        artifacts._write_new_bytes(output_path, b"replacement")
    assert output_path.read_text(encoding="utf-8") == "raced-target"


def test_post_open_journal_failure_records_invalidation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol, protocol_hash, _ = evaluation.load_protocol(base.PROTOCOL_PATH)
    base._allow_synthetic_bindings(monkeypatch)
    population = base._population()
    prepared = evaluation._make_prepared_evaluation(
        protocol=protocol,
        protocol_sha256=protocol_hash,
        candidate=base._candidate(),
        population=population,
        gate=evaluation.OutcomeAccessGate(
            population,
            expected_reserved_row_id_hash=evaluation.EXPECTED_RESERVED_ROW_ID_SHA256,
        ),
        protocol_path=base.PROTOCOL_PATH,
    )
    monkeypatch.setattr(evaluation, "prepare_evaluation", lambda **_kwargs: prepared)
    real_append = evaluation.append_evaluation_journal_event
    failed_once = False

    def fail_outcomes_opened_once(
        destination: evaluation.PreparedOutputDestination,
        *,
        event_type: str,
        event_at: str,
        fields: dict[str, object],
        allow_existing_outputs: bool = False,
    ) -> Path:
        nonlocal failed_once
        if event_type == "OUTCOMES_OPENED" and not failed_once:
            failed_once = True
            raise evaluation.EvaluationContractError("simulated post-open journal I/O")
        return real_append(
            destination,
            event_type=event_type,
            event_at=event_at,
            fields=fields,
            allow_existing_outputs=allow_existing_outputs,
        )

    monkeypatch.setattr(evaluation, "append_evaluation_journal_event", fail_outcomes_opened_once)
    journal_dir = tmp_path / "post-open-failure"
    with pytest.raises(evaluation.EvaluationContractError, match="simulated post-open"):
        evaluation.run_evaluation(
            candidate_path="/external/candidate.joblib",
            metadata_path="/external/candidate.metadata.json",
            frame_path="/external/frame.json",
            receipt_path="/external/frame.receipt.json",
            protocol_path=base.PROTOCOL_PATH,
            source_head=evaluation.current_git_head(),
            protocol_freeze_sha=base.PROTOCOL_FREEZE_SHA,
            outcome_opened_at="2026-08-23T00:00:00Z",
            journal_output_dir=journal_dir,
        )

    events = [
        json.loads(line)
        for line in (journal_dir / evaluation.JOURNAL_FILENAME).read_text().splitlines()
    ]
    assert [event["event_type"] for event in events] == [
        "OUTCOME_OPENING_STARTED",
        "EVALUATION_ATTEMPT_INVALIDATED",
    ]
    assert events[-1]["holdout_status_after"] == "CONSUMED_FOR_OFFLINE_EVALUATION"
