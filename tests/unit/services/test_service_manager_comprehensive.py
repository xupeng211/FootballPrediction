"""
服务管理器测试
Service Manager Tests

测试服务管理器的核心功能。
Tests core functionality of service manager.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.services.manager.manager import ServiceManager, service_manager, _ensure_default_services


class MockBaseService:
    """模拟基础服务类"""

    def __init__(self, name: str):
        self.name = name
        self.initialized = False
        self.shutdown_called = False

    async def initialize(self) -> bool:
        """初始化服务"""
        self.initialized = True
        return True

    async def shutdown(self) -> None:
        """关闭服务"""
        self.shutdown_called = True


class FailingService:
    """失败的服务类"""

    def __init__(self, name: str):
        self.name = name
        self.initialized = False
        self.shutdown_called = False

    async def initialize(self) -> bool:
        """初始化失败"""
        raise Exception(f"Service {self.name} failed to initialize")

    async def shutdown(self) -> None:
        """关闭失败"""
        raise Exception(f"Service {self.name} failed to shutdown")


class TestServiceManagerBasic:
    """测试服务管理器基础功能"""

    def test_service_manager_initialization(self):
        """测试服务管理器初始化"""
        manager = ServiceManager()

        assert manager.services == {}
        assert hasattr(manager, 'logger')
        assert len(manager.services) == 0

    def test_register_service_success(self):
        """测试成功注册服务"""
        manager = ServiceManager()
        service = MockBaseService("test_service")

        manager.register_service("test_service", service)

        assert "test_service" in manager.services
        assert manager.services["test_service"] == service
        assert len(manager.services) == 1

    def test_register_service_duplicate_same_instance(self):
        """测试注册相同服务实例"""
        manager = ServiceManager()
        service = MockBaseService("test_service")

        manager.register_service("test_service", service)
        manager.register_service("test_service", service)  # 重复注册相同实例

        assert len(manager.services) == 1
        assert manager.services["test_service"] == service

    def test_register_service_duplicate_same_class(self):
        """测试注册相同类不同实例"""
        manager = ServiceManager()
        service1 = MockBaseService("test_service")
        service2 = MockBaseService("test_service")

        manager.register_service("test_service", service1)
        manager.register_service("test_service", service2)  # 相同类不同实例

        assert len(manager.services) == 1
        assert manager.services["test_service"] == service1  # 应该保持第一个

    def test_register_service_replacement(self):
        """测试替换已注册服务"""
        manager = ServiceManager()
        service1 = MockBaseService("old_service")
        service2 = MockBaseService("new_service")

        manager.register_service("test_service", service1)
        manager.register_service("test_service", service2)  # 不同类，应该替换

        assert len(manager.services) == 1
        assert manager.services["test_service"] == service2

    def test_get_service_exists(self):
        """测试获取存在的服务"""
        manager = ServiceManager()
        service = MockBaseService("test_service")
        manager.register_service("test_service", service)

        retrieved_service = manager.get_service("test_service")

        assert retrieved_service == service

    def test_get_service_not_exists(self):
        """测试获取不存在的服务"""
        manager = ServiceManager()

        retrieved_service = manager.get_service("nonexistent_service")

        assert retrieved_service is None

    def test_list_services(self):
        """测试列出所有服务"""
        manager = ServiceManager()
        service1 = MockBaseService("service1")
        service2 = MockBaseService("service2")
        service3 = MockBaseService("service3")

        manager.register_service("service1", service1)
        manager.register_service("service2", service2)
        manager.register_service("service3", service3)

        services = manager.list_services()

        assert len(services) == 3
        assert "service1" in services
        assert "service2" in services
        assert "service3" in services
        assert services["service1"] == service1
        assert services["service2"] == service2
        assert services["service3"] == service3

    def test_services_property(self):
        """测试services属性"""
        manager = ServiceManager()
        service = MockBaseService("test_service")
        manager.register_service("test_service", service)

        services = manager.services

        assert services == manager._services
        assert "test_service" in services

    def test_list_services_empty(self):
        """测试列出空服务列表"""
        manager = ServiceManager()

        services = manager.list_services()

        assert services == {}
        assert len(services) == 0


class TestServiceManagerLifecycle:
    """测试服务管理器生命周期管理"""

    @pytest.mark.asyncio
    async def test_initialize_all_success(self):
        """测试成功初始化所有服务"""
        manager = ServiceManager()
        service1 = MockBaseService("service1")
        service2 = MockBaseService("service2")
        service3 = MockBaseService("service3")

        manager.register_service("service1", service1)
        manager.register_service("service2", service2)
        manager.register_service("service3", service3)

        result = await manager.initialize_all()

        assert result is True
        assert service1.initialized is True
        assert service2.initialized is True
        assert service3.initialized is True

    @pytest.mark.asyncio
    async def test_initialize_all_with_failure(self):
        """测试初始化时部分服务失败"""
        manager = ServiceManager()
        service1 = MockBaseService("service1")
        failing_service = FailingService("failing_service")
        service3 = MockBaseService("service3")

        manager.register_service("service1", service1)
        manager.register_service("failing_service", failing_service)
        manager.register_service("service3", service3)

        result = await manager.initialize_all()

        assert result is False  # 应该返回False因为有服务失败
        assert service1.initialized is True  # 成功的服务应该被初始化
        assert service3.initialized is True  # 成功的服务应该被初始化

    @pytest.mark.asyncio
    async def test_initialize_all_empty(self):
        """测试初始化空服务列表"""
        manager = ServiceManager()

        result = await manager.initialize_all()

        assert result is True

    @pytest.mark.asyncio
    async def test_shutdown_all_success(self):
        """测试成功关闭所有服务"""
        manager = ServiceManager()
        service1 = MockBaseService("service1")
        service2 = MockBaseService("service2")
        service3 = MockBaseService("service3")

        manager.register_service("service1", service1)
        manager.register_service("service2", service2)
        manager.register_service("service3", service3)

        await manager.shutdown_all()

        assert service1.shutdown_called is True
        assert service2.shutdown_called is True
        assert service3.shutdown_called is True

    @pytest.mark.asyncio
    async def test_shutdown_all_with_failure(self):
        """测试关闭时部分服务失败"""
        manager = ServiceManager()
        service1 = MockBaseService("service1")
        failing_service = FailingService("failing_service")
        service3 = MockBaseService("service3")

        manager.register_service("service1", service1)
        manager.register_service("failing_service", failing_service)
        manager.register_service("service3", service3)

        # 关闭失败不应该抛出异常
        await manager.shutdown_all()

        assert service1.shutdown_called is True
        assert service3.shutdown_called is True

    @pytest.mark.asyncio
    async def test_shutdown_all_empty(self):
        """测试关闭空服务列表"""
        manager = ServiceManager()

        # 不应该抛出异常
        await manager.shutdown_all()

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """测试完整的生命周期"""
        manager = ServiceManager()
        services = []

        # 创建多个服务
        for i in range(5):
            service = MockBaseService(f"service_{i}")
            services.append(service)
            manager.register_service(f"service_{i}", service)

        # 初始化所有服务
        init_result = await manager.initialize_all()
        assert init_result is True
        assert all(service.initialized for service in services)

        # 关闭所有服务
        await manager.shutdown_all()
        assert all(service.shutdown_called for service in services)


class TestServiceManagerEdgeCases:
    """测试服务管理器边界情况"""

    def test_register_service_with_none_name(self):
        """测试使用None名称注册服务"""
        manager = ServiceManager()
        service = MockBaseService("test")

        # 不应该抛出异常
        manager.register_service(None, service)  # type: ignore

        assert None in manager.services  # type: ignore

    def test_register_service_with_empty_name(self):
        """测试使用空字符串名称注册服务"""
        manager = ServiceManager()
        service = MockBaseService("test")

        manager.register_service("", service)

        assert "" in manager.services

    def test_get_service_with_none_name(self):
        """测试使用None名称获取服务"""
        manager = ServiceManager()

        service = manager.get_service(None)  # type: ignore
        assert service is None

    def test_register_service_with_long_name(self):
        """测试使用很长名称注册服务"""
        manager = ServiceManager()
        service = MockBaseService("test")
        long_name = "a" * 1000

        manager.register_service(long_name, service)

        assert long_name in manager.services

    def test_get_service_with_long_name(self):
        """测试使用很长名称获取服务"""
        manager = ServiceManager()
        service = MockBaseService("test")
        long_name = "a" * 1000
        manager.register_service(long_name, service)

        retrieved_service = manager.get_service(long_name)
        assert retrieved_service == service

    @pytest.mark.asyncio
    async def test_initialize_with_exception_types(self):
        """测试各种异常类型的初始化"""
        manager = ServiceManager()

        # 测试不同类型的异常
        class ValueErrorService:
            def __init__(self):
                self.name = "value_error_service"
            async def initialize(self):
                raise ValueError("Value error")

        class TypeErrorService:
            def __init__(self):
                self.name = "type_error_service"
            async def initialize(self):
                raise TypeError("Type error")

        class KeyErrorService:
            def __init__(self):
                self.name = "key_error_service"
            async def initialize(self):
                raise KeyError("Key error")

        class RuntimeErrorService:
            def __init__(self):
                self.name = "runtime_error_service"
            async def initialize(self):
                raise RuntimeError("Runtime error")

        services = [ValueErrorService(), TypeErrorService(), KeyErrorService(), RuntimeErrorService()]
        for service in services:
            manager.register_service(service.name, service)

        result = await manager.initialize_all()
        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_with_exception_types(self):
        """测试各种异常类型的关闭"""
        manager = ServiceManager()

        # 测试不同类型的异常
        class ValueErrorShutdownService:
            def __init__(self):
                self.name = "value_error_shutdown_service"
            async def initialize(self):
                return True
            async def shutdown(self):
                raise ValueError("Value error during shutdown")

        class TypeErrorShutdownService:
            def __init__(self):
                self.name = "type_error_shutdown_service"
            async def initialize(self):
                return True
            async def shutdown(self):
                raise TypeError("Type error during shutdown")

        services = [ValueErrorShutdownService(), TypeErrorShutdownService()]
        for service in services:
            manager.register_service(service.name, service)

        # 初始化应该成功
        await manager.initialize_all()

        # 关闭不应该抛出异常
        await manager.shutdown_all()


class TestServiceManagerIntegration:
    """测试服务管理器集成功能"""

    @pytest.mark.asyncio
    async def test_concurrent_registration(self):
        """测试并发注册服务"""
        import asyncio

        manager = ServiceManager()

        async def register_service_batch(start_id: int, count: int):
            """注册一批服务"""
            for i in range(count):
                service = MockBaseService(f"service_{start_id + i}")
                manager.register_service(f"service_{start_id + i}", service)
                await asyncio.sleep(0.001)  # 小延迟模拟并发

        # 创建多个并发注册任务
        tasks = [
            register_service_batch(0, 5),
            register_service_batch(5, 5),
            register_service_batch(10, 5)
        ]

        await asyncio.gather(*tasks)

        # 验证所有服务都被注册
        assert len(manager.services) == 15
        for i in range(15):
            assert f"service_{i}" in manager.services

    @pytest.mark.asyncio
    async def test_service_dependency_simulation(self):
        """模拟服务依赖关系"""
        manager = ServiceManager()

        class DatabaseService:
            def __init__(self):
                self.name = "database"
                self.connected = False
            async def initialize(self):
                await asyncio.sleep(0.1)  # 模拟数据库连接
                self.connected = True
                return True
            async def shutdown(self):
                self.connected = False

        class CacheService:
            def __init__(self):
                self.name = "cache"
                self.connected = False
            async def initialize(self):
                await asyncio.sleep(0.05)  # 模拟缓存连接
                self.connected = True
                return True
            async def shutdown(self):
                self.connected = False

        class ApiService:
            def __init__(self):
                self.name = "api"
                self.running = False
            async def initialize(self):
                await asyncio.sleep(0.02)  # 模拟API服务启动
                self.running = True
                return True
            async def shutdown(self):
                self.running = False

        # 注册服务（注意：注册顺序就是初始化顺序）
        db_service = DatabaseService()
        cache_service = CacheService()
        api_service = ApiService()

        manager.register_service("database", db_service)
        manager.register_service("cache", cache_service)
        manager.register_service("api", api_service)

        # 初始化所有服务
        result = await manager.initialize_all()
        assert result is True
        assert db_service.connected is True
        assert cache_service.connected is True
        assert api_service.running is True

        # 关闭所有服务
        await manager.shutdown_all()
        assert db_service.connected is False
        assert cache_service.connected is False
        assert api_service.running is False

    def test_service_manager_state_persistence(self):
        """测试服务管理器状态持久性"""
        manager = ServiceManager()

        # 注册多个服务
        for i in range(10):
            service = MockBaseService(f"service_{i}")
            manager.register_service(f"service_{i}", service)

        # 验证服务列表
        assert len(manager.services) == 10

        # 获取服务列表的副本
        services_copy = manager.list_services()

        # 修改副本不应该影响原列表
        services_copy["new_service"] = MockBaseService("new_service")
        assert len(manager.services) == 10  # 原列表不应该被修改
        assert "new_service" not in manager.services

        # 修改原列表
        manager.register_service("new_service", MockBaseService("new_service"))
        assert len(manager.services) == 11
        assert "new_service" in manager.services

    @patch('src.services.manager.manager.logger')
    def test_logging_behavior(self, mock_logger):
        """测试日志记录行为"""
        manager = ServiceManager()
        service1 = MockBaseService("service1")
        service2 = MockBaseService("service2")

        # 测试注册日志
        manager.register_service("service1", service1)
        mock_logger.info.assert_called_with("已注册服务: service1")

        # 测试重复注册日志
        manager.register_service("service1", service1)
        mock_logger.debug.assert_called_with("服务已存在,跳过重复注册: service1")

        # 测试替换服务日志
        service3 = MockBaseService("service3")
        manager.register_service("service1", service3)
        mock_logger.warning.assert_called()

    def test_service_replacement_with_different_classes(self):
        """测试替换不同类的服务"""
        manager = ServiceManager()

        class ServiceA:
            def __init__(self):
                self.name = "service_a"

        class ServiceB:
            def __init__(self):
                self.name = "service_b"

        service_a = ServiceA()
        service_b = ServiceB()

        manager.register_service("test_service", service_a)
        manager.register_service("test_service", service_b)

        # 应该被替换
        assert manager.services["test_service"] == service_b


class TestGlobalServiceManager:
    """测试全局服务管理器实例"""

    def test_global_service_manager_instance(self):
        """测试全局服务管理器实例"""
        from src.services.manager.manager import service_manager

        assert isinstance(service_manager, ServiceManager)
        assert service_manager.services is not None

    def test_global_service_manager_singleton(self):
        """测试全局服务管理器单例"""
        from src.services.manager.manager import service_manager

        # 获取多次应该是同一个实例
        manager1 = service_manager
        manager2 = service_manager

        assert manager1 is manager2

    @patch('src.services.manager.manager.get_settings')
    def test_ensure_default_services_empty_config(self, mock_get_settings):
        """测试空配置下的默认服务确保"""
        mock_settings = Mock()
        mock_settings.enabled_services = []
        mock_get_settings.return_value = mock_settings

        # 应该不抛出异常
        _ensure_default_services()

    @patch('src.services.manager.manager.get_settings')
    @patch('src.services.manager.manager.service_manager')
    def test_ensure_default_services_with_config(self, mock_manager, mock_get_settings):
        """测试有配置的默认服务确保"""
        mock_settings = Mock()
        mock_settings.enabled_services = ["ContentAnalysisService", "UserProfileService"]
        mock_get_settings.return_value = mock_settings

        # 模拟服务管理器
        mock_services = {}
        mock_manager.services = mock_services
        mock_manager.register_service = Mock()
        mock_manager.logger = Mock()

        _ensure_default_services()

        # 验证注册调用
        assert mock_manager.register_service.call_count == 2

    @patch('src.services.manager.manager.get_settings')
    @patch('src.services.manager.manager.service_manager')
    def test_ensure_default_services_unknown_service(self, mock_manager, mock_get_settings):
        """测试未知服务名称的处理"""
        mock_settings = Mock()
        mock_settings.enabled_services = ["UnknownService"]
        mock_get_settings.return_value = mock_settings

        mock_services = {}
        mock_manager.services = mock_services
        mock_manager.register_service = Mock()
        mock_manager.logger = Mock()

        _ensure_default_services()

        # 不应该注册任何服务
        mock_manager.register_service.assert_not_called()
        mock_manager.logger.warning.assert_called_once()

    def test_service_factories_dict(self):
        """测试服务工厂字典"""
        from src.services.manager.manager import _SERVICE_FACTORIES

        assert isinstance(_SERVICE_FACTORIES, dict)
        assert "ContentAnalysisService" in _SERVICE_FACTORIES
        assert "UserProfileService" in _SERVICE_FACTORIES
        assert "DataProcessingService" in _SERVICE_FACTORIES