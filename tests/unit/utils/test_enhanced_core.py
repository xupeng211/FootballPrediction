"""
增强基础服务测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.enhanced_core import EnhancedBaseService, ServiceConfig


class TestServiceConfig:
    """服务配置测试"""

    def test_service_config_creation(self):
        """测试服务配置创建"""
        _config = ServiceConfig("test_service")

        assert _config.service_name == "test_service"
        assert _config.enabled is True
        assert _config.retry_attempts == 3
        assert _config.timeout == 30.0
        assert _config.health_check_interval == 60.0

    def test_service_config_custom(self):
        """测试自定义服务配置"""
        _config = ServiceConfig(
            "custom_service",
            enabled=False,
            retry_attempts=5,
            timeout=60.0,
            health_check_interval=120.0,
        )

        assert _config.service_name == "custom_service"
        assert _config.enabled is False
        assert _config.retry_attempts == 5
        assert _config.timeout == 60.0
        assert _config.health_check_interval == 120.0


class TestEnhancedBaseService:
    """增强基础服务测试"""

    @pytest.fixture
    def service_config(self):
        """服务配置"""
        return ServiceConfig("test_service")

    @pytest.fixture
    def enhanced_service(self, service_config):
        """增强基础服务实例"""
        return TestEnhancedService(service_config)

    def test_enhanced_service_init(self, enhanced_service, service_config):
        """测试增强服务初始化"""
        assert enhanced_service._config == service_config
        assert enhanced_service.service_name == "test_service"
        assert enhanced_service.metrics is not None
        assert enhanced_service.is_running is False

    @pytest.mark.asyncio
    async def test_service_lifecycle(self, enhanced_service):
        """测试服务生命周期"""
        # 启动服务
        await enhanced_service.start()
        assert enhanced_service.is_running is True
        assert enhanced_service.start_time is not None

        # 停止服务
        await enhanced_service.stop()
        assert enhanced_service.is_running is False

    @pytest.mark.asyncio
    async def test_health_check(self, enhanced_service):
        """测试健康检查"""
        health = await enhanced_service.health_check()
        assert health["status"] == "healthy"
        assert "uptime" in health
        assert "metrics" in health

    def test_record_metrics(self, enhanced_service):
        """测试记录指标"""
        # 记录成功指标
        enhanced_service.record_success("test_operation")
        metrics = enhanced_service.get_metrics()
        assert metrics["total_operations"] == 1
        assert metrics["successful_operations"] == 1

        # 记录失败指标
        enhanced_service.record_failure("test_operation")
        metrics = enhanced_service.get_metrics()
        assert metrics["total_operations"] == 2
        assert metrics["failed_operations"] == 1

    def test_get_uptime(self, enhanced_service):
        """测试获取运行时间"""
        # 未启动时返回0
        uptime = enhanced_service.get_uptime()
        assert uptime == 0

    def test_reset_metrics(self, enhanced_service):
        """测试重置指标"""
        # 记录一些指标
        enhanced_service.record_success("test_op")
        enhanced_service.record_failure("test_op")

        # 重置指标
        enhanced_service.reset_metrics()
        metrics = enhanced_service.get_metrics()
        assert metrics["total_operations"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_retry(self, enhanced_service):
        """测试带重试的执行"""
        # 测试成功的情况
        mock_func = AsyncMock(return_value="success")
        _result = await enhanced_service.execute_with_retry(mock_func)
        assert _result == "success"
        mock_func.assert_called_once()

        # 测试失败后重试
        mock_func_fail = AsyncMock(side_effect=[Exception("error"), "success"])
        _result = await enhanced_service.execute_with_retry(mock_func_fail)
        assert _result == "success"
        assert mock_func_fail.call_count == 2

        # 测试达到重试次数
        mock_func_always_fail = AsyncMock(side_effect=Exception("error"))
        with pytest.raises(Exception):
            await enhanced_service.execute_with_retry(mock_func_always_fail)

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, enhanced_service):
        """测试带超时的执行"""
        # 测试快速执行
        mock_func = AsyncMock(return_value="success")
        _result = await enhanced_service.execute_with_timeout(mock_func, timeout=1.0)
        assert _result == "success"

        # 测试超时
        async def slow_func():
            await asyncio.sleep(2)
            return "too slow"

        import asyncio

        with pytest.raises(asyncio.TimeoutError):
            await enhanced_service.execute_with_timeout(slow_func, timeout=0.1)


# 用于测试的增强服务实现
class TestEnhancedService(EnhancedBaseService):
    """测试用的增强服务"""

    def __init__(self, config: ServiceConfig):
        super().__init__(config)

    async def _perform_health_check(self) -> dict:
        """执行健康检查"""
        return {"status": "healthy", "checks": {"database": "ok", "cache": "ok"}}

    async def _do_start(self):
        """启动服务"""
        pass

    async def _do_stop(self):
        """停止服务"""
        pass
