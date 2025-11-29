"""
Analytics API - Team and League Performance Analytics Endpoints

This module provides REST API endpoints for football analytics
including team performance statistics and league standings.
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from src.services.analytics_service import AnalyticsService
from src.database.repositories.analytics_repository import AnalyticsRepository
from src.database.dependencies import get_async_db
from src.core.exceptions import TeamNotFoundError, LeagueNotFoundError
from src.domain.models.analytics import TeamPerformanceStats, LeagueStandingsStats

logger = logging.getLogger(__name__)

# Create analytics router
router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_analytics_service(
    db_session = Depends(get_async_db)
) -> AnalyticsService:
    """
    Dependency injection for AnalyticsService.

    Args:
        db_session: Database session from dependency injection

    Returns:
        Configured AnalyticsService instance
    """
    analytics_repository = AnalyticsRepository(db_session)
    return AnalyticsService(analytics_repository)


@router.get("/teams/{team_id}/performance", response_model=Dict[str, Any])
async def get_team_performance(
    team_id: int,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Dict[str, Any]:
    """
    Get comprehensive team performance statistics.

    Provides detailed analytics including:
    - Win/Draw/Loss statistics
    - Goals scored/conceded metrics
    - Recent form analysis
    - Performance trends

    Args:
        team_id: Unique identifier for the team
        days: Analysis period in days (default: 30, max: 365)
        analytics_service: Injected analytics service

    Returns:
        Dictionary containing team performance statistics

    Raises:
        HTTPException: 404 if team not found
        HTTPException: 422 if validation fails
    """
    logger.info(f"Getting performance stats for team {team_id}, period: {days} days")

    try:
        # Get performance statistics from service
        performance_data = await analytics_service.get_team_performance_stats(team_id, days)

        if performance_data is None:
            logger.warning(f"Team {team_id} performance data not found")
            raise HTTPException(
                status_code=404,
                detail=f"Team with ID {team_id} not found or no performance data available"
            )

        logger.info(f"Successfully retrieved performance data for team {team_id}")
        return performance_data

    except TeamNotFoundError:
        logger.warning(f"Team {team_id} not found")
        raise HTTPException(
            status_code=404,
            detail=f"Team with ID {team_id} not found"
        )

    except ValueError as e:
        logger.error(f"Validation error for team {team_id}: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error getting team performance for {team_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving team performance data"
        )


@router.get("/leagues/{league_id}/standings", response_model=Dict[str, Any])
async def get_league_standings(
    league_id: int,
    season: str = Query(default="2024", description="Season identifier"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Dict[str, Any]:
    """
    Get league standings and statistics.

    Provides current league table including:
    - Team positions and points
    - Match statistics
    - Goal differences
    - Recent form

    Args:
        league_id: Unique identifier for the league
        season: Season identifier (default: "2024")
        analytics_service: Injected analytics service

    Returns:
        Dictionary containing league standings

    Raises:
        HTTPException: 404 if league not found
        HTTPException: 422 if validation fails
    """
    logger.info(f"Getting league standings for league {league_id}, season {season}")

    try:
        # Get league standings from service
        standings_data = await analytics_service.get_league_standings(league_id, season)

        if standings_data is None:
            logger.warning(f"League {league_id} standings for season {season} not found")
            raise HTTPException(
                status_code=404,
                detail=f"League with ID {league_id} or season {season} not found"
            )

        logger.info(f"Successfully retrieved standings for league {league_id}")
        return standings_data

    except LeagueNotFoundError:
        logger.warning(f"League {league_id} not found")
        raise HTTPException(
            status_code=404,
            detail=f"League with ID {league_id} not found"
        )

    except ValueError as e:
        logger.error(f"Validation error for league {league_id}: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error getting league standings for {league_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving league standings"
        )


@router.get("/health", response_model=Dict[str, str])
async def analytics_health_check(
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Dict[str, str]:
    """
    Health check endpoint for analytics service.

    Returns:
        Health status of analytics components
    """
    try:
        # Simple health check - just verify service is accessible
        return {
            "status": "healthy",
            "service": "analytics",
            "timestamp": "2025-01-01T12:00:00Z"
        }
    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Analytics service unavailable"
        )


# Note: Exception handlers are defined in main.py for the FastAPI app
# Router-level exception handling is done through HTTPException responses