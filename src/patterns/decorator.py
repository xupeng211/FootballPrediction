"""
装饰器模式实现

用于功能增强和横切关注点
"""

import asyncio
import time
import functools
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar
from abc import ABC, abstractmethod

from src.core.logging import get_logger

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class Component(ABC):
    """组件抽象基类"""

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """执行组件功能"""
        pass


class BaseDecorator(Component):
    """装饰器基类"""

    def __init__(self, component: Component):
        self._component = component
        self.logger = get_logger(f"decorator.{self.__class__.__name__}")

    async def execute(self, *args, **kwargs) -> Any:
        """执行装饰后的功能"""
        return await self._component.execute(*args, **kwargs)


class LoggingDecorator(BaseDecorator):
    """日志装饰器"""

    def __init__(self, component: Component, log_level: int = logging.INFO):
        super().__init__(component)
        self.log_level = log_level

    async def execute(self, *args, **kwargs) -> Any:
        """添加日志记录"""
        start_time = time.time()

        self.logger.log(
            self.log_level, f"Starting execution: {self._component.__class__.__name__}"
        )

        try:
            result = await self._component.execute(*args, **kwargs)
            duration = time.time() - start_time

            self.logger.log(
                self.log_level,
                f"Completed execution: {self._component.__class__.__name__} "
                f"in {duration:.3f}s",
            )

            return result

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Failed execution: {self._component.__class__.__name__} "
                f"in {duration:.3f}s | Error: {str(e)}"
            )
            raise


class RetryDecorator(BaseDecorator):
    """重试装饰器"""

    def __init__(
        self,
        component: Component,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: Optional[List[Exception]] = None,
    ):
        super().__init__(component)
        self.max_retries = max_retries
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions or [Exception]  # type: ignore

    async def execute(self, *args, **kwargs) -> Any:
        """添加重试机制"""
        last_exception = None
        current_delay = self.delay

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.warning(
                        f"Retry attempt {attempt}/{self.max_retries} "
                        f"for {self._component.__class__.__name__}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= self.backoff_factor

                return await self._component.execute(*args, **kwargs)

            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                last_exception = e

                if not any(isinstance(e, exc) for exc in self.exceptions):  # type: ignore
                    raise

                if attempt < self.max_retries:
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed for "
                        f"{self._component.__class__.__name__}: {str(e)}"
                    )
                else:
                    self.logger.error(
                        f"All {self.max_retries + 1} attempts failed for "
                        f"{self._component.__class__.__name__}"
                    )

        raise last_exception  # type: ignore


class MetricsDecorator(BaseDecorator):
    """指标收集装饰器"""

    def __init__(self, component: Component, metrics_name: Optional[str] = None):
        super().__init__(component)
        self.metrics_name = metrics_name or component.__class__.__name__
        self.metrics = {
            "calls": 0,
            "errors": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "min_time": float("inf"),
            "max_time": 0.0,
        }

    async def execute(self, *args, **kwargs) -> Any:
        """收集执行指标"""
        start_time = time.time()
        success = True

        try:
            self.metrics["calls"] += 1
            result = await self._component.execute(*args, **kwargs)
            return result

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
            success = False
            self.metrics["errors"] += 1
            raise

        finally:
            duration = time.time() - start_time
            self._update_metrics(duration, success)

    def _update_metrics(self, duration: float, success: bool) -> None:
        """更新指标数据"""
        self.metrics["total_time"] += duration
        self.metrics["avg_time"] = self.metrics["total_time"] / self.metrics["calls"]
        self.metrics["min_time"] = min(self.metrics["min_time"], duration)
        self.metrics["max_time"] = max(self.metrics["max_time"], duration)

        self.logger.debug(
            f"Metrics updated for {self.metrics_name}: "
            f"duration={duration:.3f}s, success={success}"
        )

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标数据"""
        metrics = self.metrics.copy()
        metrics["success_rate"] = (
            (metrics["calls"] - metrics["errors"]) / metrics["calls"] * 100
            if metrics["calls"] > 0
            else 0
        )
        return metrics


class ValidationDecorator(BaseDecorator):
    """验证装饰器"""

    def __init__(
        self,
        component: Component,
        validators: Optional[List[Callable]] = None,
        validate_result: Optional[Callable] = None,
    ):
        super().__init__(component)
        self.validators = validators or []
        self.validate_result = validate_result

    async def execute(self, *args, **kwargs) -> Any:
        """添加输入输出验证"""
        # 验证输入
        for validator in self.validators:
            try:
                validator(*args, **kwargs)
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                self.logger.error(
                    f"Input validation failed for {self._component.__class__.__name__}: {str(e)}"
                )
                raise ValueError(f"Invalid input: {str(e)}")

        # 执行组件
        result = await self._component.execute(*args, **kwargs)

        # 验证输出
        if self.validate_result:
            try:
                self.validate_result(result)
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                self.logger.error(
                    f"Result validation failed for {self._component.__class__.__name__}: {str(e)}"
                )
                raise ValueError(f"Invalid result: {str(e)}")

        return result


class CacheDecorator(BaseDecorator):
    """缓存装饰器"""

    def __init__(
        self,
        component: Component,
        cache_store: Optional[Dict[str, Any]] = None,
        ttl: Optional[float] = None,
    ):
        super().__init__(component)
        self.cache = cache_store or {}
        self.ttl = ttl
        self.timestamps = {}  # type: ignore

    def _get_cache_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [self._component.__class__.__name__]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return "|".join(key_parts)

    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self.timestamps:
            return False

        if self.ttl is None:
            return True

        age = time.time() - self.timestamps[key]
        return age < self.ttl  # type: ignore

    async def execute(self, *args, **kwargs) -> Any:
        """添加缓存功能"""
        cache_key = self._get_cache_key(*args, **kwargs)

        # 检查缓存
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            self.logger.debug(f"Cache hit for {cache_key}")
            return self.cache[cache_key]

        # 缓存未命中，执行组件
        self.logger.debug(f"Cache miss for {cache_key}")
        result = await self._component.execute(*args, **kwargs)

        # 存储到缓存
        self.cache[cache_key] = result
        self.timestamps[cache_key] = time.time()

        return result


# 函数式装饰器
def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Optional[List[Exception]] = None,
):
    """异步重试装饰器"""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            logger = get_logger(f"retry.{func.__name__}")

            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor

                    return await func(*args, **kwargs)

                except (
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    RuntimeError,
                ) as e:
                    last_exception = e

                    if exceptions and not any(isinstance(e, exc) for exc in exceptions):
                        raise

                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")

            raise last_exception

        return wrapper  # type: ignore

    return decorator


def async_log(log_level: int = logging.INFO):
    """异步日志装饰器"""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(f"func.{func.__name__}")
            start_time = time.time()

            logger.log(log_level, f"Starting {func.__name__}")

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log(log_level, f"Completed {func.__name__} in {duration:.3f}s")
                return result

            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                duration = time.time() - start_time
                logger.error(f"Failed {func.__name__} in {duration:.3f}s: {str(e)}")
                raise

        return wrapper  # type: ignore

    return decorator


def async_metrics(metrics_store: Optional[Dict[str, Dict]] = None):
    """异步指标装饰器"""
    if metrics_store is None:
        metrics_store = {}

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = func.__name__

            # 初始化指标
            if func_name not in metrics_store:
                metrics_store[func_name] = {
                    "calls": 0,
                    "errors": 0,
                    "total_time": 0.0,
                    "avg_time": 0.0,
                }

            metrics = metrics_store[func_name]
            start_time = time.time()

            try:
                metrics["calls"] += 1
                result = await func(*args, **kwargs)
                return result

            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
                metrics["errors"] += 1
                raise

            finally:
                duration = time.time() - start_time
                metrics["total_time"] += duration
                metrics["avg_time"] = metrics["total_time"] / metrics["calls"]

        return wrapper  # type: ignore

    return decorator


# 示例使用
class DatabaseService(Component):
    """数据库服务示例"""

    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"service.{name}")

    async def execute(self, query: str) -> Dict[str, Any]:
        """执行数据库查询"""
        self.logger.info(f"Executing query: {query}")

        # 模拟数据库操作
        await asyncio.sleep(0.1)

        # 模拟偶尔失败
        if "error" in query.lower():
            raise Exception("Database error")

        return {"query": query, "result": "success", "rows": 10}


def create_decorated_service(service_name: str) -> Component:
    """创建装饰后的服务"""
    base_service = DatabaseService(service_name)

    # 添加装饰器链
    service = LoggingDecorator(base_service)
    service = MetricsDecorator(service)  # type: ignore
    service = RetryDecorator(service, max_retries=2)  # type: ignore
    service = ValidationDecorator(  # type: ignore
        service,
        validators=[lambda q: isinstance(q, str) and len(q) > 0],
        validate_result=lambda r: isinstance(r, dict) and "result" in r,
    )

    return service
