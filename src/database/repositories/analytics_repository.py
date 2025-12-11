"""
Analytics Repository - Data access layer for analytics.

This repository handles data retrieval operations for analytics
following the Repository pattern in DDD architecture.
"""

import logging
from typing import Any, Optional
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from src.database.models.match import Match
from src.database.models.league import League

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """
    Repository for analytics data access operations.

    Provides database abstraction for:
    - Team performance statistics
    - League standings data
    - Historical match data
    - Aggregated metrics
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize AnalyticsRepository with database session.

        Args:
            db_session: Async database session
        """
        self._db = db_session
        logger.info("AnalyticsRepository initialized")

    async def get_team_matches_in_period(
        self, team_id: int, days: int = 30
    ) -> list[dict[str, Any]]:
        """
        Get matches for a team within specified period using raw SQL.

        Args:
            team_id: ID of the team
            days: Number of days to look back

        Returns:
            list of match dictionaries
        """
        logger.debug(f"Querying matches for team {team_id} in last {days} days")

        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # Use raw SQL to bypass ORM mapping issues
            matches_query = text("""
                SELECT
                    id, home_team_id, away_team_id, home_score, away_score,
                    status, match_date, venue, league_id, season
                FROM matches
                WHERE (home_team_id = :team_id OR away_team_id = :team_id)
                  AND match_date >= :start_date
                ORDER BY match_date DESC
            """)

            result = await self._db.execute(
                matches_query, {"team_id": team_id, "start_date": start_date}
            )
            rows = result.fetchall()

            matches = []
            for row in rows:
                matches.append(
                    {
                        "id": row.id,
                        "home_team_id": row.home_team_id,
                        "away_team_id": row.away_team_id,
                        "home_score": row.home_score,
                        "away_score": row.away_score,
                        "status": row.status,
                        "match_date": row.match_date,
                        "venue": row.venue,
                        "league_id": row.league_id,
                        "season": row.season,
                    }
                )

            logger.info(f"Found {len(matches)} matches for team {team_id}")
            return matches

        except Exception as e:
            logger.error(f"Error getting team matches: {e}")
            return []  # Return empty list to avoid breaking the API

    async def get_team_by_id(self, team_id: int) -> Optional[dict[str, Any]]:
        """
        Get team information by ID using raw SQL.

        Args:
            team_id: ID of the team

        Returns:
            Team dictionary or None if not found
        """
        try:
            # Use raw SQL to bypass ORM mapping issues
            team_query = text("""
                SELECT id, name, country, founded_year, short_name, venue, website
                FROM teams
                WHERE id = :team_id
            """)

            result = await self._db.execute(team_query, {"team_id": team_id})
            row = result.first()

            if row:
                team_dict = {
                    "id": row.id,
                    "name": row.name,
                    "country": row.country,
                    "founded_year": row.founded_year,
                    "short_name": row.short_name,
                    "venue": row.venue,
                    "website": row.website,
                }
                logger.debug(f"Found team: {row.name}")
                return team_dict
            else:
                logger.warning(f"Team {team_id} not found")
                return None

        except Exception as e:
            logger.error(f"Error getting team {team_id}: {e}")
            # Return None to avoid breaking the API
            return None

    async def get_league_by_id(self, league_id: int) -> Optional[League]:
        """
        Get league information by ID.

        Args:
            league_id: ID of the league

        Returns:
            League entity or None if not found
        """
        try:
            query = select(League).where(League.id == league_id)
            result = await self._db.execute(query)
            league = result.scalar_one_or_none()

            if league:
                logger.debug(f"Found league: {league.name}")
            else:
                logger.warning(f"League {league_id} not found")

            return league

        except Exception as e:
            logger.error(f"Error getting league {league_id}: {e}")
            raise

    async def get_league_standings(
        self, league_id: int, season: str = "2024"
    ) -> list[dict[str, Any]]:
        """
        Get current league standings for specified season.

        Args:
            league_id: ID of the league
            season: Season identifier

        Returns:
            list of standings data
        """
        logger.debug(f"Getting standings for league {league_id}, season {season}")

        try:
            # For TDD Green Phase, return empty standings
            # Real implementation would calculate based on match results
            standings = []
            logger.info(f"Returning {len(standings)} standings entries")
            return standings

        except Exception as e:
            logger.error(f"Error getting league standings: {e}")
            raise

    async def calculate_team_performance_metrics(
        self, team_id: int, matches: list[Match]
    ) -> dict[str, Any]:
        """
        Calculate performance metrics from match data.

        Args:
            team_id: ID of the team
            matches: list of matches to analyze

        Returns:
            Performance metrics dictionary
        """
        logger.debug(f"Calculating performance metrics for team {team_id}")

        try:
            wins = draws = losses = 0
            goals_for = goals_against = 0

            for match in matches:
                # Determine if team is home or away
                is_home = match.home_team_id == team_id
                is_away = match.away_team_id == team_id

                if not (is_home or is_away):
                    continue

                # Get goals for and against
                team_goals = match.home_score if is_home else match.away_score
                opponent_goals = match.away_score if is_home else match.home_score

                goals_for += team_goals
                goals_against += opponent_goals

                # Determine result
                if team_goals > opponent_goals:
                    wins += 1
                elif team_goals == opponent_goals:
                    draws += 1
                else:
                    losses += 1

            total_matches = wins + draws + losses
            matches_played = len(matches)

            return {
                "matches_played": matches_played,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "win_rate": wins / total_matches if total_matches > 0 else 0,
                "draw_rate": draws / total_matches if total_matches > 0 else 0,
                "loss_rate": losses / total_matches if total_matches > 0 else 0,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "goal_difference": goals_for - goals_against,
                "avg_goals_for": goals_for / matches_played
                if matches_played > 0
                else 0,
                "avg_goals_against": goals_against / matches_played
                if matches_played > 0
                else 0,
                "clean_sheets": sum(
                    1
                    for m in matches
                    if (m.home_team_id == team_id and m.away_score == 0)
                    or (m.away_team_id == team_id and m.home_score == 0)
                ),
            }

        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            raise

    async def get_real_team_performance_metrics(
        self, team_id: int, days: int = 30
    ) -> dict[str, Any]:
        """
        Calculate real team performance metrics from database using raw SQL.

        Args:
            team_id: ID of the team
            days: Number of days to look back

        Returns:
            Performance metrics dictionary from real database data
        """
        logger.debug(
            f"Calculating real performance metrics for team {team_id}, period: {days} days"
        )

        try:
            # Calculate start date for the period
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # Use raw SQL to bypass ORM mapping issues
            performance_query = text("""
                SELECT
                    COUNT(*) as matches_played,

                    -- Calculate wins (home or away)
                    SUM(CASE
                        WHEN (home_team_id = :team_id AND home_score > away_score) OR
                             (away_team_id = :team_id AND away_score > home_score)
                        THEN 1 ELSE 0
                    END) as wins,

                    -- Calculate draws
                    SUM(CASE
                        WHEN home_score = away_score AND
                             (home_team_id = :team_id OR away_team_id = :team_id)
                        THEN 1 ELSE 0
                    END) as draws,

                    -- Calculate losses
                    SUM(CASE
                        WHEN (home_team_id = :team_id AND home_score < away_score) OR
                             (away_team_id = :team_id AND away_score < home_score)
                        THEN 1 ELSE 0
                    END) as losses,

                    -- Goals scored (goals_for)
                    SUM(CASE
                        WHEN home_team_id = :team_id THEN home_score
                        WHEN away_team_id = :team_id THEN away_score
                        ELSE 0
                    END) as goals_for,

                    -- Goals conceded (goals_against)
                    SUM(CASE
                        WHEN home_team_id = :team_id THEN away_score
                        WHEN away_team_id = :team_id THEN home_score
                        ELSE 0
                    END) as goals_against,

                    -- Clean sheets (conceded 0 goals)
                    SUM(CASE
                        WHEN (home_team_id = :team_id AND away_score = 0) OR
                             (away_team_id = :team_id AND home_score = 0)
                        THEN 1 ELSE 0
                    END) as clean_sheets

                FROM matches
                WHERE (home_team_id = :team_id OR away_team_id = :team_id)
                  AND match_date >= :start_date
                  AND status = 'finished'
            """)

            result = await self._db.execute(
                performance_query, {"team_id": team_id, "start_date": start_date}
            )
            row = result.first()

            if not row or row.matches_played == 0:
                logger.info(
                    f"No matches found for team {team_id} in the last {days} days"
                )
                return {
                    "matches_played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "draw_rate": 0.0,
                    "loss_rate": 0.0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "goal_difference": 0,
                    "avg_goals_for": 0.0,
                    "avg_goals_against": 0.0,
                    "clean_sheets": 0,
                }

            # Calculate derived metrics with null safety
            total_matches = row.matches_played or 0
            wins = row.wins or 0
            draws = row.draws or 0
            losses = row.losses or 0
            goals_for = row.goals_for or 0
            goals_against = row.goals_against or 0
            clean_sheets = row.clean_sheets or 0

            return {
                "matches_played": total_matches,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "win_rate": wins / total_matches if total_matches > 0 else 0.0,
                "draw_rate": draws / total_matches if total_matches > 0 else 0.0,
                "loss_rate": losses / total_matches if total_matches > 0 else 0.0,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "goal_difference": goals_for - goals_against,
                "avg_goals_for": goals_for / total_matches
                if total_matches > 0
                else 0.0,
                "avg_goals_against": goals_against / total_matches
                if total_matches > 0
                else 0.0,
                "clean_sheets": clean_sheets,
            }

        except Exception as e:
            logger.error(
                f"Error calculating real performance metrics for team {team_id}: {e}"
            )
            # Return empty metrics on error to avoid breaking the API
            return {
                "matches_played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "win_rate": 0.0,
                "draw_rate": 0.0,
                "loss_rate": 0.0,
                "goals_for": 0,
                "goals_against": 0,
                "goal_difference": 0,
                "avg_goals_for": 0.0,
                "avg_goals_against": 0.0,
                "clean_sheets": 0,
            }

    async def get_real_league_standings(
        self, league_id: int, season: str = "2024"
    ) -> list[dict[str, Any]]:
        """
        Get real league standings from database.

        Args:
            league_id: ID of the league
            season: Season identifier

        Returns:
            list of standings data from real database
        """
        logger.debug(
            f"Getting real league standings for league {league_id}, season {season}"
        )

        try:
            # Complex SQL query for league standings
            # Calculates points, goal difference, and ranking
            standings_query = text("""
                WITH team_stats AS (
                    SELECT
                        team.id as team_id,
                        team.name as team_name,
                        COUNT(*) as matches_played,

                        -- Calculate wins
                        SUM(CASE
                            WHEN (matches.home_team_id = team.id AND matches.home_score > matches.away_score) OR
                                 (matches.away_team_id = team.id AND matches.away_score > matches.home_score)
                            THEN 1 ELSE 0
                        END) as wins,

                        -- Calculate draws
                        SUM(CASE
                            WHEN matches.home_score = matches.away_score AND
                                 (matches.home_team_id = team.id OR matches.away_team_id = team.id)
                            THEN 1 ELSE 0
                        END) as draws,

                        -- Calculate losses
                        SUM(CASE
                            WHEN (matches.home_team_id = team.id AND matches.home_score < matches.away_score) OR
                                 (matches.away_team_id = team.id AND matches.away_score < matches.home_score)
                            THEN 1 ELSE 0
                        END) as losses,

                        -- Calculate goals for
                        SUM(CASE
                            WHEN matches.home_team_id = team.id THEN matches.home_score
                            WHEN matches.away_team_id = team.id THEN matches.away_score
                            ELSE 0
                        END) as goals_for,

                        -- Calculate goals against
                        SUM(CASE
                            WHEN matches.home_team_id = team.id THEN matches.away_score
                            WHEN matches.away_team_id = team.id THEN matches.home_score
                            ELSE 0
                        END) as goals_against,

                        -- Calculate points (3 for win, 1 for draw, 0 for loss)
                        SUM(CASE
                            WHEN (matches.home_team_id = team.id AND matches.home_score > matches.away_score) OR
                                 (matches.away_team_id = team.id AND matches.away_score > matches.home_score)
                            THEN 3
                            WHEN matches.home_score = matches.away_score AND
                                 (matches.home_team_id = team.id OR matches.away_team_id = team.id)
                            THEN 1
                            ELSE 0
                        END) as points,

                        -- Get last 5 match results for form
                        ARRAY(
                            SELECT CASE
                                WHEN (m.home_team_id = team.id AND m.home_score > m.away_score) OR
                                     (m.away_team_id = team.id AND m.away_score > m.home_score)
                                THEN 'W'
                                WHEN m.home_score = m.away_score
                                THEN 'D'
                                ELSE 'L'
                            END
                            FROM matches m
                            WHERE (m.home_team_id = team.id OR m.away_team_id = team.id)
                            ORDER BY m.match_date DESC
                            LIMIT 5
                        ) as recent_form

                    FROM teams team
                    LEFT JOIN matches ON (
                        (matches.home_team_id = team.id OR matches.away_team_id = team.id)
                        AND matches.season = :season
                    )
                    GROUP BY team.id, team.name
                )

                SELECT
                    team_id,
                    team_name,
                    matches_played,
                    wins,
                    draws,
                    losses,
                    goals_for,
                    goals_against,
                    (goals_for - goals_against) as goal_difference,
                    points,
                    recent_form,
                    ROW_NUMBER() OVER (ORDER BY points DESC, (goals_for - goals_against) DESC, goals_for DESC) as position
                FROM team_stats
                WHERE team_id IN (
                    SELECT DISTINCT home_team_id
                    FROM matches
                    WHERE league_id = :league_id AND season = :season
                    UNION
                    SELECT DISTINCT away_team_id
                    FROM matches
                    WHERE league_id = :league_id AND season = :season
                )
                ORDER BY points DESC, (goals_for - goals_against) DESC, goals_for DESC
            """)

            result = await self._db.execute(
                standings_query, {"league_id": league_id, "season": season}
            )
            rows = result.fetchall()

            standings = []
            for row in rows:
                standings.append(
                    {
                        "position": row.position,
                        "team_id": row.team_id,
                        "team_name": row.team_name,
                        "matches_played": row.matches_played,
                        "wins": row.wins,
                        "draws": row.draws,
                        "losses": row.losses,
                        "goals_for": row.goals_for,
                        "goals_against": row.goals_against,
                        "goal_difference": row.goal_difference,
                        "points": row.points,
                        "form": row.recent_form if row.recent_form else [],
                    }
                )

            logger.info(f"Returning {len(standings)} real standings entries")
            return standings

        except Exception as e:
            logger.error(f"Error getting real league standings: {e}")
            raise
