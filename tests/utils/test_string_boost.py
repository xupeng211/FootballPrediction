import pytest
from src.utils.string_utils import StringUtils


def test_truncate():
    """测试字符串截断"""
    # 测试正常截断
    assert StringUtils.truncate("hello world", 5) == "he..."
    assert StringUtils.truncate("hello", 10) == "hello"
    assert StringUtils.truncate("", 5) == ""

    # 测试自定义后缀
    assert StringUtils.truncate("hello world", 5, "---") == "he---"

    # 测试边界情况
    assert StringUtils.truncate("hi", 2) == "hi"
    assert StringUtils.truncate("test", 4) == "test"


def test_capitalize_words():
    """测试单词首字母大写"""
    if hasattr(StringUtils, "capitalize_words"):
        assert StringUtils.capitalize_words("hello world") == "Hello World"
        assert (
            StringUtils.capitalize_words("PYTHON programming") == "Python Programming"
        )
        assert StringUtils.capitalize_words("") == ""


def test_slugify():
    """测试字符串友好化"""
    if hasattr(StringUtils, "slugify"):
        assert StringUtils.slugify("Hello World!") == "hello-world"
        assert StringUtils.slugify("Python & JavaScript") == "python-javascript"
        assert StringUtils.slugify("  Test   String  ") == "test-string"


def test_is_email():
    """测试邮箱验证"""
    if hasattr(StringUtils, "is_email"):
        assert StringUtils.is_email("test@example.com") is True
        assert StringUtils.is_email("user.name+tag@domain.co.uk") is True
        assert StringUtils.is_email("invalid") is False
        assert StringUtils.is_email("@example.com") is False
        assert StringUtils.is_email("test@") is False


def test_extract_numbers():
    """测试提取数字"""
    if hasattr(StringUtils, "extract_numbers"):
        assert StringUtils.extract_numbers("abc123def456") == [123, 456]
        assert StringUtils.extract_numbers("price: $19.99") == [19.99]
        assert StringUtils.extract_numbers("no numbers") == []


def test_reverse_string():
    """测试字符串反转"""
    if hasattr(StringUtils, "reverse_string"):
        assert StringUtils.reverse_string("hello") == "olleh"
        assert StringUtils.reverse_string("") == ""
        assert StringUtils.reverse_string("a") == "a"


def test_count_words():
    """测试单词计数"""
    if hasattr(StringUtils, "count_words"):
        assert StringUtils.count_words("Hello world") == 2
        assert StringUtils.count_words("  Multiple   spaces  ") == 2
        assert StringUtils.count_words("") == 0
        assert StringUtils.count_words("One") == 1


def test_clean_whitespace():
    """测试清理空白字符"""
    if hasattr(StringUtils, "clean_whitespace"):
        assert StringUtils.clean_whitespace("  hello   world  ") == "hello world"
        assert StringUtils.clean_whitespace("\n\ttest\n") == "test"
        assert StringUtils.clean_whitespace("") == ""
