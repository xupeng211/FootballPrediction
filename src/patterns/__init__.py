from typing import Any, Dict, List, Optional, Union
"""
设计模式实现模块

包含各种设计模式的实现，用于提升代码的可维护性和扩展性。
"""

from .observer import (
    Observer,
    Subject,
    MetricsObserver,
    LoggingObserver,
    AlertingObserver,
    ObservableService,
    create_observer_system,
    setup_service_observers,
)

from .decorator import (
    Component,
    BaseDecorator,
    LoggingDecorator,
    RetryDecorator,
    MetricsDecorator,
    ValidationDecorator,
    CacheDecorator,
    async_retry,
    async_log,
    async_metrics,
    create_decorated_service,
)

from .adapter import (
    ExternalAPI,
    APIAdapter,
    FootballApiAdapter,
    WeatherApiAdapter,
    OddsApiAdapter,
    AdapterFactory,
    UnifiedDataCollector,
    ExternalData,
)

__all__ = [
    # Observer Pattern
    "Observer",
    "Subject",
    "MetricsObserver",
    "LoggingObserver",
    "AlertingObserver",
    "ObservableService",
    "create_observer_system",
    "setup_service_observers",
    # Decorator Pattern
    "Component",
    "BaseDecorator",
    "LoggingDecorator",
    "RetryDecorator",
    "MetricsDecorator",
    "ValidationDecorator",
    "CacheDecorator",
    "async_retry",
    "async_log",
    "async_metrics",
    "create_decorated_service",
    # Adapter Pattern
    "ExternalAPI",
    "APIAdapter",
    "FootballApiAdapter",
    "WeatherApiAdapter",
    "OddsApiAdapter",
    "AdapterFactory",
    "UnifiedDataCollector",
    "ExternalData",
]
