"""
日志类型定义
Logging Type Definitions
"""

from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日志类别"""
    API = "api"
    PREDICTION = "prediction"
    DATA_COLLECTION = "data_collection"
    CACHE = "cache"
    DATABASE = "database"
    MODEL = "model"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    SECURITY = "security"