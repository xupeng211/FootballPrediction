"""
观察者模式模块
Observer Pattern Module

提供观察者模式的实现，用于监控和日志系统的通知。
Provides observer pattern implementation for monitoring and logging notifications.
"""

from .base import Observer, Subject, ObservableEvent
from .observers import (
    MetricsObserver,
    LoggingObserver,
    AlertingObserver,
    PerformanceObserver,
)
from .subjects import (
    SystemMetricsSubject,
    PredictionMetricsSubject,
    AlertSubject,
)
from .manager import ObserverManager, get_observer_manager

# 系统级便捷函数
def initialize_observer_system():
    """初始化观察者系统"""
    manager = get_observer_manager()
    if hasattr(manager, "initialize"):
        manager.initialize()
    return True

def start_observer_system():
    """启动观察者系统"""
    manager = get_observer_manager()
    if hasattr(manager, "start"):
        manager.start()
    return True

def stop_observer_system():
    """停止观察者系统"""
    manager = get_observer_manager()
    if hasattr(manager, "stop"):
        manager.stop()
    return True

__all__ = [
    # 基础类
    "Observer",
    "Subject",
    "ObservableEvent",
    # 观察者实现
    "MetricsObserver",
    "LoggingObserver",
    "AlertingObserver",
    "PerformanceObserver",
    # 被观察者实现
    "SystemMetricsSubject",
    "PredictionMetricsSubject",
    "AlertSubject",
    # 管理器
    "ObserverManager",
    "get_observer_manager",
    # 系统函数
    "initialize_observer_system",
    "start_observer_system",
    "stop_observer_system",
]
