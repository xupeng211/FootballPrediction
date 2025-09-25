"""
错误日志记录器测试 - 覆盖率提升版本

针对 error_logger.py 的详细测试，专注于提升覆盖率至 70%+
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, MagicMock, AsyncMock
from typing import Any, Dict, List, Optional
import json

from src.tasks.error_logger import (
    TaskErrorLogger,
    ErrorLog,
    ErrorConfig,
    ErrorSeverity,
    ErrorCategory,
    log_task_error,
    log_task_warning,
    log_task_info,
    get_task_errors,
    clear_task_errors,
    ErrorStatistics
)


class TestErrorConfig:
    """错误配置测试类"""

    def test_init_default_values(self):
        """测试默认值初始化"""
        config = ErrorConfig()

        assert config.max_error_logs == 1000
        assert config.error_retention_days == 30
        assert config.enable_alerting is True
        assert config.alert_threshold == 5
        assert config.alert_time_window_minutes == 60
        assert config.enable_database_logging is True
        assert config.enable_file_logging is True
        assert config.log_file_path == "/tmp/task_errors.log"

    def test_init_custom_values(self):
        """测试自定义值初始化"""
        config = ErrorConfig(
            max_error_logs=2000,
            error_retention_days=60,
            enable_alerting=False,
            alert_threshold=10,
            alert_time_window_minutes=120,
            enable_database_logging=False,
            enable_file_logging=False,
            log_file_path="/custom/errors.log"
        )

        assert config.max_error_logs == 2000
        assert config.error_retention_days == 60
        assert config.enable_alerting is False
        assert config.alert_threshold == 10
        assert config.alert_time_window_minutes == 120
        assert config.enable_database_logging is False
        assert config.enable_file_logging is False
        assert config.log_file_path == "/custom/errors.log"

    def test_dataclass_properties(self):
        """测试dataclass属性"""
        config = ErrorConfig()

        assert hasattr(config, '__dataclass_fields__')
        fields = config.__dataclass_fields__
        assert 'max_error_logs' in fields
        assert 'error_retention_days' in fields
        assert 'enable_alerting' in fields
        assert 'alert_threshold' in fields


class TestErrorLog:
    """错误日志测试类"""

    def test_init_minimal(self):
        """测试最小初始化"""
        error_log = ErrorLog(
            task_name="test_task",
            error_type="RuntimeError",
            error_message="Test error message",
            severity=ErrorSeverity.ERROR
        )

        assert error_log.task_name == "test_task"
        assert error_log.error_type == "RuntimeError"
        assert error_log.error_message == "Test error message"
        assert error_log.severity == ErrorSeverity.ERROR
        assert error_log.category is None
        assert error_log.stack_trace is None
        assert error_log.task_id is None
        assert error_log.timestamp is not None
        assert error_log.resolved is False

    def test_init_full(self):
        """测试完整初始化"""
        error_log = ErrorLog(
            task_name="test_task",
            error_type="ValueError",
            error_message="Invalid input",
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION,
            stack_trace="Traceback (most recent call last):\n...",
            task_id="task_123",
            context={"input": "invalid_value"},
            resolved=True
        )

        assert error_log.task_name == "test_task"
        assert error_log.error_type == "ValueError"
        assert error_log.error_message == "Invalid input"
        assert error_log.severity == ErrorSeverity.WARNING
        assert error_log.category == ErrorCategory.VALIDATION
        assert error_log.stack_trace == "Traceback (most recent call last):\n..."
        assert error_log.task_id == "task_123"
        assert error_log.context == {"input": "invalid_value"}
        assert error_log.resolved is True
        assert error_log.timestamp is not None

    def test_dataclass_properties(self):
        """测试dataclass属性"""
        error_log = ErrorLog(
            task_name="test_task",
            error_type="RuntimeError",
            error_message="Test error",
            severity=ErrorSeverity.ERROR
        )

        assert hasattr(error_log, '__dataclass_fields__')
        fields = error_log.__dataclass_fields__
        assert 'task_name' in fields
        assert 'error_type' in fields
        assert 'error_message' in fields
        assert 'severity' in fields


class TestErrorStatistics:
    """错误统计测试类"""

    def test_init(self):
        """测试初始化"""
        stats = ErrorStatistics()

        assert stats.total_errors == 0
        assert stats.errors_by_severity == {}
        assert stats.errors_by_category == {}
        assert stats.errors_by_task == {}
        assert stats.recent_errors == []
        assert stats.resolved_errors == 0
        assert stats.active_errors == 0

    def test_add_error(self):
        """测试添加错误"""
        stats = ErrorStatistics()
        error_log = ErrorLog(
            task_name="test_task",
            error_type="RuntimeError",
            error_message="Test error",
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.EXECUTION
        )

        stats.add_error(error_log)

        assert stats.total_errors == 1
        assert stats.errors_by_severity[ErrorSeverity.ERROR] == 1
        assert stats.errors_by_category[ErrorCategory.EXECUTION] == 1
        assert stats.errors_by_task["test_task"] == 1
        assert len(stats.recent_errors) == 1
        assert stats.active_errors == 1

    def test_mark_resolved(self):
        """测试标记已解决"""
        stats = ErrorStatistics()
        error_log = ErrorLog(
            task_name="test_task",
            error_type="RuntimeError",
            error_message="Test error",
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.EXECUTION
        )

        stats.add_error(error_log)
        stats.mark_resolved(error_log)

        assert stats.resolved_errors == 1
        assert stats.active_errors == 0


class TestTaskErrorLogger:
    """任务错误日志记录器测试类"""

    def test_init(self):
        """测试初始化"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        assert logger.config == config
        assert logger.error_logs == []
        assert logger.error_statistics is not None
        assert isinstance(logger.error_statistics, ErrorStatistics)

    def test_log_error(self):
        """测试记录错误"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        error_log = logger.log_error(
            task_name="test_task",
            error_type="RuntimeError",
            error_message="Test error message",
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.EXECUTION
        )

        assert error_log.task_name == "test_task"
        assert error_log.error_type == "RuntimeError"
        assert error_log.error_message == "Test error message"
        assert error_log.severity == ErrorSeverity.ERROR
        assert error_log.category == ErrorCategory.EXECUTION
        assert len(logger.error_logs) == 1
        assert logger.error_statistics.total_errors == 1

    def test_log_warning(self):
        """测试记录警告"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        error_log = logger.log_warning(
            task_name="test_task",
            error_type="UserWarning",
            error_message="Test warning message",
            category=ErrorCategory.VALIDATION
        )

        assert error_log.severity == ErrorSeverity.WARNING
        assert error_log.category == ErrorCategory.VALIDATION
        assert len(logger.error_logs) == 1

    def test_log_info(self):
        """测试记录信息"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        error_log = logger.log_info(
            task_name="test_task",
            error_type="Info",
            error_message="Test info message",
            category=ErrorCategory.SYSTEM
        )

        assert error_log.severity == ErrorSeverity.INFO
        assert error_log.category == ErrorCategory.SYSTEM
        assert len(logger.error_logs) == 1

    def test_log_exception(self):
        """测试记录异常"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        try:
            raise ValueError("Test exception")
        except Exception as e:
            error_log = logger.log_exception(
                task_name="test_task",
                exception=e,
                category=ErrorCategory.EXECUTION
            )

        assert error_log.task_name == "test_task"
        assert error_log.error_type == "ValueError"
        assert error_log.error_message == "Test exception"
        assert error_log.category == ErrorCategory.EXECUTION
        assert error_log.stack_trace is not None
        assert len(logger.error_logs) == 1

    def test_log_with_context(self):
        """测试带上下文记录"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        context = {"input_data": {"value": 123}, "attempt": 3}
        error_log = logger.log_error(
            task_name="test_task",
            error_type="RuntimeError",
            error_message="Test error",
            severity=ErrorSeverity.ERROR,
            context=context
        )

        assert error_log.context == context
        assert len(logger.error_logs) == 1

    def test_log_with_task_id(self):
        """测试带任务ID记录"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        error_log = logger.log_error(
            task_name="test_task",
            error_type="RuntimeError",
            error_message="Test error",
            severity=ErrorSeverity.ERROR,
            task_id="task_123"
        )

        assert error_log.task_id == "task_123"
        assert len(logger.error_logs) == 1

    def test_get_errors_by_task(self):
        """测试按任务获取错误"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        logger.log_error("task1", "RuntimeError", "Error 1", ErrorSeverity.ERROR)
        logger.log_error("task2", "ValueError", "Error 2", ErrorSeverity.ERROR)
        logger.log_error("task1", "TypeError", "Error 3", ErrorSeverity.WARNING)

        task1_errors = logger.get_errors_by_task("task1")
        task2_errors = logger.get_errors_by_task("task2")

        assert len(task1_errors) == 2
        assert len(task2_errors) == 1
        assert all(error.task_name == "task1" for error in task1_errors)
        assert all(error.task_name == "task2" for error in task2_errors)

    def test_get_errors_by_severity(self):
        """测试按严重程度获取错误"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        logger.log_error("task1", "RuntimeError", "Error 1", ErrorSeverity.ERROR)
        logger.log_error("task2", "ValueError", "Error 2", ErrorSeverity.WARNING)
        logger.log_error("task3", "TypeError", "Error 3", ErrorSeverity.INFO)

        error_errors = logger.get_errors_by_severity(ErrorSeverity.ERROR)
        warning_errors = logger.get_errors_by_severity(ErrorSeverity.WARNING)

        assert len(error_errors) == 1
        assert len(warning_errors) == 1
        assert all(error.severity == ErrorSeverity.ERROR for error in error_errors)
        assert all(error.severity == ErrorSeverity.WARNING for error in warning_errors)

    def test_get_errors_by_category(self):
        """测试按类别获取错误"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        logger.log_error("task1", "RuntimeError", "Error 1", ErrorSeverity.ERROR, ErrorCategory.EXECUTION)
        logger.log_error("task2", "ValueError", "Error 2", ErrorSeverity.ERROR, ErrorCategory.VALIDATION)
        logger.log_error("task3", "TypeError", "Error 3", ErrorSeverity.ERROR, ErrorCategory.EXECUTION)

        execution_errors = logger.get_errors_by_category(ErrorCategory.EXECUTION)
        validation_errors = logger.get_errors_by_category(ErrorCategory.VALIDATION)

        assert len(execution_errors) == 2
        assert len(validation_errors) == 1
        assert all(error.category == ErrorCategory.EXECUTION for error in execution_errors)
        assert all(error.category == ErrorCategory.VALIDATION for error in validation_errors)

    def test_get_recent_errors(self):
        """测试获取最近错误"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        logger.log_error("task1", "RuntimeError", "Error 1", ErrorSeverity.ERROR)
        logger.log_error("task2", "ValueError", "Error 2", ErrorSeverity.ERROR)
        logger.log_error("task3", "TypeError", "Error 3", ErrorSeverity.ERROR)

        recent_errors = logger.get_recent_errors(2)

        assert len(recent_errors) == 2
        # Should be the most recent errors
        assert recent_errors[0].task_name == "task3"
        assert recent_errors[1].task_name == "task2"

    def test_resolve_error(self):
        """测试解决错误"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        error_log = logger.log_error("task1", "RuntimeError", "Error 1", ErrorSeverity.ERROR)

        assert error_log.resolved is False
        assert logger.error_statistics.active_errors == 1
        assert logger.error_statistics.resolved_errors == 0

        resolved = logger.resolve_error(error_log)

        assert resolved is True
        assert error_log.resolved is True
        assert logger.error_statistics.active_errors == 0
        assert logger.error_statistics.resolved_errors == 1

    def test_resolve_error_by_id(self):
        """测试按ID解决错误"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        error_log = logger.log_error("task1", "RuntimeError", "Error 1", ErrorSeverity.ERROR)

        resolved = logger.resolve_error_by_id(error_log.timestamp)

        assert resolved is True
        assert error_log.resolved is True

    def test_clear_old_errors(self):
        """测试清理旧错误"""
        config = ErrorConfig(error_retention_days=1)
        logger = TaskErrorLogger(config)

        # Create recent error
        logger.log_error("task1", "RuntimeError", "Recent error", ErrorSeverity.ERROR)

        # Create old error (2 days ago)
        old_timestamp = datetime.now() - timedelta(days=2)
        old_error = ErrorLog(
            task_name="task2",
            error_type="ValueError",
            error_message="Old error",
            severity=ErrorSeverity.ERROR,
            timestamp=old_timestamp
        )
        logger.error_logs.append(old_error)

        assert len(logger.error_logs) == 2

        cleared = logger.clear_old_errors()

        assert cleared == 1
        assert len(logger.error_logs) == 1
        assert logger.error_logs[0].task_name == "task1"

    def test_get_error_statistics(self):
        """测试获取错误统计"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        logger.log_error("task1", "RuntimeError", "Error 1", ErrorSeverity.ERROR, ErrorCategory.EXECUTION)
        logger.log_error("task2", "ValueError", "Error 2", ErrorSeverity.WARNING, ErrorCategory.VALIDATION)
        logger.log_error("task1", "TypeError", "Error 3", ErrorSeverity.INFO, ErrorCategory.SYSTEM)

        stats = logger.get_error_statistics()

        assert stats.total_errors == 3
        assert stats.errors_by_severity[ErrorSeverity.ERROR] == 1
        assert stats.errors_by_severity[ErrorSeverity.WARNING] == 1
        assert stats.errors_by_severity[ErrorSeverity.INFO] == 1
        assert stats.errors_by_category[ErrorCategory.EXECUTION] == 1
        assert stats.errors_by_category[ErrorCategory.VALIDATION] == 1
        assert stats.errors_by_category[ErrorCategory.SYSTEM] == 1
        assert stats.errors_by_task["task1"] == 2
        assert stats.errors_by_task["task2"] == 1

    def test_check_alert_threshold(self):
        """测试检查告警阈值"""
        config = ErrorConfig(alert_threshold=2, alert_time_window_minutes=60)
        logger = TaskErrorLogger(config)

        # Below threshold
        logger.log_error("task1", "RuntimeError", "Error 1", ErrorSeverity.ERROR)
        should_alert = logger.check_alert_threshold()
        assert should_alert is False

        # At threshold
        logger.log_error("task2", "ValueError", "Error 2", ErrorSeverity.ERROR)
        should_alert = logger.check_alert_threshold()
        assert should_alert is True

    def test_export_errors(self):
        """测试导出错误"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        logger.log_error("task1", "RuntimeError", "Error 1", ErrorSeverity.ERROR)
        logger.log_error("task2", "ValueError", "Error 2", ErrorSeverity.WARNING)

        exported = logger.export_errors()

        assert isinstance(exported, list)
        assert len(exported) == 2
        assert all(isinstance(error, dict) for error in exported)
        assert "task_name" in exported[0]
        assert "error_type" in exported[0]
        assert "error_message" in exported[0]


class TestErrorLoggerFunctions:
    """错误日志记录器函数测试"""

    @patch('src.tasks.error_logger.TaskErrorLogger')
    def test_log_task_error(self, mock_logger_class):
        """测试log_task_error函数"""
        mock_logger = Mock()
        mock_logger_class.return_value = mock_logger

        error_log = log_task_error(
            task_name="test_task",
            error_type="RuntimeError",
            error_message="Test error",
            severity=ErrorSeverity.ERROR
        )

        mock_logger.log_error.assert_called_once()
        assert error_log == mock_logger.log_error.return_value

    @patch('src.tasks.error_logger.TaskErrorLogger')
    def test_log_task_warning(self, mock_logger_class):
        """测试log_task_warning函数"""
        mock_logger = Mock()
        mock_logger_class.return_value = mock_logger

        error_log = log_task_warning(
            task_name="test_task",
            error_type="UserWarning",
            error_message="Test warning"
        )

        mock_logger.log_warning.assert_called_once()
        assert error_log == mock_logger.log_warning.return_value

    @patch('src.tasks.error_logger.TaskErrorLogger')
    def test_log_task_info(self, mock_logger_class):
        """测试log_task_info函数"""
        mock_logger = Mock()
        mock_logger_class.return_value = mock_logger

        error_log = log_task_info(
            task_name="test_task",
            error_type="Info",
            error_message="Test info"
        )

        mock_logger.log_info.assert_called_once()
        assert error_log == mock_logger.log_info.return_value

    @patch('src.tasks.error_logger.TaskErrorLogger')
    def test_get_task_errors(self, mock_logger_class):
        """测试get_task_errors函数"""
        mock_logger = Mock()
        mock_logger_class.return_value = mock_logger

        errors = get_task_errors(task_name="test_task")

        mock_logger.get_errors_by_task.assert_called_once_with("test_task")
        assert errors == mock_logger.get_errors_by_task.return_value

    @patch('src.tasks.error_logger.TaskErrorLogger')
    def test_clear_task_errors(self, mock_logger_class):
        """测试clear_task_errors函数"""
        mock_logger = Mock()
        mock_logger_class.return_value = mock_logger

        result = clear_task_errors()

        mock_logger.clear_old_errors.assert_called_once()
        assert result == mock_logger.clear_old_errors.return_value


class TestErrorLoggerIntegration:
    """错误日志记录器集成测试"""

    @patch('src.tasks.error_logger.os.environ.get')
    def test_environment_configuration(self, mock_get):
        """测试环境配置"""
        # Mock environment variables
        mock_get.side_effect = lambda key, default=None: {
            'ERROR_LOG_MAX_ERRORS': '2000',
            'ERROR_LOG_RETENTION_DAYS': '60',
            'ERROR_LOG_ALERT_THRESHOLD': '10',
            'ERROR_LOG_ALERT_WINDOW': '120',
            'ERROR_LOG_FILE_PATH': '/custom/errors.log'
        }.get(key, default)

        # Test that environment variables are used
        from src.tasks.error_logger import ERROR_LOG_MAX_ERRORS, ERROR_LOG_RETENTION_DAYS
        assert ERROR_LOG_MAX_ERRORS == 2000
        assert ERROR_LOG_RETENTION_DAYS == 60

    @patch('src.tasks.error_logger.os.environ.get')
    def test_default_environment_values(self, mock_get):
        """测试默认环境值"""
        # Mock no environment variables
        mock_get.return_value = None

        # Test that default values are used
        from src.tasks.error_logger import ERROR_LOG_MAX_ERRORS, ERROR_LOG_RETENTION_DAYS
        assert ERROR_LOG_MAX_ERRORS == 1000
        assert ERROR_LOG_RETENTION_DAYS == 30

    def test_error_severity_levels(self):
        """测试错误严重程度级别"""
        assert ErrorSeverity.CRITICAL.value > ErrorSeverity.ERROR.value
        assert ErrorSeverity.ERROR.value > ErrorSeverity.WARNING.value
        assert ErrorSeverity.WARNING.value > ErrorSeverity.INFO.value
        assert ErrorSeverity.INFO.value > ErrorSeverity.DEBUG.value

    def test_error_categories(self):
        """测试错误类别"""
        # Test that all categories are defined
        categories = [ErrorCategory.EXECUTION, ErrorCategory.VALIDATION,
                     ErrorCategory.SYSTEM, ErrorCategory.NETWORK, ErrorCategory.DATABASE]

        assert len(categories) == 5
        assert all(isinstance(category, ErrorCategory) for category in categories)

    def test_error_timestamp_format(self):
        """测试错误时间戳格式"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        error_log = logger.log_error("test_task", "RuntimeError", "Test error", ErrorSeverity.ERROR)

        assert isinstance(error_log.timestamp, datetime)

    def test_error_context_serialization(self):
        """测试错误上下文序列化"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        context = {
            "input_data": {"value": 123, "nested": {"deep": "value"}},
            "metadata": {"source": "api", "version": "1.0"},
            "attempt": 3,
            "duration": 5.5
        }

        error_log = logger.log_error("test_task", "RuntimeError", "Test error", ErrorSeverity.ERROR, context=context)

        assert error_log.context == context

    def test_error_statistics_accuracy(self):
        """测试错误统计准确性"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        # Add various errors
        logger.log_error("task1", "RuntimeError", "Error 1", ErrorSeverity.ERROR, ErrorCategory.EXECUTION)
        logger.log_error("task2", "ValueError", "Error 2", ErrorSeverity.ERROR, ErrorCategory.VALIDATION)
        logger.log_error("task1", "TypeError", "Error 3", ErrorSeverity.WARNING, ErrorCategory.EXECUTION)
        logger.log_error("task3", "IOError", "Error 4", ErrorSeverity.INFO, ErrorCategory.SYSTEM)

        stats = logger.get_error_statistics()

        assert stats.total_errors == 4
        assert stats.errors_by_severity[ErrorSeverity.ERROR] == 2
        assert stats.errors_by_severity[ErrorSeverity.WARNING] == 1
        assert stats.errors_by_severity[ErrorSeverity.INFO] == 1
        assert stats.errors_by_category[ErrorCategory.EXECUTION] == 2
        assert stats.errors_by_category[ErrorCategory.VALIDATION] == 1
        assert stats.errors_by_category[ErrorCategory.SYSTEM] == 1
        assert stats.errors_by_task["task1"] == 2
        assert stats.errors_by_task["task2"] == 1
        assert stats.errors_by_task["task3"] == 1
        assert stats.active_errors == 4
        assert stats.resolved_errors == 0

    def test_error_resolution_flow(self):
        """测试错误解决流程"""
        config = ErrorConfig()
        logger = TaskErrorLogger(config)

        # Log errors
        error1 = logger.log_error("task1", "RuntimeError", "Error 1", ErrorSeverity.ERROR)
        error2 = logger.log_error("task2", "ValueError", "Error 2", ErrorSeverity.ERROR)

        assert logger.error_statistics.active_errors == 2
        assert logger.error_statistics.resolved_errors == 0

        # Resolve one error
        logger.resolve_error(error1)

        assert logger.error_statistics.active_errors == 1
        assert logger.error_statistics.resolved_errors == 1
        assert error1.resolved is True
        assert error2.resolved is False

        # Resolve second error
        logger.resolve_error(error2)

        assert logger.error_statistics.active_errors == 0
        assert logger.error_statistics.resolved_errors == 2
        assert error2.resolved is True


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])