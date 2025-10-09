"""
数据质量异常处理模块

提供模块化的数据质量异常处理功能，包括：
- 缺失值处理
- 可疑赔率检测
- 无效数据处理
- 质量日志记录
- 统计信息提供
"""

# 导入核心类
from .exception_handler import DataQualityExceptionHandler

# 导入子模块处理器
from .missing_value_handler import MissingValueHandler
from .suspicious_odds_handler import SuspiciousOddsHandler
from .invalid_data_handler import InvalidDataHandler
from .quality_logger import QualityLogger
from .statistics_provider import StatisticsProvider

# 导入异常类
from .exceptions import (
    DataQualityException,
    MissingValueException,
    SuspiciousOddsException,
    InvalidDataException,
    DataConsistencyException,
    QualityLogException,
    StatisticsQueryException,
)

# 导出所有公共接口
__all__ = [
    # 核心类
    "DataQualityExceptionHandler",

    # 子模块处理器
    "MissingValueHandler",
    "SuspiciousOddsHandler",
    "InvalidDataHandler",
    "QualityLogger",
    "StatisticsProvider",

    # 异常类
    "DataQualityException",
    "MissingValueException",
    "SuspiciousOddsException",
    "InvalidDataException",
    "DataConsistencyException",
    "QualityLogException",
    "StatisticsQueryException",
]

# 版本信息
__version__ = "1.0.0"