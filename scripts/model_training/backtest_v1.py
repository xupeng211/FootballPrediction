#!/usr/bin/env python3
"""Evaluate TITAN V1.0 validation probabilities against close market multipliers."""
# ruff: noqa: D103

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.model_training.train_baseline_v1 import (  # noqa: E402
    DEFAULT_MODEL_DIR,
    RESULT_NAMES,
    build_feature_frame,
    get_db_connection,
    load_training_rows,
    safe_float,
)

CLASS_MARKETS = {
    0: ("AWAY", "bet365_1x2_close_away"),
    1: ("DRAW", "bet365_1x2_close_draw"),
    2: ("HOME", "bet365_1x2_close_home"),
}
LOW_MULTIPLIER_CUTOFF = 2.0
HIGH_MULTIPLIER_CUTOFF = 4.0
MAX_TRIGGER_MULTIPLIER = 2.0
PROBABILITY_MATRIX_DIMENSIONS = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest TITAN V1.0 validation probabilities with market multipliers",
    )
    parser.add_argument(
        "--model-path",
        default=str(DEFAULT_MODEL_DIR / "baseline_v1_result_1x2.json"),
    )
    parser.add_argument(
        "--metadata-path",
        default=str(DEFAULT_MODEL_DIR / "baseline_v1_result_1x2.metadata.json"),
    )
    parser.add_argument("--calibrated-model-path", default=None)
    parser.add_argument("--test-size", type=float, default=0.3)
    parser.add_argument("--ev-threshold", type=float, default=0.08)
    parser.add_argument("--max-multiplier", type=float, default=MAX_TRIGGER_MULTIPLIER)
    parser.add_argument("--min-samples", type=int, default=500)
    parser.add_argument("--output-json", default=None)
    return parser.parse_args()


def load_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"找不到模型 metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_artifact_path(path_text: str | None) -> Path | None:
    if not path_text:
        return None
    path = Path(path_text)
    if path.exists():
        return path
    if path.is_absolute() and path.parts[:2] == ("/", "app"):
        local_path = PROJECT_ROOT / Path(*path.parts[2:])
        if local_path.exists():
            return local_path
    return path


def load_booster(path: Path) -> xgb.Booster:
    if not path.exists():
        raise FileNotFoundError(f"找不到模型文件: {path}")
    booster = xgb.Booster()
    booster.load_model(str(path))
    return booster


def predict_probabilities(
    x_valid: Any,
    model_path: Path,
    metadata: dict[str, Any],
    calibrated_model_path: str | None,
) -> tuple[np.ndarray, Path, str]:
    resolved_calibrated_path = resolve_artifact_path(
        calibrated_model_path or metadata.get("active_model_path") or metadata.get("calibrated_model_path"),
    )
    if resolved_calibrated_path and resolved_calibrated_path.exists():
        model = joblib.load(resolved_calibrated_path)
        return model.predict_proba(x_valid), resolved_calibrated_path, "sklearn_calibrated_joblib"

    booster = load_booster(model_path)
    return booster.predict(xgb.DMatrix(x_valid)), model_path, "xgboost_booster_json"


def validation_split(
    rows: list[dict[str, Any]],
    test_size: float,
) -> tuple[Any, Any, list[dict[str, Any]]]:
    x_frame, y = build_feature_frame(rows, include_postmatch_diagnostics=False)
    row_indices = np.arange(len(rows))
    _, x_valid, _, y_valid, _, valid_indices = train_test_split(
        x_frame,
        y,
        row_indices,
        test_size=test_size,
        random_state=42,
        stratify=y,
    )
    valid_rows = [rows[int(index)] for index in valid_indices]
    return x_valid.reset_index(drop=True), y_valid.reset_index(drop=True), valid_rows


def align_features(x_valid: Any, metadata: dict[str, Any]) -> Any:
    feature_columns = metadata.get("feature_columns")
    if not feature_columns:
        raise RuntimeError("metadata 缺少 feature_columns，无法保证回测特征顺序")
    return x_valid.reindex(columns=feature_columns, fill_value=0.0)


def valid_multiplier(value: Any) -> float | None:
    multiplier = safe_float(value, default=float("nan"))
    if not np.isfinite(multiplier) or multiplier <= 1.0:
        return None
    return multiplier


def multiplier_bucket(multiplier: float) -> str:
    if multiplier < LOW_MULTIPLIER_CUTOFF:
        return "low_<2.0"
    if multiplier < HIGH_MULTIPLIER_CUTOFF:
        return "mid_2.0_4.0"
    return "high_>=4.0"


def summarize_group(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {
            "triggers": 0,
            "hits": 0,
            "hit_rate": None,
            "net_yield": 0.0,
            "roi": None,
            "avg_multiplier": None,
            "avg_ev": None,
        }

    hits = sum(1 for item in items if item["hit"])
    net_yield = sum(float(item["yield"]) for item in items)
    return {
        "triggers": len(items),
        "hits": hits,
        "hit_rate": hits / len(items),
        "net_yield": net_yield,
        "roi": net_yield / len(items),
        "avg_multiplier": float(np.mean([item["multiplier"] for item in items])),
        "avg_ev": float(np.mean([item["ev"] for item in items])),
    }


def calculate_market_friction(rows: list[dict[str, Any]]) -> float | None:
    frictions: list[float] = []
    for row in rows:
        home = valid_multiplier(row.get("bet365_1x2_close_home"))
        draw = valid_multiplier(row.get("bet365_1x2_close_draw"))
        away = valid_multiplier(row.get("bet365_1x2_close_away"))
        if home and draw and away:
            frictions.append((1.0 / home) + (1.0 / draw) + (1.0 / away) - 1.0)
    if not frictions:
        return None
    return float(np.mean(frictions))


def evaluate(
    probabilities: np.ndarray,
    y_valid: Any,
    valid_rows: list[dict[str, Any]],
    ev_threshold: float,
    max_multiplier: float,
) -> dict[str, Any]:
    selections: list[dict[str, Any]] = []
    pass_count = 0
    invalid_multiplier_count = 0
    multiplier_filtered_count = 0

    for sample_index, probability_row in enumerate(probabilities):
        candidates: list[dict[str, Any]] = []
        has_valid_multiplier = False
        for class_index, probability in enumerate(probability_row):
            class_name, multiplier_field = CLASS_MARKETS[class_index]
            multiplier = valid_multiplier(valid_rows[sample_index].get(multiplier_field))
            if multiplier is None:
                continue
            has_valid_multiplier = True
            if multiplier >= max_multiplier:
                multiplier_filtered_count += 1
                continue
            ev = (float(probability) * multiplier) - 1.0
            candidates.append(
                {
                    "class_index": class_index,
                    "class_name": class_name,
                    "probability": float(probability),
                    "multiplier": multiplier,
                    "ev": ev,
                    "bucket": multiplier_bucket(multiplier),
                },
            )

        if not candidates:
            if not has_valid_multiplier:
                invalid_multiplier_count += 1
            pass_count += 1
            continue

        best = max(candidates, key=lambda candidate: candidate["ev"])
        if best["ev"] <= ev_threshold:
            pass_count += 1
            continue

        actual = int(y_valid.iloc[sample_index])
        hit = best["class_index"] == actual
        net_yield = best["multiplier"] - 1.0 if hit else -1.0
        selections.append(
            {
                **best,
                "match_id": valid_rows[sample_index].get("match_id"),
                "actual_class": RESULT_NAMES[actual],
                "hit": hit,
                "yield": net_yield,
            },
        )

    trigger_count = len(selections)
    hit_count = sum(1 for item in selections if item["hit"])
    net_yield = sum(float(item["yield"]) for item in selections)
    multipliers = [float(item["multiplier"]) for item in selections]
    evs = [float(item["ev"]) for item in selections]

    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for selection in selections:
        by_bucket[str(selection["bucket"])].append(selection)
        by_class[str(selection["class_name"])].append(selection)

    return {
        "validation_samples": len(valid_rows),
        "ev_threshold": ev_threshold,
        "max_multiplier": max_multiplier,
        "trigger_count": trigger_count,
        "pass_count": pass_count,
        "invalid_multiplier_count": invalid_multiplier_count,
        "multiplier_filtered_count": multiplier_filtered_count,
        "hit_count": hit_count,
        "hit_rate": hit_count / trigger_count if trigger_count else None,
        "net_yield": net_yield,
        "roi": net_yield / trigger_count if trigger_count else None,
        "avg_selected_multiplier": float(np.mean(multipliers)) if multipliers else None,
        "median_selected_multiplier": float(np.median(multipliers)) if multipliers else None,
        "avg_selected_ev": float(np.mean(evs)) if evs else None,
        "market_friction_avg": calculate_market_friction(valid_rows),
        "trigger_distribution_by_bucket": {
            bucket: summarize_group(items)
            for bucket, items in sorted(by_bucket.items())
        },
        "trigger_distribution_by_class": {
            class_name: summarize_group(items)
            for class_name, items in sorted(by_class.items())
        },
        "selected_class_counts": dict(Counter(item["class_name"] for item in selections)),
    }


def format_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def format_float(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.4f}"


def print_report(result: dict[str, Any], model_path: Path) -> None:
    print("\nTITAN V1.1 Bet365 验证集市场乘数评估")
    print(f"模型文件: {model_path}")
    print(f"模型格式: {result['model_format']}")
    print(f"验证集总样本数: {result['validation_samples']}")
    print(f"正期望触发阈值: EV > {result['ev_threshold']:.2f}")
    print(f"最大允许触发乘数: < {result['max_multiplier']:.2f}")
    print(f"实际触发次数: {result['trigger_count']}")
    print(f"放弃次数: {result['pass_count']}")
    print(f"高乘数候选过滤次数: {result['multiplier_filtered_count']}")
    print(f"命中次数: {result['hit_count']}")
    print(f"命中率: {format_percent(result['hit_rate'])}")
    print(f"总净产出: {format_float(result['net_yield'])}")
    print(f"ROI: {format_percent(result['roi'])}")
    print(f"平均触发乘数: {format_float(result['avg_selected_multiplier'])}")
    print(f"触发乘数中位数: {format_float(result['median_selected_multiplier'])}")
    print(f"平均触发 EV: {format_percent(result['avg_selected_ev'])}")
    print(f"验证集平均市场摩擦: {format_percent(result['market_friction_avg'])}")

    print("\n按乘数区间:")
    for bucket, metrics in result["trigger_distribution_by_bucket"].items():
        print(
            f"- {bucket}: 触发 {metrics['triggers']} | "
            f"命中率 {format_percent(metrics['hit_rate'])} | "
            f"ROI {format_percent(metrics['roi'])} | "
            f"平均乘数 {format_float(metrics['avg_multiplier'])}",
        )

    print("\n按类别:")
    for class_name, metrics in result["trigger_distribution_by_class"].items():
        print(
            f"- {class_name}: 触发 {metrics['triggers']} | "
            f"命中率 {format_percent(metrics['hit_rate'])} | "
            f"ROI {format_percent(metrics['roi'])} | "
            f"平均乘数 {format_float(metrics['avg_multiplier'])}",
        )


def main() -> int:
    args = parse_args()
    model_path = Path(args.model_path)
    metadata_path = Path(args.metadata_path)
    metadata = load_metadata(metadata_path)

    with get_db_connection() as conn:
        rows = load_training_rows(conn)

    if len(rows) < args.min_samples:
        raise RuntimeError(f"样本不足: need>={args.min_samples}, actual={len(rows)}")

    x_valid, y_valid, valid_rows = validation_split(rows, test_size=args.test_size)
    x_valid = align_features(x_valid, metadata)

    probabilities, used_model_path, model_format = predict_probabilities(
        x_valid=x_valid,
        model_path=model_path,
        metadata=metadata,
        calibrated_model_path=args.calibrated_model_path,
    )
    if probabilities.ndim != PROBABILITY_MATRIX_DIMENSIONS or probabilities.shape[1] != len(RESULT_NAMES):
        raise RuntimeError(f"模型概率输出形状异常: {probabilities.shape}")

    result = evaluate(
        probabilities=probabilities,
        y_valid=y_valid,
        valid_rows=valid_rows,
        ev_threshold=args.ev_threshold,
        max_multiplier=args.max_multiplier,
    )
    result["model_path"] = str(used_model_path)
    result["model_format"] = model_format
    result["fallback_model_path"] = str(model_path)
    result["metadata_path"] = str(metadata_path)
    result["class_names"] = RESULT_NAMES

    print_report(result, used_model_path)
    print("\nJSON_RESULT:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
