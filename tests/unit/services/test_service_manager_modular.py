"""
测试模块化服务管理器
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from src.services.manager import (
    ServiceManager,
    ServiceRegistry,
    ServiceFactory,
    ServiceHealthChecker,
    get_service_manager,
    get_service,
    register_service,
)
from src.services.base import BaseService


class MockService(BaseService):
    """模拟服务类"""

    def __init__(self, name: str = "mock_service"):
        super().__init__()
        self.name = name
        self.initialized = False

    async def initialize(self) -> bool:
        self.initialized = True
        return True

    async def shutdown(self) -> None:
        self.initialized = False


class TestServiceManager:
    """测试服务管理器"""

    def test_register_service(self):
        """测试服务注册"""
        manager = ServiceManager("test")
        service = MockService()

        manager.register_service("test_service", service)
        assert manager.get_service("test_service") is service
        assert manager.service_count == 1

    def test_register_duplicate_service(self):
        """测试重复注册服务"""
        manager = ServiceManager("test")
        service = MockService()

        manager.register_service("test_service", service)
        # 重复注册相同实例应该被忽略
        manager.register_service("test_service", service)
        assert manager.service_count == 1

    def test_get_nonexistent_service(self):
        """测试获取不存在的服务"""
        manager = ServiceManager("test")
        assert manager.get_service("nonexistent") is None

    @pytest.mark.asyncio
    async def test_initialize_all_services(self):
        """测试初始化所有服务"""
        manager = ServiceManager("test")
        services = [MockService(f"service_{i}") for i in range(3)]

        for i, service in enumerate(services):
            manager.register_service(f"service_{i}", service)

        result = await manager.initialize_all()
        assert result is True

        for service in services:
            assert service.initialized is True

    @pytest.mark.asyncio
    async def test_shutdown_all_services(self):
        """测试关闭所有服务"""
        manager = ServiceManager("test")
        services = [MockService(f"service_{i}") for i in range(3)]

        for i, service in enumerate(services):
            manager.register_service(f"service_{i}", service)
            service.initialized = True

        await manager.shutdown_all()

        for service in services:
            assert service.initialized is False

    @pytest.mark.asyncio
    async def test_initialize_single_service(self):
        """测试初始化单个服务"""
        manager = ServiceManager("test")
        service = MockService()

        manager.register_service("test_service", service)
        result = await manager.initialize_service("test_service")

        assert result is True
        assert service.initialized is True
        assert "test_service" in manager.get_initialized_services()

    @pytest.mark.asyncio
    async def test_restart_service(self):
        """测试重启服务"""
        manager = ServiceManager("test")
        service = MockService()

        manager.register_service("test_service", service)
        await manager.initialize_service("test_service")

        # 重启服务
        result = await manager.restart_service("test_service")
        assert result is True
        assert service.initialized is True

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        manager = ServiceManager("test")

        # 添加有健康检查方法的服务
        service_with_health = MockService("health_service")
        service_with_health.health_check = lambda: True
        manager.register_service("health_service", service_with_health)

        # 添加没有健康检查方法的服务
        service_without_health = MockService("no_health_service")
        manager.register_service("no_health_service", service_without_health)

        health_status = await manager.health_check()

        assert health_status["health_service"] is True
        assert health_status["no_health_service"] is True  # 默认认为健康

    def test_service_info(self):
        """测试获取服务信息"""
        manager = ServiceManager("test")
        service = MockService("test_service")

        manager.register_service("test_service", service)
        info = manager.get_service_info("test_service")

        assert info is not None
        assert info["name"] == "test_service"
        assert info["class"] == "MockService"
        assert info["initialized"] is False


class TestServiceRegistry:
    """测试服务注册表"""

    def test_register_factory(self):
        """测试注册工厂"""
        registry = ServiceRegistry()
        registry.register_factory("test", MockService)

        assert registry.get_factory("test") is MockService

    def test_register_singleton(self):
        """测试注册单例"""
        registry = ServiceRegistry()
        service = MockService()
        registry.register_singleton("singleton", service)

        assert registry.get_singleton("singleton") is service

    def test_create_service(self):
        """测试创建服务"""
        registry = ServiceRegistry()
        registry.register_factory("test", MockService)

        service = registry.create_service("test")
        assert isinstance(service, MockService)

    def test_dependencies(self):
        """测试依赖管理"""
        registry = ServiceRegistry()
        registry.set_dependencies("service_a", ["service_b"])
        registry.set_dependencies("service_b", [])

        assert registry.get_dependencies("service_a") == ["service_b"]
        assert registry.get_dependencies("service_b") == []

    def test_validate_dependencies(self):
        """测试验证依赖"""
        registry = ServiceRegistry()
        registry.register_factory("service_a", MockService)
        registry.register_factory("service_b", MockService)
        registry.set_dependencies("service_a", ["service_b"])

        assert registry.validate_dependencies() is True

    def test_circular_dependency(self):
        """测试循环依赖"""
        registry = ServiceRegistry()
        registry.register_factory("service_a", MockService)
        registry.register_factory("service_b", MockService)
        registry.set_dependencies("service_a", ["service_b"])
        registry.set_dependencies("service_b", ["service_a"])

        with pytest.raises(ValueError, match="循环依赖"):
            registry.get_startup_order()


class TestServiceFactory:
    """测试服务工厂"""

    def test_register_builder(self):
        """测试注册构建器"""
        factory = ServiceFactory()
        builder = lambda: MockService()

        factory.register_builder("test", builder)
        service = factory.create_service("test")

        assert isinstance(service, MockService)

    def test_register_class(self):
        """测试注册类"""
        factory = ServiceFactory()
        factory.register_class("test", MockService)

        service = factory.create_service("test")
        assert isinstance(service, MockService)

    def test_apply_config(self):
        """测试应用配置"""
        factory = ServiceFactory()
        factory.register_class("test", MockService)

        config = {"name": "configured_service"}
        factory.set_config("test", config)

        service = factory.create_service("test")
        assert service.name == "configured_service"


class TestServiceHealthChecker:
    """测试服务健康检查器"""

    def test_register_check(self):
        """测试注册健康检查"""
        checker = ServiceHealthChecker()
        check_func = lambda: True

        checker.register_check("test", check_func)
        # 测试注册成功
        assert "test" in checker._health_checks

    @pytest.mark.asyncio
    async def test_check_service(self):
        """测试检查服务健康"""
        checker = ServiceHealthChecker()
        service = MockService()

        # 注册自定义检查函数
        checker.register_check("test", lambda: True)
        status = await checker.check_service("test", service)

        assert status.service_name == "test"
        assert status.healthy is True

    @pytest.mark.asyncio
    async def test_check_service_with_exception(self):
        """测试服务检查异常"""
        checker = ServiceHealthChecker()
        service = MockService()

        # 注册会抛出异常的检查函数
        checker.register_check("test", lambda: 1/0)
        status = await checker.check_service("test", service)

        assert status.healthy is False
        assert "Health check failed" in status.message

    def test_get_summary(self):
        """测试获取健康检查摘要"""
        checker = ServiceHealthChecker()
        from datetime import datetime

        # 添加一些状态
        from src.services.manager.health_checker import HealthStatus
        checker._health_status["service1"] = HealthStatus(
            "service1", True, "OK", datetime.now()
        )
        checker._health_status["service2"] = HealthStatus(
            "service2", False, "Failed", datetime.now()
        )

        summary = checker.get_summary()

        assert summary["total_services"] == 2
        assert summary["healthy_count"] == 1
        assert summary["unhealthy_count"] == 1
        assert summary["healthy_percentage"] == 50.0


class TestGlobalManager:
    """测试全局管理器"""

    def test_get_global_manager(self):
        """测试获取全局管理器"""
        manager1 = get_service_manager()
        manager2 = get_service_manager()

        # 应该返回同一个实例
        assert manager1 is manager2

    def test_register_service_global(self):
        """测试全局注册服务"""
        service = MockService("global_test")
        register_service("global_test", service)

        retrieved = get_service("global_test")
        assert retrieved is service