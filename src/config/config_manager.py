import os
from typing import Any

"""
配置管理器模块
Configuration Manager Module

提供统一的配置管理功能，支持环境变量和默认值。
Provides unified configuration management with environment variables and default values.
"""


class ConfigManager:
    """配置管理器."""

    def __init__(self):
        self.config: dict[str, Any] = {}
        self.load_default_config()

    def load_default_config(self):
        """加载默认配置."""
        self.config = {
            "database_url": os.getenv(
                "DATABASE_URL", "sqlite:///./football_prediction.db"
            ),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "secret_key": os.getenv("SECRET_KEY", "your-secret-key-here"),
            "debug": os.getenv("DEBUG", "False").lower() == "true",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "api_host": os.getenv("API_HOST", "0.0.0.0"),
            "api_port": int(os.getenv("API_PORT", "8000")),
        }

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值."""
        self.config[key] = value

    def reload(self) -> None:
        """重新加载配置."""
        self.load_default_config()

    @property
    def database_url(self) -> str:
        """数据库URL."""
        return self.get("database_url")

    @property
    def redis_url(self) -> str:
        """Redis URL."""
        return self.get("redis_url")

    @property
    def secret_key(self) -> str:
        """密钥."""
        return self.get("secret_key")

    @property
    def debug(self) -> bool:
        """调试模式."""
        return self.get("debug", False)

    @property
    def log_level(self) -> str:
        """日志级别."""
        return self.get("log_level", "INFO")


# 全局配置实例
CONFIG_MANAGER = ConfigManager()


def example() -> str | None:
    """示例函数."""
    return CONFIG_MANAGER.get("example_value")


# 常用配置常量
EXAMPLE = "value"

__all__ = [
    "ConfigManager",
    "CONFIG_MANAGER",
    "example",
    "EXAMPLE",
]
