"""
基于实际API的健康检查测试
专注于提升真实健康检查模块的测试覆盖率
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, Mock
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError


class TestHealthCheckCore:
    """健康检查核心功能测试"""

    @patch("src.api.health._get_database_service_check")
    @patch("src.api.health._get_redis_service_check")
    @patch("src.api.health._get_filesystem_service_check")
    async def test_health_check_success(self, mock_filesystem, mock_redis, mock_database):
        """测试健康检查成功场景"""
        from src.api.health import health_check
        from src.api.schemas import HealthStatus

        # Mock服务检查结果
        mock_database.return_value = Mock(
            status=HealthStatus.HEALTHY,
            response_time_ms=10.0,
            details={"connections": 5},
        )
        mock_redis.return_value = Mock(
            status=HealthStatus.HEALTHY,
            response_time_ms=5.0,
            details={"memory_usage": "10MB"},
        )
        mock_filesystem.return_value = Mock(
            status=HealthStatus.HEALTHY,
            response_time_ms=2.0,
            details={"disk_space": "50GB free"},
        )

        # 执行健康检查
        result = await health_check()

        # 验证结果
        assert result.status == HealthStatus.HEALTHY
        assert result.timestamp is not None
        assert len(result.services) == 3
        assert result.total_response_time_ms == 17.0  # 10 + 5 + 2

        # 验证服务调用
        mock_database.assert_called_once()
        mock_redis.assert_called_once()
        mock_filesystem.assert_called_once()

    @patch("src.api.health._get_database_service_check")
    @patch("src.api.health._get_redis_service_check")
    @patch("src.api.health._get_filesystem_service_check")
    async def test_health_check_degraded(self, mock_filesystem, mock_redis, mock_database):
        """测试健康检查降级场景"""
        from src.api.health import health_check
        from src.api.schemas import HealthStatus

        # Mock部分服务失败
        mock_database.return_value = Mock(status=HealthStatus.HEALTHY, response_time_ms=10.0)
        mock_redis.return_value = Mock(
            status=HealthStatus.UNHEALTHY,
            response_time_ms=5.0,
            details={"error": "Connection timeout"},
        )
        mock_filesystem.return_value = Mock(status=HealthStatus.HEALTHY, response_time_ms=2.0)

        result = await health_check()

        # 应该标记为降级
        assert result.status == HealthStatus.DEGRADED
        assert len(result.services) == 3
        assert result.total_response_time_ms == 17.0

    @patch("src.api.health._get_database_service_check")
    @patch("src.api.health._get_redis_service_check")
    @patch("src.api.health._get_filesystem_service_check")
    async def test_health_check_unhealthy(self, mock_filesystem, mock_redis, mock_database):
        """测试健康检查不健康场景"""
        from src.api.health import health_check
        from src.api.schemas import HealthStatus

        # Mock多个服务失败
        mock_database.return_value = Mock(
            status=HealthStatus.UNHEALTHY,
            response_time_ms=10.0,
            details={"error": "Connection failed"},
        )
        mock_redis.return_value = Mock(
            status=HealthStatus.UNHEALTHY,
            response_time_ms=5.0,
            details={"error": "Redis down"},
        )
        mock_filesystem.return_value = Mock(status=HealthStatus.HEALTHY, response_time_ms=2.0)

        result = await health_check()

        # 应该标记为不健康
        assert result.status == HealthStatus.UNHEALTHY
        assert len(result.services) == 3


class TestDatabaseServiceCheck:
    """数据库服务检查测试"""

    @patch("src.api.health.get_db_session")
    async def test_database_service_check_success(self, mock_get_session):
        """测试数据库服务检查成功"""
        from src.api.health import _get_database_service_check
        from src.api.schemas import HealthStatus, ServiceCheck

        # Mock数据库会话
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)  # 模拟查询结果
        mock_session.execute.return_value = mock_result
        mock_get_session.return_value.__aenter__.return_value = mock_session

        result = await _get_database_service_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms > 0
        assert result.service_name == "database"
        assert "SELECT 1" in str(mock_session.execute.call_args)

    @patch("src.api.health.get_db_session")
    async def test_database_service_check_connection_error(self, mock_get_session):
        """测试数据库连接错误"""
        from src.api.health import _get_database_service_check
        from src.api.schemas import HealthStatus

        # Mock连接错误
        mock_get_session.side_effect = SQLAlchemyError("Connection failed")

        result = await _get_database_service_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection failed" in result.details["error"]
        assert result.service_name == "database"

    @patch("src.api.health.get_db_session")
    async def test_database_service_check_timeout(self, mock_get_session):
        """测试数据库超时"""
        from src.api.health import _get_database_service_check
        from src.api.schemas import HealthStatus
        import asyncio

        # Mock超时
        async def slow_session():
            await asyncio.sleep(10)  # 模拟慢查询
            return Mock()

        mock_get_session.return_value.__aenter__.return_value = slow_session()

        # 使用较短的超时时间进行测试
        with patch("src.api.health.DATABASE_TIMEOUT", 0.1):
            result = await _get_database_service_check()

            assert result.status == HealthStatus.UNHEALTHY
            assert "timeout" in result.details["error"].lower()


class TestRedisServiceCheck:
    """Redis服务检查测试"""

    @patch("src.api.health.redis_client")
    async def test_redis_service_check_success(self, mock_redis):
        """测试Redis服务检查成功"""
        from src.api.health import _get_redis_service_check
        from src.api.schemas import HealthStatus

        # Mock Redis客户端
        mock_redis.ping.return_value = True
        mock_redis.info.return_value = {"used_memory": "1024k"}

        result = await _get_redis_service_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms > 0
        assert result.service_name == "redis"

    @patch("src.api.health.redis_client")
    async def test_redis_service_check_failure(self, mock_redis):
        """测试Redis服务检查失败"""
        from src.api.health import _get_redis_service_check
        from src.api.schemas import HealthStatus

        # Mock Redis错误
        mock_redis.ping.side_effect = Exception("Redis connection failed")

        result = await _get_redis_service_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Redis connection failed" in result.details["error"]
        assert result.service_name == "redis"

    @patch("src.api.health.redis_client")
    async def test_redis_service_check_disabled(self, mock_redis):
        """测试Redis服务检查禁用"""
        from src.api.health import _get_redis_service_check
        from src.api.schemas import HealthStatus

        # Mock Redis未启用
        with patch("src.api.health.REDIS_ENABLED", False):
            result = await _get_redis_service_check()

            assert result.status == HealthStatus.HEALTHY
            assert "disabled" in result.details.get("info", "").lower()


class TestFilesystemServiceCheck:
    """文件系统服务检查测试"""

    @patch("src.api.health.os.path.exists")
    @patch("src.api.health.os.access")
    @patch("src.api.health.os.statvfs")
    async def test_filesystem_service_check_success(self, mock_statvfs, mock_access, mock_exists):
        """测试文件系统服务检查成功"""
        from src.api.health import _get_filesystem_service_check
        from src.api.schemas import HealthStatus

        # Mock文件系统检查
        mock_exists.return_value = True
        mock_access.return_value = True
        mock_statvfs.return_value = Mock(f_frsize=4096, f_bavail=1000000)  # 块大小  # 可用块数

        result = await _get_filesystem_service_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms > 0
        assert result.service_name == "filesystem"
        assert "disk_space" in result.details

    @patch("src.api.health.os.path.exists")
    async def test_filesystem_service_check_path_not_found(self, mock_exists):
        """测试文件系统路径不存在"""
        from src.api.health import _get_filesystem_service_check
        from src.api.schemas import HealthStatus

        mock_exists.return_value = False

        result = await _get_filesystem_service_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "not found" in result.details["error"].lower()
        assert result.service_name == "filesystem"


class TestHealthCheckUtilities:
    """健康检查工具函数测试"""

    async def test_calculate_response_time(self):
        """测试响应时间计算"""
        from src.api.health import _calculate_response_time

        start_time = datetime.now()
        # 模拟一些处理时间
        await asyncio.sleep(0.01)
        response_time = _calculate_response_time(start_time)

        assert response_time > 5.0  # 至少5ms
        assert response_time < 100.0  # 应该少于100ms

    def test_format_service_details(self):
        """测试服务详情格式化"""
        from src.api.health import _format_service_details

        details = {
            "connections": 5,
            "error": "Connection timeout",
            "response_time": 150.5,
        }

        formatted = _format_service_details(details)

        assert isinstance(formatted, dict)
        assert "connections" in formatted
        assert "error" in formatted
        assert "response_time" in formatted

    async def test_service_check_timeout_wrapper(self):
        """测试服务检查超时包装器"""
        from src.api.health import _service_check_with_timeout
        import asyncio

        async def fast_check():
            return Mock(status="healthy", response_time_ms=10)

        async def slow_check():
            await asyncio.sleep(1)  # 模拟慢检查
            return Mock(status="healthy", response_time_ms=1000)

        # 测试快速检查
        result = await _service_check_with_timeout(fast_check, timeout_seconds=0.5)
        assert result.status == "healthy"

        # 测试超时检查
        result = await _service_check_with_timeout(slow_check, timeout_seconds=0.1)
        assert result.status == "timeout" or "timeout" in result.status.lower()


class TestHealthCheckPerformance:
    """健康检查性能测试"""

    @patch("src.api.health._get_database_service_check")
    @patch("src.api.health._get_redis_service_check")
    @patch("src.api.health._get_filesystem_service_check")
    async def test_health_check_performance(self, mock_filesystem, mock_redis, mock_database):
        """测试健康检查性能"""
        from src.api.health import health_check
        from src.api.schemas import HealthStatus
        import time

        # Mock快速响应
        for mock in [mock_database, mock_redis, mock_filesystem]:
            mock.return_value = Mock(status=HealthStatus.HEALTHY, response_time_ms=5.0)

        # 测量响应时间
        start_time = time.perf_counter()
        result = await health_check()
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        # 健康检查应该很快
        assert response_time_ms < 100  # 应该在100ms内完成
        assert result.status == HealthStatus.HEALTHY
        assert result.total_response_time_ms == 15.0  # 5 + 5 + 5

    @patch("src.api.health._get_database_service_check")
    async def test_concurrent_health_checks(self, mock_database):
        """测试并发健康检查"""
        from src.api.health import _get_database_service_check
        from src.api.schemas import HealthStatus

        mock_database.return_value = Mock(status=HealthStatus.HEALTHY, response_time_ms=10.0)

        # 并发执行多个健康检查
        tasks = [_get_database_service_check() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for result in results:
            assert result.status == HealthStatus.HEALTHY
            assert result.response_time_ms == 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
