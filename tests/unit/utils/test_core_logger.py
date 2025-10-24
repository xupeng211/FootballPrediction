from unittest.mock import patch, MagicMock
"""
核心日志模块测试
"""

import pytest
import logging

from src.core.logger import Logger, logger


@pytest.mark.unit

class TestLogger:
    """日志管理器测试"""

    def test_setup_logger_default_level(self):
        """测试设置默认级别的日志器"""
        test_logger = Logger.setup_logger("test_logger")

        assert isinstance(test_logger, logging.Logger)
        assert test_logger.name == "test_logger"
        assert test_logger.level == logging.INFO
        assert len(test_logger.handlers) > 0

    def test_setup_logger_custom_level(self):
        """测试设置自定义级别的日志器"""
        test_logger = Logger.setup_logger("test_debug_logger", "DEBUG")

        assert test_logger.level == logging.DEBUG

    def test_setup_logger_error_level(self):
        """测试设置错误级别的日志器"""
        test_logger = Logger.setup_logger("test_error_logger", "ERROR")

        assert test_logger.level == logging.ERROR

    def test_setup_logger_no_duplicate_handlers(self):
        """测试重复设置不会添加重复的处理器"""
        name = "test_no_duplicate"

        # 第一次创建
        logger1 = Logger.setup_logger(name)
        handler_count_1 = len(logger1.handlers)

        # 第二次创建同名日志器
        logger2 = Logger.setup_logger(name)
        handler_count_2 = len(logger2.handlers)

        assert logger1 is logger2
        assert handler_count_1 == handler_count_2

    def test_setup_logger_formatter(self):
        """测试日志器格式"""
        test_logger = Logger.setup_logger("test_formatter")
        handler = test_logger.handlers[0]
        formatter = handler.formatter

        assert isinstance(formatter, logging.Formatter)
        assert "%(asctime)s" in formatter._fmt
        assert "%(name)s" in formatter._fmt
        assert "%(levelname)s" in formatter._fmt
        assert "%(message)s" in formatter._fmt

    def test_default_logger(self):
        """测试默认日志器"""
        assert isinstance(logger, logging.Logger)
        assert logger.name == "footballprediction"
        assert logger.level == logging.INFO

    def test_logger_can_log(self):
        """测试日志器可以记录日志"""
        test_logger = Logger.setup_logger("test_can_log")

        # 使用mock来捕获日志输出
        with patch.object(test_logger.handlers[0], "stream") as mock_stream:
            mock_stream.write = MagicMock()

            test_logger.info("Test message")
            test_logger.warning("Warning message")
            test_logger.error("Error message")

            # 验证write被调用
            assert mock_stream.write.called

    @pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    def test_setup_logger_all_levels(self, level):
        """测试设置所有日志级别"""
        test_logger = Logger.setup_logger(f"test_{level.lower()}", level)
        expected_level = getattr(logging, level)
        assert test_logger.level == expected_level
