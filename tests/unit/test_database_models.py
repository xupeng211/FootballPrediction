from src.database.models.league import League
from src.database.models.team import Team


def test_league_model():
    league = League(name="Test League")
    assert league.name == "Test League"


def test_team_model():
    team = Team(name="Test Team")
    assert team.name == "Test Team"
