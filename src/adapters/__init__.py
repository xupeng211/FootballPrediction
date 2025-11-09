from .base import Adaptee, BaseAdapter, Target

# 重新启用的模块导入
from .factory_simple import AdapterFactory as SimpleAdapterFactory
from .factory_simple import get_adapter
from .football import (
    ApiFootballAdapter,
    CompositeFootballAdapter,
    FootballApiAdapter,
    FootballDataAdapter,
    OptaDataAdapter,
)
from .registry import AdapterError, AdapterRegistry

# 适配器模式实现
# Adapter Pattern Implementation
# 用于集成外部系统和API.
# Used to integrate external systems and APIs.

__all__ = [
    # 基础类 - Base classes
    "BaseAdapter",
    "Adaptee",
    "Target",
    # 适配器实现 - Adapter implementations
    "AdapterError",
    "AdapterRegistry",
    "SimpleAdapterFactory",
    "get_adapter",
    "ApiFootballAdapter",
    "FootballApiAdapter",
    "FootballDataAdapter",
    "OptaDataAdapter",
    "CompositeFootballAdapter",
]

# 为了向后兼容，提供BaseAdapter的别名
Adapter = BaseAdapter
