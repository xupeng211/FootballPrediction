"""
服务健康检查器

提供服务健康状态监控和检查功能。
"""

import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.core import logger
from ..base import BaseService


@dataclass
class HealthStatus:
    """健康状态数据"""
    service_name: str
    healthy: bool
    message: str
    timestamp: datetime
    response_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ServiceHealthChecker:
    """服务健康检查器"""

    def __init__(self, check_interval: int = 60) -> None:
        self.check_interval = check_interval
        self._health_checks: Dict[str, Callable] = {}
        self._health_status: Dict[str, HealthStatus] = {}
        self._last_check: Optional[datetime] = None
        self.logger = logger
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def register_check(self, service_name: str, check_func: Callable) -> None:
        """注册健康检查函数"""
        self._health_checks[service_name] = check_func
        self.logger.debug(f"已注册健康检查: {service_name}")

    def unregister_check(self, service_name: str) -> None:
        """注销健康检查函数"""
        if service_name in self._health_checks:
            del self._health_checks[service_name]
            self.logger.debug(f"已注销健康检查: {service_name}")

    async def check_service(self, service_name: str, service: BaseService) -> HealthStatus:
        """检查单个服务的健康状态"""
        start_time = datetime.now()

        try:
            # 优先使用注册的检查函数
            if service_name in self._health_checks:
                check_func = self._health_checks[service_name]
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
            else:
                # 使用服务的健康检查方法
                if hasattr(service, 'health_check'):
                    if asyncio.iscoroutinefunction(service.health_check):
                        result = await service.health_check()
                    else:
                        result = service.health_check()
                else:
                    # 默认健康检查：检查服务是否已初始化
                    result = getattr(service, 'initialized', True)

            response_time = (datetime.now() - start_time).total_seconds()

            status = HealthStatus(
                service_name=service_name,
                healthy=bool(result),
                message="Healthy" if result else "Unhealthy",
                timestamp=start_time,
                response_time=response_time,
                metadata={"check_method": "custom" if service_name in self._health_checks else "service_method"}
            )

            self._health_status[service_name] = status
            return status

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            status = HealthStatus(
                service_name=service_name,
                healthy=False,
                message=f"Health check failed: {str(e)}",
                timestamp=start_time,
                response_time=response_time,
                metadata={"error": str(e)}
            )
            self._health_status[service_name] = status
            self.logger.error(f"健康检查异常: {service_name}, {e}")
            return status

    async def check_all_services(self, services: Dict[str, BaseService]) -> Dict[str, HealthStatus]:
        """检查所有服务的健康状态"""
        results = {}
        tasks = []

        # 并发检查所有服务
        for name, service in services.items():
            task = asyncio.create_task(self.check_service(name, service))
            tasks.append((name, task))

        # 等待所有检查完成
        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                self.logger.error(f"健康检查任务异常: {name}, {e}")
                # 创建失败状态
                results[name] = HealthStatus(
                    service_name=name,
                    healthy=False,
                    message=f"Check task failed: {str(e)}",
                    timestamp=datetime.now()
                )

        self._last_check = datetime.now()
        return results

    def get_status(self, service_name: str) -> Optional[HealthStatus]:
        """获取服务的最新健康状态"""
        return self._health_status.get(service_name)

    def get_all_status(self) -> Dict[str, HealthStatus]:
        """获取所有服务的最新健康状态"""
        return self._health_status.copy()

    def get_unhealthy_services(self) -> List[str]:
        """获取不健康的服务列表"""
        return [name for name, status in self._health_status.items() if not status.healthy]

    def get_healthy_services(self) -> List[str]:
        """获取健康的服务列表"""
        return [name for name, status in self._health_status.items() if status.healthy]

    async def start_monitoring(self, services: Dict[str, BaseService]) -> None:
        """开始定期健康检查监控"""
        if self._running:
            self.logger.warning("健康检查监控已在运行")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop(services))
        self.logger.info("已启动健康检查监控")

    async def stop_monitoring(self) -> None:
        """停止健康检查监控"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info("已停止健康检查监控")

    async def _monitor_loop(self, services: Dict[str, BaseService]) -> None:
        """监控循环"""
        while self._running:
            try:
                await self.check_all_services(services)
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"健康检查监控异常: {e}")
                await asyncio.sleep(min(self.check_interval, 30))

    def get_summary(self) -> Dict[str, Any]:
        """获取健康检查摘要"""
        total = len(self._health_status)
        healthy = len(self.get_healthy_services())
        unhealthy = len(self.get_unhealthy_services())

        return {
            "total_services": total,
            "healthy_count": healthy,
            "unhealthy_count": unhealthy,
            "healthy_percentage": (healthy / total * 100) if total > 0 else 0,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "monitoring_active": self._running,
        }