#!/usr/bin/env python3
"""
Unit tests for data API module.

Tests for src/api/data.py module functions and endpoints.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any

from src.api.data import get_match_features, get_team_stats, get_team_recent_stats, get_dashboard_data, get_system_health
from src.database.models.match import Match
from src.database.models.team import Team
from src.database.models.features import Features
from src.database.models.predictions import Predictions
from src.database.models.odds import Odds


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_match():
    """Mock match data."""
    match = MagicMock()
    match.id = 1
    match.home_team_id = 1
    match.away_team_id = 2
    match.match_date = datetime.now()
    match.home_score = 2
    match.away_score = 1
    match.status = "completed"
    return match


@pytest.fixture
def mock_team():
    """Mock team data."""
    team = MagicMock()
    team.id = 1
    team.name = "Test Team"
    team.league = "Test League"
    team.played = 10
    team.wins = 6
    team.draws = 2
    team.losses = 2
    team.goals_for = 20
    team.goals_against = 10
    return team


@pytest.fixture
def mock_features():
    """Mock features data."""
    features = MagicMock()
    features.match_id = 1
    features.team_id = 1
    features.recent_5_wins = 3
    features.recent_5_goals_for = 8
    features.recent_5_goals_against = 4
    features.form_rating = 7.5
    return features


class TestGetMatchFeatures:
    """Test cases for get_match_features function."""

    @pytest.mark.asyncio
    async def test_get_match_features_success(self, mock_session, mock_match):
        """Test successful match features retrieval."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute function
        result = await get_match_features(1, mock_session)

        # Verify result
        assert result["match_id"] == 1
        assert "match_info" in result
        assert "features" in result
        assert "prediction" in result
        assert "odds" in result

    @pytest.mark.asyncio
    async def test_get_match_features_not_found(self, mock_session):
        """Test match features retrieval when match not found."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute function and expect exception
        with pytest.raises(Exception):
            await get_match_features(999, mock_session)

    @pytest.mark.asyncio
    async def test_get_match_features_database_error(self, mock_session):
        """Test match features retrieval with database error."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = Exception("Database connection error")

        # Execute function and expect exception
        with pytest.raises(Exception):
            await get_match_features(1, mock_session)


class TestGetTeamStats:
    """Test cases for get_team_stats function."""

    @pytest.mark.asyncio
    async def test_get_team_stats_success(self, mock_session, mock_team):
        """Test successful team stats retrieval."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_team
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute function
        result = await get_team_stats(1, mock_session)

        # Verify result
        assert result["team_id"] == 1
        assert result["team_name"] == "Test Team"
        assert "total_matches" in result
        assert "wins" in result

    @pytest.mark.asyncio
    async def test_get_team_stats_not_found(self, mock_session):
        """Test team stats retrieval when team not found."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute function and expect exception
        with pytest.raises(Exception):
            await get_team_stats(999, mock_session)


class TestGetTeamRecentStats:
    """Test cases for get_team_recent_stats function."""

    @pytest.mark.asyncio
    async def test_get_team_recent_stats_success(self, mock_session, mock_team):
        """Test successful team recent stats retrieval."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_team
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute function
        result = await get_team_recent_stats(1, 30, mock_session)

        # Verify result
        assert result["team_id"] == 1
        assert "total_matches" in result
        assert "matches" in result

    @pytest.mark.asyncio
    async def test_get_team_recent_stats_with_limit(self, mock_session, mock_team):
        """Test team recent stats retrieval with custom days limit."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_team
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute function
        result = await get_team_recent_stats(1, 5, mock_session)

        # Verify result
        assert result["team_id"] == 1
        assert result["period_days"] == 5
        assert "total_matches" in result


class TestGetDashboardData:
    """Test cases for get_dashboard_data function."""

    @pytest.mark.asyncio
    async def test_get_dashboard_data_success(self, mock_session):
        """Test successful dashboard data retrieval."""
        # Setup mock for multiple queries
        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = []

        mock_predictions_result = MagicMock()
        mock_predictions_result.scalars.return_value.all.return_value = []

        def mock_execute_side_effect(query):
            if "matches" in str(query).lower():
                return mock_matches_result
            elif "predictions" in str(query).lower():
                return mock_predictions_result
            return MagicMock()

        mock_session.execute.side_effect = mock_execute_side_effect

        # Execute function
        with patch('src.api.data.DataQualityMonitor') as mock_monitor_class, \
             patch('src.api.data.get_system_health') as mock_health:
            # Mock the DataQualityMonitor instance and its async method
            mock_monitor_instance = AsyncMock()
            mock_monitor_instance.generate_quality_report.return_value = {
                "overall_status": "healthy",
                "quality_score": 85,
                "anomalies": {"count": 0}
            }
            mock_monitor_class.return_value = mock_monitor_instance

            mock_health.return_value = {"database": "healthy", "data_collection": "healthy"}

            result = await get_dashboard_data(mock_session)

        # Verify result
        assert "generated_at" in result
        assert "today_matches" in result
        assert "predictions" in result
        assert "data_quality" in result
        assert "system_health" in result

    @pytest.mark.asyncio
    async def test_get_dashboard_data_empty_results(self, mock_session):
        """Test dashboard data retrieval with empty results."""
        # Setup mock for empty results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute function
        with patch('src.api.data.DataQualityMonitor') as mock_monitor_class, \
             patch('src.api.data.get_system_health') as mock_health:
            # Mock the DataQualityMonitor instance and its async method
            mock_monitor_instance = AsyncMock()
            mock_monitor_instance.generate_quality_report.return_value = {
                "overall_status": "healthy",
                "quality_score": 85,
                "anomalies": {"count": 0}
            }
            mock_monitor_class.return_value = mock_monitor_instance

            mock_health.return_value = {"database": "healthy", "data_collection": "healthy"}

            result = await get_dashboard_data(mock_session)

        # Verify result
        assert "generated_at" in result
        assert "today_matches" in result
        assert "predictions" in result


class TestGetSystemHealth:
    """Test cases for get_system_health function."""

    @pytest.mark.asyncio
    async def test_get_system_health_success(self, mock_session):
        """Test successful system health check."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        # Execute function
        result = await get_system_health(mock_session)

        # Verify result
        assert "database" in result
        assert "data_collection" in result
        assert "last_collection" in result

    @pytest.mark.asyncio
    async def test_get_system_health_database_error(self, mock_session):
        """Test system health check with database error."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = Exception("Database connection failed")

        # Execute function
        result = await get_system_health(mock_session)

        # Verify result
        assert "database" in result
        assert "data_collection" in result
        assert "error" in result



class TestDataAPIModule:
    """Test cases for data API module imports and router."""

    def test_module_imports(self):
        """Test that the module can be imported successfully."""
        from src.api import data
        assert hasattr(data, 'get_match_features')
        assert hasattr(data, 'get_team_stats')
        assert hasattr(data, 'get_team_recent_stats')
        assert hasattr(data, 'get_dashboard_data')
        assert hasattr(data, 'get_system_health')
        assert hasattr(data, 'router')

    def test_router_exists(self):
        """Test that the router is properly configured."""
        from src.api import data
        assert data.router is not None
        assert data.router.prefix == "/data"
        assert "data" in data.router.tags

    def test_logger_exists(self):
        """Test that the logger is properly configured."""
        from src.api import data
        assert data.logger is not None