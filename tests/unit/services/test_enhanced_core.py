"""
增强服务核心模块测试
Tests for Enhanced Core Module
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import time

from src.services.enhanced_core import (
    ServiceConfig,
    ServiceMetrics,
    EnhancedBaseService,
    BaseService,
    AbstractBaseService,
)


class TestServiceConfig:
    """测试服务配置类"""

    def test_service_config_creation_minimal(self):
        """测试：最小参数创建配置"""
        # When
        config = ServiceConfig(name="TestService")

        # Then
        assert config.name == "TestService"
        assert config.version == "1.0.0"
        assert config.description == ""
        assert config.dependencies == []
        assert config.config == {}
        assert isinstance(config.created_at, datetime)

    def test_service_config_creation_full(self):
        """测试：完整参数创建配置"""
        # Given
        dependencies = ["service1", "service2"]
        config_dict = {"timeout": 30, "retries": 3}

        # When
        config = ServiceConfig(
            name="FullService",
            version="2.0.0",
            description="A test service with full config",
            dependencies=dependencies,
            config=config_dict
        )

        # Then
        assert config.name == "FullService"
        assert config.version == "2.0.0"
        assert config.description == "A test service with full config"
        assert config.dependencies == dependencies
        assert config.config == config_dict

    def test_service_config_empty_lists(self):
        """测试：空列表参数"""
        # When
        config = ServiceConfig(
            name="TestService",
            dependencies=[],
            config={}
        )

        # Then
        assert config.dependencies == []
        assert config.config == {}


class TestServiceMetrics:
    """测试服务指标类"""

    def test_metrics_initialization(self):
        """测试：指标初始化"""
        # When
        metrics = ServiceMetrics()

        # Then
        assert metrics.metrics["calls"] == 0
        assert metrics.metrics["errors"] == 0
        assert metrics.metrics["total_time"] == 0.0
        assert metrics.metrics["avg_time"] == 0.0
        assert metrics.metrics["last_call"] is None

    def test_record_call_success(self):
        """测试：记录成功调用"""
        # Given
        metrics = ServiceMetrics()
        duration = 0.5

        # When
        metrics.record_call(duration, success=True)

        # Then
        assert metrics.metrics["calls"] == 1
        assert metrics.metrics["errors"] == 0
        assert metrics.metrics["total_time"] == 0.5
        assert metrics.metrics["avg_time"] == 0.5
        assert isinstance(metrics.metrics["last_call"], datetime)

    def test_record_call_error(self):
        """测试：记录失败调用"""
        # Given
        metrics = ServiceMetrics()
        duration = 0.3

        # When
        metrics.record_call(duration, success=False)

        # Then
        assert metrics.metrics["calls"] == 1
        assert metrics.metrics["errors"] == 1
        assert metrics.metrics["total_time"] == 0.3
        assert metrics.metrics["avg_time"] == 0.3

    def test_multiple_calls(self):
        """测试：多次调用"""
        # Given
        metrics = ServiceMetrics()

        # When
        metrics.record_call(0.1, True)
        metrics.record_call(0.2, True)
        metrics.record_call(0.3, False)

        # Then
        assert metrics.metrics["calls"] == 3
        assert metrics.metrics["errors"] == 1
        assert abs(metrics.metrics["total_time"] - 0.6) < 0.0001
        assert abs(metrics.metrics["avg_time"] - 0.2) < 0.0001

    def test_get_metrics(self):
        """测试：获取指标副本"""
        # Given
        metrics = ServiceMetrics()
        metrics.record_call(1.0, True)

        # When
        result = metrics.get_metrics()

        # Then
        assert result is not metrics.metrics  # 应该是副本
        assert result["calls"] == 1
        assert result["total_time"] == 1.0


class MockEnhancedService(EnhancedBaseService):
    """用于测试的模拟增强服务"""

    def __init__(self, config=None):
        super().__init__(config)
        self.initialize_called = False
        self.shutdown_called = False
        self.initialize_error = None
        self.shutdown_error = None

    async def initialize(self):
        if self.initialize_error:
            raise self.initialize_error
        self.initialize_called = True
        self._initialized = True

    async def shutdown(self):
        if self.shutdown_error:
            raise self.shutdown_error
        self.shutdown_called = True


class TestEnhancedBaseService:
    """测试增强基础服务类"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        config = ServiceConfig(
            name="TestService",
            version="1.0.0",
            description="Test service for unit tests"
        )
        return MockEnhancedService(config)

    def test_service_initialization(self, service):
        """测试：服务初始化"""
        assert service.name == "TestService"
        assert service.version == "1.0.0"
        assert service.description == "Test service for unit tests"
        assert service._running is False
        assert service._initialized is False
        assert service._startup_time is None
        assert isinstance(service.metrics, ServiceMetrics)
        assert service._health_status["status"] == "unknown"
        assert len(service._dependencies) == 0

    def test_service_initialization_without_config(self):
        """测试：不带配置的服务初始化"""
        # When
        service = MockEnhancedService()

        # Then
        assert service.name == "MockEnhancedService"
        assert service.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_start_success(self, service):
        """测试：成功启动服务"""
        # When
        result = await service.start()

        # Then
        assert result is True
        assert service._running is True
        assert service._initialized is True
        assert service._startup_time is not None
        assert service._health_status["status"] == "healthy"
        assert service.initialize_called is True

    @pytest.mark.asyncio
    async def test_start_already_running(self, service):
        """测试：启动已运行的服务"""
        # Given
        await service.start()

        # When
        result = await service.start()

        # Then
        assert result is True
        # startup_time不应该更新
        original_time = service._startup_time
        await service.start()
        assert service._startup_time == original_time

    @pytest.mark.asyncio
    async def test_start_failure(self):
        """测试：启动失败"""
        # Given
        service = MockEnhancedService()
        service.initialize_error = RuntimeError("Initialization failed")

        # When
        result = await service.start()

        # Then
        assert result is False
        assert service._running is False
        assert service._health_status["status"] == "unhealthy"
        assert "Initialization failed" in service._health_status["message"]

    @pytest.mark.asyncio
    async def test_stop_success(self, service):
        """测试：成功停止服务"""
        # Given
        await service.start()

        # When
        result = await service.stop()

        # Then
        assert result is True
        assert service._running is False
        assert service._initialized is False
        assert service._health_status["status"] == "stopped"
        assert service.shutdown_called is True

    @pytest.mark.asyncio
    async def test_stop_not_running(self, service):
        """测试：停止未运行的服务"""
        # When
        result = await service.stop()

        # Then
        assert result is True
        assert service._running is False

    @pytest.mark.asyncio
    async def test_stop_failure(self, service):
        """测试：停止失败"""
        # Given
        await service.start()
        service.shutdown_error = RuntimeError("Shutdown failed")

        # When
        result = await service.stop()

        # Then
        assert result is False
        # 服务应该仍然在运行
        assert service._running is True

    def test_get_status_not_initialized(self, service):
        """测试：获取未初始化状态"""
        # When
        status = service.get_status()

        # Then
        assert status == "not_initialized"

    def test_get_status_running(self, service):
        """测试：获取运行状态"""
        # Given
        service._initialized = True
        service._running = True

        # When
        status = service.get_status()

        # Then
        assert status == "running"

    def test_get_status_stopped(self, service):
        """测试：获取停止状态"""
        # Given
        service._initialized = True
        service._running = False

        # When
        status = service.get_status()

        # Then
        assert status == "stopped"

    def test_is_healthy(self, service):
        """测试：健康检查"""
        # Given
        service._health_status["status"] = "healthy"

        # When
        result = service.is_healthy()

        # Then
        assert result is True

    def test_is_unhealthy(self, service):
        """测试：不健康检查"""
        # Given
        service._health_status["status"] = "unhealthy"

        # When
        result = service.is_healthy()

        # Then
        assert result is False

    def test_get_health_info(self, service):
        """测试：获取健康信息"""
        # Given
        service._startup_time = datetime.now() - timedelta(seconds=60)
        service._initialized = True
        service._running = True
        service._health_status["status"] = "healthy"

        # When
        info = service.get_health_info()

        # Then
        assert info["service"] == "TestService"
        assert info["version"] == "1.0.0"
        assert info["status"] == "running"
        assert "uptime_seconds" in info
        assert info["uptime_seconds"] > 50
        assert "metrics" in info
        assert "dependencies" in info

    @pytest.mark.asyncio
    async def test_health_check_with_dependencies(self, service):
        """测试：带依赖的健康检查"""
        # Given
        service._initialized = True
        service._running = True
        healthy_dep = Mock()
        healthy_dep.is_healthy.return_value = True
        healthy_dep.name = "healthy_service"

        unhealthy_dep = Mock()
        unhealthy_dep.is_healthy.return_value = False
        unhealthy_dep.name = "unhealthy_service"

        service.add_dependency("healthy", healthy_dep)
        service.add_dependency("unhealthy", unhealthy_dep)

        # When
        result = await service.health_check()

        # Then
        # health_check返回get_health_info的结果，其中status来自get_status()
        # 但_message_字段包含健康状态信息
        assert "unhealthy" in result["message"]

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, service):
        """测试：所有依赖健康"""
        # Given
        service._initialized = True
        service._running = True
        dep = Mock()
        dep.is_healthy.return_value = True
        service.add_dependency("dep", dep)

        # When
        result = await service.health_check()

        # Then
        # status来自get_status()，不是health_status
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_execute_with_metrics_success(self, service):
        """测试：执行带指标（成功）"""
        # Given
        async def test_func():
            return "test_result"

        # When
        result = await service.execute_with_metrics("test_operation", test_func)

        # Then
        assert result == "test_result"
        metrics = service.metrics.get_metrics()
        assert metrics["calls"] == 1
        assert metrics["errors"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_metrics_error(self, service):
        """测试：执行带指标（失败）"""
        # Given
        async def failing_func():
            raise ValueError("Test error")

        # When / Then
        with pytest.raises(ValueError, match="Test error"):
            await service.execute_with_metrics("failing_operation", failing_func)

        metrics = service.metrics.get_metrics()
        assert metrics["calls"] == 1
        assert metrics["errors"] == 1

    def test_add_dependency(self, service):
        """测试：添加依赖"""
        # Given
        dep = Mock()

        # When
        service.add_dependency("test_dep", dep)

        # Then
        assert "test_dep" in service._dependencies
        assert service._dependencies["test_dep"] == dep

    def test_get_dependency(self, service):
        """测试：获取依赖"""
        # Given
        dep = Mock()
        service.add_dependency("test_dep", dep)

        # When
        result = service.get_dependency("test_dep")

        # Then
        assert result == dep

    def test_get_dependency_not_found(self, service):
        """测试：获取不存在的依赖"""
        # When
        result = service.get_dependency("nonexistent")

        # Then
        assert result is None

    def test_get_config(self, service):
        """测试：获取配置"""
        # Given
        service.config.config["test_key"] = "test_value"

        # When
        result = service.get_config("test_key")

        # Then
        assert result == "test_value"

    def test_get_config_default(self, service):
        """测试：获取配置（默认值）"""
        # When
        result = service.get_config("nonexistent", "default_value")

        # Then
        assert result == "default_value"

    def test_repr(self, service):
        """测试：字符串表示"""
        # When
        result = repr(service)

        # Then
        assert "MockEnhancedService" in result
        assert "name=TestService" in result
        assert "status=not_initialized" in result


class TestBaseService:
    """测试向后兼容的基础服务类"""

    def test_base_service_creation(self):
        """测试：创建基础服务"""
        # When
        service = BaseService("TestBaseService")

        # Then
        assert service.name == "TestBaseService"
        assert service.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_base_service_initialize(self):
        """测试：基础服务初始化"""
        # Given
        service = BaseService()

        # When
        await service.initialize()

        # Then
        assert service._initialized is True

    @pytest.mark.asyncio
    async def test_base_service_shutdown(self):
        """测试：基础服务关闭"""
        # Given
        service = BaseService()
        service._running = True
        service._initialized = True

        # When
        await service.shutdown()

        # Then
        assert service._running is False
        assert service._initialized is False


class TestAbstractBaseService:
    """测试抽象基础服务类"""

    def test_abstract_base_service_creation(self):
        """测试：抽象基础服务是抽象类"""
        # When / Then
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            AbstractBaseService("TestAbstractService")