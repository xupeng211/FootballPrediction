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


class CompositeAdapter(Adapter):
    """复合适配器，组合多个适配器"""

    def __init__(self, name: Optional[str] = None):
        super().__init__(None, name)  # 不需要adaptee
        self.adapters: Dict[str, Adapter] = {}
        self.fallback_order: List[str] = []
        self.load_balancer: Optional[str] = None

    def add_adapter(self, name: str, adapter: Adapter, priority: int = 0) -> None:
        """添加适配器"""
        self.adapters[name] = adapter
        # 按优先级排序
        self.fallback_order = sorted(
            self.fallback_order + [name],
            key=lambda x: getattr(self.adapters[x], "priority", 0),
            reverse=True,
        )

    def remove_adapter(self, name: str) -> None:
        """移除适配器"""
        if name in self.adapters:
            del self.adapters[name]
            self.fallback_order.remove(name)

    async def _initialize(self) -> None:
        """初始化所有适配器"""
        for adapter in self.adapters.values():
            await adapter.initialize()

    async def _cleanup(self) -> None:
        """清理所有适配器"""
        for adapter in self.adapters.values():
            await adapter.cleanup()

    async def _request(self, *args, **kwargs) -> Any:
        """使用第一个可用的适配器处理请求"""
        errors = []

        for adapter_name in self.fallback_order:
            adapter = self.adapters[adapter_name]
            if adapter.status == AdapterStatus.ACTIVE:
                try:
                    return await adapter.request(*args, **kwargs)
                except Exception as e:
                    errors.append(f"{adapter_name}: {str(e)}")
                    continue

        # 所有适配器都失败
        raise RuntimeError(f"All adapters failed. Errors: {'; '.join(errors)}")

    async def _health_check(self) -> None:
        """检查所有适配器的健康状态"""
        for adapter in self.adapters.values():
            await adapter.health_check()

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有适配器的指标"""
        return {
            "composite_adapter": self.name,
            "total_adapters": len(self.adapters),
            "active_adapters": sum(
                1 for a in self.adapters.values() if a.status == AdapterStatus.ACTIVE
            ),
            "adapters": {
                name: adapter.get_metrics() for name, adapter in self.adapters.items()
            },
        }


class AsyncAdapter(Adapter):
    """异步适配器，支持异步操作的适配器"""

    def __init__(
        self,
        adaptee: Adaptee,
        name: Optional[str] = None,
        max_concurrent_requests: int = 10,
        timeout: float = 30.0,
    ):
        super().__init__(adaptee, name)
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.timeout = timeout
        self.request_queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None

    async def _initialize(self) -> None:
        """启动工作队列"""
        self._worker_task = asyncio.create_task(self._worker())

    async def _cleanup(self) -> None:
        """停止工作队列"""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def _worker(self) -> None:
        """工作队列处理器"""
        while True:
            try:
                future, args, kwargs = await self.request_queue.get()
                try:
                    result = await self._process_request(*args, **kwargs)
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
                finally:
                    self.request_queue.task_done()
            except asyncio.CancelledError:
                break

    async def _request(self, *args, **kwargs) -> Any:
        """将请求放入队列"""
        future = asyncio.Future()
        await self.request_queue.put((future, args, kwargs))
        return await asyncio.wait_for(future, timeout=self.timeout)

    async def _process_request(self, *args, **kwargs) -> Any:
        """处理单个请求"""
        async with self.semaphore:
            return await super()._request(*args, **kwargs)


class RetryableAdapter(Adapter):
    """可重试的适配器"""

    def __init__(
        self,
        adaptee: Adaptee,
        name: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ):
        super().__init__(adaptee, name)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor

    async def _request(self, *args, **kwargs) -> Any:
        """带重试的请求"""
        last_exception = None
        current_delay = self.retry_delay

        for attempt in range(1, self.max_retries + 1):
            try:
                return await super()._request(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    break

                await asyncio.sleep(current_delay)
                current_delay *= self.backoff_factor

        raise last_exception


class CachedAdapter(Adapter):
    """带缓存的适配器"""

    def __init__(
        self,
        adaptee: Adaptee,
        name: Optional[str] = None,
        cache_ttl: int = 300,
        cache_size: int = 1000,
    ):
        super().__init__(adaptee, name)
        self.cache_ttl = cache_ttl
        self.cache_size = cache_size
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

    async def _request(self, *args, **kwargs) -> Any:
        """带缓存的请求"""
        cache_key = self._generate_cache_key(*args, **kwargs)

        # 检查缓存
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        # 执行请求
        result = await super()._request(*args, **kwargs)

        # 更新缓存
        self._update_cache(cache_key, result)

        return result

    def _generate_cache_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        import hashlib
        import json

        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items()),
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache:
            return False

        if cache_key not in self._cache_timestamps:
            return False

        age = (datetime.utcnow() - self._cache_timestamps[cache_key]).total_seconds()
        return age < self.cache_ttl

    def _update_cache(self, cache_key: str, data: Any) -> None:
        """更新缓存"""
        # 如果缓存满了，删除最旧的条目
        if len(self._cache) >= self.cache_size:
            oldest_key = min(
                self._cache_timestamps.keys(), key=lambda k: self._cache_timestamps[k]
            )
            del self._cache[oldest_key]
            del self._cache_timestamps[oldest_key]

        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = datetime.utcnow()

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._cache_timestamps.clear()
