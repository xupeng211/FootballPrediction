#!/usr/bin/env python3
"""
依赖注入容器 - Sprint 3 核心组件

实现企业级依赖注入模式，解决硬编码依赖问题。
支持生命周期管理、配置注入和依赖解析。

设计原则:
- Constructor Injection (构造函数注入)
- Single Responsibility (单一职责)
- Loose Coupling (松耦合)
- Configuration Externalization (配置外部化)
"""

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import logging
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceLifecycle(ABC):
    """服务生命周期基类"""

    @abstractmethod
    async def initialize(self) -> None:
        """初始化服务"""

    @abstractmethod
    async def shutdown(self) -> None:
        """关闭服务"""

    @property
    @abstractmethod
    def is_initialized(self) -> bool:
        """检查是否已初始化"""


@dataclass
class ServiceDescriptor:
    """服务描述符"""

    service_type: type[T]
    factory: Callable[[], T] | None = None
    singleton: bool = True
    lazy: bool = True
    dependencies: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


class DIContainer:
    """
    依赖注入容器

    支持服务注册、依赖解析和生命周期管理。
    """

    def __init__(self):
        self._services: dict[str, ServiceDescriptor] = {}
        self._instances: dict[str, Any] = {}
        self._initializing: set[str] = set()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def register(
        self,
        service_name: str,
        service_type: type[T],
        factory: Callable[[], T] | None = None,
        singleton: bool = True,
        lazy: bool = True,
        dependencies: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        注册服务

        Args:
            service_name: 服务名称
            service_type: 服务类型
            factory: 工厂函数（可选）
            singleton: 是否单例
            lazy: 是否懒加载
            dependencies: 依赖服务列表
            config: 配置参数
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            singleton=singleton,
            lazy=lazy,
            dependencies=dependencies or [],
            config=config or {},
        )

        self._services[service_name] = descriptor
        self.logger.info(f"注册服务: {service_name} -> {service_type.__name__}")

    def register_instance(self, service_name: str, instance: T) -> None:
        """注册服务实例"""
        self._instances[service_name] = instance
        self.logger.info(f"注册实例: {service_name} -> {type(instance).__name__}")

    async def resolve(self, service_name: str) -> Any:  # type: ignore
        """
        解析服务

        Args:
            service_name: 服务名称

        Returns:
            服务实例

        Raises:
            ValueError: 服务未注册
            RuntimeError: 循环依赖
        """
        if service_name in self._initializing:
            raise RuntimeError(f"检测到循环依赖: {service_name}")

        if service_name in self._instances:
            return self._instances[service_name]

        if service_name not in self._services:
            raise ValueError(f"服务未注册: {service_name}")

        descriptor = self._services[service_name]

        # 单例且已创建
        if descriptor.singleton and service_name in self._instances:
            return self._instances[service_name]

        # 懒加载检查
        if descriptor.lazy:
            return await self._create_instance(service_name, descriptor)

        # 非懒加载，应该已经创建
        raise ValueError(f"服务 {service_name} 未创建但标记为非懒加载")

    async def _create_instance(self, service_name: str, descriptor: ServiceDescriptor) -> T:
        """创建服务实例"""
        self._initializing.add(service_name)

        try:
            # 解析依赖
            dependencies = {}
            for dep_name in descriptor.dependencies:
                dependencies[dep_name] = await self.resolve(dep_name)

            # 创建实例
            if descriptor.factory:
                if asyncio.iscoroutinefunction(descriptor.factory):
                    instance = await descriptor.factory(**dependencies)
                else:
                    instance = descriptor.factory(**dependencies)
            else:
                # 使用构造函数注入
                instance = descriptor.service_type(**dependencies)

            # 注入配置
            if descriptor.config:
                if hasattr(instance, "update_config"):
                    instance.update_config(descriptor.config)
                elif hasattr(instance, "__dict__"):
                    for key, value in descriptor.config.items():
                        setattr(instance, key, value)

            # 初始化服务
            if isinstance(instance, ServiceLifecycle):
                if not instance.is_initialized:
                    await instance.initialize()
                self.logger.info(f"服务初始化完成: {service_name}")

            # 单例模式缓存
            if descriptor.singleton:
                self._instances[service_name] = instance

            return instance

        except Exception as e:
            self.logger.error(f"创建服务失败 {service_name}: {e}")
            raise
        finally:
            self._initializing.discard(service_name)

    async def shutdown_all(self) -> None:
        """关闭所有服务"""
        self.logger.info("开始关闭所有服务...")

        shutdown_tasks = []
        for service_name, instance in self._instances.items():
            if isinstance(instance, ServiceLifecycle) and instance.is_initialized:
                shutdown_tasks.append(self._shutdown_service(service_name, instance))

        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

        self._instances.clear()
        self.logger.info("所有服务已关闭")

    async def _shutdown_service(self, service_name: str, instance: ServiceLifecycle) -> None:
        """关闭单个服务"""
        try:
            await instance.shutdown()
        except Exception as e:
            self.logger.error(f"关闭服务失败 {service_name}: {e}")

    def get_service_info(self) -> dict[str, Any]:
        """获取服务信息"""
        return {
            "registered_services": list(self._services.keys()),
            "active_instances": list(self._instances.keys()),
            "service_count": len(self._services),
            "instance_count": len(self._instances),
        }


# 全局依赖注入容器
_container: DIContainer | None = None


def get_container() -> DIContainer:
    """获取全局依赖注入容器"""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


@asynccontextmanager
async def container_context():
    """依赖注入容器上下文管理器"""
    container = get_container()
    try:
        yield container
    finally:
        await container.shutdown_all()


# 依赖注入装饰器
def injectable(service_name: str, dependencies: list[str] | None = None):
    """
    可注入服务装饰器

    Args:
        service_name: 服务名称
        dependencies: 依赖服务列表
    """

    def decorator(cls: type[T]) -> type[T]:
        original_init = cls.__init__

        def __init__(self, *args, **kwargs):
            # 保存原始参数
            self._injected_args = args
            self._injected_kwargs = kwargs

            # 如果没有传入依赖，则注入
            if not dependencies:
                original_init(self, *args, **kwargs)
            else:
                # 异步注入依赖
                async def inject_dependencies():
                    container = get_container()
                    injected_kwargs = kwargs.copy()

                    for dep_name in dependencies:
                        injected_kwargs[dep_name] = await container.resolve(dep_name)

                    original_init(self, *args, **injected_kwargs)

                # 在异步环境中调用
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 已在事件循环中，创建任务
                        asyncio.create_task(inject_dependencies())
                    else:
                        # 不在事件循环中，运行任务
                        loop.run_until_complete(inject_dependencies())
                except RuntimeError:
                    # 降级到同步初始化
                    original_init(self, *args, **kwargs)

        cls.__init__ = __init__
        cls._injectable_service_name = service_name
        cls._injectable_dependencies = dependencies or []

        return cls

    return decorator
