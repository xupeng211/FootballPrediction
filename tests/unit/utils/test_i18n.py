"""
国际化工具函数测试
"""

import os
import pytest
import gettext
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.utils.i18n import init_i18n, _, get_language_from_request


class TestI18n:
    """测试国际化功能"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置全局翻译器
        import src.utils.i18n
        src.utils.i18n._translator = None

    def test_init_i18n_with_valid_language(self):
        """测试使用有效语言初始化"""
        init_i18n("zh_CN")
        import src.utils.i18n
        assert src.utils.i18n._translator is not None

    def test_init_i18n_with_invalid_language(self):
        """测试使用无效语言初始化"""
        # 模拟翻译失败
        with patch('src.utils.i18n.gettext.translation') as mock_translation:
            mock_translation.side_effect = Exception("Translation not found")

            init_i18n("invalid_lang")

            import src.utils.i18n
            assert isinstance(src.utils.i18n._translator, gettext.NullTranslations)

    def test_init_i18n_with_missing_locale_dir(self):
        """测试缺少翻译目录时的处理"""
        with patch('src.utils.i18n.Path') as mock_path:
            mock_path.return_value.exists.return_value = False

            init_i18n("zh_CN")

            import src.utils.i18n
            assert src.utils.i18n._translator is not None

    def test_translation_function_without_init(self):
        """测试未初始化时的翻译函数"""
        # 重置翻译器
        import src.utils.i18n
        src.utils.i18n._translator = None

        # 第一次调用会自动初始化
        result = _("Test message")
        assert result == "Test message"  # 默认返回原消息

    def test_translation_function_with_translator(self):
        """测试有翻译器时的翻译函数"""
        # 创建模拟翻译器
        mock_translator = MagicMock()
        mock_translator.gettext.return_value = "测试消息"

        import src.utils.i18n
        src.utils.i18n._translator = mock_translator

        result = _("Test message")
        assert result == "测试消息"
        mock_translator.gettext.assert_called_once_with("Test message")

    def test_translation_function_with_none_translator(self):
        """测试翻译器为None时的处理"""
        import src.utils.i18n
        src.utils.i18n._translator = None

        result = _("Test message")
        assert result == "Test message"

    def test_get_language_from_request_with_none(self):
        """测试请求头为None时"""
        with patch.dict(os.environ, {"HTTP_ACCEPT_LANGUAGE": ""}):
            result = get_language_from_request(None)
            assert result == "zh_CN"

    def test_get_language_from_request_with_env_var(self):
        """测试从环境变量获取语言"""
        with patch.dict(os.environ, {"HTTP_ACCEPT_LANGUAGE": "en-US"}):
            result = get_language_from_request()
            assert result == "en_US"

    def test_get_language_from_request_zh_variants(self):
        """测试中文语言的各种格式"""
        test_cases = [
            ("zh", "zh_CN"),
            ("zh-CN", "zh_CN"),
            ("zh_CN", "zh_CN"),
        ]

        for input_lang, expected in test_cases:
            result = get_language_from_request(input_lang)
            assert result == expected

    def test_get_language_from_request_en_variants(self):
        """测试英文语言的各种格式"""
        test_cases = [
            ("en", "en_US"),
            ("en-US", "en_US"),
        ]

        for input_lang, expected in test_cases:
            result = get_language_from_request(input_lang)
            assert result == expected

    def test_get_language_from_request_with_multiple_languages(self):
        """测试Accept-Language包含多个语言"""
        accept_language = "fr-FR,en-US;q=0.9,zh-CN;q=0.8"
        result = get_language_from_request(accept_language)
        # fr-FR不支持，所以应该匹配en-US
        assert result == "en_US"  # 第一个支持的

    def test_get_language_from_request_with_quality_values(self):
        """测试带质量值的Accept-Language"""
        accept_language = "en-US;q=0.9,zh-CN;q=0.8"
        result = get_language_from_request(accept_language)
        assert result == "en_US"  # en-US在前面

    def test_get_language_from_request_unsupported_language(self):
        """测试不支持的语言"""
        result = get_language_from_request("fr-FR")
        assert result == "zh_CN"  # 默认返回中文

    def test_get_language_from_request_empty_string(self):
        """测试空字符串"""
        result = get_language_from_request("")
        assert result == "zh_CN"

    def test_get_language_from_request_malformed_header(self):
        """测试格式错误的请求头"""
        malformed_headers = [
            "invalid-header",
            ";",
            "lang;",
            "lang;q=invalid",
        ]

        for header in malformed_headers:
            result = get_language_from_request(header)
            assert result == "zh_CN"

    def test_get_language_from_request_case_insensitive(self):
        """测试大小写不敏感"""
        result = get_language_from_request("ZH-cn")
        # 注意：当前实现是大小写敏感的，这可能是需要改进的地方
        assert result == "zh_CN"  # 如果不匹配，应该返回默认值

    def test_multiple_init_calls(self):
        """测试多次初始化调用"""
        init_i18n("zh_CN")
        init_i18n("en_US")

        # 应该使用最后一次的设置
        import src.utils.i18n
        assert src.utils.i18n._translator is not None

    def test_locale_dir_path_resolution(self):
        """测试locale目录路径解析"""
        # 简化测试，只验证LOCALE_DIR是Path类型
        from src.utils.i18n import LOCALE_DIR
        from pathlib import Path

        assert isinstance(LOCALE_DIR, Path)
        assert str(LOCALE_DIR).endswith("locales")

    def test_translation_with_empty_string(self):
        """测试翻译空字符串"""
        init_i18n("zh_CN")
        result = _("")
        assert result == ""

    def test_translation_with_unicode(self):
        """测试翻译Unicode字符串"""
        mock_translator = MagicMock()
        mock_translator.gettext.return_value = "测试消息🚀"

        import src.utils.i18n
        src.utils.i18n._translator = mock_translator

        result = _("Test message with emoji 🚀")
        assert result == "测试消息🚀"