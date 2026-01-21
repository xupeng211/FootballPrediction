#!/usr/bin/env python3
"""
数据库连接工厂
Database Connection Factory

提供统一的数据库连接管理，支持测试和生产环境
"""

from contextlib import contextmanager, suppress
import logging
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """数据库连接异常"""


def get_db_connection(
    host: str | None = None,
    port: int | None = None,
    database: str | None = None,
    user: str | None = None,
    password: str | None = None,
    cursor_factory: Any = RealDictCursor,
) -> psycopg2.extensions.connection:
    """
    获取数据库连接

    Args:
        host: 数据库主机，默认从配置读取
        port: 数据库端口，默认从配置读取
        database: 数据库名，默认从配置读取
        user: 用户名，默认从配置读取
        password: 密码，默认从配置读取
        cursor_factory: 游标工厂，默认RealDictCursor

    Returns:
        数据库连接对象

    Raises:
        DatabaseConnectionError: 连接失败时抛出
    """
    try:
        settings = get_settings()
        db_config = settings.database

        # 使用传入参数或默认配置
        connection_params = {
            "host": host or db_config.host,
            "port": port or db_config.port,
            "database": database or db_config.name,
            "user": user or db_config.user,
            "password": password or db_config.password.get_secret_value(),
            "cursor_factory": cursor_factory,
            "connect_timeout": 10,
            "application_name": "football_prediction",
        }

        logger.info(
            f"正在连接数据库: {connection_params['host']}:{connection_params['port']}/{connection_params['database']}"
        )

        conn = psycopg2.connect(**connection_params)

        # 设置连接参数
        conn.autocommit = False
        conn.set_client_encoding("UTF8")

        logger.info("数据库连接成功建立")
        return conn

    except psycopg2.Error as e:
        error_msg = f"数据库连接失败: {e}"
        logger.exception(error_msg)
        raise DatabaseConnectionError(error_msg) from e
    except Exception as e:
        error_msg = f"数据库配置错误: {e}"
        logger.exception(error_msg)
        raise DatabaseConnectionError(error_msg) from e


@contextmanager
def get_db_cursor(
    host: str | None = None,
    port: int | None = None,
    database: str | None = None,
    user: str | None = None,
    password: str | None = None,
):
    """
    获取数据库游标的上下文管理器

    自动管理连接和游标的生命周期

    Args:
        host: 数据库主机
        port: 数据库端口
        database: 数据库名
        user: 用户名
        password: 密码

    Yields:
        数据库游标对象
    """
    conn = None
    cursor = None

    try:
        conn = get_db_connection(host, port, database, user, password)
        cursor = conn.cursor()

        yield cursor

        # 提交事务（如果有未提交的操作）
        if not conn.closed:
            conn.commit()

    except Exception as e:
        # 发生异常时回滚
        if conn and not conn.closed:
            with suppress(Exception):
                conn.rollback()
        logger.exception(f"数据库操作失败: {e}")
        raise
    finally:
        # 清理资源
        if cursor:
            with suppress(Exception):
                cursor.close()
        if conn and not conn.closed:
            with suppress(Exception):
                conn.close()


def get_test_db_connection():
    """
    获取测试数据库连接

    使用测试专用的数据库配置

    Returns:
        测试数据库连接对象
    """
    return get_db_connection(database="football_prediction_test")  # 使用测试数据库


def test_connection():
    """
    测试数据库连接

    Returns:
        bool: 连接是否成功
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return result is not None
    except Exception as e:
        logger.exception(f"数据库连接测试失败: {e}")
        return False


def get_connection_info() -> dict[str, Any]:
    """
    获取数据库连接信息（不包含敏感信息）

    Returns:
        连接信息字典
    """
    try:
        settings = get_settings()
        db_config = settings.database

        return {
            "host": db_config.host,
            "port": db_config.port,
            "database": db_config.name,
            "user": db_config.user,
            "connection_established": test_connection(),
        }
    except Exception as e:
        return {"error": str(e), "connection_established": False}


# 向后兼容的函数名
get_connection = get_db_connection
