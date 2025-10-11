"""
数据库异常模块
Database Exceptions Module

定义数据库相关的异常类。
"""

from typing import Optional, Any, Dict


class DatabaseError(Exception):
    """数据库错误基类"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """初始化数据库错误

        Args:
            message: 错误消息
            error_code: 错误代码
            details: 错误详情
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            Dict[str, Any]: 错误信息字典
        """
        return {
            "error": "DatabaseError",
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


class ConnectionError(DatabaseError):
    """连接错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="CONNECTION_ERROR", **kwargs)


class QueryError(DatabaseError):
    """查询错误"""

    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="QUERY_ERROR", **kwargs)
        self.query = query


class TransactionError(DatabaseError):
    """事务错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="TRANSACTION_ERROR", **kwargs)


class PoolError(DatabaseError):
    """连接池错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="POOL_ERROR", **kwargs)


class MigrationError(DatabaseError):
    """迁移错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="MIGRATION_ERROR", **kwargs)


class IntegrityError(DatabaseError):
    """完整性错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="INTEGRITY_ERROR", **kwargs)
