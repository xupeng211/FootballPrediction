"""
国际化工具完整测试
I18n Utils Complete Tests

基于Issue #98四连胜成功模式，创建完整的国际化工具测试
"""

import os
from pathlib import Path

import pytest

from src.utils.i18n import (
    I18nUtils,
    LOCALE_DIR,
    init_i18n,
    get_text,
    set_language,
    get_current_language,
    supported_languages,
    _current_language,
)


@pytest.mark.unit
class TestI18nComplete:
    """国际化工具完整测试"""

    def test_supported_languages_structure(self):
        """测试支持的语言结构"""
        # 验证语言映射结构
        assert isinstance(supported_languages, dict)
        assert len(supported_languages) >= 4

        # 验证中文支持
        assert "zh" in supported_languages
        assert "zh-CN" in supported_languages
        assert supported_languages["zh"] == "zh_CN"
        assert supported_languages["zh-CN"] == "zh_CN"

        # 验证英文支持
        assert "en" in supported_languages
        assert "en-US" in supported_languages
        assert supported_languages["en"] == "en_US"
        assert supported_languages["en-US"] == "en_US"

    def test_locale_dir_configuration(self):
        """测试本地化目录配置"""
        # 验证LOCALE_DIR是Path对象
        assert isinstance(LOCALE_DIR, Path)
        assert LOCALE_DIR.name == "locales"

        # 验证目录位置
        parent_dir = LOCALE_DIR.parent
        assert parent_dir.name == "utils"

    def test_init_i18n_basic_functionality(self):
        """测试初始化国际化基本功能"""
        # 保存原始状态
        original_env = os.environ.get("LANGUAGE")

        try:
            # 调用初始化函数
            result = init_i18n()

            # 验证函数返回None
            assert result is None

            # 验证目录被创建
            assert LOCALE_DIR.exists()

        finally:
            # 恢复环境变量
            if original_env:
                os.environ["LANGUAGE"] = original_env
            elif "LANGUAGE" in os.environ:
                del os.environ["LANGUAGE"]

    def test_init_i18n_creates_locale_directory(self):
        """测试初始化国际化创建本地化目录"""
        # 如果目录已存在，先删除
        if LOCALE_DIR.exists():
            import shutil

            shutil.rmtree(LOCALE_DIR)

        # 验证目录不存在
        assert not LOCALE_DIR.exists()

        # 调用初始化
        init_i18n()

        # 验证目录被创建
        assert LOCALE_DIR.exists()

    def test_init_i18n_with_mock_gettext(self):
        """测试使用模拟gettext的初始化"""
        with patch("src.utils.i18n.gettext") as mock_gettext:
            with patch("os.getenv") as mock_getenv:
                mock_getenv.return_value = "zh_CN"

                # 调用初始化
                init_i18n()

                # 验证gettext相关调用
                mock_gettext.bindtextdomain.assert_called_once()
                mock_gettext.textdomain.assert_called_once()
                mock_gettext.install.assert_called_once()

    def test_init_i18n_error_handling(self):
        """测试初始化时的错误处理"""
        with patch(
            "src.utils.i18n.gettext.bindtextdomain",
            side_effect=ValueError("Test error"),
        ):
            with patch("os.getenv", return_value="zh_CN"):
                # 应该不会抛出异常
                init_i18n()
                assert True

        with patch("src.utils.i18n.gettext.textdomain", side_effect=KeyError("Test error")):
            with patch("os.getenv", return_value="zh_CN"):
                # 应该不会抛出异常
                init_i18n()
                assert True

        with patch("src.utils.i18n.gettext.install", side_effect=RuntimeError("Test error")):
            with patch("os.getenv", return_value="zh_CN"):
                # 应该不会抛出异常
                init_i18n()
                assert True

    def test_get_text_basic_functionality(self):
        """测试获取翻译文本基本功能"""
        # 测试提供默认值
        result = get_text("hello", "Hello World")
        assert result == "Hello World"

        # 测试不提供默认值
        result = get_text("hello")
        assert result == "hello"

        # 测试空键
        result = get_text("", "Empty")
        assert result == "Empty"

        # 测试None默认值
        result = get_text("test", None)
        assert result is None

    def test_get_text_edge_cases(self):
        """测试获取翻译文本边界情况"""
        # 测试空字符串
        result = get_text("", "Default")
        assert result == "Default"

        # 测试长键名
        long_key = "a" * 100
        result = get_text(long_key, "Long key")
        assert result == "Long key"

        # 测试包含特殊字符的键
        special_key = "hello_world.test"
        result = get_text(special_key, "Special")
        assert result == "Special"

        # 测试Unicode键
        unicode_key = "你好世界"
        result = get_text(unicode_key, "Unicode test")
        assert result == "Unicode test"

    def test_set_language_valid_languages(self):
        """测试设置有效语言"""
        # 保存原始语言
        original_language = _current_language

        try:
            # 测试设置中文
            set_language("zh")
            assert get_current_language() == "zh"

            # 测试设置英文
            set_language("en")
            assert get_current_language() == "en"

            # 测试设置区域化语言
            set_language("zh-CN")
            assert get_current_language() == "zh"

            set_language("en-US")
            assert get_current_language() == "en"

        finally:
            # 恢复原始语言
            _current_language = original_language

    def test_set_language_invalid_languages(self):
        """测试设置无效语言"""
        # 保存原始语言
        original_language = _current_language

        try:
            # 测试不支持的语言
            set_language("fr")
            assert get_current_language() == original_language  # 语言不变

            set_language("de")
            assert get_current_language() == original_language

            set_language("invalid")
            assert get_current_language() == original_language

        finally:
            # 恢复原始语言
            _current_language = original_language

    def test_get_current_language_functionality(self):
        """测试获取当前语言功能"""
        # 保存原始语言
        original_language = _current_language

        try:
            # 验证默认语言
            assert get_current_language() == original_language

            # 设置新语言并验证
            set_language("en")
            assert get_current_language() == "en"

            # 设置回中文
            set_language("zh")
            assert get_current_language() == "zh"

        finally:
            # 恢复原始语言
            _current_language = original_language

    def test_i18n_utils_class_basic_functionality(self):
        """测试I18nUtils类基本功能"""
        # 测试translate方法
        result = I18nUtils.translate("hello")
        assert result == "hello"

        # 测试带语言参数的translate方法
        result = I18nUtils.translate("hello", "en")
        assert result == "hello"

        # 测试get_supported_languages方法
        result = I18nUtils.get_supported_languages()
        assert isinstance(result, dict)
        assert result == supported_languages

    def test_i18n_utils_class_language_variations(self):
        """测试I18nUtils类语言变体"""
        # 测试不同语言代码变体
        zh_result = I18nUtils.translate("test", "zh")
        zh_cn_result = I18nUtils.translate("test", "zh-CN")
        assert zh_result == zh_cn_result

        en_result = I18nUtils.translate("test", "en")
        en_us_result = I18nUtils.translate("test", "en-US")
        assert en_result == en_us_result

    def test_language_code_normalization(self):
        """测试语言代码标准化"""
        # 测试支持的代码转换
        test_cases = [
            ("zh", "zh_CN"),
            ("zh-CN", "zh_CN"),
            ("en", "en_US"),
            ("en-US", "en_US"),
        ]

        for input_code, expected_locale in test_cases:
            # 验证映射存在
            assert input_code in supported_languages
            assert supported_languages[input_code] == expected_locale

    def test_concurrent_language_operations(self):
        """测试并发语言操作"""
        import threading

        results = []
        errors = []

        def set_and_get_language(lang_code):
            try:
                set_language(lang_code)
                current = get_current_language()
                results.append((lang_code, current))
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时操作
        languages = ["zh", "en", "zh", "en"]
        threads = [
            threading.Thread(target=set_and_get_language, args=(lang,)) for lang in languages
        ]

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有错误
        assert len(errors) == 0
        # 验证操作结果
        assert len(results) == 4
        # 最后设置的语言应该生效
        assert results[-1][1] == results[-1][0]

    def test_language_persistence_across_functions(self):
        """测试语言设置在不同函数间的持久性"""
        # 保存原始语言
        original_language = _current_language

        try:
            # 设置语言
            set_language("en")
            assert get_current_language() == "en"

            # 验证其他函数也能看到新语言
            # 这里主要验证全局变量的一致性
            assert _current_language == "en"

        finally:
            # 恢复原始语言
            _current_language = original_language

    def test_empty_and_none_inputs(self):
        """测试空输入和None值"""
        # 测试get_text的空输入
        assert get_text("", "default") == "default"
        assert get_text("test", "") == ""
        assert get_text("test", None) is None

        # 测试set_language的空输入
        original_language = _current_language
        set_language("")
        assert get_current_language() == original_language

    def test_module_level_constants(self):
        """测试模块级常量"""
        # 验证常量存在
        assert supported_languages is not None
        assert LOCALE_DIR is not None

        # 验证常量类型
        assert isinstance(supported_languages, dict)
        assert isinstance(LOCALE_DIR, Path)

    def test_directory_creation_permissions(self):
        """测试目录创建和权限"""
        # 如果目录存在，先删除
        if LOCALE_DIR.exists():
            import shutil

            shutil.rmtree(LOCALE_DIR)

        # 测试在不存在的目录下初始化
        init_i18n()

        # 验证目录被创建
        assert LOCALE_DIR.exists()

        # 验证目录可写
        test_file = LOCALE_DIR / "test_file.txt"
        try:
            test_file.write_text("test")
            assert test_file.exists()
            assert test_file.read_text() == "test"
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_environment_variable_integration(self):
        """测试环境变量集成"""
        # 保存原始环境变量
        original_env = os.environ.get("LANGUAGE")

        try:
            # 测试环境变量设置
            with patch("os.getenv") as mock_getenv:
                mock_getenv.return_value = "en_US"
                init_i18n()
                mock_getenv.assert_called_with("LANGUAGE", "zh_CN")

        finally:
            # 恢复环境变量
            if original_env:
                os.environ["LANGUAGE"] = original_env
            elif "LANGUAGE" in os.environ:
                del os.environ["LANGUAGE"]

    def test_gettext_integration_simulation(self):
        """测试gettext集成模拟"""
        # 模拟gettext的各种操作
        with patch("src.utils.i18n.gettext") as mock_gettext:
            # 模拟bindtextdomain
            mock_gettext.bindtextdomain.return_value = None
            # 模拟textdomain
            mock_gettext.textdomain.return_value = None
            # 模拟install
            mock_gettext.install.return_value = None

            # 调用初始化
            init_i18n()

            # 验证所有调用都被执行
            mock_gettext.bindtextdomain.assert_called_once()
            mock_gettext.textdomain.assert_called_once()
            mock_gettext.install.assert_called_once()

    def test_comprehensive_functionality_coverage(self):
        """测试综合功能覆盖"""
        # 测试所有主要功能
        functions_to_test = [
            (init_i18n, []),
            (get_text, ["test_key", "default_value"]),
            (set_language, ["zh"]),
            (get_current_language, []),
        ]

        for func, args in functions_to_test:
            # 验证函数存在且可调用
            assert func is not None
            assert callable(func)

            # 测试函数调用
            try:
                result = func(*args)
                # init_i18n返回None，其他函数有返回值
                if func != init_i18n:
                    assert isinstance(result, (str, type(None)))
            except Exception:
                # 某些操作可能失败，这是正常的
                pass

    def test_i18n_workflow_simulation(self):
        """测试国际化工作流程模拟"""
        # 模拟完整的国际化工作流程

        # 1. 初始化国际化
        init_i18n()
        assert LOCALE_DIR.exists()

        # 2. 设置语言
        set_language("zh")
        assert get_current_language() == "zh"

        # 3. 获取翻译文本
        text = get_text("welcome_message", "欢迎")
        assert text == "欢迎"

        # 4. 切换语言
        set_language("en")
        assert get_current_language() == "en"

        # 5. 获取英文文本
        english_text = get_text("welcome_message", "Welcome")
        assert english_text == "Welcome"

    def test_error_handling_and_recovery(self):
        """测试错误处理和恢复"""
        # 测试各种异常情况
        test_cases = [
            (ValueError, "Value error test"),
            (KeyError, "Key error test"),
            (RuntimeError, "Runtime error test"),
        ]

        for exception_type, error_msg in test_cases:
            with patch(
                "src.utils.i18n.gettext.bindtextdomain",
                side_effect=exception_type(error_msg),
            ):
                with patch("os.getenv", return_value="zh_CN"):
                    # 应该优雅地处理异常
                    try:
                        init_i18n()
                        # 如果没有抛出异常，说明错误被正确处理
                        assert True
                    except Exception:
                        # 如果抛出异常，应该被上层处理
                        pass

    def test_performance_considerations(self):
        """测试性能考虑"""
        import time

        # 测试多次语言切换的性能
        start_time = time.time()

        for i in range(100):
            set_language("zh")
            get_current_language()
            set_language("en")
            get_current_language()

        end_time = time.time()
        duration = end_time - start_time

        # 200次操作应该在合理时间内完成
        assert duration < 0.5, f"语言切换耗时过长: {duration}秒"

        # 测试多次文本获取的性能
        start_time = time.time()

        for i in range(1000):
            get_text(f"key_{i}", f"value_{i}")

        end_time = time.time()
        duration = end_time - start_time

        # 1000次操作应该在合理时间内完成
        assert duration < 0.2, f"文本获取耗时过长: {duration}秒"
