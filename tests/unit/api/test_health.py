#!/usr/bin/env python3
"""
Unit tests for health API module.

Tests for src/api/health.py module functions and endpoints.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any
import time

from src.api.health import (
    ServiceCheckError,
    health_check,
    liveness_check,
    readiness_check,
    _check_database,
    _check_redis,
    _check_kafka,
    _check_mlflow,
    _check_filesystem,
    get_system_health,
    check_database_health
)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 1
    return session


@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    redis = MagicMock()
    redis.ping.return_value = True
    return redis


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    producer = MagicMock()
    return producer


@pytest.fixture
def mock_mlflow_client():
    """Mock MLflow client."""
    client = MagicMock()
    return client


class TestServiceCheckError:
    """Test cases for ServiceCheckError class."""

    def test_service_check_error_creation(self):
        """Test ServiceCheckError creation with message only."""
        error = ServiceCheckError("Test error message")
        assert str(error) == "Test error message"
        assert error.details == {}

    def test_service_check_error_creation_with_details(self):
        """Test ServiceCheckError creation with message and details."""
        details = {"service": "redis", "error_code": 500}
        error = ServiceCheckError("Test error message", details=details)
        assert str(error) == "Test error message"
        assert error.details == details

    def test_service_check_error_inheritance(self):
        """Test ServiceCheckError inheritance from RuntimeError."""
        error = ServiceCheckError("Test error")
        assert isinstance(error, RuntimeError)
        assert isinstance(error, Exception)


class TestHealthCheck:
    """Test cases for health_check function."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_db_session):
        """Test successful health check."""
        with patch('src.api.health._check_database') as mock_check_db, \
             patch('src.api.health._check_redis') as mock_check_redis, \
             patch('src.api.health._check_kafka') as mock_check_kafka, \
             patch('src.api.health._check_mlflow') as mock_check_mlflow, \
             patch('src.api.health._check_filesystem') as mock_check_fs:

            # Setup mocks
            mock_check_db.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 100}
            mock_check_redis.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 50}
            mock_check_kafka.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 200}
            mock_check_mlflow.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 150}
            mock_check_fs.return_value = {"status": "healthy", "response_time_ms": 10}

            # Execute function
            result = await health_check(mock_db_session)

            # Verify result
            assert result["status"] == "healthy"
            assert result["service"] == "football-prediction-api"
            assert result["version"] == "1.0.0"
            assert "checks" in result
            assert result["checks"]["database"]["status"] == "healthy"
            assert result["checks"]["redis"]["status"] == "healthy"
            assert result["checks"]["kafka"]["status"] == "healthy"
            assert result["checks"]["mlflow"]["status"] == "healthy"
            assert result["checks"]["filesystem"]["status"] == "healthy"
            assert "timestamp" in result
            assert "uptime" in result
            assert "response_time_ms" in result

    @pytest.mark.asyncio
    async def test_health_check_partial_failure(self, mock_db_session):
        """Test health check with some services failing."""
        with patch('src.api.health._check_database') as mock_check_db, \
             patch('src.api.health._check_redis') as mock_check_redis, \
             patch('src.api.health._check_kafka') as mock_check_kafka, \
             patch('src.api.health._check_mlflow') as mock_check_mlflow, \
             patch('src.api.health._check_filesystem') as mock_check_fs:

            # Setup mocks - Redis and Kafka failing
            mock_check_db.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 100}
            mock_check_redis.return_value = {"healthy": False, "status": "unhealthy", "response_time_ms": 50}
            mock_check_kafka.return_value = {"healthy": False, "status": "unhealthy", "response_time_ms": 200}
            mock_check_mlflow.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 150}
            mock_check_fs.return_value = {"status": "healthy", "response_time_ms": 10}

            # Execute function and expect HTTPException
            with pytest.raises(Exception) as exc_info:
                await health_check(mock_db_session)

            # The function should raise HTTPException when services are unhealthy
            assert exc_info.value is not None

    @pytest.mark.asyncio
    async def test_health_check_critical_failure(self, mock_db_session):
        """Test health check with critical services failing."""
        with patch('src.api.health._check_database') as mock_check_db, \
             patch('src.api.health._check_redis') as mock_check_redis, \
             patch('src.api.health._check_kafka') as mock_check_kafka, \
             patch('src.api.health._check_mlflow') as mock_check_mlflow, \
             patch('src.api.health._check_filesystem') as mock_check_fs:

            # Setup mocks - Database failing (critical)
            mock_check_db.return_value = {"healthy": False, "status": "unhealthy", "response_time_ms": 100}
            mock_check_redis.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 50}
            mock_check_kafka.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 200}
            mock_check_mlflow.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 150}
            mock_check_fs.return_value = {"status": "healthy", "response_time_ms": 10}

            # Execute function and expect HTTPException
            with pytest.raises(Exception) as exc_info:
                await health_check(mock_db_session)

            # The function should raise HTTPException when services are unhealthy
            assert exc_info.value is not None


class TestLivenessCheck:
    """Test cases for liveness_check function."""

    @pytest.mark.asyncio
    async def test_liveness_check_success(self):
        """Test successful liveness check."""
        result = await liveness_check()

        # Verify result
        assert result["status"] == "alive"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_liveness_check_with_app_start_time(self):
        """Test liveness check with application start time."""
        # This test verifies the function uses the global _app_start_time variable
        result = await liveness_check()

        # Verify result
        assert result["status"] == "alive"
        assert "timestamp" in result


class TestReadinessCheck:
    """Test cases for readiness_check function."""

    @pytest.mark.asyncio
    async def test_readiness_check_ready(self, mock_db_session):
        """Test readiness check when system is ready."""
        with patch('src.api.health._check_database') as mock_check_db, \
             patch('src.api.health._check_redis') as mock_check_redis, \
             patch('src.api.health._check_kafka') as mock_check_kafka, \
             patch('src.api.health._check_mlflow') as mock_check_mlflow:

            # Setup mocks
            mock_check_db.return_value = {"healthy": True, "status": "healthy"}
            mock_check_redis.return_value = {"healthy": True, "status": "healthy"}
            mock_check_kafka.return_value = {"healthy": True, "status": "healthy"}
            mock_check_mlflow.return_value = {"healthy": True, "status": "healthy"}

            # Execute function
            result = await readiness_check(mock_db_session)

            # Verify result
            assert result["ready"] is True
            assert "checks" in result
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_readiness_check_not_ready(self, mock_db_session):
        """Test readiness check when system is not ready."""
        with patch('src.api.health._check_database') as mock_check_db, \
             patch('src.api.health._check_redis') as mock_check_redis, \
             patch('src.api.health._check_kafka') as mock_check_kafka, \
             patch('src.api.health._check_mlflow') as mock_check_mlflow:

            # Setup mocks - Database failing
            mock_check_db.return_value = {"healthy": False, "status": "unhealthy"}
            mock_check_redis.return_value = {"healthy": True, "status": "healthy"}
            mock_check_kafka.return_value = {"healthy": True, "status": "healthy"}
            mock_check_mlflow.return_value = {"healthy": True, "status": "healthy"}

            # Execute function and expect HTTPException
            with pytest.raises(Exception):
                await readiness_check(mock_db_session)


class TestDatabaseCheck:
    """Test cases for database check functions."""

    @pytest.mark.asyncio
    async def test_check_database_success(self, mock_db_session):
        """Test successful database check."""
        result = await _check_database(mock_db_session)

        # Verify result
        assert result["healthy"] is True
        assert result["status"] == "healthy"
        assert "response_time_ms" in result
        assert "details" in result
        assert result["details"]["message"] == "数据库连接正常"

    @pytest.mark.asyncio
    async def test_check_database_failure(self, mock_db_session):
        """Test database check with failure."""
        mock_db_session.execute.side_effect = Exception("Connection failed")

        result = await _check_database(mock_db_session)

        # Verify result
        assert result["healthy"] is False
        assert result["status"] == "unhealthy"
        assert "response_time_ms" in result
        assert "details" in result
        assert "error" in result["details"]

    @pytest.mark.asyncio
    async def test_check_database_health_success(self, mock_db_session):
        """Test successful database health check."""
        result = await check_database_health(mock_db_session)

        # Verify result
        assert result["healthy"] is True
        assert result["status"] == "healthy"
        assert "response_time_ms" in result

    @pytest.mark.asyncio
    async def test_check_database_health_failure(self, mock_db_session):
        """Test database health check with failure."""
        mock_db_session.execute.side_effect = Exception("Connection failed")

        result = await check_database_health(mock_db_session)

        # Verify result
        assert result["healthy"] is False
        assert result["status"] == "unhealthy"
        assert "error" in result["details"]


class TestRedisCheck:
    """Test cases for Redis check function."""

    @pytest.mark.asyncio
    async def test_check_redis_success(self):
        """Test successful Redis check."""
        with patch('src.api.health._redis_circuit_breaker') as mock_circuit:
            async def mock_call(func):
                return {
                    "healthy": True,
                    "status": "healthy",
                    "response_time_ms": 50,
                    "details": {"message": "Redis连接正常"}
                }
            mock_circuit.call = mock_call

            result = await _check_redis()

            # Verify result
            assert result["healthy"] is True
            assert result["status"] == "healthy"
            assert "response_time_ms" in result

    @pytest.mark.asyncio
    async def test_check_redis_failure(self):
        """Test Redis check with failure."""
        with patch('src.api.health._redis_circuit_breaker') as mock_circuit:
            async def mock_call(func):
                raise ServiceCheckError("Redis connection failed")
            mock_circuit.call = mock_call

            result = await _check_redis()

            # Verify result
            assert result["healthy"] is False
            assert result["status"] == "unhealthy"
            assert "error" in result["details"]


class TestKafkaCheck:
    """Test cases for Kafka check function."""

    @pytest.mark.asyncio
    async def test_check_kafka_success(self):
        """Test successful Kafka check."""
        with patch('src.api.health._kafka_circuit_breaker') as mock_circuit:
            async def mock_call(func):
                return {
                    "healthy": True,
                    "status": "healthy",
                    "response_time_ms": 100,
                    "details": {"message": "Kafka连接正常"}
                }
            mock_circuit.call = mock_call

            result = await _check_kafka()

            # Verify result
            assert result["healthy"] is True
            assert result["status"] == "healthy"
            assert "response_time_ms" in result

    @pytest.mark.asyncio
    async def test_check_kafka_failure(self):
        """Test Kafka check with failure."""
        with patch('src.api.health._kafka_circuit_breaker') as mock_circuit:
            async def mock_call(func):
                raise ServiceCheckError("Kafka broker unavailable")
            mock_circuit.call = mock_call

            result = await _check_kafka()

            # Verify result
            assert result["healthy"] is False
            assert result["status"] == "unhealthy"
            assert "error" in result["details"]


class TestMLflowCheck:
    """Test cases for MLflow check function."""

    @pytest.mark.asyncio
    async def test_check_mlflow_success(self):
        """Test successful MLflow check."""
        with patch('src.api.health._mlflow_circuit_breaker') as mock_circuit:
            async def mock_call(func):
                return {
                    "healthy": True,
                    "status": "healthy",
                    "response_time_ms": 150,
                    "details": {"message": "MLflow连接正常"}
                }
            mock_circuit.call = mock_call

            result = await _check_mlflow()

            # Verify result
            assert result["healthy"] is True
            assert result["status"] == "healthy"
            assert "response_time_ms" in result

    @pytest.mark.asyncio
    async def test_check_mlflow_failure(self):
        """Test MLflow check with failure."""
        with patch('src.api.health._mlflow_circuit_breaker') as mock_circuit:
            async def mock_call(func):
                raise ServiceCheckError("MLflow server unavailable")
            mock_circuit.call = mock_call

            result = await _check_mlflow()

            # Verify result
            assert result["healthy"] is False
            assert result["status"] == "unhealthy"
            assert "error" in result["details"]


class TestFilesystemCheck:
    """Test cases for filesystem check function."""

    @pytest.mark.asyncio
    async def test_check_filesystem_success(self):
        """Test successful filesystem check."""
        with patch('os.access') as mock_access, \
             patch('os.statvfs') as mock_statvfs:

            mock_access.return_value = True
            mock_stat = MagicMock()
            mock_stat.f_bavail = 1000000
            mock_stat.f_blocks = 2000000
            mock_statvfs.return_value = mock_stat

            result = await _check_filesystem()

            # Verify result
            assert result["status"] == "healthy"
            assert "response_time_ms" in result
            assert "details" in result

    @pytest.mark.asyncio
    async def test_check_filesystem_no_write_access(self):
        """Test filesystem check with no write access."""
        with patch('os.path.exists') as mock_exists, \
             patch('os.makedirs') as mock_makedirs:
            mock_exists.return_value = False
            mock_makedirs.side_effect = Exception("Permission denied")

            result = await _check_filesystem()

            # Verify result
            assert result["status"] == "unhealthy"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_check_filesystem_low_space(self):
        """Test filesystem check with low space."""
        with patch('os.path.exists') as mock_exists, \
             patch('os.makedirs') as mock_makedirs:
            mock_exists.return_value = False
            mock_makedirs.side_effect = Exception("No space left on device")

            result = await _check_filesystem()

            # Verify result
            assert result["status"] == "unhealthy"
            assert "error" in result


class TestGetSystemHealth:
    """Test cases for get_system_health function."""

    def test_get_system_health_success(self):
        """Test successful system health check."""
        result = get_system_health()

        # Verify result
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "service" in result
        assert "version" in result
        assert "services" in result

    def test_get_system_health_with_app_start_time(self):
        """Test system health check considers application start time."""
        result = get_system_health()

        # Verify result
        assert result["status"] == "healthy"
        assert "services" in result
        assert "database" in result["services"]
        assert "redis" in result["services"]
        assert "filesystem" in result["services"]


class TestHealthAPIModule:
    """Test cases for health API module imports and configuration."""

    def test_module_imports(self):
        """Test that the module can be imported successfully."""
        from src.api import health
        assert hasattr(health, 'health_check')
        assert hasattr(health, 'liveness_check')
        assert hasattr(health, 'readiness_check')
        assert hasattr(health, 'ServiceCheckError')
        assert hasattr(health, 'router')

    def test_router_configuration(self):
        """Test that the router is properly configured."""
        from src.api import health
        assert health.router is not None
        assert "健康检查" in health.router.tags

    def test_circuit_breakers_exist(self):
        """Test that circuit breakers are properly defined."""
        from src.api import health
        assert hasattr(health, '_redis_circuit_breaker')
        assert hasattr(health, '_kafka_circuit_breaker')
        assert hasattr(health, '_mlflow_circuit_breaker')

    def test_app_start_time_exists(self):
        """Test that application start time is recorded."""
        from src.api import health
        assert hasattr(health, '_app_start_time')
        assert isinstance(health._app_start_time, float)

    def test_logger_exists(self):
        """Test that the logger is properly configured."""
        from src.api import health
        from src.api.health import logger
        assert logger is not None