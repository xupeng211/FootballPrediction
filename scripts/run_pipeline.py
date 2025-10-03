import os
#!/usr/bin/env python3
"""Run a synthetic end-to-end pipeline for CI smoke validation.

This script emulates the data collection → cleaning → feature engineering →
model training → batch prediction flow using deterministic synthetic data so
that CI/CD executions can validate the orchestration without hitting external
APIs or infrastructure.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

logger = logging.getLogger("pipeline.runner")


@dataclass
class MatchRecord:
    match_id: int
    home_team_strength: float
    away_team_strength: float
    home_form: float
    away_form: float
    weather_factor: float
    label: int  # 1 = home win, 0 = draw, -1 = away win

    def to_raw(self) -> Dict[str, float]:
        return {
            "match_id": self.match_id,
            "home_team_strength": self.home_team_strength,
            "away_team_strength": self.away_team_strength,
            "home_form": self.home_form,
            "away_form": self.away_form,
            "weather_factor": self.weather_factor,
            "label": self.label,
        }


def collect_synthetic_matches(
    seed: int = 42, samples: int = 64
) -> List[Dict[str, float]]:
    random.seed(seed)
    matches: List[MatchRecord] = []
    for idx in range(samples):
        home_strength = random.uniform(0.4, 1.0)
        away_strength = random.uniform(0.3, 0.9)
        home_form = random.uniform(0.0, 1.0)
        away_form = random.uniform(0.0, 1.0)
        weather = random.uniform(0.8, 1.1)

        strength_gap = home_strength - away_strength + 0.15 * (home_form - away_form)
        if strength_gap > 0.1:
            label = 1
        elif strength_gap < -0.1:
            label = -1
        else:
            label = 0

        matches.append(
            MatchRecord(
                match_id=10_000 + idx,
                home_team_strength=round(home_strength, 3),
                away_team_strength=round(away_strength, 3),
                home_form=round(home_form, 3),
                away_form=round(away_form, 3),
                weather_factor=round(weather, 3),
                label=label,
            )
        )

    logger.info("Collected %s synthetic raw matches", len(matches))
    return [record.to_raw() for record in matches]


def clean_matches(raw_matches: List[Dict[str, float]]) -> pd.DataFrame:
    df = pd.DataFrame(raw_matches)
    df = df.drop_duplicates(subset = os.getenv("RUN_PIPELINE_SUBSET_88")).reset_index(drop=True)
    df = df[
        (
            df[
                [
                    "home_team_strength",
                    "away_team_strength",
                    "home_form",
                    "away_form",
                    "weather_factor",
                ]
            ]
            > 0
        ).all(axis=1)
    ]
    logger.info("Cleaned dataset size: %s", len(df))
    return df


def engineer_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
    engineered = df.copy()
    engineered["strength_delta"] = (
        engineered["home_team_strength"] - engineered["away_team_strength"]
    )
    engineered["form_delta"] = engineered["home_form"] - engineered["away_form"]
    engineered["composite_score"] = (
        0.6 * engineered["strength_delta"]
        + 0.3 * engineered["form_delta"]
        + 0.1 * engineered["weather_factor"]
    )

    label_mapping = {1: 2, 0: 1, -1: 0}
    targets = engineered["label"].map(label_mapping).to_numpy()
    features = engineered[
        [
            "home_team_strength",
            "away_team_strength",
            "home_form",
            "away_form",
            "weather_factor",
            "strength_delta",
            "form_delta",
            "composite_score",
        ]
    ]
    return features, targets


def train_model(features: pd.DataFrame, targets: np.ndarray) -> LogisticRegression:
    model = LogisticRegression(max_iter=200, multi_class = os.getenv("RUN_PIPELINE_MULTI_CLASS_137"))
    model.fit(features.values, targets)
    logger.info("Trained logistic regression model on %s samples", len(features))
    return model


def evaluate_model(
    model: LogisticRegression, features: pd.DataFrame, targets: np.ndarray
) -> Dict[str, float]:
    predictions = model.predict(features.values)
    accuracy = accuracy_score(targets, predictions)
    report = classification_report(targets, predictions, output_dict=True)
    logger.info("Model accuracy on synthetic data: %.3f", accuracy)
    return {
        "accuracy": round(float(accuracy), 4),
        "macro_f1": round(float(report["macro avg"]["f1-score"]), 4),
    }


def run_predictions(
    model: LogisticRegression, features: pd.DataFrame
) -> List[Dict[str, float]]:
    proba = model.predict_proba(features.values)
    results = []
    for idx, probs in enumerate(proba):
        results.append(
            {
                "match_id": int(features.index[idx]),
                "home_win_probability": round(float(probs[2]), 4),
                "draw_probability": round(float(probs[1]), 4),
                "away_win_probability": round(float(probs[0]), 4),
            }
        )
    logger.info("Generated %s prediction rows", len(results))
    return results


def write_report(
    metrics: Dict[str, float], predictions: List[Dict[str, float]], output_dir: Path
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pipeline_metrics.json").write_text(json.dumps(metrics, indent=2))
    (output_dir / "predictions_sample.json").write_text(
        json.dumps(predictions[:5], indent=2)
    )
    logger.info("Wrote pipeline artefacts to %s", output_dir)


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format = os.getenv("RUN_PIPELINE_FORMAT_186"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description = os.getenv("RUN_PIPELINE_DESCRIPTION_190"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/pipeline"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--verbose", action = os.getenv("RUN_PIPELINE_ACTION_194"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)

    raw_matches = collect_synthetic_matches(seed=args.seed, samples=args.samples)
    cleaned_matches = clean_matches(raw_matches)
    feature_frame, targets = engineer_features(cleaned_matches)

    model = train_model(feature_frame, targets)
    metrics = evaluate_model(model, feature_frame, targets)
    predictions = run_predictions(model, feature_frame)

    write_report(metrics, predictions, args.output)


if __name__ == "__main__":
    main()
