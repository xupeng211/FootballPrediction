"""
适配器模式基类
Adapter Pattern Base Classes

定义适配器模式的核心接口和抽象类。
Define core interfaces and abstract classes for the adapter pattern.
"""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


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
    pass


class BaseAdapter(ABC):
    """基础适配器抽象类"""
    pass


class DataTransformer(ABC):
    """数据转换器基类"""

    @abstractmethod
    async def transform(self, data: Any, **kwargs) -> Any:
        """转换数据格式"""
        pass

    def get_source_schema(self) -> Dict[str, Any]:
        """获取源数据结构"""
        return {}

    @abstractmethod
    def get_target_schema(self) -> Dict[str, Any]:
        """获取目标数据结构"""
        pass


class CompositeAdapter(Adapter):
    """组合适配器，可以管理多个子适配器"""

    def __init__(self, name: str = "CompositeAdapter"):
        self.name = name
        self.adapters: List[Adapter] = []
        self.adapter_registry: Dict[str, Adapter] = {}
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "average_response_time": 0.0,
        }
        self.status = AdapterStatus.ACTIVE
        self.last_error = None

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
        }

    def add_adapter(self, adapter: Adapter) -> None:
        """添加子适配器"""
        self.adapters.append(adapter)
        self.adapter_registry[adapter.name] = adapter

    def remove_adapter(self, adapter_name: str) -> bool:
        """移除子适配器"""
        if adapter_name in self.adapter_registry:
            adapter = self.adapter_registry[adapter_name]
            self.adapters.remove(adapter)
            del self.adapter_registry[adapter_name]
            return True
        return False

    def get_adapter(self, adapter_name: str) -> Optional[Adapter]:
        """获取子适配器"""
        return self.adapter_registry.get(adapter_name)

    async def request(self, *args, **kwargs) -> Any:
        """并行请求所有适配器并合并结果"""
        results = []

        # 并行请求所有适配器
        tasks = [adapter.request(*args, **kwargs) for adapter in self.adapters]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤异常结果
        successful_results = [
            result for result in results if not isinstance(result, Exception)
        ]

        return {
            "adapter_name": self.name,
            "results": successful_results,
            "total_adapters": len(self.adapters),
            "successful_adapters": len(successful_results),
        }
