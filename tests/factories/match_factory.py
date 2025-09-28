"""
Factory for generating football match test data.
"""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker
from datetime import datetime, timedelta
import random

from src.database.models import Match

fake = Faker()


class MatchFactory(SQLAlchemyModelFactory):
    """Factory for generating football match data."""

    class Meta:
        model = Match
        sqlalchemy_session_persistence = "flush"

    # Basic match information
    external_match_id = factory.LazyAttribute(lambda _: f"match_{fake.uuid4().hex[:8]}")
    home_team_id = factory.LazyAttribute(lambda _: random.randint(1, 1000))
    away_team_id = factory.LazyAttribute(lambda _: random.randint(1, 1000))
    home_score = factory.LazyAttribute(lambda _: random.randint(0, 5))
    away_score = factory.LazyAttribute(lambda _: random.randint(0, 5))

    # Match status and scheduling
    match_date = factory.LazyAttribute(
        lambda _: datetime.now() - timedelta(days=random.randint(1, 365))
    )
    status = factory.Iterator([
        "scheduled", "in_progress", "finished", "postponed", "cancelled"
    ])
    competition = factory.LazyAttribute(
        lambda _: random.choice([
            "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1",
            "Champions League", "Europa League", "FA Cup", "Copa del Rey"
        ])
    )

    # Match statistics and features
    home_possession = factory.LazyAttribute(lambda _: round(random.uniform(30, 70), 1))
    away_possession = factory.LazyAttribute(lambda _: lambda obj: 100 - obj.home_possession)
    home_shots = factory.LazyAttribute(lambda _: random.randint(0, 25))
    away_shots = factory.LazyAttribute(lambda _: random.randint(0, 25))
    home_shots_on_target = factory.LazyAttribute(
        lambda obj: random.randint(0, obj.home_shots)
    )
    away_shots_on_target = factory.LazyAttribute(
        lambda obj: random.randint(0, obj.away_shots)
    )

    # Data source and metadata
    data_source = factory.Iterator(["api_football", "opta", "stats_perform", "manual"])
    processed = True
    created_at = factory.LazyAttribute(lambda _: datetime.now())
    updated_at = factory.LazyAttribute(lambda _: datetime.now())

    @factory.post_generation
    def ensure_valid_scores(obj, create, extracted, **kwargs):
        """Ensure scores are valid for finished matches."""
        if obj.status == "finished" and obj.home_score is None:
            obj.home_score = random.randint(0, 5)
        if obj.status == "finished" and obj.away_score is None:
            obj.away_score = random.randint(0, 5)


class HistoricalMatchFactory(MatchFactory):
    """Factory for generating historical match data with specific date ranges."""

    class Meta:
        model = Match
        sqlalchemy_session_persistence = "flush"

    @factory.lazy_attribute
    def match_date(self):
        """Generate a date within the last 5 years."""
        return datetime.now() - timedelta(days=random.randint(30, 1825))


class FutureMatchFactory(MatchFactory):
    """Factory for generating future match data."""

    class Meta:
        model = Match
        sqlalchemy_session_persistence = "flush"

    status = "scheduled"
    match_date = factory.LazyAttribute(
        lambda _: datetime.now() + timedelta(days=random.randint(1, 30))
    )
    home_score = None
    away_score = None


class HighScoringMatchFactory(MatchFactory):
    """Factory for generating high-scoring matches."""

    class Meta:
        model = Match
        sqlalchemy_session_persistence = "flush"

    home_score = factory.LazyAttribute(lambda _: random.randint(3, 8))
    away_score = factory.LazyAttribute(lambda _: random.randint(3, 8))
    status = "finished"


class LowScoringMatchFactory(MatchFactory):
    """Factory for generating low-scoring matches."""

    class Meta:
        model = Match
        sqlalchemy_session_persistence = "flush"

    home_score = factory.LazyAttribute(lambda _: random.randint(0, 1))
    away_score = factory.LazyAttribute(lambda _: random.randint(0, 1))
    status = "finished"


class InvalidMatchFactory:
    """Factory for generating invalid match data for testing error handling."""

    @classmethod
    def generate_missing_fields(cls):
        """Generate match data with missing required fields."""
        return {
            "home_team_id": random.randint(1, 1000),
            # Missing away_team_id and other required fields
        }

    @classmethod
    def generate_invalid_scores(cls):
        """Generate match data with invalid scores."""
        return {
            "external_match_id": f"match_{fake.uuid4().hex[:8]}",
            "home_team_id": random.randint(1, 1000),
            "away_team_id": random.randint(1, 1000),
            "home_score": -1,  # Invalid negative score
            "away_score": "invalid",  # Non-numeric score
            "match_date": datetime.now().isoformat(),
            "status": "finished"
        }

    @classmethod
    def generate_future_historical_match(cls):
        """Generate a match with future date but finished status."""
        return {
            "external_match_id": f"match_{fake.uuid4().hex[:8]}",
            "home_team_id": random.randint(1, 1000),
            "away_team_id": random.randint(1, 1000),
            "home_score": 2,
            "away_score": 1,
            "match_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "status": "finished"  # Inconsistent: finished match in future
        }