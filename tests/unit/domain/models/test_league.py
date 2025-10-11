from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from src.core.exceptions import DomainError
from src.domain.models.league import (
    League,
    LeagueSeason,
    LeagueSettings,
    LeagueStatus,
    LeagueType,
)


@pytest.fixture
def league() -> League:
    return League(name="Premier League", country="England", level=1)


class TestLeagueSeason:
    def test_should_validate_basic_constraints(self):
        start = datetime(2024, 8, 1)
        end = datetime(2025, 5, 31)
        season = LeagueSeason(
            season="2024-2025",
            start_date=start,
            end_date=end,
            total_rounds=38,
            current_round=10,
        )

        assert season.progress == pytest.approx(10 / 38)
        assert season.is_active is False

    def test_should_raise_when_dates_invalid(self):
        with pytest.raises(DomainError):
            LeagueSeason(
                season="2024",
                start_date=datetime(2024, 8, 1),
                end_date=datetime(2024, 7, 31),
            )

    def test_should_transition_status_through_lifecycle(self):
        season = LeagueSeason(
            season="2024",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            total_rounds=3,
        )

        season.start_season()
        assert season.is_active is True
        assert season.current_round == 1

        season.advance_round()
        assert season.current_round == 2
        assert season.status == LeagueStatus.ACTIVE

        season.advance_round()
        assert season.current_round == 3
        assert season.status == LeagueStatus.ACTIVE

        season.advance_round()
        assert season.status == LeagueStatus.COMPLETED
        assert season.current_round == 3


class TestLeagueSettings:
    def test_should_calculate_points(self):
        settings = LeagueSettings(points_for_win=3, points_for_draw=1, points_for_loss=0)
        assert settings.calculate_points(10, 5, 3) == 10 * 3 + 5 * 1

    def test_should_reject_invalid_configuration(self):
        with pytest.raises(DomainError):
            LeagueSettings(points_for_win=-1)


class TestLeague:
    def test_should_initialize_with_defaults(self, league):
        assert league.settings is not None
        assert league.is_active is True
        assert league.prestige == "顶级联赛"

    def test_should_require_name(self):
        with pytest.raises(DomainError):
            League(name="")

    def test_should_start_new_season(self, league):
        start = datetime.utcnow()
        end = start + timedelta(days=100)

        season = league.start_new_season("2024-2025", start, end)

        assert league.current_season is season
        assert season.total_rounds == league.settings.match_duration  # 默认沿用设置
        assert league.current_progress == 0.0

    def test_should_not_start_new_season_when_active(self, league):
        start = datetime.utcnow()
        end = start + timedelta(days=100)

        season = league.start_new_season("2024", start, end)
        season.start_season()

        with pytest.raises(DomainError):
            league.start_new_season("2025", start + timedelta(days=365), end + timedelta(days=365))

    def test_should_update_settings_and_calculate_revenue(self, league):
        league.update_settings(points_for_win=4, max_foreign_players=7)
        assert league.settings.points_for_win == 4
        assert league.settings.max_foreign_players == 7

        revenue = league.calculate_revenue_sharing(position=1, total_teams=20)
        assert revenue == Decimal("1000000") + Decimal("1900000")

    def test_should_raise_for_invalid_revenue_position(self, league):
        with pytest.raises(DomainError):
            league.calculate_revenue_sharing(position=0, total_teams=20)

    def test_should_serialize_and_deserialize(self, league):
        start = datetime(2024, 8, 1)
        end = datetime(2025, 5, 31)
        league.start_new_season("2024-2025", start, end)

        payload = league.to_dict()
        restored = League.from_dict(payload)

        assert restored.name == league.name
        assert restored.current_season is not None
        assert restored.settings is not None
        assert restored.current_season.season == "2024-2025"

    def test_should_validate_team_registration(self, league):
        assert league.can_team_register(team_level=2) is True
        assert league.can_team_register(team_level=6) is False
