import pytest

from src.domain.models.team import Team, TeamStats
from src.domain.services.team_service import (
    TeamDomainService,
    TeamPerformanceResetEvent,
    TeamProfileUpdatedEvent,
    TeamStatsEvent,
)


class InMemoryTeamRepository:
    def __init__(self):
        self.saved = []
        self.updated = []

    def save(self, team: Team) -> Team:
        self.saved.append(team)
        return team

    def update(self, team: Team) -> Team:
        self.updated.append(team)
        return team


@pytest.fixture
def service() -> TeamDomainService:
    return TeamDomainService()


@pytest.fixture
def team() -> Team:
    team = Team(id=1, name="Arsenal", country="England")
    team.stats = TeamStats(matches_played=0, wins=0, draws=0, losses=0)
    return team


class TestTeamService:
    def test_should_update_team_profile(self, team):
        repo = InMemoryTeamRepository()
        service = TeamDomainService(repository=repo)

        service.update_team_profile(
            team,
            name="Arsenal FC",
            stadium="Emirates",
            capacity=60000,
        )

        assert team.name == "Arsenal FC"
        assert team.stadium == "Emirates"
        assert team.capacity == 60000
        events = service.get_domain_events()
        assert isinstance(events[-1], TeamProfileUpdatedEvent)
        assert events[-1].updated_fields["name"] == "Arsenal FC"
        assert repo.updated, "Repository should receive update call"

    def test_should_record_match_and_emit_event(self, service, team):
        updated_team = service.record_match_result(team, "win", 3, 1)

        assert updated_team.stats.matches_played == 1
        assert updated_team.stats.points == 3

        events = service.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], TeamStatsEvent)
        assert events[0].team_id == 1
        assert events[0].points == 3

    def test_should_reset_team_performance(self, team):
        repo = InMemoryTeamRepository()
        service = TeamDomainService(repository=repo)
        service.record_match_result(team, "loss", 0, 1)
        service.reset_team_performance(team)

        assert team.stats.matches_played == 0
        assert team.form.last_matches == []
        events = service.get_domain_events()
        assert isinstance(events[-1], TeamPerformanceResetEvent)
        assert events[-1].team_id == 1
        assert repo.updated, "Reset should be persisted"

    def test_should_calculate_league_table(self, service, team):
        second_team = Team(id=2, name="Chelsea", country="England")
        second_team.stats = TeamStats(matches_played=1, wins=1, draws=0, losses=0, goals_for=2, goals_against=0)
        team.stats = TeamStats(matches_played=1, wins=0, draws=1, losses=0, goals_for=1, goals_against=1)

        table = service.calculate_league_table([team, second_team])

        assert table[0]["team_id"] == 2
        assert table[1]["team_id"] == 1

    def test_should_clear_domain_events(self, service, team):
        service.record_match_result(team, "draw", 1, 1)
        service.clear_domain_events()

        assert service.get_domain_events() == []

    def test_should_persist_changes_via_repository(self, team):
        repo = InMemoryTeamRepository()
        service = TeamDomainService(repository=repo)

        service.record_match_result(team, "win", 2, 0)
        assert repo.updated and repo.updated[0].stats.matches_played == 1

        service.update_team_profile(team, short_name="ARS")
        service.reset_team_performance(team)

        assert len(repo.updated) >= 3
        assert repo.updated[-1].stats.matches_played == 0
