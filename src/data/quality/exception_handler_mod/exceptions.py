"""
数据质量异常定义模块

定义数据质量处理相关的自定义异常类。
"""


class DataQualityException(Exception):
    """数据质量异常基类"""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        """
        初始化异常

        Args:
            message: 错误消息
            error_code: 错误代码
            details: 错误详情
        """
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class MissingValueException(DataQualityException):
    """缺失值处理异常"""

    def __init__(self, message: str, table_name: str = None, column_name: str = None):
        super().__init__(message, "MISSING_VALUE_ERROR")
        self.table_name = table_name
        self.column_name = column_name


class SuspiciousOddsException(DataQualityException):
    """可疑赔率异常"""

    def __init__(self, message: str, odds_data: dict = None):
        super().__init__(message, "SUSPICIOUS_ODDS_ERROR")
        self.odds_data = odds_data or {}


class InvalidDataException(DataQualityException):
    """无效数据异常"""

    def __init__(self, message: str, table_name: str = None, record_id: int = None):
        super().__init__(message, "INVALID_DATA_ERROR")
        self.table_name = table_name
        self.record_id = record_id


class DataConsistencyException(DataQualityException):
    """数据一致性异常"""

    def __init__(self, message: str, conflict_data: dict = None):
        super().__init__(message, "DATA_CONSISTENCY_ERROR")
        self.conflict_data = conflict_data or {}


class QualityLogException(DataQualityException):
    """质量日志异常"""

    def __init__(self, message: str, log_data: dict = None):
        super().__init__(message, "QUALITY_LOG_ERROR")
        self.log_data = log_data or {}


class StatisticsQueryException(DataQualityException):
    """统计查询异常"""

    def __init__(self, message: str, query_params: dict = None):
        super().__init__(message, "STATISTICS_QUERY_ERROR")
        self.query_params = query_params or {}