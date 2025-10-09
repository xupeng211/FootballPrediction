"""
适配器模式实现
Adapter Pattern Implementation

用于集成外部系统和API。
Used to integrate external systems and APIs.
"""

from .base import Adapter, Adaptee, Target
from .football import (
    FootballApiAdapter,
    FootballDataAdapter,
    ApiFootballAdapter,
    OptaDataAdapter,
)
from .weather import (
    WeatherApiAdapter,
    OpenWeatherMapAdapter,
    WeatherStackAdapter,
)
from .odds import (
    OddsApiAdapter,
    Bet365Adapter,
    WilliamHillAdapter,
)
from .factory import AdapterFactory
from .registry import AdapterRegistry

__all__ = [
    # Base classes
    "Adapter",
    "Adaptee",
    "Target",
    # Football adapters
    "FootballApiAdapter",
    "FootballDataAdapter",
    "ApiFootballAdapter",
    "OptaDataAdapter",
    # Weather adapters
    "WeatherApiAdapter",
    "OpenWeatherMapAdapter",
    "WeatherStackAdapter",
    # Odds adapters
    "OddsApiAdapter",
    "Bet365Adapter",
    "WilliamHillAdapter",
    # Factory
    "AdapterFactory",
    # Registry
    "AdapterRegistry",
]
