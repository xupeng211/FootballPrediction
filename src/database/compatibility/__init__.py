"""
src/database/compatibility 模块
统一导出接口
"""

# 导入兼容性函数
try:
    from ..compatibility import get_async_db_session, get_db_session
except ImportError:
    # 如果导入失败，创建占位符函数
    def get_async_db_session():
        raise NotImplementedError("get_async_db_session not implemented")

    def get_db_session():
        raise NotImplementedError("get_db_session not implemented")


# 导出所有函数
__all__ = ["get_async_db_session", "get_db_session"]
