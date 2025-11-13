"""
依赖注入容器
Dependency Injection Container

提供轻量级的依赖注入实现.
Provides a lightweight dependency injection implementation.
"""

import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from .exceptions import DependencyInjectionError

T = TypeVar("T")
logger = logging.getLogger(__name__)


class ServiceLifetime(Enum):
    """服务生命周期枚举"""

    SINGLETON = "singleton"  # 单例:整个容器生命周期内只创建一次
    SCOPED = "scoped"  # 作用域:每个作用域内创建一次
    TRANSIENT = "transient"  # 瞬时:每次请求都创建新实例


@dataclass
class ServiceDescriptor:
    """类文档字符串"""

    pass  # 添加pass语句
    """服务描述符"""

    interface: type
    implementation: type
    lifetime: ServiceLifetime
    factory: Callable | None = None
    instance: Any | None = None
    dependencies: list[type] | None = None

    def __post_init__(self):
        """函数文档字符串"""
        # 添加pass语句
        if self.dependencies is None:
            self.dependencies = []


class DIContainer:
    """类文档字符串"""

    pass  # 添加pass语句
    """依赖注入容器"""

    def __init__(self, name: str = "default"):
        """函数文档字符串"""
        # 添加pass语句
        self.name = name
        self._services: dict[type, ServiceDescriptor] = {}
        self._singletons: dict[type, Any] = {}
        self._scoped_instances: dict[str, dict[type, Any]] = {}
        self._current_scope: str | None = None
        self._building: list[type] = []  # 用于检测循环依赖

    def register_singleton(
        self,
        interface: type[T],
        implementation: type[T] | None = None,
        instance: T | None = None,
        factory: Callable[[], T] | None = None,
    ) -> "DIContainer":
        """注册单例服务"""
        return self._register(
            interface=interface,
            implementation=implementation,
            lifetime=ServiceLifetime.SINGLETON,
            instance=instance,
            factory=factory,
        )

    def register_scoped(
        self,
        interface: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
    ) -> "DIContainer":
        """注册作用域服务"""
        return self._register(
            interface=interface,
            implementation=implementation,
            lifetime=ServiceLifetime.SCOPED,
            factory=factory,
        )

    def register_transient(
        self,
        interface: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
    ) -> "DIContainer":
        """注册瞬时服务"""
        return self._register(
            interface=interface,
            implementation=implementation,
            lifetime=ServiceLifetime.TRANSIENT,
            factory=factory,
        )

    def _register(
        self,
        interface: type,
        implementation: type | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        instance: Any | None = None,
        factory: Callable | None = None,
    ) -> "DIContainer":
        """内部注册方法"""
        if implementation is None and interface is not None:
            # 如果没有指定实现,使用接口自身作为实现
            implementation = interface

        if implementation is None and factory is None:
            raise DependencyInjectionError(
                f"必须提供 implementation 或 factory for {interface}"
            )

        # 分析依赖
        dependencies = []
        if implementation:
            dependencies = self._analyze_dependencies(implementation)

        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=implementation,
            lifetime=lifetime,
            factory=factory,
            instance=instance,
            dependencies=dependencies,
        )

        self._services[interface] = descriptor
        impl_name = (
            implementation.__name__
            if hasattr(implementation, "__name__")
            else str(implementation)
        )
        logger.debug(
            f"注册服务: {self._get_type_name(interface)} -> {impl_name if implementation else 'Factory'}"
        )

        return self

    def resolve(self, interface: type[T]) -> T:
        """解析服务"""
        if interface not in self._services:
            raise DependencyInjectionError(f"服务未注册: {self._get_type_name(interface)}")

        descriptor = self._services[interface]

        # 检测循环依赖
        if interface in self._building:
            raise DependencyInjectionError(
                f"检测到循环依赖: {' -> '.join(self._get_type_name(t) for t in self._building)} -> {self._get_type_name(interface)}"
            )

        # 根据生命周期返回实例
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self._get_singleton(descriptor)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            return self._get_scoped(descriptor)
        else:  # TRANSIENT
            return self._create_instance(descriptor)

    def _get_singleton(self, descriptor: ServiceDescriptor) -> Any:
        """获取单例实例"""
        if descriptor.interface in self._singletons:
            return self._singletons[descriptor.interface]

        instance = self._create_instance(descriptor)
        self._singletons[descriptor.interface] = instance
        return instance

    def _get_scoped(self, descriptor: ServiceDescriptor) -> Any:
        """获取作用域实例"""
        if self._current_scope is None:
            # 如果没有作用域, 当作单例处理
            logger.warning("没有活动的作用域, 将作用域服务当作单例处理")
            return self._get_singleton(descriptor)

        if self._current_scope not in self._scoped_instances:
            self._scoped_instances[self._current_scope] = {}

        scope_instances = self._scoped_instances[self._current_scope]

        if descriptor.interface in scope_instances:
            return scope_instances[descriptor.interface]

        instance = self._create_instance(descriptor)
        scope_instances[descriptor.interface] = instance
        return instance

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建新实例"""
        # 如果有预注册的实例
        if descriptor.instance is not None:
            return descriptor.instance

        # 如果有工厂方法
        if descriptor.factory:
            return descriptor.factory()

        # 如果有实现类
        if descriptor.implementation:
            self._building.append(descriptor.interface)
            try:
                # 解析构造函数参数
                constructor_params = self._get_constructor_params(
                    descriptor.implementation
                )
                instance = descriptor.implementation(**constructor_params)
                return instance
            finally:
                self._building.pop()

        raise DependencyInjectionError(f"无法创建实例: {self._get_type_name(descriptor.interface)}")

    def _analyze_dependencies(self, cls: type) -> list[type]:
        """分析类的依赖"""
        dependencies = []

        # 获取构造函数签名
        sig = inspect.signature(cls.__init__)

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # 获取参数的类型注解
            if param.annotation != inspect.Parameter.empty:
                dependencies.append(param.annotation)

        return dependencies

    def _get_constructor_params(self, cls: type) -> dict[str, Any]:
        """获取构造函数参数"""
        params = {}
        sig = inspect.signature(cls.__init__)

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # 获取参数的类型
            param_type = param.annotation

            if param_type == inspect.Parameter.empty:
                if param.default == inspect.Parameter.empty:
                    raise DependencyInjectionError(
                        f"参数 {param_name} 没有类型注解且没有默认值"
                    )
                continue

            # 解析依赖
            if param_type in self._services:
                params[param_name] = self.resolve(param_type)
            else:
                # 尝试自动注册
                type_name = self._get_type_name(param_type)
                logger.warning(f"自动注册类型: {type_name}")
                self.register_transient(param_type)
                params[param_name] = self.resolve(param_type)

        return params

    def _get_type_name(self, param_type) -> str:
        """安全地获取类型名称"""
        if hasattr(param_type, '__name__'):
            return param_type.__name__
        elif hasattr(param_type, '_name'):  # typing.Generic
            return param_type._name
        elif isinstance(param_type, str):
            return param_type
        else:
            return str(param_type)

    def create_scope(self, scope_name: str | None = None) -> "DIScope":
        """创建新的作用域"""
        if scope_name is None:
            scope_name = f"scope_{datetime.now().timestamp()}"

        return DIScope(self, scope_name)

    def clear_scope(self, scope_name: str) -> None:
        """清除作用域"""
        if scope_name in self._scoped_instances:
            # 清理作用域内的资源
            scope_instances = self._scoped_instances[scope_name]
            for instance in scope_instances.values():
                # 如果实例有 cleanup 方法
                if hasattr(instance, "cleanup") and callable(instance.cleanup):
                    try:
                        instance.cleanup()
                    except (ValueError, TypeError, AttributeError, KeyError) as e:
                        logger.error(f"清理资源失败: {e}")

            del self._scoped_instances[scope_name]
            logger.debug(f"清除作用域: {scope_name}")

    def is_registered(self, interface: type) -> bool:
        """检查服务是否已注册"""
        return interface in self._services

    def get_registered_services(self) -> list[type]:
        """获取所有已注册的服务"""
        return list(self._services.keys())

    def clear(self) -> None:
        """清除所有注册的服务"""
        self._services.clear()
        self._singletons.clear()
        self._scoped_instances.clear()
        logger.info("清除所有服务注册")


class DIScope:
    """类文档字符串"""

    pass  # 添加pass语句
    """依赖注入作用域"""

    def __init__(self, container: DIContainer, scope_name: str):
        """函数文档字符串"""
        # 添加pass语句
        self.container = container
        self.scope_name = scope_name
        self._old_scope = None

    def __enter__(self):
        """函数文档字符串"""
        # 添加pass语句
        self._old_scope = self.container._current_scope
        self.container._current_scope = self.scope_name
        logger.debug(f"进入作用域: {self.scope_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """函数文档字符串"""
        # 添加pass语句
        self.container._current_scope = self._old_scope
        self.container.clear_scope(self.scope_name)
        logger.debug(f"退出作用域: {self.scope_name}")


class ServiceCollection:
    """类文档字符串"""

    pass  # 添加pass语句
    """服务集合,用于批量注册服务"""

    def __init__(self):
        """函数文档字符串"""
        # 添加pass语句
        self._registrations: list[Callable[[DIContainer], None]] = []

    def add_singleton(
        self,
        interface: type[T],
        implementation: type[T] | None = None,
        instance: T | None = None,
        factory: Callable[[], T] | None = None,
    ) -> "ServiceCollection":
        """添加单例服务"""
        self._registrations.append(
            lambda container: container.register_singleton(
                interface, implementation, instance, factory
            )
        )
        return self

    def add_scoped(
        self,
        interface: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
    ) -> "ServiceCollection":
        """添加作用域服务"""
        self._registrations.append(
            lambda container: container.register_scoped(
                interface, implementation, factory
            )
        )
        return self

    def add_transient(
        self,
        interface: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
    ) -> "ServiceCollection":
        """添加瞬时服务"""
        self._registrations.append(
            lambda container: container.register_transient(
                interface, implementation, factory
            )
        )
        return self

    def build_container(self, name: str = "default") -> DIContainer:
        """构建容器"""
        container = DIContainer(name)

        for registration in self._registrations:
            registration(container)

        return container


# 全局容器实例
_default_container: DIContainer | None = None


def get_default_container() -> DIContainer:
    """获取默认容器"""
    global _default_container
    if _default_container is None:
        _default_container = DIContainer("default")
    return _default_container


def configure_services(
    configurator: Callable[[ServiceCollection], None],
) -> DIContainer:
    """配置服务"""
    collection = ServiceCollection()
    configurator(collection)
    container = collection.build_container()

    # 设置为默认容器
    global _default_container
    _default_container = container

    return container


def resolve(service_type: type[T]) -> T:
    """从默认容器解析服务"""
    return get_default_container().resolve(service_type)


def inject(
    service_type: type[T], container: DIContainer | None = None
) -> Callable[[Callable], Callable]:
    """依赖注入装饰器"""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            """函数文档字符串"""
            # 添加pass语句
            if container is None:
                instance = resolve(service_type)
            else:
                instance = container.resolve(service_type)

            # 将服务实例添加到参数中
            sig = inspect.signature(func)
            if "service" in sig.parameters:
                kwargs["service"] = instance

            return func(*args, **kwargs)

        return wrapper

    return decorator
