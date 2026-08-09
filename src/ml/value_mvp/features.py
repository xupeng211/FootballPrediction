"""Sequential pre-match feature generation (Elo + rolling + exposure).

Strictly chronological: features for a match are computed from team state
BEFORE kickoff; the match result (FTR + goals) is applied to the state ONLY
after the feature row is frozen. Matches sharing the same kickoff_at are
processed as a batch (all features computed from pre-batch state, then all
results applied), so no same-instant match can see another same-instant
match's result.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.ml.value_mvp.sources import Match

INITIAL_ELO = 1500.0
K_FACTOR = 20.0
ROLLING_WINDOW = 5
POINTS_WIN = 3
POINTS_DRAW = 1

_HOME_SCORE = {"H": 1.0, "D": 0.5, "A": 0.0}
_MISSING = float("nan")


@dataclass
class TeamState:
    """Per-team sequential state: Elo, rolling result windows, exposure."""

    elo: float = INITIAL_ELO
    results: deque[Any] = field(default_factory=deque)  # (points, goals_for, goals_against)
    home_results: deque[Any] = field(default_factory=deque)  # points of home matches
    away_results: deque[Any] = field(default_factory=deque)  # points of away matches
    matches_seen: int = 0


def _expected_score(rating: float, opponent_rating: float) -> float:
    """Elo expected score for rating vs opponent_rating."""
    return float(1.0 / (1.0 + 10.0 ** ((opponent_rating - rating) / 400.0)))


def _mean(values: list[float]) -> float:
    """Mean of a list; NaN when empty."""
    if not values:
        return _MISSING
    return sum(values) / len(values)


def _points_ppg(window: deque[Any]) -> float:
    """Mean points per game over the window; NaN when empty."""
    if not window:
        return _MISSING
    values = [item[0] if isinstance(item, tuple) else item for item in window]
    return _mean(values)


def _goals_for(window: deque[Any]) -> float:
    """Mean goals scored per game over the window; NaN when empty."""
    if not window:
        return _MISSING
    return _mean([item[1] for item in window])


def _goals_against(window: deque[Any]) -> float:
    """Mean goals conceded per game over the window; NaN when empty."""
    if not window:
        return _MISSING
    return _mean([item[2] for item in window])


def compute_match_features(match: Match, state: dict[str, TeamState]) -> dict[str, float]:
    """Compute the 13 pre-match features for one match from pre-kickoff state."""
    home = state.setdefault(match.home, TeamState())
    away = state.setdefault(match.away, TeamState())
    return {
        "home_elo_pre": home.elo,
        "away_elo_pre": away.elo,
        "elo_diff": home.elo - away.elo,
        "home_last5_ppg": _points_ppg(home.results),
        "away_last5_ppg": _points_ppg(away.results),
        "home_last5_goals_for": _goals_for(home.results),
        "away_last5_goals_for": _goals_for(away.results),
        "home_last5_goals_against": _goals_against(home.results),
        "away_last5_goals_against": _goals_against(away.results),
        "home_last5_home_ppg": _points_ppg(home.home_results),
        "away_last5_away_ppg": _points_ppg(away.away_results),
        "home_matches_seen": float(home.matches_seen),
        "away_matches_seen": float(away.matches_seen),
    }


def _points_for(label_str: str, side: str) -> int:
    """League points awarded to a side for a result (3 win / 1 draw / 0 loss)."""
    if label_str == "D":
        return POINTS_DRAW
    if (label_str == "H" and side == "home") or (label_str == "A" and side == "away"):
        return POINTS_WIN
    return 0


def apply_match_result(match: Match, state: dict[str, TeamState]) -> None:
    """Update team state with the match result (after the feature row is frozen)."""
    home = state.setdefault(match.home, TeamState())
    away = state.setdefault(match.away, TeamState())

    home_score = _HOME_SCORE[match.label_str]
    away_score = 1.0 - home_score

    home_expected = _expected_score(home.elo, away.elo)
    away_expected = _expected_score(away.elo, home.elo)

    home.elo += K_FACTOR * (home_score - home_expected)
    away.elo += K_FACTOR * (away_score - away_expected)

    home_points = _points_for(match.label_str, "home")
    away_points = _points_for(match.label_str, "away")

    home.results.append((home_points, match.home_goals, match.away_goals))
    away.results.append((away_points, match.away_goals, match.home_goals))
    home.home_results.append(home_points)
    away.away_results.append(away_points)

    while len(home.results) > ROLLING_WINDOW:
        home.results.popleft()
    while len(away.results) > ROLLING_WINDOW:
        away.results.popleft()
    while len(home.home_results) > ROLLING_WINDOW:
        home.home_results.popleft()
    while len(away.away_results) > ROLLING_WINDOW:
        away.away_results.popleft()

    home.matches_seen += 1
    away.matches_seen += 1


def build_feature_frame(matches: list[Match]) -> list[dict[str, float]]:
    """Generate feature rows for all matches in chronological order.

    Matches are sorted by (kickoff_at, mid); same-kickoff matches are batched:
    features for the whole batch are computed from pre-batch state, then all
    batch results are applied.
    """
    ordered = sorted(matches, key=lambda m: (m.kickoff_at, m.mid))
    state: dict[str, TeamState] = defaultdict(TeamState)
    rows: list[dict[str, float]] = []

    index = 0
    while index < len(ordered):
        batch_kickoff = ordered[index].kickoff_at
        batch = []
        while index < len(ordered) and ordered[index].kickoff_at == batch_kickoff:
            batch.append(ordered[index])
            index += 1
        rows.extend(compute_match_features(match, state) for match in batch)
        for match in batch:
            apply_match_result(match, state)
    return rows
