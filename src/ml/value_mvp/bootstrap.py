"""Deterministic season-stratified paired bootstrap for VALUE_MVP-1.

Per-match delta_log_loss (model - market) is resampled WITHIN each season
(preserving season proportions), pooled, and the pooled mean delta computed.
Repetition count and seed are frozen in the protocol; results are
byte-deterministic for a fixed input order.
"""

from __future__ import annotations

import numpy as np


def season_stratified_bootstrap_deltas(
    deltas_by_season: dict[str, np.ndarray],
    replicates: int,
    seed: int,
) -> np.ndarray:
    """Return replicate pooled-mean deltas from season-stratified resampling."""
    rng = np.random.default_rng(seed)
    season_keys = sorted(deltas_by_season)
    counts = {key: len(deltas_by_season[key]) for key in season_keys}
    total = sum(counts.values())
    if total == 0:
        raise ValueError("no delta values to bootstrap")

    replicate_means = np.empty(replicates, dtype=float)
    for replicate in range(replicates):
        sampled: list[float] = []
        for key in season_keys:
            season_deltas = deltas_by_season[key]
            indices = rng.integers(0, counts[key], size=counts[key])
            sampled.extend(season_deltas[indices])
        replicate_means[replicate] = float(np.mean(sampled))
    return replicate_means


def percentile_ci(replicate_means: np.ndarray, percentiles: list[float]) -> tuple[float, float]:
    """Percentile confidence interval over bootstrap replicates."""
    low, high = np.percentile(replicate_means, percentiles)
    return float(low), float(high)


def classify_claim(delta_low: float, delta_high: float) -> str:
    """Classify the primary claim from the pooled delta CI (frozen rules).

    Returns the claim key (MODEL_BETTER_THAN_CLOSING / MARKET_BETTER_THAN_MODEL /
    INCONCLUSIVE); the protocol dict holds the human-readable definitions.
    """
    if delta_high < 0.0:
        return "MODEL_BETTER_THAN_CLOSING"
    if delta_low > 0.0:
        return "MARKET_BETTER_THAN_MODEL"
    return "INCONCLUSIVE"
