from __future__ import annotations

from dataclasses import dataclass
import os

from pydantic import BaseModel, Field, SecretStr, ValidationInfo, field_validator

from src.config.common import (
    ALLOWED_DB_NAME,
    MAX_PORT,
    MIN_PORT,
    MIN_SECRET_KEY_LENGTH,
    Environment,
    EnvironmentType,
    LogLevel,
    detect_environment,
    env_flag,
    env_int,
    get_optimal_db_host,
    load_dotenv_if_available,
    logger,
)
from src.core.exceptions import DatabaseConfigurationError


@dataclass
class DatabaseConfig:
    """数据库配置。"""

    host: str
    port: int
    name: str
    user: str
    password: SecretStr
    ssl_mode: bool = False
    pool_size: int = 15
    max_overflow: int = 20
    pool_timeout: int = 10
    pool_recycle: int = 600
    async_url: str | None = None
    async_pool_size: int = 15
    async_max_overflow: int = 20
    echo: bool = False
    echo_pool: bool = False

    def get_connection_string(self) -> str:
        password = self.password.get_secret_value()
        if self.ssl_mode:
            return (
                f"postgresql://{self.user}:{password}@{self.host}:{self.port}/{self.name}"
                "?sslmode=require"
            )
        return f"postgresql://{self.user}:{password}@{self.host}:{self.port}/{self.name}"

    def get_async_url(self) -> str:
        if self.async_url:
            return self.async_url

        password = self.password.get_secret_value()
        if self.ssl_mode:
            return (
                "postgresql+asyncpg://"
                f"{self.user}:{password}@{self.host}:{self.port}/{self.name}?ssl=require"
            )
        return f"postgresql+asyncpg://{self.user}:{password}@{self.host}:{self.port}/{self.name}"


@dataclass
class RedisConfig:
    """Redis 配置。"""

    host: str
    port: int
    db: int = 0
    password: SecretStr | None = None
    max_connections: int = 20
    socket_timeout: int = 5
    socket_connect_timeout: int = 5

    def get_connection_string(self) -> str:
        if self.password:
            password = self.password.get_secret_value()
            return f"redis://:{password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class DatabaseSettingsMixin(BaseModel):
    """环境、应用、安全、数据库与缓存配置。"""

    environment: Environment = Field(default=Environment.DEVELOPMENT, description="运行环境")
    debug: bool = Field(default=False, description="调试模式")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
    app_name: str = Field(default="Football Prediction System", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    host: str = Field(default="0.0.0.0", description="服务监听地址")
    port: int = Field(default=8000, description="服务端口")
    workers: int = Field(default=1, description="工作进程数")
    secret_key: SecretStr = Field(
        default=SecretStr("dev-secret-key-change-in-production-minimum-32-chars"),
        description="应用密钥（生产环境必须通过环境变量设置）",
    )
    allowed_hosts: list[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="允许的主机列表",
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="CORS允许的源",
    )
    db_host: str = Field(default="localhost", description="数据库主机")
    db_port: int = Field(default=5432, description="数据库端口")
    db_name: str = Field(default=ALLOWED_DB_NAME, description="数据库名称")
    db_user: str = Field(default="football_user", description="数据库用户名")
    db_password: SecretStr = Field(description="数据库密码")
    db_ssl_mode: bool = Field(default=False, description="数据库 SSL 模式")
    db_pool_size: int = Field(default=10, description="数据库连接池大小")
    redis_host: str = Field(default="localhost", description="Redis 主机")
    redis_port: int = Field(default=6379, description="Redis 端口")
    redis_db: int = Field(default=0, description="Redis 数据库")
    redis_password: SecretStr | None = Field(default=None, description="Redis 密码")

    @classmethod
    def auto_inject_env_vars(cls) -> dict[str, object]:
        """按环境自动补齐数据库与缓存配置。"""
        env_config: dict[str, object] = {}
        docker_env = False

        load_dotenv_if_available()

        if (
            EnvironmentType is not None
            and detect_environment is not None
            and get_optimal_db_host is not None
        ):
            current_env = detect_environment()
            monitoring_mode = env_flag("MONITORING_MODE")

            if current_env == EnvironmentType.DOCKER:
                docker_env = True
                logger.info("🐳 Docker 环境自动配置")
                env_config.update(
                    {
                        "db_host": "db",
                        "db_port": env_int("DB_PORT", 5432),
                        "db_name": os.getenv("DB_NAME", ALLOWED_DB_NAME),
                        "db_user": os.getenv("DB_USER", "football_user"),
                        "db_password": os.getenv("DB_PASSWORD", "change-me-in-production"),
                        "redis_host": os.getenv("REDIS_HOST", "redis"),
                        "redis_port": env_int("REDIS_PORT", 6379),
                        "environment": "monitoring" if monitoring_mode else "production",
                    }
                )
            elif current_env == EnvironmentType.WSL2:
                logger.info("🟡 WSL2 环境自动配置")
                env_config.update(
                    {
                        "db_host": get_optimal_db_host(os.getenv("DB_HOST"), os.getenv("PGHOST")),
                        "db_port": env_int("DB_PORT", 5432),
                        "db_name": os.getenv("DB_NAME", ALLOWED_DB_NAME),
                        "db_user": os.getenv("DB_USER", "football_user"),
                        "db_password": os.getenv("DB_PASSWORD")
                        or os.getenv("PGPASSWORD", "change-me-in-production"),
                        "redis_host": os.getenv("REDIS_HOST", "localhost"),
                        "redis_port": env_int("REDIS_PORT", 6379),
                        "environment": "development",
                    }
                )
            else:
                logger.info("🏠 本地环境自动配置")
                env_config.update(
                    {
                        "db_host": os.getenv("DB_HOST", "localhost"),
                        "db_port": env_int("DB_PORT", 5432),
                        "db_name": os.getenv("DB_NAME", ALLOWED_DB_NAME),
                        "db_user": os.getenv("DB_USER", "football_user"),
                        "db_password": os.getenv("DB_PASSWORD")
                        or os.getenv("PGPASSWORD", "change-me-in-production"),
                        "redis_host": os.getenv("REDIS_HOST", "localhost"),
                        "redis_port": env_int("REDIS_PORT", 6379),
                        "environment": "development",
                    }
                )
        else:
            logger.warning("⚠️  环境检测器未找到，使用旧版配置逻辑")
            docker_env = env_flag("DOCKER_ENV")
            monitoring_mode = env_flag("MONITORING_MODE")

            if docker_env:
                db_password = os.getenv("DB_PASSWORD")
                if not db_password:
                    logger.warning("🚨 Docker 环境检测到 DB_PASSWORD 未设置")

                env_config.update(
                    {
                        "db_host": "db",
                        "db_port": env_int("DB_PORT", 5432),
                        "db_name": os.getenv("DB_NAME", ALLOWED_DB_NAME),
                        "db_user": os.getenv("DB_USER", "football_user"),
                        "db_password": db_password or "change-me-in-production",
                        "redis_host": os.getenv("REDIS_HOST", "redis"),
                        "redis_port": env_int("REDIS_PORT", 6379),
                        "environment": "monitoring" if monitoring_mode else "production",
                    }
                )

        for key, value in os.environ.items():
            if key.startswith("FOOTBALL_"):
                config_key = key[9:].lower()
                if config_key in {"db_host", "redis_host"} and docker_env:
                    continue
                env_config[config_key] = value

        return env_config

    @field_validator("port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        if not MIN_PORT <= value <= MAX_PORT:
            raise ValueError("端口必须在 1-65535 范围内")
        return value

    @field_validator("workers")
    @classmethod
    def validate_workers(cls, value: int) -> int:
        if value < 1:
            raise ValueError("工作进程数必须大于 0")
        return value

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < MIN_SECRET_KEY_LENGTH:
            raise ValueError("密钥长度必须至少 32 个字符")
        return value

    @field_validator("db_host")
    @classmethod
    def validate_db_host(cls, value: str, info: ValidationInfo[object]) -> str:
        docker_env = env_flag("DOCKER_ENV")
        environment = (info.data or {}).get("environment", "development")

        if docker_env:
            logger.info("🐳 检测到 Docker 环境，数据库主机自动固定为 db")
            return "db"
        if environment in ("production", "staging") and value == "localhost":
            logger.info("🏭 生产态数据库主机从 localhost 自动切换到 db")
            return "db"
        return value

    @field_validator("redis_host")
    @classmethod
    def validate_redis_host(cls, value: str, info: ValidationInfo[object]) -> str:
        docker_env = env_flag("DOCKER_ENV")
        environment = (info.data or {}).get("environment", "development")

        if docker_env:
            logger.info("🐳 检测到 Docker 环境，Redis 主机自动固定为 redis")
            return "redis"
        if environment in ("production", "staging") and value == "localhost":
            logger.info("🏭 生产态 Redis 主机从 localhost 自动切换到 redis")
            return "redis"
        return value

    @field_validator("db_name")
    @classmethod
    def validate_db_name(cls, value: str) -> str:
        if value != ALLOWED_DB_NAME:
            raise DatabaseConfigurationError(
                "🚨 V41.51 数据库大一统：非法数据库名称\n"
                f"   检测到: '{value}'\n"
                f"   系统只允许: '{ALLOWED_DB_NAME}'\n"
                f"   请检查配置文件，确保 db_name={ALLOWED_DB_NAME}"
            )
        return value

    @property
    def database(self) -> DatabaseConfig:
        password = self.db_password.get_secret_value()
        if self.db_ssl_mode:
            async_url = (
                "postgresql+asyncpg://"
                f"{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}?ssl=require"
            )
        else:
            async_url = (
                "postgresql+asyncpg://"
                f"{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"
            )

        return DatabaseConfig(
            host=self.db_host,
            port=self.db_port,
            name=self.db_name,
            user=self.db_user,
            password=self.db_password,
            ssl_mode=self.db_ssl_mode,
            pool_size=self.db_pool_size,
            max_overflow=self.db_pool_size,
            pool_timeout=30,
            pool_recycle=3600,
            async_url=async_url,
            async_pool_size=self.db_pool_size,
            async_max_overflow=self.db_pool_size,
        )

    @property
    def redis(self) -> RedisConfig:
        return RedisConfig(
            host=self.redis_host,
            port=self.redis_port,
            db=self.redis_db,
            password=self.redis_password,
        )

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT


__all__ = [
    "DatabaseConfig",
    "DatabaseSettingsMixin",
    "Environment",
    "LogLevel",
    "RedisConfig",
]
