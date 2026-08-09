"""Evaluation metric tests (frozen formulas from the protocol)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.ml.value_mvp.evaluation import (
    accuracy,
    brier_score,
    calibration_summary,
    class_frequency_probabilities,
    log_loss_score,
    per_row_brier,
    per_row_log_loss,
    safe_round,
    validate_probability_matrix,
)


def _probs():
    return np.array(
        [
            [0.6, 0.3, 0.1],
            [0.1, 0.8, 0.1],
            [0.2, 0.2, 0.6],
        ]
    )


def test_per_row_log_loss_matches_manual_formula():
    probabilities = _probs()
    labels = np.array([0, 1, 2])
    eps = 1e-15
    manual = [-math.log(0.6), -math.log(0.8), -math.log(0.6)]
    computed = per_row_log_loss(probabilities, labels, eps)
    assert computed == pytest.approx(manual)
    assert log_loss_score(probabilities, labels, eps) == pytest.approx(sum(manual) / 3)


def test_log_loss_clips_to_eps():
    probabilities = np.array([[0.0, 1.0, 0.0]])
    labels = np.array([0])
    eps = 1e-15
    assert per_row_log_loss(probabilities, labels, eps)[0] == pytest.approx(-math.log(eps))
    # perfect prediction at the other extreme
    assert per_row_log_loss(np.array([[1.0, 0.0, 0.0]]), np.array([0]), eps)[0] == pytest.approx(
        0.0
    )


def test_brier_score_matches_manual():
    probabilities = _probs()
    labels = np.array([0, 1, 2])
    manual = [
        (1 - 0.6) ** 2 + 0.3**2 + 0.1**2,
        0.1**2 + (1 - 0.8) ** 2 + 0.1**2,
        0.2**2 + 0.2**2 + (1 - 0.6) ** 2,
    ]
    assert per_row_brier(probabilities, labels) == pytest.approx(manual)
    assert brier_score(probabilities, labels) == pytest.approx(sum(manual) / 3)


def test_accuracy_counts_argmax_matches():
    probabilities = _probs()
    assert accuracy(probabilities, np.array([0, 1, 2])) == pytest.approx(1.0)
    assert accuracy(probabilities, np.array([0, 0, 0])) == pytest.approx(1 / 3)


def test_calibration_summary_bins_and_counts():
    probabilities = np.array([[0.55, 0.35, 0.1], [0.65, 0.2, 0.15]])
    labels = np.array([0, 1])
    summary = calibration_summary(probabilities, labels, [0.0, 0.5, 1.0])
    home_bins = summary[0]["bins"]
    assert home_bins[0]["count"] == 0
    assert home_bins[1]["count"] == 2
    assert home_bins[1]["predicted_mean"] == pytest.approx(0.6)
    assert home_bins[1]["observed_frequency"] == pytest.approx(0.5)
    draw_bins = summary[1]["bins"]
    assert draw_bins[0]["count"] == 2  # 0.35 and 0.2 -> bin [0, 0.5)
    assert draw_bins[1]["count"] == 0


def test_class_frequency_probabilities():
    labels = np.array([0, 0, 0, 1])
    frequencies = class_frequency_probabilities(labels)
    assert frequencies == pytest.approx(np.array([0.75, 0.25, 0.0]))
    assert frequencies.sum() == pytest.approx(1.0)
    with pytest.raises(ValueError, match="empty label"):
        class_frequency_probabilities(np.array([], dtype=int))


def test_validate_probability_matrix():
    validate_probability_matrix(_probs(), "valid")
    with pytest.raises(ValueError, match="non-finite"):
        validate_probability_matrix(np.array([[np.nan, 0.5, 0.5]]), "nan")
    with pytest.raises(ValueError, match=r"\[0,1\]"):
        validate_probability_matrix(np.array([[1.5, -0.5, 0.0]]), "range")
    with pytest.raises(ValueError, match="sum to 1"):
        validate_probability_matrix(np.array([[0.5, 0.2, 0.1]]), "sum")


def test_safe_round_handles_nan():
    assert safe_round(0.123456789123) == 0.1234567891
    assert safe_round(math.nan) is None
    assert safe_round(0.0) == 0.0
