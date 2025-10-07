"""
独立的健康检查测试
不依赖conftest，直接测试health.py模块
"""

import sys
import os
import asyncio
import time
from unittest.mock import MagicMock, patch

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# 直接导入模块，绕过services导入
import importlib.util
spec = importlib.util.spec_from_file_location("health", "src/api/health.py")
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)

# 导入pytest用于装饰器
try:
    import pytest
except ImportError:
    pytest = None


class TestHealthModuleStandalone:
    """独立测试health模块"""

    def test_constants(self):
        """测试常量定义"""
        assert hasattr(health, '_app_start_time')
        assert hasattr(health, 'router')
        assert hasattr(health, 'ServiceCheckError')

        # 验证启动时间
        assert isinstance(health._app_start_time, float)
        assert health._app_start_time > 0

        # 验证路由标签
        assert "健康检查" in health.router.tags

    def test_service_check_error(self):
        """测试ServiceCheckError异常"""
        # 基本异常
        error1 = health.ServiceCheckError("Test message")
        assert str(error1) == "Test message"
        assert error1.details == {}

        # 带详细信息的异常
        details = {"code": 500, "service": "redis"}
        error2 = health.ServiceCheckError("Test error", details=details)
        assert str(error2) == "Test error"
        assert error2.details == details

    def test_optional_check_skipped(self):
        """测试_optional_check_skipped函数"""
        service = "Redis"
        result = health._optional_check_skipped(service)

        assert result["healthy"] is True
        assert result["status"] == "skipped"
        assert result["response_time_ms"] == 0.0
        assert service in result["details"]["message"]

    def test_optional_checks_enabled(self):
        """测试_optional_checks_enabled函数"""
        # 模拟环境变量
        with patch.object(health, 'FAST_FAIL', True):
            with patch.object(health, 'MINIMAL_HEALTH_MODE', False):
                assert health._optional_checks_enabled() is True

        with patch.object(health, 'FAST_FAIL', False):
            with patch.object(health, 'MINIMAL_HEALTH_MODE', False):
                assert health._optional_checks_enabled() is False

        with patch.object(health, 'FAST_FAIL', True):
            with patch.object(health, 'MINIMAL_HEALTH_MODE', True):
                assert health._optional_checks_enabled() is False

    @pytest.mark.asyncio
    async def test_check_database_success(self):
        """测试数据库检查成功"""
        mock_session = MagicMock()
        mock_session.execute.return_value = None

        result = await health._check_database(mock_session)

        assert result["healthy"] is True
        assert result["status"] == "healthy"
        assert "数据库连接正常" in result["details"]["message"]

    @pytest.mark.asyncio
    async def test_check_database_failure(self):
        """测试数据库检查失败"""
        from sqlalchemy.exc import SQLAlchemyError

        mock_session = MagicMock()
        mock_session.execute.side_effect = SQLAlchemyError("Connection failed")

        result = await health._check_database(mock_session)

        assert result["healthy"] is False
        assert result["status"] == "unhealthy"
        assert "Connection failed" in result["details"]["error"]

    def test_circuit_breakers(self):
        """测试熔断器定义"""
        assert hasattr(health, '_redis_circuit_breaker')
        assert hasattr(health, '_kafka_circuit_breaker')
        assert hasattr(health, '_mlflow_circuit_breaker')

        # 验证熔断器属性
        assert health._redis_circuit_breaker.failure_threshold == 3
        assert health._redis_circuit_breaker.recovery_timeout == 30.0
        assert health._redis_circuit_breaker.retry_timeout == 10.0

    def test_environment_variables(self):
        """测试环境变量处理"""
        import os

        # 保存原始值
        original_fast_fail = os.environ.get("FAST_FAIL")
        original_minimal = os.environ.get("MINIMAL_HEALTH_MODE")

        try:
            # 测试不同的环境变量组合
            test_cases = [
                ("true", "false", True),
                ("false", "false", False),
                ("true", "true", False),
                ("false", "true", False),
            ]

            for fast_fail, minimal, expected in test_cases:
                with patch.object(health, 'FAST_FAIL', fast_fail == "true"):
                    with patch.object(health, 'MINIMAL_HEALTH_MODE', minimal == "true"):
                        assert health._optional_checks_enabled() == expected

        finally:
            # 恢复原始值
            if original_fast_fail is not None:
                os.environ["FAST_FAIL"] = original_fast_fail
            if original_minimal is not None:
                os.environ["MINIMAL_HEALTH_MODE"] = original_minimal

    @pytest.mark.asyncio
    async def test_collect_database_health_no_manager(self):
        """测试数据库管理器未初始化"""
        with patch('src.api.health.get_database_manager') as mock_get:
            mock_get.side_effect = RuntimeError("Manager not initialized")

            result = await health._collect_database_health()

            assert result["status"] == "skipped"
            assert "Database manager not initialised" in result["details"]["message"]

    @pytest.mark.asyncio
    async def test_collect_database_health_session_error(self):
        """测试数据库会话错误"""
        mock_manager = MagicMock()
        mock_manager.get_session.side_effect = RuntimeError("Session error")

        with patch('src.api.health.get_database_manager', return_value=mock_manager):
            result = await health._collect_database_health()

            assert result["status"] == "skipped"
            assert "Database session unavailable" in result["details"]["message"]

    def test_import_success(self):
        """测试模块导入成功"""
        # 验证关键函数和类存在
        required_items = [
            'ServiceCheckError',
            '_optional_check_skipped',
            '_optional_checks_enabled',
            '_check_database',
            '_collect_database_health',
            'health_check',
            'liveness_check',
            'readiness_check'
        ]

        for item in required_items:
            assert hasattr(health, item), f"Missing {item} in health module"

    def test_router_has_routes(self):
        """测试路由器有路由定义"""
        routes = list(health.router.routes)
        assert len(routes) > 0, "Router should have at least one route"

        # 检查路由路径
        paths = [route.path for route in routes]
        assert any(path in ['', '/'] for path in paths), "Should have health check endpoint"

    def test_uptime_calculation(self):
        """测试运行时间计算"""
        current_time = time.time()
        with patch.object(health, '_app_start_time', current_time - 100):
            uptime = current_time - health._app_start_time
            assert 99 <= uptime <= 101  # 允许1秒误差

    def test_error_details_format(self):
        """测试错误详情格式"""
        error = health.ServiceCheckError(
            "Service unavailable",
            details={
                "service": "Redis",
                "host": "localhost",
                "port": 6379,
                "error_code": "ECONNREFUSED"
            }
        )

        assert error.details["service"] == "Redis"
        assert error.details["host"] == "localhost"
        assert error.details["port"] == 6379
        assert error.details["error_code"] == "ECONNREFUSED"


if __name__ == "__main__":
    # 运行测试
    import pytest

    # 修改asyncio事件循环策略以避免警告
    import asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    pytest.main([__file__, "-v"])