"""Tests for truthful consumed-holdout reproducibility replay evidence."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.ml.evaluation import canonical_offline_model_evaluation as evaluation
from tests.unit.ml import test_canonical_offline_model_evaluation as base

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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
