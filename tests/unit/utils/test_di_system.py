# TODO: Consider creating a fixture for 7 repeated Mock creations

# TODO: Consider creating a fixture for 7 repeated Mock creations

from unittest.mock import Mock, patch, MagicMock
"""
依赖注入系统测试
"""

import pytest
from typing import Any, Dict, Optional, Type, TypeVar
from dataclasses import dataclass

# 使用try-except导入，如果模块不存在则跳过测试
try:
    from src.core.di import DIContainer, ServiceNotFoundError, CircularDependencyError
    from src.core.di_setup import DISetup
    from src.core.config_di import ConfigDI
    from src.core.auto_binding import AutoBinding
    from src.core.service_lifecycle import ServiceLifecycle, ServiceState

    DI_AVAILABLE = True
except ImportError:
    DI_AVAILABLE = False

TEST_SKIP_REASON = "DI module not available"


@pytest.mark.skipif(not DI_AVAILABLE, reason=TEST_SKIP_REASON)
@pytest.mark.unit

class TestDIContainer:
    """依赖注入容器测试"""

    def test_container_initialization(self):
        """测试容器初始化"""
        container = DIContainer()
        assert len(container._services) == 0
        assert len(container._singletons) == 0

    def test_register_singleton(self):
        """测试注册单例服务"""
        container = DIContainer()

        class TestService:
            def __init__(self):
                self.value = 42

        container.register_singleton(TestService)

        # 获取服务实例
        service1 = container.get(TestService)
        service2 = container.get(TestService)

        assert service1 is service2  # 应该是同一个实例
        assert service1.value == 42

    def test_register_factory(self):
        """测试注册工厂函数"""
        container = DIContainer()

        def create_service():
            return Mock(value="factory_created")

        container.register_factory(Mock, create_service)

        service = container.get(Mock)
        assert service.value == "factory_created"

    def test_register_instance(self):
        """测试注册实例"""
        container = DIContainer()

        instance = Mock(value="pre_created")
        container.register_instance(Mock, instance)

        service = container.get(Mock)
        assert service is instance
        assert service.value == "pre_created"

    def test_service_not_found(self):
        """测试服务未找到异常"""
        container = DIContainer()

        with pytest.raises(ServiceNotFoundError):
            container.get(Mock)

    def test_circular_dependency_detection(self):
        """测试循环依赖检测"""
        container = DIContainer()

        class ServiceA:
            def __init__(self, b: "ServiceB"):
                self.b = b

        class ServiceB:
            def __init__(self, a: ServiceA):
                self.a = a

        container.register_transient(ServiceA)
        container.register_transient(ServiceB)

        with pytest.raises(CircularDependencyError):
            container.get(ServiceA)

    def test_dependency_injection(self):
        """测试依赖注入"""
        container = DIContainer()

        class DatabaseService:
            def __init__(self):
                self.connection = "db_connection"

        class UserService:
            def __init__(self, db: DatabaseService):
                self.db = db

        container.register_singleton(DatabaseService)
        container.register_transient(UserService)

        user_service = container.get(UserService)
        assert user_service.db.connection == "db_connection"

    def test_scoped_services(self):
        """测试作用域服务"""
        container = DIContainer()

        class ScopedService:
            def __init__(self):
                self.id = id(self)

        container.register_scoped(ScopedService)

        # 在同一作用域内应该是同一个实例
        with container.create_scope() as scope:
            service1 = scope.get(ScopedService)
            service2 = scope.get(ScopedService)
            assert service1 is service2

        # 不同作用域应该是不同实例
        with container.create_scope() as scope:
            service3 = scope.get(ScopedService)
            assert service1 is not service3

    def test_conditional_registration(self):
        """测试条件注册"""
        container = DIContainer()

        container.register_conditional(
            Mock,
            lambda: True,  # 条件
            lambda: Mock(value="conditional"),
        )

        service = container.get(Mock)
        assert service.value == "conditional"

    def test_container_disposal(self):
        """测试容器资源释放"""
        container = DIContainer()

        disposable = Mock()
        disposable.dispose = Mock()

        container.register_instance(Mock, disposable)
        container.dispose()

        disposable.dispose.assert_called_once()


@pytest.mark.skipif(not DI_AVAILABLE, reason=TEST_SKIP_REASON)
class TestDISetup:
    """DI设置测试"""

    def test_setup_initialization(self):
        """测试DI设置初始化"""
        setup = DISetup()
        assert setup.container is not None

    def test_register_core_services(self):
        """测试注册核心服务"""
        setup = DISetup()
        setup.register_core_services()

        # 验证核心服务已注册
        assert setup.container.is_registered(dict)
        assert setup.container.is_registered(list)

    def test_register_database_services(self):
        """测试注册数据库服务"""
        setup = DISetup()

        with patch("src.core.di_setup.DatabaseManager") as mock_db:
            setup.register_database_services("sqlite:///:memory:")
            mock_db.assert_called_once()

    def test_register_cache_services(self):
        """测试注册缓存服务"""
        setup = DISetup()

        with patch("src.core.di_setup.CacheManager") as mock_cache:
            setup.register_cache_services(redis_url="redis://localhost")
            mock_cache.assert_called_once()

    def test_complete_setup(self):
        """测试完整设置"""
        setup = DISetup()

        # 模拟配置
        _config = {
            "database": {"url": "sqlite:///:memory:"},
            "cache": {"redis_url": "redis://localhost"},
            "logging": {"level": "INFO"},
        }

        setup.setup_all(config)

        # 验证所有服务都已注册
        assert setup.container.is_registered(dict)


@pytest.mark.skipif(not DI_AVAILABLE, reason=TEST_SKIP_REASON)
class TestConfigDI:
    """配置依赖注入测试"""

    def test_config_registration(self):
        """测试配置注册"""
        config_di = ConfigDI()

        config_data = {"app_name": "test_app", "debug": True}
        config_di.register_config("app", config_data)

        app_config = config_di.get_config("app")
        assert app_config["app_name"] == "test_app"
        assert app_config["debug"] is True

    def test_config_injection(self):
        """测试配置注入"""
        config_di = ConfigDI()
        container = DIContainer()

        # 注册配置
        config_di.register_config("database", {"url": "sqlite:///:memory:"})

        # 注入配置到容器
        config_di.inject_into(container)

        # 创建需要配置的服务
        class DatabaseService:
            def __init__(self, config: dict):
                self.db_url = _config.get("url")

        # 手动注入配置
        db_config = config_di.get_config("database")
        service = DatabaseService(db_config)

        assert service.db_url == "sqlite:///:memory:"

    def test_config_validation(self):
        """测试配置验证"""
        config_di = ConfigDI()

        # 定义配置模式
        schema = {
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
            },
            "required": ["host", "port"],
        }

        # 有效配置
        valid_config = {"host": "localhost", "port": 5432}
        assert config_di.validate_config(valid_config, schema) is True

        # 无效配置
        invalid_config = {"host": "localhost", "port": 70000}
        assert config_di.validate_config(invalid_config, schema) is False

    def test_config_hierarchy(self):
        """测试配置层次结构"""
        config_di = ConfigDI()

        # 注册层次化配置
        config_di.register_config("app", {"name": "test"})
        config_di.register_config("app.database", {"url": "sqlite:///:memory:"})
        config_di.register_config("app.cache", {"type": "redis"})

        # 获取嵌套配置
        app_config = config_di.get_config("app")
        assert "database" in app_config
        assert "cache" in app_config
        assert app_config["database"]["url"] == "sqlite:///:memory:"


@pytest.mark.skipif(not DI_AVAILABLE, reason=TEST_SKIP_REASON)
class TestAutoBinding:
    """自动绑定测试"""

    def test_auto_scan_interfaces(self):
        """测试自动扫描接口"""
        auto_binding = AutoBinding()

        # 创建测试接口和实现
        class TestInterface:
            pass

        class TestImplementation(TestInterface):
            def test_method(self):
                return "implementation"

        # 模拟扫描
        interfaces = [TestInterface]
        implementations = [TestImplementation]

        bindings = auto_binding.bind_interfaces_to_implementations(
            interfaces, implementations
        )

        assert TestInterface in bindings
        assert bindings[TestInterface] == TestImplementation

    def test_auto_bind_by_naming(self):
        """测试按命名自动绑定"""
        auto_binding = AutoBinding()

        class UserService:
            pass

        class UserServiceImpl:
            pass

        # 按命名规则绑定
        bindings = auto_binding.bind_by_naming(
            {"UserService": UserService}, {"UserServiceImpl": UserServiceImpl}
        )

        assert UserService in bindings
        assert bindings[UserService] == UserServiceImpl

    def test_auto_bind_with_attributes(self):
        """测试通过属性自动绑定"""
        auto_binding = AutoBinding()

        # 定义带有属性的接口和实现
        class Injectable:
            pass

        @dataclass
        class ServiceImplementation:
            interface: Type = Injectable
            priority: int = 1

        impl = ServiceImplementation()
        bindings = auto_binding.bind_by_attributes([impl])

        assert Injectable in bindings
        assert bindings[Injectable] == ServiceImplementation


@pytest.mark.skipif(not DI_AVAILABLE, reason=TEST_SKIP_REASON)
class TestServiceLifecycle:
    """服务生命周期测试"""

    def test_lifecycle_states(self):
        """测试生命周期状态"""
        lifecycle = ServiceLifecycle()

        service = Mock()

        # 测试状态转换
        assert service._state == ServiceState.UNINITIALIZED

        lifecycle.initialize(service)
        assert service._state == ServiceState.INITIALIZED

        lifecycle.start(service)
        assert service._state == ServiceState.STARTED

        lifecycle.stop(service)
        assert service._state == ServiceState.STOPPED

        lifecycle.dispose(service)
        assert service._state == ServiceState.DISPOSED

    def test_lifecycle_events(self):
        """测试生命周期事件"""
        lifecycle = ServiceLifecycle()

        events = []

        def on_initialized(service):
            events.append("initialized")

        def on_started(service):
            events.append("started")

        def on_stopped(service):
            events.append("stopped")

        lifecycle.add_event_handler("initialized", on_initialized)
        lifecycle.add_event_handler("started", on_started)
        lifecycle.add_event_handler("stopped", on_stopped)

        service = Mock()

        lifecycle.initialize(service)
        lifecycle.start(service)
        lifecycle.stop(service)

        assert events == ["initialized", "started", "stopped"]

    def test_async_lifecycle(self):
        """测试异步生命周期"""
        import asyncio

        lifecycle = ServiceLifecycle()

        class AsyncService:
            async def initialize(self):
                self.initialized = True

            async def start(self):
                self.started = True

            async def stop(self):
                self.started = False

        service = AsyncService()

        # 运行异步生命周期
        async def run_lifecycle():
            await lifecycle.initialize_async(service)
            await lifecycle.start_async(service)
            await lifecycle.stop_async(service)

        asyncio.run(run_lifecycle())

        assert service.initialized is True
        assert service.started is False

    def test_lifecycle_error_handling(self):
        """测试生命周期错误处理"""
        lifecycle = ServiceLifecycle()

        class FaultyService:
            def initialize(self):
                raise Exception("Initialization failed")

        service = FaultyService()

        with pytest.raises(Exception, match="Initialization failed"):
            lifecycle.initialize(service)

        # 验证状态保持一致
        assert service._state == ServiceState.FAILED

    def test_service_dependencies_lifecycle(self):
        """测试服务依赖生命周期"""
        lifecycle = ServiceLifecycle()

        class DatabaseService:
            def __init__(self):
                self.connected = False

            def initialize(self):
                self.connected = True

            def dispose(self):
                self.connected = False

        class UserService:
            def __init__(self, db: DatabaseService):
                self.db = db
                self.users = []

            def initialize(self):
                self.users = [{"id": 1, "name": "test"}]

        db = DatabaseService()
        user_service = UserService(db)

        # 按依赖顺序初始化
        lifecycle.initialize(db)
        lifecycle.initialize(user_service)

        assert db.connected is True
        assert len(user_service.users) == 1

        # 按相反顺序释放
        lifecycle.dispose(user_service)
        lifecycle.dispose(db)

        assert db.connected is False


@pytest.mark.skipif(not DI_AVAILABLE, reason=TEST_SKIP_REASON)
class TestDIIntegration:
    """DI集成测试"""

    def test_full_di_workflow(self):
        """测试完整的DI工作流"""
        # 创建容器
        container = DIContainer()

        # 定义服务
        class Logger:
            def log(self, message):
                print(f"LOG: {message}")

        class Database:
            def __init__(self, logger: Logger):
                self.logger = logger
                self.connected = False

            def connect(self):
                self.connected = True
                self.logger.log("Database connected")

        class UserRepository:
            def __init__(self, db: Database, logger: Logger):
                self.db = db
                self.logger = logger

            def save(self, user):
                if not self.db.connected:
                    raise Exception("Database not connected")
                self.logger.log(f"User saved: {user}")

        # 注册服务
        container.register_singleton(Logger)
        container.register_singleton(Database)
        container.register_transient(UserRepository)

        # 获取服务并使用
        logger = container.get(Logger)
        db = container.get(Database)
        repo = container.get(UserRepository)

        db.connect()
        repo.save({"name": "John"})

        # 验证单例
        logger2 = container.get(Logger)
        assert logger is logger2

    def test_di_with_configuration(self):
        """测试DI与配置集成"""
        config_di = ConfigDI()
        DIContainer()

        # 注册配置
        app_config = {
            "database": {"host": "localhost", "port": 5432, "pool_size": 10},
            "cache": {"type": "redis", "ttl": 3600},
        }

        config_di.register_config("app", app_config)

        # 创建配置驱动的服务
        class DatabaseService:
            def __init__(self, config: dict):
                self.host = _config["host"]
                self.port = _config["port"]
                self.pool_size = _config["pool_size"]

        # 获取配置并创建服务
        db_config = config_di.get_config("app")["database"]
        db_service = DatabaseService(db_config)

        assert db_service.host == "localhost"
        assert db_service.port == 5432
        assert db_service.pool_size == 10
