"""
数据访问对象(DAO)模块异常定义
Database Access Object (DAO) Module Exception Definitions

定义DAO层的专用异常类型，提供更精确的错误处理和调试信息。
"""

from typing import Optional, Any, Dict


class DAOException(Exception):
    """DAO基础异常类

    所有DAO相关异常的基类，提供统一的错误处理接口。
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于API响应"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


class DatabaseConnectionError(DAOException):
    """数据库连接异常

    当无法建立或维持数据库连接时抛出。
    """

    def __init__(self, message: str = "数据库连接失败"):
        super().__init__(message)


class RecordNotFoundError(DAOException):
    """记录未找到异常

    当查询操作未能找到预期记录时抛出。
    """

    def __init__(self, model: str, identifier: Any, message: Optional[str] = None):
        self.model = model
        self.identifier = identifier
        if not message:
            message = f"在{model}中未找到记录: {identifier}"
        details = {"model": model, "identifier": str(identifier)}
        super().__init__(message, details)


class DuplicateRecordError(DAOException):
    """重复记录异常

    当插入或更新操作违反唯一性约束时抛出。
    """

    def __init__(self, model: str, field: str, value: Any, message: Optional[str] = None):
        self.model = model
        self.field = field
        self.value = value
        if not message:
            message = f"{model}中已存在{field}为'{value}'的记录"
        details = {"model": model, "field": field, "value": str(value)}
        super().__init__(message, details)


class ValidationError(DAOException):
    """数据验证异常

    当数据不符合模型验证规则时抛出。
    """

    def __init__(self, model: str, validation_errors: Dict[str, Any], message: Optional[str] = None):
        self.model = model
        self.validation_errors = validation_errors
        if not message:
            message = f"{model}数据验证失败"
        details = {"model": model, "validation_errors": validation_errors}
        super().__init__(message, details)


class TransactionError(DAOException):
    """事务处理异常

    当事务操作（提交、回滚）失败时抛出。
    """

    def __init__(self, operation: str, message: Optional[str] = None):
        self.operation = operation
        if not message:
            message = f"事务操作失败: {operation}"
        details = {"operation": operation}
        super().__init__(message, details)


class QueryTimeoutError(DAOException):
    """查询超时异常

    当数据库操作执行超时时抛出。
    """

    def __init__(self, query: str, timeout_seconds: float, message: Optional[str] = None):
        self.query = query
        self.timeout_seconds = timeout_seconds
        if not message:
            message = f"查询执行超时 ({timeout_seconds}s): {query[:100]}..."
        details = {"query": query, "timeout_seconds": timeout_seconds}
        super().__init__(message, details)


def handle_sqlalchemy_exception(func_name: str, exc: Exception) -> DAOException:
    """SQLAlchemy异常转换工具函数

    将底层SQLAlchemy异常转换为业务友好的DAO异常。

    Args:
        func_name: 出错的函数名
        exc: SQLAlchemy原始异常

    Returns:
        转换后的DAO异常
    """
    error_message = f"{func_name}执行失败"

    exc_str = str(exc).lower()

    if "duplicate key" in exc_str or "unique constraint" in exc_str:
        return DuplicateRecordError("Unknown", "unknown", "unknown", error_message)
    elif "connection" in exc_str or "timeout" in exc_str:
        return DatabaseConnectionError(error_message)
    elif "not found" in exc_str or "no result" in exc_str:
        return RecordNotFoundError("Unknown", "unknown", error_message)
    else:
        return DAOException(error_message, {"sql_error": str(exc)}, exc)


# 导出所有异常
__all__ = [
    'DAOException',
    'DatabaseConnectionError',
    'RecordNotFoundError',
    'DuplicateRecordError',
    'ValidationError',
    'TransactionError',
    'QueryTimeoutError',
    'handle_sqlalchemy_exception'
]