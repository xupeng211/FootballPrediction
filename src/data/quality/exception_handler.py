"""
数据质量异常处理机制

实现数据质量问题的自动化处理和修复策略：
1. 缺失值处理：使用历史平均值填充
2. 异常赔率处理：标记为可疑并记录
3. 错误数据处理：写入质量日志供人工排查

该文件已重构为模块化架构，原始功能现在通过以下模块提供：
- exceptions: 自定义异常类
- missing_value_handler: 缺失值处理
- suspicious_odds_handler: 可疑赔率处理
- invalid_data_handler: 无效数据处理
- quality_logger: 质量日志记录
- statistics_provider: 统计信息提供
"""

from .exception_handler_mod import (

# 为了向后兼容，从新的模块化实现重新导出所有类
    DataQualityExceptionHandler,
    MissingValueHandler,
    SuspiciousOddsHandler,
    InvalidDataHandler,
    QualityLogger,
    StatisticsProvider,
    DataQualityException,
    MissingValueException,
    SuspiciousOddsException,
    InvalidDataException,
    DataConsistencyException,
    QualityLogException,
    StatisticsQueryException,
)

# 保持原有的 __all__ 导出以维持兼容性
__all__ = [
    "DataQualityExceptionHandler",
    "MissingValueHandler",
    "SuspiciousOddsHandler",
    "InvalidDataHandler",
    "QualityLogger",
    "StatisticsProvider",
    "DataQualityException",
    "MissingValueException",
    "SuspiciousOddsException",
    "InvalidDataException",
    "DataConsistencyException",
    "QualityLogException",
    "StatisticsQueryException",
]
