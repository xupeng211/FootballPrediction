"""Validator tamper-rejection tests: any divergence must raise ValueError."""

from __future__ import annotations

import json

import pytest

from src.ml.value_mvp.pipeline import freeze_protocol, run_oos
from src.ml.value_mvp.sources import build_dataset, load_csv_rows, load_observations
from src.ml.value_mvp.validator import (
    check_predictions_invariants,
    check_protocol_frozen,
    load_predictions,
    validate_run,
)
from tests.unit.ml.value_mvp._helpers import synthetic_protocol


@pytest.fixture
def completed_run(staged_inputs, tmp_path):
    """A full synthetic run with frozen protocol, ready to validate."""
    protocol = synthetic_protocol()
    matches = build_dataset(
        load_observations(staged_inputs / "observations"),
        load_csv_rows(staged_inputs / "csv"),
        protocol,
    )
    freeze_dir = tmp_path / "freeze"
    freeze_protocol(protocol, freeze_dir)
    output_dir = tmp_path / "runs"
    run_oos(matches, protocol, output_dir, "test-sha", staged_inputs, freeze_dir)
    return {"input_dir": staged_inputs, "output_dir": output_dir, "protocol": protocol}


def test_validate_run_ok_on_untampered_run(completed_run):
    result = validate_run(
        completed_run["input_dir"],
        completed_run["output_dir"],
        completed_run["protocol"],
        "test-sha",
    )
    assert result["status"] == "OK"
    assert "bootstrap_ci" in result["verified"]


def test_validate_rejects_tampered_market_probability(completed_run):
    path = completed_run["output_dir"] / "fold1-predictions.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    header, first = lines[0], lines[1]
    fields = first.split(",")
    home_index = header.split(",").index("market_p_home")
    fields[home_index] = "0.999"
    lines[1] = ",".join(fields)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="market probability mismatch"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )


def test_validate_rejects_tampered_metric(completed_run):
    path = completed_run["output_dir"] / "pooled-metrics.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["model_log_loss"] = data["model_log_loss"] + 0.05
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    with pytest.raises(ValueError, match="metric mismatch"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )


def test_validate_rejects_tampered_duplicate_row(completed_run):
    """Duplicating a prediction row changes the fold population -> reject."""
    path = completed_run["output_dir"] / "fold2-predictions.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join([*lines, lines[1]]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate match_identity"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )


def test_validate_rejects_protocol_drift(completed_run):
    drifted = dict(completed_run["protocol"])
    drifted["minimum_bookmaker_count"] = 3
    with pytest.raises(ValueError, match="protocol sha mismatch"):
        validate_run(completed_run["input_dir"], completed_run["output_dir"], drifted, "test-sha")


def test_check_predictions_invariants_detects_nonfinite(completed_run):
    rows = load_predictions(completed_run["output_dir"] / "fold1-predictions.csv")
    rows[0]["model_p_away"] = "nan"
    with pytest.raises(ValueError, match="non-finite"):
        check_predictions_invariants(rows, "fold1")


def test_check_protocol_frozen_requires_records(tmp_path):
    protocol = synthetic_protocol()
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(ValueError, match="frozen protocol records missing"):
        check_protocol_frozen(protocol, empty_dir)
