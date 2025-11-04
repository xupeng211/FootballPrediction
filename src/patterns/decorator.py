"""
装饰器模式模块
Decorator Pattern Module

提供装饰器模式的实现，允许动态地添加对象的功能.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any


class Component(ABC):
    """组件抽象基类

    定义装饰器和具体组件的共同接口.
    """

    @abstractmethod
    def operation(self) -> str:
        """执行操作"""


class ConcreteComponent(Component):
    """具体组件类

    实现基础功能.
    """

    def __init__(self, name: str = "ConcreteComponent"):
        """初始化具体组件

        Args:
            name: 组件名称
        """
        self.name = name

    def operation(self) -> str:
        """执行基础操作"""
        return f"{self.name}: 基础操作"


class Decorator(Component):
    """装饰器抽象基类

    实现装饰器的通用功能.
    """

    def __init__(self, component: Component):
        """初始化装饰器

        Args:
            component: 要装饰的组件
        """
        self._component = component

    @property
    def component(self) -> Component:
        """获取被装饰的组件"""
        return self._component

    def operation(self) -> str:
        """执行操作，委托给组件"""
        return self._component.operation()


class ConcreteDecoratorA(Decorator):
    """具体装饰器A

    添加状态并修改操作行为.
    """

    def __init__(self, component: Component, added_state: str = "装饰器A"):
        """初始化具体装饰器A

        Args:
            component: 要装饰的组件
            added_state: 添加的状态
        """
        super().__init__(component)
        self.added_state = added_state

    def operation(self) -> str:
        """执行装饰后的操作"""
        result = super().operation()
        return f"{result} + {self.added_state}"


class ConcreteDecoratorB(Decorator):
    """具体装饰器B

    添加新的行为.
    """

    def __init__(self, component: Component):
        """初始化具体装饰器B

        Args:
            component: 要装饰的组件
        """
        super().__init__(component)

    def operation(self) -> str:
        """执行装饰后的操作"""
        result = super().operation()
        return f"{result} + 装饰器B增强"

    def added_behavior(self) -> str:
        """新增的行为"""
        return "装饰器B的额外功能"


# 函数装饰器实现
def timing_decorator(func: Callable) -> Callable:
    """计时装饰器

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
        execution_time = end_time - start_time

        print(f"函数 {func.__name__} 执行时间: {execution_time:.4f} 秒")
        return result

    return wrapper


def logging_decorator(log_level: str = "INFO") -> Callable:
    """日志装饰器

    记录函数调用信息.

    Args:
        log_level: 日志级别

    Returns:
        Callable: 装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"[{log_level}] 调用函数: {func.__name__}")
            print(f"[{log_level}] 参数: args={args}, kwargs={kwargs}")

            try:
                result = func(*args, **kwargs)
                print(f"[{log_level}] 函数 {func.__name__} 执行成功")
                return result
            except Exception as e:
                print(f"[{log_level}] 函数 {func.__name__} 执行失败: {str(e)}")
                raise

        return wrapper

    return decorator


def cache_decorator(max_size: int = 128) -> Callable:
    """缓存装饰器

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
                print(f"缓存命中: {func.__name__}")
                return cache[cache_key]

            # 缓存未命中，执行函数
            print(f"缓存未命中: {func.__name__}")
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
        wrapper.cache_info = lambda: {"size": len(cache),
    "max_size": max_size}

        return wrapper

    return decorator


def retry_decorator(max_attempts: int = 3,
    delay: float = 1.0) -> Callable:
    """重试装饰器

    在函数失败时自动重试.

    Args:
        max_attempts: 最大重试次数
        delay: 重试间隔（秒）

    Returns:
        Callable: 装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args,
    **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args,
    **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        print(f"尝试 {attempt + 1}/{max_attempts} 失败: {str(e)}")
                        print(f"等待 {delay} 秒后重试...")
                        time.sleep(delay)
                    else:
                        print(f"所有 {max_attempts} 次尝试都失败了")

            raise last_exception

        return wrapper

    return decorator


class DecoratorChain:
    """装饰器链管理器

    管理多个装饰器的应用顺序.
    """

    def __init__(self):
        """初始化装饰器链"""
        self.decorators: list[Callable] = []

    def add_decorator(self, decorator: Callable) -> "DecoratorChain":
        """添加装饰器到链中

        Args:
            decorator: 要添加的装饰器

        Returns:
            DecoratorChain: 返回自身以支持链式调用
        """
        self.decorators.append(decorator)
        return self

    def apply_to(self, func: Callable) -> Callable:
        """将装饰器链应用到函数

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
        """清除装饰器链

        Returns:
            DecoratorChain: 返回自身以支持链式调用
        """
        self.decorators.clear()
        return self

    def count(self) -> int:
        """获取装饰器数量

        Returns:
            int: 装饰器数量
        """
        return len(self.decorators)


# 使用示例和演示函数
@timing_decorator
@logging_decorator("DEBUG")
@cache_decorator(max_size=64)
def example_function(x: int, y: int) -> int:
    """示例函数，用于演示装饰器"""
    print(f"执行计算: {x} + {y}")
    time.sleep(0.1)  # 模拟计算时间
    return x + y


@retry_decorator(max_attempts=3, delay=0.5)
def unstable_function(should_fail: bool = False) -> str:
    """不稳定的函数，用于演示重试装饰器"""
    if should_fail:
        raise ValueError("函数执行失败")
    return "成功"


# 便捷函数
def create_component_chain(
    base_component: Component, decorators: list[type]
) -> Component:
    """创建组件装饰链

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
    """演示装饰器模式的使用"""
    print("=== 装饰器模式演示 ===")

    # 创建基础组件
    component = ConcreteComponent("数据处理组件")
    print(f"基础操作: {component.operation()}")

    # 添加装饰器A
    decorated_a = ConcreteDecoratorA(component, "数据验证")
    print(f"装饰A后: {decorated_a.operation()}")

    # 添加装饰器B
    decorated_ab = ConcreteDecoratorB(decorated_a)
    print(f"装饰A+B后: {decorated_ab.operation()}")

    # 调用装饰器的额外行为
    if isinstance(decorated_ab, ConcreteDecoratorB):
        print(f"额外行为: {decorated_ab.added_behavior()}")

    print("\n=== 函数装饰器演示 ===")
    # 演示函数装饰器
    result1 = example_function(5, 3)
    print(f"结果: {result1}")

    # 缓存命中
    result2 = example_function(5, 3)
    print(f"结果: {result2}")

    print("\n=== 重试装饰器演示 ===")
    try:
        unstable_function(False)
        print("稳定调用成功")
    except Exception as e:
        print(f"稳定调用失败: {e}")

    try:
        unstable_function(True)
        print("不稳定调用成功")
    except Exception as e:
        print(f"不稳定调用失败: {e}")


# 企业级装饰器实现
class BaseDecorator(Decorator):
    """基础装饰器类

    提供装饰器的基础实现.
    """

    def __init__(self, component: Component):
        """初始化基础装饰器

        Args:
            component: 要装饰的组件
        """
        super().__init__(component)

    def operation(self) -> str:
        """执行装饰后的操作"""
        return self._component.operation()


class LoggingDecorator(BaseDecorator):
    """日志装饰器

    为组件添加日志功能.
    """

    def __init__(self, component: Component, log_level: str = "INFO"):
        """初始化日志装饰器

        Args:
            component: 要装饰的组件
            log_level: 日志级别
        """
        super().__init__(component)
        self.log_level = log_level

    def operation(self) -> str:
        """执行带日志的操作"""
        print(f"[{self.log_level}] 开始执行操作")
        result = self._component.operation()
        print(f"[{self.log_level}] 操作完成: {result}")
        return result


class MetricsDecorator(BaseDecorator):
    """指标装饰器

    为组件添加性能监控功能.
    """

    def __init__(self, component: Component):
        """初始化指标装饰器

        Args:
            component: 要装饰的组件
        """
        super().__init__(component)
        self.call_count = 0
        self.total_time = 0.0

    def operation(self) -> str:
        """执行带指标收集的操作"""
        start_time = time.time()
        self.call_count += 1

        result = self._component.operation()

        duration = time.time() - start_time
        self.total_time += duration

        print(
            f"[指标] 调用次数: {self.call_count}, 耗时: {duration:.4f}s, 平均耗时: {self.total_time / self.call_count:.4f}s"
        )
        return result

    def get_metrics(self) -> dict[str, Any]:
        """获取性能指标"""
        return {
            "call_count": self.call_count,
            "total_time": self.total_time,
            "avg_time": (
                self.total_time / self.call_count if self.call_count > 0 else 0.0
            ),
        }


class RetryDecorator(BaseDecorator):
    """重试装饰器

    为组件添加重试功能.
    """

    def __init__(self, component: Component, max_retries: int = 3, delay: float = 1.0):
        """初始化重试装饰器

        Args:
            component: 要装饰的组件
            max_retries: 最大重试次数
            delay: 重试延迟（秒）
        """
        super().__init__(component)
        self.max_retries = max_retries
        self.delay = delay

    def operation(self) -> str:
        """执行带重试的操作"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                result = self._component.operation()
                if attempt > 0:
                    print(f"[重试] 第{attempt}次重试成功")
                return result
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    print(
                        f"[重试] 第{attempt + 1}次尝试失败，{self.delay}秒后重试: {e}"
                    )
                    time.sleep(self.delay)
                else:
                    print("[重试] 所有重试均失败")

        raise last_exception


class ValidationDecorator(BaseDecorator):
    """验证装饰器

    为组件添加输入验证功能.
    """

    def __init__(self,
    component: Component,
    validator: Callable | None = None):
        """初始化验证装饰器

        Args:
            component: 要装饰的组件
            validator: 验证函数
        """
        super().__init__(component)
        self.validator = validator or self._default_validator

    def _default_validator(self,
    *args,
    **kwargs):
        """默认验证器"""
        return True

    def operation(self) -> str:
        """执行带验证的操作"""
        print("[验证] 开始验证输入...")

        if self.validator():
            print("[验证] 验证通过")
            result = self._component.operation()
            print("[验证] 输出验证通过")
            return result
        else:
            raise ValueError("验证失败")


class CacheDecorator(BaseDecorator):
    """缓存装饰器

    为组件添加缓存功能.
    """

    def __init__(self, component: Component, cache_size: int = 128):
        """初始化缓存装饰器

        Args:
            component: 要装饰的组件
            cache_size: 缓存大小
        """
        super().__init__(component)
        self.cache_size = cache_size
        self._cache = {}

    def operation(self) -> str:
        """执行带缓存的操作"""
        cache_key = str(id(self._component))

        if cache_key in self._cache:
            print(f"[缓存] 命中缓存: {cache_key}")
            return self._cache[cache_key]

        print(f"[缓存] 缓存未命中，执行操作: {cache_key}")
        result = self._component.operation()

        # 如果缓存满了，移除最旧的条目
        if len(self._cache) >= self.cache_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            print(f"[缓存] 移除最旧缓存: {oldest_key}")

        self._cache[cache_key] = result
        print(f"[缓存] 缓存结果: {cache_key}")
        return result

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        print("[缓存] 缓存已清空")

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        return {
            "cache_size": len(self._cache),
    "max_size": self.cache_size,
    "hit_rate": 0.0,
    # 简化实现
        }


# 异步装饰器
def async_log(log_level: str = "INFO"):
    """异步日志装饰器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args,
    **kwargs):
            print(f"[{log_level}] 开始执行异步函数: {func.__name__}")
            try:
                result = await func(*args, **kwargs)
                print(f"[{log_level}] 异步函数完成: {func.__name__}")
                return result
            except Exception as e:
                print(f"[{log_level}] 异步函数异常: {func.__name__}, 错误: {e}")
                raise

        return wrapper

    return decorator


def async_metrics(func):
    """异步指标装饰器"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            print(f"[异步指标] {func.__name__} 耗时: {duration:.4f}s")
            return result
        except Exception:
            duration = time.time() - start_time
            print(f"[异步指标] {func.__name__} 异常，耗时: {duration:.4f}s")
            raise

    return wrapper


def async_retry(max_retries: int = 3, delay: float = 1.0):
    """异步重试装饰器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        print(f"[异步重试] 第{attempt}次重试成功")
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(
                            f"[异步重试] 第{attempt + 1}次尝试失败，{delay}秒后重试: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        print("[异步重试] 所有重试均失败")

            raise last_exception

        return wrapper

    return decorator


def create_decorated_service(service_name: str) -> Component:
    """创建装饰后的服务

    Args:
        service_name: 服务名称

    Returns:
        Component: 装饰后的服务组件
    """
    base_service = ConcreteComponent(service_name)

    # 添加装饰器
    logged_service = LoggingDecorator(base_service,
    "INFO")
    metrics_service = MetricsDecorator(logged_service)
    cached_service = CacheDecorator(metrics_service,
    cache_size=64)

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
