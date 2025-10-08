import os
from unittest.mock import patch
from src.utils.i18n import _, get_language_from_request, init_i18n
import src.utils.i18n

"""
测试国际化工具模块
"""


class TestI18n:
    """测试国际化功能"""

    def test_init_i18n_with_valid_language(self):
        """测试使用有效语言初始化"""
        # 应该不抛出异常
        init_i18n("zh_CN")
        init_i18n("en_US")

    def test_init_i18n_with_invalid_language(self):
        """测试使用无效语言初始化"""
        # 应该不抛出异常，会使用fallback
        init_i18n("invalid_lang")

    def test_translate_function_without_init(self):
        """测试翻译函数（未初始化）"""
        # 重置全局翻译器
        src.utils.i18n._translator = None

        # 第一次调用会自动初始化
        result = _("Hello")
        assert isinstance(result, str)
        assert result == "Hello"

    def test_translate_function_after_init(self):
        """测试翻译函数（已初始化）"""
        init_i18n()
        result = _("Hello, World!")
        assert isinstance(result, str)
        # 由于没有翻译文件，应该返回原文
        assert result == "Hello, World!"

    def test_translate_function_with_unicode(self):
        """测试翻译Unicode文本"""
        result = _("你好，世界！")
        assert isinstance(result, str)
        assert result == "你好，世界！"

    def test_get_language_from_request_header_zh_cn(self):
        """测试从请求头获取中文语言"""
        result = get_language_from_request("zh-CN,zh;q=0.9,en;q=0.8")
        assert result == "zh_CN"

    def test_get_language_from_request_header_zh(self):
        """测试从请求头获取中文（简化）"""
        result = get_language_from_request("zh,en-US;q=0.9")
        assert result == "zh_CN"

    def test_get_language_from_request_header_en(self):
        """测试从请求头获取英文"""
        result = get_language_from_request("en-US,en;q=0.9")
        assert result == "en_US"

    def test_get_language_from_request_header_en_short(self):
        """测试从请求头获取英文（简化）"""
        result = get_language_from_request("en,zh;q=0.9")
        assert result == "en_US"

    def test_get_language_from_request_multiple_languages(self):
        """测试从多语言请求头获取"""
        result = get_language_from_request("fr-FR,de;q=0.9,en-US;q=0.8,zh-CN;q=0.7")
        # 第一个匹配的支持的语言是en-US
        assert result == "en_US"

    def test_get_language_from_request_unsupported_language(self):
        """测试不支持的语言"""
        result = get_language_from_request("fr-FR,de;q=0.9")
        # 应该返回默认的中文
        assert result == "zh_CN"

    def test_get_language_from_request_none(self):
        """测试空请求头"""
        result = get_language_from_request(None)
        assert result == "zh_CN"

    def test_get_language_from_request_empty_string(self):
        """测试空字符串请求头"""
        result = get_language_from_request("")
        assert result == "zh_CN"

    def test_get_language_from_request_with_quality_values(self):
        """测试带质量值的请求头"""
        result = get_language_from_request("zh-CN;q=0.8,en-US;q=0.9")
        # 应该优先选择en-US（q值更高）
        assert result == "en_US"

    def test_get_language_from_request_from_env(self):
        """测试从环境变量获取语言"""
        with patch.dict(os.environ, {"HTTP_ACCEPT_LANGUAGE": "en-US"}):
            result = get_language_from_request()
            assert result == "en_US"

    def test_get_language_from_request_complex_header(self):
        """测试复杂的请求头"""
        result = get_language_from_request("zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4")
        assert result == "zh_CN"

    def test_translate_function_multiple_calls(self):
        """测试多次调用翻译函数"""
        init_i18n()
        texts = ["Hello", "World", "Test", "你好"]
        for text in texts:
            result = _(text)
            assert result == text

    def test_translate_function_empty_string(self):
        """测试翻译空字符串"""
        result = _("")
        assert result == ""
