"""
Src模块扩展测试 - Phase 2: 字符串工具模块测试
目标: 提升src模块覆盖率，向65%历史水平迈进

测试范围:
- StringUtils类的核心方法
- 字符串清理、验证、格式化功能
- 性能优化和边界条件测试
"""

import pytest
import sys
import os

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.utils.string_utils import StringUtils, cached_slug, batch_clean_strings, validate_batch_emails


class TestStringUtilsCore:
    """StringUtils核心功能测试"""

    def test_clean_string_basic(self):
        """测试基本字符串清理"""
        # 正常情况
        assert StringUtils.clean_string("  hello world  ") == "hello world"
        assert StringUtils.clean_string("hello\nworld\ttest") == "hello world test"

        # 空值处理
        assert StringUtils.clean_string("") == ""
        assert StringUtils.clean_string(None) == ""
        assert StringUtils.clean_string(123) == ""

    def test_clean_string_special_chars(self):
        """测试特殊字符清理"""
        text = "hello@#$%^&*()world"
        result = StringUtils.clean_string(text, remove_special_chars=True)
        assert "@" not in result
        assert "#" not in result
        assert "hello" in result
        assert "world" in result

    def test_truncate_basic(self):
        """测试字符串截断"""
        # 正常截断
        assert StringUtils.truncate("hello world", 5) == "he..."
        assert StringUtils.truncate("hello", 10) == "hello"

        # 边界情况
        assert StringUtils.truncate("hello", 5) == "hello"
        assert StringUtils.truncate("hello world", 0) == "..."
        assert StringUtils.truncate("hello world", -2) == "..."

    def test_validate_email(self):
        """测试邮箱验证"""
        # 有效邮箱
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "test123@test-domain.com"
        ]

        for email in valid_emails:
            assert StringUtils.validate_email(email), f"应该验证通过: {email}"

        # 无效邮箱
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test.example.com",
            "",
            None,
            123
        ]

        for email in invalid_emails:
            assert not StringUtils.validate_email(email), f"应该验证失败: {email}"

    def test_slugify(self):
        """测试URL友好字符串生成"""
        # 基本转换
        assert StringUtils.slugify("Hello World") == "hello-world"
        assert StringUtils.slugify("Python & FastAPI") == "python-fastapi"

        # 特殊字符处理
        assert StringUtils.slugify("Café au lait") == "caf-au-lait"
        assert StringUtils.slugify("  multiple   spaces  ") == "multiple-spaces"

        # 空值处理
        assert StringUtils.slugify("") == ""
        assert StringUtils.slugify(None) == ""

    def test_naming_convention_conversion(self):
        """测试命名风格转换"""
        # 驼峰转下划线
        assert StringUtils.camel_to_snake("HelloWorld") == "hello_world"
        assert StringUtils.camel_to_snake("testHTTPRequest") == "test_http_request"

        # 下划线转驼峰
        assert StringUtils.snake_to_camel("hello_world") == "helloWorld"
        assert StringUtils.snake_to_camel("test_http_request") == "testHTTPRequest"

        # 空值处理
        assert StringUtils.camel_to_snake("") == ""
        assert StringUtils.snake_to_camel(None) == ""

    def test_validate_phone_number(self):
        """测试手机号验证"""
        # 有效手机号
        valid_phones = [
            "13812345678",
            "15987654321",
            "18612345678"
        ]

        for phone in valid_phones:
            assert StringUtils.validate_phone_number(phone), f"应该验证通过: {phone}"

        # 无效手机号
        invalid_phones = [
            "12812345678",  # 不是1开头的合法号段
            "1381234567",   # 位数不够
            "138123456789", # 位数过多
            "",
            None,
            "abc12345678"
        ]

        for phone in invalid_phones:
            assert not StringUtils.validate_phone_number(phone), f"应该验证失败: {phone}"

    def test_extract_numbers(self):
        """测试数字提取"""
        text = "价格: ¥123.45, 数量: 10个, 总计: ¥1234.5"
        numbers = StringUtils.extract_numbers(text)
        assert 123.45 in numbers
        assert 10 in numbers
        assert 1234.5 in numbers

        # 负数测试
        text = "温度: -5.5度, 湿度: 60%"
        numbers = StringUtils.extract_numbers(text)
        assert -5.5 in numbers
        assert 60 in numbers

        # 空值处理
        assert StringUtils.extract_numbers("") == []
        assert StringUtils.extract_numbers(None) == []

    def test_mask_sensitive_data(self):
        """测试敏感数据遮蔽"""
        # 正常遮蔽
        assert StringUtils.mask_sensitive_data("13812345678") == "1381****"
        assert StringUtils.mask_sensitive_data("password123", 4) == "pass****"

        # 短字符串处理
        assert StringUtils.mask_sensitive_data("123") == "123"

        # 空值处理
        assert StringUtils.mask_sensitive_data("") == ""
        assert StringUtils.mask_sensitive_data(None) == None

    def test_is_url(self):
        """测试URL验证"""
        # 有效URL
        valid_urls = [
            "https://www.example.com",
            "http://example.com/path",
            "https://sub.domain.co.uk:8080/path?query=value"
        ]

        for url in valid_urls:
            assert StringUtils.is_url(url), f"应该是有效URL: {url}"

        # 无效URL
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "",
            None
        ]

        for url in invalid_urls:
            assert not StringUtils.is_url(url), f"应该是无效URL: {url}"

    def test_is_palindrome(self):
        """测试回文检查"""
        # 回文字符串
        palindromes = [
            "racecar",
            "A man a plan a canal Panama",
            "No lemon, no melon"
        ]

        for text in palindromes:
            assert StringUtils.is_palindrome(text), f"应该是回文: {text}"

        # 非回文
        non_palindromes = ["hello", "world", "test"]
        for text in non_palindromes:
            assert not StringUtils.is_palindrome(text), f"应该不是回文: {text}"

    def test_html_escape_unescape(self):
        """测试HTML转义和反转义"""
        # 转义测试
        html = "<script>alert('Hello & Welcome')</script>"
        escaped = StringUtils.escape_html(html)
        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "&amp;" in escaped
        assert "&#39;" in escaped

        # 反转义测试
        unescaped = StringUtils.unescape_html(escaped)
        assert unescaped == html

    def test_format_bytes(self):
        """测试字节格式化"""
        # 各种单位转换
        assert StringUtils.format_bytes(0) == "0 B"
        assert StringUtils.format_bytes(1024) == "1.00 KB"
        assert StringUtils.format_bytes(1024 * 1024) == "1.00 MB"
        assert StringUtils.format_bytes(1024 * 1024 * 1024) == "1.00 GB"

        # 精度测试
        result = StringUtils.format_bytes(1536, 1)
        assert "1.5" in result and "KB" in result


class TestStringUtilsPerformance:
    """StringUtils性能测试"""

    def test_random_string_generation(self):
        """测试随机字符串生成"""
        # 默认参数
        s1 = StringUtils.random_string(10)
        assert len(s1) == 10
        assert s1.isalnum()

        # 自定义字符集
        custom_chars = "ABCDEF0123456789"
        s2 = StringUtils.random_string(8, custom_chars)
        assert len(s2) == 8
        assert all(c in custom_chars for c in s2)

        # 边界情况
        assert StringUtils.random_string(0) == ""
        assert StringUtils.random_string(-5) == ""

    def test_count_words(self):
        """测试单词计数"""
        assert StringUtils.count_words("hello world") == 2
        assert StringUtils.count_words("  multiple   spaces  ") == 2
        assert StringUtils.count_words("") == 0
        assert StringUtils.count_words(None) == 0
        assert StringUtils.count_words("word") == 1

    def test_char_frequency(self):
        """测试字符频率统计"""
        text = "hello world"
        freq = StringUtils.char_frequency(text)
        assert freq['l'] == 3
        assert freq['o'] == 2
        assert freq['h'] == 1
        assert freq[' '] == 1

        # 空值处理
        assert StringUtils.char_frequency("") == {}
        assert StringUtils.char_frequency(None) == {}


class TestStringUtilsCached:
    """缓存函数测试"""

    def test_cached_slug(self):
        """测试缓存的slug生成"""
        text = "Hello World Test"

        # 第一次调用
        result1 = cached_slug(text)
        # 第二次调用（应该使用缓存）
        result2 = cached_slug(text)

        assert result1 == result2 == "hello-world-test"

    def test_batch_clean_strings(self):
        """测试批量字符串清理"""
        strings = [
            "  hello  ",
            "\tworld\n",
            "  test  ",
            ""
        ]

        cleaned = batch_clean_strings(strings)
        assert cleaned == ["hello", "world", "test", ""]

        # 空列表处理
        assert batch_clean_strings([]) == []

    def test_validate_batch_emails(self):
        """测试批量邮箱验证"""
        emails = [
            "test@example.com",
            "invalid-email",
            "user@domain.org",
            "@invalid.com"
        ]

        result = validate_batch_emails(emails)
        assert result["test@example.com"] == True
        assert result["invalid-email"] == False
        assert result["user@domain.org"] == True
        assert result["@invalid.com"] == False


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])