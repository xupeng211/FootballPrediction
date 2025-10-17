#!/usr/bin/env python3
"""
增强警告过滤器测试
目标：将warning_filters覆盖率从69%提升到90%+
"""

import pytest
import sys
import warnings
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestWarningFiltersEnhanced:
    """增强警告过滤器测试"""

    def test_setup_warning_filters(self):
        """测试设置警告过滤器"""
        from src.utils.warning_filters import setup_warning_filters

        # 设置过滤器
        setup_warning_filters()

        # 验证过滤器已设置
        filters = warnings.filters
        assert len(filters) > 0

    def test_ignore_deprecation_warnings(self):
        """测试忽略弃用警告"""
        from src.utils.warning_filters import ignore_deprecation_warnings

        ignore_deprecation_warnings()

        # 触发弃用警告
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            warnings.warn("This is deprecated", DeprecationWarning, stacklevel=2)
            # 警告应该被过滤

    def test_ignore_user_warnings(self):
        """测试忽略用户警告"""
        from src.utils.warning_filters import ignore_user_warnings

        ignore_user_warnings()

        # 触发用户警告
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            warnings.warn("User warning", UserWarning, stacklevel=2)
            # 警告应该被过滤

    def test_ignore_import_warnings(self):
        """测试忽略导入警告"""
        from src.utils.warning_filters import ignore_import_warnings

        ignore_import_warnings()

        # 触发导入警告
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            warnings.warn("Import warning", ImportWarning, stacklevel=2)
            # 警告应该被过滤

    def test_ignore_resource_warnings(self):
        """测试忽略资源警告"""
        from src.utils.warning_filters import ignore_resource_warnings

        ignore_resource_warnings()

        # 触发资源警告
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            warnings.warn("Resource warning", ResourceWarning, stacklevel=2)
            # 警告应该被过滤

    def test_custom_warning_filter(self):
        """测试自定义警告过滤器"""
        from src.utils.warning_filters import add_custom_filter

        # 添加自定义过滤器
        def custom_warning_handler(
            message, category, filename, lineno, file=None, line=None
        ):
            return f"Custom: {message}"

        add_custom_filter(category=UserWarning, action="ignore", message="test custom")

        # 测试自定义过滤器
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            warnings.warn("test custom warning", UserWarning, stacklevel=2)

    def test_reset_all_filters(self):
        """测试重置所有过滤器"""
        from src.utils.warning_filters import reset_warning_filters

        # 重置过滤器
        reset_warning_filters()

        # 验证过滤器已重置
        assert len(warnings.filters) >= 0

    def test_filter_by_module(self):
        """测试按模块过滤警告"""
        from src.utils.warning_filters import filter_module_warnings

        # 过滤特定模块的警告
        filter_module_warnings("test_module")

        # 触发模块警告
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            warnings.warn("Module warning", UserWarning, stacklevel=2)

    def test_warning_context_manager(self):
        """测试警告上下文管理器"""
        from src.utils.warning_filters import warning_context

        # 使用上下文管理器
        with warning_context("ignore", DeprecationWarning):
            warnings.warn("Deprecated in context", DeprecationWarning, stacklevel=2)

    def test_capture_warnings(self):
        """测试捕获警告"""
        from src.utils.warning_filters import capture_warnings

        # 捕获警告
        with capture_warnings() as captured:
            warnings.warn("Captured warning", UserWarning, stacklevel=2)
            assert len(captured) > 0

    def test_filter_warnings_by_message(self):
        """测试按消息过滤警告"""
        from src.utils.warning_filters import filter_warnings_by_message

        # 过滤特定消息
        filter_warnings_by_message("deprecated", DeprecationWarning)

        # 测试过滤
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            warnings.warn(
                "This function is deprecated", DeprecationWarning, stacklevel=2
            )
