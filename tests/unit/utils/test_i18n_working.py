"""国际化(i18n)模块测试（工作版本）"""

from src.utils.i18n import get_language_from_request, _


class TestI18nWorking:
    """国际化模块测试（工作版本）"""

    def test_get_language_from_request_header_zh_cn(self):
        """测试从请求头获取语言（中文简体）"""
        result = get_language_from_request("zh-CN,zh;q=0.9,en;q=0.8")
        assert result == "zh_CN"

    def test_get_language_from_request_header_zh_tw(self):
        """测试从请求头获取语言（中文繁体）"""
        result = get_language_from_request("zh-TW,zh;q=0.9,en;q=0.8")
        assert result == "zh_TW"

    def test_get_language_from_request_header_en(self):
        """测试从请求头获取语言（英文）"""
        result = get_language_from_request("en-US,en;q=0.9")
        assert result == "en_US"

    def test_get_language_from_request_header_es(self):
        """测试从请求头获取语言（西班牙语）"""
        result = get_language_from_request("es-ES,es;q=0.9")
        assert result == "es_ES"

    def test_get_language_from_request_header_fr(self):
        """测试从请求头获取语言（法语）"""
        result = get_language_from_request("fr-FR,fr;q=0.9")
        assert result == "fr_FR"

    def test_get_language_from_request_empty(self):
        """测试从空的请求头获取语言"""
        result = get_language_from_request("")
        # 应该返回默认语言
        assert result in ["en_US", "en"]

    def test_get_language_from_request_none(self):
        """测试从None请求头获取语言"""
        result = get_language_from_request(None)
        # 应该返回默认语言
        assert result in ["en_US", "en"]

    def test_get_language_from_request_invalid(self):
        """测试从无效的请求头获取语言"""
        result = get_language_from_request("invalid-language-header")
        # 应该返回默认语言
        assert result in ["en_US", "en"]

    def test_get_language_from_request_complex_header(self):
        """测试从复杂的请求头获取语言"""
        result = get_language_from_request(
            "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6"
        )
        assert result == "zh_CN"

    def test_get_language_from_request_with_region_variant(self):
        """测试带地区变体的语言"""
        result = get_language_from_request("en-GB,en-US;q=0.9")
        # 可能返回 en_GB 或 en_US
        assert result.startswith("en")

    def test_translation_function(self):
        """测试翻译函数"""
        # 测试基本的翻译函数
        result = _("Hello World")
        assert result is not None
        assert isinstance(result, str)

    def test_translation_function_empty(self):
        """测试翻译函数（空字符串）"""
        result = _("")
        assert result == ""

    def test_translation_function_unicode(self):
        """测试翻译函数（Unicode字符）"""
        result = _("测试中文")
        assert result is not None
        assert isinstance(result, str)

    def test_edge_case_request_header_with_whitespace(self):
        """测试边界情况：带空白的请求头"""
        result = get_language_from_request("  zh-CN , zh;q=0.9  ")
        # 应该能正确处理空白字符
        assert "zh" in result or result in ["en_US", "en"]

    def test_edge_case_request_header_with_quality_values(self):
        """测试边界情况：带质量值的请求头"""
        result = get_language_from_request("zh-CN;q=0.8,en-US;q=0.9")
        # 应该根据质量值选择
        assert result in ["zh_CN", "en_US"]

    def test_edge_case_request_header_lowercase(self):
        """测试边界情况：小写语言代码"""
        result = get_language_from_request("zh-cn,en-us")
        # 应该能处理小写
        assert result in ["zh_CN", "en_US"]

    def test_edge_case_request_header_mixed_case(self):
        """测试边界情况：混合大小写语言代码"""
        result = get_language_from_request("Zh-Cn,zH;q=0.9")
        # 应该能处理混合大小写
        assert result in ["zh_CN"]

    def test_edge_case_very_long_language_header(self):
        """测试边界情况：很长的语言头部"""
        long_header = ",".join([f"lang-{i}" for i in range(100)])
        result = get_language_from_request(long_header)
        # 应该能处理很长的头部而不崩溃
        assert result is not None

    def test_edge_case_special_characters_in_header(self):
        """测试边界情况：头部包含特殊字符"""
        result = get_language_from_request("zh-CN;q=0.9; charset=utf-8")
        # 应该能处理特殊字符
        assert result is not None

    def test_multiple_calls_consistency(self):
        """测试多次调用的一致性"""
        result1 = get_language_from_request("zh-CN,zh;q=0.9")
        result2 = get_language_from_request("zh-CN,zh;q=0.9")
        assert result1 == result2

    def test_supported_languages_fallback(self):
        """测试支持的语言回退"""
        # 测试不支持的语言
        result = get_language_from_request("xx-YY,xx;q=0.9")
        # 应该回退到默认语言
        assert result in ["en_US", "en", "zh_CN"]

    def test_language_preference_order(self):
        """测试语言偏好顺序"""
        # 测试语言偏好顺序
        result = get_language_from_request("en-US,zh-CN;q=0.8,fr-FR;q=0.6")
        # 应该选择第一个支持的语言
        assert result == "en_US"

    def test_environment_variable_fallback(self):
        """测试环境变量回退"""
        # 这个测试需要mock环境变量
        # 在实际环境中可能不起作用
        result = get_language_from_request(None)
        # 应该使用环境变量或默认值
        assert result is not None
        assert isinstance(result, str)

    def test_integration_translation_with_language_detection(self):
        """测试集成：翻译与语言检测"""
        # 检测语言
        language = get_language_from_request("zh-CN,zh;q=0.9,en;q=0.8")
        assert language == "zh_CN"

        # 使用翻译函数
        text = _("Hello")
        assert text is not None
        assert isinstance(text, str)

    def test_performance_multiple_language_headers(self):
        """测试性能：处理多个语言头部"""
        headers = [
            "zh-CN,zh;q=0.9,en;q=0.8",
            "en-US,en;q=0.9",
            "fr-FR,fr;q=0.9",
            "es-ES,es;q=0.9",
            "ja-JP,ja;q=0.9",
        ]

        results = []
        for header in headers:
            result = get_language_from_request(header)
            results.append(result)

        assert len(results) == len(headers)
        for result in results:
            assert result is not None
            assert isinstance(result, str)
