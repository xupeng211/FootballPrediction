"""
StringUtils增强测试 - 深化50.3%到65%+覆盖率
针对未覆盖的字符串工具函数进行全面测试
"""

from src.utils.string_utils import (
    StringUtils,
    batch_clean_strings,
    cached_slug,
    validate_batch_emails,
)


class TestStringUtilsEnhanced:
    """StringUtils增强测试类 - 提升覆盖率到65%+"""

    def test_slugify_function(self):
        """测试slugify功能"""
        # 基本slugify
        result = StringUtils.slugify("Hello World!")
        assert result == "hello-world"

        # Unicode处理
        unicode_result = StringUtils.slugify("你好世界")
        assert isinstance(unicode_result, str)
        assert len(unicode_result) > 0

        # 特殊字符处理
        special_result = StringUtils.slugify("Hello @#$%^&*() World")
        assert "hello" in special_result
        assert "world" in special_result

        # 无效输入
        assert StringUtils.slugify(None) == ""
        assert StringUtils.slugify(123) == ""

    def test_camel_to_snake_conversion(self):
        """测试驼峰命名转下划线命名"""
        # 基本转换
        assert StringUtils.camel_to_snake("HelloWorld") == "hello_world"
        assert StringUtils.camel_to_snake("CamelCase") == "camel_case"
        assert StringUtils.camel_to_snake("XMLHttpRequest") == "xml_http_request"

        # 无效输入
        assert StringUtils.camel_to_snake(None) == ""
        assert StringUtils.camel_to_snake(123) == ""

        # 边界情况
        assert StringUtils.camel_to_snake("") == ""
        assert StringUtils.camel_to_snake("ABC") == "a_b_c"

    def test_snake_to_camel_conversion(self):
        """测试下划线命名转驼峰命名"""
        # 基本转换
        assert StringUtils.snake_to_camel("hello_world") == "helloWorld"
        assert StringUtils.snake_to_camel("snake_case") == "snakeCase"
        assert StringUtils.snake_to_camel("multiple_words_here") == "multipleWordsHere"

        # 无效输入
        assert StringUtils.snake_to_camel(None) == ""
        assert StringUtils.snake_to_camel(123) == ""

        # 边界情况
        assert StringUtils.snake_to_camel("") == ""
        assert StringUtils.snake_to_camel("single") == "single"
        assert StringUtils.snake_to_camel("_leading") == "_leading"

    def test_clean_text_function(self):
        """测试文本清理功能"""
        # 基本清理
        assert StringUtils.clean_text("  Hello   World  ") == "Hello World"
        assert StringUtils.clean_text("Multiple    spaces") == "Multiple spaces"
        assert StringUtils.clean_text("Line\n\n\nBreaks") == "Line Breaks"

        # 制表符和混合空白
        assert StringUtils.clean_text("Tab\t\tSeparated") == "Tab Separated"
        assert (
            StringUtils.clean_text("Mixed \t whitespace \n here")
            == "Mixed whitespace here"
        )

        # 无效输入
        assert StringUtils.clean_text(None) == ""
        assert StringUtils.clean_text(123) == ""

    def test_validate_phone_number_function(self):
        """测试手机号验证功能"""
        # 有效手机号
        valid_phones = ["13800138000", "15912345678", "18888888888"]
        for phone in valid_phones:
            assert StringUtils.validate_phone_number(phone) is True

        # 包含分隔符的手机号
        formatted_phones = ["138-0013-8000", "138 0013 8000", "(138)00138000"]
        for phone in formatted_phones:
            assert StringUtils.validate_phone_number(phone) is True

        # 无效手机号
        invalid_phones = ["1234567890", "12800138000", "1380013800", "138001380000"]
        for phone in invalid_phones:
            assert StringUtils.validate_phone_number(phone) is False

        # 无效输入
        assert StringUtils.validate_phone_number(None) is False
        assert StringUtils.validate_phone_number(123) is False

    def test_sanitize_phone_number_function(self):
        """测试电话号码清理功能"""
        # 基本清理
        assert StringUtils.sanitize_phone_number("13800138000") == "13800138000"
        assert StringUtils.sanitize_phone_number("138-0013-8000") == "13800138000"
        assert StringUtils.sanitize_phone_number("138 0013 8000") == "13800138000"

        # 无效号码
        assert StringUtils.sanitize_phone_number("1234567890") == ""
        assert StringUtils.sanitize_phone_number("12800138000") == ""

        # 无效输入
        assert StringUtils.sanitize_phone_number(None) == ""
        assert StringUtils.sanitize_phone_number(123) == ""

    def test_extract_numbers_function(self):
        """测试数字提取功能"""
        # 基本提取
        assert StringUtils.extract_numbers("abc123def456") == [123.0, 456.0]
        assert StringUtils.extract_numbers("Price: $19.99") == [19.99]
        assert StringUtils.extract_numbers("-42 is negative") == [-42.0]

        # 小数处理
        assert StringUtils.extract_numbers("3.14 and 2.71") == [3.14, 2.71]

        # 无数字
        assert StringUtils.extract_numbers("no numbers here") == []

        # 无效输入
        assert StringUtils.extract_numbers(None) == []
        assert StringUtils.extract_numbers(123) == []

    def test_mask_sensitive_data_function(self):
        """测试敏感数据遮蔽功能"""
        # 基本遮蔽
        assert StringUtils.mask_sensitive_data("1234567890123456") == "1234************"
        assert StringUtils.mask_sensitive_data("hello@world.com") == "hell************"

        # 自定义参数
        assert (
            StringUtils.mask_sensitive_data("1234567890", visible_chars=2)
            == "12********"
        )
        assert StringUtils.mask_sensitive_data("password", mask_char="#") == "pass####"

        # 短字符串不遮蔽
        assert StringUtils.mask_sensitive_data("123") == "123"
        assert StringUtils.mask_sensitive_data("") == ""

        # 无效输入
        assert StringUtils.mask_sensitive_data(None, 4, "*") is None
        assert StringUtils.mask_sensitive_data(123, 4, "*") == 123

    def test_generate_slug_function(self):
        """测试slug生成功能"""
        # 基本功能
        assert StringUtils.generate_slug("Hello World!") == "hello-world"
        assert callable(StringUtils.generate_slug)

        # 验证它与slugify功能相同
        text = "Test String Here"
        assert StringUtils.generate_slug(text) == StringUtils.slugify(text)

    def test_format_bytes_function(self):
        """测试字节格式化功能"""
        # 各种单位
        assert StringUtils.format_bytes(0) == "0 B"
        assert StringUtils.format_bytes(1024) == "1.00 KB"
        assert StringUtils.format_bytes(1024 * 1024) == "1.00 MB"
        assert StringUtils.format_bytes(1024 * 1024 * 1024) == "1.00 GB"

        # 精度控制
        assert StringUtils.format_bytes(1536, precision=1) == "1.5 KB"

        # 小数值
        assert StringUtils.format_bytes(512) == "512.00 B"

    def test_count_words_function(self):
        """测试单词计数功能"""
        # 基本计数
        assert StringUtils.count_words("Hello world") == 2
        assert StringUtils.count_words("One two three four") == 4

        # 空白处理
        assert StringUtils.count_words("  Hello   world  ") == 2
        assert StringUtils.count_words("") == 0

        # 无效输入
        assert StringUtils.count_words(None) == 0
        assert StringUtils.count_words(123) == 0

    def test_escape_html_function(self):
        """测试HTML转义功能"""
        # 基本转义
        assert (
            StringUtils.escape_html("<div>Hello & 'world'</div>")
            == "&lt;div&gt;Hello &amp; &#39;world&#39;&lt;/div&gt;"
        )
        assert StringUtils.escape_html('Quote: "test"') == "Quote: &quot;test&quot;"
        assert StringUtils.escape_html("Ampersand: &") == "Ampersand: &amp;"

        # 无输入
        assert StringUtils.escape_html("") == ""
        assert StringUtils.escape_html(None) == ""
        assert StringUtils.escape_html(123) == ""

    def test_unescape_html_function(self):
        """测试HTML反转义功能"""
        # 基本反转义
        assert (
            StringUtils.unescape_html("&lt;div&gt;Hello&lt;/div&gt;")
            == "<div>Hello</div>"
        )
        assert StringUtils.unescape_html("&quot;test&quot;") == '"test"'
        assert StringUtils.unescape_html("&amp;") == "&"

        # 组合转义
        assert (
            StringUtils.unescape_html(
                "&lt;div&gt;Hello &amp; &#39;world&#39;&lt;/div&gt;"
            )
            == "<div>Hello & 'world'</div>"
        )

        # 无输入
        assert StringUtils.unescape_html("") == ""
        assert StringUtils.unescape_html(None) == ""
        assert StringUtils.unescape_html(123) == ""

    def test_is_url_function(self):
        """测试URL检查功能"""
        # 有效URL
        valid_urls = [
            "http://example.com",
            "https://www.example.com",
            "https://example.com/path/to/resource",
            "http://example.com:8080",
            "https://sub.domain.example.com",
        ]

        for url in valid_urls:
            assert StringUtils.is_url(url) is True

        # 无效URL
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "http//example.com",
            "example.com",
            "http://",
            "",
        ]

        for url in invalid_urls:
            assert StringUtils.is_url(url) is False

        # 无效输入
        assert StringUtils.is_url(None) is False
        assert StringUtils.is_url(123) is False

    def test_reverse_string_function(self):
        """测试字符串反转功能"""
        # 基本反转
        assert StringUtils.reverse_string("hello") == "olleh"
        assert StringUtils.reverse_string("12345") == "54321"
        assert StringUtils.reverse_string("racecar") == "racecar"  # 回文

        # Unicode
        assert StringUtils.reverse_string("你好") == "好你"

        # 无效输入
        assert StringUtils.reverse_string(None) == ""
        assert StringUtils.reverse_string(123) == ""

    def test_is_palindrome_function(self):
        """测试回文检查功能"""
        # 基本回文
        assert StringUtils.is_palindrome("racecar") is True
        assert StringUtils.is_palindrome("level") is True
        assert StringUtils.is_palindrome("A man a plan a canal Panama") is True

        # 非回文
        assert StringUtils.is_palindrome("hello") is False
        assert StringUtils.is_palindrome("world") is False

        # 数值和符号忽略
        assert StringUtils.is_palindrome("A man, a plan, a canal: Panama") is True

        # 无效输入
        assert StringUtils.is_palindrome(None) is False
        assert StringUtils.is_palindrome(123) is False

    def test_capitalize_words_function(self):
        """测试单词首字母大写功能"""
        # 基本大写
        assert StringUtils.capitalize_words("hello world") == "Hello World"
        assert (
            StringUtils.capitalize_words("python programming") == "Python Programming"
        )

        # 多重空格处理
        assert (
            StringUtils.capitalize_words("  multiple   spaces  ") == "Multiple Spaces"
        )

        # 无效输入
        assert StringUtils.capitalize_words(None) == ""
        assert StringUtils.capitalize_words(123) == ""

    def test_random_string_function(self):
        """测试随机字符串生成功能"""
        # 基本生成
        result = StringUtils.random_string(10)
        assert isinstance(result, str)
        assert len(result) == 10

        # 不同长度
        for length in [1, 5, 20]:
            result = StringUtils.random_string(length)
            assert len(result) == length

        # 零长度
        assert StringUtils.random_string(0) == ""
        assert StringUtils.random_string(-5) == ""

        # 自定义字符集
        custom_chars = "ABC123"
        result = StringUtils.random_string(5, custom_chars)
        assert len(result) == 5
        assert all(c in custom_chars for c in result)

    def test_remove_duplicates_function(self):
        """测试重复字符移除功能"""
        # 基本去重
        assert StringUtils.remove_duplicates("hello") == "helo"
        assert StringUtils.remove_duplicates("112233") == "123"

        # 保持顺序
        assert StringUtils.remove_duplicates("abcaab") == "abc"

        # 无输入
        assert StringUtils.remove_duplicates("") == ""
        assert StringUtils.remove_duplicates(None) == ""

    def test_word_count_function(self):
        """测试单词计数功能（别名）"""
        # 基本计数
        assert StringUtils.word_count("hello world") == 2
        assert StringUtils.word_count("one two three") == 3

        # 与count_words结果一致
        text = "test word count here"
        assert StringUtils.word_count(text) == StringUtils.count_words(text)

        # 无效输入
        assert StringUtils.word_count(None) == 0
        assert StringUtils.word_count(123) == 0

    def test_char_frequency_function(self):
        """测试字符频率计算功能"""
        # 基本频率
        freq = StringUtils.char_frequency("hello")
        assert freq == {"h": 1, "e": 1, "l": 2, "o": 1}

        # 大小写敏感
        freq = StringUtils.char_frequency("Hello")
        assert freq == {"H": 1, "e": 1, "l": 2, "o": 1}

        # 无输入
        assert StringUtils.char_frequency("") == {}
        assert StringUtils.char_frequency(None) == {}

    def test_cached_slug_function(self):
        """测试缓存的slug生成函数"""
        # 基本功能
        result = cached_slug("Hello World")
        assert isinstance(result, str)
        assert "hello" in result and "world" in result

        # 多次调用应该返回相同结果（缓存测试）
        result1 = cached_slug("Test String")
        result2 = cached_slug("Test String")
        assert result1 == result2

        # 无效输入
        assert cached_slug(None) == ""
        assert cached_slug(123) == ""

    def test_batch_clean_strings_function(self):
        """测试批量字符串清理功能"""
        # 基本批量清理
        strings = ["  hello  ", "  world  ", "\ttest\t"]
        result = batch_clean_strings(strings)
        expected = ["hello", "world", "test"]
        assert result == expected

        # 空列表
        assert batch_clean_strings([]) == []

        # 混合输入
        strings = ["clean", "", "  spaces  "]
        result = batch_clean_strings(strings)
        assert result == ["clean", "", "spaces"]

    def test_validate_batch_emails_function(self):
        """测试批量邮箱验证功能"""
        # 基本批量验证
        emails = ["test@example.com", "invalid-email", "user@domain.org"]
        result = validate_batch_emails(emails)

        assert isinstance(result, dict)
        # 检查新的格式：邮箱级别结果
        assert "test@example.com" in result
        assert "invalid-email" in result
        assert "user@domain.org" in result
        assert result["test@example.com"] is True
        assert result["user@domain.org"] is True
        assert result["invalid-email"] is False

        # 检查内部列表格式
        assert "_valid_list" in result
        assert "_invalid_list" in result
        assert len(result["_valid_list"]) == 2
        assert len(result["_invalid_list"]) == 1
        assert "test@example.com" in result["_valid_list"]
        assert "user@domain.org" in result["_valid_list"]
        assert "invalid-email" in result["_invalid_list"]

        # 空列表
        empty_result = validate_batch_emails([])
        assert empty_result == {"_valid_list": [], "_invalid_list": []}

    def test_string_utils_comprehensive_workflow(self):
        """测试字符串工具的完整工作流程"""
        # 1. 文本清理和处理
        original_text = "  Hello @#$%^&*() World! 123  "
        cleaned = StringUtils.clean_string(original_text, remove_special_chars=True)
        assert "Hello" in cleaned
        assert "World" in cleaned

        # 2. 文本截断
        long_text = "This is a very long text that needs to be truncated"
        truncated = StringUtils.truncate(long_text, 20)
        assert len(truncated) <= 23  # 20 + "..."

        # 3. 格式转换
        camel_case = "helloWorldTest"
        snake_case = StringUtils.camel_to_snake(camel_case)
        back_to_camel = StringUtils.snake_to_camel(snake_case)
        assert back_to_camel == camel_case

        # 4. URL处理
        slug = StringUtils.slugify("Hello World Test")
        assert "hello" in slug and "world" in slug and "test" in slug

        # 5. 数据遮蔽
        sensitive = "1234567890123456"
        masked = StringUtils.mask_sensitive_data(sensitive)
        assert masked != sensitive
        assert masked.startswith("1234")

        # 6. 批量处理
        texts = ["  Text1  ", "  Text2  ", "Text3"]
        cleaned_batch = batch_clean_strings(texts)
        assert all(" " not in text for text in cleaned_batch)

    def test_edge_cases_and_error_handling(self):
        """测试边界情况和错误处理"""
        # 测试极长字符串
        very_long = "a" * 10000
        result = StringUtils.clean_string(very_long)
        assert len(result) <= 10000

        # 测试Unicode复杂情况
        complex_unicode = "café naïve résumé 🌍✨"
        cleaned = StringUtils.clean_string(complex_unicode)
        assert isinstance(cleaned, str)

        # 测试各种无效输入
        invalid_inputs = [None, 123, [], {}, object()]
        for invalid_input in invalid_inputs:
            assert StringUtils.clean_string(invalid_input) == ""
            assert StringUtils.truncate(invalid_input) == ""
            assert StringUtils.slugify(invalid_input) == ""

    def test_performance_considerations(self):
        """测试性能考虑"""
        import time

        # 测试大量操作性能
        strings = [f"Hello World {i} {j}" for i in range(50) for j in range(2)]

        start_time = time.time()

        # 批量处理
        cleaned = batch_clean_strings(strings)

        end_time = time.time()
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成
        assert len(cleaned) == len(strings)
