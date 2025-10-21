"""
足球预测系统核心功能模块

提供系统核心功能，包括：
- 配置管理
- 日志系统
- 异常处理
- 基础工具类
"""

from .config import Config, Settings, get_config, get_settings
from .exceptions import (
    ConfigError,
    DataError,
    FootballPredictionError,
    ModelError,
    PredictionError,
    DependencyInjectionError,
)
from .logger import Logger, logger
from .di import (
    DIContainer,
    ServiceCollection,
    ServiceLifetime,
    configure_services,
    resolve,
    inject,
)
from .service_lifecycle import ServiceLifecycleManager, get_lifecycle_manager
from .config_di import ConfigurationBinder

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
