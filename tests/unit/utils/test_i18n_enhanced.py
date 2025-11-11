"""
I18n模块增强测试 - 快速提升覆盖率
测试国际化支持功能
"""

from pathlib import Path

from src.utils.i18n import (
    LOCALE_DIR,
    I18nUtils,
    get_current_language,
    get_text,
    init_i18n,
    set_language,
    supported_languages,
)


class TestI18nEnhanced:
    """国际化模块增强测试"""

    def test_supported_languages_dict(self):
        """测试支持的语言字典"""
        assert isinstance(supported_languages, dict)
        assert "zh" in supported_languages
        assert "en" in supported_languages
        assert supported_languages["zh"] == "zh_CN"
        assert supported_languages["en"] == "en_US"

    def test_locale_dir_path(self):
        """测试本地化目录路径"""
        assert isinstance(LOCALE_DIR, Path)
        assert LOCALE_DIR.name == "locales"
        assert LOCALE_DIR.exists()  # init_i18n应该已经创建了目录

    def test_init_i18n_function(self):
        """测试初始化国际化函数"""
        # 初始化应该成功执行（不抛出异常）
        try:
            init_i18n()
            assert True  # 如果到达这里说明初始化成功
        except Exception:
            raise AssertionError("init_i18n不应该抛出异常") from None

        # 多次调用应该也是安全的
        try:
            init_i18n()
            init_i18n()
            init_i18n()
            assert True
        except Exception:
            raise AssertionError("多次调用init_i18n应该是安全的") from None

    def test_get_text_with_default(self):
        """测试带默认值的获取翻译文本"""
        # 测试使用默认值
        result = get_text("welcome", "欢迎")
        assert result == "欢迎"

        # 测试使用默认值（英文）
        result = get_text("goodbye", "Goodbye")
        assert result == "Goodbye"

        # 测试使用空字符串作为默认值
        result = get_text("empty", "")
        assert result == "empty"  # 空字符串是falsy，所以返回键名

        # 测试使用None作为默认值
        result = get_text("key_only")
        assert result == "key_only"  # 应该返回键名

    def test_get_text_without_default(self):
        """测试不使用默认值的获取翻译文本"""
        # 没有默认值时应该返回键名
        result = get_text("user.login")
        assert result == "user.login"

        result = get_text("menu.settings")
        assert result == "menu.settings"

        result = get_text("error.404")
        assert result == "error.404"

    def test_get_text_edge_cases(self):
        """测试获取翻译文本的边界情况"""
        # 测试空键
        result = get_text("", "empty_key")
        assert result == "empty_key"

        # 测试长键
        long_key = "a" * 100
        result = get_text(long_key, "long_key")
        assert result == "long_key"

        # 测试特殊字符键
        special_key = "user.name@domain.com"
        result = get_text(special_key, "special")
        assert result == "special"

        # 测试Unicode键
        unicode_key = "测试.键名"
        result = get_text(unicode_key, "unicode")
        assert result == "unicode"

    def test_set_language_supported(self):
        """测试设置支持的语言"""
        # 设置为中文
        set_language("zh")
        assert get_current_language() == "zh"

        # 设置为英文
        set_language("en")
        assert get_current_language() == "en"

        # 使用完整格式设置
        set_language("zh-CN")
        assert get_current_language() == "zh-CN"

        set_language("en-US")
        assert get_current_language() == "en-US"

    def test_set_language_unsupported(self):
        """测试设置不支持的语言"""
        # 记录当前语言
        current_lang = get_current_language()

        # 尝试设置不支持的语言（应该被忽略）
        set_language("fr")  # 法语不支持
        assert get_current_language() == current_lang

        set_language("de")  # 德语不支持
        assert get_current_language() == current_lang

        set_language("invalid")
        assert get_current_language() == current_lang

        set_language("")  # 空语言
        assert get_current_language() == current_lang

    def test_get_current_language_default(self):
        """测试获取当前语言的默认值"""
        # 重置到默认状态
        set_language("zh")
        assert get_current_language() == "zh"

    def test_get_current_language_after_changes(self):
        """测试语言变更后的当前语言"""
        # 切换到不同语言
        set_language("en")
        assert get_current_language() == "en"

        set_language("zh-CN")
        assert get_current_language() == "zh-CN"

        # 无效语言变更应该保持原值
        current = get_current_language()
        set_language("invalid")
        assert get_current_language() == current

    def test_i18n_utils_translate(self):
        """测试I18nUtils翻译方法"""
        # 测试基本翻译（当前是简化实现，直接返回键）
        result = I18nUtils.translate("hello")
        assert result == "hello"

        result = I18nUtils.translate("user.profile")
        assert result == "user.profile"

        # 测试带语言参数的翻译
        result = I18nUtils.translate("welcome", "en")
        assert result == "welcome"

        result = I18nUtils.translate("welcome", "zh")
        assert result == "welcome"

    def test_i18n_utils_translate_edge_cases(self):
        """测试I18nUtils翻译边界情况"""
        # 测试空字符串
        result = I18nUtils.translate("")
        assert result == ""

        # 测试特殊字符
        result = I18nUtils.translate("!@#$%")
        assert result == "!@#$%"

        # 测试Unicode
        result = I18nUtils.translate("测试消息")
        assert result == "测试消息"

        # 测试长文本
        long_text = "a" * 1000
        result = I18nUtils.translate(long_text)
        assert result == long_text

    def test_i18n_utils_get_supported_languages(self):
        """测试I18nUtils获取支持语言"""
        languages = I18nUtils.get_supported_languages()

        assert isinstance(languages, dict)
        assert len(languages) >= 4  # 至少有zh, zh-CN, en, en-US

        # 验证特定语言存在
        assert "zh" in languages
        assert "zh-CN" in languages
        assert "en" in languages
        assert "en-US" in languages

        # 验证映射关系
        assert languages["zh"] == "zh_CN"
        assert languages["zh-CN"] == "zh_CN"
        assert languages["en"] == "en_US"
        assert languages["en-US"] == "en_US"

    def test_i18n_utils_methods_are_static(self):
        """测试I18nUtils方法是静态的"""
        # 直接调用应该正常工作（静态方法）
        result1 = I18nUtils.translate("test")
        assert result1 == "test"

        result2 = I18nUtils.get_supported_languages()
        assert isinstance(result2, dict)

        # 不需要实例化，直接通过类调用
        assert callable(I18nUtils.translate)
        assert callable(I18nUtils.get_supported_languages)

    def test_integration_workflow(self):
        """测试国际化集成工作流程"""
        # 1. 初始化系统
        init_i18n()

        # 2. 设置语言
        set_language("zh")

        # 3. 获取当前语言
        current_lang = get_current_language()
        assert current_lang == "zh"

        # 4. 获取翻译文本
        welcome_text = get_text("welcome", "欢迎")
        assert welcome_text == "欢迎"

        # 5. 使用工具类翻译
        utils_text = I18nUtils.translate("menu.home")
        assert utils_text == "menu.home"

        # 6. 切换语言
        set_language("en")
        assert get_current_language() == "en"

        # 7. 获取支持的语言列表
        supported = I18nUtils.get_supported_languages()
        assert isinstance(supported, dict)

    def test_global_state_management(self):
        """测试全局状态管理"""
        # 设置初始状态
        set_language("zh")
        assert get_current_language() == "zh"

        # 多次变更语言
        languages = ["en", "zh", "zh-CN", "en-US", "zh"]
        for lang in languages:
            set_language(lang)
            assert get_current_language() == lang

        # 验证最终状态
        assert get_current_language() == "zh"

    def test_error_handling_and_robustness(self):
        """测试错误处理和健壮性"""
        # 测试get_text的各种输入
        assert get_text("", "default") == "default"
        # None键在default or key表达式中会返回default
        result = get_text(None, "default")
        assert result == "default"  # None是falsy，返回default

        assert get_text("key", None) == "key"  # None默认值会返回键

        # 测试set_language的无效输入
        current = get_current_language()
        set_language(None)  # None不应该改变状态
        assert get_current_language() == current

        set_language(123)  # 数字不应该改变状态
        assert get_current_language() == current

        set_language([])  # 列表不应该改变状态
        assert get_current_language() == current

        # I18nUtils.translate应该能处理None（直接返回）
        assert I18nUtils.translate(None) is None
        assert I18nUtils.get_supported_languages() == supported_languages
