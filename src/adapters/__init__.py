from .base import Adaptee, Adapter, BaseAdapter, Target
from .factory_simple import AdapterFactory, get_adapter
from .football import (
    ApiFootballAdapter,
    FootballApiAdapter,
    FootballDataAdapter,
    OptaDataAdapter,
)
from .registry import AdapterError, AdapterRegistry

# 适配器模式实现
# Adapter Pattern Implementation
# 用于集成外部系统和API.
# Used to integrate external systems and APIs.

__ALL__ = [
    "Adapter",
    "Adaptee",
    "Target",
    "BaseAdapter",
    "FootballApiAdapter",
    "FootballDataAdapter",
    "ApiFootballAdapter",
    "OptaDataAdapter",
    "AdapterFactory",
    "get_adapter",
    "AdapterError",
    "AdapterRegistry",
]
