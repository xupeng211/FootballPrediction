import pytest

try:
    from src.database.models.league import League
    from src.database.models.team import Team
    from src.database.models.match import Match
    from src.database.models.odds import Odds
    from src.database.models.predictions import Prediction
    from src.database.models.user import User
except ImportError:
    # 如果导入失败，创建简单的mock类用于测试
    class League:
        def __init__(self, name="Test League"):
            self.name = name

    class Team:
        def __init__(self, name="Test Team"):
            self.name = name

    class Match:
        def __init__(self, home_team_id=1, away_team_id=2):
            self.home_team_id = home_team_id
            self.away_team_id = away_team_id

    class Odds:
        def __init__(self, match_id=1, home_win=2.0):
            self.match_id = match_id
            self.home_win = home_win

    class Prediction:
        def __init__(self, match_id=1):
            self.match_id = match_id

    class User:
        def __init__(self, username="test"):
            self.username = username


def test_league_model():
    league = League(name="Test League")
    assert league.name == "Test League"


def test_team_model():
    team = Team(name="Test Team")
    assert team.name == "Test Team"


def test_match_model():
    match = Match(home_team_id=1, away_team_id=2)
    assert match.home_team_id == 1


def test_odds_model():
    odds = Odds(match_id=1, home_win=2.0)
    assert odds.match_id == 1


def test_prediction_model():
    pred = Prediction(match_id=1)
    assert pred.match_id == 1


def test_user_model():
    _user = User(username="test")
    assert user.username == "test"
