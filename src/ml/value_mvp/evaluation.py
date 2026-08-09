"""Evaluation metrics for VALUE_MVP-1 (frozen formulas from the protocol).

Primary: multiclass log loss (eps-clipped). Secondary: multiclass Brier,
accuracy, calibration summary. All computed per match so paired model-vs-market
comparisons and bootstraps stay possible.
"""

from __future__ import annotations

from itertools import pairwise
import math

import numpy as np


def per_row_log_loss(
    probabilities: np.ndarray, labels: np.ndarray, eps: float = 1e-15
) -> np.ndarray:
    """Per-match multiclass log loss: -log(p_actual) with p clipped to [eps, 1]."""
    n = probabilities.shape[0]
    clipped = np.maximum(probabilities, eps)
    actual = clipped[np.arange(n), labels]
    return -np.log(actual)


def log_loss_score(probabilities: np.ndarray, labels: np.ndarray, eps: float = 1e-15) -> float:
    """Mean multiclass log loss over matches."""
    return float(np.mean(per_row_log_loss(probabilities, labels, eps)))


def per_row_brier(probabilities: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Per-match multiclass Brier: sum_k (p_k - y_k)^2."""
    one_hot = np.zeros_like(probabilities)
    one_hot[np.arange(probabilities.shape[0]), labels] = 1.0
    return np.sum((probabilities - one_hot) ** 2, axis=1)


def brier_score(probabilities: np.ndarray, labels: np.ndarray) -> float:
    """Mean multiclass Brier over matches."""
    return float(np.mean(per_row_brier(probabilities, labels)))


def accuracy(probabilities: np.ndarray, labels: np.ndarray) -> float:
    """Fraction of matches where argmax probability equals the outcome."""
    predictions = np.argmax(probabilities, axis=1)
    return float(np.mean(predictions == labels))


def calibration_summary(
    probabilities: np.ndarray, labels: np.ndarray, bins: list[float]
) -> list[dict]:
    """Fixed-bin calibration per class: predicted mean, observed frequency, count."""
    summary: list[dict] = []
    for class_index in range(probabilities.shape[1]):
        values = probabilities[:, class_index]
        actual = (labels == class_index).astype(float)
        entries = []
        for low, high in pairwise(bins):
            mask = (
                (values >= low) & (values < high)
                if high < 1.0
                else (values >= low) & (values <= high)
            )
            count = int(np.sum(mask))
            if count == 0:
                entries.append({"bin": [low, high], "count": 0})
                continue
            entries.append(
                {
                    "bin": [low, high],
                    "count": count,
                    "predicted_mean": round(float(np.mean(values[mask])), 6),
                    "observed_frequency": round(float(np.mean(actual[mask])), 6),
                }
            )
        summary.append({"class": class_index, "bins": entries})
    return summary


def class_frequency_probabilities(labels: np.ndarray) -> np.ndarray:
    """Training-fold class frequencies as a sanity baseline probability vector."""
    counts = np.bincount(labels, minlength=3)
    total = counts.sum()
    if total == 0:
        raise ValueError("cannot compute class frequencies from an empty label set")
    return counts.astype(float) / total


def validate_probability_matrix(probabilities: np.ndarray, name: str) -> None:
    """Assert finite probabilities in [0,1] with rows summing to ~1."""
    if not np.all(np.isfinite(probabilities)):
        raise ValueError(f"{name}: non-finite probabilities present")
    if probabilities.min() < 0.0 or probabilities.max() > 1.0:
        raise ValueError(f"{name}: probabilities outside [0,1]")
    row_sums = probabilities.sum(axis=1)
    if not np.allclose(row_sums, 1.0, atol=1e-6):
        raise ValueError(
            f"{name}: probability rows do not sum to 1 (max deviation {np.max(np.abs(row_sums - 1.0))})"
        )


def safe_round(value: float) -> float:
    """Round for deterministic byte-stable serialization."""
    if math.isnan(value):
        return None  # type: ignore[return-value]
    return round(value, 10)
