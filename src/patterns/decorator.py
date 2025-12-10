"""装饰器模式模块
Decorator Pattern Module.

提供装饰器模式的实现，允许动态地添加对象的功能.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any


class Component(ABC):
    """组件抽象基类.

    定义装饰器和具体组件的共同接口.
    """

    @abstractmethod
    def operation(self) -> str:
        """执行操作."""


class ConcreteComponent(Component):
    """具体组件类.

    实现基础功能.
    """

    def __init__(self, name: str = "ConcreteComponent"):
        """初始化具体组件.

        Args:
            name: 组件名称
        """
        self.name = name

    def operation(self) -> str:
        """执行基础操作."""
        return f"{self.name}: 基础操作"


class Decorator(Component):
    """装饰器抽象基类.

    实现装饰器的通用功能.
    """

    def __init__(self, component: Component):
        """初始化装饰器.

        Args:
            component: 要装饰的组件
        """
        self._component = component

    @property
    def component(self) -> Component:
        """获取被装饰的组件."""
        return self._component

    def operation(self) -> str:
        """执行操作，委托给组件."""
        return self._component.operation()


class ConcreteDecoratorA(Decorator):
    """具体装饰器A.

    添加状态并修改操作行为.
    """

    def __init__(self, component: Component, added_state: str = "装饰器A"):
        """初始化具体装饰器A.

        Args:
            component: 要装饰的组件
            added_state: 添加的状态
        """
        super().__init__(component)
        self.added_state = added_state

    def operation(self) -> str:
        """执行装饰后的操作."""
        result = super().operation()
        return f"{result} + {self.added_state}"


class ConcreteDecoratorB(Decorator):
    """具体装饰器B.

    添加新的行为.
    """

    def __init__(self, component: Component):
        """初始化具体装饰器B.

        Args:
            component: 要装饰的组件
        """
        super().__init__(component)

    def operation(self) -> str:
        """执行装饰后的操作."""
        result = super().operation()
        return f"{result} + 装饰器B增强"

    def added_behavior(self) -> str:
        """新增的行为."""
        return "装饰器B的额外功能"


# 函数装饰器实现
def timing_decorator(func: Callable) -> Callable:
    """计时装饰器.

    测量函数执行时间.

    Args:
        func: 要装饰的函数

    Returns:
        Callable: 装饰后的函数
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        end_time - start_time

        return result

    return wrapper


def logging_decorator(log_level: str = "INFO") -> Callable:
    """日志装饰器.

    记录函数调用信息.

    Args:
        log_level: 日志级别

    Returns:
        Callable: 装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                raise

        return wrapper

    return decorator


def cache_decorator(max_size: int = 128) -> Callable:
    """缓存装饰器.

    缓存函数结果.

    Args:
        max_size: 最大缓存大小

    Returns:
        Callable: 装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        cache: dict[str, Any] = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 创建缓存键
            cache_key = f"{func.__name__}:{args}:{frozenset(kwargs.items())}"

            # 检查缓存
            if cache_key in cache:
                return cache[cache_key]

            # 缓存未命中，执行函数
            result = func(*args, **kwargs)

            # 缓存结果（简单的LRU实现）
            if len(cache) >= max_size:
                # 删除最旧的条目
                oldest_key = next(iter(cache))
                del cache[oldest_key]

            cache[cache_key] = result
            return result

        # 添加缓存管理方法
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_info = lambda: {"size": len(cache), "max_size": max_size}

        return wrapper

    return decorator


def retry_decorator(max_attempts: int = 3, delay: float = 1.0) -> Callable:
    """重试装饰器.

    在函数失败时自动重试.

    Args:
        max_attempts: 最大重试次数
        delay: 重试间隔（秒）

    Returns:
        Callable: 装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
                    else:
                        pass

            raise last_exception

        return wrapper

    return decorator


class DecoratorChain:
    """装饰器链管理器.

    管理多个装饰器的应用顺序.
    """

    def __init__(self):
        """初始化装饰器链."""
        self.decorators: list[Callable] = []

    def add_decorator(self, decorator: Callable) -> "DecoratorChain":
        """添加装饰器到链中.

        Args:
            decorator: 要添加的装饰器

        Returns:
            DecoratorChain: 返回自身以支持链式调用
        """
        self.decorators.append(decorator)
        return self

    def apply_to(self, func: Callable) -> Callable:
        """将装饰器链应用到函数.

        Args:
            func: 要装饰的函数

        Returns:
            Callable: 装饰后的函数
        """
        result = func
        for decorator in reversed(self.decorators):
            result = decorator(result)
        return result

    def clear(self) -> "DecoratorChain":
        """清除装饰器链.

        Returns:
            DecoratorChain: 返回自身以支持链式调用
        """
        self.decorators.clear()
        return self

    def count(self) -> int:
        """获取装饰器数量.

        Returns:
            int: 装饰器数量
        """
        return len(self.decorators)


# 使用示例和演示函数
@timing_decorator
@logging_decorator("DEBUG")
@cache_decorator(max_size=64)
def example_function(x: int, y: int) -> int:
    """示例函数，用于演示装饰器."""
    time.sleep(0.1)  # 模拟计算时间
    return x + y


@retry_decorator(max_attempts=3, delay=0.5)
def unstable_function(should_fail: bool = False) -> str:
    """不稳定的函数，用于演示重试装饰器."""
    if should_fail:
        raise ValueError("函数执行失败")
    return "成功"


# 便捷函数
def create_component_chain(
    base_component: Component, decorators: list[typing.Type]
) -> Component:
    """创建组件装饰链.

    Args:
        base_component: 基础组件
        decorators: 装饰器类列表

    Returns:
        Component: 装饰后的组件
    """
    result = base_component
    for decorator_class in decorators:
        result = decorator_class(result)
    return result


def demonstrate_decorator_pattern():
    """演示装饰器模式的使用."""
    # 创建基础组件
    component = ConcreteComponent("数据处理组件")

    # 添加装饰器A
    decorated_a = ConcreteDecoratorA(component, "数据验证")

    # 添加装饰器B
    decorated_ab = ConcreteDecoratorB(decorated_a)

    # 调用装饰器的额外行为
    if isinstance(decorated_ab, ConcreteDecoratorB):
        pass

    # 演示函数装饰器
    example_function(5, 3)

    # 缓存命中
    example_function(5, 3)

    try:
        unstable_function(False)
    except Exception:
        pass

    try:
        unstable_function(True)
    except Exception:
        pass


# 企业级装饰器实现
class BaseDecorator(Decorator):
    """基础装饰器类.

    提供装饰器的基础实现.
    """

    def __init__(self, component: Component):
        """初始化基础装饰器.

        Args:
            component: 要装饰的组件
        """
        super().__init__(component)

    def operation(self) -> str:
        """执行装饰后的操作."""
        return self._component.operation()


class LoggingDecorator(BaseDecorator):
    """日志装饰器.

    为组件添加日志功能.
    """

    def __init__(self, component: Component, log_level: str = "INFO"):
        """初始化日志装饰器.

        Args:
            component: 要装饰的组件
            log_level: 日志级别
        """
        super().__init__(component)
        self.log_level = log_level

    def operation(self) -> str:
        """执行带日志的操作."""
        result = self._component.operation()
        return result


class MetricsDecorator(BaseDecorator):
    """指标装饰器.

    为组件添加性能监控功能.
    """

    def __init__(self, component: Component):
        """初始化指标装饰器.

        Args:
            component: 要装饰的组件
        """
        super().__init__(component)
        self.call_count = 0
        self.total_time = 0.0

    def operation(self) -> str:
        """执行带指标收集的操作."""
        start_time = time.time()
        self.call_count += 1

        result = self._component.operation()

        duration = time.time() - start_time
        self.total_time += duration

        return result

    def get_metrics(self) -> dict[str, Any]:
        """获取性能指标."""
        return {
            "call_count": self.call_count,
            "total_time": self.total_time,
            "avg_time": (
                self.total_time / self.call_count if self.call_count > 0 else 0.0
            ),
        }


class RetryDecorator(BaseDecorator):
    """重试装饰器.

    为组件添加重试功能.
    """

    def __init__(self, component: Component, max_retries: int = 3, delay: float = 1.0):
        """初始化重试装饰器.

        Args:
            component: 要装饰的组件
            max_retries: 最大重试次数
            delay: 重试延迟（秒）
        """
        super().__init__(component)
        self.max_retries = max_retries
        self.delay = delay

    def operation(self) -> str:
        """执行带重试的操作."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                result = self._component.operation()
                if attempt > 0:
                    pass
                return result
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(self.delay)
                else:
                    pass

        raise last_exception


class ValidationDecorator(BaseDecorator):
    """验证装饰器.

    为组件添加输入验证功能.
    """

    def __init__(self, component: Component, validator: Callable | None = None):
        """初始化验证装饰器.

        Args:
            component: 要装饰的组件
            validator: 验证函数
        """
        super().__init__(component)
        self.validator = validator or self._default_validator

    def _default_validator(self, *args, **kwargs):
        """默认验证器."""
        return True

    def operation(self) -> str:
        """执行带验证的操作."""
        if self.validator():
            result = self._component.operation()
            return result
        else:
            raise ValueError("验证失败")


class CacheDecorator(BaseDecorator):
    """缓存装饰器.

    为组件添加缓存功能.
    """

    def __init__(self, component: Component, cache_size: int = 128):
        """初始化缓存装饰器.

        Args:
            component: 要装饰的组件
            cache_size: 缓存大小
        """
        super().__init__(component)
        self.cache_size = cache_size
        self._cache = {}

    def operation(self) -> str:
        """执行带缓存的操作."""
        cache_key = str(id(self._component))

        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self._component.operation()

        # 如果缓存满了，移除最旧的条目
        if len(self._cache) >= self.cache_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[cache_key] = result
        return result

    def clear_cache(self):
        """清空缓存."""
        self._cache.clear()

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计."""
        return {
            "cache_size": len(self._cache),
            "max_size": self.cache_size,
            "hit_rate": 0.0,
            # 简化实现
        }


# 异步装饰器
def async_log(log_level: str = "INFO"):
    """异步日志装饰器."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                raise

        return wrapper

    return decorator


def async_metrics(func):
    """异步指标装饰器."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            time.time() - start_time
            return result
        except Exception:
            time.time() - start_time
            raise

    return wrapper


def async_retry(max_retries: int = 3, delay: float = 1.0):
    """异步重试装饰器."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        pass
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(delay)
                    else:
                        pass

            raise last_exception

        return wrapper

    return decorator


def create_decorated_service(service_name: str) -> Component:
    """创建装饰后的服务.

    Args:
        service_name: 服务名称

    Returns:
        Component: 装饰后的服务组件
    """
    base_service = ConcreteComponent(service_name)

    # 添加装饰器
    logged_service = LoggingDecorator(base_service, "INFO")
    metrics_service = MetricsDecorator(logged_service)
    cached_service = CacheDecorator(metrics_service, cache_size=64)

    return cached_service


# 导出的公共接口
__all__ = [
    "Component",
    "ConcreteComponent",
    "BaseDecorator",
    "Decorator",
    "LoggingDecorator",
    "MetricsDecorator",
    "RetryDecorator",
    "ValidationDecorator",
    "CacheDecorator",
    "ConcreteDecoratorA",
    "ConcreteDecoratorB",
    "timing_decorator",
    "logging_decorator",
    "cache_decorator",
    "retry_decorator",
    "async_log",
    "async_metrics",
    "async_retry",
    "DecoratorChain",
    "example_function",
    "unstable_function",
    "create_component_chain",
    "demonstrate_decorator_pattern",
    "create_decorated_service",
]
