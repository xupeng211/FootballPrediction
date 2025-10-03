from src.core.logger import Logger
from unittest.mock import Mock, patch
import logging
import pytest
import os

pytestmark = pytest.mark.unit
class TestLogger:
    """测试Logger类的所有方法"""
    def test_setup_logger_default_level(self):
        """测试设置默认级别的日志器"""
        logger = Logger.setup_logger("test_logger[")": assert logger.name =="]test_logger[" assert logger.level ==logging.INFO[""""
        assert len(logger.handlers) ==1
        assert isinstance(logger.handlers[0], logging.StreamHandler)
    def test_setup_logger_custom_level(self):
        "]]""测试设置自定义级别的日志器"""
        logger = Logger.setup_logger("test_debug[", "]DEBUG[")": assert logger.level ==logging.DEBUG[" logger = Logger.setup_logger("]]test_error[", "]ERROR[")": assert logger.level ==logging.ERROR[" logger = Logger.setup_logger("]]test_warning[", "]WARNING[")": assert logger.level ==logging.WARNING[" def test_setup_logger_case_insensitive(self):""
        "]]""测试级别设置大小写不敏感"""
        logger = Logger.setup_logger("test_lower[", "]debug[")": assert logger.level ==logging.DEBUG[" logger = Logger.setup_logger("]]test_mixed[", "]Info[")": assert logger.level ==logging.INFO[" def test_setup_logger_handler_not_duplicated(self):""
        "]]""测试重复调用不会添加重复的handler"""
        logger_name = os.getenv("TEST_CORE_LOGGER_LOGGER_NAME_20"): logger1 = Logger.setup_logger(logger_name)": logger2 = Logger.setup_logger(logger_name)"""
        # 应该是同一个logger实例
        assert logger1 is logger2
        # handler不应该重复添加
        assert len(logger1.handlers) ==1
    def test_logger_formatter_format(self):
        "]""测试日志格式器"""
        logger = Logger.setup_logger("test_format[")": handler = logger.handlers[0]": formatter = handler.formatter[""
        # 检查格式字符串
        expected_format = os.getenv("TEST_CORE_LOGGER_EXPECTED_FORMAT_28"): assert formatter._fmt ==expected_format[" def test_global_logger_instance(self):"""
        "]]""测试全局日志实例"""
        from src.core.logger import logger
        assert isinstance(logger, logging.Logger)
        assert logger.name =="footballprediction[" def test_logger_actually_logs("
    """"
        "]""测试日志器实际输出功能"""
        with patch("logging.StreamHandler.emit[") as mock_emit:": logger = Logger.setup_logger("]test_emit_unique[")": logger.info("]测试信息[")": assert mock_emit.called[" def test_setup_logger_with_existing_handlers(self):""
        "]]""测试已有handler的logger不会重复添加"""
        logger = logging.getLogger("test_existing[")""""
        # 先添加一个handler
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        original_handler_count = len(logger.handlers)
        # 调用setup_logger
        result_logger = Logger.setup_logger("]test_existing[")""""
        # handler数量不应该增加
        assert len(result_logger.handlers) ==original_handler_count
        assert result_logger is logger
    def test_logger_level_setting_edge_cases(self):
        "]""测试日志级别设置的边界情况"""
        # 测试所有有效的日志级别
        levels = ["CRITICAL[", "]ERROR[", "]WARNING[", "]INFO[", "]DEBUG["]": for level in levels = logger Logger.setup_logger(f["]test_{level.lower()"], level)": assert logger.level ==getattr(logging, level)"""
    @patch("logging.getLogger[")": def test_setup_logger_calls_getLogger(self, mock_get_logger):"""
        "]""测试setup_logger调用logging.getLogger"""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger
        Logger.setup_logger("test_mock[")": mock_get_logger.assert_called_once_with("]test_mock[")"]"""
