from unittest.mock import patch, MagicMock
"""
测试拆分后的日志系统
Test Split Logging System
"""

import pytest


# 测试导入
@pytest.mark.unit
@pytest.mark.critical

def test_import_logging_types():
    """测试能否正常导入日志类型"""
    from src.core.logging import LogLevel, LogCategory

    assert LogLevel is not None
    assert LogCategory is not None
    assert LogLevel.DEBUG.value == "DEBUG"
    assert LogCategory.API.value == "api"


def test_import_structured_logger():
    """测试能否正常导入结构化日志器"""
    from src.core.logging import StructuredLogger

    assert StructuredLogger is not None


def test_import_logger_manager():
    """测试能否正常导入日志管理器"""
    from src.core.logging import LoggerManager, get_logger

    assert LoggerManager is not None
    assert get_logger is not None


def test_import_decorators():
    """测试能否正常导入日志装饰器"""
    from src.core.logging import log_performance, log_async_performance, log_audit

    assert log_performance is not None
    assert log_async_performance is not None
    assert log_audit is not None


def test_import_formatters():
    """测试能否正常导入格式化器"""
    from src.core.logging.formatters import StructuredFormatter

    assert StructuredFormatter is not None


def test_import_handlers():
    """测试能否正常导入处理器"""
    from src.core.logging.handlers import LogHandlerManager

    assert LogHandlerManager is not None


# 测试结构化日志器
def test_structured_logger_creation():
    """测试创建结构化日志器"""
    from src.core.logging import StructuredLogger, LogLevel, LogCategory

    logger = StructuredLogger(
        name="test_logger",
        category=LogCategory.TEST if hasattr(LogCategory, "TEST") else LogCategory.API,
        level=LogLevel.DEBUG,
        enable_json=False,
        enable_console=False,
        enable_file=False,
    )

    assert logger.name == "test_logger"
    assert logger.logger.level == 10  # DEBUG level


# 测试日志管理器
def test_logger_manager_configure():
    """测试日志管理器配置"""
    from src.core.logging import LoggerManager, LogLevel

    LoggerManager.configure(
        level=LogLevel.WARNING, enable_json=False, log_dir="/tmp/test_logs"
    )

    assert LoggerManager._config["level"] == LogLevel.WARNING
    assert LoggerManager._config["enable_json"] is False
    assert LoggerManager._config["log_dir"] == "/tmp/test_logs"


def test_logger_manager_get_logger():
    """测试从日志管理器获取日志器"""
    from src.core.logging import LoggerManager, LogCategory

    logger = LoggerManager.get_logger("test_manager", LogCategory.DATABASE)

    assert logger.name == "test_manager"
    assert logger.category == LogCategory.DATABASE


# 测试装饰器
def test_performance_decorator():
    """测试性能监控装饰器"""
    from src.core.logging import log_performance, LogCategory

    @log_performance("test_operation")
    def test_function():
        return "test_result"

    _result = test_function()
    assert _result == "test_result"


def test_audit_decorator():
    """测试审计日志装饰器"""
    from src.core.logging import log_audit

    @log_audit("test_action")
    def test_function():
        return "test_result"

    _result = test_function()
    assert _result == "test_result"


# 测试向后兼容性
def test_backward_compatibility_import():
    """测试向后兼容的导入"""
    from src.core.logging_system import (
        LogLevel,
        LogCategory,
        StructuredLogger,
        LoggerManager,
        get_logger,
        log_performance,
        log_async_performance,
        log_audit,
    )

    assert LogLevel is not None
    assert LogCategory is not None
    assert StructuredLogger is not None
    assert LoggerManager is not None
    assert get_logger is not None
    assert log_performance is not None
    assert log_async_performance is not None
    assert log_audit is not None


def test_backward_compatibility_get_logger():
    """测试向后兼容的获取日志器"""
    from src.core.logging_system import get_logger, LogCategory

    logger = get_logger("test_compat", LogCategory.API)

    assert logger is not None
    assert logger.name == "test_compat"
    assert logger.category == LogCategory.API


# 测试格式化器
def test_structured_formatter():
    """测试结构化格式化器"""
    from src.core.logging.formatters import StructuredFormatter

    # 测试启用JSON
    formatter = StructuredFormatter(enable_json=True)
    assert formatter.enable_json is True

    # 测试禁用JSON
    formatter = StructuredFormatter(enable_json=False)
    assert formatter.enable_json is False


# 测试处理器
def test_log_handler_manager():
    """测试日志处理器管理器"""
    from src.core.logging.handlers import LogHandlerManager

    handler_manager = LogHandlerManager("test_handler")

    # 测试创建控制台处理器
    console_handler = handler_manager.create_console_handler()
    assert console_handler is not None

    # 测试创建文件处理器
    file_handler = handler_manager.create_file_handler("/tmp/test.log")
    assert file_handler is not None


# 测试日志方法
@patch("os.getenv")
def test_logger_methods(mock_getenv):
    """测试日志器的各种方法"""
    mock_getenv.return_value = "test"

    from src.core.logging import StructuredLogger, LogLevel, LogCategory

    logger = StructuredLogger(
        name="test_methods",
        category=LogCategory.API,
        enable_json=False,
        enable_console=False,
        enable_file=False,
    )

    # 测试各种日志方法不会抛出异常
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    # 测试特殊日志方法
    logger.audit("test_action", user_id="test_user")
    logger.performance("test_operation", 0.5, success=True)
    logger.api_request("GET", "/test", 200, 0.1, user_id="test_user")
    logger.prediction(123, "v1.0", "HOME_WIN", 0.85, success=True)
    logger.data_collection("api", "matches", 100, success=True)
    logger.cache_operation("get", "test_key", hit=True, duration_ms=10)
    logger.security_event("login_attempt", severity="low", user_id="test_user")
