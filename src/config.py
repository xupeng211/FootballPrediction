#!/usr/bin/env python3
"""
Football Prediction System Configuration (Legacy Compatibility Wrapper)

⚠️  DEPRECATION NOTICE ⚠️
This file is maintained for backward compatibility only.
Please use config_secure.py for new development.

迁移指南:
1. 将 `from src.config import Settings` 改为 `from src.config_secure import Settings`
2. 将配置访问方式从 `Settings().database.xxx` 改为 `get_settings().database.xxx`
3. 确保所有必需的环境变量已配置

主要特性:
- 向后兼容的配置接口
- 类型安全的配置访问
- 环境变量自动加载
- 安全配置验证
"""

import os
import logging
import warnings
from typing import Optional, List, Dict, Any, Callable

# 导入新的安全配置系统
try:
    from .config_secure import (
        Settings as _SecureSettings,
        get_settings as _get_secure_settings,
        validate_required_environment,
        ConfigurationError,
        SecurityConfigurationError,
        print_configuration_summary
    )
    _SECURE_CONFIG_AVAILABLE = True
except ImportError as e:
    logging.error(f"Failed to import secure configuration: {e}")
    _SECURE_CONFIG_AVAILABLE = False

# 如果安全配置不可用，定义基本异常
if not _SECURE_CONFIG_AVAILABLE:
    class ConfigurationError(Exception):
        """配置相关异常"""
        pass

    class SecurityConfigurationError(ConfigurationError):
        """安全配置异常"""
        pass

# 发出弃用警告
warnings.warn(
    "src.config is deprecated. Please use src.config_secure instead.",
    DeprecationWarning,
    stacklevel=2
)

logger = logging.getLogger(__name__)


class Settings:
    """
    向后兼容的配置类包装器

    ⚠️ 此类将被弃用，请使用 config_secure.py 中的 Settings 类
    """

    def __init__(self):
        if not _SECURE_CONFIG_AVAILABLE:
            raise ConfigurationError(
                "Secure configuration module not available. "
                "Please check your Python path and dependencies."
            )

        # 验证必需的环境变量
        try:
            validate_required_environment()
        except ConfigurationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise

        self._secure_settings = _get_secure_settings()

        # 提供向后兼容的属性访问
        self.database = self._secure_settings.database
        self.redis = self._secure_settings.redis
        self.fotmob = self._secure_settings.fotmob_api
        self.app = self._secure_settings.application
        self.application = self._secure_settings.application
        self.security = self._secure_settings.security
        self.logging = self._secure_settings.logging
        self.ml = self._secure_settings.ml

        # 保持旧的属性名兼容性
        self.db_pool = self.database  # 向后兼容
        self.fotmob_api = self.fotmob  # 向后兼容

        logger.warning(
            "Using deprecated config.py. Please migrate to config_secure.py "
            "for enhanced security and functionality."
        )

    # 向后兼容的方法
    def get_database_url(self) -> str:
        """获取数据库连接字符串"""
        return self._secure_settings.get_database_url()

    def get_async_database_url(self) -> str:
        """获取异步数据库连接字符串"""
        return self._secure_settings.get_async_database_url()

    def get_redis_url(self) -> str:
        """获取Redis连接字符串"""
        return self._secure_settings.get_redis_url()

    def get_fotmob_headers(self) -> Dict[str, str]:
        """获取FotMob API请求头"""
        return self._secure_settings.get_fotmob_headers()

    def is_debug_mode(self) -> bool:
        """检查是否为调试模式"""
        return self._secure_settings.is_debug_enabled()

    def is_production(self) -> bool:
        """检查是否为生产环境"""
        return self._secure_settings.is_production()

    def is_development(self) -> bool:
        """检查是否为开发环境"""
        return self._secure_settings.is_development()

    def setup_logging(self) -> None:
        """设置日志配置"""
        return self._secure_settings.setup_logging()

    def summary(self) -> Dict[str, Any]:
        """获取配置摘要信息"""
        return self._secure_settings.summary()

    def get_service_url(self) -> str:
        """获取服务URL"""
        return f"http://{self.application.host}:{self.application.port}"


# 全局配置实例（向后兼容）
try:
    settings = Settings()
except Exception as e:
    logger.error(f"Failed to initialize configuration: {e}")
    raise


# 向后兼容的全局函数
def get_settings() -> Settings:
    """获取全局配置实例"""
    return settings


def reload_settings() -> Settings:
    """重新加载配置（主要用于测试）"""
    global settings
    settings = Settings()
    return settings


def get_database_url() -> str:
    """获取数据库连接字符串"""
    return settings.get_database_url()


def get_async_database_url() -> str:
    """获取异步数据库连接字符串"""
    return settings.get_async_database_url()


def get_redis_url() -> str:
    """获取Redis连接字符串"""
    return settings.get_redis_url()


def get_fotmob_headers() -> Dict[str, str]:
    """获取FotMob API请求头"""
    return settings.get_fotmob_headers()


def is_debug_mode() -> bool:
    """是否为调试模式"""
    return settings.is_debug_mode()


def is_production() -> bool:
    """是否为生产环境"""
    return settings.is_production()


def is_development() -> bool:
    """是否为开发环境"""
    return settings.is_development()


def setup_logging() -> None:
    """设置日志配置"""
    return settings.setup_logging()


def get_log_level() -> str:
    """获取日志级别"""
    return settings.logging.level


def get_service_url() -> str:
    """获取服务URL"""
    return settings.get_service_url()


def validate_configuration() -> List[str]:
    """验证配置完整性（已弃用，使用 validate_required_environment）"""
    warnings.warn(
        "validate_configuration is deprecated. Use validate_required_environment instead.",
        DeprecationWarning
    )
    try:
        validate_required_environment()
        return []
    except ConfigurationError as e:
        return [str(e)]


def print_configuration_summary() -> None:
    """打印配置摘要信息（已弃用，使用 config_secure.print_configuration_summary）"""
    warnings.warn(
        "print_configuration_summary is deprecated. Use config_secure.print_configuration_summary instead.",
        DeprecationWarning
    )
    return print_configuration_summary()


# 模块导出
__all__ = [
    "Settings",
    "ConfigurationError",
    "SecurityConfigurationError",
    "get_settings",
    "reload_settings",
    "get_database_url",
    "get_async_database_url",
    "get_redis_url",
    "get_fotmob_headers",
    "is_debug_mode",
    "is_production",
    "is_development",
    "setup_logging",
    "get_log_level",
    "get_service_url",
    "validate_configuration",
    "print_configuration_summary"
]