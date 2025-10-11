"""
适配器注册表
Adapter Registry

管理适配器的注册、发现和生命周期。
Manages adapter registration, discovery, and lifecycle.
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from .base import Adapter, AdapterStatus
from .factory import AdapterFactory, AdapterConfig, AdapterGroupConfig


class RegistryStatus(Enum):
    """注册表状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SHUTTING_DOWN = "shutting_down"


class AdapterRegistry:
    """适配器注册表，管理所有适配器的生命周期"""

    def __init__(self, factory: Optional[AdapterFactory] = None):
        self.factory = factory or AdapterFactory()
        self.adapters: Dict[str, Adapter] = {}
        self.groups: Dict[str, Adapter] = {}
        self.status = RegistryStatus.INACTIVE
        self.health_check_interval: float = 60.0  # 秒
        self._health_check_task: Optional[asyncio.Task] = None
        self._metrics_collector: Optional[Dict[str, Any]] = None

    async def initialize(self) -> None:
        """初始化注册表"""
        if self.status != RegistryStatus.INACTIVE:
            raise RuntimeError("Registry already initialized")

        self.status = RegistryStatus.ACTIVE

        # 启动健康检查任务
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def shutdown(self) -> None:
        """关闭注册表"""
        if self.status == RegistryStatus.SHUTTING_DOWN:
            return

        self.status = RegistryStatus.SHUTTING_DOWN

        # 停止健康检查任务
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # 清理所有适配器
        cleanup_tasks = []
        for adapter in self.adapters.values():
            cleanup_tasks.append(adapter.cleanup())

        # 清理所有组
        for group in self.groups.values():
            cleanup_tasks.append(group.cleanup())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self.status = RegistryStatus.INACTIVE

    async def register_adapter(self, config: AdapterConfig) -> Adapter:
        """注册适配器"""
        if self.status != RegistryStatus.ACTIVE:
            raise RuntimeError("Registry not active")

        # 检查是否已存在
        if config.name in self.adapters:
            raise ValueError(f"Adapter {config.name} already registered")

        # 创建适配器
        adapter = self.factory.create_adapter(config)

        # 初始化适配器
        await adapter.initialize()

        # 注册
        self.adapters[config.name] = adapter

        return adapter

    async def unregister_adapter(self, name: str) -> None:
        """注销适配器"""
        if name in self.adapters:
            adapter = self.adapters[name]
            await adapter.cleanup()
            del self.adapters[name]

    async def register_group(self, group_config: AdapterGroupConfig) -> Adapter:
        """注册适配器组"""
        if self.status != RegistryStatus.ACTIVE:
            raise RuntimeError("Registry not active")

        if group_config.name in self.groups:
            raise ValueError(f"Group {group_config.name} already registered")

        # 创建组
        group = self.factory.create_adapter_group(group_config)

        # 初始化组
        await group.initialize()

        # 注册
        self.groups[group_config.name] = group

        return group

    async def unregister_group(self, name: str) -> None:
        """注销适配器组"""
        if name in self.groups:
            group = self.groups[name]
            await group.cleanup()
            del self.groups[name]

    def get_adapter(self, name: str) -> Optional[Adapter]:
        """获取适配器"""
        return self.adapters.get(name)

    def get_group(self, name: str) -> Optional[Adapter]:
        """获取适配器组"""
        return self.groups.get(name)

    def list_adapters(self) -> List[str]:
        """列出所有适配器名称"""
        return list(self.adapters.keys())

    def list_groups(self) -> List[str]:
        """列出所有组名称"""
        return list(self.groups.keys())

    def get_adapters_by_type(self, adapter_type: str) -> List[Adapter]:
        """按类型获取适配器"""
        return [
            adapter
            for adapter in self.adapters.values()
            if adapter.__class__.__name__ == adapter_type
        ]

    def get_active_adapters(self) -> List[Adapter]:
        """获取所有活跃的适配器"""
        return [
            adapter
            for adapter in self.adapters.values()
            if adapter.status == AdapterStatus.ACTIVE
        ]

    def get_inactive_adapters(self) -> List[Adapter]:
        """获取所有非活跃的适配器"""
        return [
            adapter
            for adapter in self.adapters.values()
            if adapter.status != AdapterStatus.ACTIVE
        ]

    async def enable_adapter(self, name: str) -> bool:
        """启用适配器"""
        adapter = self.adapters.get(name)
        if adapter:
            try:
                await adapter.initialize()
                return True
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
                return False
        return False

    async def disable_adapter(self, name: str) -> bool:
        """禁用适配器"""
        adapter = self.adapters.get(name)
        if adapter:
            try:
                await adapter.cleanup()
                adapter.status = AdapterStatus.INACTIVE
                return True
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
                return False
        return False

    async def restart_adapter(self, name: str) -> bool:
        """重启适配器"""
        adapter = self.adapters.get(name)
        if adapter:
            try:
                await adapter.cleanup()
                await adapter.initialize()
                return True
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
                return False
        return False

    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self.status == RegistryStatus.ACTIVE:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                # 健康检查失败不应中断循环
                print(f"Health check error: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def _perform_health_checks(self) -> None:
        """执行健康检查"""
        health_results = {}

        # 检查单个适配器
        for name, adapter in self.adapters.items():
            try:
                result = await adapter.health_check()
                health_results[name] = result
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                health_results[name] = {
                    "adapter": name,
                    "status": "error",
                    "error": str(e),
                }

        # 检查适配器组
        for name, group in self.groups.items():
            try:
                result = await group.health_check()
                health_results[f"group:{name}"] = result
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                health_results[f"group:{name}"] = {
                    "adapter": f"group:{name}",
                    "status": "error",
                    "error": str(e),
                }

        # 更新指标
        if self._metrics_collector:
            self._metrics_collector["last_health_check"] = datetime.utcnow()
            self._metrics_collector["health_results"] = health_results

    async def get_health_status(self) -> Dict[str, Any]:
        """获取整体健康状态"""
        if self.status != RegistryStatus.ACTIVE:
            return {
                "registry_status": "inactive",
                "adapters": {},
                "groups": {},
            }

        health_status = {
            "registry_status": "active",
            "total_adapters": len(self.adapters),
            "active_adapters": len(self.get_active_adapters()),
            "inactive_adapters": len(self.get_inactive_adapters()),
            "total_groups": len(self.groups),
            "last_health_check": None,
            "adapters": {},
            "groups": {},
        }

        # 获取各适配器状态
        for name, adapter in self.adapters.items():
            health_status["adapters"][name] = {  # type: ignore
                "status": adapter.status.value,
                "metrics": adapter.get_metrics(),
            }

        # 获取各组状态
        for name, group in self.groups.items():
            health_status["groups"][name] = {  # type: ignore
                "status": group.status.value,
                "metrics": group.get_metrics(),
            }

        # 获取最后健康检查时间
        if self._metrics_collector:
            health_status["last_health_check"] = self._metrics_collector.get(
                "last_health_check"
            )

        return health_status

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        total_requests = 0
        total_successful = 0
        total_failed = 0
        adapter_types: Dict[str, int] = {}

        for adapter in self.adapters.values():
            metrics = adapter.get_metrics()
            total_requests += metrics["total_requests"]
            total_successful += metrics["successful_requests"]
            total_failed += metrics["failed_requests"]

            adapter_type = adapter.__class__.__name__
            adapter_types[adapter_type] = adapter_types.get(adapter_type, 0) + 1

        return {
            "total_requests": total_requests,
            "total_successful": total_successful,
            "total_failed": total_failed,
            "success_rate": (
                total_successful / total_requests if total_requests > 0 else 0
            ),
            "adapter_types": adapter_types,
            "registered_adapters": len(self.adapters),
            "registered_groups": len(self.groups),
        }

    async def find_best_adapter(
        self,
        adapter_type: Optional[str] = None,
        max_response_time: Optional[float] = None,
        min_success_rate: Optional[float] = None,
    ) -> Optional[Adapter]:
        """找到最佳的适配器"""
        candidates = []

        for adapter in self.get_active_adapters():
            # 按类型筛选
            if adapter_type and adapter.__class__.__name__ != adapter_type:
                continue

            metrics = adapter.get_metrics()

            # 按响应时间筛选
            if (
                max_response_time
                and metrics["average_response_time"] > max_response_time
            ):
                continue

            # 按成功率筛选
            if min_success_rate and metrics["success_rate"] < min_success_rate:
                continue

            candidates.append((adapter, metrics["success_rate"]))

        # 返回成功率最高的适配器
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def enable_metrics_collection(self) -> None:
        """启用指标收集"""
        self._metrics_collector = {
            "start_time": datetime.utcnow(),
            "health_checks": 0,
            "adapter_failures": {},
        }

    def disable_metrics_collection(self) -> None:
        """禁用指标收集"""
        self._metrics_collector = None


# 全局适配器注册表实例
adapter_registry = AdapterRegistry()
