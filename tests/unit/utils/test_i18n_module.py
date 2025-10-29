# TODO: Consider creating a fixture for 4 repeated Mock creations

# TODO: Consider creating a fixture for 4 repeated Mock creations

from unittest.mock import MagicMock, patch

"""
国际化模块测试
"""

from pathlib import Path

import pytest

from src.utils.i18n import LOCALE_DIR, init_i18n, supported_languages


@pytest.mark.unit
class TestI18nModule:
    """国际化模块测试"""

    def test_supported_languages(self):
        """测试支持的语言"""
        assert isinstance(supported_languages, dict)
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

    @patch("src.utils.i18n.gettext")
    @patch("src.utils.i18n.os.getenv")
    def test_init_i18n(self, mock_getenv, mock_gettext):
        """测试初始化国际化"""
        # 设置模拟
        mock_getenv.return_value = "zh_CN"
        MagicMock()
        mock_gettext.bindtextdomain = MagicMock()
        mock_gettext.textdomain = MagicMock()
        mock_gettext.install = MagicMock()

        # 调用函数
        init_i18n()

        # 验证目录创建
        mock_gettext.bindtextdomain.assert_called_once()
        mock_gettext.textdomain.assert_called_once()
        mock_gettext.install.assert_called_once()

    @patch("src.utils.i18n.gettext")
    @patch("src.utils.i18n.os.getenv")
    def test_init_i18n_with_exception(self, mock_getenv, mock_gettext):
        """测试初始化国际化时异常处理"""
        # 设置模拟抛出异常
        mock_getenv.return_value = "zh_CN"
        mock_gettext.bindtextdomain.side_effect = Exception("Test exception")

        # 调用函数应该不抛出异常
        init_i18n()  # 应该正常返回，不抛出异常

    def test_init_i18n_creates_directory(self, tmp_path):
        """测试初始化时创建目录"""
        # 使用临时目录
        test_locale_dir = tmp_path / "test_locales"

        # 修改LOCALE_DIR为测试路径
        original_locale_dir = None
        try:
            import src.utils.i18n as i18n_module

            original_locale_dir = i18n_module.LOCALE_DIR
            i18n_module.LOCALE_DIR = test_locale_dir

            # 验证目录不存在
            assert not test_locale_dir.exists()

            # 调用初始化
            i18n_module.init_i18n()

            # 验证目录被创建
            assert test_locale_dir.exists()

        finally:
            # 恢复原始值
            if original_locale_dir:
                i18n_module.LOCALE_DIR = original_locale_dir
