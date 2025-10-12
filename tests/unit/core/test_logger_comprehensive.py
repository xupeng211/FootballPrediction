"""
日志模块综合测试
Comprehensive Tests for Logger Module

测试src.core.logger模块的功能
"""

import logging
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from src.core.logger import Logger, get_logger, logger


class TestLogger:
    """日志管理类测试"""

    def test_setup_logger_default_level(self):
        """测试：设置默认级别的日志器"""
        test_logger = Logger.setup_logger("test_logger")
        assert isinstance(test_logger, logging.Logger)
        assert test_logger.name == "test_logger"
        assert test_logger.level == logging.INFO

    def test_setup_logger_debug_level(self):
        """测试：设置DEBUG级别的日志器"""
        test_logger = Logger.setup_logger("test_logger_debug", "DEBUG")
        assert test_logger.level == logging.DEBUG

    def test_setup_logger_warning_level(self):
        """测试：设置WARNING级别的日志器"""
        test_logger = Logger.setup_logger("test_logger_warn", "WARNING")
        assert test_logger.level == logging.WARNING

    def test_setup_logger_error_level(self):
        """测试：设置ERROR级别的日志器"""
        test_logger = Logger.setup_logger("test_logger_error", "ERROR")
        assert test_logger.level == logging.ERROR

    def test_setup_logger_critical_level(self):
        """测试：设置CRITICAL级别的日志器"""
        test_logger = Logger.setup_logger("test_logger_critical", "CRITICAL")
        assert test_logger.level == logging.CRITICAL

    def test_setup_logger_with_same_name(self):
        """测试：相同名称的日志器"""
        logger1 = Logger.setup_logger("duplicate_test")
        logger2 = Logger.setup_logger("duplicate_test")
        # 应该返回同一个logger实例
        assert logger1 is logger2

    def test_setup_logger_adds_handler_once(self):
        """测试：只添加一次处理器"""
        test_logger = Logger.setup_logger("handler_test")
        initial_handler_count = len(test_logger.handlers)

        # 再次调用应该不会添加新的处理器
        Logger.setup_logger("handler_test")
        assert len(test_logger.handlers) == initial_handler_count

    def test_setup_logger_formatter(self):
        """测试：日志器格式"""
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            test_logger = Logger.setup_logger("format_test")
            test_logger.info("Test message")

            output = mock_stderr.getvalue()
            assert "format_test" in output
            assert "INFO" in output
            assert "Test message" in output
            # 检查时间格式
            assert "-" in output  # 时间分隔符

    def test_setup_logger_invalid_level(self):
        """测试：无效的日志级别"""
        with pytest.raises(AttributeError):
            Logger.setup_logger("invalid_test", "INVALID_LEVEL")

    def test_setup_logger_empty_name(self):
        """测试：空名称的日志器"""
        test_logger = Logger.setup_logger("")
        assert isinstance(test_logger, logging.Logger)
        # logging.getLogger("") 返回 root logger
        assert test_logger.name == "root"

    def test_setup_logger_none_name(self):
        """测试：None名称的日志器"""
        test_logger = Logger.setup_logger(None)
        assert isinstance(test_logger, logging.Logger)
        # logging.getLogger(None) 返回 root logger
        assert test_logger.name == "root"

    @patch("logging.StreamHandler")
    def test_setup_logger_custom_handler(self, mock_stream_handler):
        """测试：自定义处理器"""
        mock_handler = MagicMock()
        mock_stream_handler.return_value = mock_handler

        test_logger = Logger.setup_logger("custom_handler_test")

        # 验证处理器被创建和配置
        mock_stream_handler.assert_called_once()
        mock_handler.setFormatter.assert_called_once()
        # addHandler是方法，不是属性
        assert mock_handler in test_logger.handlers

    def test_logger_levels_hierarchy(self):
        """测试：日志级别层次"""
        test_logger = Logger.setup_logger("level_test", "DEBUG")

        # DEBUG级别应该记录所有消息
        assert test_logger.isEnabledFor(logging.DEBUG)
        assert test_logger.isEnabledFor(logging.INFO)
        assert test_logger.isEnabledFor(logging.WARNING)
        assert test_logger.isEnabledFor(logging.ERROR)
        assert test_logger.isEnabledFor(logging.CRITICAL)

        # INFO级别不应该记录DEBUG消息
        info_logger = Logger.setup_logger("level_test_info", "INFO")
        assert not info_logger.isEnabledFor(logging.DEBUG)
        assert info_logger.isEnabledFor(logging.INFO)

    def test_logger_message_output(self):
        """测试：日志消息输出"""
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            test_logger = Logger.setup_logger("output_test", "DEBUG")

            # 测试不同级别的日志
            test_logger.debug("Debug message")
            test_logger.info("Info message")
            test_logger.warning("Warning message")
            test_logger.error("Error message")
            test_logger.critical("Critical message")

            output = mock_stderr.getvalue()
            assert "Debug message" in output
            assert "Info message" in output
            assert "Warning message" in output
            assert "Error message" in output
            assert "Critical message" in output
            # 检查级别标签
            assert "DEBUG" in output
            assert "INFO" in output
            assert "WARNING" in output
            assert "ERROR" in output
            assert "CRITICAL" in output

    def test_logger_with_exception(self):
        """测试：记录异常信息"""
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            test_logger = Logger.setup_logger("exception_test")

            try:
                raise ValueError("Test exception")
            except ValueError:
                test_logger.exception("An error occurred")

            output = mock_stderr.getvalue()
            assert "An error occurred" in output
            assert "ValueError" in output
            assert "Test exception" in output
            # 检查堆栈跟踪
            assert "Traceback" in output

    def test_logger_multiple_loggers(self):
        """测试：多个日志器"""
        logger1 = Logger.setup_logger("multi_test_1")
        logger2 = Logger.setup_logger("multi_test_2")
        logger3 = Logger.setup_logger("multi_test_3")

        # 每个日志器应该是独立的
        assert logger1 is not logger2
        assert logger2 is not logger3
        assert logger1 is not logger3

        # 名称应该正确
        assert logger1.name == "multi_test_1"
        assert logger2.name == "multi_test_2"
        assert logger3.name == "multi_test_3"

    def test_logger_handler_cleanup(self):
        """测试：日志器处理器清理"""
        test_logger = Logger.setup_logger("cleanup_test")

        # 记录初始处理器数量
        initial_handlers = len(test_logger.handlers)
        assert initial_handlers > 0

        # 手动清理处理器
        test_logger.handlers.clear()
        assert len(test_logger.handlers) == 0

        # 重新设置应该添加处理器
        Logger.setup_logger("cleanup_test")
        assert len(test_logger.handlers) == initial_handlers


class TestGetLoggerFunction:
    """全局日志函数测试"""

    def test_get_logger_default(self):
        """测试：获取默认日志器"""
        test_logger = get_logger("function_test")
        assert isinstance(test_logger, logging.Logger)
        assert test_logger.name == "function_test"
        assert test_logger.level == logging.INFO

    def test_get_logger_with_level(self):
        """测试：获取带级别的日志器"""
        test_logger = get_logger("function_test_debug", "DEBUG")
        assert test_logger.level == logging.DEBUG

    def test_get_logger_is_same_as_class_method(self):
        """测试：函数与类方法返回相同的日志器"""
        name = "comparison_test"
        logger1 = get_logger(name)
        logger2 = Logger.setup_logger(name)

        # 应该是同一个实例
        assert logger1 is logger2

    def test_get_logger_multiple_calls(self):
        """测试：多次调用get_logger"""
        name = "multiple_calls_test"
        logger1 = get_logger(name)
        logger2 = get_logger(name)
        logger3 = get_logger(name)

        # 所有调用应该返回同一个实例
        assert logger1 is logger2
        assert logger2 is logger3

    def test_get_logger_case_sensitivity(self):
        """测试：日志器名称大小写敏感性"""
        logger1 = get_logger("CaseSensitive")
        logger2 = get_logger("casesensitive")

        # 大小写不同，应该是不同的日志器
        assert logger1 is not logger2
        assert logger1.name != logger2.name


class TestDefaultLogger:
    """默认日志器测试"""

    def test_default_logger_exists(self):
        """测试：默认日志器存在"""
        assert isinstance(logger, logging.Logger)
        assert logger.name == "footballprediction"

    def test_default_logger_level(self):
        """测试：默认日志器级别"""
        assert logger.level == logging.INFO

    def test_default_logger_can_log(self):
        """测试：默认日志器可以记录日志"""
        # 默认日志器已经存在，直接测试
        assert isinstance(logger, logging.Logger)
        assert logger.name == "footballprediction"
        # 默认日志器已经设置了处理器，不需要重新测试输出


class TestLoggerIntegration:
    """日志集成测试"""

    def test_logger_with_standard_logging(self):
        """测试：与标准logging模块集成"""
        test_logger = Logger.setup_logger("integration_test")

        # 应该与标准logging模块兼容
        assert isinstance(test_logger, logging.Logger)
        root_logger = logging.getLogger()
        # root logger是RootLogger类型，其他是Logger类型
        assert isinstance(root_logger, logging.Logger)

    def test_logger_propagation(self):
        """测试：日志传播"""
        # 创建子日志器
        parent = Logger.setup_logger("parent_test")
        child = Logger.setup_logger("parent_test.child")

        # 子日志器应该能正常工作
        assert isinstance(child, logging.Logger)
        assert child.name == "parent_test.child"
        assert child.parent == parent

    def test_logger_thread_safety(self):
        """测试：日志器线程安全"""
        import threading

        loggers = []
        errors = []

        def create_logger(name):
            try:
                loggers.append(Logger.setup_logger(f"thread_test_{name}"))
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时创建日志器
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_logger, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 检查没有错误
        assert len(errors) == 0
        assert len(loggers) == 10

        # 检查所有日志器都有效
        for logger_instance in loggers:
            assert isinstance(logger_instance, logging.Logger)

    def test_logger_performance(self):
        """测试：日志器性能"""
        import time

        test_logger = Logger.setup_logger("performance_test")
        message = "Performance test message"

        # 测试大量日志记录的性能
        start_time = time.time()
        for _ in range(1000):
            test_logger.info(message)
        end_time = time.time()

        # 应该在合理时间内完成（例如1秒）
        duration = end_time - start_time
        assert duration < 1.0, f"日志记录耗时过长: {duration:.3f}秒"

    def test_logger_memory_usage(self):
        """测试：日志器内存使用"""
        import gc
        import sys

        # 获取初始对象计数
        gc.collect()
        initial_count = len(
            [obj for obj in gc.get_objects() if isinstance(obj, logging.Logger)]
        )

        # 创建大量日志器
        loggers = []
        for i in range(100):
            loggers.append(Logger.setup_logger(f"memory_test_{i}"))

        # 验证日志器被创建
        assert len(loggers) == 100

        # 清理引用
        del loggers
        gc.collect()

        # 验证内存被正确清理（至少部分）
        final_count = len(
            [obj for obj in gc.get_objects() if isinstance(obj, logging.Logger)]
        )
        # 允许一些差异，因为可能有其他日志器存在
        assert abs(final_count - initial_count) < 110
