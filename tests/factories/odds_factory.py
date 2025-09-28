"""
Factory for generating betting odds test data.
"""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker
from datetime import datetime, timedelta
import random

from src.database.models import Odds

fake = Faker()


class OddsFactory(SQLAlchemyModelFactory):
    """Factory for generating betting odds data."""

    class Meta:
        model = Odds
        sqlalchemy_session_persistence = "flush"

    # Basic odds information
    match_id = factory.LazyAttribute(lambda _: random.randint(1, 10000))
    bookmaker = factory.LazyAttribute(
        lambda _: random.choice([
            "Bet365", "William Hill", "Ladbrokes", "Paddy Power", "Betfair",
            "Sky Bet", "Coral", "BetVictor", "Unibet", "888sport"
        ])
    )

    # Market odds (1X2 market)
    home_win = factory.LazyAttribute(lambda _: round(random.uniform(1.5, 5.0), 2))
    draw = factory.LazyAttribute(lambda _: round(random.uniform(2.5, 4.5), 2))
    away_win = factory.LazyAttribute(lambda _: round(random.uniform(1.5, 5.0), 2))

    # Asian handicaps and totals
    asian_handicap_home = factory.LazyAttribute(lambda _: round(random.uniform(-2.0, 2.0), 1))
    asian_handicap_away = factory.LazyAttribute(lambda _: round(random.uniform(-2.0, 2.0), 1))
    over_under = factory.LazyAttribute(lambda _: round(random.uniform(2.0, 3.5), 1))
    over_odds = factory.LazyAttribute(lambda _: round(random.uniform(1.7, 2.2), 2))
    under_odds = factory.LazyAttribute(lambda _: round(random.uniform(1.7, 2.2), 2))

    # Both teams to score
    btts_yes = factory.LazyAttribute(lambda _: round(random.uniform(1.6, 2.2), 2))
    btts_no = factory.LazyAttribute(lambda _: round(random.uniform(1.6, 2.2), 2))

    # Correct score (sample)
    correct_score_home = factory.LazyAttribute(
        lambda _: random.choice([1.0, 1.2, 1.5, 2.0, 2.5, 3.0])
    )
    correct_score_away = factory.LazyAttribute(
        lambda _: random.choice([1.0, 1.2, 1.5, 2.0, 2.5, 3.0])
    )

    # Double chance
    home_win_or_draw = factory.LazyAttribute(lambda _: round(random.uniform(1.1, 1.5), 2))
    home_win_or_away = factory.LazyAttribute(lambda _: round(random.uniform(1.2, 1.8), 2))
    draw_or_away = factory.LazyAttribute(lambda _: round(random.uniform(1.2, 1.8), 2))

    # Timestamp and data source
    timestamp = factory.LazyAttribute(
        lambda _: datetime.now() - timedelta(hours=random.randint(1, 168))
    )
    data_source = factory.Iterator(["api_football", "oddschecker", "betfair", "manual"])

    @factory.post_generation
    def ensure_valid_odds(obj, create, extracted, **kwargs):
        """Ensure odds have reasonable mathematical relationships."""
        # Ensure home_win, draw, away_win have reasonable total implied probability
        total_implied = 1/obj.home_win + 1/obj.draw + 1/obj.away_win
        if total_implied > 1.2:  # Adjust if bookmaker margin is too high
            adjustment_factor = 1.1 / total_implied
            obj.home_win = round(obj.home_win * adjustment_factor, 2)
            obj.draw = round(obj.draw * adjustment_factor, 2)
            obj.away_win = round(obj.away_win * adjustment_factor, 2)


class PreMatchOddsFactory(OddsFactory):
    """Factory for generating pre-match odds with realistic timing."""

    class Meta:
        model = Odds
        sqlalchemy_session_persistence = "flush"

    @factory.lazy_attribute
    def timestamp(self):
        """Generate timestamp 1-7 days before match."""
        return datetime.now() - timedelta(days=random.randint(1, 7))


class LiveOddsFactory(OddsFactory):
    """Factory for generating live in-play odds."""

    class Meta:
        model = Odds
        sqlalchemy_session_persistence = "flush"

    @factory.lazy_attribute
    def timestamp(self):
        """Generate timestamp within the last hour."""
        return datetime.now() - timedelta(minutes=random.randint(1, 60))


class HighProbabilityHomeWinFactory(OddsFactory):
    """Factory for generating odds with high home win probability."""

    class Meta:
        model = Odds
        sqlalchemy_session_persistence = "flush"

    home_win = factory.LazyAttribute(lambda _: round(random.uniform(1.2, 1.8), 2))
    draw = factory.LazyAttribute(lambda _: round(random.uniform(3.0, 4.0), 2))
    away_win = factory.LazyAttribute(lambda _: round(random.uniform(4.0, 8.0), 2))


class BalancedOddsFactory(OddsFactory):
    """Factory for generating balanced odds (close match)."""

    class Meta:
        model = Odds
        sqlalchemy_session_persistence = "flush"

    home_win = factory.LazyAttribute(lambda _: round(random.uniform(2.2, 2.8), 2))
    draw = factory.LazyAttribute(lambda _: round(random.uniform(3.0, 3.5), 2))
    away_win = factory.LazyAttribute(lambda _: round(random.uniform(2.2, 2.8), 2))


class InvalidOddsFactory:
    """Factory for generating invalid odds data for testing error handling."""

    @classmethod
    def generate_negative_odds(cls):
        """Generate odds with negative values."""
        return {
            "match_id": random.randint(1, 10000),
            "bookmaker": "InvalidBookmaker",
            "home_win": -2.50,  # Invalid negative odds
            "draw": 3.40,
            "away_win": 3.80,
            "timestamp": datetime.now().isoformat()
        }

    @classmethod
    def generate_zero_odds(cls):
        """Generate odds with zero values."""
        return {
            "match_id": random.randint(1, 10000),
            "bookmaker": "ZeroOddsBookmaker",
            "home_win": 0.0,  # Invalid zero odds
            "draw": 0.0,
            "away_win": 0.0,
            "timestamp": datetime.now().isoformat()
        }

    @classmethod
    def generate_unrealistic_odds(cls):
        """Generate unrealistic odds that don't make mathematical sense."""
        return {
            "match_id": random.randint(1, 10000),
            "bookmaker": "UnrealisticBookmaker",
            "home_win": 1.01,  # Too low
            "draw": 1.01,    # Too low
            "away_win": 1.01, # Too low
            "timestamp": datetime.now().isoformat()
        }

    @classmethod
    def generate_non_numeric_odds(cls):
        """Generate odds with non-numeric values."""
        return {
            "match_id": random.randint(1, 10000),
            "bookmaker": "StringOddsBookmaker",
            "home_win": "high",     # Non-numeric
            "draw": "medium",     # Non-numeric
            "away_win": "low",     # Non-numeric
            "timestamp": datetime.now().isoformat()
        }