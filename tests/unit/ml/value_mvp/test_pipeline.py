"""Pipeline orchestration tests: gates, freeze, folds, pooled results."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.ml.value_mvp.features import build_feature_frame
from src.ml.value_mvp.pipeline import (
    freeze_protocol,
    phase0_probe,
    pooled_results,
    population_gates,
    run_fold,
    run_oos,
    verify_frozen_protocol,
    verify_inputs,
    write_predictions_csv,
)
from src.ml.value_mvp.sources import build_dataset, load_csv_rows, load_observations
from src.ml.value_mvp.validator import load_predictions, validate_run
from tests.unit.ml.value_mvp._helpers import synthetic_protocol

if TYPE_CHECKING:
    from pathlib import Path


def _matches(input_dir: Path, protocol: dict):
    return build_dataset(
        load_observations(input_dir / "observations"),
        load_csv_rows(input_dir / "csv"),
        protocol,
    )


def test_verify_inputs_rejects_wrong_hash(tmp_path):
    (tmp_path / "csv").mkdir(parents=True)
    (tmp_path / "observations").mkdir()
    for name in ("raw_odds_2223.csv", "raw_odds_2324.csv", "real_odds_raw.csv"):
        (tmp_path / "csv" / name).write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_inputs(tmp_path)


def test_population_gates_pass_with_synthetic_data(staged_inputs):
    protocol = synthetic_protocol()
    matches = _matches(staged_inputs, protocol)
    gates = population_gates(matches)
    assert gates["CANONICAL_SOURCE_RECOVERY"] == "PASS"
    assert gates["fold1_oos"] == 1
    assert gates["fold2_oos"] == 1
    assert gates["pooled_oos"] == 2


def test_phase0_probe_reports_coverage_and_metrics(staged_inputs):
    protocol = synthetic_protocol()
    matches = _matches(staged_inputs, protocol)
    probe = phase0_probe(matches, protocol)
    assert probe["eligible_matches"] == 8
    assert probe["closing_coverage"] == 8
    assert probe["first_collection_coverage"] == 8
    assert probe["bookmaker_count_distribution"]["2"] == 8
    assert probe["per_season"]["2022/23"]["closing_coverage"] == 6
    assert probe["closing"]["log_loss"] is not None


def test_freeze_and_verify_protocol_flow(tmp_path):
    protocol = synthetic_protocol()
    freeze_dir = tmp_path / "freeze"
    freeze_protocol(protocol, freeze_dir)
    sha_file = freeze_dir / "protocol-sha256.txt"
    assert sha_file.read_text(encoding="utf-8").strip()
    verify_frozen_protocol(protocol, freeze_dir)
    drifted = dict(protocol)
    drifted["minimum_bookmaker_count"] = 3
    with pytest.raises(ValueError, match="protocol drift"):
        verify_frozen_protocol(drifted, freeze_dir)
    with pytest.raises(ValueError, match="not frozen"):
        verify_frozen_protocol(protocol, tmp_path / "missing")


def test_run_oos_end_to_end_byte_deterministic(staged_inputs, tmp_path):
    protocol = synthetic_protocol()
    matches = _matches(staged_inputs, protocol)
    freeze_dir = tmp_path / "freeze"
    freeze_protocol(protocol, freeze_dir)

    output_a = tmp_path / "runs" / "A"
    output_b = tmp_path / "runs" / "B"
    receipt_a = run_oos(matches, protocol, output_a, "test-sha", staged_inputs, freeze_dir)
    run_oos(matches, protocol, output_b, "test-sha", staged_inputs, freeze_dir)

    for name in (
        "fold1-predictions.csv",
        "fold2-predictions.csv",
        "fold1-metrics.json",
        "fold2-metrics.json",
        "pooled-metrics.json",
        "bootstrap.json",
        "calibration.json",
        "input-manifest.json",
        "run-receipt.json",
        "summary.md",
    ):
        assert (output_a / name).read_bytes() == (output_b / name).read_bytes(), name
    assert receipt_a["pooled"]["final_classification"] in {
        "MODEL_BETTER_THAN_CLOSING",
        "MARKET_BETTER_THAN_MODEL",
        "INCONCLUSIVE",
    }
    assert receipt_a["evaluation_population_hash"]


def test_run_fold_refuses_missing_closing_benchmark(staged_inputs, tmp_path):
    """A test-season match without a closing benchmark must abort the fold."""
    protocol = synthetic_protocol()
    observations = load_observations(staged_inputs / "observations")
    csv_rows = load_csv_rows(staged_inputs / "csv")
    first_only = [obs for obs in observations if obs["provider_collection_phase"] != "closing"]
    matches_first_only = build_dataset(first_only, csv_rows, protocol)
    ordered = sorted(matches_first_only, key=lambda m: (m.kickoff_at, m.mid))
    rows = build_feature_frame(ordered)
    with pytest.raises(ValueError, match="closing benchmark missing"):
        run_fold(
            "fold1",
            ["2022/23"],
            ["2023/24"],
            ordered,
            rows,
            protocol,
            tmp_path / "artifacts",
        )


def test_pooled_results_reports_bootstrap_and_classification(staged_inputs, tmp_path):
    protocol = synthetic_protocol()
    matches = _matches(staged_inputs, protocol)
    ordered = sorted(matches, key=lambda m: (m.kickoff_at, m.mid))
    rows = build_feature_frame(ordered)
    fold1 = run_fold("fold1", ["2022/23"], ["2023/24"], ordered, rows, protocol, tmp_path / "a")
    fold2 = run_fold(
        "fold2", ["2022/23", "2023/24"], ["2024/25"], ordered, rows, protocol, tmp_path / "b"
    )
    pooled = pooled_results(fold1, fold2, protocol)
    assert pooled["metrics"]["oos_count"] == 2
    assert pooled["bootstrap"]["replicates"] == 100
    assert (
        pooled["bootstrap"]["delta_log_loss_ci95_low"]
        <= pooled["bootstrap"]["delta_log_loss_ci95_high"]
    )
    assert pooled["metrics"]["final_classification"] in {
        "MODEL_BETTER_THAN_CLOSING",
        "MARKET_BETTER_THAN_MODEL",
        "INCONCLUSIVE",
    }


def test_write_predictions_csv_roundtrip(tmp_path):
    rows = [
        {
            "match_identity": "47_2022_101",
            "season": "2022/23",
            "kickoff": "2022-08-06T14:00:00+01:00",
            "home": "Alpha FC",
            "away": "Beta FC",
            "actual_result": "H",
            "model_p_home": 0.5,
            "model_p_draw": 0.3,
            "model_p_away": 0.2,
            "market_p_home": 0.55,
            "market_p_draw": 0.25,
            "market_p_away": 0.2,
            "valid_closing_bookmaker_count": 2,
            "fold_id": "fold1",
        }
    ]
    path = tmp_path / "predictions.csv"
    write_predictions_csv(path, rows)
    loaded = load_predictions(path)
    assert loaded[0]["match_identity"] == "47_2022_101"
    assert float(loaded[0]["model_p_home"]) == 0.5


def test_validate_run_accepts_full_synthetic_run(staged_inputs, tmp_path):
    protocol = synthetic_protocol()
    matches = _matches(staged_inputs, protocol)
    freeze_dir = tmp_path / "freeze"
    freeze_protocol(protocol, freeze_dir)
    output_dir = tmp_path / "runs"
    run_oos(matches, protocol, output_dir, "test-sha", staged_inputs, freeze_dir)
    result = validate_run(staged_inputs, output_dir, protocol, "test-sha")
    assert result["status"] == "OK"
