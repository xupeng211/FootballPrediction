from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

"""
外观模式基类模块
Facade Base Module

提供外观模式的核心抽象基类和状态管理.
"""


class SubsystemStatus(Enum):
    """子系统状态枚举"""

    ACTIVE = "active"  # 活跃状态
    INACTIVE = "inactive"  # 非活跃状态
    STARTING = "starting"  # 启动中
    STOPPING = "stopping"  # 停止中
    ERROR = "error"  # 错误状态
    MAINTENANCE = "maintenance"  # 维护状态


class Subsystem(ABC):
    """子系统抽象基类

    为所有子系统提供统一的接口和生命周期管理.
    """

    def __init__(self, name: str, config: dict[str, Any] | None = None):
        """初始化子系统

        Args:
            name: 子系统名称
            config: 配置参数
        """
        self.name = name
        self.config = config or {}
        self.status = SubsystemStatus.INACTIVE
        self.created_at = datetime.utcnow()
        self.last_health_check = None
        self.error_message: str | None = None
        self.metrics: dict[str, Any] = {}

    @abstractmethod
    async def start(self) -> bool:
        """启动子系统"""

    @abstractmethod
    async def stop(self) -> bool:
        """停止子系统"""

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""

    def get_status_info(self) -> dict[str, Any]:
        """获取状态信息"""
        return {
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_health_check": (
                self.last_health_check.isoformat() if self.last_health_check else None
            ),
            "error_message": self.error_message,
            "metrics": self.metrics.copy(),
            "config": self.config.copy(),
        }

    def set_error(self, error_message: str) -> None:
        """设置错误状态"""
        self.status = SubsystemStatus.ERROR
        self.error_message = error_message


class Facade:
    """外观基类

    为复杂的子系统集合提供简化的接口.
    """

    def __init__(self, name: str):
        """初始化外观"""
        self.name = name
        self.subsystems: dict[str, Subsystem] = {}
        self.created_at = datetime.utcnow()

    def register_subsystem(self, subsystem: Subsystem) -> None:
        """注册子系统"""
        self.subsystems[subsystem.name] = subsystem

    def get_subsystem(self, name: str) -> Subsystem | None:
        """获取子系统"""
        return self.subsystems.get(name)

    def get_overall_status(self) -> dict[str, Any]:
        """获取整体状态"""
        subsystems_status = {
            name: subsystem.get_status_info()
            for name, subsystem in self.subsystems.items()
        }

        active_count = sum(
            1 for status in subsystems_status.values() if status["status"] == "active"
        )

        return {
            "facade_name": self.name,
            "total_subsystems": len(self.subsystems),
            "active_subsystems": active_count,
            "created_at": self.created_at.isoformat(),
            "subsystems": subsystems_status,
        }

    def set_error(self, error_message: str) -> None:
        """设置错误状态"""
        for subsystem in self.subsystems.values():
            subsystem.set_error(error_message)


class SubsystemManager:
    """子系统管理器"""

    def __init__(self):
        self.subsystems: dict[str, Subsystem] = {}
        self.facades: dict[str, Facade] = {}

    def register_subsystem(self, subsystem: Subsystem) -> None:
        """注册子系统"""
        self.subsystems[subsystem.name] = subsystem

    def register_facade(self, facade: Facade) -> None:
        """注册外观"""
        self.facades[facade.name] = facade

    def get_subsystem(self, name: str) -> Subsystem | None:
        """获取子系统"""
        return self.subsystems.get(name)


class SystemFacade(Facade):
    """系统外观"""

    def __init__(self, name: str = "System", config: dict[str, Any] | None = None):
        super().__init__(name)
        self.config = config or {}
        self.initialized = False

    async def start_all(self) -> dict[str, bool]:
        """启动所有子系统"""
        results = {}
        for name, subsystem in self.subsystems.items():
            try:
                result = await subsystem.start()
                results[name] = result
            except Exception as e:
                results[name] = False
                subsystem.set_error(str(e))
        return results

    async def stop_all(self) -> dict[str, bool]:
        """停止所有子系统"""
        results = {}
        for name, subsystem in self.subsystems.items():
            try:
                result = await subsystem.stop()
                results[name] = result
            except Exception as e:
                results[name] = False
                subsystem.set_error(str(e))
        return results

    async def health_check_all(self) -> dict[str, bool]:
        """检查所有子系统健康状态"""
        results = {}
        for name, subsystem in self.subsystems.items():
            try:
                result = await subsystem.health_check()
                results[name] = result
            except Exception as e:
                results[name] = False
                subsystem.set_error(str(e))
        return results


__all__ = ["SubsystemStatus", "Subsystem", "Facade", "SubsystemManager", "SystemFacade"]
