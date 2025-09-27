"""
Auto-generated tests for src.core.logging module
"""

import logging
import pytest
from unittest.mock import patch, MagicMock
from src.core.logging import get_logger


class TestCoreLogging:
    """测试核心日志模块"""

    def test_get_logger_with_name_only(self):
        """测试只提供名称的日志器获取"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            result = get_logger("test_logger")

            assert result == mock_logger
            mock_base_logger.setup_logger.assert_called_once_with("test_logger", "INFO")

    def test_get_logger_with_name_and_level(self):
        """测试提供名称和级别的日志器获取"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            result = get_logger("test_logger", "DEBUG")

            assert result == mock_logger
            mock_base_logger.setup_logger.assert_called_once_with("test_logger", "DEBUG")

    def test_get_logger_with_none_level(self):
        """测试级别为None时的日志器获取"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            result = get_logger("test_logger", None)

            assert result == mock_logger
            mock_base_logger.setup_logger.assert_called_once_with("test_logger", "INFO")

    def test_get_logger_with_empty_level(self):
        """测试级别为空字符串时的日志器获取"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            result = get_logger("test_logger", "")

            assert result == mock_logger
            mock_base_logger.setup_logger.assert_called_once_with("test_logger", "INFO")

    @pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    def test_get_logger_with_different_levels(self, level):
        """测试不同日志级别的日志器获取"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            result = get_logger("test_logger", level)

            assert result == mock_logger
            mock_base_logger.setup_logger.assert_called_once_with("test_logger", level)

    @pytest.mark.parametrize("logger_name", ["", "test", "module.submodule", "very.long.logger.name.hierarchy"])
    def test_get_logger_with_different_names(self, logger_name):
        """测试不同名称的日志器获取"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            result = get_logger(logger_name)

            assert result == mock_logger
            mock_base_logger.setup_logger.assert_called_once_with(logger_name, "INFO")

    def test_get_logger_returns_correct_type(self):
        """测试get_logger返回正确的类型"""
        mock_logger = MagicMock(spec=logging.Logger)
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            result = get_logger("test_logger")

            # 应该返回Logger实例
            assert isinstance(result, logging.Logger)

    def test_get_logger_preserves_logger_functionality(self):
        """测试get_logger保持日志器功能"""
        mock_logger = MagicMock(spec=logging.Logger)
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            result = get_logger("test_logger")

            # 返回的logger应该有标准的日志方法
            assert hasattr(result, 'debug')
            assert hasattr(result, 'info')
            assert hasattr(result, 'warning')
            assert hasattr(result, 'error')
            assert hasattr(result, 'critical')

    def test_multiple_calls_with_same_name(self):
        """测试多次调用相同名称的get_logger"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            result1 = get_logger("test_logger")
            result2 = get_logger("test_logger")

            # 每次调用都应该调用setup_logger
            assert mock_base_logger.setup_logger.call_count == 2
            assert mock_base_logger.setup_logger.call_args_list[0] == (("test_logger", "INFO"),)
            assert mock_base_logger.setup_logger.call_args_list[1] == (("test_logger", "INFO"),)

    def test_multiple_calls_with_different_names(self):
        """测试多次调用不同名称的get_logger"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            result1 = get_logger("logger1")
            result2 = get_logger("logger2")

            # 应该调用setup_logger两次，使用不同的名称
            assert mock_base_logger.setup_logger.call_count == 2
            assert mock_base_logger.setup_logger.call_args_list[0] == (("logger1", "INFO"),)
            assert mock_base_logger.setup_logger.call_args_list[1] == (("logger2", "INFO"),)

    def test_get_logger_case_sensitivity(self):
        """测试日志器名称的大小写敏感性"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            result1 = get_logger("TestLogger")
            result2 = get_logger("testlogger")

            # 应该调用setup_logger两次，名称不同
            assert mock_base_logger.setup_logger.call_count == 2
            assert mock_base_logger.setup_logger.call_args_list[0] == (("TestLogger", "INFO"),)
            assert mock_base_logger.setup_logger.call_args_list[1] == (("testlogger", "INFO"),)

    def test_get_logger_with_special_characters(self):
        """测试包含特殊字符的日志器名称"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        special_names = ["logger.dotted", "logger-with-dashes", "logger_with_underscores", "logger123"]

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            for name in special_names:
                result = get_logger(name)
                assert result == mock_logger
                mock_base_logger.setup_logger.assert_called_with(name, "INFO")

    def test_get_logger_level_passthrough(self):
        """测试日志级别直接传递"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            # 测试不同的级别直接传递，不做转换
            test_cases = [
                "info", "INFO", "Info",
                "warning", "WARNING", "Warning",
                "debug", "DEBUG", "Debug",
                "error", "ERROR", "Error",
                "critical", "CRITICAL", "Critical"
            ]

            for level in test_cases:
                mock_base_logger.setup_logger.reset_mock()
                get_logger("test_logger", level)
                mock_base_logger.setup_logger.assert_called_once_with("test_logger", level)

    def test_get_logger_with_invalid_level(self):
        """测试无效日志级别"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            # 即使级别无效，也应该传递给setup_logger
            get_logger("test_logger", "INVALID_LEVEL")
            mock_base_logger.setup_logger.assert_called_once_with("test_logger", "INVALID_LEVEL")

    def test_get_logger_default_level_fallback(self):
        """测试默认级别回退机制"""
        mock_logger = MagicMock()
        mock_base_logger = MagicMock()
        mock_base_logger.setup_logger.return_value = mock_logger

        with patch('src.core.logging._BaseLogger', mock_base_logger):
            # 测试各种假值情况
            false_values = [None, "", False, 0]

            for false_value in false_values:
                mock_base_logger.setup_logger.reset_mock()
                get_logger("test_logger", false_value)
                mock_base_logger.setup_logger.assert_called_once_with("test_logger", "INFO")

    def test_get_logger_import_dependency(self):
        """测试导入依赖"""
        # 验证模块可以正确导入
        from src.core.logging import get_logger
        assert callable(get_logger)

        # 验证依赖的Logger类存在
        from src.core.logger import Logger
        assert hasattr(Logger, 'setup_logger')

    def test_function_signature(self):
        """测试函数签名"""
        import inspect
        sig = inspect.signature(get_logger)

        # 验证参数
        params = list(sig.parameters.keys())
        assert 'name' in params
        assert 'level' in params

        # 验证默认值
        assert sig.parameters['level'].default == "INFO"

    def test_function_docstring(self):
        """测试函数文档字符串"""
        doc = get_logger.__doc__
        assert doc is not None
        assert "获取指定名称的日志器" in doc
        assert "Args:" in doc
        assert "Returns:" in doc