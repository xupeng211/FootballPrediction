from datetime import datetime
from decimal import Decimal

import pytest

from src.features.feature_definitions import (
    HistoricalMatchupFeatures,
    OddsFeatures,
    RecentPerformanceFeatures,
)


def build_recent_features(**overrides):
    base = dict(
        team_id=1,
        calculation_date=datetime.utcnow(),
        recent_5_wins=3,
        recent_5_draws=1,
        recent_5_losses=1,
        recent_5_goals_for=12,
        recent_5_goals_against=4,
        recent_5_points=10,
        recent_5_home_wins=2,
        recent_5_away_wins=1,
        recent_5_home_goals_for=7,
        recent_5_away_goals_for=5,
    )
    base.update(overrides)
    return RecentPerformanceFeatures(**base)


def test_recent_performance_rates():
    features = build_recent_features()
    assert pytest.approx(features.recent_5_win_rate, 0.01) == 0.6
    assert pytest.approx(features.recent_5_goals_per_game, 0.01) == 12 / 5

    empty = build_recent_features(
        recent_5_wins=0, recent_5_draws=0, recent_5_losses=0, recent_5_goals_for=0
    )
    assert empty.recent_5_win_rate == 0.0
    assert empty.recent_5_goals_per_game == 0.0


def test_recent_performance_to_dict_contains_computed_fields():
    features = build_recent_features()
    payload = features.to_dict()
    assert payload["recent_5_win_rate"] == features.recent_5_win_rate
    assert payload["recent_5_goals_per_game"] == features.recent_5_goals_per_game


def build_historical_features(**overrides):
    base = dict(
        home_team_id=1,
        away_team_id=2,
        calculation_date=datetime.utcnow(),
        h2h_total_matches=4,
        h2h_home_wins=2,
        h2h_away_wins=1,
        h2h_draws=1,
        h2h_home_goals_total=6,
        h2h_away_goals_total=4,
        h2h_recent_5_home_wins=1,
        h2h_recent_5_away_wins=1,
        h2h_recent_5_draws=1,
    )
    base.update(overrides)
    return HistoricalMatchupFeatures(**base)


def test_historical_matchup_rates():
    features = build_historical_features()
    assert pytest.approx(features.h2h_home_win_rate, 0.01) == 0.5
    assert pytest.approx(features.h2h_goals_avg, 0.01) == 2.5
    assert pytest.approx(features.h2h_home_goals_avg, 0.01) == 1.5

    zero = build_historical_features(
        h2h_total_matches=0, h2h_home_goals_total=0, h2h_away_goals_total=0
    )
    assert zero.h2h_home_win_rate == 0.0
    assert zero.h2h_goals_avg == 0.0
    assert zero.h2h_home_goals_avg == 0.0


def test_historical_matchup_to_dict_contains_statistics():
    features = build_historical_features()
    payload = features.to_dict()
    assert payload["h2h_home_win_rate"] == features.h2h_home_win_rate
    assert payload["h2h_goals_avg"] == features.h2h_goals_avg


def build_odds_features(**overrides):
    base = dict(
        match_id=123,
        calculation_date=datetime.utcnow(),
        home_odds_avg=Decimal("2.0"),
        draw_odds_avg=Decimal("3.5"),
        away_odds_avg=Decimal("4.2"),
        home_implied_probability=0.5,
        draw_implied_probability=0.2857,
        away_implied_probability=0.2381,
        bookmaker_count=5,
        odds_variance_home=0.02,
        odds_variance_draw=0.03,
        odds_variance_away=0.01,
        max_home_odds=Decimal("2.2"),
        min_home_odds=Decimal("1.8"),
        odds_range_home=0.4,
    )
    base.update(overrides)
    return OddsFeatures(**base)


def test_bookmaker_consensus_calculation():
    features = build_odds_features()
    expected = 1 - ((0.02 + 0.03 + 0.01) / 3)
    assert pytest.approx(features.bookmaker_consensus, 0.01) == expected

    incomplete = build_odds_features(odds_variance_home=None)
    assert incomplete.bookmaker_consensus is None
