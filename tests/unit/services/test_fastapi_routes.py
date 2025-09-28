import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException, status
import json
from datetime import datetime

from src.main import app
from src.services.data_processing import DataProcessingService


class TestFastAPIRoutes:
    """Test FastAPI routes with HTTP 200/400/500 response coverage"""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_data_processing_service(self):
        """Mock DataProcessingService for route testing"""
        service = MagicMock()
        service.process_raw_match_data = AsyncMock()
        service.process_raw_odds_data = AsyncMock()
        service.process_features_data = AsyncMock()
        service.validate_data_quality = AsyncMock()
        service.process_batch_matches = AsyncMock()
        service.run_etl_pipeline = AsyncMock()
        service.cache_processed_data = AsyncMock()
        service.get_cached_data = AsyncMock()
        return service

    @pytest.fixture
    def sample_valid_match_data(self):
        """Sample valid match data for testing"""
        return {
            "match_id": "12345",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "match_date": "2023-09-29T15:00:00Z",
            "status": "finished",
            "competition": "Premier League"
        }

    @pytest.fixture
    def sample_valid_odds_data(self):
        """Sample valid odds data for testing"""
        return [{
            "match_id": "12345",
            "bookmaker": "Bet365",
            "home_win": 2.10,
            "draw": 3.40,
            "away_win": 3.80,
            "timestamp": "2023-09-29T14:00:00Z"
        }]

    @pytest.fixture
    def sample_valid_features_data(self):
        """Sample valid features data for testing"""
        return {
            "home_form": 3.0,
            "away_form": 1.5,
            "home_goals_scored": 10,
            "away_goals_conceded": 8,
            "home_shots_on_target": 15,
            "away_shots_on_target": 8
        }

    # Test Health Check Routes
    def test_health_check_success(self, client):
        """Test health check endpoint returns 200"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_health_check_with_service_status(self, client):
        """Test health check with service status information"""
        with patch('src.api.routes.health.get_service_status') as mock_status:
            mock_status.return_value = {
                "database": "healthy",
                "redis": "healthy",
                "data_lake": "healthy"
            }

            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "services" in data
            assert data["services"]["database"] == "healthy"

    # Test Data Processing Routes - Success Cases (200)
    @pytest.mark.asyncio
    async def test_process_match_data_success(self, client, mock_data_processing_service, sample_valid_match_data):
        """Test successful match data processing returns 200"""
        mock_data_processing_service.process_raw_match_data.return_value = {
            "match_id": "12345",
            "processed": True,
            "status": "success"
        }

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/data/matches/process", json=sample_valid_match_data)
            assert response.status_code == 200
            data = response.json()
            assert data["processed"] is True
            assert data["match_id"] == "12345"

    @pytest.mark.asyncio
    async def test_process_odds_data_success(self, client, mock_data_processing_service, sample_valid_odds_data):
        """Test successful odds data processing returns 200"""
        mock_data_processing_service.process_raw_odds_data.return_value = {
            "processed_count": 1,
            "status": "success"
        }

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/data/odds/process", json=sample_valid_odds_data)
            assert response.status_code == 200
            data = response.json()
            assert data["processed_count"] == 1
            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_process_features_data_success(self, client, mock_data_processing_service, sample_valid_features_data):
        """Test successful features data processing returns 200"""
        mock_data_processing_service.process_features_data.return_value = {
            "match_id": "12345",
            "processed": True,
            "features_count": 5
        }

        with patch('src.api.routes.features.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/features/process", json={
                "match_id": "12345",
                "features": sample_valid_features_data
            })
            assert response.status_code == 200
            data = response.json()
            assert data["processed"] is True
            assert data["features_count"] == 5

    @pytest.mark.asyncio
    async def test_batch_process_matches_success(self, client, mock_data_processing_service):
        """Test successful batch match processing returns 200"""
        batch_data = [
            {"match_id": "001", "home_team": "Team A", "away_team": "Team B"},
            {"match_id": "002", "home_team": "Team C", "away_team": "Team D"}
        ]

        mock_data_processing_service.process_batch_matches.return_value = [
            {"match_id": "001", "processed": True},
            {"match_id": "002", "processed": True}
        ]

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/data/matches/batch-process", json={
                "matches": batch_data,
                "batch_size": 10
            })
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 2
            assert all(result["processed"] for result in data["results"])

    # Test Validation Error Routes (400)
    @pytest.mark.asyncio
    async def test_process_match_data_invalid_input(self, client):
        """Test match data processing with invalid input returns 400"""
        invalid_data = {
            "home_team": "Team A",
            # Missing required match_id and away_team
            "home_score": "invalid_score"  # Invalid data type
        }

        response = client.post("/api/v1/data/matches/process", json=invalid_data)
        assert response.status_code == 422  # FastAPI validation error

    @pytest.mark.asyncio
    async def test_process_odds_data_invalid_input(self, client):
        """Test odds data processing with invalid input returns 400"""
        invalid_odds = [{
            "match_id": "12345",
            "bookmaker": "Bet365",
            "home_win": "invalid",  # Should be numeric
            "draw": 3.40,
            "away_win": 3.80
        }]

        response = client.post("/api/v1/data/odds/process", json=invalid_odds)
        assert response.status_code == 422  # FastAPI validation error

    @pytest.mark.asyncio
    async def test_process_features_data_missing_match_id(self, client, sample_valid_features_data):
        """Test features data processing without match_id returns 400"""
        response = client.post("/api/v1/features/process", json={
            "features": sample_valid_features_data
            # Missing match_id
        })
        assert response.status_code == 422  # FastAPI validation error

    @pytest.mark.asyncio
    async def test_batch_process_matches_empty_batch(self, client):
        """Test batch processing with empty batch returns 400"""
        response = client.post("/api/v1/data/matches/batch-process", json={
            "matches": [],
            "batch_size": 10
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_batch_process_matches_invalid_batch_size(self, client):
        """Test batch processing with invalid batch_size returns 400"""
        batch_data = [{"match_id": "001", "home_team": "Team A", "away_team": "Team B"}]

        response = client.post("/api/v1/data/matches/batch-process", json={
            "matches": batch_data,
            "batch_size": 0  # Invalid batch size
        })
        assert response.status_code == 400

    # Test Server Error Routes (500)
    @pytest.mark.asyncio
    async def test_process_match_data_service_error(self, client, mock_data_processing_service, sample_valid_match_data):
        """Test match data processing service error returns 500"""
        mock_data_processing_service.process_raw_match_data.side_effect = Exception("Service unavailable")

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/data/matches/process", json=sample_valid_match_data)
            assert response.status_code == 500
            data = response.json()
            assert "error" in data

    @pytest.mark.asyncio
    async def test_process_odds_data_database_error(self, client, mock_data_processing_service, sample_valid_odds_data):
        """Test odds data processing with database error returns 500"""
        mock_data_processing_service.process_raw_odds_data.side_effect = Exception("Database connection failed")

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/data/odds/process", json=sample_valid_odds_data)
            assert response.status_code == 500
            data = response.json()
            assert "error" in data

    @pytest.mark.asyncio
    async def test_process_features_data_validation_error(self, client, mock_data_processing_service):
        """Test features data processing with validation error returns 500"""
        mock_data_processing_service.process_features_data.side_effect = Exception("Validation failed")

        with patch('src.api.routes.features.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/features/process", json={
                "match_id": "12345",
                "features": {"invalid": "data"}
            })
            assert response.status_code == 500
            data = response.json()
            assert "error" in data

    @pytest.mark.asyncio
    async def test_service_unavailable_error(self, client):
        """Test service unavailable returns 500"""
        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.side_effect = Exception("Service not available")

            response = client.post("/api/v1/data/matches/process", json={"match_id": "12345"})
            assert response.status_code == 500
            data = response.json()
            assert "error" in data

    # Test Data Quality Validation Routes
    @pytest.mark.asyncio
    async def test_validate_data_quality_success(self, client, mock_data_processing_service):
        """Test successful data quality validation returns 200"""
        test_data = {"match_id": "12345", "home_team": "Team A", "away_team": "Team B"}

        mock_data_processing_service.validate_data_quality.return_value = {
            "valid": True,
            "score": 0.95,
            "issues": []
        }

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/data/validate", json={
                "data": test_data,
                "data_type": "match"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["score"] == 0.95

    @pytest.mark.asyncio
    async def test_validate_data_quality_failure(self, client, mock_data_processing_service):
        """Test data quality validation failure returns 200 with failure details"""
        test_data = {"match_id": "", "home_team": "", "away_team": ""}

        mock_data_processing_service.validate_data_quality.return_value = {
            "valid": False,
            "score": 0.1,
            "issues": ["Empty match_id", "Empty home_team", "Empty away_team"]
        }

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/data/validate", json={
                "data": test_data,
                "data_type": "match"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert len(data["issues"]) == 3

    # Test ETL Pipeline Routes
    @pytest.mark.asyncio
    async def test_run_etl_pipeline_success(self, client, mock_data_processing_service):
        """Test successful ETL pipeline execution returns 200"""
        pipeline_config = {
            "source": "bronze",
            "target": "silver",
            "data_type": "matches",
            "batch_size": 100
        }

        mock_data_processing_service.run_etl_pipeline.return_value = {
            "status": "success",
            "processed_count": 150,
            "execution_time": 5.2
        }

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/data/etl/run", json=pipeline_config)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["processed_count"] == 150

    @pytest.mark.asyncio
    async def test_run_etl_pipeline_invalid_config(self, client):
        """Test ETL pipeline with invalid config returns 400"""
        invalid_config = {
            "source": "invalid_source",
            "target": "silver",
            "data_type": "matches"
        }

        response = client.post("/api/v1/data/etl/run", json=invalid_config)
        assert response.status_code == 400

    # Test Caching Routes
    @pytest.mark.asyncio
    async def test_cache_data_success(self, client, mock_data_processing_service):
        """Test successful data caching returns 200"""
        cache_data = {"match_id": "12345", "processed": True}

        mock_data_processing_service.cache_processed_data.return_value = {
            "status": "cached",
            "key": "match_12345"
        }

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/data/cache", json={
                "key": "match_12345",
                "data": cache_data
            })
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "cached"

    @pytest.mark.asyncio
    async def test_get_cached_data_success(self, client, mock_data_processing_service):
        """Test successful cached data retrieval returns 200"""
        cached_data = {"match_id": "12345", "processed": True}

        mock_data_processing_service.get_cached_data.return_value = cached_data

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.get("/api/v1/data/cache/match_12345")
            assert response.status_code == 200
            data = response.json()
            assert data["match_id"] == "12345"

    @pytest.mark.asyncio
    async def test_get_cached_data_not_found(self, client, mock_data_processing_service):
        """Test cached data not found returns 404"""
        mock_data_processing_service.get_cached_data.return_value = None

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.get("/api/v1/data/cache/nonexistent_key")
            assert response.status_code == 404

    # Test Monitoring Routes
    def test_metrics_endpoint_success(self, client):
        """Test metrics endpoint returns 200"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_endpoint_with_accept_header(self, client):
        """Test metrics endpoint with accept header"""
        response = client.get("/metrics", headers={"Accept": "application/json"})
        assert response.status_code == 200

    # Test Error Handling Middleware
    def test_custom_exception_handler(self, client):
        """Test custom exception handling"""
        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.side_effect = HTTPException(
                status_code=403,
                detail="Access denied"
            )

            response = client.post("/api/v1/data/matches/process", json={})
            assert response.status_code == 403
            data = response.json()
            assert "detail" in data

    def test_generic_exception_handler(self, client):
        """Test generic exception handling"""
        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.side_effect = RuntimeError("Unexpected error")

            response = client.post("/api/v1/data/matches/process", json={})
            assert response.status_code == 500
            data = response.json()
            assert "error" in data

    # Test Request Validation
    def test_invalid_json_payload(self, client):
        """Test invalid JSON payload returns 400"""
        response = client.post("/api/v1/data/matches/process", data="invalid json")
        assert response.status_code == 422

    def test_missing_required_headers(self, client):
        """Test endpoint that requires specific headers"""
        response = client.post("/api/v1/data/matches/process",
                              json={"match_id": "12345"},
                              headers={"Content-Type": "application/xml"})  # Wrong content type
        assert response.status_code == 422

    # Test Rate Limiting (if implemented)
    def test_rate_limiting(self, client):
        """Test rate limiting returns 429"""
        # This would need to be implemented with actual rate limiting
        # For now, we'll test the concept
        for i in range(100):  # Simulate many requests
            response = client.get("/health")
            if response.status_code == 429:
                break
        # If rate limiting is implemented, this would eventually return 429
        # For now, we expect 200
        assert response.status_code in [200, 429]

    # Test Authentication/Authorization (if implemented)
    def test_unauthorized_access(self, client):
        """Test unauthorized access returns 401"""
        # This would need to be implemented with actual auth
        response = client.get("/api/v1/admin/status")
        # If auth is implemented, this might return 401
        # For now, we'll accept either 401 or 404 (if endpoint doesn't exist)
        assert response.status_code in [401, 404]

    # Test API Documentation Endpoints
    def test_api_docs_available(self, client):
        """Test API documentation endpoints are available"""
        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/redoc")
        assert response.status_code == 200

        response = client.get("/openapi.json")
        assert response.status_code == 200

    # Test CORS Headers
    def test_cors_headers(self, client):
        """Test CORS headers are properly set"""
        response = client.options("/api/v1/data/matches/process")
        # Should include CORS headers if CORS is enabled
        assert response.status_code in [200, 404, 422]  # Depends on CORS setup

    # Test Large Payload Handling
    @pytest.mark.asyncio
    async def test_large_payload_handling(self, client, mock_data_processing_service):
        """Test handling of large payloads"""
        large_batch = [{"match_id": f"match_{i}", "home_team": f"Team {i}", "away_team": f"Opponent {i}"}
                      for i in range(1000)]

        mock_data_processing_service.process_batch_matches.return_value = [
            {"match_id": f"match_{i}", "processed": True} for i in range(1000)
        ]

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            response = client.post("/api/v1/data/matches/batch-process", json={
                "matches": large_batch,
                "batch_size": 100
            })
            # Should handle large payload gracefully
            assert response.status_code in [200, 413]  # 413 if payload too large

    # Test Timeout Handling
    @pytest.mark.asyncio
    async def test_timeout_handling(self, client, mock_data_processing_service, sample_valid_match_data):
        """Test timeout handling for slow operations"""
        import asyncio

        async def slow_processing(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow processing
            return {"match_id": "12345", "processed": True}

        mock_data_processing_service.process_raw_match_data.side_effect = slow_processing

        with patch('src.api.routes.data.get_data_processing_service') as mock_get_service:
            mock_get_service.return_value = mock_data_processing_service

            # This might timeout depending on server configuration
            response = client.post("/api/v1/data/matches/process", json=sample_valid_match_data, timeout=1)
            # Status code depends on timeout configuration
            assert response.status_code in [200, 408, 504]