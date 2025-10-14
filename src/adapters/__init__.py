from typing import Any, Dict, List, Optional, Union
"""
适配器模式实现
Adapter Pattern Implementation

用于集成外部系统和API。
Used to integrate external systems and APIs.
"""

from .base import Adapter, Adaptee, Target, BaseAdapter
from .football import (
    FootballApiAdapter,
    FootballDataAdapter,
    ApiFootballAdapter,
    OptaDataAdapter,
)
from .factory_simple import AdapterFactory, get_adapter
from .registry_simple import AdapterRegistry, register_adapter

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
    "register_adapter",
]
