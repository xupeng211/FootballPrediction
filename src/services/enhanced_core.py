"""
增强的服务核心模块

定义统一的基础服务类和配置。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
import asyncio
import time
import logging

from src.core.logging import get_logger


class ServiceConfig:
    """服务配置类"""

    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        dependencies: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.dependencies = dependencies or []
        self.config = config or {}
        self.created_at = datetime.now()


class ServiceMetrics:
    """服务指标收集器"""

    def __init__(self):
        self.metrics = {
            "calls": 0,
            "errors": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "last_call": None,
        }

    def record_call(self, duration: float, success: bool = True):
        """记录调用"""
        self.metrics["calls"] += 1
        self.metrics["total_time"] += duration
        self.metrics["avg_time"] = self.metrics["total_time"] / self.metrics["calls"]
        self.metrics["last_call"] = datetime.now()
        if not success:
            self.metrics["errors"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics.copy()  # type: ignore


class EnhancedBaseService(ABC):
    """增强的基础服务类

    整合了原有BaseService和AbstractBaseService的功能，
    并添加了指标收集、配置管理、健康检查等功能。
    """

    def __init__(self, config: Optional[ServiceConfig] = None):
        """初始化服务

        Args:
            config: 服务配置
        """
        self.config = config or ServiceConfig(self.__class__.__name__)
        self.name = self.config.name
        self.version = self.config.version
        self.description = self.config.description

        # 日志记录器
        self.logger = get_logger(f"service.{self.name}")

        # 服务状态
        self._running = False
        self._initialized = False
        self._startup_time: Optional[datetime] = None

        # 指标收集
        self.metrics = ServiceMetrics()
        self._health_status: Any = {
            "status": "unknown",
            "message": "Service not initialized",
            "last_check": None,
            "details": {},
        }

        # 依赖管理
        self._dependencies: Dict[str, "EnhancedBaseService"] = {}

    @abstractmethod
    async def initialize(self) -> None:
        """初始化服务 - 子类必须实现"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """关闭服务 - 子类必须实现"""
        pass

    async def start(self) -> bool:
        """启动服务"""
        if self._running:
            self.logger.warning(f"Service {self.name} is already running")
            return True

        try:
            await self.initialize()
            self._running = True
            self._startup_time = datetime.now()
            self._update_health_status("healthy", "Service started successfully")
            self.logger.info(f"Service {self.name} started successfully")
            return True
        except Exception as e:
            self._update_health_status("unhealthy", f"Failed to start: {str(e)}")
            self.logger.error(f"Failed to start service {self.name}: {e}")
            return False

    async def stop(self) -> bool:
        """停止服务"""
        if not self._running:
            self.logger.warning(f"Service {self.name} is not running")
            return True

        try:
            await self.shutdown()
            self._running = False
            self._initialized = False
            self._update_health_status("stopped", "Service stopped successfully")
            self.logger.info(f"Service {self.name} stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop service {self.name}: {e}")
            return False

    def get_status(self) -> str:
        """获取服务状态"""
        if not self._initialized:
            return "not_initialized"
        return "running" if self._running else "stopped"

    def is_healthy(self) -> bool:
        """检查服务是否健康"""
        return self._health_status["status"] == "healthy"  # type: ignore

    def get_health_info(self) -> Dict[str, Any]:
        """获取健康信息"""
        health_info = self._health_status.copy()
        health_info.update(
            {
                "service": self.name,
                "version": self.version,
                "status": self.get_status(),
                "uptime_seconds": self._get_uptime_seconds(),
                "metrics": self.metrics.get_metrics(),
                "dependencies": list(self._dependencies.keys()),
            }
        )
        return health_info  # type: ignore

    async def health_check(self) -> Dict[str, Any]:
        """执行健康检查 - 子类可以重写"""
        # 检查依赖
        unhealthy_deps = []
        for name, dep in self._dependencies.items():
            if not dep.is_healthy():
                unhealthy_deps.append(name)

        if unhealthy_deps:
            self._update_health_status(
                "degraded", f"Dependencies unhealthy: {', '.join(unhealthy_deps)}"
            )
        else:
            self._update_health_status("healthy", "All checks passed")

        return self.get_health_info()

    async def execute_with_metrics(
        self, operation_name: str, func: Callable, *args, **kwargs
    ) -> Any:
        """执行函数并收集指标"""
        start_time = time.time()
        success = True

        try:
            self.logger.debug(f"Executing operation: {operation_name}")
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            self.logger.error(f"Operation {operation_name} failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self.metrics.record_call(duration, success)
            self.logger.debug(
                f"Operation {operation_name} completed in {duration:.3f}s"
            )

    def add_dependency(self, name: str, service: "EnhancedBaseService"):
        """添加依赖服务"""
        self._dependencies[name] = service
        self.logger.debug(f"Added dependency: {name}")

    def get_dependency(self, name: str) -> Optional["EnhancedBaseService"]:
        """获取依赖服务"""
        return self._dependencies.get(name)

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.config.get(key, default)

    def _update_health_status(
        self, status: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        """更新健康状态"""
        self._health_status.update(
            {
                "status": status,
                "message": message,
                "last_check": datetime.now(),
                "details": details or {},
            }
        )

    def _get_uptime_seconds(self) -> Optional[float]:
        """获取运行时间（秒）"""
        if self._startup_time:
            return (datetime.now() - self._startup_time).total_seconds()
        return None

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}(name={self.name}, status={self.get_status()})>"
        )


# 为了向后兼容，保留原有的BaseService类
class BaseService(EnhancedBaseService):
    """向后兼容的基础服务类"""

    def __init__(self, name: str = "BaseService"):
        config = ServiceConfig(name=name)
        super().__init__(config)

    async def initialize(self) -> None:
        """默认初始化实现"""
        self._initialized = True

    async def shutdown(self) -> None:
        """默认关闭实现"""
        self._running = False
        self._initialized = False


class AbstractBaseService(EnhancedBaseService):
    """抽象基础服务类 - 强制子类实现所有方法"""

    def __init__(self, name: str):
        config = ServiceConfig(name=name)
        super().__init__(config)


# 导出所有类
__all__ = [
    "ServiceConfig",
    "ServiceMetrics",
    "EnhancedBaseService",
    "BaseService",
    "AbstractBaseService",
]
