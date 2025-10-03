import os
"""""""
Factory for generating football team test data.
"""""""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker
import random

from src.database.models import Team

fake = Faker()


class TeamFactory(SQLAlchemyModelFactory):
    """Factory for generating football team data."""""""

    class Meta = model Team
        sqlalchemy_session_persistence = os.getenv("TEAM_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_19")""""

    # Basic team information
    external_team_id = factory.LazyAttribute(lambda _: f["]team_{fake.uuid4().hex[:8]}"])": name = factory.LazyAttribute(lambda _: fake.company())": short_name = factory.LazyAttribute(lambda obj: obj.name[:3].upper())": country = factory.LazyAttribute(lambda _: fake.country())"
    league = factory.LazyAttribute(
        lambda _: random.choice(
            ["Premier League[", "]La Liga[", "]Bundesliga[", "]Serie A[", "]Ligue 1["]""""
        )
    )

    # Team statistics
    founded_year = factory.LazyAttribute(lambda _: random.randint(1880, 2020))
    stadium_name = factory.LazyAttribute(lambda _: f["]{fake.company()} Stadium["])": stadium_capacity = factory.LazyAttribute(lambda _: random.randint(20000, 90000))"""

    # Team performance metrics
    league_position = factory.LazyAttribute(lambda _: random.randint(1, 20))
    points = factory.LazyAttribute(lambda _: random.randint(0, 100))
    goals_scored = factory.LazyAttribute(lambda _: random.randint(20, 120))
    goals_conceded = factory.LazyAttribute(lambda _: random.randint(20, 120))

    # Data source and metadata
    data_source = factory.Iterator(["]api_football[", "]opta[", "]stats_perform[", "]manual["])": created_at = factory.LazyAttribute(lambda _: fake.date_time_this_year())": updated_at = factory.LazyAttribute(lambda _: fake.date_time_this_month())""

    @classmethod
    def create_batch_with_league(cls, league, size=10):
        "]""Create a batch of teams from the same league."""""""
        return [cls(league=league) for _ in range(size)]

    @classmethod
    def create_top_teams(cls, size=6):
        """Create top-performing teams."""""""
        return [
            cls(
                league_position=i + 1,
                points=random.randint(80, 100),
                goals_scored=random.randint(80, 120),
                goals_conceded=random.randint(20, 50),
            )
            for i in range(size)
        ]

    @classmethod
    def create_bottom_teams(cls, size=6):
        """Create bottom-performing teams."""""""
        return [
            cls(
                league_position=15 + i,
                points=random.randint(20, 40),
                goals_scored=random.randint(20, 50),
                goals_conceded=random.randint(80, 120),
            )
            for i in range(size)
        ]


class InvalidTeamFactory:
    """Factory for generating invalid team data for testing error handling."""""""

    @classmethod
    def generate_missing_name(cls):
        """Generate team data with missing name."""""""
        return {
            "external_team_id[": f["]team_{fake.uuid4().hex[:8]}"],""""
            "country[": fake.country(),""""
            # Missing required name field
        }

    @classmethod
    def generate_invalid_year(cls):
        "]""Generate team data with invalid founded year."""""""
        return {
            "external_team_id[": f["]team_{fake.uuid4().hex[:8]}"],""""
            "name[": fake.company(),""""
            "]founded_year[": 1800,  # Invalid year (too early)""""
            "]country[": fake.country(),""""
        }

    @classmethod
    def generate_negative_capacity(cls):
        "]""Generate team data with negative stadium capacity."""""""
        return {
            "external_team_id[": f["]team_{fake.uuid4().hex[:8]}"],""""
            "name[": fake.company(),""""
            "]stadium_capacity[": -5000,  # Invalid negative capacity[""""
            "]]country[": fake.country(),"]"""
        }
