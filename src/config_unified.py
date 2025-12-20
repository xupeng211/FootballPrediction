#!/usr/bin/env python3
"""
统一配置系统 - 工业级纯净架构

合并config.py和config_secure.py的功能，提供类型安全的统一配置接口。

设计原则:
- Single Configuration Source (单一配置源)
- Type Safety First (类型安全优先)
- Environment Isolation (环境隔离)
- Validation & Defaults (验证与默认值)

配置层级:
1. Core Settings (核心设置)
2. Environment Settings (环境设置)
3. Database Settings (数据库设置)
4. Redis Settings (缓存设置)
5. External API Settings (外部API设置)
"""

import os
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Literal
from pathlib import Path
from dataclasses import dataclass, field

from pydantic import Field, validator, SecretStr
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """环境枚举"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """日志级别枚举"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseConfig:
    """数据库配置"""

    host: str
    port: int
    name: str
    user: str
    password: SecretStr
    ssl_mode: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600

    def get_connection_string(self) -> str:
        """获取连接字符串"""
        password = self.password.get_secret_value()
        if self.ssl_mode:
            return f"postgresql://{self.user}:{password}@{self.host}:{self.port}/{self.name}?sslmode=require"
        else:
            return f"postgresql://{self.user}:{password}@{self.host}:{self.port}/{self.name}"


@dataclass
class RedisConfig:
    """Redis配置"""

    host: str
    port: int
    db: int = 0
    password: Optional[SecretStr] = None
    max_connections: int = 20
    socket_timeout: int = 5
    socket_connect_timeout: int = 5

    def get_connection_string(self) -> str:
        """获取Redis连接字符串"""
        if self.password:
            password = self.password.get_secret_value()
            return f"redis://:{password}@{self.host}:{self.port}/{self.db}"
        else:
            return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class FotMobAPIConfig:
    """FotMob API配置"""

    base_url: str = "https://www.fotmob.com/api"
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        """初始化后验证"""
        if not self.headers:
            # 默认 headers
            self.headers = {
                "User-Agent": "FootballPrediction/1.0",
                "Accept": "application/json",
            }


class UnifiedSettings(BaseSettings):
    """统一设置类 - 工业级类型安全"""

    # === 环境自动检测和注入 ===
    @classmethod
    def auto_inject_env_vars(cls) -> Dict[str, Any]:
        """自动注入环境变量"""
        env_config = {}

        # 检测Docker环境
        docker_env = os.getenv("DOCKER_ENV", "").lower() in ("true", "1", "yes")
        monitoring_mode = os.getenv("MONITORING_MODE", "").lower() in ("true", "1", "yes")

        if docker_env:
            # Docker环境自动配置
            env_config.update(
                {
                    "db_host": "db",
                    "db_port": int(os.getenv("DB_PORT", 5432)),
                    "db_name": os.getenv("DB_NAME", "football_prediction"),
                    "db_user": os.getenv("DB_USER", "football_user"),
                    "db_password": os.getenv("DB_PASSWORD", "football_pass"),
                    "redis_host": os.getenv("REDIS_HOST", "redis"),
                    "redis_port": int(os.getenv("REDIS_PORT", 6379)),
                    "environment": "monitoring" if monitoring_mode else "production",
                }
            )

        # 自动注入所有FOOTBALL_前缀的环境变量
        for key, value in os.environ.items():
            if key.startswith("FOOTBALL_"):
                config_key = key[9:].lower()  # 去掉FOOTBALL_前缀并转小写
                # 特殊处理某些变量
                if config_key in ["db_host", "redis_host"] and docker_env:
                    continue  # Docker环境下保持容器名
                env_config[config_key] = value

        return env_config

    def __init__(self, **kwargs):
        # 自动注入环境变量
        auto_env = self.auto_inject_env_vars()
        # 用户传入的参数优先级更高
        auto_env.update(kwargs)
        super().__init__(**auto_env)

    # === 环境配置 ===
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="运行环境")

    debug: bool = Field(default=False, description="调试模式")

    log_level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")

    # === 应用配置 ===
    app_name: str = Field(default="Football Prediction System", description="应用名称")

    app_version: str = Field(default="1.0.0", description="应用版本")

    host: str = Field(default="0.0.0.0", description="服务监听地址")

    port: int = Field(default=8000, description="服务端口")

    workers: int = Field(default=1, description="工作进程数")

    # === 安全配置 ===
    secret_key: SecretStr = Field(default="dev-secret-key-2024-production-ready", description="应用密钥")

    allowed_hosts: List[str] = Field(default=["localhost", "127.0.0.1"], description="允许的主机列表")

    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], description="CORS允许的源"
    )

    # === 数据库配置 ===
    db_host: str = Field(default="localhost", description="数据库主机")

    db_port: int = Field(default=5432, description="数据库端口")

    db_name: str = Field(default="football_prediction", description="数据库名称")

    db_user: str = Field(default="football_user", description="数据库用户名")

    db_password: SecretStr = Field(description="数据库密码")

    db_ssl_mode: bool = Field(default=False, description="数据库SSL模式")

    db_pool_size: int = Field(default=10, description="数据库连接池大小")

    # === Redis配置 ===
    redis_host: str = Field(default="localhost", description="Redis主机")

    redis_port: int = Field(default=6379, description="Redis端口")

    redis_db: int = Field(default=0, description="Redis数据库")

    redis_password: Optional[SecretStr] = Field(default=None, description="Redis密码")

    # === 外部API配置 ===
    fotmob_base_url: str = Field(default="https://www.fotmob.com/api", description="FotMob API基础URL")

    fotmob_x_mas_header: Optional[str] = Field(default=None, description="FotMob X-MAS Header")

    fotmob_x_foo_header: Optional[str] = Field(default=None, description="FotMob X-FOO Header")

    # === 模型配置 ===
    model_path: str = Field(default="data/models/xgb_football_v2_real_scores.joblib", description="模型文件路径")

    model_version: str = Field(default="xgboost_v2", description="模型版本")

    # === 监控配置 ===
    enable_metrics: bool = Field(default=True, description="启用指标收集")

    metrics_port: int = Field(default=9090, description="指标端口")

    enable_tracing: bool = Field(default=False, description="启用链路追踪")

    # === 缓存配置 ===
    cache_ttl_seconds: int = Field(default=300, description="缓存TTL（秒）")

    cache_max_size: int = Field(default=1000, description="缓存最大条目数")

    # === 业务配置 ===
    default_confidence_threshold: float = Field(default=0.6, description="默认置信度阈值")

    max_batch_size: int = Field(default=100, description="最大批量处理大小")

    prediction_timeout_seconds: int = Field(default=30, description="预测超时时间（秒）")

    class Config:
        # 禁用.env文件自动加载，避免解析错误
        env_file = None
        env_file_encoding = "utf-8"
        case_sensitive = False

    # === 验证器 ===
    @validator("port")
    def validate_port(cls, v: int) -> int:
        """验证端口范围"""
        if not 1 <= v <= 65535:
            raise ValueError("端口必须在1-65535范围内")
        return v

    @validator("workers")
    def validate_workers(cls, v: int) -> int:
        """验证工作进程数"""
        if v < 1:
            raise ValueError("工作进程数必须大于0")
        return v

    @validator("secret_key")
    def validate_secret_key(cls, v: SecretStr) -> SecretStr:
        """验证密钥强度"""
        secret = v.get_secret_value()
        if len(secret) < 32:
            raise ValueError("密钥长度必须至少32个字符")
        return v

    @validator("default_confidence_threshold")
    def validate_confidence_threshold(cls, v: float) -> float:
        """验证置信度阈值"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("置信度阈值必须在0.0-1.0之间")
        return v

    @validator("max_batch_size")
    def validate_batch_size(cls, v: int) -> int:
        """验证批量大小"""
        if not 1 <= v <= 1000:
            raise ValueError("批量大小必须在1-1000之间")
        return v

    @validator("db_host")
    def validate_db_host(cls, v: str, values: Dict[str, Any]) -> str:
        """自动适配Docker环境的数据库主机"""
        # 检查是否在Docker环境中
        docker_env = os.getenv("DOCKER_ENV", "").lower() in ("true", "1", "yes")
        environment = values.get("environment", "development")

        # 如果明确设置了DOCKER_ENV=true，自动使用db作为主机名
        if docker_env:
            logger.info("🐳 检测到Docker环境，自动使用db作为数据库主机")
            return "db"

        # 如果在生产环境中且没有显式设置主机，使用db
        if environment in ("production", "staging") and v == "localhost":
            logger.info("🏭 生产环境，自动使用db作为数据库主机")
            return "db"

        # 否则使用原设置
        return v

    @validator("redis_host")
    def validate_redis_host(cls, v: str, values: Dict[str, Any]) -> str:
        """自动适配Docker环境的Redis主机"""
        # 检查是否在Docker环境中
        docker_env = os.getenv("DOCKER_ENV", "").lower() in ("true", "1", "yes")
        environment = values.get("environment", "development")

        # 如果明确设置了DOCKER_ENV=true，自动使用redis作为主机名
        if docker_env:
            logger.info("🐳 检测到Docker环境，自动使用redis作为Redis主机")
            return "redis"

        # 如果在生产环境中且没有显式设置主机，使用redis
        if environment in ("production", "staging") and v == "localhost":
            logger.info("🏭 生产环境，自动使用redis作为Redis主机")
            return "redis"

        # 否则使用原设置
        return v

    # === 属性方法 ===
    @property
    def database(self) -> DatabaseConfig:
        """获取数据库配置"""
        return DatabaseConfig(
            host=self.db_host,
            port=self.db_port,
            name=self.db_name,
            user=self.db_user,
            password=self.db_password,
            ssl_mode=self.db_ssl_mode,
            pool_size=self.db_pool_size,
        )

    @property
    def redis(self) -> RedisConfig:
        """获取Redis配置"""
        return RedisConfig(
            host=self.redis_host,
            port=self.redis_port,
            db=self.redis_db,
            password=self.redis_password,
        )

    @property
    def fotmob_api(self) -> FotMobAPIConfig:
        """获取FotMob API配置"""
        headers = {}
        if self.fotmob_x_mas_header:
            headers["X-MAS"] = self.fotmob_x_mas_header
        if self.fotmob_x_foo_header:
            headers["X-FOO"] = self.fotmob_x_foo_header

        return FotMobAPIConfig(
            base_url=self.fotmob_base_url,
            headers=headers,
        )

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == Environment.DEVELOPMENT

    # === 便捷方法 ===
    def get_model_path(self) -> Path:
        """获取模型文件路径"""
        return Path(self.model_path)

    def get_log_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": self.log_level.value,
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": self.log_level.value,
                    "formatter": "detailed",
                    "filename": "logs/app.log",
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                },
            },
            "root": {
                "level": self.log_level.value,
                "handlers": ["console", "file"] if not self.is_development else ["console"],
            },
        }

    def validate_integrity(self) -> List[str]:
        """验证配置完整性"""
        errors = []

        # 检查必需的配置
        if not self.secret_key.get_secret_value():
            errors.append("secret_key 不能为空")

        if not self.db_password.get_secret_value():
            errors.append("db_password 不能为空")

        # 检查路径
        if not self.get_model_path().exists():
            errors.append(f"模型文件不存在: {self.model_path}")

        # 检查环境特定的配置
        if self.is_production:
            if self.debug:
                errors.append("生产环境不应启用debug模式")
            if not self.enable_metrics:
                errors.append("生产环境应启用指标收集")
            if "localhost" in self.allowed_hosts:
                errors.append("生产环境allowed_hosts不应包含localhost")

        return errors


# === 全局设置实例 ===
_settings_instance: Optional[UnifiedSettings] = None


def get_settings() -> UnifiedSettings:
    """获取全局设置实例（单例模式）"""
    global _settings_instance
    if _settings_instance is None:
        # 简化初始化，避免环境变量解析问题
        try:
            _settings_instance = UnifiedSettings()

            # 验证配置完整性
            errors = _settings_instance.validate_integrity()
            if errors:
                logger.warning(f"配置验证警告: {'; '.join(errors)}")
        except Exception as e:
            logger.warning(f"配置初始化警告: {e}")
            # 创建最小可用配置
            _settings_instance = UnifiedSettings(
                environment=Environment.DEVELOPMENT,
                debug=True,
                secret_key=SecretStr("dev-secret-key-please-change-in-production"),
            )

    return _settings_instance


def reload_settings() -> UnifiedSettings:
    """重新加载设置"""
    global _settings_instance
    _settings_instance = None
    return get_settings()


# === 便捷函数 ===
def get_database_url() -> str:
    """获取数据库连接字符串"""
    return get_settings().database.get_connection_string()


def get_redis_url() -> str:
    """获取Redis连接字符串"""
    return get_settings().redis.get_connection_string()


def is_production() -> bool:
    """检查是否为生产环境"""
    return get_settings().is_production


def is_development() -> bool:
    """检查是否为开发环境"""
    return get_settings().is_development


# === 类型安全的配置访问器 ===
@dataclass
class ConfigAccessor:
    """类型安全的配置访问器"""

    _settings: UnifiedSettings = field(default_factory=get_settings)

    @property
    def database(self) -> DatabaseConfig:
        """获取数据库配置"""
        return self._settings.database

    @property
    def redis(self) -> RedisConfig:
        """获取Redis配置"""
        return self._settings.redis

    @property
    def fotmob_api(self) -> FotMobAPIConfig:
        """获取FotMob API配置"""
        return self._settings.fotmob_api

    def reload(self) -> None:
        """重新加载配置"""
        self._settings = reload_settings()


# 全局配置访问器（延迟初始化）
config = None


def get_config() -> ConfigAccessor:
    """获取配置访问器（延迟初始化）"""
    global config
    if config is None:
        config = ConfigAccessor()
    return config
