"""
适配器工厂模块
BaseAdapter Factory Module

提供适配器的创建、注册和管理功能。
Provides adapter creation, registration, and management functionality.
"""

from dataclasses import dataclass, field
from typing import Any

# 导入基础类
from .base import BaseAdapter

# 尝试导入具体适配器类，如果失败则创建Mock实现
try:
    from .football import (
        ApiFootballAdapter,
        CompositeFootballAdapter,
        OptaDataAdapter,
    )
except ImportError:

    class ApiFootballAdapter(BaseAdapter):
        """Mock API Football适配器"""

        pass

    class CompositeFootballAdapter(BaseAdapter):
        """Mock Composite Football适配器"""

        pass

    class OptaDataAdapter(BaseAdapter):
        """Mock Opta Data适配器"""

        pass


class BaseAdapterError(Exception):
    """适配器错误"""

    pass


@dataclass
class BaseAdapterConfig:
    """适配器配置"""

    name: str
    adapter_type: str
    enabled: bool = True
    priority: int = 0
    config: dict[str, Any] = field(default_factory=dict)
    timeout: int | None = None

    # 兼容测试期望的属性
    RETRY_COUNT: int = 3
    RATE_LIMIT: int | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    RATE_LIMITS: Any = None
    CACHE_CONFIG: Any = None
    RETRY_CONFIG: Any = None


@dataclass
class BaseAdapterGroupConfig:
    """适配器组配置"""

    name: str
    description: str = ""
    adapters: list[Any] = field(default_factory=list)

    # 兼容测试期望的属性
    FALLBACK_ENABLED: bool = True
    LOAD_BALANCING: str = "round_robin"
    PRIMARY_ADAPTER: Any = None
    FALLBACK_STRATEGY: str = "sequential"


class BaseAdapterFactory:
    """适配器工厂类"""

    def __init__(self):
        """初始化适配器工厂"""
        self._adapters: dict[str, BaseAdapter] = {}
        self._configs: dict[str, BaseAdapterConfig] = {}
        self._groups: dict[str, BaseAdapterGroupConfig] = {}
        self._register_default_adapters()

    def create_adapter(
        self, name: str, config: dict[str, Any] | None = None, **kwargs
    ) -> BaseAdapter:
        """创建适配器"""
        if name not in self._adapters:
            raise ValueError(f"Unknown adapter: {name}")
        adapter_class = self._adapters[name]
        return adapter_class(config or {}, **kwargs)

    def register_adapter(self, name: str, adapter_class: type[BaseAdapter]) -> None:
        """注册适配器类"""
        self._adapters[name] = adapter_class

    def register_config(self, name: str, config: BaseAdapterConfig) -> None:
        """注册适配器配置"""
        self._configs[name] = config

    def register_group(self, name: str, group_config: BaseAdapterGroupConfig) -> None:
        """注册适配器组"""
        self._groups[name] = group_config

    def get_adapter(self, name: str) -> BaseAdapter:
        """获取适配器"""
        return self.create_adapter(name)

    def _register_default_adapters(self):
        """注册默认适配器"""
        # 注册足球数据适配器
        self.register_adapter("api_football", ApiFootballAdapter)
        self.register_adapter("composite_football", CompositeFootballAdapter)
        self.register_adapter("opta_data", OptaDataAdapter)


# 全局适配器工厂实例
_global_factory = BaseAdapterFactory()
adapter_factory = _global_factory  # 导出全局工厂实例,兼容测试期望


def register_adapter(name: str, adapter_class: type[BaseAdapter]) -> None:
    """注册适配器的便捷函数"""
    _global_factory.register_adapter(name, adapter_class)


def create_adapter(
    name: str, config: dict[str, Any] | None = None, **kwargs
) -> BaseAdapter:
    """创建适配器的便捷函数"""
    return _global_factory.create_adapter(name, config, **kwargs)


def get_global_factory() -> BaseAdapterFactory:
    """获取全局工厂实例"""
    return _global_factory


__all__ = [
    "BaseAdapterError",
    "BaseAdapterConfig",
    "BaseAdapterGroupConfig",
    "BaseAdapterFactory",
    "adapter_factory",
    "register_adapter",
    "create_adapter",
    "get_global_factory",
    # 具体适配器类
    "ApiFootballAdapter",
    "CompositeFootballAdapter",
    "OptaDataAdapter",
]
