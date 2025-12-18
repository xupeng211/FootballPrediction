"""
Unit tests for Analytics API endpoints - Green Phase.

This test file follows TDD approach - tests are now GREEN after implementation.
Tests verify the analytics API endpoints work correctly.
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app


class TestTeamPerformanceAnalytics:
    """Test cases for team performance analytics API endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_get_team_performance_success(self, client):
        """Test successful team performance stats retrieval - Green Phase."""
        # Arrange
        team_id = 123
        days = 30

        # Act
        response = client.get(
            f"/api/v1/analytics/teams/{team_id}/performance?days={days}"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == team_id
        assert data["team_name"] == "Manchester United"
        assert data["period_days"] == days
        assert data["matches_played"] == 10
        assert data["performance"]["wins"] == 6
        assert data["performance"]["draws"] == 2
        assert data["performance"]["losses"] == 2
        assert data["performance"]["win_rate"] == 0.6
        assert data["goals"]["goals_for"] == 18
        assert data["goals"]["goals_against"] == 8
        assert data["recent_form"] == ["W", "W", "D", "L", "W"]

    def test_get_team_performance_with_default_days(self, client):
        """Test team performance with default days parameter (30 days)."""
        # Arrange
        team_id = 456

        # Act (without days parameter - should default to 30)
        response = client.get(f"/api/v1/analytics/teams/{team_id}/performance")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == team_id
        assert data["team_name"] == "Liverpool"
        assert data["period_days"] == 30  # Default value
        assert data["matches_played"] == 8
        assert data["performance"]["wins"] == 5
        assert data["performance"]["win_rate"] == 0.625

    def test_get_team_performance_invalid_team_id(self, client):
        """Test with invalid team ID returns 404."""
        # Arrange
        invalid_team_id = 999999

        # Act
        response = client.get(f"/api/v1/analytics/teams/{invalid_team_id}/performance")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_team_performance_invalid_days_parameter(self, client):
        """Test with invalid days parameter returns validation error."""
        # Arrange
        team_id = 123
        invalid_days = 400  # More than allowed maximum

        # Act
        response = client.get(
            f"/api/v1/analytics/teams/{team_id}/performance?days={invalid_days}"
        )

        # Assert
        assert response.status_code == 422  # Validation error
        assert "days" in str(response.json())

    def test_get_team_performance_no_data_available(self, client):
        """Test when no performance data is available for the team."""
        # Arrange
        team_id = 789

        # Act
        response = client.get(f"/api/v1/analytics/teams/{team_id}/performance")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["matches_played"] == 0
        assert data["performance"]["win_rate"] == 0.0
        assert data["recent_form"] == []


class TestLeagueStandingsAnalytics:
    """Test cases for league standings analytics API endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_get_league_standings_success(self, client):
        """Test successful league standings retrieval - Green Phase."""
        # Arrange
        league_id = 39  # Premier League
        season = "2024"

        # Act
        response = client.get(
            f"/api/v1/analytics/leagues/{league_id}/standings?season={season}"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["league_id"] == league_id
        assert data["league_name"] == "Premier League"
        assert data["season"] == season
        assert "standings" in data
        assert len(data["standings"]) == 2  # Mock data has 2 teams
        assert data["standings"][0]["team_name"] == "Arsenal"
        assert data["standings"][0]["position"] == 1


class TestAnalyticsModuleStructure:
    """Test that verifies the analytics module structure is complete."""

    def test_import_analytics_service_should_succeed(self):
        """Test that importing AnalyticsService should now succeed."""
        # Act & Assert - This should NOT raise an exception
        from src.services.analytics_service import AnalyticsService

        assert AnalyticsService is not None

    def test_import_analytics_models_should_succeed(self):
        """Test that importing analytics models should now succeed."""
        # Act & Assert - This should NOT raise an exception
        from src.domain.models.analytics import (
            TeamPerformanceStats,
            LeagueStandingsStats,
        )

        assert TeamPerformanceStats is not None
        assert LeagueStandingsStats is not None

    def test_analytics_service_can_be_instantiated(self):
        """Test that AnalyticsService can be instantiated with repository."""
        # Arrange
        from src.services.analytics_service import AnalyticsService
        from src.database.repositories.analytics_repository import AnalyticsRepository
        from unittest.mock import Mock

        mock_repo = Mock(spec=AnalyticsRepository)

        # Act
        service = AnalyticsService(mock_repo)

        # Assert
        assert service is not None
        assert service._repository == mock_repo


class TestAnalyticsEndpointsIntegration:
    """Integration tests for analytics endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_analytics_health_check(self, client):
        """Test analytics health check endpoint."""
        # Act
        response = client.get("/api/v1/analytics/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "analytics"

    def test_analytics_endpoints_are_accessible(self, client):
        """Test that analytics endpoints are properly registered and accessible."""
        # Test team performance endpoint
        response = client.get("/api/v1/analytics/teams/123/performance")
        assert response.status_code != 404  # Should not be "Not Found"

        # Test league standings endpoint
        response = client.get("/api/v1/analytics/leagues/39/standings")
        assert response.status_code != 404  # Should not be "Not Found"
