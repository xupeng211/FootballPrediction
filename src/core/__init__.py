"""
足球预测系统核心功能模块

提供系统核心功能,包括:
- 配置管理
- 日志系统
- 异常处理
- 基础工具类
"""

from .config_di import ConfigurationBinder
from .di import (
    DIContainer,
    ServiceCollection,
    ServiceLifetime,
    configure_services,
    inject,
    resolve,
)
from .exceptions import (
    ConfigError,
    DataError,
    DependencyInjectionError,
    FootballPredictionError,
    ModelError,
    PredictionError,
)
from .logger import Logger, logger
from .service_lifecycle import ServiceLifecycleManager, get_lifecycle_manager

__all__ = [
    # 配置管理
    "Config",
    "config",
    "Settings",
    "get_settings",
    # 日志系统
    "Logger",
    "logger",
    # 异常类
    "FootballPredictionError",
    "ConfigError",
    "DataError",
    "ModelError",
    "PredictionError",
    "DependencyInjectionError",
    # 依赖注入
    "DIContainer",
    "ServiceCollection",
    "ServiceLifetime",
    "configure_services",
    "resolve",
    "inject",
    "ServiceLifecycleManager",
    "get_lifecycle_manager",
    "ConfigurationBinder",
]
