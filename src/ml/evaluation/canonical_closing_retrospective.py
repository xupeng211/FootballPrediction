"""只消费已冻结证据的 RETROSPECTIVE_DIAGNOSTIC；不加载模型、不推理。

lifecycle: permanent。复用 GD-A01/frame 合同、canonical metrics 与已批准市场规则。
"""

from __future__ import annotations

from collections import Counter
import csv
from datetime import datetime
import io
import json
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING, Any

import numpy as np

from src.ml.evaluation import canonical_offline_model_evaluation_contract as contract
from src.ml.evaluation.canonical_offline_model_evaluation_artifacts import build_evaluation_receipt
from src.ml.evaluation.canonical_offline_model_evaluation_metrics import (
    metric_bundle,
    validate_probability_matrix,
)
from src.ml.training.canonical_training_producer import _row_id_hash
from src.ml.value_mvp.bootstrap import (
    classify_claim,
    percentile_ci,
    season_stratified_bootstrap_deltas,
)
from src.ml.value_mvp.evaluation import per_row_brier, per_row_log_loss
from src.ml.value_mvp.market import closing_consensus, no_vig, valid_triple
from src.ml.value_mvp.sources import Match, csv_row_for

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[3]
EVALUATION_SHA = "574a20ebde1e055e61e16789e23f21d9d7023f8cef4c379a4a14d0db15a11155"
EVALUATION_RECEIPT_SHA = "730f9c3620c3821b7dd96a6882750508f411d87aeb297df5f11450eb3e9401d5"
MISSION = "CANONICAL_CANDIDATE_VS_CLOSING_MARKET_RETROSPECTIVE_DIAGNOSTIC"
SELECTIONS = ("home", "draw", "away")
RESAMPLES = 10000
SEED = 20261008
MINIMUM_PAIRS = 30  # 描述性小样本门槛，不是功效/稳定优势证明。
LOCATOR_PARTS = 4

# 跨语言桥仅调用已有纯合同及原 adapter 的列映射。
BRIDGE = """
const fs = require('node:fs');
const {validateOutputFiles} = require('./src/infrastructure/golden_dataset/GdA01AssemblyContract');
const {validatePriorStateOutputFiles} = require('./src/infrastructure/golden_dataset/GdA03ArtifactContract');
const factsContract = require('./src/infrastructure/golden_dataset/GdA02FactsContract');
const {FOOTBALL_DATA_COLUMN_GROUPS} = require('./src/infrastructure/odds_staging/adapters');
const {buildSemanticDuplicateKey} = require('./src/infrastructure/odds_staging/contracts');
const {artifact} = validateOutputFiles(fs.readFileSync(process.argv[1]), fs.readFileSync(process.argv[2]));
validatePriorStateOutputFiles(fs.readFileSync(process.argv[3]), fs.readFileSync(process.argv[4]));
factsContract.validateOutputFiles(fs.readFileSync(process.argv[5]), fs.readFileSync(process.argv[6]));
const semanticKeys = {};
for (const row of artifact.rows) for (const obs of row.football_data.observations) {
 semanticKeys[obs.idempotency_key] = buildSemanticDuplicateKey(obs);
}
process.stdout.write(JSON.stringify({groups: FOOTBALL_DATA_COLUMN_GROUPS, semanticKeys}));
"""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise contract.EvaluationContractError(reason)


def _read(path: Path, expected: str | None = None) -> tuple[dict[str, Any], bytes]:
    _, payload = contract._read_external_file(path, "diagnostic source")
    if expected is not None:
        _require(contract._sha256_bytes(payload) == expected, "SOURCE_HASH_MISMATCH")
    return contract._parse_json(payload, "diagnostic source"), payload


def load_sources(paths: dict[str, Path]) -> dict[str, Any]:
    """绑定冻结 SHA、原收据、frame split 与 GD-A01→GD-A03→frame 证据链。"""
    protocol, protocol_hash, _ = contract.load_protocol(
        ROOT / "config/canonical_offline_model_evaluation_protocol.json"
    )
    evaluation, evaluation_bytes = _read(paths["evaluation"], EVALUATION_SHA)
    receipt, _ = _read(paths["evaluation_receipt"], EVALUATION_RECEIPT_SHA)
    expected_receipt = build_evaluation_receipt(
        evaluation,
        evaluation_bytes,
        protocol_freeze_sha=evaluation["protocol_freeze_sha"],
        evaluation_source_head=evaluation["evaluation_code_revision"],
    )
    _require(receipt == expected_receipt, "EVALUATION_RECEIPT_MISMATCH")
    _require(evaluation["evaluation_protocol_sha256"] == protocol_hash, "PROTOCOL_MISMATCH")
    _, candidate_bytes = contract._read_external_file(paths["candidate"], "frozen candidate")
    metadata, metadata_bytes = _read(paths["metadata"], protocol["candidate"]["metadata_sha256"])
    candidate_hash = contract._sha256_bytes(candidate_bytes)
    _require(candidate_hash == protocol["candidate"]["artifact_sha256"], "CANDIDATE_HASH_MISMATCH")
    contract.validate_candidate_metadata_binding(
        metadata,
        artifact_sha256=candidate_hash,
        metadata_sha256=contract._sha256_bytes(metadata_bytes),
        protocol=protocol,
    )
    population = contract._load_population(paths["frame"], paths["frame_receipt"], protocol)
    contract.validate_population_binding(population, protocol)
    frame, _ = _read(paths["frame"], protocol["frame"]["artifact_sha256"])
    gd03, _ = _read(paths["gd03"], frame["source_bindings"]["gd_a03_artifact"]["sha256"])
    _read(paths["gd03_receipt"], frame["source_bindings"]["gd_a03_receipt"]["sha256"])
    _read(paths["gd02"], gd03["source_bindings"]["gd_a02_artifact"]["sha256"])
    _read(paths["gd02_receipt"], gd03["source_bindings"]["gd_a02_receipt"]["sha256"])
    gd01, _ = _read(paths["gd01"], gd03["source_bindings"]["gd_a01_artifact"]["sha256"])
    _read(paths["gd01_receipt"], gd03["source_bindings"]["gd_a01_receipt"]["sha256"])
    result = subprocess.run(
        [
            "node",
            "-e",
            BRIDGE,
            *[
                str(paths[k])
                for k in ("gd01", "gd01_receipt", "gd03", "gd03_receipt", "gd02", "gd02_receipt")
            ],
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    _require(result.returncode == 0, "GD_CONTRACT_INVALID")
    recovered = json.loads(result.stdout)
    csv_rows = {}
    csv_hashes = {}
    for source in gd01["source_bindings"]["football_data_historical_odds"]["sources"]:
        _, raw = contract._read_external_file(paths["csv_dir"] / f"{source['id']}.csv", "saved CSV")
        _require(
            contract._sha256_bytes(raw) == source["raw_sha256"]
            and len(raw) == source["raw_size_bytes"],
            "CSV_HASH_MISMATCH",
        )
        blob = subprocess.run(
            ["git", "hash-object", "--stdin"],
            input=raw,
            capture_output=True,
            timeout=30,
            check=False,
        )
        _require(
            blob.returncode == 0
            and blob.stdout.decode().strip() == source["repository_provenance"]["blob_sha"],
            "CSV_BLOB_IDENTITY_MISMATCH",
        )
        csv_rows[source["id"]] = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        csv_hashes[source["id"]] = source["raw_sha256"]
    hashes = {
        key: contract._sha256_bytes(path.read_bytes())
        for key, path in paths.items()
        if key != "csv_dir"
    }
    hashes.update(csv_hashes)
    return {
        "evaluation": evaluation,
        "frame": frame,
        "gd01": gd01,
        "reserved_ids": list(population.reserved_ids),
        "csv_rows": csv_rows,
        "column_groups": recovered["groups"],
        "semantic_keys": recovered["semanticKeys"],
        "source_hashes": hashes,
    }


def _instant(text: str) -> datetime:
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    _require(parsed.tzinfo is not None, "KICKOFF_TIMEZONE_MISSING")
    return parsed


def _unique_index(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    index = {}
    for row in rows:
        _require(row[key] not in index, "DUPLICATE_OR_WRONG_JOIN")
        index[row[key]] = row
    return index


def _validate_identity(
    prediction: dict[str, Any], frame: dict[str, Any], spine: dict[str, Any]
) -> None:
    mid = prediction["row_id"]
    _require(
        mid
        == frame["canonical_match_id"]
        == spine["canonical_match_id"]
        == spine["source_linkage"]["matched_id"]
        == spine["fotmob_frozen_source"]["canonical_match_id"]
        == frame["target_label"]["canonical_match_id"],
        "MATCH_ID_MISMATCH",
    )
    frozen = frame["target_label"]["provenance_input"]["source_provenance"]["frozen"]
    _require(
        frozen["fotmob_match_id"] == spine["fotmob_frozen_source"]["fotmob_match_id"]
        and frozen["snapshot_id"] == spine["fotmob_frozen_source"]["snapshot_id"]
        and frozen["raw_payload_sha256"] == spine["fotmob_frozen_source"]["raw_payload_sha256"],
        "PROVIDER_IDENTITY_MISMATCH",
    )
    _require(
        _instant(prediction["kickoff_utc"])
        == _instant(frame["target_kickoff_utc"])
        == _instant(spine["kickoff_at"]),
        "KICKOFF_MISMATCH",
    )
    for side in ("home", "away"):
        _require(
            frame["target_match_identity"][f"{side}_team"] == spine[f"{side}_team"],
            "TEAM_ORDER_MISMATCH",
        )
    actual = prediction["actual_class"]
    _require(type(actual) is int and actual in contract.CLASS_ORDER, "OUTCOME_INVALID")
    outcome = contract.CLASS_NAMES[actual]
    _require(
        prediction["actual_class_name"] == outcome
        and frame["target_label"]["outcome"].upper() == outcome,
        "OUTCOME_MAPPING_INVALID",
    )


def _market(  # noqa: PLR0915 -- 每份完整报价先验证再折叠；不跨 source 拼三元组。
    spine: dict[str, Any], frame: dict[str, Any], sources: dict[str, Any], policy: dict[str, Any]
) -> tuple[list[float], list[dict[str, Any]]]:
    groups: dict[tuple[str, int, str, str, str], dict[str, Any]] = {}
    columns = {g["id"]: g for g in sources["column_groups"]}
    result = frame["target_label"]["provenance_input"]["result"]
    score = (result["home_score"], result["away_score"])
    expected_outcome = "home" if score[0] > score[1] else "away" if score[1] > score[0] else "draw"
    _require(
        result["outcome"] == frame["target_label"]["outcome"] == expected_outcome,
        "FINAL_SCORE_MISMATCH",
    )
    for obs in spine["football_data"]["observations"]:
        if obs["provider_collection_phase"] != "closing":
            continue
        _require(
            obs["market"] == "1X2" and obs["line"] is None and obs["snapshot_type"] == "closing",
            "CLOSING_MARKET_INVALID",
        )
        _require(
            obs["match_link"]["matched_id"] == spine["canonical_match_id"], "ODDS_MATCH_ID_MISMATCH"
        )
        _require(
            _instant(obs["kickoff_at"]) == _instant(spine["kickoff_at"]), "ODDS_KICKOFF_MISMATCH"
        )
        _require(
            all(obs[f"{s}_team"] == spine[f"{s}_team"] for s in ("home", "away")),
            "ODDS_TEAM_ORDER_MISMATCH",
        )
        locator = obs["raw_record_locator"].split(":")
        _require(
            len(locator) == LOCATOR_PARTS
            and locator[0] == "csv"
            and locator[3] == obs["selection"],
            "ODDS_SELECTION_MAPPING_INVALID",
        )
        source, row_number, family = (
            obs["source_id"],
            int(locator[1].removeprefix("row=")),
            locator[2],
        )
        _require(obs["raw_sha256"] == sources["source_hashes"][source], "ODDS_SOURCE_HASH_MISMATCH")
        csv_row = csv_row_for(sources["csv_rows"], source, row_number)
        _require((int(csv_row["FTHG"]), int(csv_row["FTAG"])) == score, "CSV_FINAL_SCORE_MISMATCH")
        _require(
            csv_row["FTR"] == {"home": "H", "draw": "D", "away": "A"}[expected_outcome],
            "CSV_OUTCOME_MISMATCH",
        )
        group = columns[family]
        _require(
            group["bookmaker_source_id"] == obs["bookmaker_source_id"]
            and group["source_quote_series"] == obs["source_quote_series"],
            "BOOKMAKER_SERIES_MISMATCH",
        )
        selection = obs["selection"]
        _require(selection in SELECTIONS, "ODDS_SELECTION_MAPPING_INVALID")
        _require(
            float(csv_row[group["columns"][selection]]) == obs["decimal_odds"],
            "ODDS_COLUMN_OR_VALUE_MISMATCH",
        )
        key = (source, row_number, obs["bookmaker_source_id"], obs["source_quote_series"], family)
        entry = groups.setdefault(key, {"selections": {}, "observations": []})
        _require(selection not in entry["selections"], "DUPLICATE_ODDS_SELECTION")
        entry["selections"][selection] = obs["decimal_odds"]
        entry["observations"].append(
            {
                k: obs[k]
                for k in ("idempotency_key", "raw_record_locator", "raw_sha256", "source_url")
            }
        )
    odds: dict[str, dict[str, float]] = {}
    details: list[dict[str, Any]] = []
    bookmaker_keys: dict[str, list[str]] = {}
    for key, entry in sorted(groups.items()):
        source, row_number, bookmaker, series, _ = key
        if bookmaker in policy["population_policy"]["bookmaker_exclusion"]:
            continue
        triple = (
            valid_triple(entry["selections"])
            if set(entry["selections"]) == set(SELECTIONS)
            else None
        )
        detail = {
            "source": source,
            "csv_row": row_number,
            "bookmaker": bookmaker,
            "series": series,
            "observations": entry["observations"],
        }
        if triple is None:
            detail["status"] = "INVALID_OR_INCOMPLETE_TRIPLE"
        else:
            keys = sorted(
                sources["semantic_keys"][o["idempotency_key"]] for o in entry["observations"]
            )
            if bookmaker in odds:
                _require(
                    entry["selections"] == odds[bookmaker] and keys == bookmaker_keys[bookmaker],
                    "AMBIGUOUS_MULTIPLE_QUOTES_PER_BOOKMAKER",
                )
                detail["status"] = "EQUIVALENT_DUPLICATE_NOT_DOUBLE_WEIGHTED"
                details.append(detail)
                continue
            p, overround = no_vig(triple)
            odds[bookmaker] = entry["selections"]
            bookmaker_keys[bookmaker] = keys
            detail.update(
                status="VALID",
                odds_hda=list(triple),
                probabilities_hda=list(p),
                overround=overround,
                margin=overround - 1,
            )
        details.append(detail)
    match = Match(
        spine["canonical_match_id"],
        spine["kickoff_at"],
        spine["home_team"],
        spine["away_team"],
        spine["season"],
        0,
        "",
        odds={"closing": odds},
    )
    consensus = closing_consensus(match, policy)
    if consensus is None:
        raise contract.EvaluationContractError("MISSING_VALID_CLOSING_ODDS")
    # 市场 H/D/A → canonical A/D/H；显式映射，不依赖 JSON key 顺序。
    return list(reversed(consensus["p"])), details


def analyze(sources: dict[str, Any]) -> dict[str, Any]:
    """每个 reserved ID 必须有去向；row 缺陷排除、全局合同缺陷停止评分。"""
    evaluation = sources["evaluation"]
    ids = sources["reserved_ids"]
    _require(len(ids) == contract.RESERVED_ROWS and len(set(ids)) == len(ids), "POPULATION_INVALID")
    _require(
        _row_id_hash(ids) == contract.EXPECTED_RESERVED_ROW_ID_SHA256, "POPULATION_HASH_MISMATCH"
    )
    output = evaluation["model_output"]
    _require(
        tuple(output["class_names"]) == contract.CLASS_NAMES
        and tuple(output["model_class_order"]) == contract.CLASS_ORDER
        and tuple(output["probability_column_order"]) == contract.PROBABILITY_COLUMN_ORDER,
        "PROBABILITY_CLASS_ORDER_INVALID",
    )
    _require(evaluation["population"]["reserved_row_ids"] == ids, "EVALUATION_POPULATION_MISMATCH")
    _require(
        evaluation["holdout"]["status_after"] == contract.RESERVED_STATUS_AFTER,
        "CONSUMED_HOLDOUT_REQUIRED",
    )
    predictions = _unique_index(evaluation["prediction_rows"], "row_id")
    _require(set(predictions) <= set(ids), "EXTRA_PREDICTION_OR_WRONG_JOIN")
    frames = _unique_index(sources["frame"]["rows"], "canonical_match_id")
    spines = _unique_index(sources["gd01"]["rows"], "canonical_match_id")
    policy = json.loads((ROOT / "config/value_mvp_1_evaluation_protocol.json").read_text())
    rows, model, market, labels = [], [], [], []
    for mid in ids:
        row = {"canonical_match_id": mid, "status": "EXCLUDED", "reason": None}
        try:
            _require(mid in predictions, "MISSING_FROZEN_PREDICTION")
            _require(mid in frames and mid in spines, "MISSING_IDENTITY_OR_OUTCOME")
            prediction, frame, spine = predictions[mid], frames[mid], spines[mid]
            _validate_identity(prediction, frame, spine)
            _require(
                set(prediction["probabilities"]) == set(contract.PROBABILITY_COLUMN_ORDER),
                "PROBABILITY_COLUMNS_INVALID",
            )
            p = [prediction["probabilities"][k] for k in contract.PROBABILITY_COLUMN_ORDER]
            validate_probability_matrix(np.asarray([p], dtype=float), expected_rows=1)
            q, bookmaker_details = _market(spine, frame, sources, policy)
            validate_probability_matrix(np.asarray([q], dtype=float), expected_rows=1)
            label = prediction["actual_class"]
            row.update(
                status="PAIRED",
                kickoff_utc=prediction["kickoff_utc"],
                fotmob_match_id=spine["fotmob_frozen_source"]["fotmob_match_id"],
                frozen_source=spine["fotmob_frozen_source"],
                home_team=spine["home_team"],
                away_team=spine["away_team"],
                final_score=frame["target_label"]["provenance_input"]["result"],
                actual_class=label,
                actual_class_name=contract.CLASS_NAMES[label],
                model_probabilities_adh=p,
                market_probabilities_adh=q,
                bookmakers=bookmaker_details,
                outcome_provenance_digest=frame["target_label"]["provenance_digest"],
            )
            model.append(p)
            market.append(q)
            labels.append(label)
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            row["reason"] = (
                str(exc)
                if isinstance(exc, contract.EvaluationContractError)
                else f"INVALID_ROW_EVIDENCE:{type(exc).__name__}"
            )
        rows.append(row)
    metrics: dict[str, Any] | None = None
    uncertainty: dict[str, Any] | None = None
    interpretation = "INSUFFICIENT_EVIDENCE"
    if len(labels) >= MINIMUM_PAIRS:
        model_array, market_array, y = (
            np.asarray(model),
            np.asarray(market),
            np.asarray(labels, dtype=int),
        )
        model_metrics, market_metrics = (
            metric_bundle(model_array, y),
            metric_bundle(market_array, y),
        )
        metrics = {
            "model": model_metrics,
            "market": market_metrics,
            "model_minus_market": {k: model_metrics[k] - market_metrics[k] for k in model_metrics},
            "paired_n": len(y),
        }
        uncertainty = {}
        functions: dict[
            str, Callable[[np.ndarray[Any, Any], np.ndarray[Any, Any]], np.ndarray[Any, Any]]
        ] = {"log_loss": per_row_log_loss, "brier": per_row_brier}
        for name, function in functions.items():
            m, b = function(model_array, y), function(market_array, y)
            delta = m - b
            ci = percentile_ci(
                season_stratified_bootstrap_deltas({"2023/24": delta}, RESAMPLES, SEED), [2.5, 97.5]
            )
            uncertainty[name] = {
                "paired_delta_mean": float(delta.mean()),
                "paired_delta_95_percentile_ci": list(ci),
            }
            for row, mv, bv in zip((r for r in rows if r["status"] == "PAIRED"), m, b, strict=True):
                row[name] = {"model": float(mv), "market": float(bv), "delta": float(mv - bv)}
        interpretation = classify_claim(*uncertainty["log_loss"]["paired_delta_95_percentile_ci"])
    return {
        "mission": MISSION,
        "analysis_type": "RETROSPECTIVE_DIAGNOSTIC",
        "candidate": evaluation["candidate"],
        "source_hashes": sources["source_hashes"],
        "accounted_matches": len(rows),
        "valid_paired_matches": len(labels),
        "excluded_matches": len(rows) - len(labels),
        "exclusion_reasons": dict(
            sorted(Counter(r["reason"] for r in rows if r["status"] == "EXCLUDED").items())
        ),
        "class_order": list(contract.CLASS_NAMES),
        "metrics": metrics,
        "uncertainty": uncertainty,
        "bootstrap": {
            "replicates": RESAMPLES,
            "seed": SEED,
            "minimum_pairs": MINIMUM_PAIRS,
            "assumption": "iid paired matches conditional on this consumed 2023/24 cohort; team/time dependence unmodelled",
        },
        "market_policy": {
            "source": "football-data.co.uk provider-defined closing 1X2; exact tick UNPROVEN",
            "no_vig": policy["market_no_vig_method"],
            "consensus": policy["market_consensus_method"],
            "minimum_bookmakers": policy["minimum_bookmaker_count"],
            "protocol_sha256": contract._sha256_bytes(
                (ROOT / "config/value_mvp_1_evaluation_protocol.json").read_bytes()
            ),
        },
        "result_interpretation": interpretation,
        "consumed_holdout_disclosed": True,
        "brier_definition": "mean(sum_k((p_k - one_hot(y)_k)^2)); unscaled [0,2]",
        "claim_boundary": "No fresh holdout, decision-time execution, tradable value, profitability, ROI or CLV proof",
        "rows": rows,
    }
