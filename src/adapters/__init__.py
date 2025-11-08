from .base import Adaptee, Adapter, BaseAdapter, Target
from .factory_simple import AdapterFactory, get_adapter
from .football import (
    ApiFootballAdapter,
    FootballApiAdapter,
    FootballDataAdapter,
    OptaDataAdapter,
)
from .registry import AdapterError, AdapterRegistry

"""
适配器模式实现
Adapter Pattern Implementation

用于集成外部系统和API.
Used to integrate external systems and APIs.
"""

__all__ = [
    # Base classes
    "Adapter",
    "Adaptee",
    "Target",
    "BaseAdapter",
    # Football adapters
    "FootballApiAdapter",
    "FootballDataAdapter",
    "ApiFootballAdapter",
    "OptaDataAdapter",
    # Factory
    "AdapterFactory",
    "get_adapter",
    # Registry
    "AdapterRegistry",
    "AdapterError",
]
