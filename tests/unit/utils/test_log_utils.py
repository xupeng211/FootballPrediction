from unittest.mock import MagicMock, patch

"""
日志工具测试
"""

import json
import logging
import logging.config
import os
import tempfile
from pathlib import Path

import pytest


@pytest.mark.unit
@pytest.mark.critical
class TestLogUtils:
    """日志工具测试"""

    def test_logging_basic(self):
        """测试基本日志功能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            # 创建日志器
            logger = logging.getLogger("test_logger")
            logger.setLevel(logging.INFO)

            # 创建文件处理器
            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logger.addHandler(handler)

            assert isinstance(logger, logging.Logger)
            assert logger.name == "test_logger"
            assert logger.level == logging.INFO

            # 测试写入日志
            logger.info("Test message")

            # 清理处理器
            handler.close()
            logger.removeHandler(handler)

            # 验证文件被创建
            assert log_file.exists()

            # 验证日志内容
            content = log_file.read_text()
            assert "Test message" in content

    def test_logging_json_format(self):
        """测试JSON格式日志"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.json"

            # 自定义JSON格式化器
            class JsonFormatter(logging.Formatter):
                def format(self, record):
                    log_data = {
                        "timestamp": self.formatTime(record),
                        "level": record.levelname,
                        "message": record.getMessage(),
                        "logger": record.name,
                    }
                    return json.dumps(log_data)

            # 创建日志器
            logger = logging.getLogger("json_logger")
            logger.setLevel(logging.DEBUG)

            # 创建文件处理器
            handler = logging.FileHandler(log_file)
            handler.setFormatter(JsonFormatter())
            logger.addHandler(handler)

            # 记录不同级别的日志
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            # 清理处理器
            handler.close()
            logger.removeHandler(handler)

            # 验证JSON格式
            content = log_file.read_text()
            lines = content.strip().split("\n")

            for line in lines:
                # 每行都应该是有效的JSON
                log_data = json.loads(line)
                assert "message" in log_data
                assert "level" in log_data
                assert "timestamp" in log_data

    def test_logging_console_only(self):
        """测试仅控制台日志"""
        logger = logging.getLogger("console_logger")
        logger.setLevel(logging.WARNING)

        # 创建控制台处理器
        handler = logging.StreamHandler()
        handler.setLevel(logging.WARNING)
        logger.addHandler(handler)

        assert isinstance(logger, logging.Logger)
        assert logger.level == logging.WARNING

        # 测试日志输出
        with patch("sys.stdout"):
            logger.warning("Warning message")

        # 清理处理器
        logger.removeHandler(handler)

    def test_logging_multiple_handlers(self):
        """测试多个处理器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file1 = Path(tmpdir) / "handler1.log"
            log_file2 = Path(tmpdir) / "handler2.log"

            logger = logging.getLogger("multi_handler_logger")
            logger.setLevel(logging.INFO)

            # 添加两个文件处理器
            handler1 = logging.FileHandler(log_file1)
            handler1.setFormatter(logging.Formatter("Handler1: %(message)s"))
            logger.addHandler(handler1)

            handler2 = logging.FileHandler(log_file2)
            handler2.setFormatter(logging.Formatter("Handler2: %(message)s"))
            logger.addHandler(handler2)

            # 记录日志
            logger.info("Test message")

            # 清理处理器
            handler1.close()
            handler2.close()
            logger.removeHandler(handler1)
            logger.removeHandler(handler2)

            # 验证两个文件都有日志
            assert log_file1.exists()
            assert log_file2.exists()

            content1 = log_file1.read_text()
            content2 = log_file2.read_text()
            assert "Handler1: Test message" in content1
            assert "Handler2: Test message" in content2

    def test_logging_levels(self):
        """测试不同日志级别"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "levels.log"

            logger = logging.getLogger("levels_test")
            logger.setLevel(logging.DEBUG)

            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            logger.addHandler(handler)

            # 记录不同级别的日志
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")

            # 清理处理器
            handler.close()
            logger.removeHandler(handler)

            # 验证所有级别都被记录
            content = log_file.read_text()
            assert "DEBUG: Debug message" in content
            assert "INFO: Info message" in content
            assert "WARNING: Warning message" in content
            assert "ERROR: Error message" in content
            assert "CRITICAL: Critical message" in content

    def test_logging_exception(self):
        """测试异常日志记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "exception.log"

            logger = logging.getLogger("exception_logger")
            logger.setLevel(logging.ERROR)

            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter("%(levelname)s: %(message)s\n%(exc_info)s")
            )
            logger.addHandler(handler)

            try:
                # 故意引发异常
                raise ValueError("Test exception")
            except Exception:
                logger.exception("Exception occurred")

            # 清理处理器
            handler.close()
            logger.removeHandler(handler)

            # 验证异常信息
            content = log_file.read_text()
            assert "Exception occurred" in content
            assert "ValueError" in content
            assert "Test exception" in content

    def test_logging_filter(self):
        """测试日志过滤器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "filtered.log"

            # 创建自定义过滤器
            class LevelFilter(logging.Filter):
                def filter(self, record):
                    # 只允许ERROR及以上级别
                    return record.levelno >= logging.ERROR

            logger = logging.getLogger("filtered_logger")
            logger.setLevel(logging.DEBUG)

            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            handler.addFilter(LevelFilter())
            logger.addHandler(handler)

            # 记录不同级别的日志
            logger.debug("Debug message")  # 应被过滤
            logger.info("Info message")  # 应被过滤
            logger.warning("Warning message")  # 应被过滤
            logger.error("Error message")  # 应通过
            logger.critical("Critical message")  # 应通过

            # 清理处理器
            handler.close()
            logger.removeHandler(handler)

            # 验证只有ERROR及以上级别的日志被记录
            content = log_file.read_text()
            assert "Debug message" not in content
            assert "Info message" not in content
            assert "Warning message" not in content
            assert "ERROR: Error message" in content
            assert "CRITICAL: Critical message" in content

    def test_logging_context(self):
        """测试日志上下文"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "context.log"

            # 使用LoggerAdapter添加上下文
            class ContextAdapter(logging.LoggerAdapter):
                def process(self, msg, kwargs):
                    return f"[{self.extra['context']}] {msg}", kwargs

            logger = logging.getLogger("context_logger")
            logger.setLevel(logging.INFO)

            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)

            # 创建带上下文的适配器
            adapter = ContextAdapter(logger, {"context": "REQUEST-123"})

            # 记录日志
            adapter.info("Request started")
            adapter.info("Processing data")

            # 清理处理器
            handler.close()
            logger.removeHandler(handler)

            # 验证上下文信息
            content = log_file.read_text()
            assert "[REQUEST-123] Request started" in content
            assert "[REQUEST-123] Processing data" in content

    def test_logging_rotation(self):
        """测试日志轮转（模拟）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "rotating.log"

            logger = logging.getLogger("rotating_logger")
            logger.setLevel(logging.INFO)

            # 模拟日志轮转
            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)

            # 写入一些日志
            for i in range(10):
                logger.info(f"Message {i}")

            # 模拟轮转：关闭当前处理器，创建新文件
            handler.close()
            logger.removeHandler(handler)

            # 重命名文件
            rotated_file = log_file.with_suffix(".log.1")
            log_file.rename(rotated_file)

            # 创建新处理器
            new_handler = logging.FileHandler(log_file)
            new_handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(new_handler)

            # 写入新日志
            logger.info("New message after rotation")

            # 清理处理器
            new_handler.close()
            logger.removeHandler(new_handler)

            # 验证轮转
            assert rotated_file.exists()
            assert log_file.exists()

            rotated_content = rotated_file.read_text()
            new_content = log_file.read_text()

            assert "Message 0" in rotated_content
            assert "New message after rotation" in new_content

    def test_logging_configuration_from_dict(self):
        """测试从字典配置日志"""
        _config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                },
            },
            "handlers": {
                "default": {
                    "level": "INFO",
                    "formatter": "standard",
                    "class": "logging.StreamHandler",
                },
            },
            "loggers": {
                "": {"handlers": ["default"], "level": "INFO", "propagate": False}
            },
        }

        # 应用配置
        logging._config.dictConfig(config)

        # 验证配置
        logger = logging.getLogger()
        assert logger.level == logging.INFO

        # 重置配置
        logging.getLogger().handlers.clear()

    def test_custom_logger_class(self):
        """测试自定义日志器类"""

        class CustomLogger(logging.Logger):
            def __init__(self, name):
                super().__init__(name)
                self.extra_data = {}

            def with_extra(self, **kwargs):
                """添加额外数据"""
                self.extra_data.update(kwargs)
                return self

            def _log(
                self, level, msg, args, exc_info=None, extra=None, stack_info=False
            ):
                # 合并额外数据
                if self.extra_data:
                    extra = extra or {}
                    extra.update(self.extra_data)
                super()._log(level, msg, args, exc_info, extra, stack_info)

        # 注册自定义日志器类
        logging.setLoggerClass(CustomLogger)

        # 创建自定义日志器
        logger = logging.getLogger("custom_logger")
        assert isinstance(logger, CustomLogger)

        # 测试额外数据功能
        logger.with_extra(user_id=123, request_id="abc")

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "custom.log"

            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter(
                    "%(message)s - User: %(user_id)s - Request: %(request_id)s"
                )
            )
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            logger.info("Test message")

            handler.close()
            logger.removeHandler(handler)

            content = log_file.read_text()
            assert "User: 123" in content
            assert "Request: abc" in content

        # 恢复默认日志器类
        logging.setLoggerClass(logging.Logger)
