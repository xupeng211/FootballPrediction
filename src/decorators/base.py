"""装饰器模式基类
Decorator Pattern Base Classes.

定义装饰器模式的核心接口和抽象类.
Define core interfaces and abstract classes for the decorator pattern.
"""

import inspect
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any


class Component(ABC):
    """组件接口,定义了组件的基本操作."""

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """执行组件操作."""

    @abstractmethod
    def get_name(self) -> str:
        """获取组件名称."""


class ConcreteComponent(Component):
    """具体组件,实现了组件接口的基本功能."""

    def __init__(self, name: str, func: Callable):
        """函数文档字符串."""
        # 添加pass语句
        self.name = name
        self.func = func
        self._wrapped = self._wrap_function(func)

    def _wrap_function(self, func: Callable) -> Callable:
        """包装函数为异步函数."""
        if inspect.iscoroutinefunction(func):
            return func
        else:

            async def async_wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return async_wrapper

    async def execute(self, *args, **kwargs) -> Any:
        """执行具体组件的操作."""
        return await self._wrapped(*args, **kwargs)

    def get_name(self) -> str:
        return self.name


class Decorator(Component):
    """装饰器基类,实现了组件接口并持有一个组件引用."""

    def __init__(self, component: Component, name: str | None = None):
        """函数文档字符串."""
        # 添加pass语句
        self.component = component
        self.name = name or f"{self.__class__.__name__}_{uuid.uuid4().hex[:8]}"
        self.execution_count = 0
        self.last_execution_time: datetime | None = None
        self.total_execution_time = 0.0
        self.error_count = 0

    async def execute(self, *args, **kwargs) -> Any:
        """执行装饰器的操作,通常会调用被装饰组件的方法."""
        self.execution_count += 1
        start_time = time.time()

        try:
            # 调用具体装饰器的实现
            result = await self._execute(*args, **kwargs)
            return result
        except (ValueError, typeError, AttributeError, KeyError, RuntimeError):
            self.error_count += 1
            # 错误处理装饰器可能会重写此行为
            raise
        finally:
            # 记录执行时间
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            self.last_execution_time = datetime.utcnow()

    @abstractmethod
    async def _execute(self, *args, **kwargs) -> Any:
        """装饰器的具体实现,由子类重写."""

    def get_name(self) -> str:
        return self.name

    def get_stats(self) -> dict[str, Any]:
        """获取装饰器执行统计信息."""
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "success_rate": (
                (self.execution_count - self.error_count) / self.execution_count
                if self.execution_count > 0
                else 0
            ),
            "total_execution_time": self.total_execution_time,
            "average_execution_time": (
                self.total_execution_time / self.execution_count
                if self.execution_count > 0
                else 0
            ),
            "last_execution_time": self.last_execution_time,
        }


class DecoratorComponent(Decorator):
    """装饰器组件,用于装饰函数或方法."""

    def __init__(
        self,
        func: Callable,
        decorators: list[Decorator],
        name: str | None = None,
    ):
        # 创建具体组件
        component = ConcreteComponent(name or func.__name__, func)
        super().__init__(component, name)
        self.decorators = decorators
        self.func = func

    async def _execute(self, *args, **kwargs) -> Any:
        """依次执行所有装饰器."""
        # 从外到内应用装饰器
        current_component = self.component

        for decorator in reversed(self.decorators):
            decorator.component = current_component
            current_component = decorator

        # 执行最外层的装饰器
        return await current_component.execute(*args, **kwargs)

    def get_all_stats(self) -> dict[str, Any]:
        """获取所有装饰器的统计信息."""
        stats = {"function": self.func.__name__, "decorators": []}

        for decorator in self.decorators:
            stats["decorators"].append(decorator.get_stats())

        return stats


class DecoratorChain:
    """类文档字符串."""

    pass  # 添加pass语句
    """装饰器链,用于管理多个装饰器的执行顺序"""

    def __init__(self):
        """函数文档字符串."""
        # 添加pass语句
        self.decorators: list[Decorator] = []

    def add_decorator(self, decorator: Decorator) -> "DecoratorChain":
        """添加装饰器到链中."""
        self.decorators.append(decorator)
        return self

    def remove_decorator(self, name: str) -> bool:
        """从链中移除装饰器."""
        for i, decorator in enumerate(self.decorators):
            if decorator.get_name() == name:
                del self.decorators[i]
                return True
        return False

    def execute(self, component: Component, *args, **kwargs) -> Awaitable[Any]:
        """执行装饰器链."""
        current_component = component

        for decorator in reversed(self.decorators):
            decorator.component = current_component
            current_component = decorator

        return current_component.execute(*args, **kwargs)

    def get_chain_stats(self) -> dict[str, Any]:
        """获取装饰器链的统计信息."""
        return {
            "chain_length": len(self.decorators),
            "decorators": [d.get_stats() for d in self.decorators],
        }


# 装饰器上下文管理器
class DecoratorContext:
    """类文档字符串."""

    pass  # 添加pass语句
    """装饰器执行上下文,用于在装饰器之间传递数据"""

    def __init__(self):
        """函数文档字符串."""
        # 添加pass语句
        self.data: dict[str, Any] = {}
        self.start_time = time.time()
        self.trace_id = str(uuid.uuid4())
        self.execution_path: list[str] = []

    def set(self, key: str, value: Any) -> None:
        """设置上下文数据."""
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文数据."""
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        """检查上下文数据是否存在."""
        return key in self.data

    def add_execution_step(self, decorator_name: str) -> None:
        """添加执行步骤."""
        self.execution_path.append(decorator_name)

    def get_execution_time(self) -> float:
        """获取执行时间."""
        return time.time() - self.start_time

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "trace_id": self.trace_id,
            "execution_time": self.get_execution_time(),
            "execution_path": self.execution_path,
            "data": self.data,
        }


# 装饰器注册表
class DecoratorRegistry:
    """类文档字符串."""

    pass  # 添加pass语句
    """装饰器注册表,用于管理全局装饰器"""

    def __init__(self):
        """函数文档字符串."""
        # 添加pass语句
        self._decorators: dict[str, type[Decorator]] = {}
        self._instances: dict[str, Decorator] = {}

    def register(self, name: str, decorator_class: type[Decorator]) -> None:
        """注册装饰器类."""
        self._decorators[name] = decorator_class

    def unregister(self, name: str) -> None:
        """注销装饰器类."""
        self._decorators.pop(name, None)
        self._instances.pop(name, None)

    def get_decorator_class(self, name: str) -> type[Decorator] | None:
        """获取装饰器类."""
        return self._decorators.get(name)

    def get_decorator_instance(
        self, name: str, component: Component, **kwargs
    ) -> Decorator | None:
        """获取装饰器实例（单例模式）."""
        decorator_class = self._decorators.get(name)
        if not decorator_class:
            return None

        instance_key = f"{name}_{id(component)}"
        if instance_key not in self._instances:
            self._instances[instance_key] = decorator_class(component, **kwargs)

        return self._instances[instance_key]

    def list_decorators(self) -> list[str]:
        """列出所有注册的装饰器."""
        return list(self._decorators.keys())

    def clear(self) -> None:
        """清空注册表."""
        self._decorators.clear()
        self._instances.clear()


# 全局装饰器注册表
decorator_registry = DecoratorRegistry()
