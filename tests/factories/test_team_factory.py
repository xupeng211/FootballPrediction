"""Team 模型工厂,基于真实 SQLAlchemy 模型。"""

import factory
from faker import Faker

from src.database.models.team import Team
from tests.factories.base import BaseFactory

_faker = Faker()


class TeamFactory(BaseFactory):
    """创建持久化的球队测试数据。"""

    class Meta:
        model = Team

    team_name = factory.Sequence(lambda n: f"Test Team {n}")
    team_code = factory.Sequence(lambda n: f"TT{n:03d}")
    country = factory.LazyFunction(lambda: _faker.country()[:50])
    is_active = True
    founded_year = factory.Faker("random_int", min=1900, max=2024)
    stadium = factory.LazyFunction(lambda: f"{_faker.company()} Stadium")
    api_team_id = factory.Sequence(lambda n: n + 1000)
    league_id = None

    @classmethod
    def create_batch_with_league(cls, count: int, league_id: int, **kwargs):
        """为同一联赛批量创建球队。"""
        return cls.create_batch(count, league_id=league_id, **kwargs)

    @classmethod
    def create_premier_team(cls, **kwargs):
        """创建英超风格球队。"""
        return cls(
            team_name=factory.Faker(
                "random_element",
                elements=[
                    "Manchester United",
                    "Liverpool",
                    "Arsenal",
                    "Chelsea",
                    "Manchester City",
                    "Tottenham Hotspur",
                ],
            )(),
            country="England",
            founded_year=factory.Faker("random_int", min=1870, max=1905)(),
            **kwargs,
        )

    @classmethod
    def create_la_liga_team(cls, **kwargs):
        """创建西甲风格球队。"""
        return cls(
            team_name=factory.Faker(
                "random_element",
                elements=[
                    "Real Madrid",
                    "Barcelona",
                    "Atletico Madrid",
                    "Sevilla",
                    "Real Sociedad",
                ],
            )(),
            country="Spain",
            founded_year=factory.Faker("random_int", min=1890, max=1930)(),
            **kwargs,
        )


class ChineseTeamFactory(TeamFactory):
    """中国联赛球队。"""

    class Meta:
        model = Team

    team_name = factory.Faker(
        "random_element",
        elements=[
            "北京国安",
            "上海海港",
            "广州队",
            "山东泰山",
            "大连人",
            "河南嵩山龙门",
        ],
    )
    country = "China"

    team_code = factory.Sequence(lambda n: f"CN{n:03d}")


class HistoricTeamFactory(TeamFactory):
    """历史悠久球队。"""

    class Meta:
        model = Team

    founded_year = factory.Faker("random_int", min=1880, max=1920)
    stadium = factory.LazyFunction(lambda: f"{_faker.company()} Ground")
