"""
"""







    """结构化日志格式化器"""


        """创建日志格式化器"""

from typing import Optional
import logging
import os

日志格式化器
Logging Formatters
# Import moved to top
try:
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False
class StructuredFormatter:
    def __init__(self, enable_json: bool = True):
        self.enable_json = enable_json and HAS_JSON_LOGGER
    def create_formatter(self) -> logging.Formatter:
        if self.enable_json:
            return jsonlogger.JsonFormatter(
                "%(asctime)s %(name)s %(levelname)s %(message)s",)
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            return logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )