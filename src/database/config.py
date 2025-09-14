"""
数据库配置模块

提供PostgreSQL数据库连接配置管理，支持开发、测试和生产环境。
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """数据库配置类"""

    # 数据库连接参数
    host: str
    port: int
    database: str
    username: str
    password: str

    # 连接池配置
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600  # 1小时

    # 异步连接配置
    async_pool_size: int = 20
    async_max_overflow: int = 30

    # 其他配置
    echo: bool = False
    echo_pool: bool = False

    @property
    def sync_url(self) -> str:
        """同步数据库连接URL"""
        # 检查是否为SQLite数据库
        if self.database.endswith(".db") or self.database == ":memory:":
            if self.database == ":memory:":
                return "sqlite+aiosqlite:///:memory:"
            return f"sqlite+aiosqlite:///{self.database}"
        return f"postgresql+psycopg2://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def async_url(self) -> str:
        """异步数据库连接URL"""
        # 检查是否为SQLite数据库
        if self.database.endswith(".db") or self.database == ":memory:":
            if self.database == ":memory:":
                return "sqlite+aiosqlite:///:memory:"
            return f"sqlite+aiosqlite:///{self.database}"
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def alembic_url(self) -> str:
        """Alembic迁移使用的数据库连接URL（使用同步驱动）"""
        # 检查是否为SQLite数据库
        if self.database.endswith(".db") or self.database == ":memory:":
            if self.database == ":memory:":
                return "sqlite:///:memory:"
            return f"sqlite:///{self.database}"
        return self.sync_url


def get_database_config(environment: Optional[str] = None) -> DatabaseConfig:
    """
    获取数据库配置

    Args:
        environment: 环境名称，如果为None则从环境变量获取

    Returns:
        DatabaseConfig: 数据库配置对象
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    # 环境变量前缀映射
    env_prefix_map = {"development": "", "test": "TEST_", "production": "PROD_"}

    prefix = env_prefix_map.get(environment, "")

    # 测试环境默认使用内存SQLite
    if environment == "test":
        database = os.getenv(f"{prefix}DB_NAME", ":memory:")
        host = "localhost"
        port = 0
        username = "test"
        password = "test"
    else:
        # 从环境变量读取配置
        host = os.getenv(f"{prefix}DB_HOST", "localhost")
        port = int(os.getenv(f"{prefix}DB_PORT", "5432"))
        database = os.getenv(f"{prefix}DB_NAME", "football_prediction_dev")
        username = os.getenv(f"{prefix}DB_USER", "football_user")
        password = os.getenv(f"{prefix}DB_PASSWORD", "football_pass")

    # 连接池配置
    pool_size = int(os.getenv(f"{prefix}DB_POOL_SIZE", "5"))
    max_overflow = int(os.getenv(f"{prefix}DB_MAX_OVERFLOW", "10"))

    # 调试配置
    echo = os.getenv(f"{prefix}DB_ECHO", "false").lower() == "true"
    echo_pool = os.getenv(f"{prefix}DB_ECHO_POOL", "false").lower() == "true"

    return DatabaseConfig(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        pool_size=pool_size,
        max_overflow=max_overflow,
        echo=echo,
        echo_pool=echo_pool,
    )


def get_test_database_config() -> DatabaseConfig:
    """
    获取测试数据库配置

    Returns:
        DatabaseConfig: 测试数据库配置
    """
    return get_database_config("test")


def get_production_database_config() -> DatabaseConfig:
    """
    获取生产数据库配置

    Returns:
        DatabaseConfig: 生产数据库配置
    """
    return get_database_config("production")
