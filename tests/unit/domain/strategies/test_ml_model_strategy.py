import asyncio
from datetime import datetime, timedelta

import pytest

from src.domain.models.match import Match
from src.domain.models.team import Team
from src.domain.strategies.base import PredictionInput
from src.domain.strategies.ml_model import MLModelStrategy


@pytest.mark.unit
def test_ml_model_strategy_mock_predictions_are_deterministic():
    strategy = MLModelStrategy("mock_model")
    asyncio.run(strategy.initialize({"random_seed": 321}))

    upcoming_match = Match(
        home_team_id=3,
        away_team_id=4,
        league_id=1,
        season="2024-2025",
        match_date=datetime.utcnow() + timedelta(days=3),
    )
    home_team = Team(id=3, name="Gamma FC", country="England")
    away_team = Team(id=4, name="Delta FC", country="England")

    input_data = PredictionInput(
        match=upcoming_match,
        home_team=home_team,
        away_team=away_team,
        additional_features={
            "ml_features": {
                "home_team_rating": 82,
                "away_team_rating": 75,
                "home_form": 0.6,
                "away_form": 0.4,
                "head_to_head_home_wins": 5,
                "head_to_head_away_wins": 2,
                "days_since_last_match_home": 4,
                "days_since_last_match_away": 6,
                "home_advantage": 1,
                "match_importance": 0.8,
            }
        },
    )

    single_prediction = asyncio.run(strategy.predict(input_data))
    repeat_prediction = asyncio.run(strategy.predict(input_data))

    assert (
        single_prediction.predicted_home_score == repeat_prediction.predicted_home_score
    )
    assert (
        single_prediction.predicted_away_score == repeat_prediction.predicted_away_score
    )
    assert (
        single_prediction.probability_distribution
        == repeat_prediction.probability_distribution
    )
    assert single_prediction.confidence == repeat_prediction.confidence

    batch_outputs = asyncio.run(strategy.batch_predict([input_data, input_data]))
    assert len(batch_outputs) == 2
    assert (
        batch_outputs[0].predicted_home_score == single_prediction.predicted_home_score
    )
    assert (
        batch_outputs[0].probability_distribution
        == single_prediction.probability_distribution
    )
