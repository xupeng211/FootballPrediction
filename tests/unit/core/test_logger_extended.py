"""日志模块扩展测试"""

import pytest
import logging
from unittest.mock import patch, MagicMock

from src.core.logger import Logger


class TestLoggerExtended:
    """日志模块扩展测试"""

    def test_setup_logger_default(self):
        """测试默认日志设置"""
        logger = Logger.setup_logger("test")

        assert logger is not None
        assert logger.name == "test"
        assert logger.level == logging.INFO

    def test_setup_logger_custom_level(self):
        """测试自定义日志级别"""
        logger = Logger.setup_logger("test", "DEBUG")

        assert logger.level == logging.DEBUG

    def test_setup_logger_custom_name(self):
        """测试自定义日志器名称"""
        logger = Logger.setup_logger("test_logger")

        assert logger.name == "test_logger"

    def test_get_logger_same_name(self):
        """测试获取相同名称的日志器返回同一实例"""
        logger1 = logging.getLogger("test")
        logger2 = logging.getLogger("test")

        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """测试获取不同名称的日志器返回不同实例"""
        logger1 = logging.getLogger("test1")
        logger2 = logging.getLogger("test2")

        assert logger1 is not logger2
        assert logger1.name == "test1"
        assert logger2.name == "test2"

    def test_logger_no_duplicate_handlers(self):
        """测试不重复添加处理器"""
        logger = Logger.setup_logger("test_no_duplicate")

        # 第一次设置应该添加处理器
        initial_handlers = len(logger.handlers)

        # 第二次设置不应该添加新处理器
        logger2 = Logger.setup_logger("test_no_duplicate")

        assert len(logger2.handlers) == initial_handlers
        assert logger is logger2

    def test_logger_format(self):
        """测试日志格式"""
        logger = Logger.setup_logger("test_format")

        # 检查是否有格式化器
        if logger.handlers:
            handler = logger.handlers[0]
            assert handler.formatter is not None
            assert "%(asctime)s" in handler.formatter._fmt
            assert "%(name)s" in handler.formatter._fmt
            assert "%(levelname)s" in handler.formatter._fmt
            assert "%(message)s" in handler.formatter._fmt