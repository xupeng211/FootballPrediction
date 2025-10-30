"""Match 模型工厂,产出持久化数据以便集成测试使用。"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import factory
from faker import Faker

from src.database.models.league import League
from src.database.models.match import Match, MatchStatus
from src.database.models.team import Team
from tests.factories.base import BaseFactory

_faker = Faker()


class MatchFactory(BaseFactory):
    """创建标准联赛比赛。"""

    class Meta:
        model = Match

    home_team = factory.SubFactory("tests.factories.team_factory.TeamFactory")
    away_team = factory.SubFactory("tests.factories.team_factory.TeamFactory")
    league = factory.SubFactory("tests.factories.league_factory.LeagueFactory")
    season = factory.LazyFunction(lambda: f"{datetime.utcnow().year}-{datetime.utcnow().year + 1}")
    match_time = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(days=1))
    match_status = MatchStatus.SCHEDULED
    venue = factory.LazyFunction(lambda: f"{_faker.company()} Stadium")
    referee = factory.Faker("name")
    weather = factory.Faker("word")
    home_score = None
    away_score = None
    home_ht_score = None
    away_ht_score = None
    minute = None

    @factory.post_generation
    def _sync_related(obj, create, extracted, **_):
        if not create:
            return
        if obj.league and obj.home_team and obj.home_team.league_id is None:
            obj.home_team.league = obj.league
        if obj.league and obj.away_team and obj.away_team.league_id is None:
            obj.away_team.league = obj.league

    @classmethod
    def create_with_teams(cls, home_team_id: int, away_team_id: int, league_id: int, **kwargs):
        session = cls._meta.sqlalchemy_session
        if session is None:
            raise RuntimeError("MatchFactory requires an active SQLAlchemy session")

        home_team = session.get(Team, home_team_id)
        away_team = session.get(Team, away_team_id)
        league = session.get(League, league_id)

        return cls(home_team=home_team, away_team=away_team, league=league, **kwargs)

    @classmethod
    def create_finished_match(cls, **kwargs):
        home_score = random.randint(0, 5)
        away_score = random.randint(0, 5)
        ids = {}
        for key in ("home_team_id", "away_team_id", "league_id"):
            if key in kwargs:
                ids[key] = kwargs.pop(key)

        base_kwargs = dict(
            match_status=MatchStatus.FINISHED,
            home_score=home_score,
            away_score=away_score,
            home_ht_score=random.randint(0, home_score or 0),
            away_ht_score=random.randint(0, away_score or 0),
            match_time=datetime.utcnow() - timedelta(days=1),
        )
        base_kwargs.update(kwargs)

        if ids:
            return cls.create_with_teams(**ids, **base_kwargs)

        return cls(**base_kwargs)

    @classmethod
    def create_live_match(cls, **kwargs):
        home_score = random.randint(0, 3)
        away_score = random.randint(0, 3)
        ids = {}
        for key in ("home_team_id", "away_team_id", "league_id"):
            if key in kwargs:
                ids[key] = kwargs.pop(key)

        base_kwargs = dict(
            match_status=MatchStatus.LIVE,
            home_score=home_score,
            away_score=away_score,
            minute=random.randint(1, 90),
            match_time=datetime.utcnow(),
        )
        base_kwargs.update(kwargs)

        if ids:
            return cls.create_with_teams(**ids, **base_kwargs)

        return cls(**base_kwargs)

    @classmethod
    def create_postponed_match(cls, **kwargs):
        return cls(match_status=MatchStatus.CANCELLED, **kwargs)

    @classmethod
    def create_season_batch(
        cls, league_id: int, team_ids: list[int], start_date: datetime, **kwargs
    ) -> list[Match]:
        matches: list[Match] = []
        team_count = len(team_ids)
        session = cls._meta.sqlalchemy_session
        if session is None:
            raise RuntimeError("MatchFactory requires an active SQLAlchemy session")

        league = session.get(League, league_id)

        for round_index in range(2):
            for i in range(team_count):
                for j in range(i + 1, team_count):
                    matches.append(
                        cls(
                            home_team=session.get(Team, team_ids[i]),
                            away_team=session.get(Team, team_ids[j]),
                            league=league,
                            match_time=start_date
                            + timedelta(days=round_index * (team_count - 1) * 7 + i * 7),
                            **kwargs,
                        )
                    )
        return matches


class CupMatchFactory(MatchFactory):
    """杯赛场景。"""

    class Meta:
        model = Match

    match_status = MatchStatus.SCHEDULED

    @classmethod
    def create_knockout_match(cls, round_name: str, **kwargs):
        return cls(venue=f"{_faker.company()} Arena", **kwargs)
