"""
服务生命周期管理
Service Lifecycle Management

管理服务的创建、初始化、运行和销毁。
Manages service creation, initialization, running and destruction.
"""

import asyncio
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.exceptions import ServiceLifecycleError

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """服务状态"""

    UNINITIALIZED = "uninitialized"  # 未初始化
    INITIALIZING = "initializing"  # 初始化中
    READY = "ready"  # 就绪
    STARTING = "starting"  # 启动中
    RUNNING = "running"  # 运行中
    STOPPING = "stopping"  # 停止中
    STOPPED = "stopped"  # 已停止
    ERROR = "error"  # 错误状态
    DISPOSED = "disposed"  # 已销毁


@dataclass
class ServiceInfo:
    """服务信息"""

    name: str
    instance: Any
    state: ServiceState = ServiceState.UNINITIALIZED
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[Exception] = None
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.dependencies, str):
            self.dependencies = [self.dependencies]


class IServiceLifecycle(ABC):
    """服务生命周期接口"""

    @abstractmethod
    async def initialize(self) -> None:
        """初始化服务"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动服务"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止服务"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        pass


class ServiceLifecycleManager:
    """服务生命周期管理器"""

    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._start_order: List[str] = []
        self._stop_order: List[str] = []
        self._lock = threading.RLock()
        self._shutdown_event = asyncio.Event()
        self._monitor_task: Optional[asyncio.Task] = None

    def register_service(
        self, name: str, instance: Any, dependencies: Optional[List[str]] = None
    ) -> None:
        """注册服务"""
        with self._lock:
            if name in self._services:
                raise ServiceLifecycleError(f"服务已注册: {name}")

            # 检查循环依赖
            if dependencies:
                self._check_circular_dependency(name, dependencies)

            service_info = ServiceInfo(
                name=name, instance=instance, dependencies=dependencies or []
            )

            self._services[name] = service_info

            # 更新依赖关系
            for dep in service_info.dependencies:
                if dep in self._services:
                    self._services[dep].dependents.append(name)

            logger.info(f"注册服务: {name}, 依赖: {dependencies}")

    def unregister_service(self, name: str) -> None:
        """注销服务"""
        with self._lock:
            if name not in self._services:
                raise ServiceLifecycleError(f"服务未注册: {name}")

            service_info = self._services[name]

            # 检查是否有依赖的服务还在运行
            running_dependents = [
                dep
                for dep in service_info.dependents
                if self._services[dep].state == ServiceState.RUNNING
            ]

            if running_dependents:
                raise ServiceLifecycleError(
                    f"无法注销服务 {name}，以下服务仍在运行: {running_dependents}"
                )

            # 如果服务正在运行，先停止它
            if service_info.state == ServiceState.RUNNING:
                asyncio.create_task(self.stop_service(name))

            # 清理依赖关系
            for dep in service_info.dependencies:
                if dep in self._services:
                    self._services[dep].dependents.remove(name)

            del self._services[name]
            logger.info(f"注销服务: {name}")

    async def initialize_service(self, name: str) -> None:
        """初始化服务"""
        with self._lock:
            if name not in self._services:
                raise ServiceLifecycleError(f"服务未注册: {name}")

            service_info = self._services[name]

            if service_info.state != ServiceState.UNINITIALIZED:
                if service_info.state == ServiceState.ERROR:
                    logger.warning(f"服务 {name} 处于错误状态，尝试重新初始化")
                else:
                    logger.debug(f"服务 {name} 已初始化，跳过")
                    return

            service_info.state = ServiceState.INITIALIZING

        try:
            logger.info(f"初始化服务: {name}")

            # 先初始化依赖的服务
            for dep in service_info.dependencies:
                await self.initialize_service(dep)

            # 执行初始化
            if hasattr(service_info.instance, "initialize"):
                if asyncio.iscoroutinefunction(service_info.instance.initialize):
                    await service_info.instance.initialize()
                else:
                    service_info.instance.initialize()

            # 如果实现了生命周期接口
            if isinstance(service_info.instance, IServiceLifecycle):
                await service_info.instance.initialize()

            with self._lock:
                service_info.state = ServiceState.READY
                logger.info(f"服务初始化完成: {name}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            with self._lock:
                service_info.state = ServiceState.ERROR
                service_info.last_error = e
                service_info.error_count += 1
            logger.error(f"服务初始化失败 {name}: {e}")
            raise ServiceLifecycleError(f"服务初始化失败: {name}") from e

    async def start_service(self, name: str) -> None:
        """启动服务"""
        with self._lock:
            if name not in self._services:
                raise ServiceLifecycleError(f"服务未注册: {name}")

            service_info = self._services[name]

            if service_info.state == ServiceState.RUNNING:
                logger.debug(f"服务已在运行: {name}")
                return

            if service_info.state not in [ServiceState.READY, ServiceState.STOPPED]:
                await self.initialize_service(name)

            service_info.state = ServiceState.STARTING

        try:
            logger.info(f"启动服务: {name}")

            # 先启动依赖的服务
            for dep in service_info.dependencies:
                await self.start_service(dep)

            # 执行启动
            if hasattr(service_info.instance, "start"):
                if asyncio.iscoroutinefunction(service_info.instance.start):
                    await service_info.instance.start()
                else:
                    service_info.instance.start()

            # 如果实现了生命周期接口
            if isinstance(service_info.instance, IServiceLifecycle):
                await service_info.instance.start()

            with self._lock:
                service_info.state = ServiceState.RUNNING
                service_info.started_at = datetime.utcnow()
                logger.info(f"服务启动完成: {name}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            with self._lock:
                service_info.state = ServiceState.ERROR
                service_info.last_error = e
                service_info.error_count += 1
            logger.error(f"服务启动失败 {name}: {e}")
            raise ServiceLifecycleError(f"服务启动失败: {name}") from e

    async def stop_service(self, name: str) -> None:
        """停止服务"""
        with self._lock:
            if name not in self._services:
                raise ServiceLifecycleError(f"服务未注册: {name}")

            service_info = self._services[name]

            if service_info.state != ServiceState.RUNNING:
                logger.debug(f"服务未在运行: {name}")
                return

            service_info.state = ServiceState.STOPPING

        try:
            logger.info(f"停止服务: {name}")

            # 先停止依赖于此的服务
            for dependent in service_info.dependents:
                if self._services[dependent].state == ServiceState.RUNNING:
                    await self.stop_service(dependent)

            # 执行停止
            if hasattr(service_info.instance, "stop"):
                if asyncio.iscoroutinefunction(service_info.instance.stop):
                    await service_info.instance.stop()
                else:
                    service_info.instance.stop()

            # 如果实现了生命周期接口
            if isinstance(service_info.instance, IServiceLifecycle):
                await service_info.instance.stop()

            with self._lock:
                service_info.state = ServiceState.STOPPED
                service_info.stopped_at = datetime.utcnow()
                logger.info(f"服务停止完成: {name}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            with self._lock:
                service_info.state = ServiceState.ERROR
                service_info.last_error = e
                service_info.error_count += 1
            logger.error(f"服务停止失败 {name}: {e}")
            raise ServiceLifecycleError(f"服务停止失败: {name}") from e

    async def start_all_services(self) -> None:
        """启动所有服务"""
        logger.info("启动所有服务")

        # 计算启动顺序（拓扑排序）
        self._calculate_startup_order()

        for service_name in self._start_order:
            try:
                await self.start_service(service_name)
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"启动服务失败 {service_name}: {e}")
                # 继续启动其他服务
                continue

        logger.info("所有服务启动完成")

    async def stop_all_services(self) -> None:
        """停止所有服务"""
        logger.info("停止所有服务")

        # 计算停止顺序（启动顺序的逆序）
        self._calculate_stop_order()

        for service_name in self._stop_order:
            try:
                await self.stop_service(service_name)
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"停止服务失败 {service_name}: {e}")
                continue

        logger.info("所有服务停止完成")

    def get_service_state(self, name: str) -> ServiceState:
        """获取服务状态"""
        with self._lock:
            if name not in self._services:
                raise ServiceLifecycleError(f"服务未注册: {name}")
            return self._services[name].state

    def get_service_info(self, name: str) -> ServiceInfo:
        """获取服务信息"""
        with self._lock:
            if name not in self._services:
                raise ServiceLifecycleError(f"服务未注册: {name}")
            return self._services[name]

    def get_all_services(self) -> Dict[str, ServiceInfo]:
        """获取所有服务信息"""
        with self._lock:
            return self._services.copy()

    def get_running_services(self) -> List[str]:
        """获取正在运行的服务"""
        with self._lock:
            return [
                name
                for name, info in self._services.items()
                if info.state == ServiceState.RUNNING
            ]

    async def health_check(self, name: Optional[str] = None) -> Dict[str, bool]:
        """健康检查"""
        results = {}

        services_to_check = [name] if name else list(self._services.keys())

        for service_name in services_to_check:
            if service_name not in self._services:
                results[service_name] = False
                continue

            service_info = self._services[service_name]

            if service_info.state != ServiceState.RUNNING:
                results[service_name] = False
                continue

            try:
                # 执行健康检查
                if hasattr(service_info.instance, "health_check"):
                    if asyncio.iscoroutinefunction(service_info.instance.health_check):
                        healthy = await service_info.instance.health_check()
                    else:
                        healthy = service_info.instance.health_check()
                elif isinstance(service_info.instance, IServiceLifecycle):
                    healthy = service_info.instance.health_check()
                else:
                    # 默认健康检查：只要服务在运行就认为是健康的
                    healthy = True

                results[service_name] = healthy

            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"健康检查失败 {service_name}: {e}")
                results[service_name] = False

        return results

    def start_monitoring(self, interval: float = 30.0) -> None:
        """启动监控"""
        if self._monitor_task and not self._monitor_task.done():
            logger.warning("监控已在运行")
            return

        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info(f"启动服务监控，间隔: {interval}秒")

    def stop_monitoring(self) -> None:
        """停止监控"""
        if self._monitor_task:
            self._monitor_task.cancel()
            logger.info("停止服务监控")

    async def _monitor_loop(self, interval: float) -> None:
        """监控循环"""
        while not self._shutdown_event.is_set():
            try:
                # 执行健康检查
                health_results = await self.health_check()

                # 记录不健康的服务
                unhealthy_services = [
                    name for name, healthy in health_results.items() if not healthy
                ]

                if unhealthy_services:
                    logger.warning(f"发现不健康的服务: {unhealthy_services}")

                # 等待下次检查
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), timeout=interval
                    )
                    break  # 收到停止信号
                except asyncio.TimeoutError:
                    continue  # 继续循环

            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(interval)

    async def shutdown(self) -> None:
        """关闭管理器"""
        logger.info("关闭服务生命周期管理器")

        # 停止监控
        self.stop_monitoring()
        self._shutdown_event.set()

        # 停止所有服务
        await self.stop_all_services()

        # 清理资源
        with self._lock:
            for service_info in self._services.values():
                if hasattr(service_info.instance, "cleanup"):
                    try:
                        if asyncio.iscoroutinefunction(service_info.instance.cleanup):
                            await service_info.instance.cleanup()
                        else:
                            service_info.instance.cleanup()
                    except (
                        ValueError,
                        TypeError,
                        AttributeError,
                        KeyError,
                        RuntimeError,
                    ) as e:
                        logger.error(f"清理服务资源失败 {service_info.name}: {e}")

        logger.info("服务生命周期管理器已关闭")

    def _check_circular_dependency(self, name: str, dependencies: List[str]) -> None:
        """检查循环依赖"""
        visited = set()
        stack = [(name, dependencies.copy())]

        while stack:
            current, deps = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            for dep in deps:
                if dep == name:
                    raise ServiceLifecycleError(f"检测到循环依赖: {name}")
                if dep in self._services:
                    dep_deps = self._services[dep].dependencies
                    if dep_deps:
                        stack.append((dep, dep_deps))

    def _calculate_startup_order(self) -> None:
        """计算启动顺序（拓扑排序）"""
        self._start_order = []
        visited = set()
        temp_visited = set()

        def visit(service_name: str) -> None:
            if service_name in temp_visited:
                raise ServiceLifecycleError(f"检测到循环依赖: {service_name}")
            if service_name in visited:
                return

            temp_visited.add(service_name)

            if service_name in self._services:
                for dep in self._services[service_name].dependencies:
                    visit(dep)

            temp_visited.remove(service_name)
            visited.add(service_name)
            self._start_order.append(service_name)

        for service_name in self._services:
            visit(service_name)

    def _calculate_stop_order(self) -> None:
        """计算停止顺序（启动顺序的逆序）"""
        self._stop_order = self._start_order.copy()
        self._stop_order.reverse()


# 全局服务生命周期管理器
_default_lifecycle_manager: Optional[ServiceLifecycleManager] = None


def get_lifecycle_manager() -> ServiceLifecycleManager:
    """获取默认的生命周期管理器"""
    global _default_lifecycle_manager
    if _default_lifecycle_manager is None:
        _default_lifecycle_manager = ServiceLifecycleManager()
    return _default_lifecycle_manager


# 生命周期装饰器
def lifecycle_service(
    name: Optional[str] = None, dependencies: Optional[List[str]] = None
):
    """服务生命周期装饰器"""

    def decorator(cls):
        # 获取服务名称
        service_name = name or cls.__name__

        # 保存原始的 __init__ 方法
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            # 调用原始初始化
            original_init(self, *args, **kwargs)

            # 注册到生命周期管理器
            manager = get_lifecycle_manager()
            manager.register_service(service_name, self, dependencies)

        cls.__init__ = new_init

        return cls

    return decorator
