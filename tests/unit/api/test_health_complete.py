"""
Health API完整测试
测试覆盖所有健康检查功能，提升覆盖率到30%+
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import time
import os
import asyncio
from fastapi import HTTPException, status

# 直接导入模块进行测试
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

from src.api.health import (
    ServiceCheckError,
    _optional_checks_enabled,
    _optional_check_skipped,
    _collect_database_health,
    health_check,
    liveness_check,
    readiness_check,
    _check_database,
    _check_redis,
    _check_kafka,
    _check_mlflow,
    _check_filesystem,
    get_system_health,
    check_database_health,
    get_async_session
)


class TestUtilityFunctions:
    """测试工具函数"""

    def test_service_check_error(self):
        """测试ServiceCheckError异常"""
        error = ServiceCheckError("Test error")
        assert str(error) == "Test error"
        assert error.details == {}

        error_with_details = ServiceCheckError(
            "Test error with details",
            details={"code": 500, "service": "database"}
        )
        assert error_with_details.details["code"] == 500
        assert error_with_details.details["service"] == "database"

    @patch('src.api.health.FAST_FAIL', True)
    @patch('src.api.health.MINIMAL_HEALTH_MODE', False)
    def test_optional_checks_enabled_true(self):
        """测试可选检查启用 - True"""
        result = _optional_checks_enabled()
        assert result is True

    @patch('src.api.health.FAST_FAIL', False)
    @patch('src.api.health.MINIMAL_HEALTH_MODE', True)
    def test_optional_checks_enabled_false(self):
        """测试可选检查启用 - False"""
        result = _optional_checks_enabled()
        assert result is False

    def test_optional_check_skipped(self):
        """测试可选检查跳过响应"""
        result = _optional_check_skipped("redis")
        expected = {
            "healthy": True,
            "status": "skipped",
            "response_time_ms": 0.0,
            "details": {"message": "redis check skipped in minimal mode"}
        }
        assert result == expected

        # 测试不同服务
        result_kafka = _optional_check_skipped("kafka")
        assert result_kafka["details"]["message"] == "kafka check skipped in minimal mode"


@pytest.mark.asyncio
class TestDatabaseHealth:
    """测试数据库健康检查"""

    @patch('src.api.health.get_database_manager')
    async def test_collect_database_health_success(self, mock_db_manager):
        """测试收集数据库健康状态成功"""
        # 模拟数据库会话
        mock_session = MagicMock()
        mock_db_manager.return_value.get_session.return_value.__enter__.return_value = mock_session

        with patch('src.api.health._check_database') as mock_check:
            mock_check.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 5.0,
                "details": {"connection": "ok"}
            }

            result = await _collect_database_health()

            assert result["healthy"] is True
            assert result["status"] == "healthy"
            assert result["response_time_ms"] == 5.0

    async def test_check_database_success(self):
        """测试数据库检查成功"""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = [1]

        result = await _check_database(mock_db)

        assert result["healthy"] is True
        assert result["status"] == "healthy"
        assert "response_time_ms" in result
        assert result["details"]["message"] == "数据库连接正常"

    async def test_check_database_error(self):
        """测试数据库检查错误"""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Connection failed")

        result = await _check_database(mock_db)

        assert result["healthy"] is False
        assert result["status"] == "unhealthy"
        assert "Connection failed" in result["details"]["error"]

    @patch('src.api.health.get_database_manager')
    async def test_check_database_health_function(self, mock_db_manager):
        """测试check_database_health函数"""
        mock_session = MagicMock()
        mock_db_manager.return_value.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.fetchone.return_value = [1]

        result = await check_database_health(mock_session)

        assert result["healthy"] is True
        assert result["status"] == "healthy"


@pytest.mark.asyncio
class TestRedisHealth:
    """测试Redis健康检查"""

    @patch('src.api.health._redis_circuit_breaker')
    async def test_check_redis_success(self, mock_circuit):
        """测试Redis检查成功"""
        mock_circuit.call.return_value = True
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_circuit.call.return_value = mock_redis_client.ping.return_value

        with patch('src.api.health.redis_client') as mock_client:
            mock_client.ping.return_value = True
            mock_client.info.return_value = {"redis_version": "6.0.0"}

            result = await _check_redis()

            assert result["healthy"] is True
            assert result["status"] == "healthy"

    @patch('src.api.health._redis_circuit_breaker')
    async def test_check_redis_failure(self, mock_circuit):
        """测试Redis检查失败"""
        mock_circuit.call.side_effect = Exception("Redis connection failed")

        result = await _check_redis()

        assert result["healthy"] is False
        assert result["status"] == "unhealthy"
        assert "Redis connection failed" in result["details"]["error"]

    @patch('src.api.health._redis_circuit_breaker')
    async def test_check_redis_timeout(self, mock_circuit):
        """测试Redis检查超时"""
        mock_circuit.call.side_effect = asyncio.TimeoutError("Timeout")

        result = await _check_redis()

        assert result["healthy"] is False
        assert result["status"] == "unhealthy"
        assert "timeout" in result["details"]["error"].lower()


@pytest.mark.asyncio
class TestKafkaHealth:
    """测试Kafka健康检查"""

    @patch('src.api.health._kafka_circuit_breaker')
    async def test_check_kafka_success(self, mock_circuit):
        """测试Kafka检查成功"""
        with patch('src.api.health.KafkaProducer') as mock_producer:
            mock_producer_instance = MagicMock()
            mock_producer.return_value = mock_producer_instance
            mock_producer_instance.bootstrap_connected.return_value = True

            result = await _check_kafka()

            assert result["healthy"] is True
            assert result["status"] == "healthy"

    @patch('src.api.health._kafka_circuit_breaker')
    async def test_check_kafka_failure(self, mock_circuit):
        """测试Kafka检查失败"""
        mock_circuit.call.side_effect = Exception("Kafka connection failed")

        result = await _check_kafka()

        assert result["healthy"] is False
        assert result["status"] == "unhealthy"


@pytest.mark.asyncio
class TestMLflowHealth:
    """测试MLflow健康检查"""

    @patch('src.api.health._mlflow_circuit_breaker')
    async def test_check_mlflow_success(self, mock_circuit):
        """测试MLflow检查成功"""
        with patch('src.api.health.mlflow') as mock_mlflow:
            mock_mlflow.tracking.get_tracking_uri.return_value = "http://localhost:5000"
            mock_mlflow.client.search_experiments.return_value = []

            result = await _check_mlflow()

            assert result["healthy"] is True
            assert result["status"] == "healthy"

    @patch('src.api.health._mlflow_circuit_breaker')
    async def test_check_mlflow_failure(self, mock_circuit):
        """测试MLflow检查失败"""
        mock_circuit.call.side_effect = Exception("MLflow service unavailable")

        result = await _check_mlflow()

        assert result["healthy"] is False
        assert result["status"] == "unhealthy"


@pytest.mark.asyncio
class TestFilesystemHealth:
    """测试文件系统健康检查"""

    async def test_check_filesystem_success(self):
        """测试文件系统检查成功"""
        with patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch('os.statvfs') as mock_statvfs:

            mock_stat = MagicMock()
            mock_stat.f_bavail = 1000000
            mock_stat.f_blocks = 10000000
            mock_stat.f_frsize = 4096
            mock_statvfs.return_value = mock_stat

            result = await _check_filesystem()

            assert result["healthy"] is True
            assert result["status"] == "healthy"
            assert "free_space_gb" in result["details"]

    async def test_check_filesystem_no_space(self):
        """测试文件系统空间不足"""
        with patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch('os.statvfs') as mock_statvfs:

            mock_stat = MagicMock()
            mock_stat.f_bavail = 100  # 很少的可用空间
            mock_stat.f_blocks = 10000000
            mock_stat.f_frsize = 4096
            mock_statvfs.return_value = mock_stat

            result = await _check_filesystem()

            assert result["healthy"] is False
            assert result["status"] == "unhealthy"
            assert "space" in result["details"]["error"].lower()


@pytest.mark.asyncio
class TestHealthEndpoints:
    """测试健康检查端点"""

    @patch('src.api.health.MINIMAL_HEALTH_MODE', False)
    @patch('src.api.health.FAST_FAIL', True)
    async def test_health_check_full_mode_success(self):
        """测试完整模式健康检查成功"""
        with patch('src.api.health._collect_database_health') as mock_db, \
             patch('src.api.health._check_redis') as mock_redis, \
             patch('src.api.health._check_kafka') as mock_kafka, \
             patch('src.api.health._check_mlflow') as mock_mlflow, \
             patch('src.api.health._check_filesystem') as mock_fs:

            # 设置所有服务健康
            mock_db.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 5}
            mock_redis.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 2}
            mock_kafka.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 10}
            mock_mlflow.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 15}
            mock_fs.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 1}

            result = await health_check()

            assert result["status"] == "healthy"
            assert result["mode"] == "full"
            assert "checks" in result
            assert all(check["status"] == "healthy" for check in result["checks"].values())
            assert result["response_time_ms"] > 0

    @patch('src.api.health.MINIMAL_HEALTH_MODE', True)
    async def test_health_check_minimal_mode(self):
        """测试最小模式健康检查"""
        result = await health_check()

        assert result["status"] == "healthy"
        assert result["mode"] == "minimal"
        assert result["checks"]["database"]["status"] == "skipped"
        assert result["checks"]["redis"]["status"] == "skipped"

    @patch('src.api.health.MINIMAL_HEALTH_MODE', False)
    async def test_health_check_unhealthy(self):
        """测试健康检查 - 不健康状态"""
        with patch('src.api.health._collect_database_health') as mock_db, \
             patch('src.api.health._check_redis') as mock_redis:

            mock_db.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 5}
            mock_redis.return_value = {"healthy": False, "status": "unhealthy", "response_time_ms": 2}

            with pytest.raises(HTTPException) as exc_info:
                await health_check()

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["status"] == "unhealthy"
            assert "redis" in exc_info.value.detail["failed_checks"]

    async def test_liveness_check(self):
        """测试存活检查"""
        result = await liveness_check()
        assert result["status"] == "alive"
        assert "timestamp" in result
        assert "uptime" in result

    @patch('src.api.health.MINIMAL_HEALTH_MODE', False)
    async def test_readiness_check_ready(self):
        """测试就绪检查 - 就绪"""
        with patch('src.api.health._collect_database_health') as mock_db:
            mock_db.return_value = {"healthy": True, "status": "healthy", "response_time_ms": 5}

            result = await readiness_check()

            assert result["status"] == "ready"
            assert result["checks"]["database"]["healthy"] is True

    @patch('src.api.health.MINIMAL_HEALTH_MODE', False)
    async def test_readiness_check_not_ready(self):
        """测试就绪检查 - 未就绪"""
        with patch('src.api.health._collect_database_health') as mock_db:
            mock_db.return_value = {"healthy": False, "status": "unhealthy", "response_time_ms": 5}

            result = await readiness_check()

            assert result["status"] == "not_ready"
            assert result["checks"]["database"]["healthy"] is False


class TestSystemHealth:
    """测试系统健康状态"""

    def test_get_system_health(self):
        """测试获取系统健康状态"""
        result = get_system_health()

        assert "timestamp" in result
        assert "uptime" in result
        assert "memory_usage" in result
        assert "cpu_usage" in result
        assert isinstance(result["uptime"], float)

    @patch('src.api.health.psutil')
    def test_get_system_health_with_psutil(self, mock_psutil):
        """测试获取系统健康状态（使用psutil）"""
        mock_psutil.virtual_memory.return_value.percent = 50.0
        mock_psutil.cpu_percent.return_value = 30.0

        result = get_system_health()

        assert result["memory_usage"] == 50.0
        assert result["cpu_usage"] == 30.0


@pytest.mark.asyncio
class TestAsyncSession:
    """测试异步会话"""

    async def test_get_async_session(self):
        """测试获取异步会话"""
        session_gen = get_async_session()
        session = await anext(session_gen)
        assert session is not None
        # 清理
        await session_gen.aclose()


@pytest.mark.asyncio
class TestHealthCheckEdgeCases:
    """测试健康检查边界情况"""

    @patch('src.api.health.MINIMAL_HEALTH_MODE', False)
    async def test_health_check_exception_handling(self):
        """测试健康检查异常处理"""
        with patch('src.api.health._collect_database_health') as mock_db:
            mock_db.side_effect = Exception("Unexpected error")

            with pytest.raises(HTTPException) as exc_info:
                await health_check()

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["status"] == "unhealthy"
            assert "error" in exc_info.value.detail

    @patch('src.api.health.FAST_FAIL', False)
    def test_optional_checks_disabled(self):
        """测试可选检查禁用"""
        result = _optional_checks_enabled()
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])