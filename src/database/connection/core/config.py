"""
数据库连接配置

定义数据库连接的重试配置和常量
"""

import os
from typing import Tuple

from src.utils.retry import RetryConfig

# 数据库重试配置 / Database retry configuration
DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=int(os.getenv("DATABASE_RETRY_MAX_ATTEMPTS", "5")),
    base_delay=float(os.getenv("DATABASE_RETRY_BASE_DELAY", "1.0")),
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=(ConnectionError, TimeoutError),
)

# 数据库连接默认配置 / Default database connection configuration
DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 20
DEFAULT_POOL_TIMEOUT = 30
DEFAULT_POOL_RECYCLE = 3600

DEFAULT_ASYNC_POOL_SIZE = 20
DEFAULT_ASYNC_MAX_OVERFLOW = 30


def get_pool_settings(
    is_async: bool = False,
    is_sqlite: bool = False
) -> Tuple[int, int, int, int]:
    """
    获取连接池设置

    Args:
        is_async: 是否为异步连接
        is_sqlite: 是否为SQLite数据库

    Returns:
        Tuple[int, int, int, int]: (pool_size, max_overflow, pool_timeout, pool_recycle)
    """
    if is_sqlite:
        # SQLite不使用连接池
        return 0, 0, 0, 0

    if is_async:
        return (
            DEFAULT_ASYNC_POOL_SIZE,
            DEFAULT_ASYNC_MAX_OVERFLOW,
            DEFAULT_POOL_TIMEOUT,
            DEFAULT_POOL_RECYCLE,
        )

    return (
        DEFAULT_POOL_SIZE,
        DEFAULT_MAX_OVERFLOW,
        DEFAULT_POOL_TIMEOUT,
        DEFAULT_POOL_RECYCLE,
    )