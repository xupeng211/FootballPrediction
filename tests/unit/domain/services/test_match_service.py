from datetime import datetime, timedelta

import pytest

from src.domain.models.match import Match, MatchStatus
from src.domain.models.team import Team
from src.domain.services.match_service import MatchDomainService


@pytest.fixture
def service() -> MatchDomainService:
    return MatchDomainService()


@pytest.fixture
def home_team() -> Team:
    return Team(id=1, name="Home FC", country="England")


@pytest.fixture
def away_team() -> Team:
    return Team(id=2, name="Away FC", country="England")


class TestMatchScheduling:
    def test_should_schedule_match(self, service, home_team, away_team):
        match_time = datetime.utcnow() + timedelta(days=1)
        match = service.schedule_match(
            home_team, away_team, match_time, venue="Stadium"
        )

        assert match.home_team_id == home_team.id
        assert match.away_team_id == away_team.id
        assert match.match_date == match_time
        assert match.venue == "Stadium"

    def test_should_validate_schedule_inputs(self, service, home_team):
        with pytest.raises(ValueError):
            service.schedule_match(home_team, home_team, datetime.utcnow())

        away_without_id = Team(name="No ID", country="England")
        with pytest.raises(ValueError):
            service.schedule_match(home_team, away_without_id, datetime.utcnow())


class TestMatchLifecycle:
    def test_should_start_match_and_emit_event(self, service, home_team, away_team):
        match_time = datetime.utcnow() - timedelta(minutes=5)
        match = service.schedule_match(home_team, away_team, match_time)
        match.id = 99

        service.start_match(match)

        assert match.status == MatchStatus.LIVE
        events = service.get_domain_events()
        assert len(events) == 1
        assert events[0].match_id == 99

    def test_should_reject_start_when_time_not_reached(
        self, service, home_team, away_team
    ):
        match = service.schedule_match(
            home_team, away_team, datetime.utcnow() + timedelta(hours=1)
        )

        with pytest.raises(ValueError):
            service.start_match(match)

    def test_should_update_score_and_finish_with_event(
        self, service, home_team, away_team
    ):
        match_time = datetime.utcnow() - timedelta(minutes=5)
        match = service.schedule_match(home_team, away_team, match_time)
        match.id = 5

        service.start_match(match)
        service.update_match_score(match, 2, 1)
        service.finish_match(match)

        assert match.status == MatchStatus.FINISHED
        events = service.get_domain_events()
        assert len(events) == 2
        finished_event = events[-1]
        assert finished_event.final_score.home_score == 2

    def test_should_require_live_match_for_updates(self, service, home_team, away_team):
        match = service.schedule_match(
            home_team, away_team, datetime.utcnow() - timedelta(minutes=5)
        )

        with pytest.raises(ValueError):
            service.update_match_score(match, 1, 0)

        match.status = MatchStatus.LIVE
        with pytest.raises(ValueError):
            service.update_match_score(match, -1, 0)


class TestMatchAdjustments:
    def test_should_cancel_and_postpone_match(self, service, home_team, away_team):
        match = service.schedule_match(
            home_team, away_team, datetime.utcnow() + timedelta(days=1)
        )
        match.id = 7

        service.cancel_match(match, "heavy rain")
        assert match.status == MatchStatus.CANCELLED
        assert service.get_domain_events()[-1].reason == "heavy rain"

        new_match = service.schedule_match(
            home_team, away_team, datetime.utcnow() + timedelta(days=1)
        )
        service.postpone_match(
            new_match, datetime.utcnow() + timedelta(days=2), "broadcast"
        )
        assert new_match.status == MatchStatus.POSTPONED
        assert service.get_domain_events()[-1].reason == "broadcast"

    def test_should_prevent_invalid_cancellations_or_postpones(
        self, service, home_team, away_team
    ):
        match = service.schedule_match(
            home_team, away_team, datetime.utcnow() + timedelta(days=1)
        )
        match.status = MatchStatus.FINISHED

        with pytest.raises(ValueError):
            service.cancel_match(match, "too late")

        with pytest.raises(ValueError):
            service.postpone_match(match, datetime.utcnow(), "too late")


class TestMatchUtilities:
    def test_should_validate_schedule(self, service, home_team, away_team):
        past_match = service.schedule_match(
            home_team,
            away_team,
            datetime.utcnow() - timedelta(days=1),
            venue=None,
        )

        errors = service.validate_match_schedule(past_match)
        assert "比赛时间必须是未来时间" in errors
        assert "必须指定比赛场地" in errors

    def test_should_calculate_importance(self, service):
        match = Match(home_team_id=1, away_team_id=2, league_id=3)
        importance = service.calculate_match_importance(match, 2, 3, 20)

        assert importance > 0.5
        assert importance <= 1.0
