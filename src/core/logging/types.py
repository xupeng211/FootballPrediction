"""
"""



    """日志级别"""


    """日志类别"""

from enum import Enum

日志类型定义
Logging Type Definitions
class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
class LogCategory(Enum):
    API = "api"
    PREDICTION = "prediction"
    DATA_COLLECTION = "data_collection"
    CACHE = "cache"
    DATABASE = "database"
    MODEL = "model"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    SECURITY = "security"