"""
适配器模式基类
Adapter Pattern Base Classes

定义适配器模式的核心接口和抽象类。
Define core interfaces and abstract classes for the adapter pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
import asyncio


class AdapterStatus(Enum):
    """适配器状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class Adaptee(ABC):
    """被适配者接口，需要被适配的现有接口"""

    @abstractmethod
    async def get_data(self, *args, **kwargs) -> Any:
        """获取原始数据"""
        pass

    @abstractmethod
    async def send_data(self, data: Any) -> Any:
        """发送数据"""
        pass


class Target(ABC):
    """目标接口，客户端期望的接口"""

    @abstractmethod
    async def request(self, *args, **kwargs) -> Any:
        """标准请求方法"""
        pass


class Adapter(Target):
    """适配器基类，将Adaptee接口转换为Target接口"""

    def __init__(self, adaptee: Adaptee, name: Optional[str] = None):
        self.adaptee = adaptee
        self.name = name or self.__class__.__name__
        self.status = AdapterStatus.INACTIVE
        self.last_error: Optional[str] = None
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "average_response_time": 0.0,
        }

    async def initialize(self) -> None:
        """初始化适配器"""
        try:
            await self._initialize()
            self.status = AdapterStatus.ACTIVE
        except Exception as e:
            self.status = AdapterStatus.ERROR
            self.last_error = str(e)
            raise

    async def cleanup(self) -> None:
        """清理适配器资源"""
        try:
            await self._cleanup()
            self.status = AdapterStatus.INACTIVE
        except Exception as e:
            self.status = AdapterStatus.ERROR
            self.last_error = str(e)
            raise

    @abstractmethod
    async def _initialize(self) -> None:
        """具体的初始化逻辑"""
        pass

    @abstractmethod
    async def _cleanup(self) -> None:
        """具体的清理逻辑"""
        pass

    async def request(self, *args, **kwargs) -> Any:
        """标准请求方法"""
        if self.status != AdapterStatus.ACTIVE:
            raise RuntimeError(f"Adapter {self.name} is not active")

        start_time = datetime.utcnow()
        self.metrics["total_requests"] += 1

        try:
            # 调用具体适配器的实现
            result = await self._request(*args, **kwargs)

            # 更新成功指标
            self.metrics["successful_requests"] += 1
            self.last_error = None

            return result

        except Exception as e:
            # 更新失败指标
            self.metrics["failed_requests"] += 1
            self.last_error = str(e)
            raise

        finally:
            # 更新响应时间
            response_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics["total_response_time"] += response_time
            self.metrics["average_response_time"] = (
                self.metrics["total_response_time"] / self.metrics["total_requests"]
            )

    @abstractmethod
    async def _request(self, *args, **kwargs) -> Any:
        """具体的请求处理逻辑"""
        pass

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 执行简单的健康检查请求
            start_time = datetime.utcnow()
            await self._health_check()
            response_time = (datetime.utcnow() - start_time).total_seconds()

            return {
                "adapter": self.name,
                "status": "healthy",
                "response_time": response_time,
                "metrics": self.get_metrics(),
            }
        except Exception as e:
            return {
                "adapter": self.name,
                "status": "unhealthy",
                "error": str(e),
                "metrics": self.get_metrics(),
            }

    async def _health_check(self) -> None:
        """具体的健康检查逻辑"""
        pass

    def get_metrics(self) -> Dict[str, Any]:
        """获取适配器指标"""
        return {
            "name": self.name,
            "status": self.status.value,
            "last_error": self.last_error,
            "total_requests": self.metrics["total_requests"],
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "success_rate": (
                self.metrics["successful_requests"] / self.metrics["total_requests"]
                if self.metrics["total_requests"] > 0
                else 0
            ),
            "average_response_time": self.metrics["average_response_time"],
        }

    def reset_metrics(self) -> None:
        """重置指标"""
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "average_response_time": 0.0,
        }


class DataTransformer(ABC):
    """数据转换器基类"""

    @abstractmethod
    async def transform(self, data: Any, **kwargs) -> Any:
        """转换数据格式"""
        pass

    @abstractmethod
    def get_source_schema(self) -> Dict[str, Any]:
        """获取源数据结构"""
        pass

    @abstractmethod
    def get_target_schema(self) -> Dict[str, Any]:
        """获取目标数据结构"""
        pass


class BaseAdapter(ABC):
    """基础适配器抽象类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.is_initialized = False

    async def initialize(self) -> None:
        """初始化适配器"""
        if not self.is_initialized:
            await self._setup()
            self.is_initialized = True

    async def cleanup(self) -> None:
        """清理适配器"""
        if self.is_initialized:
            await self._teardown()
            self.is_initialized = False

    @abstractmethod
    async def _setup(self) -> None:
        """设置适配器"""
        pass

    @abstractmethod
    async def _teardown(self) -> None:
        """清理适配器"""
        pass
