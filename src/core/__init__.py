"""
足球预测系统核心功能模块

提供系统核心功能，包括：
- 配置管理
- 日志系统
- 异常处理
- 基础工具类
"""

from .config import Config, Settings, config, get_settings
from .exceptions import (
    ConfigError,
    DataError,
    FootballPredictionError,
    ModelError,
    PredictionError,
)
from .logger import Logger, logger

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
]
