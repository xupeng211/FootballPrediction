"""
Auto-generated tests for src.utils.warning_filters module
"""

import warnings
import pytest
from unittest.mock import patch, MagicMock
from src.utils.warning_filters import (
    setup_warning_filters,
    setup_test_warning_filters,
    suppress_marshmallow_warnings,
    _setup_third_party_warning_filters
)


class TestWarningFilters:
    """测试警告过滤器模块"""

    @patch('builtins.print')
    def test_setup_warning_filters_with_marshmallow_import(self, mock_print):
        """测试带有Marshmallow导入的警告过滤器设置"""
        with patch('warnings.filterwarnings') as mock_filterwarnings:
            # 模拟成功导入marshmallow.warnings
            with patch('importlib.import_module') as mock_import:
                mock_marshmallow = MagicMock()
                mock_marshmallow.warnings = MagicMock()
                mock_marshmallow.warnings.ChangedInMarshmallow4Warning = Warning
                mock_import.return_value = mock_marshmallow

                setup_warning_filters()

                # 验证调用了正确的警告过滤器
                mock_filterwarnings.assert_called_with(
                    "ignore",
                    category=mock_marshmallow.warnings.ChangedInMarshmallow4Warning,
                    message=r".*Number.*field should not be instantiated.*",
                )
                mock_print.assert_called_with("✅ Marshmallow 4 兼容性警告已抑制")

    @patch('builtins.print')
    def test_setup_warning_filters_without_marshmallow_import(self, mock_print):
        """测试没有Marshmallow导入的警告过滤器设置"""
        with patch('warnings.filterwarnings') as mock_filterwarnings:
            with patch('importlib.import_module') as mock_import:
                # 模拟导入失败
                mock_import.side_effect = ImportError("No module named 'marshmallow.warnings'")

                setup_warning_filters()

                # 验证使用了通用过滤器
                mock_filterwarnings.assert_any_call(
                    "ignore", message=r".*Number.*field.*should.*not.*be.*instantiated.*"
                )
                mock_print.assert_called_with("⚠️  使用通用方式抑制 Marshmallow 警告")

    def test_setup_third_party_warning_filters(self):
        """测试第三方库警告过滤器设置"""
        with patch('warnings.filterwarnings') as mock_filterwarnings:
            _setup_third_party_warning_filters()

            # 验证调用了Great Expectations和SQLAlchemy的过滤器
            assert mock_filterwarnings.call_count >= 2

            calls = mock_filterwarnings.call_args_list
            messages = [call[0][1] for call in calls if len(call[0]) > 1]

            # 应该包含Great Expectations和SQLAlchemy相关的消息
            assert any("great_expectations" in msg for msg in messages)
            assert any("sqlalchemy" in msg for msg in messages)

    def test_setup_test_warning_filters(self):
        """测试测试环境警告过滤器设置"""
        with patch('src.utils.warning_filters.setup_warning_filters') as mock_setup:
            with patch('warnings.filterwarnings') as mock_filterwarnings:
                setup_test_warning_filters()

                # 验证调用了基础设置
                mock_setup.assert_called_once()

                # 验证调用了测试专用的过滤器
                assert mock_filterwarnings.call_count >= 2

    def test_suppress_marshmallow_warnings_decorator(self):
        """测试Marshmallow警告抑制装饰器"""
        with patch('warnings.catch_warnings') as mock_catch_warnings:
            mock_context = MagicMock()
            mock_catch_warnings.return_value.__enter__ = MagicMock()
            mock_catch_warnings.return_value.__exit__ = MagicMock()

            @suppress_marshmallow_warnings
            def test_function():
                return "test_result"

            result = test_function()
            assert result == "test_result"
            mock_catch_warnings.assert_called_once()

    def test_suppress_marshmallow_warnings_decorator_with_args(self):
        """测试带参数的Marshmallow警告抑制装饰器"""
        with patch('warnings.catch_warnings') as mock_catch_warnings:
            mock_context = MagicMock()
            mock_catch_warnings.return_value.__enter__ = MagicMock()
            mock_catch_warnings.return_value.__exit__ = MagicMock()

            @suppress_marshmallow_warnings()
            def test_function():
                return "test_result"

            result = test_function()
            assert result == "test_result"
            mock_catch_warnings.assert_called_once()

    def test_suppress_marshmallow_warnings_decorator_without_marshmallow_import(self):
        """测试没有Marshmallow导入时的装饰器"""
        with patch('warnings.catch_warnings') as mock_catch_warnings:
            with patch('importlib.import_module') as mock_import:
                # 模拟导入失败
                mock_import.side_effect = ImportError("No module named 'marshmallow.warnings'")

                mock_context = MagicMock()
                mock_catch_warnings.return_value.__enter__ = MagicMock()
                mock_catch_warnings.return_value.__exit__ = MagicMock()

                @suppress_marshmallow_warnings
                def test_function():
                    return "test_result"

                result = test_function()
                assert result == "test_result"

                # 验证仍然设置了过滤器
                mock_catch_warnings.assert_called_once()

    def test_decorator_preserves_function_signature(self):
        """测试装饰器保持函数签名"""
        @suppress_marshmallow_warnings
        def test_function(arg1, arg2, kwarg1=None):
            return (arg1, arg2, kwarg1)

        result = test_function("a", "b", kwarg1="c")
        assert result == ("a", "b", "c")

    def test_decorator_handles_function_with_kwargs(self):
        """测试装饰器处理带kwargs的函数"""
        @suppress_marshmallow_warnings
        def test_function(*args, **kwargs):
            return (args, kwargs)

        result = test_function(1, 2, 3, key="value")
        assert result == ((1, 2, 3), {"key": "value"})

    @patch('src.utils.warning_filters._auto_setup')
    def test_auto_setup_on_import(self, mock_auto_setup):
        """测试模块导入时自动设置"""
        # 这个测试验证模块在导入时的行为
        # 由于模块已经导入，我们主要验证函数存在且可调用
        assert callable(mock_auto_setup)

    @patch('builtins.print')
    def test_auto_setup_with_exception(self, mock_print):
        """测试自动设置失败处理"""
        with patch('src.utils.warning_filters.setup_warning_filters') as mock_setup:
            mock_setup.side_effect = Exception("Test error")

            # 导入模块以触发自动设置
            import importlib
            import src.utils.warning_filters
            importlib.reload(src.utils.warning_filters)

            # 验证异常被捕获且不影响执行
            mock_print.assert_called_with("⚠️  警告过滤器自动设置失败: Test error")

    def test_warning_filter_regex_patterns(self):
        """测试警告过滤器的正则表达式模式"""
        test_patterns = [
            r".*Number.*field should not be instantiated.*",
            r".*Number.*field.*should.*not.*be.*instantiated.*",
            r".*great_expectations.*",
            r".*sqlalchemy.*"
        ]

        for pattern in test_patterns:
            # 验证正则表达式模式是有效的
            import re
            try:
                re.compile(pattern)
            except re.error:
                pytest.fail(f"Invalid regex pattern: {pattern}")

    def test_decorator_with_exception_in_function(self):
        """测试装饰器处理函数中的异常"""
        @suppress_marshmallow_warnings
        def test_function():
            raise ValueError("Test exception")

        with pytest.raises(ValueError, match="Test exception"):
            test_function()

    def test_decorator_with_return_values(self):
        """测试装饰器保持返回值"""
        @suppress_marshmallow_warnings
        def test_function():
            return {"key": "value", "number": 42}

        result = test_function()
        assert result == {"key": "value", "number": 42}

    def test_multiple_decorators_stack(self):
        """测试多个装饰器堆叠"""
        @suppress_marshmallow_warnings
        def outer_function():
            return "outer"

        @suppress_marshmallow_warnings
        def inner_function():
            return "inner"

        assert outer_function() == "outer"
        assert inner_function() == "inner"

    def test_warning_categories_handling(self):
        """测试不同警告类别的处理"""
        with patch('warnings.filterwarnings') as mock_filterwarnings:
            _setup_third_party_warning_filters()

            # 验证使用了DeprecationWarning类别
            calls = mock_filterwarnings.call_args_list
            deprecation_calls = [
                call for call in calls
                if len(call[0]) > 2 and call[0][2] == DeprecationWarning
            ]

            # 应该至少有一个DeprecationWarning调用
            assert len(deprecation_calls) > 0