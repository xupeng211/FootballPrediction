"""Bootstrap and claim-classification tests (determinism enforced)."""

from __future__ import annotations

import numpy as np
import pytest

from src.ml.value_mvp.bootstrap import (
    classify_claim,
    percentile_ci,
    season_stratified_bootstrap_deltas,
)


def _deltas() -> dict[str, np.ndarray]:
    rng = np.random.default_rng(42)
    return {
        "2022/23": rng.normal(0.01, 0.1, 50),
        "2023/24": rng.normal(-0.02, 0.1, 60),
        "2024/25": rng.normal(0.0, 0.1, 40),
    }


def test_bootstrap_is_byte_deterministic_for_same_seed():
    first = season_stratified_bootstrap_deltas(_deltas(), 200, 20260810)
    second = season_stratified_bootstrap_deltas(_deltas(), 200, 20260810)
    assert first.tolist() == second.tolist()
    third = season_stratified_bootstrap_deltas(_deltas(), 200, 20260811)
    assert third.tolist() != first.tolist()


def test_bootstrap_preserves_season_proportions_and_pooled_mean():
    deltas = _deltas()
    replicates = season_stratified_bootstrap_deltas(deltas, 2000, 7)
    expected = sum(deltas[key].sum() for key in deltas) / sum(len(deltas[key]) for key in deltas)
    assert float(np.mean(replicates)) == pytest.approx(expected, abs=0.01)


def test_percentile_ci_returns_bounds():
    replicates = np.linspace(-0.05, 0.05, 401)
    low, high = percentile_ci(replicates, [2.5, 97.5])
    assert low == pytest.approx(-0.0475)
    assert high == pytest.approx(0.0475)
    assert low < high


def test_classify_claim_three_bands():
    assert classify_claim(-0.1, -0.001) == "MODEL_BETTER_THAN_CLOSING"
    assert classify_claim(0.001, 0.1) == "MARKET_BETTER_THAN_MODEL"
    assert classify_claim(-0.001, 0.001) == "INCONCLUSIVE"
    assert classify_claim(0.0, 0.0) == "INCONCLUSIVE"
