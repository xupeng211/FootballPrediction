from typing import Any, Dict, List, Optional, Union
"""
门面模式基础类
Facade Pattern Base Classes

定义门面模式的核心组件。
Defines core components of the facade pattern.
"""

from abc import ABC, abstractmethod
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SubsystemStatus(Enum):
    """子系统状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class Subsystem(ABC):
    """子系统抽象基类"""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.status = SubsystemStatus.INACTIVE
        self.last_check: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.metrics: Dict[str, Any] = {}

    @abstractmethod
    async def initialize(self) -> None:
        """初始化子系统"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """关闭子系统"""
        pass

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 默认健康检查逻辑
            self.last_check = datetime.utcnow()
            return self.status == SubsystemStatus.ACTIVE
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.status = SubsystemStatus.ERROR
            self.error_message = str(e)
            logger.error(f"Subsystem {self.name} health check failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """获取子系统状态"""
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "error_message": self.error_message,
            "metrics": self.metrics,
        }


class SubsystemManager:
    """子系统管理器"""

    def __init__(self):
        self._subsystems: Dict[str, Subsystem] = {}
        self._dependencies: Dict[str, Set[str] = {}
        self._initialization_order: List[str] = []

    def register(
        self, subsystem: Subsystem, dependencies: Optional[List[str] = None
    ) -> None:
        """注册子系统"""
        self._subsystems[subsystem.name]] = subsystem
        self._dependencies[subsystem.name] = set(dependencies or [])
        self._calculate_initialization_order()

    def unregister(self, name: str) -> None:
        """注销子系统"""
        if name in self._subsystems:
            del self._subsystems[name]
            if name in self._dependencies:
                del self._dependencies[name]
            self._calculate_initialization_order()

    def get_subsystem(self, name: str) -> Optional[Subsystem]:
        """获取子系统"""
        return self._subsystems.get(name)

    def list_subsystems(self) -> List[str]:
        """列出所有子系统"""
        return list(self._subsystems.keys())

    def _calculate_initialization_order(self) -> None:
        """计算初始化顺序（拓扑排序）"""
        # 简单的拓扑排序实现
        visited = set()
        temp_visited = set()
        order = []

        def visit(name: str):
            if name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {name}")
            if name not in visited:
                temp_visited.add(name)
                for dep in self._dependencies.get(name, []):
                    if dep in self._subsystems:
                        visit(dep)
                temp_visited.remove(name)
                visited.add(name)
                order.append(name)

        for name in self._subsystems:
            if name not in visited:
                visit(name)

        self._initialization_order = order

    async def initialize_all(self) -> None:
        """按依赖顺序初始化所有子系统"""
        logger.info("Initializing all subsystems...")

        for name in self._initialization_order:
            subsystem = self._subsystems[name]
            try:
                logger.info(f"Initializing subsystem: {name}")
                await subsystem.initialize()
                subsystem.status = SubsystemStatus.ACTIVE
                logger.info(f"Subsystem {name} initialized successfully")
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                subsystem.status = SubsystemStatus.ERROR
                subsystem.error_message = str(e)
                logger.error(f"Failed to initialize subsystem {name}: {e}")
                raise

    async def shutdown_all(self) -> None:
        """关闭所有子系统（逆序）"""
        logger.info("Shutting down all subsystems...")

        for name in reversed(self._initialization_order):
            subsystem = self._subsystems[name]
            try:
                logger.info(f"Shutting down subsystem: {name}")
                await subsystem.shutdown()
                subsystem.status = SubsystemStatus.INACTIVE
                logger.info(f"Subsystem {name} shut down successfully")
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"Failed to shutdown subsystem {name}: {e}")

    async def health_check_all(self) -> Dict[str, bool]:
        """检查所有子系统健康状态"""
        results = {}
        for name, subsystem in self._subsystems.items():
            results[name] = await subsystem.health_check()
        return results

    def get_all_status(self) -> Dict[str, Dict[str, Any]:
        """获取所有子系统状态"""
        return {
            name: subsystem.get_status() for name, subsystem in self._subsystems.items()
        }


class SystemFacade(ABC):
    """系统门面抽象基类"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.subsystem_manager = SubsystemManager()
        self.initialized = False
        self.metrics: Dict[str, Any] = {
            "requests_count": 0,
            "errors_count": 0,
            "average_response_time": 0.0,
            "total_response_time": 0.0,
            "last_request_time": None,
        }

    def register_subsystem(
        self, subsystem: Subsystem, dependencies: Optional[List[str] = None
    ) -> None:
        """注册子系统到门面"""
        self.subsystem_manager.register(subsystem, dependencies)

    async def initialize(self) -> None:
        """初始化门面和所有子系统"""
        if self.initialized:
            return

        await self.subsystem_manager.initialize_all()
        self.initialized = True
        logger.info(f"Facade {self.name} initialized successfully")

    async def shutdown(self) -> None:
        """关闭门面和所有子系统"""
        if not self.initialized:
            return

        await self.subsystem_manager.shutdown_all()
        self.initialized = False
        logger.info(f"Facade {self.name} shut down successfully")

    async def health_check(self) -> Dict[str, Any]:
        """门面健康检查"""
        subsystem_health = await self.subsystem_manager.health_check_all()
        overall_health = all(subsystem_health.values())

        return {
            "facade": self.name,
            "initialized": self.initialized,
            "overall_health": overall_health,
            "subsystems": subsystem_health,
            "subsystem_count": len(subsystem_health),
            "healthy_subsystems": sum(subsystem_health.values()),
        }

    def get_status(self) -> Dict[str, Any]:
        """获取门面状态"""
        return {
            "name": self.name,
            "description": self.description,
            "initialized": self.initialized,
            "subsystems": self.subsystem_manager.get_all_status(),
            "metrics": self.metrics.copy(),
        }

    async def _execute_with_metrics(self, operation_name: str, operation):
        """执行操作并记录指标"""
        start_time = datetime.utcnow()
        self.metrics["requests_count"] += 1

        try:
            _result = await operation()

            # 记录成功指标
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_response_time_metrics(execution_time)

            logger.debug(
                f"Operation {operation_name} completed in {execution_time:.3f}s"
            )
            return result

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            # 记录错误指标
            self.metrics["errors_count"] += 1
            logger.error(f"Operation {operation_name} failed: {e}")
            raise

    def _update_response_time_metrics(self, execution_time: float) -> None:
        """更新响应时间指标"""
        self.metrics["total_response_time"] += execution_time
        self.metrics["last_request_time"] = datetime.utcnow().isoformat()

        # 计算平均响应时间
        if self.metrics["requests_count"] > 0:
            self.metrics["average_response_time"] = (
                self.metrics["total_response_time"] / self.metrics["requests_count"]
            )

    def reset_metrics(self) -> None:
        """重置指标"""
        self.metrics = {
            "requests_count": 0,
            "errors_count": 0,
            "average_response_time": 0.0,
            "total_response_time": 0.0,
            "last_request_time": None,
        }

    @abstractmethod
    async def execute(self, operation: str, **kwargs) -> Any:
        """执行门面操作"""
        pass
