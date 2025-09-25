from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
import pytest

from src.features.entities import MatchEntity
from src.features.feature_calculator import FeatureCalculator
from src.features.feature_definitions import (
    HistoricalMatchupFeatures,
    OddsFeatures,
    RecentPerformanceFeatures,
)


class StubResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items


class StubSession:
    def __init__(self, items):
        self._items = items

    async def execute(self, _query):
        return StubResult(self._items)


@dataclass
class MatchStub:
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    match_time: datetime
    match_status: str = "completed"


@dataclass
class OddsStub:
    home_odds: float
    draw_odds: float
    away_odds: float
    bookmaker: str
    collected_at: datetime
    market_type: str = "1x2"


@pytest.mark.asyncio
async def test_calculate_recent_performance_basic_counts():
    calculator = FeatureCalculator()
    matches = [
        MatchStub(1, 2, 3, 1, datetime.utcnow()),
        MatchStub(2, 1, 0, 0, datetime.utcnow()),
        MatchStub(1, 3, 1, 2, datetime.utcnow()),
    ]
    session = StubSession(matches)

    features = await calculator._calculate_recent_performance(
        session=session, team_id=1, calculation_date=datetime.utcnow()
    )

    assert isinstance(features, RecentPerformanceFeatures)
    assert features.recent_5_wins == 1
    assert features.recent_5_draws == 1
    assert features.recent_5_losses == 1
    assert features.recent_5_goals_for == 4
    assert features.recent_5_goals_against == 3
    assert features.recent_5_points == 4


@pytest.mark.asyncio
async def test_calculate_historical_matchup_handles_home_away_switch():
    calculator = FeatureCalculator()
    matches = [
        MatchStub(1, 2, 2, 0, datetime.utcnow()),  # 主队胜
        MatchStub(
            2, 1, 1, 3, datetime.utcnow() - timedelta(days=1)
        ),  # 交换位置 -> 仍主队胜
        MatchStub(1, 2, 0, 0, datetime.utcnow() - timedelta(days=2)),  # 平局
        MatchStub(2, 1, 4, 5, datetime.utcnow() - timedelta(days=3)),  # 客队胜
    ]
    session = StubSession(matches)

    features = await calculator._calculate_historical_matchup(
        session=session,
        home_team_id=1,
        away_team_id=2,
        calculation_date=datetime.utcnow(),
    )

    assert isinstance(features, HistoricalMatchupFeatures)
    assert features.h2h_total_matches == 4
    assert features.h2h_home_wins == 3
    assert features.h2h_away_wins == 0
    assert features.h2h_draws == 1
    assert features.h2h_home_goals_total == 10  # 2+3+0+5
    assert features.h2h_away_goals_total == 5  # 0+1+0+4
    assert features.h2h_recent_5_home_wins >= 1


@pytest.mark.asyncio
async def test_calculate_odds_features_computes_statistics():
    calculator = FeatureCalculator()
    odds_samples = [
        OddsStub(
            home_odds=2.0,
            draw_odds=3.5,
            away_odds=4.0,
            bookmaker="a",
            collected_at=datetime.utcnow(),
        ),
        OddsStub(
            home_odds=2.2,
            draw_odds=3.3,
            away_odds=4.5,
            bookmaker="b",
            collected_at=datetime.utcnow(),
        ),
    ]
    session = StubSession(odds_samples)

    features = await calculator._calculate_odds_features(
        session=session, match_id=55, calculation_date=datetime.utcnow()
    )

    assert isinstance(features, OddsFeatures)
    assert features.bookmaker_count == 2
    assert features.home_odds_avg == Decimal("2.1")
    assert features.min_home_odds == Decimal("2.0")
    assert features.max_home_odds == Decimal("2.2")
    assert features.away_implied_probability == pytest.approx(1 / 4.25, 1e-3)


def test_calculator_stat_helpers_handle_invalid_inputs():
    calculator = FeatureCalculator()
    assert calculator.calculate_mean([]) is None
    assert calculator.calculate_std([1]) is None
    assert calculator.calculate_min([]) is None
    assert calculator.calculate_max([]) is None

    data = [1, 2, 3]
    assert calculator.calculate_mean(data) == pytest.approx(2.0)
    assert calculator.calculate_std(data) == pytest.approx(pd.Series(data).std(ddof=1))
    assert calculator.calculate_min(data) == 1.0
    assert calculator.calculate_max(data) == 3.0


@pytest.mark.asyncio
async def test_calculate_all_match_features_uses_subtasks(monkeypatch):
    calculator = FeatureCalculator()

    async def fake_recent(session, team_id, calc_date):  # noqa: ARG001
        return RecentPerformanceFeatures(
            team_id=team_id, calculation_date=calc_date, recent_5_wins=1
        )

    async def fake_historical(session, home_id, away_id, calc_date):  # noqa: ARG001
        return HistoricalMatchupFeatures(
            home_team_id=home_id,
            away_team_id=away_id,
            calculation_date=calc_date,
            h2h_total_matches=1,
        )

    async def fake_odds(session, match_id, calc_date):  # noqa: ARG001
        return OddsFeatures(
            match_id=match_id, calculation_date=calc_date, bookmaker_count=1
        )

    class DummyAsyncContext:
        def __init__(self):
            self.session = object()

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(calculator, "_calculate_recent_performance", fake_recent)
    monkeypatch.setattr(calculator, "_calculate_historical_matchup", fake_historical)
    monkeypatch.setattr(calculator, "_calculate_odds_features", fake_odds)
    monkeypatch.setattr(
        calculator.db_manager, "get_async_session", lambda: DummyAsyncContext()
    )

    match_entity = MatchEntity(
        match_id=77,
        home_team_id=1,
        away_team_id=2,
        league_id=3,
        match_time=datetime.utcnow(),
        season="2024/25",
    )

    result = await calculator.calculate_all_match_features(match_entity)
    assert result.match_entity.match_id == 77
    assert result.home_team_recent.recent_5_wins == 1
    assert result.odds_features.bookmaker_count == 1


def test_calculate_rolling_mean_with_list():
    calculator = FeatureCalculator()
    series = calculator.calculate_rolling_mean([1, 2, 3], window=2)
    assert list(series) == [1.0, 1.5, 2.5]
