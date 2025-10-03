"""
核心模块测试
测试src/core目录下的模块
"""

import pytest
import sys
import os
import logging
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

# 导入核心模块
from src.core.exceptions import (
    FootballPredictionError,
    ValidationError,
    PredictionError,
    DatabaseError,
    ConfigError
)
from src.core.logger import Logger


class TestExceptions:
    """测试异常类"""

    def test_football_prediction_error(self):
        """测试基础异常类"""
        # 测试消息
        msg = "Test error message"
        error = FootballPredictionError(msg)
        assert str(error) == msg
        assert error.args == (msg,)

        # 测试继承
        assert isinstance(error, Exception)

    def test_data_validation_error(self):
        """测试数据验证异常"""
        msg = "Validation failed"
        error = ValidationError(msg)
        assert str(error) == msg
        assert isinstance(error, FootballPredictionError)

    def test_prediction_error(self):
        """测试预测异常"""
        msg = "Prediction failed"
        error = PredictionError(msg)
        assert str(error) == msg
        assert isinstance(error, FootballPredictionError)

    def test_database_error(self):
        """测试数据库异常"""
        msg = "Database connection failed"
        error = DatabaseError(msg)
        assert str(error) == msg
        assert isinstance(error, FootballPredictionError)

    def test_configuration_error(self):
        """测试配置异常"""
        msg = "Configuration missing"
        error = ConfigError(msg)
        assert str(error) == msg
        assert isinstance(error, FootballPredictionError)

    def test_exception_with_details(self):
        """测试带详情的异常"""
        msg = "Error occurred"
        details = {"field": "value", "code": 123}

        error = ValidationError(msg, details)
        # 异常的str()可能包含所有参数
        assert msg in str(error)
        # 可以通过属性访问详情（如果实现了的话）
        if hasattr(error, 'details'):
            assert error.details == details

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise FootballPredictionError("Wrapped error") from e
        except FootballPredictionError as e:
            assert str(e) == "Wrapped error"
            assert e.__cause__ is not None
            assert str(e.__cause__) == "Original error"


class TestLogger:
    """测试日志模块"""

    def test_get_logger(self):
        """测试获取日志器"""
        logger = Logger.setup_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_get_logger_default(self):
        """测试默认日志器"""
        logger = Logger.setup_logger("test")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test"

    def test_setup_logging_levels(self):
        """测试设置不同日志级别"""
        # 测试不同级别
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in levels:
            logger = Logger.setup_logger(f"test_{level.lower()}", level)
            assert isinstance(logger, logging.Logger)
            # 验证级别设置
            assert logger.level == getattr(logging, level)

    def test_logger_levels(self):
        """测试日志级别"""
        logger = Logger.setup_logger("test_levels")

        # 测试所有级别
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

    def test_logger_with_exception(self):
        """测试记录异常"""
        logger = Logger.setup_logger("test_exception")

        try:
            raise ValueError("Test exception")
        except ValueError as e:
            # 记录异常信息
            logger.exception("An error occurred")

    def test_logger_context(self):
        """测试日志上下文"""
        logger = Logger.setup_logger("test_context")

        # 使用额外信息
        logger.info("User action", extra={"user_id": 123, "action": "login"})

    def test_logger_formatting(self):
        """测试日志格式"""
        logger = Logger.setup_logger("test_format")

        # 测试不同格式的日志
        logger.info("User %s logged in at %s", "john", "10:00")
        logger.info("Multiple values: %s, %d, %.2f", "test", 42, 3.14)

    def test_logger_handlers(self):
        """测试日志处理器"""
        logger = Logger.setup_logger("test_handlers")

        # 添加自定义处理器
        handler = logging.StreamHandler()
        logger.addHandler(handler)

        # 验证处理器已添加
        assert handler in logger.handlers

        # 清理
        logger.removeHandler(handler)

    def test_logger_propagation(self):
        """测试日志传播"""
        logger = Logger.setup_logger("test_propagation")

        # 测试传播设置
        logger.propagate = False
        assert logger.propagate == False

        logger.propagate = True
        assert logger.propagate == True


class TestCoreModuleIntegration:
    """测试核心模块集成"""

    def test_exception_in_logger(self):
        """测试在日志中使用异常"""
        logger = Logger.setup_logger("test_exception_logger")

        try:
            # 模拟一个错误场景
            config = {}
            if "required_key" not in config:
                raise ConfigError("Missing required configuration key")
        except ConfigError as e:
            logger.error(f"Configuration error: {e}")
            # 日志应该记录了错误信息

    def test_multiple_loggers(self):
        """测试多个日志器"""
        logger1 = Logger.setup_logger("module1")
        logger2 = Logger.setup_logger("module2")

        assert logger1.name != logger2.name
        assert isinstance(logger1, logging.Logger)
        assert isinstance(logger2, logging.Logger)

    def test_logger_hierarchy(self):
        """测试日志器层次结构"""
        parent_logger = Logger.setup_logger("parent")
        child_logger = Logger.setup_logger("parent.child")

        assert child_logger.parent == parent_logger
        assert parent_logger.parent.name == "root"

    def test_custom_logger_configuration(self):
        """测试自定义日志配置"""
        with patch('logging.LoggerAdapter') as mock_adapter:
            # 模拟自定义配置
            logger = Logger.setup_logger("custom")

            # 验证可以配置自定义属性
            if hasattr(logger, 'adapter'):
                pass


class TestCoreModulePerformance:
    """测试核心模块性能"""

    def test_logger_performance(self):
        """测试日志性能"""
        import time

        logger = Logger.setup_logger("performance_test")

        # 测试大量日志记录的性能
        start_time = time.perf_counter()
        for i in range(1000):
            logger.info(f"Log message {i}")
        duration = time.perf_counter() - start_time

        # 1000条日志应该在合理时间内完成
        assert duration < 1.0  # 1秒内完成

    def test_exception_creation_performance(self):
        """测试异常创建性能"""
        import time

        start_time = time.perf_counter()
        exceptions = []
        for i in range(1000):
            exceptions.append(ValidationError(f"Error {i}"))
        duration = time.perf_counter() - start_time

        # 创建1000个异常应该很快
        assert duration < 0.1  # 100ms内完成
        assert len(exceptions) == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])