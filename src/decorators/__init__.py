from typing import Any, Dict, List, Optional, Union
"""
装饰器模式实现
Decorator Pattern Implementation

用于功能增强和横切关注点。
Used for functionality enhancement and cross-cutting concerns.
"""

from .base import Decorator, DecoratorComponent
from .decorators import (
    LoggingDecorator,
    RetryDecorator,
    MetricsDecorator,
    ValidationDecorator,
    CacheDecorator,
    AuthDecorator,
    RateLimitDecorator,
    TimeoutDecorator,
)
from .factory import DecoratorFactory
from .service import DecoratorService

__all__ = [
    # Base classes
    "Decorator",
    "DecoratorComponent",
    # Concrete decorators
    "LoggingDecorator",
    "RetryDecorator",
    "MetricsDecorator",
    "ValidationDecorator",
    "CacheDecorator",
    "AuthDecorator",
    "RateLimitDecorator",
    "TimeoutDecorator",
    # Factory
    "DecoratorFactory",
    # Service
    "DecoratorService",
]
