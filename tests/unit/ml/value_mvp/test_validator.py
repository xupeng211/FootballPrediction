"""Validator tamper-rejection tests: any divergence must raise ValueError."""

from __future__ import annotations

import hashlib
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
    with pytest.raises(ValueError, match="invalid model probability"):
        check_predictions_invariants(rows, "fold1")


def test_check_predictions_invariants_detects_out_of_bounds(completed_run):
    rows = load_predictions(completed_run["output_dir"] / "fold1-predictions.csv")
    rows[0]["model_p_home"] = "1.5"
    rows[0]["model_p_draw"] = "-0.3"
    with pytest.raises(ValueError, match="invalid model probability"):
        check_predictions_invariants(rows, "fold1")


def test_validate_rejects_tampered_receipt(completed_run):
    """The receipt summarizes the metric files; flipping a result must fail."""
    path = completed_run["output_dir"] / "run-receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["pooled"]["final_classification"] = (
        "MODEL_BETTER_THAN_CLOSING"
        if receipt["pooled"]["final_classification"] != "MODEL_BETTER_THAN_CLOSING"
        else "MARKET_BETTER_THAN_MODEL"
    )
    path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    with pytest.raises(ValueError, match="pooled block"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )


def test_validate_rejects_tampered_output_digest(completed_run):
    """summary.md is bound to the receipt only by its digest."""
    path = completed_run["output_dir"] / "summary.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="output digest mismatch"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )


def test_check_protocol_frozen_requires_records(tmp_path):
    protocol = synthetic_protocol()
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(ValueError, match="frozen protocol records missing"):
        check_protocol_frozen(protocol, empty_dir)


def _rewrite_json(path, data):
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


def test_validate_rejects_tampered_pooled_ci(completed_run):
    """F-01: pooled CI must match the bootstrap record (cross-source)."""
    path = completed_run["output_dir"] / "pooled-metrics.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["delta_log_loss_ci95_low"] = 0.01
    _rewrite_json(path, data)
    with pytest.raises(ValueError, match="delta_log_loss_ci95_low"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )


def test_validate_rejects_consistent_ci_tamper(completed_run):
    """F-01 regression: coordinated pooled+bootstrap CI tamper that used to
    pass is now caught by the brier CI recomputed from predictions."""
    for name in ("bootstrap.json", "pooled-metrics.json"):
        path = completed_run["output_dir"] / name
        data = json.loads(path.read_text(encoding="utf-8"))
        data["delta_brier_ci95_low"] = 0.01
        data["delta_brier_ci95_high"] = 0.02
        _rewrite_json(path, data)
    with pytest.raises(ValueError, match="bootstrap brier CI"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )


def test_validate_rejects_tampered_calibration(completed_run):
    """F-01: calibration must equal the recomputation from predictions, even
    when the receipt block and digest are tampered in concert."""
    path = completed_run["output_dir"] / "calibration.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["model"][0]["bins"][0]["count"] += 1
    _rewrite_json(path, data)
    receipt_path = completed_run["output_dir"] / "run-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["calibration"] = data
    receipt["output_digests"]["calibration.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _rewrite_json(receipt_path, receipt)
    with pytest.raises(ValueError, match="calibration summary mismatch"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )


def test_validate_rejects_unknown_metric_key(completed_run):
    """F-01: recorded keys outside the known set must be rejected outright."""
    path = completed_run["output_dir"] / "pooled-metrics.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["bogus_key"] = 1
    _rewrite_json(path, data)
    with pytest.raises(ValueError, match="unexpected recorded metric key"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )


def test_validate_rejects_tampered_environment(completed_run):
    """F-02: the receipt environment fingerprint must equal the runtime one."""
    path = completed_run["output_dir"] / "run-receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["environment"]["sklearn"] = "9.9.9"
    _rewrite_json(path, receipt)
    with pytest.raises(ValueError, match="environment fingerprint mismatch"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )


def test_validate_rejects_inconsistent_convergence(completed_run):
    """F-02: convergence flag inconsistent with iterations/max_iter is rejected."""
    path = completed_run["output_dir"] / "run-receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    entry = receipt["model_convergence"]["fold1"]
    entry["converged"] = not entry["converged"]
    _rewrite_json(path, receipt)
    with pytest.raises(ValueError, match="model_convergence"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )


def test_validate_rejects_wrong_receipt_schema(completed_run):
    path = completed_run["output_dir"] / "run-receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["schema"] = "value-mvp-1-run-receipt/v1"
    _rewrite_json(path, receipt)
    with pytest.raises(ValueError, match="run-receipt schema mismatch"):
        validate_run(
            completed_run["input_dir"],
            completed_run["output_dir"],
            completed_run["protocol"],
            "test-sha",
        )
