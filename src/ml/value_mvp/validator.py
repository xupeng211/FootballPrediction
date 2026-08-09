"""Independent validation of a VALUE_MVP-1 run (tamper rejection).

Recomputes hashes, population invariants, fold assignments, prediction
invariants and all reported metrics from the prediction CSVs alone, then
compares byte-for-byte (rounded) against the recorded receipts. Any mismatch
raises ValueError with the offending field named.
"""

from __future__ import annotations

import csv as csv_module
import hashlib
import json
from typing import TYPE_CHECKING

import numpy as np

from src.ml.value_mvp import evaluation
from src.ml.value_mvp.bootstrap import (
    classify_claim,
    percentile_ci,
    season_stratified_bootstrap_deltas,
)
from src.ml.value_mvp.market import closing_consensus
from src.ml.value_mvp.pipeline import (
    _RECEIPT_SCHEMA,
    _environment_fingerprint,
    build_input_manifest,
    verify_inputs,
)
from src.ml.value_mvp.protocol import protocol_sha256
from src.ml.value_mvp.sources import (
    Match,
    build_dataset,
    evaluation_population_hash,
    load_csv_rows,
    load_observations,
)

if TYPE_CHECKING:
    from pathlib import Path

_LABEL_INDEX = {"H": 0, "D": 1, "A": 2}
_TOLERANCE = 1e-9
_MAX_ROW_SUM_DEVIATION = 1e-6
_MIN_CLOSING_BOOKMAKERS = 2
_CI_KEYS = (
    "delta_log_loss_ci95_low",
    "delta_log_loss_ci95_high",
    "delta_brier_ci95_low",
    "delta_brier_ci95_high",
)
_ALLOWED_META_KEYS = {
    "delta_log_loss",
    "delta_brier",
    "fold",
    "final_classification",
    "power_statement",
    "test_seasons",
    "train_seasons",
}


def load_predictions(path: Path) -> list[dict]:
    """Read a predictions CSV back as list of dicts (strings preserved)."""
    with path.open("r", encoding="utf-8") as handle:
        return list(csv_module.DictReader(handle))


def check_input_manifest(
    input_dir: Path, protocol: dict, matches: list[Match], git_revision: str, recorded: dict
) -> None:
    """Recompute the input manifest and compare with the recorded one."""
    recomputed = build_input_manifest(input_dir, protocol, matches, git_revision)
    if recomputed != recorded:
        raise ValueError("input manifest mismatch (inputs tampered or different inputs used)")


def check_population_hash(matches: list[Match], recorded: dict) -> None:
    """Recompute the evaluation population hash and compare."""
    actual = evaluation_population_hash(matches)
    if actual != recorded.get("evaluation_population_hash"):
        raise ValueError(
            f"evaluation population hash mismatch: {actual} != {recorded.get('evaluation_population_hash')}"
        )


def check_protocol_frozen(protocol: dict, output_dir: Path) -> None:
    """Compare the loaded protocol against the frozen copy + sha file."""
    sha_file = output_dir / "protocol-sha256.txt"
    copy_file = output_dir / "protocol-copy.json"
    if not sha_file.exists() or not copy_file.exists():
        raise ValueError(
            "frozen protocol records missing (protocol-copy.json / protocol-sha256.txt)"
        )
    frozen_sha = sha_file.read_text(encoding="utf-8").strip()
    actual_sha = protocol_sha256(protocol)
    if actual_sha != frozen_sha:
        raise ValueError(f"protocol sha mismatch: {actual_sha} != frozen {frozen_sha}")
    with copy_file.open("r", encoding="utf-8") as handle:
        copied = json.load(handle)
    if protocol_sha256(copied) != actual_sha:
        raise ValueError("protocol-copy.json does not match the frozen protocol sha")


def check_predictions_invariants(predictions: list[dict], fold_name: str) -> None:
    """Structural invariants on a predictions CSV (no metrics yet)."""
    mids = [row["match_identity"] for row in predictions]
    if len(mids) != len(set(mids)):
        raise ValueError(f"{fold_name}: duplicate match_identity rows")
    for row in predictions:
        probs = [row[f"model_p_{sel}"] for sel in ("home", "draw", "away")]
        for key in probs:
            if not _is_bounded_probability(key):
                raise ValueError(f"{fold_name}: invalid model probability {key}")
        total = sum(float(key) for key in probs)
        if not abs(total - 1.0) <= _MAX_ROW_SUM_DEVIATION:
            raise ValueError(f"{fold_name}: model probabilities do not sum to 1 ({total})")
        market = [row[f"market_p_{sel}"] for sel in ("home", "draw", "away")]
        for key in market:
            if not _is_bounded_probability(key):
                raise ValueError(f"{fold_name}: invalid market probability {key}")
        if row["actual_result"] not in _LABEL_INDEX:
            raise ValueError(f"{fold_name}: invalid actual_result {row['actual_result']}")
        if int(row["valid_closing_bookmaker_count"]) < _MIN_CLOSING_BOOKMAKERS:
            raise ValueError(f"{fold_name}: closing benchmark count below minimum")


def _is_bounded_probability(value: str) -> bool:
    """Finite AND within [0, 1] (mirrors evaluation.validate_probability_matrix)."""
    try:
        parsed = float(value)
    except ValueError:
        return False
    return np.isfinite(parsed) and 0.0 <= parsed <= 1.0


def check_fold_assignments(
    predictions: list[dict], expected_seasons: set[str], fold_name: str
) -> None:
    """All rows in a fold must belong to the fold's test seasons."""
    actual = {row["season"] for row in predictions}
    if actual != expected_seasons:
        raise ValueError(f"{fold_name}: season assignment mismatch {actual} != {expected_seasons}")


def recompute_market_probabilities(
    matches: list[Match], predictions: list[dict], fold_name: str, protocol: dict
) -> list[list[float]]:
    """Recompute closing consensus per prediction row from raw observations."""
    by_mid = {match.mid: match for match in matches}
    market_rows: list[list[float]] = []
    for row in predictions:
        match = by_mid.get(row["match_identity"])
        if match is None:
            raise ValueError(
                f"{fold_name}: prediction row references unknown match {row['match_identity']}"
            )
        consensus = closing_consensus(match, protocol)
        if consensus is None:
            raise ValueError(f"{fold_name}: closing consensus missing for {row['match_identity']}")
        recorded = [float(row[f"market_p_{sel}"]) for sel in ("home", "draw", "away")]
        recomputed = [float(value) for value in consensus["p"]]
        if not all(abs(a - b) <= _TOLERANCE for a, b in zip(recorded, recomputed, strict=True)):
            raise ValueError(
                f"{fold_name}: market probability mismatch for {row['match_identity']}"
            )
        market_rows.append(recomputed)
    return market_rows


def recompute_metrics(
    predictions: list[dict],
    market_rows: list[list[float]],
    recorded: dict,
    protocol: dict,
    expected_ci: dict | None = None,
) -> dict:
    """Recompute fold/pooled metrics from predictions and compare with recorded.

    Strict by design (F-01): every recomputed key must be present in the
    recorded metrics and equal; CI keys are cross-checked against the bootstrap
    record (expected_ci) instead of being skipped; unknown recorded keys are
    rejected outright.
    """
    eps = float(protocol.get("log_loss_eps", 1e-15))
    labels = np.array([_LABEL_INDEX[row["actual_result"]] for row in predictions])
    model_probs = np.array(
        [[float(row[f"model_p_{sel}"]) for sel in ("home", "draw", "away")] for row in predictions]
    )
    market_probs = np.array(market_rows)
    class_frequency = evaluation.class_frequency_probabilities(labels)
    class_probs = np.tile(class_frequency, (len(labels), 1))
    recomputed = {
        "model_log_loss": evaluation.log_loss_score(model_probs, labels, eps),
        "market_log_loss": evaluation.log_loss_score(market_probs, labels, eps),
        "class_frequency_log_loss": evaluation.log_loss_score(class_probs, labels, eps),
        "model_brier": evaluation.brier_score(model_probs, labels),
        "market_brier": evaluation.brier_score(market_probs, labels),
        "model_accuracy": evaluation.accuracy(model_probs, labels),
        "market_accuracy": evaluation.accuracy(market_probs, labels),
        "oos_count": len(labels),
    }
    _check_computed_keys(recomputed, recorded)
    _check_ci_keys(recorded, expected_ci)
    _check_unknown_keys(recomputed, recorded)
    return recomputed


def _check_computed_keys(recomputed: dict, recorded: dict) -> None:
    """Every recomputed key must be present in the recorded metrics and equal."""
    for key, value in recomputed.items():
        if key not in recorded:
            raise ValueError(f"metric {key} missing from recorded metrics")
        if abs(value - float(recorded[key])) > _TOLERANCE:
            raise ValueError(
                f"metric mismatch {key}: recomputed {value} != recorded {recorded[key]}"
            )


def _check_ci_keys(recorded: dict, expected_ci: dict | None) -> None:
    """CI keys are cross-checked against the bootstrap record (never skipped)."""
    if expected_ci is None:
        for key in _CI_KEYS:
            if key in recorded:
                raise ValueError(f"unexpected CI key {key} in fold metrics")
        return
    for key in _CI_KEYS:
        if key not in expected_ci:
            continue
        if key not in recorded:
            raise ValueError(f"CI key {key} missing from recorded metrics")
        if abs(float(recorded[key]) - float(expected_ci[key])) > _TOLERANCE:
            raise ValueError(
                f"metric mismatch {key}: recorded {recorded[key]} != bootstrap {expected_ci[key]}"
            )


def _check_unknown_keys(recomputed: dict, recorded: dict) -> None:
    """Recorded keys outside the known set are rejected outright."""
    allowed = set(recomputed) | set(_CI_KEYS) | _ALLOWED_META_KEYS
    for key in recorded:
        if key not in allowed:
            raise ValueError(f"unexpected recorded metric key {key}")


def check_bootstrap(
    predictions: list[dict],
    market_rows: list[list[float]],
    protocol: dict,
    recorded_bootstrap: dict,
    recorded_pooled: dict,
) -> None:
    """Recompute the season-stratified bootstrap CIs from prediction rows.

    F-01: the Brier CI is recomputed too (previously only recorded), and the
    pooled-metrics CI fields must equal the bootstrap record (cross-source,
    not self-referential).
    """
    eps = float(protocol.get("log_loss_eps", 1e-15))
    labels = np.array([_LABEL_INDEX[row["actual_result"]] for row in predictions])
    model_probs = np.array(
        [[float(row[f"model_p_{sel}"]) for sel in ("home", "draw", "away")] for row in predictions]
    )
    market_probs = np.array(market_rows)
    per_row_deltas = evaluation.per_row_log_loss(
        model_probs, labels, eps
    ) - evaluation.per_row_log_loss(market_probs, labels, eps)
    per_row_brier_deltas = evaluation.per_row_brier(model_probs, labels) - evaluation.per_row_brier(
        market_probs, labels
    )
    deltas_by_season: dict[str, np.ndarray] = {}
    brier_by_season: dict[str, np.ndarray] = {}
    for i, row in enumerate(predictions):
        deltas_by_season.setdefault(row["season"], []).append(per_row_deltas[i])
        brier_by_season.setdefault(row["season"], []).append(per_row_brier_deltas[i])
    deltas_by_season = {season: np.array(values) for season, values in deltas_by_season.items()}
    brier_by_season = {season: np.array(values) for season, values in brier_by_season.items()}
    replicates = int(protocol["bootstrap"]["replicates"])
    seed = int(protocol["bootstrap"]["seed"])
    percentiles = protocol["bootstrap"]["ci_percentiles"]
    ll_replicates = season_stratified_bootstrap_deltas(deltas_by_season, replicates, seed)
    low, high = percentile_ci(ll_replicates, percentiles)
    if abs(low - float(recorded_bootstrap["delta_log_loss_ci95_low"])) > _TOLERANCE:
        raise ValueError(
            f"bootstrap CI low mismatch: {low} != {recorded_bootstrap['delta_log_loss_ci95_low']}"
        )
    if abs(high - float(recorded_bootstrap["delta_log_loss_ci95_high"])) > _TOLERANCE:
        raise ValueError(
            f"bootstrap CI high mismatch: {high} != {recorded_bootstrap['delta_log_loss_ci95_high']}"
        )
    brier_replicates = season_stratified_bootstrap_deltas(brier_by_season, replicates, seed)
    brier_low, brier_high = percentile_ci(brier_replicates, percentiles)
    if abs(brier_low - float(recorded_bootstrap["delta_brier_ci95_low"])) > _TOLERANCE:
        raise ValueError(
            f"bootstrap brier CI low mismatch: {brier_low} != "
            f"{recorded_bootstrap['delta_brier_ci95_low']}"
        )
    if abs(brier_high - float(recorded_bootstrap["delta_brier_ci95_high"])) > _TOLERANCE:
        raise ValueError(
            f"bootstrap brier CI high mismatch: {brier_high} != "
            f"{recorded_bootstrap['delta_brier_ci95_high']}"
        )
    for key in _CI_KEYS:
        if abs(float(recorded_pooled[key]) - float(recorded_bootstrap[key])) > _TOLERANCE:
            raise ValueError(f"pooled-metrics {key} does not match bootstrap.json {key}")
    classification = classify_claim(low, high)
    recorded_classification = recorded_pooled.get("final_classification")
    if classification != recorded_classification:
        raise ValueError(
            f"final classification mismatch: {classification} != {recorded_classification}"
        )


def check_calibration(
    predictions: list[dict],
    market_rows: list[list[float]],
    protocol: dict,
    recorded_calibration: dict,
) -> None:
    """Recompute the fixed-bin calibration summary from the prediction rows.

    F-01: calibration was previously bound only by file digest and the
    self-referential receipt block; now it must equal the recomputation.
    """
    labels = np.array([_LABEL_INDEX[row["actual_result"]] for row in predictions])
    model_probs = np.array(
        [[float(row[f"model_p_{sel}"]) for sel in ("home", "draw", "away")] for row in predictions]
    )
    market_probs = np.array(market_rows)
    bins = protocol["calibration_bins"]
    recomputed = {
        "model": evaluation.calibration_summary(model_probs, labels, bins),
        "market": evaluation.calibration_summary(market_probs, labels, bins),
    }
    if recomputed != recorded_calibration:
        raise ValueError("calibration summary mismatch (recomputed from predictions)")


def validate_run(input_dir: Path, output_dir: Path, protocol: dict, git_revision: str) -> dict:
    """Full independent validation; raises ValueError on any tamper/divergence."""
    matches, _ = _load_inputs(input_dir, protocol)
    check_protocol_frozen(protocol, output_dir)

    recorded_manifest = _read_json(output_dir / "input-manifest.json")
    check_input_manifest(input_dir, protocol, matches, git_revision, recorded_manifest)

    recorded_population = _read_json(output_dir / "evaluation-dataset-manifest.json")
    check_population_hash(matches, recorded_population)

    fold1 = load_predictions(output_dir / "fold1-predictions.csv")
    fold2 = load_predictions(output_dir / "fold2-predictions.csv")
    check_predictions_invariants(fold1, "fold1")
    check_predictions_invariants(fold2, "fold2")
    expected_fold1 = set(protocol["season_split_policy"]["fold1"]["test"])
    expected_fold2 = set(protocol["season_split_policy"]["fold2"]["test"])
    check_fold_assignments(fold1, expected_fold1, "fold1")
    check_fold_assignments(fold2, expected_fold2, "fold2")

    market1 = recompute_market_probabilities(matches, fold1, "fold1", protocol)
    market2 = recompute_market_probabilities(matches, fold2, "fold2", protocol)

    recorded_fold1 = _read_json(output_dir / "fold1-metrics.json")
    recorded_fold2 = _read_json(output_dir / "fold2-metrics.json")
    recompute_metrics(fold1, market1, recorded_fold1, protocol)
    recompute_metrics(fold2, market2, recorded_fold2, protocol)

    combined = fold1 + fold2
    pooled_market = market1 + market2
    recorded_pooled = _read_json(output_dir / "pooled-metrics.json")
    recorded_bootstrap = _read_json(output_dir / "bootstrap.json")
    recompute_metrics(
        combined, pooled_market, recorded_pooled, protocol, expected_ci=recorded_bootstrap
    )

    check_bootstrap(combined, pooled_market, protocol, recorded_bootstrap, recorded_pooled)
    check_calibration(
        combined,
        pooled_market,
        protocol,
        _read_json(output_dir / "calibration.json"),
    )

    recorded_receipt = _read_json(output_dir / "run-receipt.json")
    check_receipt_contents(
        output_dir,
        recorded_manifest,
        recorded_population,
        recorded_fold1,
        recorded_fold2,
        recorded_pooled,
        recorded_receipt,
    )

    return {
        "status": "OK",
        "verified": [
            "input_manifest",
            "population_hash",
            "protocol_frozen",
            "fold_assignments",
            "prediction_invariants",
            "market_probabilities",
            "fold_metrics",
            "pooled_metrics",
            "bootstrap_ci",
            "bootstrap_brier_ci",
            "calibration_recomputed",
            "final_classification",
            "run_receipt",
            "run_receipt_contents",
            "output_digests",
            "environment_fingerprint",
            "model_convergence",
        ],
    }


def _check_environment_and_convergence(recorded_receipt: dict) -> None:
    """F-02: the receipt must carry the pinned schema, the runtime environment
    fingerprint and a self-consistent per-fold optimizer convergence record."""
    if recorded_receipt.get("schema") != _RECEIPT_SCHEMA:
        raise ValueError(
            f"run-receipt schema mismatch: {recorded_receipt.get('schema')} != {_RECEIPT_SCHEMA}"
        )
    if recorded_receipt.get("environment") != _environment_fingerprint():
        raise ValueError("run-receipt environment fingerprint mismatch")
    convergence = recorded_receipt.get("model_convergence") or {}
    for fold_name in ("fold1", "fold2"):
        entry = convergence.get(fold_name)
        if not isinstance(entry, dict):
            raise TypeError(f"run-receipt model_convergence missing {fold_name}")
        iterations, max_iter = entry.get("iterations"), entry.get("max_iter")
        if not isinstance(iterations, int) or not isinstance(max_iter, int):
            raise TypeError(f"run-receipt model_convergence {fold_name} malformed")
        if entry.get("converged") != (iterations < max_iter):
            raise ValueError(f"run-receipt model_convergence {fold_name} inconsistent")


def check_receipt_contents(
    output_dir: Path,
    recorded_manifest: dict,
    recorded_population: dict,
    recorded_fold1: dict,
    recorded_fold2: dict,
    recorded_pooled: dict,
    recorded_receipt: dict,
) -> None:
    """Cross-check the run receipt against every file it summarizes."""
    _check_environment_and_convergence(recorded_receipt)

    recomputed_receipt_sha = hashlib.sha256(
        json.dumps(recorded_manifest, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if recomputed_receipt_sha != recorded_receipt.get("input_manifest_sha256"):
        raise ValueError(
            f"run-receipt input_manifest_sha256 mismatch: {recomputed_receipt_sha} != "
            f"{recorded_receipt.get('input_manifest_sha256')}"
        )

    frozen_sha = (output_dir / "protocol-sha256.txt").read_text(encoding="utf-8").strip()
    if recorded_receipt.get("protocol_sha256") != frozen_sha:
        raise ValueError(
            f"run-receipt protocol_sha256 mismatch: {recorded_receipt.get('protocol_sha256')} "
            f"!= frozen {frozen_sha}"
        )
    if recorded_receipt.get("evaluation_population_hash") != recorded_population.get(
        "evaluation_population_hash"
    ):
        raise ValueError("run-receipt evaluation_population_hash mismatch")

    checks = {
        "fold1": (recorded_receipt.get("fold1"), recorded_fold1),
        "fold2": (recorded_receipt.get("fold2"), recorded_fold2),
        "pooled": (recorded_receipt.get("pooled"), recorded_pooled),
        "bootstrap": (
            recorded_receipt.get("bootstrap"),
            _read_json(output_dir / "bootstrap.json"),
        ),
        "calibration": (
            recorded_receipt.get("calibration"),
            _read_json(output_dir / "calibration.json"),
        ),
    }
    for key, (receipt_value, file_value) in checks.items():
        if receipt_value != file_value:
            raise ValueError(f"run-receipt {key} block does not match its file")

    recorded_digests = recorded_receipt.get("output_digests") or {}
    for name, expected in recorded_digests.items():
        path = output_dir / name
        if not path.exists():
            raise ValueError(f"run-receipt digest target missing: {name}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"run-receipt output digest mismatch for {name}")


def _load_inputs(input_dir: Path, protocol: dict) -> tuple[list[Match], dict]:
    """Load and build inputs like the pipeline does (fail on drift)."""
    csv_rows = load_csv_rows(input_dir / "csv")
    observations = load_observations(input_dir / "observations")
    matches = build_dataset(observations, csv_rows, protocol)
    return matches, verify_inputs(input_dir)


def _read_json(path: Path) -> dict:
    """Read a JSON record; fail loudly when missing."""
    if not path.exists():
        raise ValueError(f"missing recorded output: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_single_file_probe(probe_path: Path) -> None:
    """Sanity-check the Phase 0 market probe file structure."""
    probe = _read_json(probe_path)
    for season, stats in probe["per_season"].items():
        if stats["closing_coverage"] == 0:
            raise ValueError(f"phase0 probe: no closing coverage for {season}")
