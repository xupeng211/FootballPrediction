"""
WarningFilters初始化测试 - 专门覆盖第24-28行初始化代码
"""

import pytest
import warnings
import logging
import sys
from unittest.mock import patch, MagicMock


class TestWarningFiltersInitialization:
    """专门测试warning_filters模块初始化的类"""

    def test_initialization_code_coverage_simple(self):
        """简单测试覆盖初始化代码"""
        # 模拟模块初始化时的错误处理
        with patch('warnings.filterwarnings', side_effect=ValueError("Test error")):
            with patch('src.utils.warning_filters.logger') as mock_logger:
                # 导入模块来触发初始化代码
                from src.utils import warning_filters

                # 这应该会触发第27-30行的错误处理
                # 验证logger.info被调用
                mock_logger.info.assert_called()

    def test_initialization_different_errors(self):
        """测试不同类型的初始化错误"""
        errors_to_test = [
            ValueError("ValueError test"),
            KeyError("KeyError test"),
            TypeError("TypeError test")
        ]

        for error in errors_to_test:
            with patch('warnings.filterwarnings', side_effect=error):
                with patch('src.utils.warning_filters.logger') as mock_logger:
                    # 重新导入模块
                    import importlib
                    importlib.reload(sys.modules['src.utils.warning_filters'])

                    # 验证错误被记录
                    mock_logger.info.assert_called()

    def test_warning_filters_setup_calls(self):
        """测试警告过滤器设置的调用次数"""
        with patch('warnings.filterwarnings') as mock_filterwarnings:
            from src.utils.warning_filters import setup_warning_filters

            setup_warning_filters()

            # 验证调用了4次filterwarnings
            assert mock_filterwarnings.call_count == 4

    def test_pytest_environment_check(self):
        """测试pytest环境检查"""
        # 确保pytest在sys.modules中
        assert 'pytest' in sys.modules

    def test_logger_exists(self):
        """测试logger存在"""
        from src.utils import warning_filters

        assert hasattr(warning_filters, 'logger')
        assert isinstance(warning_filters.logger, logging.Logger)

    def test_setup_function_return_value(self):
        """测试setup函数返回值"""
        from src.utils.warning_filters import setup_warning_filters

        result = setup_warning_filters()
        assert result is None  # 函数没有显式返回值

    def test_filterwarnings_parameters(self):
        """测试filterwarnings调用参数"""
        with patch('warnings.filterwarnings') as mock_filterwarnings:
            from src.utils.warning_filters import setup_warning_filters

            setup_warning_filters()

            # 检查调用参数
            calls = mock_filterwarnings.call_args_list

            # 应该有4次调用
            assert len(calls) == 4

            # 检查第一次调用 (UserWarning, tensorflow.*)
            assert calls[0][0] == ("ignore",)
            assert calls[0][1] == UserWarning
            assert "tensorflow" in str(calls[0][2])

            # 检查第二次调用 (DeprecationWarning, sklearn.*)
            assert calls[1][0] == ("ignore",)
            assert calls[1][1] == DeprecationWarning
            assert "sklearn" in str(calls[1][2])

            # 检查第三次调用 (FutureWarning, pandas.*)
            assert calls[2][0] == ("ignore",)
            assert calls[2][1] == FutureWarning
            assert "pandas" in str(calls[2][2])

            # 检查第四次调用 (PendingDeprecationWarning)
            assert calls[3][0] == ("ignore",)
            assert calls[3][1] == PendingDeprecationWarning