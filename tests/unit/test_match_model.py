from src.database.models.match import Match

def test_match_model():
    match = Match(home_team_id=1, away_team_id=2)
    assert match.home_team_id == 1
    assert match.away_team_id == 2