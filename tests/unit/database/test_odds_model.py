import pytest

from src.database.models.odds import Odds


@pytest.mark.unit
@pytest.mark.database
def test_odds_model():
    odds = Odds(match_id=1, home_win=2.0, draw=3.0, away_win=3.5)
    assert odds.match_id == 1
    assert odds.home_win == 2.0
