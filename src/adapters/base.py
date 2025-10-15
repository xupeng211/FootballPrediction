from typing import Any, Dict, List, Optional, Union

"""
适配器模式基类
Adapter Pattern Base Classes

定义适配器模式的核心接口和抽象类。
Define core interfaces and abstract classes for the adapter pattern.
"""

from abc import ABC, abstractmethod
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
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.status = AdapterStatus.ERROR
            self.last_error = str(e)
            raise

    async def cleanup(self) -> None:
        """清理适配器资源"""
        try:
            await self._cleanup()
            self.status = AdapterStatus.INACTIVE
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
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
            _result = await self._request(*args, **kwargs)

            # 更新成功指标
            self.metrics["successful_requests"] += 1
            self.last_error = None

            return result

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
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
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
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
        }


class CompositeAdapter(Adapter):
    """组合适配器，可以管理多个子适配器"""

    def __init__(self, name: str, adapters: List[Adapter] = None):
        """初始化组合适配器

        Args:
            name: 适配器名称
            adapters: 子适配器列表
        """
        super().__init__(name)
        self.adapters: List[Adapter] = adapters or []
        self.adapter_registry: Dict[str, Adapter] = {}
        self._register_adapters()

    def _register_adapters(self):
        """注册所有子适配器"""
        for adapter in self.adapters:
            self.adapter_registry[adapter.name] = adapter

    def add_adapter(self, adapter: Adapter):
        """添加子适配器

        Args:
            adapter: 要添加的适配器
        """
        self.adapters.append(adapter)
        self.adapter_registry[adapter.name] = adapter

    def remove_adapter(self, adapter_name: str) -> bool:
        """移除子适配器

        Args:
            adapter_name: 适配器名称

        Returns:
            bool: 是否成功移除
        """
        if adapter_name in self.adapter_registry:
            adapter = self.adapter_registry[adapter_name]
            self.adapters.remove(adapter)
            del self.adapter_registry[adapter_name]
            return True
        return False

    def get_adapter(self, adapter_name: str) -> Optional[Adapter]:
        """获取子适配器

        Args:
            adapter_name: 适配器名称

        Returns:
            Adapter: 子适配器，如果不存在则返回None
        """
        return self.adapter_registry.get(adapter_name)

    async def request(self, *args, **kwargs) -> Any:
        """并行请求所有适配器并合并结果

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Any: 合并后的结果
        """
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

    async def _request(self, *args, **kwargs) -> Any:
        """具体的请求处理逻辑（Composite使用并行请求）"""
        return await self.request(*args, **kwargs)

    async def health_check(self) -> Dict[str, Any]:
        """检查所有子适配器的健康状态"""
        health_results = {}

        # 并行检查所有适配器的健康状态
        tasks = [(adapter.name, adapter.health_check()) for adapter in self.adapters]

        if tasks:
            for name, task in tasks:
                try:
                    health_results[name] = await task
                except (
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    RuntimeError,
                ) as e:
                    health_results[name] = {
                        "adapter": name,
                        "status": "unhealthy",
                        "error": str(e),
                    }

        # 计算整体健康状态
        healthy_count = sum(
            1 for result in health_results.values() if result.get("status") == "healthy"
        )

        return {
            "adapter": self.name,
            "status": "healthy" if healthy_count == len(self.adapters) else "degraded",
            "total_adapters": len(self.adapters),
            "healthy_adapters": healthy_count,
            "adapter_health": health_results,
            "metrics": self.get_metrics(),
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
        self._config = config or {}
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
