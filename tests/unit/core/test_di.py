"""
依赖注入系统测试
Dependency Injection System Tests

测试核心依赖注入功能的完整性和正确性.
Tests the integrity and correctness of core dependency injection functionality.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from unittest.mock import Mock, patch

import pytest

from src.core.di import (
    DependencyInjectionError,
    DIContainer,
    DIScope,
    ServiceCollection,
    ServiceDescriptor,
    ServiceLifetime,
    configure_services,
    get_default_container,
    inject,
    resolve,
)


# 测试接口和实现类
class TestService:
    """基础测试服务"""

    __test__ = False  # 告诉pytest这不是测试类

    def __init__(self):
        self.name = "test"

    def get_name(self) -> str:
        return self.name


class AnotherTestService:
    """另一个测试服务"""

    def __init__(self, test_service: TestService):
        self.test_service = test_service

    def get_combined_name(self) -> str:
        return f"{self.test_service.get_name()}_combined"


@runtime_checkable
class ITestService(Protocol):
    """测试服务接口"""

    def get_name(self) -> str: ...


class TestServiceImpl(ITestService):
    """测试服务实现"""

    __test__ = False  # 告诉pytest这不是测试类

    def __init__(self):
        self.prefix = "impl"

    def get_name(self) -> str:
        return f"{self.prefix}_name"


class ServiceWithCleanup:
    """带清理方法的服务"""

    def __init__(self, value: int = 0):
        self.value = value
        self.cleaned_up = False

    def cleanup(self):
        """清理资源"""
        self.cleaned_up = True

    def is_cleaned_up(self) -> bool:
        return self.cleaned_up


class TestServiceLifetime:
    """测试服务生命周期枚举"""

    def test_service_lifetime_values(self):
        """测试服务生命周期枚举值"""
        assert ServiceLifetime.SINGLETON.value == "singleton"
        assert ServiceLifetime.SCOPED.value == "scoped"
        assert ServiceLifetime.TRANSIENT.value == "transient"

    def test_service_lifetime_equality(self):
        """测试服务生命周期比较"""
        lifetime1 = ServiceLifetime.SINGLETON
        lifetime2 = ServiceLifetime.SINGLETON
        lifetime3 = ServiceLifetime.TRANSIENT

        assert lifetime1 == lifetime2
        assert lifetime1 != lifetime3
        assert hash(lifetime1) == hash(lifetime2)
        assert hash(lifetime1) != hash(lifetime3)


class TestServiceDescriptor:
    """测试服务描述符"""

    def test_service_descriptor_creation_minimal(self):
        """测试最小参数创建服务描述符"""
        descriptor = ServiceDescriptor(
            interface=TestService,
            implementation=TestService,
            lifetime=ServiceLifetime.TRANSIENT,
        )

        assert descriptor.interface == TestService
        assert descriptor.implementation == TestService
        assert descriptor.lifetime == ServiceLifetime.TRANSIENT
        assert descriptor.factory is None
        assert descriptor.instance is None
        assert descriptor.dependencies == []

    def test_service_descriptor_creation_full(self):
        """测试完整参数创建服务描述符"""
        factory = Mock(return_value=TestService())
        factory.return_value.name = "factory"
        instance = TestService()
        instance.name = "instance"

        descriptor = ServiceDescriptor(
            interface=TestService,
            implementation=None,
            lifetime=ServiceLifetime.SINGLETON,
            factory=factory,
            instance=instance,
            dependencies=[AnotherTestService],
        )

        assert descriptor.interface == TestService
        assert descriptor.implementation is None
        assert descriptor.lifetime == ServiceLifetime.SINGLETON
        assert descriptor.factory == factory
        assert descriptor.instance == instance
        assert descriptor.dependencies == [AnotherTestService]

    def test_service_descriptor_post_init(self):
        """测试服务描述符后初始化"""
        descriptor = ServiceDescriptor(
            interface=TestService,
            implementation=TestService,
            lifetime=ServiceLifetime.TRANSIENT,
        )

        assert descriptor.dependencies == []


class TestDIContainer:
    """测试依赖注入容器"""

    def test_container_initialization(self):
        """测试容器初始化"""
        container = DIContainer("test_container")

        assert container.name == "test_container"
        assert len(container._services) == 0
        assert len(container._singletons) == 0
        assert len(container._scoped_instances) == 0
        assert container._current_scope is None
        assert len(container._building) == 0

    def test_register_singleton_with_implementation(self):
        """测试注册单例服务（使用实现类）"""
        container = DIContainer()

        result = container.register_singleton(TestService, TestServiceImpl)

        assert isinstance(result, DIContainer)
        assert TestService in container._services
        descriptor = container._services[TestService]
        assert descriptor.interface == TestService
        assert descriptor.implementation == TestServiceImpl
        assert descriptor.lifetime == ServiceLifetime.SINGLETON

    def test_register_singleton_with_instance(self):
        """测试注册单例服务（使用实例）"""
        container = DIContainer()
        instance = TestService()
        instance.name = "instance"  # 手动设置属性

        container.register_singleton(TestService, instance=instance)

        descriptor = container._services[TestService]
        assert descriptor.instance == instance

    def test_register_singleton_with_factory(self):
        """测试注册单例服务（使用工厂方法）"""
        container = DIContainer()
        factory = Mock(return_value=TestService())
        factory.return_value.name = "factory"  # 手动设置属性

        container.register_singleton(TestService, factory=factory)

        descriptor = container._services[TestService]
        assert descriptor.factory == factory

    def test_register_scoped(self):
        """测试注册作用域服务"""
        container = DIContainer()

        container.register_scoped(TestService, TestServiceImpl)

        descriptor = container._services[TestService]
        assert descriptor.lifetime == ServiceLifetime.SCOPED

    def test_register_transient(self):
        """测试注册瞬时服务"""
        container = DIContainer()

        container.register_transient(TestService, TestServiceImpl)

        descriptor = container._services[TestService]
        assert descriptor.lifetime == ServiceLifetime.TRANSIENT

    def test_register_auto_implementation(self):
        """测试自动使用接口作为实现"""
        container = DIContainer()

        container.register_singleton(TestService)

        descriptor = container._services[TestService]
        assert descriptor.interface == TestService
        assert descriptor.implementation == TestService

    def test_register_error_no_implementation_or_factory(self):
        """测试注册错误：Protocol类型解析时失败"""
        container = DIContainer()

        # 注册Protocol类型（这会成功，因为会自动使用Protocol作为实现）
        container.register_transient(ITestService)

        # 但解析时会失败，因为Protocol无法实例化且构造函数参数有问题
        with pytest.raises(DependencyInjectionError) as exc_info:
            container.resolve(ITestService)

        assert "参数 args 没有类型注解且没有默认值" in str(exc_info.value)

    def test_resolve_unregistered_service(self):
        """测试解析未注册的服务"""
        container = DIContainer()

        with pytest.raises(DependencyInjectionError) as exc_info:
            container.resolve(TestService)

        assert "服务未注册" in str(exc_info.value)

    def test_resolve_singleton(self):
        """测试解析单例服务"""
        container = DIContainer()
        container.register_singleton(TestService, TestServiceImpl)

        instance1 = container.resolve(TestService)
        instance2 = container.resolve(TestService)

        assert isinstance(instance1, TestServiceImpl)
        assert instance1 is instance2  # 同一个实例

    def test_resolve_transient(self):
        """测试解析瞬时服务"""
        container = DIContainer()
        container.register_transient(TestService, TestServiceImpl)

        instance1 = container.resolve(TestService)
        instance2 = container.resolve(TestService)

        assert isinstance(instance1, TestServiceImpl)
        assert isinstance(instance2, TestServiceImpl)
        assert instance1 is not instance2  # 不同实例

    def test_resolve_with_factory(self):
        """测试使用工厂方法解析服务"""
        container = DIContainer()
        factory = Mock(return_value=TestService())
        factory.return_value.name = "factory"

        container.register_singleton(TestService, factory=factory)

        instance = container.resolve(TestService)

        assert isinstance(instance, TestService)
        assert instance.name == "factory"
        factory.assert_called_once()

    def test_resolve_with_instance(self):
        """测试解析预注册实例"""
        container = DIContainer()
        instance = TestService()
        instance.name = "pre_registered"

        container.register_singleton(TestService, instance=instance)

        resolved_instance = container.resolve(TestService)

        assert resolved_instance is instance

    def test_resolve_with_dependencies(self):
        """测试解析带依赖的服务"""
        container = DIContainer()
        container.register_transient(TestService, TestServiceImpl)
        container.register_transient(AnotherTestService)

        instance = container.resolve(AnotherTestService)

        assert isinstance(instance, AnotherTestService)
        assert isinstance(instance.test_service, TestServiceImpl)

    def test_circular_dependency_detection(self):
        """测试循环依赖检测"""

        @dataclass
        class ServiceA:
            b: "ServiceB"

        @dataclass
        class ServiceB:
            a: ServiceA

        container = DIContainer()
        container.register_transient(ServiceA)
        container.register_transient(ServiceB)

        with pytest.raises(DependencyInjectionError) as exc_info:
            container.resolve(ServiceA)

        assert "检测到循环依赖" in str(exc_info.value)

    def test_resolve_scoped_without_scope(self):
        """测试在没有作用域时解析作用域服务"""
        container = DIContainer()
        container.register_scoped(TestService, TestServiceImpl)

        with patch("src.core.di.logger") as mock_logger:
            instance1 = container.resolve(TestService)
            instance2 = container.resolve(TestService)

            # 应该当作单例处理
            assert instance1 is instance2
            mock_logger.warning.assert_called_with(
                "没有活动的作用域, 将作用域服务当作单例处理"
            )

    def test_is_registered(self):
        """测试检查服务是否已注册"""
        container = DIContainer()

        assert not container.is_registered(TestService)

        container.register_singleton(TestService)
        assert container.is_registered(TestService)

    def test_get_registered_services(self):
        """测试获取所有已注册的服务"""
        container = DIContainer()
        container.register_singleton(TestService)
        container.register_transient(AnotherTestService)

        services = container.get_registered_services()

        assert TestService in services
        assert AnotherTestService in services
        assert len(services) == 2

    def test_clear(self):
        """测试清除所有服务"""
        container = DIContainer()
        container.register_singleton(TestService)
        container.register_transient(AnotherTestService)

        container.clear()

        assert len(container._services) == 0
        assert len(container._singletons) == 0
        assert len(container._scoped_instances) == 0

    def test_create_scope(self):
        """测试创建作用域"""
        container = DIContainer()

        scope = container.create_scope("test_scope")

        assert isinstance(scope, DIScope)
        assert scope.scope_name == "test_scope"
        assert scope.container == container

    def test_create_scope_auto_name(self):
        """测试创建自动命名的作用域"""
        container = DIContainer()

        scope = container.create_scope()

        assert isinstance(scope, DIScope)
        assert scope.scope_name.startswith("scope_")

    def test_clear_scope(self):
        """测试清除作用域"""
        container = DIContainer()
        container.register_scoped(ServiceWithCleanup)

        # 创建并进入作用域
        with container.create_scope("test_scope"):
            # 解析服务创建实例
            instance = container.resolve(ServiceWithCleanup)
            assert not instance.is_cleaned_up()

        # 退出作用域后应该自动清理
        assert instance.is_cleaned_up()

    def test_clear_scope_with_cleanup_error(self):
        """测试清除作用域时清理方法出错"""
        container = DIContainer()
        container.register_scoped(ServiceWithCleanup)

        class BadCleanupService:
            def cleanup(self):
                raise ValueError("Cleanup failed")

        container.register_scoped(BadCleanupService)

        with patch("src.core.di.logger") as mock_logger:
            with container.create_scope("test_scope"):
                container.resolve(ServiceWithCleanup)
                container.resolve(BadCleanupService)

            # 应该记录错误但不抛出异常
            mock_logger.error.assert_called()


class TestDIScope:
    """测试依赖注入作用域"""

    def test_scope_context_manager(self):
        """测试作用域上下文管理器"""
        container = DIContainer()
        container.register_scoped(TestService, TestServiceImpl)

        with container.create_scope("test_scope"):
            assert container._current_scope == "test_scope"

            instance1 = container.resolve(TestService)
            instance2 = container.resolve(TestService)

            # 作用域内应该是同一个实例
            assert instance1 is instance2

        # 退出作用域后应该清理
        assert container._current_scope is None
        assert "test_scope" not in container._scoped_instances

    def test_scope_with_different_services(self):
        """测试不同服务的作用域行为"""
        container = DIContainer()
        container.register_scoped(TestService, TestServiceImpl)
        container.register_singleton(AnotherTestService)

        with container.create_scope("test_scope"):
            scoped_instance = container.resolve(TestService)
            singleton_instance = container.resolve(AnotherTestService)

            # 作用域服务在作用域内是同一个实例
            with container.create_scope("another_scope"):
                another_scoped = container.resolve(TestService)
                another_singleton = container.resolve(AnotherTestService)

                # 单例服务始终是同一个实例
                assert singleton_instance is another_singleton
                # 作用域服务在不同作用域中是不同实例
                assert scoped_instance is not another_scoped


class TestServiceCollection:
    """测试服务集合"""

    def test_service_collection_initialization(self):
        """测试服务集合初始化"""
        collection = ServiceCollection()

        assert len(collection._registrations) == 0

    def test_add_singleton(self):
        """测试添加单例服务"""
        collection = ServiceCollection()

        result = collection.add_singleton(TestService, TestServiceImpl)

        assert isinstance(result, ServiceCollection)
        assert len(collection._registrations) == 1

    def test_add_scoped(self):
        """测试添加作用域服务"""
        collection = ServiceCollection()

        result = collection.add_scoped(TestService, TestServiceImpl)

        assert isinstance(result, ServiceCollection)
        assert len(collection._registrations) == 1

    def test_add_transient(self):
        """测试添加瞬时服务"""
        collection = ServiceCollection()

        result = collection.add_transient(TestService, TestServiceImpl)

        assert isinstance(result, ServiceCollection)
        assert len(collection._registrations) == 1

    def test_build_container(self):
        """测试构建容器"""
        collection = ServiceCollection()
        collection.add_singleton(TestService, TestServiceImpl)
        collection.add_transient(AnotherTestService)

        container = collection.build_container("test_container")

        assert isinstance(container, DIContainer)
        assert container.name == "test_container"
        assert container.is_registered(TestService)
        assert container.is_registered(AnotherTestService)

    def test_chaining_registrations(self):
        """测试链式注册"""
        collection = ServiceCollection()

        result = (
            collection.add_singleton(TestService, TestServiceImpl)
            .add_transient(AnotherTestService)
            .add_scoped(ServiceWithCleanup)
        )

        assert isinstance(result, ServiceCollection)
        assert len(collection._registrations) == 3


class TestGlobalFunctions:
    """测试全局函数"""

    def test_get_default_container(self):
        """测试获取默认容器"""
        # 清除全局容器
        import src.core.di

        src.core.di._default_container = None

        container1 = get_default_container()
        container2 = get_default_container()

        assert isinstance(container1, DIContainer)
        assert container1 is container2
        assert container1.name == "default"

    def test_configure_services(self):
        """测试配置服务"""

        def configurator(collection):
            collection.add_singleton(TestService, TestServiceImpl)

        container = configure_services(configurator)

        assert isinstance(container, DIContainer)
        assert container.is_registered(TestService)

        # 验证设置为默认容器
        default_container = get_default_container()
        assert default_container is container

    def test_resolve_from_default_container(self):
        """测试从默认容器解析服务"""
        # 清除并重新配置默认容器
        import src.core.di

        src.core.di._default_container = None

        def configurator(collection):
            collection.add_singleton(TestService, TestServiceImpl)

        configure_services(configurator)

        instance = resolve(TestService)

        assert isinstance(instance, TestServiceImpl)

    def test_resolve_without_default_container(self):
        """测试没有默认容器时解析服务"""
        # 清除全局容器
        import src.core.di

        src.core.di._default_container = None

        instance = resolve(TestService)

        assert isinstance(instance, TestService)


class TestInjectDecorator:
    """测试依赖注入装饰器"""

    def test_inject_decorator(self):
        """测试依赖注入装饰器"""
        # 清除并重新配置默认容器
        import src.core.di

        src.core.di._default_container = None

        def configurator(collection):
            collection.add_singleton(TestService, TestServiceImpl("injected"))

        configure_services(configurator)

        @inject(TestService)
        def test_function(service=None):
            return service.get_name() if service else "no service"

        result = test_function()

        assert result == "injected_name"

    def test_inject_decorator_with_custom_container(self):
        """测试使用自定义容器的依赖注入装饰器"""
        container = DIContainer()
        container.register_singleton(TestService, TestServiceImpl("custom"))

        @inject(TestService, container)
        def test_function(service=None):
            return service.get_name() if service else "no service"

        result = test_function()

        assert result == "custom_name"

    def test_inject_decorator_without_service_param(self):
        """测试装饰器函数没有service参数"""
        # 清除并重新配置默认容器
        import src.core.di

        src.core.di._default_container = None

        def configurator(collection):
            collection.add_singleton(TestService, TestServiceImpl)

        configure_services(configurator)

        @inject(TestService)
        def test_function():
            return "no service param"

        result = test_function()

        assert result == "no service param"


class TestEdgeCases:
    """测试边界情况"""

    def test_service_with_no_constructor_params(self):
        """测试没有构造函数参数的服务"""

        class NoParamsService:
            pass

        container = DIContainer()
        container.register_singleton(NoParamsService)

        instance = container.resolve(NoParamsService)

        assert isinstance(instance, NoParamsService)

    def test_service_with_default_params(self):
        """测试有默认参数的服务"""

        class DefaultParamsService:
            def __init__(self, name: str = "default", value: int = 42):
                self.name = name
                self.value = value

        container = DIContainer()
        container.register_singleton(DefaultParamsService)

        instance = container.resolve(DefaultParamsService)

        assert instance.name == "default"
        assert instance.value == 42

    def test_auto_registration_of_dependencies(self):
        """测试自动注册依赖"""

        class AutoService:
            def __init__(self, test_service: TestService):
                self.test_service = test_service

        container = DIContainer()
        container.register_singleton(AutoService)

        with patch("src.core.di.logger") as mock_logger:
            instance = container.resolve(AutoService)

            assert isinstance(instance, AutoService)
            assert isinstance(instance.test_service, TestService)
            mock_logger.warning.assert_called_with("自动注册类型: TestService")

    def test_dependency_injection_error_messages(self):
        """测试依赖注入错误消息"""
        container = DIContainer()

        # 测试未注册服务的错误消息
        with pytest.raises(DependencyInjectionError) as exc_info:
            container.resolve(TestService)

        assert "服务未注册: TestService" in str(exc_info.value)

        # 测试循环依赖的错误消息
        @dataclass
        class CircularA:
            b: "CircularB"

        @dataclass
        class CircularB:
            a: CircularA

        container.register_transient(CircularA)
        container.register_transient(CircularB)

        with pytest.raises(DependencyInjectionError) as exc_info:
            container.resolve(CircularA)

        assert "检测到循环依赖" in str(exc_info.value)
        assert "CircularA" in str(exc_info.value)
        assert "CircularB" in str(exc_info.value)


class TestIntegrationScenarios:
    """测试集成场景"""

    def test_complex_dependency_graph(self):
        """测试复杂依赖图"""

        class DatabaseService:
            def __init__(self):
                self.connected = True

        class CacheService:
            def __init__(self):
                self.cache = {}

        class LoggingService:
            def __init__(self):
                self.logs = []

        class UserService:
            def __init__(self, db: DatabaseService, cache: CacheService):
                self.db = db
                self.cache = cache

        class OrderService:
            def __init__(self, db: DatabaseService, user_service: UserService):
                self.db = db
                self.user_service = user_service

        class ApplicationService:
            def __init__(
                self, orders: OrderService, users: UserService, logging: LoggingService
            ):
                self.orders = orders
                self.users = users
                self.logging = logging

        # 构建容器
        collection = ServiceCollection()
        collection.add_singleton(DatabaseService)
        collection.add_scoped(CacheService)
        collection.add_transient(LoggingService)
        collection.add_scoped(UserService)
        collection.add_scoped(OrderService)
        collection.add_transient(ApplicationService)

        container = collection.build_container()

        with container.create_scope():
            app_service = container.resolve(ApplicationService)

            # 验证依赖图正确构建
            assert isinstance(app_service, ApplicationService)
            assert isinstance(app_service.orders, OrderService)
            assert isinstance(app_service.users, UserService)
            assert isinstance(app_service.logging, LoggingService)

            # 验证单例行为
            assert app_service.orders.db is app_service.users.db

    def test_service_lifecycle_behaviors(self):
        """测试服务生命周期行为"""
        collection = ServiceCollection()
        collection.add_singleton(TestService, TestServiceImpl("singleton"))
        collection.add_scoped(AnotherTestService)
        collection.add_transient(ServiceWithCleanup)

        container = collection.build_container()

        # 测试单例行为
        singleton1 = container.resolve(TestService)
        singleton2 = container.resolve(TestService)
        assert singleton1 is singleton2

        # 测试作用域行为
        with container.create_scope("scope1"):
            scoped1a = container.resolve(AnotherTestService)
            scoped1b = container.resolve(AnotherTestService)
            assert scoped1a is scoped1b

            with container.create_scope("scope2"):
                scoped2a = container.resolve(AnotherTestService)
                assert scoped2a is not scoped1a

        # 测试瞬时行为
        transient1 = container.resolve(ServiceWithCleanup)
        transient2 = container.resolve(ServiceWithCleanup)
        assert transient1 is not transient2

    def test_factory_with_dependencies(self):
        """测试带依赖的工厂方法"""
        container = DIContainer()
        container.register_singleton(TestService, TestServiceImpl("factory_dep"))

        def create_another_service(test_service: TestService):
            return AnotherTestService(test_service)

        container.register_singleton(AnotherTestService, factory=create_another_service)

        instance = container.resolve(AnotherTestService)

        assert isinstance(instance, AnotherTestService)
        assert isinstance(instance.test_service, TestServiceImpl)
        assert instance.test_service.name == "factory_dep_name"
