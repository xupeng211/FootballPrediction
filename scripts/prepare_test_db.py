#!/usr/bin/env python3
"""Prepare the integration database for CI runs.

- Runs Alembic migrations so that slow / integration test suites start with an
  up-to-date schema.
- Seeds a small amount of deterministic reference data that integration tests
  can rely on without leaking into real environments.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Ensure repository root is importable when executed from CI working dir
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(ROOT))

from src.database.base import Base  # noqa: E402
from src.database.config import get_test_database_config  # noqa: E402
from src.database.models.league import League  # noqa: E402
from src.database.models.match import Match, MatchStatus  # noqa: E402
from src.database.models.team import Team  # noqa: E402

logger = logging.getLogger("prepare_test_db")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SEED_LEAGUE_ID = 99001
SEED_HOME_TEAM_ID = 99011
SEED_AWAY_TEAM_ID = 99012
SEED_MATCH_ID = 99021


async def seed_reference_data(session: AsyncSession) -> None:
    """Insert deterministic reference data if it does not exist."""
    league = await session.get(League, SEED_LEAGUE_ID)
    if not league:
        league = League(
            id=SEED_LEAGUE_ID,
            league_name="Synthetic Premier League",
            league_code="SYN",
            country="Synthetic",
            level=1,
            api_league_id=SEED_LEAGUE_ID,
        )
        session.add(league)
        logger.info("Seeded synthetic league %s", league.league_name)

    # Ensure two teams exist for integration flows
    home_team = await session.get(Team, SEED_HOME_TEAM_ID)
    if not home_team:
        home_team = Team(
            id=SEED_HOME_TEAM_ID,
            team_name="Synthetic United",
            team_code="SYN-U",
            country="Synthetic",
            league_id=SEED_LEAGUE_ID,
            founded_year=2000,
            stadium="Synthetic Arena",
        )
        session.add(home_team)
        logger.info("Seeded home team %s", home_team.team_name)

    away_team = await session.get(Team, SEED_AWAY_TEAM_ID)
    if not away_team:
        away_team = Team(
            id=SEED_AWAY_TEAM_ID,
            team_name="Synthetic City",
            team_code="SYN-C",
            country="Synthetic",
            league_id=SEED_LEAGUE_ID,
            founded_year=2001,
            stadium="Synthetic Dome",
        )
        session.add(away_team)
        logger.info("Seeded away team %s", away_team.team_name)

    match = await session.get(Match, SEED_MATCH_ID)
    if not match:
        match = Match(
            id=SEED_MATCH_ID,
            home_team_id=SEED_HOME_TEAM_ID,
            away_team_id=SEED_AWAY_TEAM_ID,
            league_id=SEED_LEAGUE_ID,
            season="2024/2025",
            match_time=datetime.utcnow() + timedelta(days=7),
            match_status=MatchStatus.SCHEDULED,
            venue="Synthetic Arena",
            referee="Synthetic Ref",
        )
        session.add(match)
        logger.info("Seeded synthetic match %s", match.id)

    await session.commit()

    # Validate counts for logging purposes
    team_count = await session.scalar(select(func.count(Team.id)))
    league_count = await session.scalar(select(func.count(League.id)))
    logger.info(
        "Reference data totals → leagues: %s, teams: %s", league_count, team_count
    )


def run_migrations(db_config) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "src/database/migrations"))
    config.set_main_option("sqlalchemy.url", db_config.sync_url)
    command.upgrade(config, "head")
    logger.info("Alembic upgrade head completed")


def ensure_schema(db_config) -> None:
    """Ensure all ORM models have backing tables (fallback for empty databases)."""
    engine = create_engine(db_config.sync_url, future=True)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("SQLAlchemy metadata create_all completed")
    finally:
        engine.dispose()


async def main() -> None:
    os.environ.setdefault("ENVIRONMENT", "test")
    db_config = get_test_database_config()
    run_migrations(db_config)
    ensure_schema(db_config)

    engine = create_async_engine(db_config.async_url, future=True)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        await seed_reference_data(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
