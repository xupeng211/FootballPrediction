"""
数据库配置
Database Configuration

定义数据库连接配置类。
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """
    数据库配置类 / Database Configuration Class

    存储数据库连接的配置信息。
    Stores database connection configuration information.

    Attributes:
        host (str): 数据库主机地址 / Database host address
        port (int): 数据库端口 / Database port
        database (str): 数据库名称 / Database name
        username (str): 用户名 / Username
        password (str): 密码 / Password
        driver (str): 驱动名称 / Driver name
        ssl_mode (str): SSL模式 / SSL mode
        timezone (str): 时区 / Timezone
    """

    host: str
    port: int
    database: str
    username: str
    password: str
    driver: str = "postgresql"
    ssl_mode: str = "prefer"
    timezone: str = "UTC"

    def get_sync_url(self) -> str:
        """
        获取同步连接URL / Get Synchronous Connection URL

        Returns:
            str: 同步连接URL / Synchronous connection URL
        """
        return (
            f"{self.driver}://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    def get_async_url(self) -> str:
        """
        获取异步连接URL / Get Asynchronous Connection URL

        Returns:
            str: 异步连接URL / Asynchronous connection URL
        """
        return (
            f"{self.driver}+asyncpg://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


def get_database_config() -> DatabaseConfig:
    """
    从环境变量获取数据库配置 / Get Database Configuration from Environment Variables

    Returns:
        DatabaseConfig: 数据库配置对象 / Database configuration object
    """
    return DatabaseConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "football_prediction"),
        username=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        driver=os.getenv("DB_DRIVER", "postgresql"),
        ssl_mode=os.getenv("DB_SSL_MODE", "prefer"),
        timezone=os.getenv("DB_TIMEZONE", "UTC"),
    )
