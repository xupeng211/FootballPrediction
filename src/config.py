#!/usr/bin/env python3
"""
配置兼容性桥接文件 - 用于向后兼容
实际配置已迁移到 src.config_unified
"""

# 导入统一配置并提供向后兼容的别名
from .config_unified import (
    UnifiedSettings,
    get_settings,
    DatabaseConfig,
    RedisConfig,
    FotMobAPIConfig,
    ServiceConfig,
    LoggingConfig,
    Environment
)

# 为了向后兼容，提供常用的别名
Settings = UnifiedSettings
Config = UnifiedSettings

# 导出所有配置类以保持向后兼容性
__all__ = [
    'UnifiedSettings',
    'Settings',
    'Config',
    'get_settings',
    'DatabaseConfig',
    'RedisConfig',
    'FotMobAPIConfig',
    'ServiceConfig',
    'LoggingConfig',
    'Environment'
]