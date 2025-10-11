"""
装饰器服务
Decorator Service

提供装饰器的高层管理和服务。
Provides high-level management and services for decorators.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from pathlib import Path

from ..core.logger import get_logger
from .base import (
    DecoratorComponent,
    ConcreteComponent,
    DecoratorContext,
)
from .factory import DecoratorFactory, DecoratorConfig

logger = get_logger(__name__)


class DecoratorService:
    """装饰器服务，管理和应用装饰器"""

    def __init__(self, factory: Optional[DecoratorFactory] = None):
        self.factory = factory or DecoratorFactory()
        self._decorated_functions: Dict[str, DecoratorComponent] = {}
        self._global_decorators: List[DecoratorConfig] = []
        self._function_decorators: Dict[str, List[DecoratorConfig]] = {}

    def load_configuration(self, config_path: Union[str, Path]) -> None:
        """加载装饰器配置文件"""
        self.factory.load_config_from_file(config_path)

        # 加载全局装饰器
        for name, config in self.factory._config_cache.items():
            if config.conditions and config.conditions.get("global", False):
                self._global_decorators.append(config)

    def register_global_decorator(self, config: DecoratorConfig) -> None:
        """注册全局装饰器"""
        self._global_decorators.append(config)
        self.factory._config_cache[config.name] = config

    def register_function_decorator(
        self, function_name: str, config: DecoratorConfig
    ) -> None:
        """为特定函数注册装饰器"""
        if function_name not in self._function_decorators:
            self._function_decorators[function_name] = []
        self._function_decorators[function_name].append(config)
        self.factory._config_cache[config.name] = config

    def apply_decorators(
        self, func: Callable, decorator_names: Optional[List[str]] = None, **kwargs
    ) -> Callable:
        """应用装饰器到函数"""
        func_name = func.__name__

        # 如果已经装饰过，直接返回
        if func_name in self._decorated_functions:
            return self._decorated_functions[func_name]  # type: ignore

        # 创建具体组件
        component = ConcreteComponent(func_name, func)

        # 收集所有要应用的装饰器配置
        configs_to_apply = []

        # 1. 添加全局装饰器
        configs_to_apply.extend(self._global_decorators)

        # 2. 添加函数特定的装饰器
        if func_name in self._function_decorators:
            configs_to_apply.extend(self._function_decorators[func_name])

        # 3. 添加指定的装饰器
        if decorator_names:
            for name in decorator_names:
                config = self.factory.get_config(name)
                if config:
                    configs_to_apply.append(config)

        # 4. 添加链配置中的装饰器
        for chain_config in self.factory._chain_configs.values():
            if self._matches_function(func_name, chain_config.target_functions):
                configs_to_apply.extend(chain_config.decorators)

        # 创建装饰器
        decorators = self.factory.create_chain(configs_to_apply, component)

        # 创建装饰器组件
        decorator_component = DecoratorComponent(
            func, decorators, name=f"decorated_{func_name}"
        )

        # 保存装饰后的函数
        self._decorated_functions[func_name] = decorator_component

        # 返回包装后的函数
        return self._create_wrapper(decorator_component)

    def _matches_function(self, func_name: str, patterns: List[str]) -> bool:
        """检查函数名是否匹配模式"""
        for pattern in patterns:
            if pattern.endswith("*"):
                # 前缀匹配
                if func_name.startswith(pattern[:-1]):
                    return True
            elif pattern.startswith("*"):
                # 后缀匹配
                if func_name.endswith(pattern[1:]):
                    return True
            elif "*" in pattern:
                # 通配符匹配
                import fnmatch

                if fnmatch.fnmatch(func_name, pattern):
                    return True
            else:
                # 精确匹配
                if func_name == pattern:
                    return True
        return False

    def _create_wrapper(self, decorator_component: DecoratorComponent) -> Callable:
        """创建函数包装器"""

        async def wrapper(*args, **kwargs):
            # 创建装饰器上下文
            context = kwargs.pop("decorator_context", None)
            if not context:
                context = DecoratorContext()
                kwargs["decorator_context"] = context

            # 添加执行步骤
            context.add_execution_step(decorator_component.get_name())

            # 执行装饰器组件
            return await decorator_component.execute(*args, **kwargs)

        # 保留原函数的元数据
        wrapper.__name__ = decorator_component.func.__name__
        wrapper.__doc__ = decorator_component.func.__doc__
        wrapper.__module__ = decorator_component.func.__module__
        wrapper.__annotations__ = decorator_component.func.__annotations__

        # 添加装饰器统计方法
        wrapper.get_decorator_stats = decorator_component.get_all_stats  # type: ignore

        return wrapper

    def get_function_stats(self, func_name: str) -> Optional[Dict[str, Any]]:
        """获取函数的装饰器统计信息"""
        if func_name in self._decorated_functions:
            return self._decorated_functions[func_name].get_all_stats()
        return None

    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有装饰器的统计信息"""
        stats = {"total_functions": len(self._decorated_functions), "functions": {}}

        for func_name, component in self._decorated_functions.items():
            stats["functions"][func_name] = component.get_all_stats()  # type: ignore

        return stats

    def clear_stats(self) -> None:
        """清空所有统计信息"""
        for component in self._decorated_functions.values():
            for decorator in component.decorators:
                decorator.execution_count = 0
                decorator.error_count = 0
                decorator.total_execution_time = 0.0
                decorator.last_execution_time = None

    def reload_configuration(self) -> None:
        """重新加载配置"""
        # 清空缓存
        self._global_decorators.clear()
        self._function_decorators.clear()

        # 从工厂重新加载
        for config in self.factory._config_cache.values():
            if config.conditions and config.conditions.get("global", False):
                self._global_decorators.append(config)


# 便捷装饰器函数
def decorate(
    decorator_names: Optional[List[str]] = None, **decorator_kwargs
) -> Callable:
    """装饰器工厂函数，用于装饰其他函数"""

    def decorator(func: Callable) -> Callable:
        # 获取装饰器服务
        service = DecoratorService()

        # 应用装饰器
        return service.apply_decorators(
            func, decorator_names=decorator_names, **decorator_kwargs
        )

    return decorator


def with_logging(
    level: str = "INFO", log_args: bool = True, log_result: bool = True, **kwargs
) -> Callable:
    """添加日志装饰器"""
    return decorate(
        decorator_names=["default_logging"],
        level=level,
        log_args=log_args,
        log_result=log_result,
        **kwargs,
    )


def with_retry(
    max_attempts: int = 3, delay: float = 1.0, backoff_factor: float = 2.0, **kwargs
) -> Callable:
    """添加重试装饰器"""
    return decorate(
        decorator_names=["default_retry"],
        max_attempts=max_attempts,
        delay=delay,
        backoff_factor=backoff_factor,
        **kwargs,
    )


def with_metrics(
    metric_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None, **kwargs
) -> Callable:
    """添加指标装饰器"""
    return decorate(
        decorator_names=["default_metrics"],
        metric_name=metric_name,
        tags=tags,
        **kwargs,
    )


def with_cache(ttl: Optional[int] = None, **kwargs) -> Callable:
    """添加缓存装饰器"""
    return decorate(decorator_names=["default_cache"], ttl=ttl, **kwargs)


def with_timeout(timeout_seconds: float = 30.0, **kwargs) -> Callable:
    """添加超时装饰器"""
    return decorate(
        decorator_names=["default_timeout"], timeout_seconds=timeout_seconds, **kwargs
    )


def with_all(
    log_level: str = "INFO",
    retry_attempts: int = 3,
    cache_ttl: Optional[int] = None,
    timeout_seconds: float = 30.0,
    **kwargs,
) -> Callable:
    """添加所有常用装饰器"""
    return decorate(
        decorator_names=[
            "default_logging",
            "default_retry",
            "default_metrics",
            "default_cache",
            "default_timeout",
        ],
        level=log_level,
        max_attempts=retry_attempts,
        ttl=cache_ttl,
        timeout_seconds=timeout_seconds,
        **kwargs,
    )


# 创建全局装饰器服务实例
decorator_service = DecoratorService()
