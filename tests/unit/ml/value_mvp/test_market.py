"""Market probability construction tests (no-vig, consensus, eligibility)."""

from __future__ import annotations

import pytest

from src.ml.value_mvp.market import (
    bookmaker_consensus,
    closing_consensus,
    first_collection_consensus,
    mean_overround,
    no_vig,
    valid_triple,
)
from src.ml.value_mvp.sources import Match
from tests.unit.ml.value_mvp._helpers import PHASE_CLOSING, PHASE_FIRST, synthetic_protocol


def _match_with_odds(closing=None, first=None) -> Match:
    return Match(
        mid="m1",
        kickoff_at="2022-08-06T14:00:00+01:00",
        home="Alpha FC",
        away="Beta FC",
        season="2022/23",
        label=0,
        label_str="H",
        odds={
            PHASE_CLOSING: closing or {},
            PHASE_FIRST: first or {},
        },
    )


def test_valid_triple_accepts_complete_odds():
    triple = valid_triple({"home": 2.0, "draw": 3.4, "away": 3.8})
    assert triple == pytest.approx((2.0, 3.4, 3.8))


def test_valid_triple_rejects_incomplete_and_bad_odds():
    assert valid_triple({"home": 2.0, "draw": 3.4}) is None
    assert valid_triple({"home": 0.9, "draw": 3.4, "away": 3.8}) is None
    assert valid_triple({"home": "x", "draw": 3.4, "away": 3.8}) is None


def test_no_vig_proportional_and_overround():
    probabilities, overround = no_vig((2.0, 3.4, 3.8))
    expected_overround = 1 / 2.0 + 1 / 3.4 + 1 / 3.8
    assert overround == pytest.approx(expected_overround)
    assert sum(probabilities) == pytest.approx(1.0)
    assert probabilities[0] == pytest.approx((1 / 2.0) / expected_overround)
    with pytest.raises(ValueError, match="non-positive overround"):
        no_vig((-2.0, -2.0, 2.0))


def test_bookmaker_consensus_means_and_renormalizes():
    match = _match_with_odds(
        closing={
            "b1": {"home": 2.0, "draw": 3.4, "away": 3.8},
            "b2": {"home": 1.9, "draw": 3.5, "away": 4.0},
        }
    )
    consensus = bookmaker_consensus(match, PHASE_CLOSING, ())
    assert consensus is not None
    assert consensus["n_bookmakers"] == 2
    assert len(consensus["overrounds"]) == 2
    assert sum(consensus["p"]) == pytest.approx(1.0)
    # every component must lie strictly inside the [0,1] simplex
    assert all(0.0 < value < 1.0 for value in consensus["p"])


def test_bookmaker_consensus_excludes_synthetic_columns():
    match = _match_with_odds(
        closing={
            "b1": {"home": 2.0, "draw": 3.4, "away": 3.8},
            "Max": {"home": 1.1, "draw": 1.2, "away": 1.3},
            "Avg": {"home": 1.05, "draw": 1.1, "away": 1.15},
        }
    )
    consensus = bookmaker_consensus(match, PHASE_CLOSING, ("Max", "Avg"))
    assert consensus["n_bookmakers"] == 1


def test_closing_consensus_enforces_minimum_bookmaker_count():
    protocol = synthetic_protocol()
    match = _match_with_odds(closing={"b1": {"home": 2.0, "draw": 3.4, "away": 3.8}})
    assert closing_consensus(match, protocol) is None  # only 1 bookmaker, min is 2
    protocol["minimum_bookmaker_count"] = 1
    assert closing_consensus(match, protocol)["n_bookmakers"] == 1
    # no closing odds at all
    assert closing_consensus(_match_with_odds(), synthetic_protocol()) is None


def test_first_collection_consensus_is_separate_phase():
    match = _match_with_odds(first={"f1": {"home": 2.1, "draw": 3.3, "away": 3.5}})
    first = first_collection_consensus(match, synthetic_protocol())
    assert first is not None
    assert first["n_bookmakers"] == 1
    assert closing_consensus(match, synthetic_protocol()) is None


def test_mean_overround():
    match = _match_with_odds(
        closing={
            "b1": {"home": 2.0, "draw": 3.4, "away": 3.8},
            "b2": {"home": 1.9, "draw": 3.5, "away": 4.0},
        }
    )
    consensus = bookmaker_consensus(match, PHASE_CLOSING, ())
    overround = mean_overround(consensus)
    expected = sum(consensus["overrounds"]) / len(consensus["overrounds"])
    assert overround == pytest.approx(expected)
    assert mean_overround(None) is None
