"""
测试核心日志模块
"""

import logging
import pytest
from src.core.logger import Logger, get_logger


@pytest.mark.unit

def test_get_logger():
    """测试获取日志器"""
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"


def test_get_logger_with_level():
    """测试获取指定级别的日志器"""
    logger = get_logger("test_logger_debug", "DEBUG")
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.DEBUG


def test_logger_setup():
    """测试日志器设置"""
    logger = Logger.setup_logger("test_setup", "INFO")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_setup"


def test_logger_multiple_calls():
    """测试多次调用获取同一日志器"""
    logger1 = get_logger("test_same")
    logger2 = get_logger("test_same")
    assert logger1 is logger2
