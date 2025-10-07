"""
简化的健康检查API测试
专注于提高health.py的覆盖率
"""

import pytest
from unittest.mock import MagicMock, patch

from src.api.health import (
    ServiceCheckError,
    _check_database,
    _optional_check_skipped,
    _optional_checks_enabled,
)


class TestUtilityFunctions:
    """测试工具函数"""

    def test_optional_checks_enabled_true(self):
        """测试启用可选检查的情况"""
        with patch("src.api.health.FAST_FAIL", True):
            with patch("src.api.health.MINIMAL_HEALTH_MODE", False):
                assert _optional_checks_enabled() is True

    def test_optional_checks_enabled_false_fast_fail(self):
        """测试FAST_FAIL为False的情况"""
        with patch("src.api.health.FAST_FAIL", False):
            with patch("src.api.health.MINIMAL_HEALTH_MODE", False):
                assert _optional_checks_enabled() is False

    def test_optional_checks_enabled_false_minimal_mode(self):
        """测试MINIMAL_HEALTH_MODE为True的情况"""
        with patch("src.api.health.FAST_FAIL", True):
            with patch("src.api.health.MINIMAL_HEALTH_MODE", True):
                assert _optional_checks_enabled() is False

    def test_optional_check_skipped(self):
        """测试可选检查跳过响应"""
        service = "Redis"
        result = _optional_check_skipped(service)

        assert result["healthy"] is True
        assert result["status"] == "skipped"
        assert result["response_time_ms"] == 0.0
        assert f"{service} check skipped in minimal mode" in result["details"]["message"]

    def test_optional_check_skipped_different_services(self):
        """测试不同服务的可选检查跳过"""
        services = ["database", "redis", "kafka", "mlflow", "filesystem"]

        for service in services:
            result = _optional_check_skipped(service)
            assert result["status"] == "skipped"
            assert service in result["details"]["message"]

    def test_service_check_error_basic(self):
        """测试ServiceCheckError基本功能"""
        message = "Test error"
        error = ServiceCheckError(message)

        assert str(error) == message
        assert error.details == {}

    def test_service_check_error_with_details(self):
        """测试带详细信息的ServiceCheckError"""
        message = "Test error"
        details = {"code": 500, "service": "redis"}
        error = ServiceCheckError(message, details=details)

        assert str(error) == message
        assert error.details == details
        assert error.details["code"] == 500
        assert error.details["service"] == "redis"


class TestDatabaseHealthCheck:
    """测试数据库健康检查"""

    @pytest.mark.asyncio
    async def test_check_database_success(self):
        """测试数据库连接成功"""
        mock_session = MagicMock()
        mock_session.execute.return_value = None

        result = await _check_database(mock_session)

        assert result["healthy"] is True
        assert result["status"] == "healthy"
        assert result["response_time_ms"] == 0
        assert "message" in result["details"]
        assert "数据库连接正常" in result["details"]["message"]

    @pytest.mark.asyncio
    async def test_check_database_exception(self):
        """测试数据库连接异常"""
        from sqlalchemy.exc import SQLAlchemyError

        mock_session = MagicMock()
        mock_session.execute.side_effect = SQLAlchemyError("Connection failed")

        result = await _check_database(mock_session)

        assert result["healthy"] is False
        assert result["status"] == "unhealthy"
        assert result["response_time_ms"] == 0
        assert "error" in result["details"]
        assert "Connection failed" in result["details"]["error"]

    @pytest.mark.asyncio
    async def test_check_database_generic_exception(self):
        """测试数据库通用异常"""
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Generic error")

        result = await _check_database(mock_session)

        assert result["healthy"] is False
        assert result["status"] == "unhealthy"
        assert "Generic error" in result["details"]["error"]

    @pytest.mark.asyncio
    async def test_check_database_session_closed(self):
        """测试数据库会话已关闭"""
        from sqlalchemy.exc import DBAPIError

        mock_session = MagicMock()
        mock_session.execute.side_effect = DBAPIError("", {}, None)

        result = await _check_database(mock_session)

        assert result["healthy"] is False
        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_check_database_timeout(self):
        """测试数据库连接超时"""
        import asyncio

        mock_session = MagicMock()

        async def timeout_query(*args, **kwargs):
            await asyncio.sleep(2)
            return None

        mock_session.execute.side_effect = timeout_query

        # 设置很短的超时时间
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            result = await _check_database(mock_session)

            assert result["healthy"] is False
            assert result["status"] == "unhealthy"


class TestHealthCheckEndpoints:
    """测试健康检查端点（如果可以导入的话）"""

    def test_health_check_constants(self):
        """测试健康检查常量"""
        # 这些常量应该存在
        from src.api import health

        assert hasattr(health, "_app_start_time")
        assert hasattr(health, "router")

        # 验证启动时间是一个数字
        assert isinstance(health._app_start_time, float)
        assert health._app_start_time > 0

    def test_router_configuration(self):
        """测试路由配置"""
        from src.api import health

        # 检查路由器标签
        assert "健康检查" in health.router.tags

        # 检查是否有路由
        routes = [str(route.path) for route in health.router.routes]
        assert "" in routes or "/" in routes  # 主健康检查端点

    def test_import_health_module(self):
        """测试health模块可以正常导入"""
        from src.api import health

        # 检查关键函数是否可以导入
        assert callable(health.ServiceCheckError)
        assert callable(health._optional_check_skipped)
        assert callable(health._optional_checks_enabled)
        assert callable(health._check_database)

    def test_circuit_breaker_exists(self):
        """测试熔断器存在"""
        from src.api import health

        # 检查熔断器是否定义
        assert hasattr(health, "_redis_circuit_breaker")
        assert hasattr(health, "_kafka_circuit_breaker")
        assert hasattr(health, "_mlflow_circuit_breaker")

    def test_environment_variables_handling(self):
        """测试环境变量处理"""
        import os

        # 临时设置环境变量
        original_fast_fail = os.environ.get("FAST_FAIL")
        original_minimal = os.environ.get("MINIMAL_HEALTH_MODE")

        try:
            os.environ["FAST_FAIL"] = "true"
            os.environ["MINIMAL_HEALTH_MODE"] = "false"

            # 重新导入模块以测试
            import importlib
            import src.api.health
            importlib.reload(src.api.health)

            # 验证环境变量被正确读取
            from src.api.health import FAST_FAIL, MINIMAL_HEALTH_MODE
            assert FAST_FAIL is True
            assert MINIMAL_HEALTH_MODE is False

        finally:
            # 恢复原始环境变量
            if original_fast_fail is not None:
                os.environ["FAST_FAIL"] = original_fast_fail
            else:
                os.environ.pop("FAST_FAIL", None)

            if original_minimal is not None:
                os.environ["MINIMAL_HEALTH_MODE"] = original_minimal
            else:
                os.environ.pop("MINIMAL_HEALTH_MODE", None)