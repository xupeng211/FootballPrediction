import pytest

from src.core.exceptions import DomainError
from src.domain.models.team import Team, TeamForm, TeamStats


@pytest.fixture
def team() -> Team:
    return Team(name="Arsenal", country="England", code="ARS")


@pytest.mark.unit
class TestTeamInitialization:
    def test_should_initialize_with_default_stats_and_form(self, team):
        assert team.stats is not None
        assert team.form is not None
        assert team.is_active is True

    def test_should_validate_basic_constraints(self):
        with pytest.raises(DomainError):
            Team(name="")

        with pytest.raises(DomainError):
            Team(name="Valid", short_name="TooLongShortName")

        with pytest.raises(DomainError):
            Team(name="Valid", code="A1B")

        with pytest.raises(DomainError):
            Team(name="Valid", capacity=-1)


class TestTeamStats:
    def test_should_compute_points_and_goal_difference(self):
        _stats = TeamStats(
            matches_played=10, wins=6, draws=2, losses=2, goals_for=20, goals_against=10
        )

        assert stats.points == 20
        assert stats.goal_difference == 10
        assert stats.win_rate == pytest.approx(0.6)

    def test_should_reject_invalid_totals(self):
        with pytest.raises(DomainError):
            TeamStats(matches_played=5, wins=6)

        with pytest.raises(DomainError):
            TeamStats(matches_played=1, wins=1, goals_for=-1)


class TestTeamForm:
    def test_should_manage_recent_results(self):
        form = TeamForm()
        form.add_result("W")
        form.add_result("L")
        form.add_result("W")

        assert form.last_matches[0] == "W"
        assert form.current_streak >= 0

    def test_should_reject_invalid_results(self):
        form = TeamForm()
        with pytest.raises(DomainError):
            form.add_result("X")


class TestTeamBehaviour:
    def test_should_add_match_result_and_update_stats(self, team):
        team.add_match_result("win", goals_for=3, goals_against=1)

        assert team.stats.matches_played == 1
        assert team.stats.wins == 1
        assert team.form.last_matches[0] == "W"
        assert team.updated_at >= team.created_at

    def test_should_calculate_strength_and_rank(self, team):
        team.stats.matches_played = 12
        team.stats.wins = 10
        team.stats.draws = 1
        team.stats.losses = 1
        team.stats.goals_for = 32
        team.stats.goals_against = 8

        for result in ["W", "W", "W", "W", "D"]:
            team.form.add_result(result)

        strength = team.calculate_strength()
        assert 80 <= strength <= 100
        assert team.rank == "顶级"

    def test_should_handle_rival_logic(self, team, monkeypatch):
        monkeypatch.setattr(team, "get_rival_team_ids", lambda: [10, 11])
        assert team.is_rival(10) is True
        assert team.is_rival(20) is False

    def test_should_roundtrip_via_dict(self, team):
        team.stats.matches_played = 10
        team.stats.wins = 5
        team.stats.draws = 3
        team.stats.losses = 2
        team.stats.goals_for = 18
        team.stats.goals_against = 12
        team.form.add_result("W")

        _data = team.to_dict()
        restored = Team.from_dict(data)

        assert restored.name == team.name
        assert restored.stats.matches_played == 10
        assert restored.form.last_matches[0] == "W"

    def test_should_update_info_fields(self, team):
        original_updated_at = team.updated_at
        team.update_info(name="New Name", capacity=60000)

        assert team.name == "New Name"
        assert team.capacity == 60000
        assert team.updated_at >= original_updated_at

    def test_should_validate_match_result_inputs(self, team):
        with pytest.raises(DomainError):
            team.add_match_result("invalid", 1, 0)

        with pytest.raises(DomainError):
            team.add_match_result("win", -1, 0)
