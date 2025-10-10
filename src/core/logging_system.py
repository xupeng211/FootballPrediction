"""
日志系统（向后兼容）
Logging System (Backward Compatible)

为了保持向后兼容性，此文件重新导出新的模块化日志系统。

Provides backward compatible exports for the modular logging system.
"""

import os

from .logging import (  # type: ignore
    # 重新导出主要类和函数
    LogLevel,
    LogCategory,
    StructuredLogger,
    LoggerManager,
    get_logger,
    log_performance,
    log_async_performance,
    log_audit,
)

# 初始化默认配置

LoggerManager.configure(
    level=LogLevel.INFO,  # type: ignore
    enable_json=os.getenv("LOG_JSON", "true").lower() == "true",
    log_dir=os.getenv("LOG_DIR", "logs"),
)

# 导出所有符号
__all__ = [
    "LogLevel",
    "LogCategory",
    "StructuredLogger",
    "LoggerManager",
    "get_logger",
    "log_performance",
    "log_async_performance",
    "log_audit",
]
