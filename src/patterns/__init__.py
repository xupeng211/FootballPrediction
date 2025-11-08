from .adapter import (
    AdapterFactory,
    APIAdapter,
    ExternalAPI,
    ExternalData,
    FootballApiAdapter,
    OddsApiAdapter,
    UnifiedDataCollector,
    WeatherApiAdapter,
)
from .decorator import (
    BaseDecorator,
    CacheDecorator,
    Component,
    LoggingDecorator,
    MetricsDecorator,
    RetryDecorator,
    ValidationDecorator,
    async_log,
    async_metrics,
    async_retry,
    create_decorated_service,
)
from .observer import (
    AlertingObserver,
    LoggingObserver,
    MetricsObserver,
    ObservableService,
    Observer,
    Subject,
    create_observer_system,
    setup_service_observers,
)

"""
设计模式实现模块

包含各种设计模式的实现,用于提升代码的可维护性和扩展性.
"""

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
