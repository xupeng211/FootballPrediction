"""VALUE_MVP-1 run orchestration: gates, Phase 0, protocol freeze, folds.

Zero DB, zero network. All business outputs are byte-deterministic JSON/CSV
(no wall-clock in any business hash or output).
"""

from __future__ import annotations

import csv as csv_module
import json
from typing import TYPE_CHECKING

import joblib
import numpy as np

from src.ml.value_mvp import evaluation, leakage
from src.ml.value_mvp.bootstrap import (
    classify_claim,
    percentile_ci,
    season_stratified_bootstrap_deltas,
)
from src.ml.value_mvp.features import build_feature_frame
from src.ml.value_mvp.market import closing_consensus, first_collection_consensus, mean_overround
from src.ml.value_mvp.protocol import FEATURE_NAMES, feature_contract_violations, protocol_sha256
from src.ml.value_mvp.receipt import (
    _RECEIPT_OUTPUT_FILES,
    build_run_receipt,
    sha256_file,
    write_json,
    write_summary,
)
from src.ml.value_mvp.sources import (
    Match,
    build_dataset,
    evaluation_population_hash,
    load_csv_rows,
    load_observations,
    season_counts,
)

if TYPE_CHECKING:
    from pathlib import Path

INPUT_HASHES = {
    "raw_odds_2223.csv": "e51361323bcdcdcec2faf8f58e7bcfc4f5b193ed6017b284c71538ed70d98ea2",
    "raw_odds_2324.csv": "0b669038e94bf305603d841f02006c7d35ebd41c8722c76e479f2393079b995f",
    "real_odds_raw.csv": "045cb84f6a75dc947e5aa5c4170c844237c1dcd489ae3264a795f39a20114361",
}
OBSERVATION_COUNTS = {
    "raw_odds_2223.jsonl": 13572,
    "raw_odds_2324.jsonl": 12510,
    "real_odds_raw.jsonl": 12534,
}
# Content pins for the M3-R2 canonical accepted observations and receipt
# (fail-closed: counts alone do not protect the odds that the benchmark
# compares against). Values are the SHA256 of the M3-R2 rebuild-BUILD_A
# byte-deterministic exports (A == B verified).
OBSERVATION_HASHES = {
    "raw_odds_2223.jsonl": "ae2fffe64813eefa8be3719299dec550a473b2b7e603dfd3ed7d8522e0c21f2f",
    "raw_odds_2324.jsonl": "1e33be60a9a68bac0a2bc657f6d0f1488f91d1a621d2c490a8f37c0ce19c0a58",
    "real_odds_raw.jsonl": "c2730fbd12308bb7b02cde8df2dc701c623fdad17603afb8e930c9904ee7d859",
}
RECEIPT_HASH = "c2141746a08ec58aaa3453810b8a4a4da0184383949fa4817d377736328c1b9d"
RECEIPT_SCHEMA = "m3-historical-odds-rebuild-receipt/v3"
CONTRACT_ID = "football-data-provider-contract/v1"

DATA_GATES = {
    "total_eligible_min": 850,
    "fold1_oos_min": 300,
    "fold2_oos_min": 100,
    "pooled_oos_min": 400,
}

_LABEL_INDEX = {"H": 0, "D": 1, "A": 2}


def _round_json(value: float) -> float:
    """Round for deterministic byte-stable serialization (None for NaN)."""
    if value is None:
        return None  # type: ignore[return-value]
    return evaluation.safe_round(value)


def _verify_observation_files(observations_dir: Path) -> tuple[dict, set[str]]:
    """Pin-count and pin-hash each observation JSONL; collect matched ids."""
    record: dict = {}
    distinct_matched_ids: set[str] = set()
    for name, expected_count in OBSERVATION_COUNTS.items():
        path = observations_dir / name
        count = 0
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                count += 1
                obs = json.loads(line)
                match_link = obs.get("match_link") or {}
                mid = match_link.get("matched_id")
                if mid:
                    distinct_matched_ids.add(mid)
        if count != expected_count:
            raise ValueError(f"observation count mismatch {name}: {count} != {expected_count}")
        actual = sha256_file(path)
        expected_hash = OBSERVATION_HASHES.get(name)
        if expected_hash is None:
            raise ValueError(f"no pinned observation hash for {name}")
        if actual != expected_hash:
            raise ValueError(f"observation hash mismatch {name}: {actual} != {expected_hash}")
        record[name] = {"lines": count, "sha256": actual, "pinned": expected_hash}
    return record, distinct_matched_ids


def _verify_receipt(observations_dir: Path) -> dict:
    """Pin-hash the receipt and validate its schema + readiness declaration."""
    receipt = observations_dir / "receipt.json"
    if not receipt.exists():
        raise FileNotFoundError("missing receipt.json")
    actual_receipt_hash = sha256_file(receipt)
    if actual_receipt_hash != RECEIPT_HASH:
        raise ValueError(f"receipt hash mismatch: {actual_receipt_hash} != {RECEIPT_HASH}")
    with receipt.open("r", encoding="utf-8") as handle:
        receipt_content = json.load(handle)
    actual_schema = receipt_content.get("schema_version") or receipt_content.get("schema")
    if actual_schema != RECEIPT_SCHEMA:
        raise ValueError(f"receipt schema mismatch: {actual_schema} != {RECEIPT_SCHEMA}")
    readiness = (receipt_content.get("evaluation_readiness") or {}).get(
        "closing_market_benchmark_semantics_ready"
    )
    if readiness != "YES":
        raise ValueError(f"receipt closing benchmark readiness: {readiness!r} != 'YES'")
    return {
        "sha256": actual_receipt_hash,
        "pinned": RECEIPT_HASH,
        "schema": actual_schema,
        "closing_market_benchmark_semantics_ready": readiness,
    }


def verify_inputs(input_dir: Path) -> dict:
    """Verify pinned input hashes/counts; return an input identity record.

    Fail-closed: CSV files, observation JSONL files AND receipt.json are all
    pinned by SHA256 (not just counts); the receipt's schema and its closing
    benchmark readiness declaration are validated against the contract.
    """
    csv_dir = input_dir / "csv"
    observations_dir = input_dir / "observations"
    record: dict = {"csv_files": {}, "observation_files": {}}
    for name, expected in INPUT_HASHES.items():
        path = csv_dir / name
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"input hash mismatch {name}: {actual} != {expected}")
        record["csv_files"][name] = {"sha256": actual, "pinned": expected}
    observation_files, distinct_matched_ids = _verify_observation_files(observations_dir)
    record["observation_files"] = observation_files
    record["receipt.json"] = _verify_receipt(observations_dir)
    record["source_population_derived"] = {"distinct_matched_ids": len(distinct_matched_ids)}
    return record


def load_inputs(input_dir: Path, protocol: dict) -> tuple[list[Match], dict]:
    """Load observations + CSVs, build the dataset, verify population invariants."""
    csv_rows = load_csv_rows(input_dir / "csv")
    observations = load_observations(input_dir / "observations")
    matches = build_dataset(observations, csv_rows, protocol)
    counts = season_counts(matches)
    expected = protocol["population_policy"]["expected_population"]
    if counts != expected["per_season"] or len(matches) != expected["total"]:
        raise ValueError(
            f"population drift: got {counts} total {len(matches)}, expected {expected}"
        )
    return matches, {"per_season": counts, "total": len(matches)}


def build_input_manifest(
    input_dir: Path, protocol: dict, matches: list[Match], git_revision: str
) -> dict:
    """Assemble the input manifest (source identities, hashes, population)."""
    inputs = verify_inputs(input_dir)
    return {
        "schema": "value-mvp-1-input-manifest/v1",
        "git_revision": git_revision,
        "protocol_sha256": protocol_sha256(protocol),
        "protocol_schema": protocol["schema_version"],
        "m3_receipt_schema": "m3-historical-odds-rebuild-receipt/v3",
        "provider_contract_id": CONTRACT_ID,
        "sources": inputs,
        "evaluation_population": {
            "total": len(matches),
            "per_season": season_counts(matches),
            "population_hash": evaluation_population_hash(matches),
            "exact_link_subset": True,
        },
    }


def check_contract_module(repo_root: Path) -> str:
    """Verify the M3 provider contract module exists in the repo with the expected id."""
    contract_path = repo_root / "src/infrastructure/odds_staging/footballDataProviderContract.js"
    if not contract_path.exists():
        raise FileNotFoundError(f"provider contract module missing: {contract_path}")
    content = contract_path.read_text(encoding="utf-8")
    if CONTRACT_ID not in content:
        raise ValueError(f"contract id {CONTRACT_ID} not found in contract module")
    return sha256_file(contract_path)


def _closing_coverage(matches: list[Match], protocol: dict) -> int:
    """Count matches with a valid closing consensus (min bookmaker count)."""
    return sum(1 for match in matches if closing_consensus(match, protocol) is not None)


def _split_invariant(matches: list[Match], protocol: dict) -> dict:
    """Per-fold assertion: max(train kickoff) < min(test kickoff), by ISO string."""
    results: dict[str, str] = {}
    for fold_name, fold in protocol["season_split_policy"].items():
        if not fold_name.startswith("fold"):
            continue  # policy-level keys (e.g. no_random_split) are not folds
        if not isinstance(fold, dict):
            raise TypeError(f"season_split_policy entry not a dict: {fold_name}")
        train_seasons, test_seasons = fold.get("train", []), fold.get("test", [])
        if not train_seasons or not test_seasons:
            results[fold_name] = "FAIL: empty train or test seasons"
            continue
        train_kickoffs = [m.kickoff_at for m in matches if m.season in train_seasons]
        test_kickoffs = [m.kickoff_at for m in matches if m.season in test_seasons]
        if not train_kickoffs or not test_kickoffs:
            results[fold_name] = "FAIL: no matches in train or test seasons"
            continue
        if max(train_kickoffs) >= min(test_kickoffs):
            results[fold_name] = (
                f"FAIL: max(train) {max(train_kickoffs)} >= min(test) {min(test_kickoffs)}"
            )
        else:
            results[fold_name] = "PASS"
    return results


def population_gates(
    matches: list[Match],
    protocol: dict,
    contract_status: dict,
    inputs_verified: bool = True,
) -> dict:
    """Evaluate the mandatory data gates from actual data (fail closed).

    Every status is the result of a performed check; no literal PASS exists.
    """
    counts = season_counts(matches)
    gates: dict = {
        "season_counts": counts,
        "total_matches": len(matches),
        "CANONICAL_SOURCE_RECOVERY": "PASS" if inputs_verified else "FAIL",
        "M3_PROVIDER_CONTRACT": "FAIL",
        "SOURCE_POPULATION_NO_DRIFT": "NO",
        "VALID_LABELS_SUFFICIENT": "NO",
        "SEASON_SPLIT_VALID": "FAIL",
        "CLOSING_BENCHMARK_COVERAGE": "FAIL",
    }

    # Data-gate thresholds (mandate §67)
    if len(matches) < DATA_GATES["total_eligible_min"]:
        raise ValueError(
            f"data gate failed: total {len(matches)} < {DATA_GATES['total_eligible_min']}"
        )
    fold1_test = counts.get("2023/24", 0)
    fold2_test = counts.get("2024/25", 0)
    if fold1_test < DATA_GATES["fold1_oos_min"]:
        raise ValueError(
            f"data gate failed: fold1 OOS {fold1_test} < {DATA_GATES['fold1_oos_min']}"
        )
    if fold2_test < DATA_GATES["fold2_oos_min"]:
        raise ValueError(
            f"data gate failed: fold2 OOS {fold2_test} < {DATA_GATES['fold2_oos_min']}"
        )
    if fold1_test + fold2_test < DATA_GATES["pooled_oos_min"]:
        raise ValueError(
            f"data gate failed: pooled OOS {fold1_test + fold2_test} < {DATA_GATES['pooled_oos_min']}"
        )
    gates["fold1_oos"] = fold1_test
    gates["fold2_oos"] = fold2_test
    gates["pooled_oos"] = fold1_test + fold2_test

    # M3 provider contract module (checked against the actual repo)
    if contract_status is None or contract_status.get("status") != "PASS":
        raise ValueError(
            f"data gate failed: M3 provider contract "
            f"{'not checked' if contract_status is None else contract_status.get('reason')}"
        )
    gates["M3_PROVIDER_CONTRACT"] = "PASS"
    gates["contract_sha256"] = contract_status.get("contract_sha256")

    # Source population drift vs the frozen protocol expectation
    expected = protocol["population_policy"]["expected_population"]
    if len(matches) != expected["total"] or counts != expected["per_season"]:
        raise ValueError(
            f"data gate failed: population drift {len(matches)}/{counts} != "
            f"{expected['total']}/{expected['per_season']}"
        )
    gates["SOURCE_POPULATION_NO_DRIFT"] = "YES"

    # Labels: every match carries a valid FTR label from its pinned source rows
    if not all(match.label_str in _LABEL_INDEX for match in matches):
        raise ValueError("data gate failed: some matches lack a valid FTR label")
    gates["VALID_LABELS_SUFFICIENT"] = "YES"

    # Chronological walk-forward split invariant
    split_results = _split_invariant(matches, protocol)
    if any(result != "PASS" for result in split_results.values()):
        raise ValueError(f"data gate failed: season split invalid: {split_results}")
    gates["SEASON_SPLIT_VALID"] = "PASS"
    gates["split_details"] = split_results

    # Closing-benchmark eligibility for EVERY match (not only test rows)
    covered = _closing_coverage(matches, protocol)
    if covered != len(matches):
        raise ValueError(
            f"data gate failed: closing benchmark coverage {covered}/{len(matches)} != total"
        )
    gates["CLOSING_BENCHMARK_COVERAGE"] = "PASS"
    gates["closing_benchmark_covered"] = covered

    gates["population_hash"] = evaluation_population_hash(matches)
    return gates


def phase0_probe(matches: list[Match], protocol: dict) -> dict:
    """Market probe: first-collection vs closing consensus performance, per season."""
    excluded = tuple(protocol["population_policy"]["bookmaker_exclusion"])
    per_season: dict[str, dict] = {}
    for season in sorted({m.season for m in matches}):
        season_matches = [m for m in matches if m.season == season]
        per_season[season] = _phase_stats(season_matches, protocol)
        per_season[season]["matches"] = len(season_matches)
    overall_stats = _phase_stats(matches, protocol)
    return {
        "eligible_matches": len(matches),
        "closing_coverage": overall_stats["closing_coverage"],
        "first_collection_coverage": overall_stats["first_collection_coverage"],
        "bookmaker_count_distribution": overall_stats["bookmaker_count_distribution"],
        "overround": overall_stats["overround"],
        "first_collection": overall_stats["first_collection"],
        "closing": overall_stats["closing"],
        "per_season": per_season,
        "bookmaker_exclusion_applied": list(excluded),
        "minimum_bookmaker_count": protocol["minimum_bookmaker_count"],
    }


def _phase_stats(matches: list[Match], protocol: dict) -> dict:
    """Phase statistics for a match set (both phases)."""
    closing_vectors = []
    first_vectors = []
    bookmaker_counts: dict[int, int] = {}
    closing_overrounds: list[float] = []
    first_overrounds: list[float] = []
    for match in matches:
        closing = closing_consensus(match, protocol)
        first = first_collection_consensus(match, protocol)
        if closing is not None:
            closing_vectors.append((match, closing["p"]))
            bookmaker_counts[closing["n_bookmakers"]] = (
                bookmaker_counts.get(closing["n_bookmakers"], 0) + 1
            )
            overround = mean_overround(closing)
            if overround is not None:
                closing_overrounds.append(overround)
        if first is not None:
            first_vectors.append((match, first["p"]))
            overround = mean_overround(first)
            if overround is not None:
                first_overrounds.append(overround)

    def metrics(vectors: list) -> dict:
        if not vectors:
            return {"count": 0}
        probs = np.array([vec for _match, vec in vectors])
        labels = np.array([match.label for match, _vec in vectors])
        return {
            "count": len(vectors),
            "log_loss": _round_json(evaluation.log_loss_score(probs, labels, 1e-15)),
            "brier": _round_json(evaluation.brier_score(probs, labels)),
            "accuracy": _round_json(evaluation.accuracy(probs, labels)),
        }

    return {
        "closing_coverage": len(closing_vectors),
        "first_collection_coverage": len(first_vectors),
        "bookmaker_count_distribution": {str(k): v for k, v in sorted(bookmaker_counts.items())},
        "overround": {
            "closing_mean": _round_json(float(np.mean(closing_overrounds)))
            if closing_overrounds
            else None,
            "closing_median": _round_json(float(np.median(closing_overrounds)))
            if closing_overrounds
            else None,
            "first_collection_mean": _round_json(float(np.mean(first_overrounds)))
            if first_overrounds
            else None,
        },
        "first_collection": metrics(first_vectors),
        "closing": metrics(closing_vectors),
    }


def run_fold(
    fold_name: str,
    train_seasons: list[str],
    test_seasons: list[str],
    matches: list[Match],
    feature_rows: list[dict],
    protocol: dict,
    artifacts_dir: Path,
) -> dict:
    """Train on train_seasons, predict on test_seasons; return fold results."""
    # Function-level sklearn imports: tests/unit/ml/test_training_no_write_guard.py
    # stubs sys.modules["sklearn"] with __path__=[] at import time, which would
    # break the CI collection gate if these were module-level.
    from sklearn.impute import SimpleImputer  # noqa: PLC0415
    from sklearn.linear_model import LogisticRegression  # noqa: PLC0415
    from sklearn.preprocessing import StandardScaler  # noqa: PLC0415

    train_indices = [i for i, m in enumerate(matches) if m.season in train_seasons]
    test_indices = [i for i, m in enumerate(matches) if m.season in test_seasons]
    x_all = np.array([[row[name] for name in FEATURE_NAMES] for row in feature_rows], dtype=float)
    x_train, y_train = x_all[train_indices], np.array([matches[i].label for i in train_indices])
    x_test = x_all[test_indices]

    imputer = SimpleImputer(strategy="median")
    imputer.fit(x_train)
    if np.any(np.isnan(imputer.statistics_)):
        raise ValueError(f"{fold_name}: all-NaN column in training fold")

    x_train_imputed = imputer.transform(x_train)
    scaler = StandardScaler()
    scaler.fit(x_train_imputed)
    x_train_scaled = scaler.transform(x_train_imputed)

    hyperparameters = dict(protocol["model_hyperparameters"])
    model = LogisticRegression(**hyperparameters)
    model.fit(x_train_scaled, y_train)
    # Record optimizer convergence: with lbfgs the fitted coefficients can stop
    # at the iteration limit (ConvergenceWarning), making probabilities depend
    # on the optimizer trajectory and therefore on the pinned environment.
    iterations = int(max(model.n_iter_))
    max_iter = int(hyperparameters.get("max_iter", 0))
    convergence = {
        "converged": iterations < max_iter,
        "iterations": iterations,
        "max_iter": max_iter,
    }

    x_test_scaled = scaler.transform(imputer.transform(x_test))
    model_probs = model.predict_proba(x_test_scaled)
    evaluation.validate_probability_matrix(model_probs, f"{fold_name} model")

    predictions: list[dict] = []
    market_rows: list[dict] = []
    for position, match in enumerate([matches[i] for i in test_indices]):
        closing = closing_consensus(match, protocol)
        if closing is None:
            raise ValueError(f"{fold_name}: closing benchmark missing for {match.mid}")
        market_p = closing["p"]
        market_rows.append({"p": market_p, "n_bookmakers": closing["n_bookmakers"]})
        predictions.append(
            _prediction_row(
                fold_name, match, model_probs[position], market_p, closing["n_bookmakers"]
            )
        )

    labels = np.array([matches[i].label for i in test_indices])
    market_probs = np.array([row["p"] for row in market_rows])
    evaluation.validate_probability_matrix(market_probs, f"{fold_name} market")

    metrics = _fold_metrics(model_probs, market_probs, labels, protocol)
    metrics["fold"] = fold_name
    metrics["train_seasons"] = train_seasons
    metrics["test_seasons"] = test_seasons
    metrics["oos_count"] = len(test_indices)

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for name, obj in (("imputer", imputer), ("scaler", scaler), ("model", model)):
        _dump_artifact(artifacts_dir, f"{fold_name}_{name}.joblib", obj)

    return {
        "metrics": metrics,
        "predictions": predictions,
        "labels": labels.tolist(),
        "convergence": convergence,
    }


def _prediction_row(
    fold_name: str, match: Match, model_p: np.ndarray, market_p: tuple, n_bookmakers: int
) -> dict:
    """One auditable OOS prediction row (protocol section 53)."""
    return {
        "match_identity": match.mid,
        "season": match.season,
        "kickoff": match.kickoff_at,
        "home": match.home,
        "away": match.away,
        "actual_result": match.label_str,
        "model_p_home": _round_json(float(model_p[0])),
        "model_p_draw": _round_json(float(model_p[1])),
        "model_p_away": _round_json(float(model_p[2])),
        "market_p_home": _round_json(float(market_p[0])),
        "market_p_draw": _round_json(float(market_p[1])),
        "market_p_away": _round_json(float(market_p[2])),
        "valid_closing_bookmaker_count": n_bookmakers,
        "fold_id": fold_name,
    }


def _fold_metrics(
    model_probs: np.ndarray, market_probs: np.ndarray, labels: np.ndarray, protocol: dict
) -> dict:
    """Per-fold metrics for model, market and the class-frequency baseline."""
    eps = protocol.get("log_loss_eps", 1e-15)
    class_frequency = evaluation.class_frequency_probabilities(labels)
    class_frequency_probs = np.tile(class_frequency, (len(labels), 1))
    return {
        "model_log_loss": _round_json(evaluation.log_loss_score(model_probs, labels, eps)),
        "market_log_loss": _round_json(evaluation.log_loss_score(market_probs, labels, eps)),
        "class_frequency_log_loss": _round_json(
            evaluation.log_loss_score(class_frequency_probs, labels, eps)
        ),
        "delta_log_loss": _round_json(
            evaluation.log_loss_score(model_probs, labels, eps)
            - evaluation.log_loss_score(market_probs, labels, eps)
        ),
        "model_brier": _round_json(evaluation.brier_score(model_probs, labels)),
        "market_brier": _round_json(evaluation.brier_score(market_probs, labels)),
        "delta_brier": _round_json(
            evaluation.brier_score(model_probs, labels)
            - evaluation.brier_score(market_probs, labels)
        ),
        "model_accuracy": _round_json(evaluation.accuracy(model_probs, labels)),
        "market_accuracy": _round_json(evaluation.accuracy(market_probs, labels)),
    }


def _dump_artifact(directory: Path, name: str, obj) -> None:
    """Persist a model artifact (research evidence, never committed)."""
    joblib.dump(obj, directory / name)


def write_predictions_csv(path: Path, predictions: list[dict]) -> None:
    """Write auditable prediction rows as deterministic CSV."""
    columns = [
        "match_identity",
        "season",
        "kickoff",
        "home",
        "away",
        "actual_result",
        "model_p_home",
        "model_p_draw",
        "model_p_away",
        "market_p_home",
        "market_p_draw",
        "market_p_away",
        "valid_closing_bookmaker_count",
        "fold_id",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv_module.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in predictions:
            writer.writerow({key: row[key] for key in columns})


def pooled_results(fold1: dict, fold2: dict, protocol: dict) -> dict:
    """Pool fold OOS rows and recompute metrics + bootstrap + claim."""
    combined = fold1["predictions"] + fold2["predictions"]
    eps = protocol.get("log_loss_eps", 1e-15)
    n = len(combined)
    model_probs = np.array(
        [[p["model_p_home"], p["model_p_draw"], p["model_p_away"]] for p in combined]
    )
    market_probs = np.array(
        [[p["market_p_home"], p["market_p_draw"], p["market_p_away"]] for p in combined]
    )
    labels = np.array([{"H": 0, "D": 1, "A": 2}[p["actual_result"]] for p in combined])
    evaluation.validate_probability_matrix(model_probs, "pooled model")
    evaluation.validate_probability_matrix(market_probs, "pooled market")

    per_row_model = evaluation.per_row_log_loss(model_probs, labels, eps)
    per_row_market = evaluation.per_row_log_loss(market_probs, labels, eps)
    delta_log_loss = per_row_model - per_row_market
    per_row_model_brier = evaluation.per_row_brier(model_probs, labels)
    per_row_market_brier = evaluation.per_row_brier(market_probs, labels)
    delta_brier = per_row_model_brier - per_row_market_brier

    deltas_by_season: dict[str, np.ndarray] = {}
    brier_by_season: dict[str, np.ndarray] = {}
    for i, row in enumerate(combined):
        season = row["season"]
        deltas_by_season.setdefault(season, []).append(delta_log_loss[i])
        brier_by_season.setdefault(season, []).append(delta_brier[i])
    deltas_by_season = {season: np.array(values) for season, values in deltas_by_season.items()}
    brier_by_season = {season: np.array(values) for season, values in brier_by_season.items()}

    replicates = int(protocol["bootstrap"]["replicates"])
    seed = int(protocol["bootstrap"]["seed"])
    percentiles = protocol["bootstrap"]["ci_percentiles"]
    ll_replicates = season_stratified_bootstrap_deltas(deltas_by_season, replicates, seed)
    ll_low, ll_high = percentile_ci(ll_replicates, percentiles)
    brier_replicates = season_stratified_bootstrap_deltas(brier_by_season, replicates, seed)
    brier_low, brier_high = percentile_ci(brier_replicates, percentiles)

    metrics = _fold_metrics(model_probs, market_probs, labels, protocol)
    metrics["fold"] = "pooled"
    metrics["oos_count"] = n
    metrics["delta_log_loss_ci95_low"] = _round_json(ll_low)
    metrics["delta_log_loss_ci95_high"] = _round_json(ll_high)
    metrics["delta_brier_ci95_low"] = _round_json(brier_low)
    metrics["delta_brier_ci95_high"] = _round_json(brier_high)
    metrics["final_classification"] = classify_claim(ll_low, ll_high)
    metrics["power_statement"] = (
        f"n={n} pooled (fold1 {len(fold1['predictions'])} + fold2 {len(fold2['predictions'])}); "
        "small n means small differences cannot be distinguished; INCONCLUSIVE is a valid result"
    )

    calibration = evaluation.calibration_summary(model_probs, labels, protocol["calibration_bins"])
    calibration_market = evaluation.calibration_summary(
        market_probs, labels, protocol["calibration_bins"]
    )
    bootstrap = {
        "method": protocol["statistical_inference_method"],
        "replicates": replicates,
        "seed": seed,
        "ci_percentiles": percentiles,
        "delta_log_loss_ci95_low": _round_json(ll_low),
        "delta_log_loss_ci95_high": _round_json(ll_high),
        "delta_brier_ci95_low": _round_json(brier_low),
        "delta_brier_ci95_high": _round_json(brier_high),
    }
    return {
        "metrics": metrics,
        "predictions": combined,
        "bootstrap": bootstrap,
        "calibration": {"model": calibration, "market": calibration_market},
    }


def freeze_protocol(protocol: dict, output_dir: Path) -> None:
    """Write protocol-copy.json + protocol-sha256.txt (pre-OOS freeze record)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "protocol-copy.json", protocol)
    (output_dir / "protocol-sha256.txt").write_text(
        protocol_sha256(protocol) + "\n", encoding="utf-8"
    )


def verify_frozen_protocol(protocol: dict, freeze_dir: Path) -> None:
    """Abort when the loaded protocol does not match the frozen protocol hash."""
    sha_file = freeze_dir / "protocol-sha256.txt"
    if not sha_file.exists():
        raise ValueError(
            "protocol not frozen: protocol-sha256.txt missing; freeze before running OOS"
        )
    frozen = sha_file.read_text(encoding="utf-8").strip()
    actual = protocol_sha256(protocol)
    if actual != frozen:
        raise ValueError(f"protocol drift: {actual} != frozen {frozen}")


def run_oos(
    matches: list[Match],
    protocol: dict,
    output_dir: Path,
    git_revision: str,
    input_dir: Path,
    freeze_dir: Path,
) -> dict:
    """Full OOS run: folds, pooled, bootstrap, calibration, receipts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    verify_frozen_protocol(protocol, freeze_dir)

    ordered = sorted(matches, key=lambda m: (m.kickoff_at, m.mid))
    feature_rows = build_feature_frame(ordered)
    if len(feature_rows) != len(ordered):
        raise ValueError("feature frame length mismatch")

    artifacts_dir = output_dir / "artifacts"
    fold1 = run_fold(
        "fold1",
        protocol["season_split_policy"]["fold1"]["train"],
        protocol["season_split_policy"]["fold1"]["test"],
        ordered,
        feature_rows,
        protocol,
        artifacts_dir,
    )
    fold2 = run_fold(
        "fold2",
        protocol["season_split_policy"]["fold2"]["train"],
        protocol["season_split_policy"]["fold2"]["test"],
        ordered,
        feature_rows,
        protocol,
        artifacts_dir,
    )
    pooled = pooled_results(fold1, fold2, protocol)

    write_predictions_csv(output_dir / "fold1-predictions.csv", fold1["predictions"])
    write_predictions_csv(output_dir / "fold2-predictions.csv", fold2["predictions"])
    write_json(output_dir / "fold1-metrics.json", fold1["metrics"])
    write_json(output_dir / "fold2-metrics.json", fold2["metrics"])
    write_json(output_dir / "pooled-metrics.json", pooled["metrics"])
    write_json(output_dir / "bootstrap.json", pooled["bootstrap"])
    write_json(output_dir / "calibration.json", pooled["calibration"])
    write_json(output_dir / "protocol-copy.json", protocol)
    (output_dir / "protocol-sha256.txt").write_text(
        protocol_sha256(protocol) + "\n", encoding="utf-8"
    )

    manifest = build_input_manifest(input_dir, protocol, matches, git_revision)
    write_json(output_dir / "input-manifest.json", manifest)

    population_manifest = {
        "evaluation_population_hash": evaluation_population_hash(matches),
        "per_season": season_counts(matches),
        "total": len(matches),
        "exact_link_subset": True,
    }
    write_json(output_dir / "evaluation-dataset-manifest.json", population_manifest)

    receipt = build_run_receipt(
        pooled,
        fold1,
        fold2,
        protocol,
        manifest,
        population_manifest,
        git_revision,
        output_dir,
        compute_digests=False,
    )
    write_summary(output_dir / "summary.md", receipt)
    receipt["output_digests"] = {
        name: sha256_file(output_dir / name) for name in _RECEIPT_OUTPUT_FILES
    }
    write_json(output_dir / "run-receipt.json", receipt)
    return receipt


def build_phase0_outputs(
    matches: list[Match],
    protocol: dict,
    input_dir: Path,
    output_dir: Path,
    git_revision: str,
    contract_status: dict,
) -> dict:
    """Phase 0 run: manifests + market probe + gates (no model)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    probe = phase0_probe(matches, protocol)
    # Manifest first: verify_inputs (pinned content hashes + receipt schema)
    # must succeed before any gate can be reported PASS.
    manifest = build_input_manifest(input_dir, protocol, matches, git_revision)
    gates = population_gates(matches, protocol, contract_status, inputs_verified=True)
    violations = feature_contract_violations(protocol)
    if violations:
        raise ValueError(f"feature contract violations: {violations}")
    name_violations = leakage.feature_name_violations()
    if name_violations:
        raise ValueError(f"feature name leakage violations: {name_violations}")
    gates["LEAKAGE_TESTS"] = "PASS" if not name_violations else "FAIL"
    gates["feature_contract_violations"] = violations
    write_json(output_dir / "market-probe.json", probe)
    write_json(output_dir / "phase0-gates.json", gates)
    write_json(output_dir / "input-manifest.json", manifest)
    write_json(
        output_dir / "evaluation-dataset-manifest.json",
        {
            "evaluation_population_hash": evaluation_population_hash(matches),
            "per_season": season_counts(matches),
            "total": len(matches),
            "exact_link_subset": True,
        },
    )
    write_json(output_dir / "protocol-copy.json", protocol)
    return {"probe": probe, "gates": gates, "manifest": manifest}
