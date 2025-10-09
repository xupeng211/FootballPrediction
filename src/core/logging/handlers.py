"""
日志处理器
Logging Handlers
"""

import logging
import os
import sys
from typing import Optional

from .formatters import StructuredFormatter


class LogHandlerManager:
    """日志处理器管理器"""

    def __init__(self, name: str, enable_json: bool = True):
        self.name = name
        self.formatter = StructuredFormatter(enable_json).create_formatter()

    def create_console_handler(self) -> logging.StreamHandler:
        """创建控制台处理器"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.formatter)
        return handler

    def create_file_handler(self, log_file: Optional[str] = None) -> logging.FileHandler:
        """创建文件处理器"""
        if not log_file:
            log_dir = os.getenv("LOG_DIR", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"{self.name}.log")

        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(self.formatter)
        return handler