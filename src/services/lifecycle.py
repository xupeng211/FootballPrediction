"""
服务生命周期管理

提供服务的启动、停止和生命周期管理功能。
"""

import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime

from .core import EnhancedBaseService
from src.core.logging import get_logger

logger = get_logger(__name__)


class ServiceLifecycleManager:
    """服务生命周期管理器"""

    def __init__(self):
        self._services: Dict[str, EnhancedBaseService] = {}
        self._startup_order: List[str] = []
        self._shutdown_order: List[str] = []
        self._managed_services: Set[str] = set()
        self._starting = False
        self._stopping = False

    def register_service(
        self, service: EnhancedBaseService, startup_order: int = 0
    ) -> None:
        """注册服务

        Args:
            service: 服务实例
            startup_order: 启动顺序（数字越小越早启动）
        """
        name = service.name
        if name in self._services:
            logger.warning(f"Service {name} already registered, replacing...")
            self._services[name] = service
        else:
            self._services[name] = service
            logger.info(f"Registered service: {name}")

        # 更新启动顺序
        self._update_startup_order(name, startup_order)

    def _update_startup_order(self, name: str, order: int) -> None:
        """更新启动顺序"""
        # 移除旧的顺序
        if name in self._startup_order:
            # 找到并移除
            pass

        # 按顺序插入
        inserted = False
        for i, (existing_name, existing_order) in enumerate(self._startup_order):
            if order < existing_order:
                self._startup_order.insert(i, (name, order))
                inserted = True
                break

        if not inserted:
            self._startup_order.append((name, order))

        # 生成关闭顺序（启动顺序的逆序）
        self._shutdown_order = [name for name, _ in reversed(self._startup_order)]

    async def start_all(self) -> bool:
        """启动所有注册的服务"""
        if self._starting:
            logger.warning("Already starting services...")
            return False

        self._starting = True
        logger.info("Starting all services...")

        success = True
        started_services = []

        try:
            # 按启动顺序启动服务
            for name, _ in self._startup_order:
                if name not in self._services:
                    logger.error(f"Service {name} not found in registry")
                    success = False
                    continue

                service = self._services[name]
                logger.info(f"Starting service: {name}")

                try:
                    if await service.start():
                        started_services.append(name)
                        self._managed_services.add(name)
                        logger.info(f"Service {name} started successfully")
                    else:
                        logger.error(f"Failed to start service: {name}")
                        success = False
                        break
                except Exception as e:
                    logger.error(f"Exception starting service {name}: {e}")
                    success = False
                    break

            if success:
                logger.info(
                    f"All services started successfully ({len(started_services)} services)"
                )
            else:
                # 如果有服务启动失败，停止已启动的服务
                logger.error(
                    "Some services failed to start, stopping started services..."
                )
                await self._stop_services(started_services)

        finally:
            self._starting = False

        return success

    async def stop_all(self) -> bool:
        """停止所有服务"""
        if self._stopping:
            logger.warning("Already stopping services...")
            return False

        self._stopping = True
        logger.info("Stopping all services...")

        success = True
        list(self._managed_services)

        try:
            # 按关闭顺序停止服务
            for name in self._shutdown_order:
                if name not in self._managed_services:
                    continue

                if name not in self._services:
                    logger.warning(f"Service {name} not found in registry")
                    continue

                service = self._services[name]
                logger.info(f"Stopping service: {name}")

                try:
                    if await service.stop():
                        self._managed_services.remove(name)
                        logger.info(f"Service {name} stopped successfully")
                    else:
                        logger.error(f"Failed to stop service: {name}")
                        success = False
                except Exception as e:
                    logger.error(f"Exception stopping service {name}: {e}")
                    success = False

            if success:
                logger.info("All services stopped successfully")
            else:
                logger.warning("Some services failed to stop gracefully")

        finally:
            self._stopping = False

        return success

    async def start_service(self, name: str) -> bool:
        """启动单个服务"""
        if name not in self._services:
            logger.error(f"Service {name} not registered")
            return False

        if name in self._managed_services:
            logger.warning(f"Service {name} is already running")
            return True

        service = self._services[name]
        if await service.start():
            self._managed_services.add(name)
            return True
        return False

    async def stop_service(self, name: str) -> bool:
        """停止单个服务"""
        if name not in self._services:
            logger.error(f"Service {name} not registered")
            return False

        if name not in self._managed_services:
            logger.warning(f"Service {name} is not running")
            return True

        service = self._services[name]
        if await service.stop():
            self._managed_services.remove(name)
            return True
        return False

    async def _stop_services(self, service_names: List[str]) -> None:
        """停止指定的服务列表"""
        # 按逆序停止
        for name in reversed(service_names):
            if name in self._managed_services:
                await self.stop_service(name)

    def get_service(self, name: str) -> Optional[EnhancedBaseService]:
        """获取服务实例"""
        return self._services.get(name)

    def get_all_services(self) -> Dict[str, EnhancedBaseService]:
        """获取所有注册的服务"""
        return self._services.copy()

    def get_running_services(self) -> List[str]:
        """获取正在运行的服务列表"""
        return list(self._managed_services)

    def get_service_status(self, name: str) -> Optional[str]:
        """获取服务状态"""
        service = self._services.get(name)
        if service:
            return service.get_status()
        return None

    async def check_all_health(self) -> Dict[str, dict]:
        """检查所有服务的健康状态"""
        health_report = {}

        for name in self._managed_services:
            service = self._services.get(name)
            if service:
                try:
                    health_report[name] = await service.health_check()
                except Exception as e:
                    logger.error(f"Failed to check health for {name}: {e}")
                    health_report[name] = {
                        "status": "error",
                        "message": f"Health check failed: {str(e)}",
                    }

        return health_report

    def get_status_summary(self) -> dict:
        """获取状态摘要"""
        return {
            "total_services": len(self._services),
            "running_services": len(self._managed_services),
            "service_names": list(self._services.keys()),
            "running_names": list(self._managed_services),
            "startup_order": [name for name, _ in self._startup_order],
            "shutdown_order": self._shutdown_order,
        }


# 全局生命周期管理器实例
lifecycle_manager = ServiceLifecycleManager()

__all__ = [
    "ServiceLifecycleManager",
    "lifecycle_manager",
]
