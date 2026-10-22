"""离线配对语义与负面合同测试；fixture 不替代真实研究资产。"""

from __future__ import annotations

from copy import deepcopy
import json
import socket
import sqlite3

import joblib
import numpy as np
import pytest
import xgboost as xgb

from src.ml.evaluation import canonical_closing_retrospective as diagnostic
from src.ml.training import canonical_training_producer as producer

CALIBRATION_STATISTICS = (
    "model_mean",
    "market_mean",
    "observed_frequency",
    "model_absolute_gap",
    "market_absolute_gap",
)


@pytest.fixture(autouse=True)
def prohibit_side_effects(monkeypatch):
    """所有测试禁止网络、训练、模型加载与子进程副作用。"""

    def forbidden(*_args, **_kwargs):
        pytest.fail("negative test attempted a forbidden side effect")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(joblib, "load", forbidden)
    monkeypatch.setattr(diagnostic.subprocess, "run", forbidden)
    monkeypatch.setattr(producer, "produce_candidate", forbidden)
    monkeypatch.setattr(producer, "fit_canonical_model", forbidden)
    monkeypatch.setattr(diagnostic.contract, "load_verified_candidate", forbidden)
    for method in ("fit", "predict", "predict_proba"):
        monkeypatch.setattr(xgb.XGBClassifier, method, forbidden)


@pytest.fixture
def sources(monkeypatch):
    """三个不对称 H/D/A fixture，显式保留每份完整市场报价。"""
    ids = [f"fixture-{i}" for i in range(3)]
    monkeypatch.setattr(diagnostic.contract, "RESERVED_ROWS", len(ids))
    monkeypatch.setattr(
        diagnostic.contract, "EXPECTED_RESERVED_ROW_ID_SHA256", producer._row_id_hash(ids)
    )
    monkeypatch.setattr(diagnostic, "MINIMUM_PAIRS", 2)
    predictions, frames, spines, csv_rows, semantic_keys = [], [], [], [], {}
    raw_hash = "a" * 64
    for i, mid in enumerate(ids):
        kickoff = f"2024-03-0{i + 1}T12:00:00Z"
        scores = [(0, 2), (1, 1), (3, 0)][i]
        outcome = diagnostic.contract.CLASS_NAMES[i].lower()
        frozen = {
            "fotmob_match_id": str(i),
            "snapshot_id": "snapshot",
            "raw_payload_sha256": "b" * 64,
        }
        result = {"home_score": scores[0], "away_score": scores[1], "outcome": outcome}
        probabilities = {"P_AWAY": 0.2, "P_DRAW": 0.3, "P_HOME": 0.5}
        predictions.append(
            {
                "row_id": mid,
                "kickoff_utc": kickoff,
                "actual_class": i,
                "actual_class_name": outcome.upper(),
                "probabilities": probabilities,
            }
        )
        frames.append(
            {
                "canonical_match_id": mid,
                "target_kickoff_utc": kickoff,
                "target_match_identity": {"home_team": "Home", "away_team": "Away"},
                "target_label": {
                    "canonical_match_id": mid,
                    "outcome": outcome,
                    "provenance_digest": "c" * 64,
                    "provenance_input": {"result": result, "source_provenance": {"frozen": frozen}},
                },
            }
        )
        observations = []
        csv_row = {"FTHG": str(scores[0]), "FTAG": str(scores[1]), "FTR": ["A", "D", "H"][i]}
        for bookmaker in ("B365", "PS"):
            family = f"{bookmaker}-closing"
            for selection, odd in zip(diagnostic.SELECTIONS, (2.0, 4.0, 5.0), strict=True):
                identity = f"{mid}:{bookmaker}:{selection}"
                observations.append(
                    {
                        "provider_collection_phase": "closing",
                        "market": "1X2",
                        "line": None,
                        "snapshot_type": "closing",
                        "kickoff_at": kickoff,
                        "match_link": {"matched_id": mid},
                        "home_team": "Home",
                        "away_team": "Away",
                        "raw_record_locator": f"csv:row={i + 2}:{family}:{selection}",
                        "source_id": "saved",
                        "raw_sha256": raw_hash,
                        "bookmaker_source_id": bookmaker,
                        "source_quote_series": f"{bookmaker}C",
                        "selection": selection,
                        "decimal_odds": odd,
                        "idempotency_key": identity,
                        "source_url": "saved://fixture",
                    }
                )
                csv_row[f"{bookmaker}C{selection[0].upper()}"] = str(odd)
                semantic_keys[identity] = identity
        csv_rows.append(csv_row)
        spines.append(
            {
                "canonical_match_id": mid,
                "kickoff_at": kickoff,
                "season": "2023/2024",
                "home_team": "Home",
                "away_team": "Away",
                "source_linkage": {"matched_id": mid},
                "fotmob_frozen_source": {**frozen, "canonical_match_id": mid},
                "football_data": {"observations": observations},
            }
        )
    return {
        "reserved_ids": ids,
        "evaluation": {
            "model_output": {
                "class_names": list(diagnostic.contract.CLASS_NAMES),
                "model_class_order": [0, 1, 2],
                "probability_column_order": list(diagnostic.contract.PROBABILITY_COLUMN_ORDER),
            },
            "population": {"reserved_row_ids": ids},
            "holdout": {"status_after": diagnostic.contract.RESERVED_STATUS_AFTER},
            "prediction_rows": predictions,
            "candidate": {"candidate_id": "fixture"},
        },
        "frame": {"rows": frames},
        "gd01": {"rows": spines},
        "source_hashes": {"saved": raw_hash},
        "csv_rows": {"saved": csv_rows},
        "semantic_keys": semantic_keys,
        "column_groups": [
            {
                "id": f"{b}-closing",
                "bookmaker_source_id": b,
                "source_quote_series": f"{b}C",
                "columns": {s: f"{b}C{s[0].upper()}" for s in diagnostic.SELECTIONS},
            }
            for b in ("B365", "PS")
        ],
    }


def test_valid_pair_class_mapping_metrics_and_determinism(sources):
    """A/D/H 显式映射、未缩放 Brier 与确定性输出。"""
    first = diagnostic.analyze(sources)
    second = diagnostic.analyze(deepcopy(sources))
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["valid_paired_matches"] == len(sources["reserved_ids"])
    row = first["rows"][0]
    q = np.array([1 / 5, 1 / 4, 1 / 2]) / (1 / 5 + 1 / 4 + 1 / 2)
    assert row["market_probabilities_adh"] == pytest.approx(q)
    assert row["log_loss"]["market"] == pytest.approx(-np.log(q[0]))
    assert row["brier"]["market"] == pytest.approx(np.sum((q - [1, 0, 0]) ** 2))
    assert row["bookmakers"][0]["margin"] == pytest.approx(-0.05)
    calibration = first["paired_calibration"]
    assert calibration["binning_basis"] == "model_probability"
    assert calibration["boundary_semantics"] == "left_closed_right_open_except_final_bin_includes_1.0"
    assert calibration["bin_edges"] == [0, 0.2, 0.4, 0.6, 0.8, 1]
    assert calibration["minimum_nonempty_bin_count"] == 10
    assert calibration["sample_status"] == "INSUFFICIENT_SAMPLE"
    assert list(calibration["classwise"]) == ["AWAY", "DRAW", "HOME"]
    for index, name in enumerate(("AWAY", "DRAW", "HOME")):
        bins = calibration["classwise"][name]
        assert len(bins) == 5
        assert sum(b["count"] for b in bins) == first["valid_paired_matches"]
        occupied = bins[1 if index < 2 else 2]
        assert occupied["count"] == 3
        assert occupied["model_mean"] == [0.2, 0.3, 0.5][index]
        assert occupied["market_mean"] == round(float(q[index]), 12)
        assert occupied["observed_frequency"] == round(1 / 3, 12)
        assert occupied["model_absolute_gap"] == round(abs([0.2, 0.3, 0.5][index] - 1 / 3), 12)
        assert occupied["market_absolute_gap"] == round(abs(float(q[index]) - 1 / 3), 12)


@pytest.mark.parametrize("field", ["class_names", "probability_column_order", "model_class_order"])
def test_global_column_order_rejected(sources, field):
    """全局 class-order 错误阻止任何指标。"""
    sources["evaluation"]["model_output"][field].reverse()
    with pytest.raises(ValueError, match="PROBABILITY_CLASS_ORDER_INVALID"):
        diagnostic.analyze(sources)


@pytest.mark.parametrize(
    "fault",
    [
        "id",
        "kickoff",
        "provider",
        "outcome",
        "odds_id",
        "odds_kickoff",
        "hash",
        "market",
        "column_swap",
        "duplicate_selection",
        "probability_columns",
    ],
)
def test_row_faults_excluded_and_accounted(sources, fault):  # noqa: C901 -- 独立业务故障矩阵。
    """关键身份、来源、列和市场失败必须留在全量 accounting。"""
    prediction = sources["evaluation"]["prediction_rows"][0]
    spine = sources["gd01"]["rows"][0]
    obs = spine["football_data"]["observations"][0]
    if fault == "id":
        spine["source_linkage"]["matched_id"] = "other"
    elif fault == "kickoff":
        prediction["kickoff_utc"] = "2024-03-01T12:01:00Z"
    elif fault == "provider":
        spine["fotmob_frozen_source"]["fotmob_match_id"] = "other"
    elif fault == "outcome":
        prediction["actual_class_name"] = "HOME"
    elif fault == "odds_id":
        obs["match_link"]["matched_id"] = "other"
    elif fault == "odds_kickoff":
        obs["kickoff_at"] = "2024-03-01T12:01:00Z"
    elif fault == "hash":
        obs["raw_sha256"] = "0" * 64
    elif fault == "market":
        obs["market"] = "first_half_1X2"
    elif fault == "column_swap":
        obs["decimal_odds"] = 5.0
    elif fault == "duplicate_selection":
        spine["football_data"]["observations"].append(deepcopy(obs))
    elif fault == "probability_columns":
        prediction["probabilities"]["HOME"] = prediction["probabilities"].pop("P_HOME")
    result = diagnostic.analyze(sources)
    assert result["accounted_matches"] == len(sources["reserved_ids"])
    assert result["excluded_matches"] == 1
    assert result["rows"][0]["reason"]
    assert result["rows"][0]["status"] == "EXCLUDED"
    assert result["exclusion_reasons"] == {result["rows"][0]["reason"]: 1}
    for name, bins in result["paired_calibration"]["classwise"].items():
        assert sum(b["count"] for b in bins) == result["valid_paired_matches"] == 2
        occupied = next(b for b in bins if b["count"])
        assert occupied["observed_frequency"] == (0.0 if name == "AWAY" else 0.5)


@pytest.mark.parametrize("selection", diagnostic.SELECTIONS)
def test_missing_odds_never_spliced_or_imputed(sources, selection):
    """两家公司各缺一项时，不能跨组拼报价。"""
    spine = sources["gd01"]["rows"][0]
    spine["football_data"]["observations"] = [
        o for o in spine["football_data"]["observations"] if o["selection"] != selection
    ]
    result = diagnostic.analyze(sources)
    assert result["rows"][0]["reason"] == "MISSING_VALID_CLOSING_ODDS"


@pytest.mark.parametrize("bad", [0.0, 1.0, -1.0, float("nan"), float("inf")])
def test_invalid_odds(sources, bad):
    """异常赔率不能变成市场概率。"""
    for obs in sources["gd01"]["rows"][0]["football_data"]["observations"]:
        obs["decimal_odds"] = bad
    assert diagnostic.analyze(sources)["rows"][0]["status"] == "EXCLUDED"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.1, 1.1, 0.0])
def test_invalid_probabilities(sources, bad):
    """非有限、越界与不归一的概率不被修补。"""
    sources["evaluation"]["prediction_rows"][0]["probabilities"]["P_HOME"] = bad
    assert diagnostic.analyze(sources)["rows"][0]["status"] == "EXCLUDED"


def test_missing_predictions_insufficient_evidence(sources):
    """缺失预测不静默丢弃；不足时没有指标或优势结论。"""
    sources["evaluation"]["prediction_rows"] = []
    result = diagnostic.analyze(sources)
    assert result["excluded_matches"] == len(sources["reserved_ids"])
    assert result["result_interpretation"] == "INSUFFICIENT_EVIDENCE"
    assert result["metrics"] is None
    assert result["uncertainty"] is None
    assert result["valid_paired_matches"] == 0
    calibration = result["paired_calibration"]
    assert calibration["sample_status"] == "INSUFFICIENT_SAMPLE"
    assert calibration["minimum_observed_nonempty_bin_count"] == 0
    for bins in calibration["classwise"].values():
        assert len(bins) == 5
        for entry in bins:
            assert entry["count"] == 0
            assert entry["sample_status"] == "INSUFFICIENT_SAMPLE"
            assert all(entry[key] is None for key in CALIBRATION_STATISTICS)


def test_duplicate_population_or_prediction_rejected(sources):
    """重复样本必须在全局失败，不能重复计分。"""
    sources["evaluation"]["prediction_rows"].append(
        deepcopy(sources["evaluation"]["prediction_rows"][0])
    )
    with pytest.raises(ValueError, match="DUPLICATE_OR_WRONG_JOIN"):
        diagnostic.analyze(sources)


def test_duplicate_population_and_extra_join_rejected(sources):
    """population 重复与额外预测均不能通过 conservation。"""
    duplicate = deepcopy(sources)
    duplicate["reserved_ids"][0] = duplicate["reserved_ids"][1]
    with pytest.raises(ValueError, match="POPULATION_INVALID"):
        diagnostic.analyze(duplicate)
    extra = deepcopy(sources["evaluation"]["prediction_rows"][0])
    extra["row_id"] = "not-reserved"
    sources["evaluation"]["prediction_rows"].append(extra)
    with pytest.raises(ValueError, match="EXTRA_PREDICTION_OR_WRONG_JOIN"):
        diagnostic.analyze(sources)


def test_equivalent_quotes_no_double_weight_conflicts_excluded(sources):
    """只有 canonical semantic identity 与完整三元组都等价才可折叠。"""
    observations = sources["gd01"]["rows"][0]["football_data"]["observations"]
    duplicate = deepcopy(observations)
    sources["csv_rows"]["copy"] = deepcopy(sources["csv_rows"]["saved"])
    sources["source_hashes"]["copy"] = sources["source_hashes"]["saved"]
    for obs in duplicate:
        previous = obs["idempotency_key"]
        obs["source_id"] = "copy"
        obs["idempotency_key"] += ":copy"
        sources["semantic_keys"][obs["idempotency_key"]] = sources["semantic_keys"][previous]
    before = diagnostic.analyze(sources)
    observations.extend(duplicate)
    after = diagnostic.analyze(sources)
    assert after["metrics"] == before["metrics"]
    assert any(
        b["status"] == "EQUIVALENT_DUPLICATE_NOT_DOUBLE_WEIGHTED"
        for b in after["rows"][0]["bookmakers"]
    )
    duplicate[0]["decimal_odds"] = 9.0
    sources["csv_rows"]["copy"][0]["B365CH"] = "9"
    assert diagnostic.analyze(sources)["rows"][0]["status"] == "EXCLUDED"


@pytest.mark.parametrize("source", ["evaluation", "receipt", "artifact", "source_sha"])
def test_tampered_file_hash_before_any_effect(tmp_path, source):
    """任何 source artifact/receipt/SHA 不匹配都在外部调用前失败。"""
    path = tmp_path / f"{source}.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_HASH_MISMATCH"):
        diagnostic._read(path, "0" * 64)


def test_cli_source_loader_tamper_fails_before_subprocess(tmp_path):
    """实际 consumer loader 在冻结预测被篡改时不能进入任何外部动作。"""
    path = tmp_path / "evaluation.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_HASH_MISMATCH"):
        diagnostic.load_sources({"evaluation": path})


@pytest.mark.parametrize("class_index", [0, 1, 2])
def test_paired_calibration_uses_model_mask_for_both_sides(class_index):
    """市场概率跨箱时仍只比较模型箱内同场，覆盖 A/D/H 映射。"""
    p = np.array([0.1, 0.15, 0.7])
    q = np.array([0.8, 0.05, 0.1])
    model = np.column_stack((p, (1 - p) / 2, (1 - p) / 2))
    market = np.column_stack((q, (1 - q) / 2, (1 - q) / 2))
    model = np.roll(model, class_index, axis=1)
    market = np.roll(market, class_index, axis=1)
    labels = np.array([class_index, (class_index + 1) % 3, (class_index + 2) % 3])
    result = diagnostic._paired_calibration_summary(model, market, labels)
    bins = result["classwise"][["AWAY", "DRAW", "HOME"][class_index]]
    assert bins[0] == {
        "bin": [0.0, 0.2],
        "count": 2,
        "model_mean": 0.125,
        "market_mean": 0.425,
        "observed_frequency": 0.5,
        "model_absolute_gap": 0.375,
        "market_absolute_gap": 0.075,
        "sample_status": "INSUFFICIENT_SAMPLE",
    }
    assert bins[3]["count"] == 1
    assert bins[3]["market_mean"] == 0.1
    assert bins[3]["observed_frequency"] == 0.0


@pytest.mark.parametrize("class_index", [0, 1, 2])
def test_paired_calibration_all_boundaries_and_conservation(class_index):
    """每个内部边界进右箱，0 和 1 均计数；各类别守恒。"""
    edges = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    model = np.roll(
        np.column_stack((edges, (1 - edges) / 2, (1 - edges) / 2)), class_index, axis=1
    )
    market = np.full((6, 3), 1 / 3)
    labels = np.arange(6) % 3
    result = diagnostic._paired_calibration_summary(model, market, labels)
    assert list(result["classwise"]) == ["AWAY", "DRAW", "HOME"]
    for bins in result["classwise"].values():
        assert len(bins) == 5
        assert [b["bin"] for b in bins] == [
            [0.0, 0.2],
            [0.2, 0.4],
            [0.4, 0.6],
            [0.6, 0.8],
            [0.8, 1.0],
        ]
        assert sum(b["count"] for b in bins) == 6
    bins = result["classwise"][["AWAY", "DRAW", "HOME"][class_index]]
    assert [b["count"] for b in bins] == [1, 1, 1, 1, 2]
    assert [b["model_mean"] for b in bins] == [0.0, 0.2, 0.4, 0.6, 0.9]
    assert all(b["market_mean"] == round(1 / 3, 12) for b in bins)


@pytest.mark.parametrize("count", [0, 9, 10])
def test_paired_calibration_fixed_sample_threshold_empty_bins_and_rounding(count):
    """非空箱门槛固定为 10；空箱不拉低顶层状态，五项均为空。"""
    model = np.full((count, 3), 1 / 3)
    market = np.tile([0.1, 0.3, 0.6], (count, 1))
    labels = np.zeros(count, dtype=int)
    result = diagnostic._paired_calibration_summary(model, market, labels)
    expected_status = "INSUFFICIENT_SAMPLE" if count < 10 else "DESCRIPTIVE_ONLY"
    assert result["sample_status"] == expected_status
    assert result["minimum_observed_nonempty_bin_count"] == count
    assert result["minimum_nonempty_bin_count"] == 10
    for index, name in enumerate(("AWAY", "DRAW", "HOME")):
        bins = result["classwise"][name]
        assert len(bins) == 5
        assert sum(b["count"] for b in bins) == count
        for entry in bins:
            if entry["count"]:
                assert entry["count"] == count
                assert entry["sample_status"] == expected_status
                frequency = float(index == 0)
                assert entry["model_mean"] == round(1 / 3, 12)
                assert entry["market_mean"] == [0.1, 0.3, 0.6][index]
                assert entry["observed_frequency"] == frequency
                assert entry["model_absolute_gap"] == round(abs(1 / 3 - frequency), 12)
                assert entry["market_absolute_gap"] == round(abs([0.1, 0.3, 0.6][index] - frequency), 12)
            else:
                assert entry["sample_status"] == "INSUFFICIENT_SAMPLE"
                assert all(entry[key] is None for key in CALIBRATION_STATISTICS)


def test_paired_calibration_top_level_uses_smallest_nonempty_bin():
    """总对数足够但存在小箱时，顶层仍提示小样本。"""
    model = np.array([[0.1, 0.3, 0.6]] * 10 + [[0.3, 0.3, 0.4]])
    result = diagnostic._paired_calibration_summary(model, model, np.zeros(11, dtype=int))
    assert result["minimum_observed_nonempty_bin_count"] == 1
    assert result["sample_status"] == "INSUFFICIENT_SAMPLE"
    assert result["classwise"]["AWAY"][0]["sample_status"] == "DESCRIPTIVE_ONLY"
    assert result["classwise"]["AWAY"][1]["sample_status"] == "INSUFFICIENT_SAMPLE"


def test_analyze_paired_calibration_below_scoring_threshold(sources, monkeypatch):
    """通过真实 fixture 报价链配对，校准不依赖 30 对评分门槛。"""
    monkeypatch.setattr(diagnostic, "MINIMUM_PAIRS", 30)
    for i, (p, q) in enumerate(zip([0.1, 0.15, 0.7], [0.8, 0.05, 0.1], strict=True)):
        sources["evaluation"]["prediction_rows"][i]["probabilities"] = {
            "P_AWAY": p,
            "P_DRAW": (1 - p) / 2,
            "P_HOME": (1 - p) / 2,
        }
        probabilities = {"away": q, "draw": (1 - q) / 2, "home": (1 - q) / 2}
        for obs in sources["gd01"]["rows"][i]["football_data"]["observations"]:
            odds = 1 / probabilities[obs["selection"]]
            obs["decimal_odds"] = odds
            column = f"{obs['bookmaker_source_id']}C{obs['selection'][0].upper()}"
            sources["csv_rows"]["saved"][i][column] = str(odds)
    result = diagnostic.analyze(sources)
    assert result["valid_paired_matches"] == result["accounted_matches"] == 3
    assert result["excluded_matches"] == 0
    assert result["exclusion_reasons"] == {}
    assert result["metrics"] is None
    assert result["uncertainty"] is None
    assert result["result_interpretation"] == "INSUFFICIENT_EVIDENCE"
    entry = result["paired_calibration"]["classwise"]["AWAY"][0]
    assert entry["count"] == 2
    assert [entry[key] for key in CALIBRATION_STATISTICS] == [0.125, 0.425, 0.5, 0.375, 0.075]
    assert result["claim_boundary"] == (
        "No fresh holdout, decision-time execution, tradable value, profitability, ROI or CLV proof"
    )
