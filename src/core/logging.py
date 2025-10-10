"""
统一日志访问接口

提供 get_logger(name, level) 以兼容各处引用（例如监控与脚本）。
"""

import logging
from typing import Optional, cast

from .logger import Logger as _BaseLogger

# 导出 LogLevel 作为整数常量
LogLevel = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# 默认日志级别
DEFAULT_LOG_LEVEL = LogLevel["INFO"]

# 日志分类
LogCategory = {
    "SYSTEM": "system",
    "API": "api",
    "DATABASE": "database",
    "CACHE": "cache",
    "PREDICTION": "prediction",
    "COLLECTION": "collection",
    "MONITORING": "monitoring",
    "AUDIT": "audit",
}


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str, category: Optional[str] = None):
        """初始化结构化日志记录器"""
        self.logger = logging.getLogger(name)
        self.category = category or LogCategory["SYSTEM"]

    def info(self, message: str, **kwargs):
        """记录信息日志"""
        extra = {"category": self.category, **kwargs}
        self.logger.info(message, extra=extra)

    def error(self, message: str, **kwargs):
        """记录错误日志"""
        extra = {"category": self.category, **kwargs}
        self.logger.error(message, extra=extra)

    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        extra = {"category": self.category, **kwargs}
        self.logger.warning(message, extra=extra)

    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        extra = {"category": self.category, **kwargs}
        self.logger.debug(message, extra=extra)


def get_logger(name: str, level: Optional[str] = "INFO") -> logging.Logger:
    """获取指定名称的日志器。

    Args:
        name: 日志器名称（一般为 __name__）。
        level: 日志级别，默认为 "INFO"。

    Returns:
        logging.Logger: 已配置处理器与格式的日志器。
    """
    # 复用现有的标准化配置，确保输出一致
    return _BaseLogger.setup_logger(name, level or "INFO")
