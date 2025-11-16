"""
装饰器模式实现
Decorator Pattern Implementation

用于功能增强和横切关注点.
Used for functionality enhancement and cross-cutting concerns.
"""

from .base import Decorator, DecoratorComponent

# 导入__init__相关类
# 模块暂未实现 - 自动修复
AuthDecorator = None
CacheDecorator = None
LoggingDecorator = None
MetricsDecorator = None
RateLimitDecorator = None
RetryDecorator = None
TimeoutDecorator = None
ValidationDecorator = None

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
