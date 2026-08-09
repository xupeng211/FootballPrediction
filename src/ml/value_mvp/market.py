"""Market probability construction: no-vig conversion and closing consensus.

Frozen rules (protocol): proportional no-vig per valid bookmaker triple
(odds > 1, all three selections present, finite); arithmetic mean across valid
bookmakers; renormalization to sum exactly 1. Synthetic derived columns
(Max/Avg) are excluded. Matches with fewer than minimum_bookmaker_count valid
closing bookmakers are MARKET_BENCHMARK_INELIGIBLE and are never imputed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.ml.value_mvp.protocol import CLASS_LABELS

if TYPE_CHECKING:
    from src.ml.value_mvp.sources import Match

VALID_PHASES = ("closing", "first_collection_after_market_open")


def valid_triple(selections: dict) -> tuple[float, float, float] | None:
    """Return (h, d, a) odds when the triple is valid, else None."""
    if set(selections) < set(CLASS_LABELS):
        return None
    odds = []
    for selection in CLASS_LABELS:
        value = selections[selection]
        if not isinstance(value, (int, float)) or value <= 1.0:
            return None
        odds.append(float(value))
    return tuple(odds)  # type: ignore[return-value]


def no_vig(triple: tuple[float, float, float]) -> tuple[tuple[float, float, float], float]:
    """Proportional de-juice: p_k = (1/odds_k) / sum(1/odds). Returns (p, overround)."""
    inverse = [1.0 / odd for odd in triple]
    overround = sum(inverse)
    if not overround > 0:
        raise ValueError(f"non-positive overround: {overround}")
    probabilities = tuple(value / overround for value in inverse)
    return probabilities, overround


def bookmaker_consensus(match: Match, phase: str, excluded: tuple[str, ...]) -> dict | None:
    """Arithmetic-mean no-vig consensus across valid bookmakers for a phase.

    Returns {"p": (h, d, a), "n_bookmakers": int, "overrounds": [...]} or None
    when no valid bookmaker triple exists for the phase.
    """
    phase_odds = match.odds.get(phase, {})
    vectors: list[tuple[float, float, float]] = []
    overrounds: list[float] = []
    for bookmaker in sorted(phase_odds):
        if bookmaker in excluded:
            continue
        triple = valid_triple(phase_odds[bookmaker])
        if triple is None:
            continue
        probabilities, overround = no_vig(triple)
        vectors.append(probabilities)
        overrounds.append(overround)
    if not vectors:
        return None
    mean = tuple(sum(vec[k] for vec in vectors) / len(vectors) for k in range(3))
    total = sum(mean)
    renormalized = tuple(value / total for value in mean)
    return {"p": renormalized, "n_bookmakers": len(vectors), "overrounds": overrounds}


def closing_consensus(match: Match, protocol: dict) -> dict | None:
    """Closing consensus with the protocol's minimum bookmaker count enforced."""
    consensus = bookmaker_consensus(
        match, "closing", tuple(protocol["population_policy"]["bookmaker_exclusion"])
    )
    if consensus is None or consensus["n_bookmakers"] < protocol["minimum_bookmaker_count"]:
        return None
    return consensus


def first_collection_consensus(match: Match, protocol: dict) -> dict | None:
    """First-collection consensus (market probe only; never a model feature)."""
    return bookmaker_consensus(
        match,
        "first_collection_after_market_open",
        tuple(protocol["population_policy"]["bookmaker_exclusion"]),
    )


def mean_overround(consensus: dict | None) -> float | None:
    """Mean bookmaker overround for a consensus; None when unavailable."""
    if consensus is None or not consensus["overrounds"]:
        return None
    return sum(consensus["overrounds"]) / len(consensus["overrounds"])
