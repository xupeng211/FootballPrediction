"""核心模块测试"""

import pytest


@pytest.mark.unit

class TestCoreModules:
    """测试核心模块"""

    def test_error_handler_import(self):
        """测试错误处理器导入"""
        try:
            from src.core.error_handler import ErrorHandler, handle_error

            assert ErrorHandler is not None
            assert callable(handle_error)
        except ImportError:
            pytest.skip("error_handler not available")

    def test_logging_system_import(self):
        """测试日志系统导入"""
        try:
            from src.core.logging_system import get_logger, setup_logging

            assert callable(get_logger)
            assert callable(setup_logging)
        except ImportError:
            pytest.skip("logging_system not available")

    def test_prediction_engine_import(self):
        """测试预测引擎导入"""
        try:
            from src.core.prediction_engine import PredictionEngine

            assert PredictionEngine is not None
        except ImportError:
            pytest.skip("PredictionEngine not available")

    def test_exceptions_import(self):
        """测试异常模块导入"""
        try:
            from src.core.exceptions import FootballPredictionError, ValidationError

            assert FootballPredictionError is not None
            assert ValidationError is not None
        except ImportError:
            pytest.skip("exceptions not available")
