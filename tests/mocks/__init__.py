"""
高性能 Mock 模块
提供预配置的高性能 Mock 对象
"""

# 导出常用的 mock 对象
from .fast_mocks import (
    FastDatabaseManager,
    FastRedisManager,
    FastAsyncSession,
    FastHTTPClient
)

__all__ = [
    'FastDatabaseManager',
    'FastRedisManager',
    'FastAsyncSession',
    'FastHTTPClient'
]