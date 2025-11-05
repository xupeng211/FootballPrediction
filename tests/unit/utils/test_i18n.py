"""
国际化支持测试
Internationalization Support Test
"""

import pytest
from unittest.mock import patch, MagicMock

from src.utils.i18n import (
    I18nUtils,
    get_current_language,
    get_text,
    init_i18n,
    set_language,
    supported_languages,
)


class TestI18nBasic:
    """国际化基础功能测试"""

    def test_supported_languages(self):
        """测试支持的语言列表"""
        assert isinstance(supported_languages, dict)
        assert "zh" in supported_languages
        assert "en" in supported_languages
        assert supported_languages["zh"] == "zh_CN"
        assert supported_languages["en"] == "en_US"

    def test_get_text_basic(self):
        """测试基础翻译功能"""
        # 测试返回默认值
        result = get_text("test.key", "默认值")
        assert result == "默认值"

        # 测试返回键名
        result = get_text("test.key")
        assert result == "test.key"

    def test_get_text_edge_cases(self):
        """测试翻译功能边界情况"""
        # 空键
        result = get_text("", "空键默认值")
        assert result == "空键默认值"

        # 空默认值
        result = get_text("test.key", "")
        assert result == "test.key"

        # 特殊字符
        result = get_text("special.key", "特殊字符@#$%")
        assert result == "特殊字符@#$%"

    def test_set_language_valid(self):
        """测试设置有效语言"""
        # 设置中文
        set_language("zh")
        assert get_current_language() == "zh"

        # 设置英文
        set_language("en")
        assert get_current_language() == "en"

        # 设置带区域的语言代码
        set_language("zh-CN")
        assert get_current_language() == "zh-CN"

        set_language("en-US")
        assert get_current_language() == "en-US"

    def test_set_language_invalid(self):
        """测试设置无效语言"""
        # 保存当前语言
        original_lang = get_current_language()

        # 尝试设置无效语言
        set_language("invalid_lang")
        # 应该保持原值
        assert get_current_language() == original_lang

        # 测试空字符串
        set_language("")
        assert get_current_language() == original_lang

    def test_get_current_language(self):
        """测试获取当前语言"""
        # 设置语言并验证
        set_language("zh")
        assert get_current_language() == "zh"

        set_language("en")
        assert get_current_language() == "en"


class TestI18nUtils:
    """I18nUtils工具类测试"""

    def test_translate_basic(self):
        """测试基础翻译功能"""
        result = I18nUtils.translate("test.key")
        assert result == "test.key"

        result = I18nUtils.translate("test.key", "en")
        assert result == "test.key"

    def test_translate_edge_cases(self):
        """测试翻译功能边界情况"""
        # 空键
        result = I18nUtils.translate("")
        assert result == ""

        # 特殊字符键
        result = I18nUtils.translate("special.key@#$")
        assert result == "special.key@#$"

        # 不同语言参数
        result = I18nUtils.translate("test", "zh")
        assert result == "test"

        result = I18nUtils.translate("test", "invalid_lang")
        assert result == "test"

    def test_get_supported_languages(self):
        """测试获取支持的语言"""
        languages = I18nUtils.get_supported_languages()
        assert isinstance(languages, dict)
        assert len(languages) >= 2  # 至少支持中英文
        assert "zh" in languages
        assert "en" in languages


class TestI18nInit:
    """国际化初始化测试"""

    @patch('src.utils.i18n.gettext')
    @patch('src.utils.i18n.os.getenv')
    def test_init_i18n_success(self, mock_getenv, mock_gettext):
        """测试成功初始化"""
        mock_getenv.return_value = "zh_CN"

        init_i18n()

        # 验证调用了相关方法
        mock_getenv.assert_called_once_with("LANGUAGE", "zh_CN")

    @patch('src.utils.i18n.gettext')
    def test_init_i18n_with_exception(self, mock_gettext):
        """测试初始化异常处理"""
        # 模拟gettext抛出异常
        mock_gettext.bindtextdomain.side_effect = ValueError("Test error")

        # 应该不抛出异常
        init_i18n()  # 应该正常完成

    @patch('src.utils.i18n.gettext.bindtextdomain')
    @patch('src.utils.i18n.gettext.textdomain')
    @patch('src.utils.i18n.gettext.install')
    def test_init_i18n_full_flow(self, mock_install, mock_textdomain, mock_bindtextdomain):
        """测试完整的初始化流程"""
        init_i18n()

        # 验证所有gettext方法都被调用
        mock_bindtextdomain.assert_called_once()
        mock_textdomain.assert_called_once()
        mock_install.assert_called_once()


class TestI18nIntegration:
    """国际化集成测试"""

    def test_language_state_persistence(self):
        """测试语言状态持久性"""
        # 设置语言
        set_language("zh")

        # 多次调用应该保持一致
        assert get_current_language() == "zh"
        assert get_current_language() == "zh"
        assert get_current_language() == "zh"

    def test_multiple_language_switches(self):
        """测试多次语言切换"""
        # 在多种语言间切换
        languages = ["zh", "en", "zh-CN", "en-US"]

        for lang in languages:
            set_language(lang)
            assert get_current_language() == lang

    def test_i18n_utils_with_global_state(self):
        """测试I18nUtils与全局状态的交互"""
        # 设置全局语言
        set_language("zh")

        # I18nUtils应该独立工作（当前实现是独立的）
        result = I18nUtils.translate("test")
        assert result == "test"

        # 切换语言不应该影响I18nUtils
        set_language("en")
        result = I18nUtils.translate("test")
        assert result == "test"


class TestI18nEdgeCases:
    """国际化边界情况测试"""

    def test_concurrent_language_access(self):
        """测试并发语言访问（简化版）"""
        # 快速连续访问
        set_language("zh")

        results = []
        for _ in range(10):
            results.append(get_current_language())

        # 所有结果应该一致
        assert all(r == "zh" for r in results)

    def test_language_case_sensitivity(self):
        """测试语言代码大小写敏感性"""
        set_language("zh")
        assert get_current_language() == "zh"

        # 测试不同大小写（当前实现不支持）
        set_language("ZH")
        assert get_current_language() == "zh"  # 应该保持原值

    def test_unsupported_language_codes(self):
        """测试不支持的语言代码"""
        original_lang = get_current_language()

        unsupported_codes = ["fr", "de", "ja", "ko", "invalid", "zh_Hans", "en_GB"]

        for code in unsupported_codes:
            set_language(code)
            assert get_current_language() == original_lang

    def test_empty_and_none_inputs(self):
        """测试空输入和None输入"""
        # get_text测试
        assert get_text("", "default") == "default"
        assert get_text("key", "") == "key"

        # set_language测试
        original_lang = get_current_language()
        set_language("")
        assert get_current_language() == original_lang


class TestI18nPerformance:
    """国际化性能测试"""

    def test_translation_performance(self):
        """测试翻译性能"""
        import time

        # 测试大量翻译调用
        start_time = time.time()

        for i in range(1000):
            get_text(f"test.key.{i}", f"default.{i}")

        end_time = time.time()
        duration = end_time - start_time

        # 应该在合理时间内完成（1秒内）
        assert duration < 1.0

    def test_language_switch_performance(self):
        """测试语言切换性能"""
        import time

        start_time = time.time()

        languages = ["zh", "en", "zh-CN", "en-US"]
        for _ in range(100):
            for lang in languages:
                set_language(lang)

        end_time = time.time()
        duration = end_time - start_time

        # 应该在合理时间内完成（0.5秒内）
        assert duration < 0.5