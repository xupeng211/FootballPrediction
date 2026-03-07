"""
FootballPrediction V7.0 通用工具模块 - V4.45 大圆满版

V4.45: 清除幽灵导入，确立极简架构
- 移除所有不存在模块的引用
- 100% 配置驱动、0 冗余导入
"""

# V4.25: 从统一的连接池模块导入
from src.database.db_pool import (
    SyncDatabasePool as DatabaseManager,
    get_sync_db_pool as get_db_manager,
)

# V4.25: 兼容性别名
def database_connection(dict_cursor: bool = True):
    """向后兼容的数据库连接上下文管理器"""
    pool = get_db_manager()
    return pool.get_connection()

from .logger import get_logger, setup_logger

# 新增：重试装饰器
try:
    from .retry import (
        retry_db_connection,
        retry_on_connection_error,
        retry_on_timeout,
        retry_redis_connection,
        with_retry,
    )

    _HAS_RETRY = True
except ImportError:
    _HAS_RETRY = False


__all__ = [
    "DatabaseManager",
    "database_connection",
    "get_db_manager",
    "get_logger",
    "setup_logger",
]

# 如果重试装饰器可用，添加到导出列表
if _HAS_RETRY:
    __all__.extend(
        [
            "retry_db_connection",
            "retry_on_connection_error",
            "retry_on_timeout",
            "retry_redis_connection",
            "with_retry",
        ]
    )
