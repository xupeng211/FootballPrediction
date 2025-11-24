#!/usr/bin/env python3
"""统一日志工具库."""

import logging
import sys


class SimpleLogger:
    """简单日志器."""

    def __init__(self, name="simple"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def info(self, message):
        self.logger.info(f"ℹ️  {message}")

    def success(self, message):
        self.logger.info(f"✅ {message}")

    def warning(self, message):
        self.logger.warning(f"⚠️  {message}")

    def error(self, message):
        self.logger.error(f"❌ {message}")


def get_logger(name=None):
    """获取日志器."""
    return SimpleLogger(name or "default")
