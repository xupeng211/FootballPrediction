"""League 模型工厂。"""

import factory

from tests.factories.base import BaseFactory
from src.database.models.league import League


class LeagueFactory(BaseFactory):
    """创建持久化联赛数据。"""

    class Meta:
        model = League

    league_name = factory.Sequence(lambda n: f"Test League {n}")
    league_code = factory.Sequence(lambda n: f"TL{n:03d}")
    country = factory.Faker("country")
    level = 1
    is_active = True
    api_league_id = factory.Sequence(lambda n: n + 500)
    season_start_month = 8
    season_end_month = 5

    @classmethod
    def create_premier_league(cls, **kwargs):
        return cls(
            league_name="Premier League",
            country="England",
            level=1,
            **kwargs,
        )

    @classmethod
    def create_la_liga(cls, **kwargs):
        return cls(
            league_name="La Liga",
            country="Spain",
            level=1,
            **kwargs,
        )

    @classmethod
    def create_inactive_league(cls, **kwargs):
        return cls(is_active=False, level=2, **kwargs)


class InternationalLeagueFactory(LeagueFactory):
    """国际赛事联赛。"""

    class Meta:
        model = League

    country = "Multiple"

    @classmethod
    def create_champions_league(cls, **kwargs):
        return cls(
            league_name="UEFA Champions League",
            level=1,
            **kwargs,
        )

    @classmethod
    def create_world_cup(cls, **kwargs):
        return cls(
            league_name="FIFA World Cup",
            is_active=False,
            **kwargs,
        )
