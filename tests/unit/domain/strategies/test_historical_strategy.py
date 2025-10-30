import asyncio
from datetime import datetime, timedelta

import pytest

from src.domain.models.match import Match
from src.domain.models.team import Team
from src.domain.strategies.base import PredictionInput
from src.domain.strategies.historical import HistoricalMatch, HistoricalStrategy


@pytest.mark.unit
def test_historical_strategy_provides_stable_predictions():
    strategy = HistoricalStrategy()
    asyncio.run(
        strategy.initialize(
            {
                "min_historical_matches": 1,
                "random_seed": 123,
                "disable_mock_generation": True,
            }
        )
    )

    base_date = datetime(2023, 1, 1)
    match_a = HistoricalMatch(
        match_id=1,
        home_team_id=1,
        away_team_id=2,
        home_score=2,
        away_score=1,
        match_date=base_date,
        league_id=1,
        season="2022/2023",
        importance=1.0,
    )
    match_b = HistoricalMatch(
        match_id=2,
        home_team_id=1,
        away_team_id=2,
        home_score=1,
        away_score=0,
        match_date=base_date + timedelta(days=60),
        league_id=1,
        season="2022/2023",
        importance=1.0,
    )
    match_c = HistoricalMatch(
        match_id=3,
        home_team_id=2,
        away_team_id=1,
        home_score=0,
        away_score=2,
        match_date=base_date + timedelta(days=120),
        league_id=1,
        season="2022/2023",
        importance=1.0,
    )

    strategy._team_vs_team[(1, 2)] = [match_a, match_b, match_c]
    strategy._historical_matches[1] = [match_a, match_b]
    strategy._historical_matches[2] = [match_c]
    strategy._score_patterns = {
    }
    strategy._season_patterns = {"2022/2023": [match_a, match_b, match_c]}

    upcoming_match = Match(
        home_team_id=1,
        away_team_id=2,
        league_id=1,
        season="2024-2025",
        match_date=datetime.utcnow() + timedelta(days=5),
    )
    upcoming_match.scheduled_time = upcoming_match.match_date
    home_team = Team(id=1, name="Alpha FC", country="England")
    away_team = Team(id=2, name="Beta FC", country="England")

    input_data = PredictionInput(
        match=upcoming_match,
        home_team=home_team,
        away_team=away_team,
    )

    first_output = asyncio.run(strategy.predict(input_data))
    second_output = asyncio.run(strategy.predict(input_data))

    assert first_output.predicted_home_score == second_output.predicted_home_score
    assert first_output.predicted_away_score == second_output.predicted_away_score
    assert first_output.probability_distribution == second_output.probability_distribution
    assert first_output.confidence == pytest.approx(second_output.confidence)
    assert first_output.predicted_home_score >= 0
    assert first_output.predicted_away_score >= 0
