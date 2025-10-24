"""Odds 模型工厂。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import factory

from faker import Faker

from tests.factories.base import BaseFactory
from src.database.models.odds import MarketType, Odds
from src.database.models.match import Match


_faker = Faker()


class OddsFactory(BaseFactory):
    """创建通用的胜平负赔率记录。"""

    class Meta:
        model = Odds

    match = factory.SubFactory("tests.factories.match_factory.MatchFactory")
    bookmaker = factory.LazyFunction(lambda: f"{_faker.company()} Betting")
    market_type = MarketType.ONE_X_TWO
    home_odds = factory.LazyFunction(lambda: Decimal("2.40"))
    draw_odds = factory.LazyFunction(lambda: Decimal("3.20"))
    away_odds = factory.LazyFunction(lambda: Decimal("2.80"))
    collected_at = factory.LazyFunction(datetime.utcnow)

    @classmethod
    def _attach_match(cls, payload: dict) -> dict:
        if "match" in payload:
            return payload

        match_id = payload.get("match_id")
        if match_id is None:
            return payload

        session = cls._meta.sqlalchemy_session
        payload["match"] = session.get(Match, match_id) if session else None
        return payload

    @classmethod
    def create_for_match(cls, match_id: int, **kwargs) -> Odds:
        _data = cls._attach_match({"match_id": match_id, **kwargs})
        return cls(**data)

    @classmethod
    def create_bet365_odds(cls, **kwargs) -> Odds:
        _data = cls._attach_match({"bookmaker": "Bet365", **kwargs})
        return cls(**data)

    @classmethod
    def create_william_hill_odds(cls, **kwargs) -> Odds:
        _data = cls._attach_match({"bookmaker": "William Hill", **kwargs})
        return cls(**data)

    @classmethod
    def create_betfair_odds(cls, **kwargs) -> Odds:
        _data = cls._attach_match({"bookmaker": "Betfair", **kwargs})
        return cls(**data)

    @classmethod
    def create_balanced_odds(cls, **kwargs) -> Odds:
        _data = cls._attach_match(
            {
                "home_odds": Decimal("2.50"),
                "draw_odds": Decimal("2.50"),
                "away_odds": Decimal("2.50"),
                **kwargs,
            }
        )
        return cls(**data)


class AsianOddsFactory(OddsFactory):
    """亚洲盘市场。"""

    class Meta:
        model = Odds

    market_type = MarketType.ASIAN_HANDICAP
    line_value = factory.LazyFunction(lambda: Decimal("0.50"))
    home_odds = factory.LazyFunction(lambda: Decimal("1.90"))
    away_odds = factory.LazyFunction(lambda: Decimal("1.95"))


class LiveOddsFactory(OddsFactory):
    """实时赔率。"""

    class Meta:
        model = Odds

    @classmethod
    def create_live_odds(
        cls, home_score: int, away_score: int, minute: int, **kwargs
    ) -> Odds:
        base_home = Decimal("1.80") if home_score > away_score else Decimal("2.80")
        base_away = Decimal("1.80") if away_score > home_score else Decimal("2.80")
        return cls(
            home_odds=base_home,
            away_odds=base_away,
            draw_odds=Decimal("3.10"),
            collected_at=datetime.utcnow(),
            **kwargs,
        )


class BookmakerOddsFactory(OddsFactory):
    """特定博彩公司配置。"""

    class Meta:
        model = Odds

    bookmaker = "SampleBookmaker"
