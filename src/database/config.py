from typing import Any, Dict, List, Optional, Union

"""数据库配置模块"""


import os
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """封装数据库连接配置及常用连接URL。"""

    host: str
    port: int
    database: str
    username: str
    password: Optional[str]
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800
    async_pool_size: int = 10
    async_max_overflow: int = 20
    echo: bool = False
    echo_pool: bool = False

    def _is_sqlite(self) -> bool:
        return self.database.endswith(".db") or self.database == ":memory:"

    @property
    def sync_url(self) -> str:
        if self._is_sqlite():
            if self.database == ":memory:":
                return "sqlite:///:memory:"
            return f"sqlite:///{self.database}"
        password_part = f":{self.password}" if self.password else ""
        return (
            f"postgresql+psycopg2://{self.username}{password_part}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    @property
    def async_url(self) -> str:
        if self._is_sqlite():
            if self.database == ":memory:":
                return "sqlite+aiosqlite:///:memory:"
            return f"sqlite+aiosqlite:///{self.database}"
        password_part = f":{self.password}" if self.password else ""
        return (
            f"postgresql+asyncpg://{self.username}{password_part}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    @property
    def alembic_url(self) -> str:
        return self.sync_url


_ENV_PREFIX = {
    "development": "",
    "dev": "",
    "test": "TEST_",
    "production": "PROD_",
    "prod": "PROD_",
}


def _get_env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _parse_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_database_config(environment: Optional[str] = None) -> DatabaseConfig:
    """根据环境返回数据库配置。"""

    env = (
        environment or os.getenv("ENVIRONMENT", "development") or "development"
    ).lower()
    prefix = _ENV_PREFIX.get(env, "")

    if env == "test":
        default_db = ":memory:"
    else:
        default_db = "football_prediction_dev"

    host = os.getenv(f"{prefix}DB_HOST", "localhost")
    port = _parse_int(f"{prefix}DB_PORT", 5432)
    database = os.getenv(f"{prefix}DB_NAME", default_db)
    username = os.getenv(f"{prefix}DB_USER", "football_user")

    # 数据库密码必须通过环境变量提供（测试环境除外）
    password = os.getenv(f"{prefix}DB_PASSWORD")
    if password is None and env != "test":
        raise ValueError(
            f"数据库密码未配置！请设置环境变量: {prefix}DB_PASSWORD\n"
            f"Database password not configured! Please set environment variable: {prefix}DB_PASSWORD"
        )

    pool_size = _parse_int(f"{prefix}DB_POOL_SIZE", 10)
    max_overflow = _parse_int(f"{prefix}DB_MAX_OVERFLOW", 20)
    pool_timeout = _parse_int(f"{prefix}DB_POOL_TIMEOUT", 30)
    pool_recycle = _parse_int(f"{prefix}DB_POOL_RECYCLE", 1800)
    async_pool_size = _parse_int(f"{prefix}DB_ASYNC_POOL_SIZE", pool_size)
    async_max_overflow = _parse_int(f"{prefix}DB_ASYNC_MAX_OVERFLOW", max_overflow)
    echo = _get_env_bool(f"{prefix}DB_ECHO", False)
    echo_pool = _get_env_bool(f"{prefix}DB_ECHO_POOL", False)

    return DatabaseConfig(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        async_pool_size=async_pool_size,
        async_max_overflow=async_max_overflow,
        echo=echo,
        echo_pool=echo_pool,
    )


def get_test_database_config() -> DatabaseConfig:
    """返回测试环境数据库配置。"""

    return get_database_config("test")


def get_production_database_config() -> DatabaseConfig:
    """返回生产环境数据库配置。"""

    return get_database_config("production")
