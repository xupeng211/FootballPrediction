#!/usr/bin/env python3
"""TITAN V1.0 quant baseline training scaffold.

This script intentionally uses only high-availability pre-match features by
default. Same-match tactical stats are available behind an explicit diagnostics
flag because they are post-match data for a result prediction target.
"""
# ruff: noqa: D101,D103

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

import joblib
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, classification_report, log_loss
from sklearn.model_selection import train_test_split
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models" / "baseline_v1"
RESULT_NAMES = ["AWAY", "DRAW", "HOME"]
CALIBRATED_MODEL_FILENAME = "baseline_v1_result_1x2.calibrated.joblib"

PREMATCH_JSON_FEATURES = {
    "elo_features": [
        "home_elo_pre",
        "away_elo_pre",
        "elo_diff",
        "elo_diff_adjusted",
        "expected_home_win",
        "expected_away_win",
        "k_factor_home",
        "k_factor_away",
    ],
    "odds_features": [
        "initial_home_odds",
        "initial_draw_odds",
        "initial_away_odds",
        "current_home_odds",
        "current_draw_odds",
        "current_away_odds",
        "implied_prob_home",
        "implied_prob_draw",
        "implied_prob_away",
        "home_odds_change",
        "draw_odds_change",
        "away_odds_change",
        "home_odds_change_pct",
        "draw_odds_change_pct",
        "away_odds_change_pct",
        "bookmaker_margin",
        "favorite_prob",
        "prob_entropy",
        "total_movement",
        "steam_strength",
        "odds_history_count",
    ],
}

BET365_ODDS_FEATURES = [
    "bet365_1x2_open_home",
    "bet365_1x2_open_draw",
    "bet365_1x2_open_away",
    "bet365_1x2_close_home",
    "bet365_1x2_close_draw",
    "bet365_1x2_close_away",
    "bet365_ah_open_line",
    "bet365_ah_close_line",
    "bet365_ah_open_home",
    "bet365_ah_open_away",
    "bet365_ah_close_home",
    "bet365_ah_close_away",
    "bet365_ou_open_line",
    "bet365_ou_close_line",
    "bet365_ou_open_over",
    "bet365_ou_open_under",
    "bet365_ou_close_over",
    "bet365_ou_close_under",
    "bet365_count_1x2",
    "bet365_count_ah",
    "bet365_count_ou",
]

POSTMATCH_DIAGNOSTIC_FEATURES = [
    "home_shots",
    "away_shots",
    "home_shots_on_target",
    "away_shots_on_target",
    "home_corners",
    "away_corners",
    "home_yellow_cards",
    "away_yellow_cards",
    "shots_on_target_diff",
    "corners_diff",
]


@dataclass
class BaselineTrainingResult:
    target: str
    model_path: str | None
    calibrated_model_path: str | None
    metadata_path: str | None
    samples: int
    features: int
    accuracy: float | None
    log_loss: float | None
    raw_accuracy: float | None
    raw_log_loss: float | None
    calibration_method: str
    calibration_cv: int
    class_distribution: dict[str, int]
    generated_at: str


def setup_logging(verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger("baseline_v1")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train TITAN V1.0 baseline model")
    parser.add_argument("--target", default="result_1x2", choices=["result_1x2"])
    parser.add_argument("--min-samples", type=int, default=500)
    parser.add_argument("--test-size", type=float, default=0.3)
    parser.add_argument("--estimators", type=int, default=250)
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--lr", type=float, default=0.05)
    parser.add_argument("--output-dir", default=str(DEFAULT_MODEL_DIR))
    parser.add_argument("--calibration-method", default="sigmoid", choices=["sigmoid", "isotonic", "none"])
    parser.add_argument("--calibration-cv", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-postmatch-diagnostics", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def get_db_connection():
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise RuntimeError("DB_PASSWORD is required")

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "football_db"),
        user=os.getenv("DB_USER", "football_user"),
        password=password,
    )


def load_training_rows(conn) -> list[dict[str, Any]]:
    query = """
        WITH bet365_odds AS (
            SELECT
                match_id,
                MAX(NULLIF(open_odds->>'home', '')::numeric)
                    FILTER (WHERE market_type = '1x2') AS bet365_1x2_open_home,
                MAX(NULLIF(open_odds->>'draw', '')::numeric)
                    FILTER (WHERE market_type = '1x2') AS bet365_1x2_open_draw,
                MAX(NULLIF(open_odds->>'away', '')::numeric)
                    FILTER (WHERE market_type = '1x2') AS bet365_1x2_open_away,
                MAX(NULLIF(close_odds->>'home', '')::numeric)
                    FILTER (WHERE market_type = '1x2') AS bet365_1x2_close_home,
                MAX(NULLIF(close_odds->>'draw', '')::numeric)
                    FILTER (WHERE market_type = '1x2') AS bet365_1x2_close_draw,
                MAX(NULLIF(close_odds->>'away', '')::numeric)
                    FILTER (WHERE market_type = '1x2') AS bet365_1x2_close_away,
                MAX(NULLIF(open_odds->>'line', '')::numeric)
                    FILTER (WHERE market_type = 'Asian Handicap') AS bet365_ah_open_line,
                MAX(NULLIF(close_odds->>'line', '')::numeric)
                    FILTER (WHERE market_type = 'Asian Handicap') AS bet365_ah_close_line,
                MAX(NULLIF(open_odds->>'home', '')::numeric)
                    FILTER (WHERE market_type = 'Asian Handicap') AS bet365_ah_open_home,
                MAX(NULLIF(open_odds->>'away', '')::numeric)
                    FILTER (WHERE market_type = 'Asian Handicap') AS bet365_ah_open_away,
                MAX(NULLIF(close_odds->>'home', '')::numeric)
                    FILTER (WHERE market_type = 'Asian Handicap') AS bet365_ah_close_home,
                MAX(NULLIF(close_odds->>'away', '')::numeric)
                    FILTER (WHERE market_type = 'Asian Handicap') AS bet365_ah_close_away,
                MAX(NULLIF(open_odds->>'line', '')::numeric)
                    FILTER (WHERE market_type = 'Over/Under') AS bet365_ou_open_line,
                MAX(NULLIF(close_odds->>'line', '')::numeric)
                    FILTER (WHERE market_type = 'Over/Under') AS bet365_ou_close_line,
                MAX(NULLIF(open_odds->>'over', '')::numeric)
                    FILTER (WHERE market_type = 'Over/Under') AS bet365_ou_open_over,
                MAX(NULLIF(open_odds->>'under', '')::numeric)
                    FILTER (WHERE market_type = 'Over/Under') AS bet365_ou_open_under,
                MAX(NULLIF(close_odds->>'over', '')::numeric)
                    FILTER (WHERE market_type = 'Over/Under') AS bet365_ou_close_over,
                MAX(NULLIF(close_odds->>'under', '')::numeric)
                    FILTER (WHERE market_type = 'Over/Under') AS bet365_ou_close_under,
                COUNT(*) FILTER (WHERE market_type = '1x2') AS bet365_count_1x2,
                COUNT(*) FILTER (WHERE market_type = 'Asian Handicap') AS bet365_count_ah,
                COUNT(*) FILTER (WHERE market_type = 'Over/Under') AS bet365_count_ou
            FROM bookmaker_odds_history
            WHERE lower(bookmaker_name) = 'bet365'
            GROUP BY match_id
        )
        SELECT
            m.match_id,
            m.league_name,
            m.season,
            m.match_date,
            m.home_score,
            m.away_score,
            l.elo_features,
            l.odds_features,
            l.tactical_features,
            b.*
        FROM matches m
        JOIN l3_features l ON l.match_id = m.match_id
        LEFT JOIN bet365_odds b ON b.match_id = m.match_id
        WHERE m.home_score IS NOT NULL
          AND m.away_score IS NOT NULL
        ORDER BY m.match_date ASC, m.match_id ASC
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query)
        return list(cursor.fetchall())


def parse_jsonb(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        number = float(value)
        return number if np.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def encode_result(home_score: int, away_score: int) -> int:
    if home_score > away_score:
        return 2
    if home_score == away_score:
        return 1
    return 0


def add_json_features(features: dict[str, float], payload: dict[str, Any], keys: list[str], prefix: str) -> None:
    for key in keys:
        features[f"{prefix}_{key}"] = safe_float(payload.get(key))


def build_feature_frame(
    rows: list[dict[str, Any]],
    include_postmatch_diagnostics: bool,
) -> tuple[pd.DataFrame, pd.Series]:
    records: list[dict[str, float | str]] = []
    labels: list[int] = []

    for row in rows:
        elo = parse_jsonb(row.get("elo_features"))
        odds = parse_jsonb(row.get("odds_features"))
        tactical = parse_jsonb(row.get("tactical_features"))
        match_date = row.get("match_date")
        features: dict[str, float | str] = {
            "league_name": str(row.get("league_name") or "unknown"),
            "season_start_year": safe_float(str(row.get("season") or "0").split("/")[0]),
            "match_month": float(getattr(match_date, "month", 0) or 0),
            "match_dayofweek": float(getattr(match_date, "weekday", lambda: 0)()),
        }

        add_json_features(features, elo, PREMATCH_JSON_FEATURES["elo_features"], "elo")
        add_json_features(features, odds, PREMATCH_JSON_FEATURES["odds_features"], "odds")

        for key in BET365_ODDS_FEATURES:
            features[key] = safe_float(row.get(key))

        features["bet365_ah_line_move"] = features["bet365_ah_close_line"] - features["bet365_ah_open_line"]
        features["bet365_ou_line_move"] = features["bet365_ou_close_line"] - features["bet365_ou_open_line"]

        if include_postmatch_diagnostics:
            add_json_features(features, tactical, POSTMATCH_DIAGNOSTIC_FEATURES, "postmatch")

        records.append(features)
        labels.append(encode_result(int(row["home_score"]), int(row["away_score"])))

    frame = pd.DataFrame(records)
    frame = pd.get_dummies(frame, columns=["league_name"], prefix="league", dtype=float)
    frame = frame.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return frame, pd.Series(labels, name="result_1x2")


def train_model(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_valid: pd.DataFrame,
    y_valid: pd.Series,
    args: argparse.Namespace,
) -> xgb.XGBClassifier:
    model = build_xgb_classifier(args)
    model.fit(x_train, y_train, eval_set=[(x_valid, y_valid)], verbose=False)
    return model


def build_xgb_classifier(args: argparse.Namespace) -> xgb.XGBClassifier:
    return xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        n_estimators=args.estimators,
        max_depth=args.depth,
        learning_rate=args.lr,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=2,
    )


def calibrate_model(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    args: argparse.Namespace,
    logger: logging.Logger,
) -> Any:
    if args.calibration_method == "none":
        logger.info("Probability calibration disabled; using raw XGBoost probabilities.")
        model = build_xgb_classifier(args)
        model.fit(x_train, y_train, verbose=False)
        return model

    logger.info(
        "Fitting probability calibrator method=%s cv=%s",
        args.calibration_method,
        args.calibration_cv,
    )
    calibrator = CalibratedClassifierCV(
        estimator=build_xgb_classifier(args),
        method=args.calibration_method,
        cv=args.calibration_cv,
        n_jobs=1,
    )
    calibrator.fit(x_train, y_train)
    return calibrator


def evaluate_model(model: Any, x_valid: pd.DataFrame, y_valid: pd.Series, logger: logging.Logger, label: str) -> tuple[float, float]:
    probabilities = model.predict_proba(x_valid)
    predictions = probabilities.argmax(axis=1)
    accuracy = accuracy_score(y_valid, predictions)
    loss = log_loss(y_valid, probabilities, labels=[0, 1, 2])
    logger.info("%s validation accuracy=%.4f log_loss=%.4f", label, accuracy, loss)
    logger.info(
        "%s classification report:\n%s",
        label,
        classification_report(y_valid, predictions, target_names=RESULT_NAMES, zero_division=0),
    )
    return float(accuracy), float(loss)


def persist_outputs(
    raw_model: xgb.XGBClassifier,
    calibrated_model: Any,
    feature_columns: list[str],
    result: BaselineTrainingResult,
    output_dir: Path,
) -> BaselineTrainingResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "baseline_v1_result_1x2.json"
    calibrated_model_path = output_dir / CALIBRATED_MODEL_FILENAME
    metadata_path = output_dir / "baseline_v1_result_1x2.metadata.json"
    raw_model.get_booster().save_model(str(model_path))
    joblib.dump(calibrated_model, calibrated_model_path)

    result.model_path = str(model_path)
    result.calibrated_model_path = str(calibrated_model_path)
    result.metadata_path = str(metadata_path)
    metadata = asdict(result)
    metadata["feature_columns"] = feature_columns
    metadata["class_names"] = RESULT_NAMES
    metadata["active_model_path"] = str(calibrated_model_path)
    metadata["active_model_format"] = "sklearn_calibrated_joblib"
    metadata["raw_model_path"] = str(model_path)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    return result


def main() -> int:
    args = parse_args()
    logger = setup_logging(args.verbose)
    generated_at = datetime.now(UTC).isoformat()

    with get_db_connection() as conn:
        rows = load_training_rows(conn)

    if len(rows) < args.min_samples:
        raise RuntimeError(f"训练样本不足: need>={args.min_samples}, actual={len(rows)}")

    x_frame, y = build_feature_frame(rows, args.include_postmatch_diagnostics)
    class_distribution = {RESULT_NAMES[index]: int((y == index).sum()) for index in range(3)}
    logger.info("Loaded dataset samples=%s features=%s classes=%s", len(x_frame), x_frame.shape[1], class_distribution)

    x_train, x_valid, y_train, y_valid = train_test_split(
        x_frame,
        y,
        test_size=args.test_size,
        random_state=42,
        stratify=y,
    )

    result = BaselineTrainingResult(
        target=args.target,
        model_path=None,
        calibrated_model_path=None,
        metadata_path=None,
        samples=len(x_frame),
        features=x_frame.shape[1],
        accuracy=None,
        log_loss=None,
        raw_accuracy=None,
        raw_log_loss=None,
        calibration_method=args.calibration_method,
        calibration_cv=args.calibration_cv,
        class_distribution=class_distribution,
        generated_at=generated_at,
    )

    if args.dry_run:
        logger.info("Dry run only. Dataset is ready; model training skipped.")
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0

    raw_model = train_model(x_train, y_train, x_valid, y_valid, args)
    raw_accuracy, raw_loss = evaluate_model(raw_model, x_valid, y_valid, logger, "Raw XGBoost")
    calibrated_model = calibrate_model(x_train, y_train, args, logger)
    accuracy, loss = evaluate_model(calibrated_model, x_valid, y_valid, logger, "Calibrated")
    result.raw_accuracy = raw_accuracy
    result.raw_log_loss = raw_loss
    result.accuracy = accuracy
    result.log_loss = loss
    result = persist_outputs(raw_model, calibrated_model, list(x_frame.columns), result, Path(args.output_dir))
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
