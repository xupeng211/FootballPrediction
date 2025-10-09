"""
日志格式化器
Logging Formatters
"""

import logging
import os
from typing import Optional

try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False


class StructuredFormatter:
    """结构化日志格式化器"""

    def __init__(self, enable_json: bool = True):
        self.enable_json = enable_json and HAS_JSON_LOGGER

    def create_formatter(self) -> logging.Formatter:
        """创建日志格式化器"""
        if self.enable_json:
            return jsonlogger.JsonFormatter(
                "%(asctime)s %(name)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            return logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )