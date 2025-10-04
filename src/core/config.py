"""
足球预测系统配置管理模块

提供统一的配置读写和持久化机制。
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Pydantic compatibility logic
try:
    # Pydantic v2
    from pydantic import Field
    from pydantic_settings import BaseSettings

    HAS_PYDANTIC = True
except ImportError:
    try:
        # Pydantic v1
        from pydantic import BaseSettings, Field

        HAS_PYDANTIC = True
    except ImportError:
        HAS_PYDANTIC = False
        BaseSettings = object

        def Field(*args: Any, **kwargs: Any) -> Any:
            return None


class Config:
    """配置管理类 - 提供统一的配置读写和持久化机制"""

    def __init__(self):
        # 配置文件存储在用户主目录下，避免权限问题
        self.config_dir = Path.home() / ".footballprediction"
        self.config_file = self.config_dir / "config.json"
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件 - 自动处理文件不存在或格式错误的情况"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception as e:
                # 配置文件损坏时记录警告，但不中断程序执行
                logging.warning(f"配置文件加载失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项 - 支持默认值，确保程序健壮性"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置项 - 仅更新内存中的配置，需调用save()持久化"""
        self._config[key] = value

    def save(self) -> None:
        """保存配置到文件 - 自动创建目录，确保配置持久化"""
        # 确保配置目录存在，parents=True递归创建父目录
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            # ensure_ascii=False保证中文字符正确显示
            json.dump(self._config, f, ensure_ascii=False, indent=2)


SettingsClass = BaseSettings if HAS_PYDANTIC else object


class Settings(SettingsClass):
    """应用程序设置类 - 使用Pydantic进行配置管理和验证"""

    # 数据库配置
    database_url: str = (
        Field(
            default="sqlite+aiosqlite:///./data/football_prediction.db",
            description="数据库连接URL",
        )
        if HAS_PYDANTIC
        else "sqlite+aiosqlite:///./data/football_prediction.db"
    )
    test_database_url: str = (
        Field(
            default="postgresql+asyncpg://postgres:postgres@db:5432/football_prediction_test",
            description="测试数据库连接URL",
        )
        if HAS_PYDANTIC
        else "postgresql+asyncpg://postgres:postgres@db:5432/football_prediction_test"
    )

    # Redis配置
    redis_url: str = (
        Field(default="redis://redis:6379/0", description="Redis连接URL")
        if HAS_PYDANTIC
        else "redis://redis:6379/0"
    )

    # API配置
    api_host: str = (
        Field(default="localhost", description="API服务器主机")
        if HAS_PYDANTIC
        else "localhost"
    )
    api_port: int = (
        Field(default=8000, description="API服务器端口") if HAS_PYDANTIC else 8000
    )

    # 环境配置
    environment: str = (
        Field(default="development", description="运行环境")
        if HAS_PYDANTIC
        else "development"
    )
    log_level: str = (
        Field(default="INFO", description="日志级别") if HAS_PYDANTIC else "INFO"
    )

    # MLflow配置
    mlflow_tracking_uri: str = (
        Field(default="file:///tmp/mlflow", description="MLflow跟踪URI")
        if HAS_PYDANTIC
        else "file:///tmp/mlflow"
    )

    # 外部API配置
    api_football_key: Optional[str] = (
        Field(default=None, description="API-Football密钥") if HAS_PYDANTIC else None
    )
    api_football_url: str = (
        Field(
            default="https://api-football-v1.p.rapidapi.com/v3",
            description="API-Football基础URL",
        )
        if HAS_PYDANTIC
        else "https://api-football-v1.p.rapidapi.com/v3"
    )

    if HAS_PYDANTIC:
        # Pydantic v2 configuration
        try:
            model_config = {
                "env_file": ".env",
                "env_file_encoding": "utf-8",
                "case_sensitive": False,
                "extra": "allow",  # Allow extra fields from environment
            }
        except Exception:
            # Fallback for older versions
            class Config:
                env_file = ".env"
                env_file_encoding = "utf-8"
                case_sensitive = False
                extra = "allow"  # Allow extra fields from environment

    else:

        def __init__(self, **kwargs):
            # 设置默认值
            self.database_url = "sqlite+aiosqlite:///./data/football_prediction.db"
            self.test_database_url = "postgresql+asyncpg://postgres:postgres@db:5432/football_prediction_test"
            self.redis_url = "redis://redis:6379/0"
            self.api_host = "localhost"
            self.api_port = 8000
            self.environment = "development"
            self.log_level = "INFO"
            self.mlflow_tracking_uri = "file:///tmp/mlflow"
            self.api_football_key = None
            self.api_football_url = "https://api-football-v1.p.rapidapi.com/v3"

            # 从环境变量或kwargs更新配置
            for key, value in kwargs.items():
                setattr(self, key, value)

            # 从环境变量读取配置
            self._load_from_env()

        def _load_from_env(self):
            """从环境变量加载配置"""
            env_mapping = {
                "DATABASE_URL": "database_url",
                "TEST_DATABASE_URL": "test_database_url",
                "REDIS_URL": "redis_url",
                "API_HOST": "api_host",
                "API_PORT": "api_port",
                "ENVIRONMENT": "environment",
                "LOG_LEVEL": "log_level",
                "MLFLOW_TRACKING_URI": "mlflow_tracking_uri",
                "API_FOOTBALL_KEY": "api_football_key",
                "API_FOOTBALL_URL": "api_football_url",
            }

            for env_key, attr_name in env_mapping.items():
                env_value = os.getenv(env_key)
                if env_value is not None:
                    # 处理特殊类型
                    if attr_name == "api_port":
                        try:
                            env_value = int(env_value)
                        except ValueError:
                            continue
                    setattr(self, attr_name, env_value)


# 全局配置实例
config = Config()


# 创建全局设置实例
def get_settings() -> Settings:
    """获取应用程序设置实例"""
    return Settings()
