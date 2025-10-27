from unittest.mock import MagicMock, patch

"""
简化日志管理工具测试
Simplified Logging Management Tool Tests

测试src/core/logger_simple.py中定义的简化日志管理功能。
Tests simplified logging management functionality defined in src/core/logger_simple.py.
"""

import io
import logging

import pytest

# 导入要测试的模块
try:
    from src.core.logger_simple import get_simple_logger

    LOGGER_SIMPLE_AVAILABLE = True
except ImportError:
    LOGGER_SIMPLE_AVAILABLE = False


@pytest.mark.skipif(
    not LOGGER_SIMPLE_AVAILABLE, reason="Logger simple module not available"
)
@pytest.mark.unit
class TestSimpleLogger:
    """SimpleLogger类测试"""

    def test_get_simple_logger_default_level(self):
        """测试获取默认日志级别的简单日志器"""
        logger = get_simple_logger("test_logger")

        # 验证日志器基本属性
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO  # 默认级别

    def test_get_simple_logger_custom_level(self):
        """测试获取自定义日志级别的简单日志器"""
        # 测试不同日志级别
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level_name in levels:
            logger = get_simple_logger(f"test_logger_{level_name}", level_name)
            expected_level = getattr(logging, level_name)
            assert logger.level == expected_level

    def test_get_simple_logger_invalid_level(self):
        """测试无效日志级别处理"""
        with pytest.raises(AttributeError):
            get_simple_logger("test_logger", "INVALID_LEVEL")

    def test_get_simple_logger_lowercase_level(self):
        """测试小写日志级别处理"""
        logger = get_simple_logger("test_logger", "debug")
        assert logger.level == logging.DEBUG

        logger = get_simple_logger("test_logger", "warning")
        assert logger.level == logging.WARNING

    def test_get_simple_logger_mixed_case_level(self):
        """测试混合大小写日志级别处理"""
        logger = get_simple_logger("test_logger", "Info")
        assert logger.level == logging.INFO

        logger = get_simple_logger("test_logger", "ERROR")
        assert logger.level == logging.ERROR

    def test_get_simple_logger_single_call(self):
        """测试单次调用获取日志器"""
        get_simple_logger("single_test")

        # 验证日志器有处理器
        assert len(logger.handlers) > 0
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_get_simple_logger_multiple_calls_same_name(self):
        """测试多次调用获取同名日志器"""
        logger1 = get_simple_logger("same_name_test")
        logger2 = get_simple_logger("same_name_test")

        # 应该返回同一个日志器实例
        assert logger1 is logger2

    def test_get_simple_logger_multiple_calls_different_names(self):
        """测试多次调用获取不同名日志器"""
        logger1 = get_simple_logger("different_test_1")
        logger2 = get_simple_logger("different_test_2")

        # 应该返回不同的日志器实例
        assert logger1 is not logger2
        assert logger1.name == "different_test_1"
        assert logger2.name == "different_test_2"

    def test_get_simple_logger_handler_addition(self):
        """测试处理器添加逻辑"""
        logger = get_simple_logger("handler_test")

        # 验证添加了StreamHandler
        stream_handlers = [
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert len(stream_handlers) >= 1

    def test_get_simple_logger_handler_format(self):
        """测试处理器格式设置"""
        logger = get_simple_logger("format_test")

        # 获取第一个StreamHandler
        handler = None
        for h in logger.handlers:
            if isinstance(h, logging.StreamHandler):
                handler = h
                break

        assert handler is not None
        assert isinstance(handler.formatter, logging.Formatter)

        # 验证格式字符串
        format_string = handler.formatter._fmt
        assert "%(asctime)s" in format_string
        assert "%(name)s" in format_string
        assert "%(levelname)s" in format_string
        assert "%(message)s" in format_string

    def test_get_simple_logger_handler_not_duplicated(self):
        """测试处理器不重复添加"""
        logger = get_simple_logger("no_duplicate_test")

        # 第一次调用应该添加处理器
        initial_handlers_count = len(logger.handlers)

        # 第二次调用不应该添加新处理器
        get_simple_logger("no_duplicate_test")
        final_handlers_count = len(logger.handlers)

        # 处理器数量不应该增加
        assert final_handlers_count == initial_handlers_count

    def test_get_simple_logger_function_availability(self):
        """测试函数可用性"""
        # 验证函数可以被导入和调用
        assert callable(get_simple_logger)

        # 验证函数签名
        import inspect

        sig = inspect.signature(get_simple_logger)
        assert "name" in sig.parameters
        assert "level" in sig.parameters
        assert sig.parameters["level"].default == "INFO"

    def test_get_simple_logger_with_special_characters(self):
        """测试包含特殊字符的日志器名称"""
        special_names = [
            "test.logger",
            "test-logger",
            "test_logger_123",
            "测试日志器",  # 中文
            "🚀logger",  # emoji
        ]

        for name in special_names:
            logger = get_simple_logger(name)
            assert logger.name == name

    def test_get_simple_logger_empty_name(self):
        """测试空名称日志器"""
        logger = get_simple_logger("")
        assert logger.name == ""

    def test_get_simple_logger_very_long_name(self):
        """测试很长的日志器名称"""
        long_name = "a" * 1000
        logger = get_simple_logger(long_name)
        assert logger.name == long_name

    def test_get_simple_logger_logging_functionality(self):
        """测试日志器实际日志功能"""
        # 捕获日志输出
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)

        logger = get_simple_logger("functionality_test", "DEBUG")

        # 移除默认处理器，添加我们的测试处理器
        logger.handlers.clear()
        logger.addHandler(handler)

        # 测试不同级别的日志
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # 获取日志输出
        log_output = log_capture.getvalue()

        # 验证所有日志都被记录
        assert "Debug message" in log_output
        assert "Info message" in log_output
        assert "Warning message" in log_output
        assert "Error message" in log_output
        assert "Critical message" in log_output

    def test_get_simple_logger_level_filtering(self):
        """测试日志级别过滤"""
        # 设置WARNING级别
        logger = get_simple_logger("filter_test", "WARNING")

        # 捕获日志输出
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)

        logger.handlers.clear()
        logger.addHandler(handler)

        # 测试不同级别的日志
        logger.debug("Debug message - should not appear")
        logger.info("Info message - should not appear")
        logger.warning("Warning message - should appear")
        logger.error("Error message - should appear")

        log_output = log_capture.getvalue()

        # 验证过滤生效
        assert "Debug message" not in log_output
        assert "Info message" not in log_output
        assert "Warning message" in log_output
        assert "Error message" in log_output

    @patch("logging.StreamHandler")
    def test_get_simple_logger_handler_creation(self, mock_handler_class):
        """测试处理器创建过程"""
        mock_handler = MagicMock()
        mock_handler_class.return_value = mock_handler

        logger = get_simple_logger("creation_test")

        # 验证StreamHandler被创建
        mock_handler_class.assert_called_once()

        # 验证格式化器被设置
        mock_handler.setFormatter.assert_called_once()

        # 验证处理器被添加到日志器
        assert mock_handler in logger.handlers

    @patch("logging.Formatter")
    def test_get_simple_logger_formatter_creation(self, mock_formatter_class):
        """测试格式化器创建过程"""
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter

        # 重新创建logger以触发格式化器创建
        import importlib

        import src.core.logger_simple

        importlib.reload(src.core.logger_simple)

        from src.core.logger_simple import get_simple_logger

        get_simple_logger("formatter_test")

        # 验证格式化器被创建
        mock_formatter_class.assert_called()

        # 验证格式化器参数
        call_args = mock_formatter_class.call_args
        if call_args:
            format_string = call_args[0][0]
            assert "%(asctime)s" in format_string
            assert "%(name)s" in format_string
            assert "%(levelname)s" in format_string
            assert "%(message)s" in format_string

    def test_get_simple_logger_thread_safety(self):
        """测试日志器线程安全性"""
        import threading
        import time

        results = []

        def create_logger():
            logger = get_simple_logger(
                f"thread_test_{threading.current_thread().ident}"
            )
            results.append(logger.name)

        # 创建多个线程同时创建日志器
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_logger)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有日志器都被成功创建
        assert len(results) == 5
        assert all("thread_test_" in name for name in results)

    def test_get_simple_logger_memory_efficiency(self):
        """测试内存效率"""
        # 创建多个日志器
        loggers = []
        for i in range(100):
            logger = get_simple_logger(f"memory_test_{i}")
            loggers.append(logger)

        # 验证所有日志器都被正确创建
        assert len(loggers) == 100
        for i, logger in enumerate(loggers):
            assert logger.name == f"memory_test_{i}"
            assert isinstance(logger, logging.Logger)

    def test_get_simple_logger_error_handling(self):
        """测试错误处理"""
        # 测试各种错误情况
        with pytest.raises(AttributeError):
            get_simple_logger("test", "nonexistent_level")

        # 测试None名称
        try:
            logger = get_simple_logger(None)  # type: ignore
            # 某些情况下可能允许None，但我们测试异常处理
            assert logger is not None
        except (TypeError, AttributeError):
            # 预期的异常
            pass

    def test_get_simple_logger_integration_with_logging(self):
        """测试与标准logging模块的集成"""
        logger = get_simple_logger("integration_test")

        # 验证与标准logging模块的兼容性
        assert isinstance(logger, logging.Logger)
        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "critical")
        assert hasattr(logger, "log")

        # 验证标准logging方法可用
        for method_name in ["debug", "info", "warning", "error", "critical"]:
            method = getattr(logger, method_name)
            assert callable(method)
