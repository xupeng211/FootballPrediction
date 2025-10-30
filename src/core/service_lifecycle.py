"""
服务生命周期管理器
ServiceLifecycleManager

管理服务的注册,启动,停止和监控.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """服务状态枚举"""
    INITIALIZED = "initialized"
    READY = "ready"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    service: Any
    state: ServiceState
    dependencies: List[str]
    dependents: List[str]
    health_check: Optional[Callable] = None
    startup_timeout: float = 30.0
    shutdown_timeout: float = 10.0
    last_health_check: Optional[datetime] = None


class ServiceLifecycleError(Exception):
    """服务生命周期错误"""
    pass


class ServiceLifecycleManager:
    """服务生命周期管理器"""

    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def register_service(
        self,
        name: str,
        service: Any,
        dependencies: Optional[List[str]] = None,
        health_check: Optional[Callable] = None,
        startup_timeout: float = 30.0,
        shutdown_timeout: float = 10.0
    ) -> None:
        """注册服务"""
        with self._lock:
            if name in self._services:
                logger.warning(f"服务已存在: {name}")
                return

            service_info = ServiceInfo(
                name=name,
                service=service,
                state=ServiceState.INITIALIZED,
                dependencies=dependencies or [],
                dependents=[],
                health_check=health_check,
                startup_timeout=startup_timeout,
                shutdown_timeout=shutdown_timeout
            )

            self._services[name] = service_info

            # 更新依赖关系
            for dep in service_info.dependencies:
                if dep in self._services:
                    self._services[dep].dependents.append(name)

            logger.info(f"注册服务: {name}")

    def unregister_service(self, name: str) -> None:
        """注销服务"""
        with self._lock:
            if name not in self._services:
                raise ServiceLifecycleError(f"服务未注册: {name}")

            service_info = self._services[name]

            # 停止服务（如果正在运行）
            if service_info.state == ServiceState.RUNNING:
                self._stop_service_sync(name)

            # 移除依赖关系
            for dep in service_info.dependencies:
                if dep in self._services:
                    self._services[dep].dependents.remove(name)

            del self._services[name]
            logger.info(f"注销服务: {name}")

    def start_service(self, name: str) -> None:
        """启动服务"""
        with self._lock:
            if name not in self._services:
                raise ServiceLifecycleError(f"服务未注册: {name}")

            service_info = self._services[name]

            if service_info.state == ServiceState.RUNNING:
                logger.debug(f"服务已在运行: {name}")
                return

            if service_info.state not in [ServiceState.READY, ServiceState.STOPPED]:
                raise ServiceLifecycleError(f"服务状态不允许启动: {name} - {service_info.state.value}")

            service_info.state = ServiceState.STARTING

        try:
            logger.info(f"启动服务: {name}")

            # 先启动依赖的服务
            for dep in service_info.dependencies:
                self.start_service(dep)

            # 启动当前服务
            if hasattr(service_info.service, 'start'):
                if asyncio.iscoroutinefunction(service_info.service.start):
                    # 异步启动
                    self._start_service_async(name)
                else:
                    # 同步启动
                    service_info.service.start()

            service_info.state = ServiceState.RUNNING
            logger.info(f"服务启动成功: {name}")

        except Exception as e:
            service_info.state = ServiceState.ERROR
            logger.error(f"服务启动失败: {name} - {e}")
            raise ServiceLifecycleError(f"服务启动失败: {name}") from e

    def stop_service(self, name: str) -> None:
        """停止服务"""
        with self._lock:
            if name not in self._services:
                raise ServiceLifecycleError(f"服务未注册: {name}")

            service_info = self._services[name]

            if service_info.state != ServiceState.RUNNING:
                logger.debug(f"服务未运行: {name}")
                return

            self._stop_service_sync(name)

    def _stop_service_sync(self, name: str) -> None:
        """同步停止服务"""
        service_info = self._services[name]
        service_info.state = ServiceState.STOPPING

        try:
            logger.info(f"停止服务: {name}")

            # 先停止依赖于此服务的服务
            for dependent in service_info.dependents:
                if self._services[dependent].state == ServiceState.RUNNING:
                    self._stop_service_sync(dependent)

            # 停止当前服务
            if hasattr(service_info.service, 'stop'):
                if asyncio.iscoroutinefunction(service_info.service.stop):
                    # 异步停止
                    self._stop_service_async(name)
                else:
                    # 同步停止
                    service_info.service.stop()

            service_info.state = ServiceState.STOPPED
            logger.info(f"服务停止成功: {name}")

        except Exception as e:
            service_info.state = ServiceState.ERROR
            logger.error(f"服务停止失败: {name} - {e}")
            raise ServiceLifecycleError(f"服务停止失败: {name}") from e

    async def _start_service_async(self, name: str) -> None:
        """异步启动服务"""
        service_info = self._services[name]
        try:
            await asyncio.wait_for(
                service_info.service.start(),
                timeout=service_info.startup_timeout
            )
        except asyncio.TimeoutError:
            raise ServiceLifecycleError(f"服务启动超时: {name}")

    async def _stop_service_async(self, name: str) -> None:
        """异步停止服务"""
        service_info = self._services[name]
        try:
            await asyncio.wait_for(
                service_info.service.stop(),
                timeout=service_info.shutdown_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"服务停止超时: {name}")

    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        health_results = {}

        with self._lock:
            for name, service_info in self._services.items():
                if service_info.state == ServiceState.RUNNING:
                    try:
                        if service_info.health_check:
                            if asyncio.iscoroutinefunction(service_info.health_check):
                                healthy = await service_info.health_check(service_info.service)
                            else:
                                healthy = service_info.health_check(service_info.service)
                        else:
                            # 默认健康检查:检查服务是否有严重错误
                            healthy = service_info.state != ServiceState.ERROR

                        health_results[name] = healthy
                        service_info.last_health_check = datetime.now()

                    except Exception as e:
                        logger.warning(f"健康检查失败: {name} - {e}")
                        health_results[name] = False
                        service_info.last_health_check = datetime.now()
                else:
                    health_results[name] = False

        return health_results

    def get_service_status(self, name: str) -> Optional[ServiceInfo]:
        """获取服务状态"""
        with self._lock:
            return self._services.get(name)

    def get_all_services(self) -> Dict[str, ServiceInfo]:
        """获取所有服务"""
        with self._lock:
            return self._services.copy()

    def start_monitoring(self, interval: float = 30.0) -> None:
        """启动监控"""
        if self._monitoring_task is not None:
            logger.warning("监控已在运行")
            return

        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        self._monitoring_task = self._loop.create_task(self._monitoring_loop(interval))
        logger.info("启动服务监控")

    def stop_monitoring(self) -> None:
        """停止监控"""
        if self._monitoring_task is None:
            return

        self._shutdown_event.set()

        if self._monitoring_task:
            self._monitoring_task.cancel()

        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

        self._monitoring_task = None
        self._loop = None
        logger.info("停止服务监控")

    async def _monitoring_loop(self, interval: float) -> None:
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
                    logger.warning(f"不健康的服务: {unhealthy_services}")

                # 等待下次检查
                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(5)  # 错误时短暂等待

    def shutdown_all(self) -> None:
        """关闭所有服务"""
        logger.info("开始关闭所有服务")

        # 停止监控
        self.stop_monitoring()

        # 停止所有服务
        with self._lock:
            running_services = [
                name for name, info in self._services.items()
                if info.state == ServiceState.RUNNING
            ]

        # 按依赖关系顺序停止
        for name in running_services:
            try:
                self.stop_service(name)
            except Exception as e:
                logger.error(f"停止服务失败: {name} - {e}")

        logger.info("所有服务已关闭")


# 全局服务生命周期管理器实例
_lifecycle_manager: Optional[ServiceLifecycleManager] = None


def get_lifecycle_manager() -> ServiceLifecycleManager:
    """获取全局服务生命周期管理器"""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = ServiceLifecycleManager()
    return _lifecycle_manager