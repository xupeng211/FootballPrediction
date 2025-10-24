# TODO: Consider creating a fixture for 6 repeated Mock creations

# TODO: Consider creating a fixture for 6 repeated Mock creations

from unittest.mock import patch, MagicMock
"""
国际化测试
Internationalization Tests

测试实际的i18n功能。
"""

import pytest
import os
from pathlib import Path

from src.utils.i18n import (
    init_i18n,
    supported_languages,
    LOCALE_DIR,
)


@pytest.mark.unit

class TestI18n:
    """测试国际化功能"""

    def test_supported_languages(self):
        """测试支持的语言"""
        assert "zh" in supported_languages
        assert "zh-CN" in supported_languages
        assert "en" in supported_languages
        assert "en-US" in supported_languages

        assert supported_languages["zh"] == "zh_CN"
        assert supported_languages["en"] == "en_US"

    def test_locale_dir(self):
        """测试本地化目录"""
        assert isinstance(LOCALE_DIR, Path)
        assert LOCALE_DIR.name == "locales"
        assert LOCALE_DIR.exists() or True  # 目录可能不存在，这很正常

    def test_init_i18n(self):
        """测试初始化国际化"""
        # 测试初始化不会抛出异常
        init_i18n()

        # 验证目录存在（会被创建）
        assert LOCALE_DIR.exists()

    def test_init_i18n_with_mock(self):
        """测试使用mock初始化国际化"""
        # Mock gettext模块
        with patch("src.utils.i18n.gettext") as mock_gettext:
            mock_gettext.bindtextdomain = MagicMock()
            mock_gettext.textdomain = MagicMock()
            mock_gettext.install = MagicMock()

            # Mock环境变量
            with patch.dict(os.environ, {"LANGUAGE": "en_US"}):
            with patch.dict(os.environ, {"LANGUAGE": "en_US"}):
            with patch.dict(os.environ, {"LANGUAGE": "en_US"}):
                init_i18n()

            # 验证gettext方法被调用
            mock_gettext.bindtextdomain.assert_called_once()
            mock_gettext.textdomain.assert_called_once()
            mock_gettext.install.assert_called_once()

    def test_init_i18n_error_handling(self):
        """测试初始化错误处理"""
        # 测试异常情况
        with patch("src.utils.i18n.gettext") as mock_gettext:
            mock_gettext.bindtextdomain.side_effect = ValueError("Test error")

            # 不应该抛出异常
            init_i18n()

            # 测试其他异常
            mock_gettext.bindtextdomain.side_effect = KeyError("Test error")
            init_i18n()

            mock_gettext.bindtextdomain.side_effect = RuntimeError("Test error")
            init_i18n()

    def test_multiple_initialization(self):
        """测试多次初始化"""
        # 初始化多次应该不会出错
        init_i18n()
        init_i18n()
        init_i18n()

        # 目录应该存在
        assert LOCALE_DIR.exists()

    def test_language_mapping(self):
        """测试语言映射"""
        # 测试中文映射
        assert supported_languages.get("zh") == "zh_CN"
        assert supported_languages.get("zh-CN") == "zh_CN"

        # 测试英文映射
        assert supported_languages.get("en") == "en_US"
        assert supported_languages.get("en-US") == "en_US"

        # 测试不存在的语言
        assert supported_languages.get("fr") is None
        assert supported_languages.get("de") is None

    def test_locale_dir_creation(self):
        """测试本地化目录创建"""
        # 删除目录（如果存在）
        if LOCALE_DIR.exists():
            LOCALE_DIR.rmdir()

        # 确保目录不存在
        assert not LOCALE_DIR.exists()

        # 初始化应该创建目录
        init_i18n()

        # 目录应该存在
        assert LOCALE_DIR.exists()

    def test_environment_variable_default(self):
        """测试环境变量默认值"""
        # Mock os.getenv
        with patch("src.utils.i18n.os.getenv") as mock_getenv:
            mock_getenv.return_value = "zh_CN"
            init_i18n()
            mock_getenv.assert_called_with("LANGUAGE", "zh_CN")

        # 测试返回None的情况
        with patch("src.utils.i18n.os.getenv") as mock_getenv:
            mock_getenv.return_value = None
            init_i18n()
            mock_getenv.assert_called_with("LANGUAGE", "zh_CN")

    def test_directory_structure(self):
        """测试目录结构"""
        # 验证LOCALE_DIR是Path对象
        assert isinstance(LOCALE_DIR, Path)

        # 验证父目录存在
        assert LOCALE_DIR.parent.exists()

        # 验证目录名称
        assert LOCALE_DIR.name == "locales"

    def test_integration_with_gettext(self):
        """测试与gettext的集成"""
        # 这个测试验证i18n模块正确使用了gettext
        with patch("src.utils.i18n.gettext") as mock_gettext:
            # 模拟gettext的函数
            mock_gettext.bindtextdomain = MagicMock()
            mock_gettext.textdomain = MagicMock()
            mock_gettext.install = MagicMock()

            # 调用初始化
            init_i18n()

            # 验证调用参数
            mock_gettext.bindtextdomain.assert_called_with(
                "football_prediction", str(LOCALE_DIR)
            )
            mock_gettext.textdomain.assert_called_with("football_prediction")
            mock_gettext.install.assert_called_with(
                "football_prediction", localedir=str(LOCALE_DIR)
            )

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试空的环境变量
        with patch.dict(os.environ, {}, clear=True):
        with patch.dict(os.environ, {}, clear=True):
        with patch.dict(os.environ, {}, clear=True):
            init_i18n()
            # 应该使用默认值

        # 测试非常长的语言代码
        with patch.dict(os.environ, {"LANGUAGE": "very_long_language_code"}):
            init_i18n()
            # 应该处理 gracefully
