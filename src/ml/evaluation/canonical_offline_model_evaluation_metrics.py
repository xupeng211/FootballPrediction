"""Frozen probability metrics, baselines, calibration, and uncertainty."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Mapping

from .canonical_offline_model_evaluation_contract import (
    BOOTSTRAP_CONFIDENCE_LEVEL,
    CLASS_NAMES,
    CLASS_ORDER,
    CLEARLY_MISALIGNED_CALIBRATION_GAP,
    LOG_LOSS_EPSILON,
    PROBABILITY_COLUMN_ORDER,
    PROBABILITY_MATRIX_DIMENSIONS,
    PROBABILITY_SUM_ATOL,
    TRAINING_CLASS_COUNTS,
    TRAINING_CLASS_DISTRIBUTION,
    TRAINING_ROWS,
    EvaluationContractError,
    VerifiedCandidate,
)


def validate_probability_matrix(
    probabilities: np.ndarray[Any, Any], *, expected_rows: int | None = None
) -> None:
    """Fail closed on finite, range-valid, row-normalized multiclass output."""
    if probabilities.ndim != PROBABILITY_MATRIX_DIMENSIONS or probabilities.shape[1] != len(
        CLASS_ORDER
    ):
        raise EvaluationContractError("probability matrix shape is invalid")
    if expected_rows is not None and probabilities.shape[0] != expected_rows:
        raise EvaluationContractError("probability row count is invalid")
    if not np.isfinite(probabilities).all():
        raise EvaluationContractError("probability matrix contains non-finite values")
    if float(probabilities.min()) < 0.0 or float(probabilities.max()) > 1.0:
        raise EvaluationContractError("probability matrix is outside [0,1]")
    if not np.allclose(probabilities.sum(axis=1), 1.0, atol=PROBABILITY_SUM_ATOL, rtol=0.0):
        raise EvaluationContractError("probability rows do not sum to one")


def _validate_labels(labels: np.ndarray[Any, Any], expected_rows: int) -> None:
    if labels.ndim != 1 or len(labels) != expected_rows or not np.isin(labels, CLASS_ORDER).all():
        raise EvaluationContractError("opened outcome labels are invalid")


def _per_row_log_loss(
    probabilities: np.ndarray[Any, Any], labels: np.ndarray[Any, Any]
) -> np.ndarray[Any, Any]:
    clipped = np.clip(probabilities, LOG_LOSS_EPSILON, 1.0)
    return np.asarray(-np.log(clipped[np.arange(len(labels)), labels]), dtype=float)


def _per_row_brier(
    probabilities: np.ndarray[Any, Any], labels: np.ndarray[Any, Any]
) -> np.ndarray[Any, Any]:
    one_hot = np.eye(len(CLASS_ORDER), dtype=float)[labels]
    return np.asarray(np.sum((probabilities - one_hot) ** 2, axis=1), dtype=float)


def metric_bundle(
    probabilities: np.ndarray[Any, Any], labels: np.ndarray[Any, Any]
) -> dict[str, float]:
    """Compute the frozen primary and secondary metrics."""
    validate_probability_matrix(probabilities, expected_rows=len(labels))
    _validate_labels(labels, len(probabilities))
    predictions = np.argmax(probabilities, axis=1)
    return {
        "multiclass_log_loss": float(np.mean(_per_row_log_loss(probabilities, labels))),
        "multiclass_brier_score": float(np.mean(_per_row_brier(probabilities, labels))),
        "accuracy": float(np.mean(predictions == labels)),
    }


def _class_distribution(values: np.ndarray[Any, Any]) -> dict[str, int]:
    return {name: int(np.sum(values == index)) for index, name in enumerate(CLASS_NAMES)}


def _confusion_matrix(
    labels: np.ndarray[Any, Any], predictions: np.ndarray[Any, Any]
) -> list[list[int]]:
    matrix = np.zeros((len(CLASS_ORDER), len(CLASS_ORDER)), dtype=int)
    for actual, predicted in zip(labels, predictions, strict=True):
        matrix[int(actual), int(predicted)] += 1
    return matrix.tolist()


def _round_number(value: float | None) -> float | None:
    return None if value is None else round(float(value), 12)


def _per_class_metrics(
    labels: np.ndarray[Any, Any], predictions: np.ndarray[Any, Any]
) -> dict[str, dict[str, Any]]:
    matrix = np.asarray(_confusion_matrix(labels, predictions), dtype=int)
    result: dict[str, dict[str, Any]] = {}
    for class_index, name in enumerate(CLASS_NAMES):
        true_positive = int(matrix[class_index, class_index])
        support = int(matrix[class_index, :].sum())
        predicted_count = int(matrix[:, class_index].sum())
        recall = true_positive / support if support else None
        precision = true_positive / predicted_count if predicted_count else None
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else None
        )
        result[name] = {
            "support": support,
            "predicted_count": predicted_count,
            "recall": _round_number(recall),
            "precision": _round_number(precision),
            "f1": _round_number(f1),
        }
    return result


def _calibration_summary(
    probabilities: np.ndarray[Any, Any], labels: np.ndarray[Any, Any], protocol: Mapping[str, Any]
) -> dict[str, Any]:
    edges = tuple(float(value) for value in protocol["calibration"]["bin_edges"])
    minimum_count = int(protocol["calibration"]["minimum_nonempty_bin_count"])
    classwise: dict[str, list[dict[str, Any]]] = {}
    nonempty_counts: list[int] = []
    pooled_abs_gap_numerator = 0.0
    pooled_count = 0
    for class_index, class_name in enumerate(CLASS_NAMES):
        values = probabilities[:, class_index]
        actual = (labels == class_index).astype(float)
        bins: list[dict[str, Any]] = []
        for index in range(len(edges) - 1):
            low, high = edges[index], edges[index + 1]
            mask = (values >= low) & ((values <= high) if high == 1.0 else (values < high))
            count = int(np.sum(mask))
            entry: dict[str, Any] = {"bin": [low, high], "count": count}
            if count:
                predicted_mean = float(np.mean(values[mask]))
                observed_frequency = float(np.mean(actual[mask]))
                absolute_gap = abs(predicted_mean - observed_frequency)
                entry.update(
                    {
                        "predicted_mean": _round_number(predicted_mean),
                        "observed_frequency": _round_number(observed_frequency),
                        "absolute_gap": _round_number(absolute_gap),
                    }
                )
                nonempty_counts.append(count)
                pooled_abs_gap_numerator += absolute_gap * count
                pooled_count += count
            bins.append(entry)
        classwise[class_name] = bins
    minimum_nonempty = min(nonempty_counts) if nonempty_counts else 0
    status = "INSUFFICIENT_SAMPLE" if minimum_nonempty < minimum_count else "DESCRIPTIVE_ONLY"
    return {
        "method": "fixed_probability_bins",
        "bin_edges": list(edges),
        "minimum_nonempty_bin_count": minimum_count,
        "sample_status": status,
        "minimum_observed_nonempty_bin_count": minimum_nonempty,
        "overall": {
            "pooled_probability_class_cells": pooled_count,
            "weighted_mean_absolute_gap": _round_number(
                pooled_abs_gap_numerator / pooled_count if pooled_count else None
            ),
        },
        "classwise": classwise,
    }


def _bootstrap_intervals(
    candidate_probabilities: np.ndarray[Any, Any],
    prior_probabilities: np.ndarray[Any, Any],
    labels: np.ndarray[Any, Any],
    majority_class: int,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    resamples = int(protocol["uncertainty"]["resamples"])
    seed = int(protocol["uncertainty"]["seed"])
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(labels), size=(resamples, len(labels)))
    candidate_ll = _per_row_log_loss(candidate_probabilities, labels)
    prior_ll = _per_row_log_loss(prior_probabilities, labels)
    candidate_brier = _per_row_brier(candidate_probabilities, labels)
    prior_brier = _per_row_brier(prior_probabilities, labels)
    candidate_predictions = np.argmax(candidate_probabilities, axis=1)
    candidate_delta_ll = np.mean((candidate_ll - prior_ll)[indices], axis=1)
    candidate_delta_brier = np.mean((candidate_brier - prior_brier)[indices], axis=1)
    accuracy_delta = np.mean((candidate_predictions[indices] == labels[indices]), axis=1) - np.mean(
        labels[indices] == majority_class, axis=1
    )

    def interval(values: np.ndarray[Any, Any]) -> dict[str, Any]:
        lower, upper = np.percentile(values, [2.5, 97.5], method="linear")
        return {
            "lower": _round_number(float(lower)),
            "upper": _round_number(float(upper)),
            "confidence_level": BOOTSTRAP_CONFIDENCE_LEVEL,
            "method": "percentile",
            "resamples": resamples,
            "seed": seed,
        }

    return {
        "log_loss_delta": interval(candidate_delta_ll),
        "brier_delta": interval(candidate_delta_brier),
        "accuracy_delta": interval(accuracy_delta),
    }


def _class_prior_from_metadata(metadata: Mapping[str, Any]) -> np.ndarray[Any, Any]:
    distribution = metadata.get("provenance", {}).get("train_class_distribution")
    if distribution != TRAINING_CLASS_DISTRIBUTION:
        raise EvaluationContractError("training class prior provenance is invalid")
    counts = np.asarray(TRAINING_CLASS_COUNTS, dtype=float)
    if counts.sum() != TRAINING_ROWS:
        raise EvaluationContractError("training class prior count is invalid")
    return np.asarray(counts / counts.sum(), dtype=float)


def build_baselines(
    candidate: VerifiedCandidate,
    labels: np.ndarray[Any, Any],
) -> tuple[dict[str, Any], np.ndarray[Any, Any], np.ndarray[Any, Any], int]:
    """Build constant baselines solely from the candidate's training metadata."""
    prior = _class_prior_from_metadata(candidate.metadata)
    prior_probabilities = np.tile(prior, (len(labels), 1))
    majority_class = int(np.argmax(prior))
    majority_matrix = np.tile(
        np.eye(len(CLASS_ORDER), dtype=float)[majority_class], (len(labels), 1)
    )
    return (
        {
            "training_class_prior": {
                "definition": "constant HOME/DRAW/AWAY probability vector from training rows only",
                "source": "candidate_metadata.provenance.train_class_distribution",
                "counts": dict(zip(CLASS_NAMES, TRAINING_CLASS_COUNTS, strict=True)),
                "probabilities": {
                    column: _round_number(float(value))
                    for column, value in zip(PROBABILITY_COLUMN_ORDER, prior, strict=True)
                },
            },
            "training_majority_class": {
                "definition": "constant argmax class from training rows only",
                "source": "candidate_metadata.provenance.train_class_distribution",
                "class_index": majority_class,
                "class_name": CLASS_NAMES[majority_class],
            },
        },
        prior_probabilities,
        majority_matrix,
        majority_class,
    )


def _quality_status(
    deltas: Mapping[str, float],
    intervals: Mapping[str, Mapping[str, Any]],
    calibration: Mapping[str, Any],
) -> str:
    log_loss_delta = float(deltas["log_loss_delta_vs_prior"])
    brier_delta = float(deltas["brier_delta_vs_prior"])
    accuracy_delta = float(deltas["accuracy_delta_vs_majority"])
    log_interval = intervals["log_loss_delta"]
    brier_interval = intervals["brier_delta"]
    clearly_adverse = float(log_interval["lower"]) > 0 and float(brier_interval["lower"]) > 0
    clearly_improved = float(log_interval["upper"]) < 0 and float(brier_interval["upper"]) < 0
    clearly_misaligned = (
        calibration.get("sample_status") == "DESCRIPTIVE_ONLY"
        and float(calibration["overall"]["weighted_mean_absolute_gap"] or 0.0)
        > CLEARLY_MISALIGNED_CALIBRATION_GAP
    )
    if (
        log_loss_delta < 0
        and brier_delta < 0
        and accuracy_delta >= 0
        and clearly_improved
        and not clearly_misaligned
    ):
        return "PROMISING"
    if log_loss_delta < 0 and brier_delta < 0 and not clearly_adverse:
        return "MIXED"
    if log_loss_delta > 0 and brier_delta > 0:
        return "CLEARLY_UNDERPERFORMING" if clearly_adverse else "WEAK"
    return "MIXED"


__all__ = [
    "_calibration_summary",
    "_class_distribution",
    "_confusion_matrix",
    "_per_class_metrics",
    "_quality_status",
    "_round_number",
    "build_baselines",
    "metric_bundle",
    "validate_probability_matrix",
]
