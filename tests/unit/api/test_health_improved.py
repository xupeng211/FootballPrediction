"""
测试健康检查API端点（改进版）
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.api.health import (
    ServiceCheckError,
    liveness_check,
    _check_database,
    _check_redis,
    _check_filesystem,
    _optional_check_skipped,
    get_system_health,
    check_database_health,
)


class TestHealthCheckUtils:
    """测试健康检查工具函数"""

    def test_optional_check_skipped(self):
        """测试可选检查跳过响应"""
        result = _optional_check_skipped("test-service")
        expected = {
            "healthy": True,
            "status": "skipped",
            "response_time_ms": 0.0,
            "details": {"message": "test-service check skipped in minimal mode"},
        }
        assert result == expected

    @pytest.mark.parametrize(
        "fast_fail, minimal_mode, expected",
        [
            ("true", "false", True),  # 启用可选检查
            ("false", "true", False),  # 禁用可选检查
            ("false", "false", False),  # 禁用可选检查
            ("true", "true", False),  # 最小模式，禁用可选检查
        ],
    )
    def test_optional_checks_enabled(self, fast_fail, minimal_mode, expected):
        """测试可选检查是否启用"""
        with patch.dict(os.environ, {"FAST_FAIL": fast_fail, "MINIMAL_HEALTH_MODE": minimal_mode}):
            # 重新导入模块以获取新的环境变量值
            from importlib import reload
            import src.api.health as health_module
            reload(health_module)

            assert health_module._optional_checks_enabled() == expected

    def test_get_system_health(self):
        """测试获取系统健康状态"""
        result = get_system_health()
        assert "status" in result
        assert "timestamp" in result
        assert "service" in result
        assert "version" in result
        assert "services" in result
        assert result["status"] == "healthy"
        assert result["service"] == "football-prediction-api"


class TestDatabaseHealthCheck:
    """测试数据库健康检查"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = MagicMock(spec=Session)
        return session

    @pytest.mark.asyncio
    async def test_check_database_success(self, mock_db_session):
        """测试数据库健康检查成功"""
        result = await _check_database(mock_db_session)
        assert result["healthy"] is True
        assert result["status"] == "healthy"
        assert "message" in result["details"]
        assert "数据库连接正常" in result["details"]["message"]

    @pytest.mark.asyncio
    async def test_check_database_failure(self, mock_db_session):
        """测试数据库健康检查失败"""
        mock_db_session.execute.side_effect = Exception("Connection failed")
        result = await _check_database(mock_db_session)
        assert result["healthy"] is False
        assert result["status"] == "unhealthy"
        assert "error" in result["details"]

    async def test_check_database_public_interface(self, mock_db_session):
        """测试数据库健康检查公开接口"""
        result = await check_database_health(mock_db_session)
        assert isinstance(result, dict)
        assert "healthy" in result or "status" in result


class TestRedisHealthCheck:
    """测试Redis健康检查"""

    @pytest.mark.asyncio
    async def test_check_redis_success(self):
        """测试Redis健康检查成功"""
        with patch('src.api.health.RedisManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.aping.return_value = True
            mock_manager.get_info.return_value = {
                "version": "6.2.0",
                "connected_clients": 10,
                "used_memory_human": "1.5M"
            }

            result = await _check_redis()
            assert result["healthy"] is True
            assert result["status"] == "healthy"
            assert "response_time_ms" in result
            assert result["details"]["message"] == "Redis连接正常"
            assert result["details"]["server_info"]["version"] == "6.2.0"

    @pytest.mark.asyncio
    async def test_check_redis_failure(self):
        """测试Redis健康检查失败"""
        with patch('src.api.health.RedisManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.aping.return_value = False

            result = await _check_redis()
            assert result["healthy"] is False
            assert result["status"] == "unhealthy"
            assert "Redis连接失败" in result["details"]["message"]

    @pytest.mark.asyncio
    async def test_check_redis_exception(self):
        """测试Redis健康检查异常"""
        with patch('src.api.health.RedisManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.aping.side_effect = Exception("Connection timeout")

            result = await _check_redis()
            assert result["healthy"] is False
            assert result["status"] == "unhealthy"
            assert "Connection timeout" in result["details"]["error"]


class TestFilesystemHealthCheck:
    """测试文件系统健康检查"""

    @pytest.mark.asyncio
    async def test_check_filesystem_success(self):
        """测试文件系统健康检查成功"""
        result = await _check_filesystem()
        assert result["status"] == "healthy"
        assert "message" in result["details"]
        assert "log_directory" in result["details"]

    @pytest.mark.asyncio
    async def test_check_filesystem_failure(self):
        """测试文件系统健康检查失败"""
        with patch('os.makedirs', side_effect=PermissionError("Permission denied")):
            result = await _check_filesystem()
            assert result["status"] == "unhealthy"
            assert "Permission denied" in result["details"]["message"]


class TestHealthEndpoints:
    """测试健康检查端点"""

    @pytest.mark.asyncio
    async def test_health_check_full_mode(self):
        """测试完整模式健康检查"""
        with patch.dict(os.environ, {"FAST_FAIL": "true", "MINIMAL_HEALTH_MODE": "false"}):
            # 重新加载模块以应用新的环境变量
            from importlib import reload
            import src.api.health as health_module
            reload(health_module)

            # Mock所有依赖
            with patch.object(health_module, '_collect_database_health') as mock_db, \
                 patch.object(health_module, '_check_redis') as mock_redis, \
                 patch.object(health_module, '_check_kafka') as mock_kafka, \
                 patch.object(health_module, '_check_mlflow') as mock_mlflow, \
                 patch.object(health_module, '_check_filesystem') as mock_fs:

                mock_db.return_value = {"healthy": True, "status": "healthy"}
                mock_redis.return_value = {"healthy": True, "status": "healthy"}
                mock_kafka.return_value = {"healthy": True, "status": "healthy"}
                mock_mlflow.return_value = {"healthy": True, "status": "healthy"}
                mock_fs.return_value = {"status": "healthy"}

                result = await health_module.health_check()

                assert result["status"] == "healthy"
                assert result["mode"] == "full"
                assert "checks" in result
                assert "database" in result["checks"]
                assert "redis" in result["checks"]
                assert "kafka" in result["checks"]
                assert "mlflow" in result["checks"]
                assert "filesystem" in result["checks"]

    @pytest.mark.asyncio
    async def test_health_check_minimal_mode(self):
        """测试最小模式健康检查"""
        with patch.dict(os.environ, {"FAST_FAIL": "true", "MINIMAL_HEALTH_MODE": "true"}):
            # 重新加载模块以应用新的环境变量
            from importlib import reload
            import src.api.health as health_module
            reload(health_module)

            with patch.object(health_module, '_collect_database_health') as mock_db:
                mock_db.return_value = {"healthy": True, "status": "healthy"}

                result = await health_module.health_check()

                assert result["status"] == "healthy"
                assert result["mode"] == "minimal"
                assert result["checks"]["database"]["status"] == "skipped"
                assert result["checks"]["redis"]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """测试健康检查失败"""
        with patch.dict(os.environ, {"FAST_FAIL": "true", "MINIMAL_HEALTH_MODE": "false"}):
            from importlib import reload
            import src.api.health as health_module
            reload(health_module)

            with patch.object(health_module, '_collect_database_health') as mock_db:
                mock_db.return_value = {"healthy": False, "status": "unhealthy"}

                with pytest.raises(HTTPException) as exc_info:
                    await health_module.health_check()

                assert exc_info.value.status_code == 503
                assert exc_info.value.detail["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_liveness_check(self):
        """测试存活性检查"""
        result = await liveness_check()
        assert result["status"] == "alive"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_readiness_check_success(self):
        """测试就绪性检查成功"""
        with patch.dict(os.environ, {"FAST_FAIL": "true", "MINIMAL_HEALTH_MODE": "false"}):
            from importlib import reload
            import src.api.health as health_module
            reload(health_module)

            with patch.object(health_module, '_collect_database_health') as mock_db, \
                 patch.object(health_module, '_check_redis') as mock_redis:

                mock_db.return_value = {"healthy": True, "status": "healthy"}
                mock_redis.return_value = {"healthy": True, "status": "healthy"}

                result = await health_module.readiness_check()

                assert result["ready"] is True
                assert "checks" in result

    @pytest.mark.asyncio
    async def test_readiness_check_failure(self):
        """测试就绪性检查失败"""
        with patch.dict(os.environ, {"FAST_FAIL": "true", "MINIMAL_HEALTH_MODE": "false"}):
            from importlib import reload
            import src.api.health as health_module
            reload(health_module)

            with patch.object(health_module, '_collect_database_health') as mock_db:
                mock_db.return_value = {"healthy": False, "status": "unhealthy"}

                with pytest.raises(HTTPException) as exc_info:
                    await health_module.readiness_check()

                assert exc_info.value.status_code == 503
                assert exc_info.value.detail["ready"] is False


class TestServiceCheckError:
    """测试ServiceCheckError异常"""

    def test_service_check_error_without_details(self):
        """测试不带details的ServiceCheckError"""
        error = ServiceCheckError("Test error")
        assert str(error) == "Test error"
        assert error.details == {}

    def test_service_check_error_with_details(self):
        """测试带details的ServiceCheckError"""
        details = {"code": 500, "service": "redis"}
        error = ServiceCheckError("Test error", details=details)
        assert str(error) == "Test error"
        assert error.details == details