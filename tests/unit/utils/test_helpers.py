"""
Helper functions test
"""

from datetime import datetime

from src.utils.helpers import (
    format_timestamp,
    generate_hash,
    generate_uuid,
    safe_get,
    sanitize_string,
)


class TestHelpers:
    """Helper functions tests"""

    def test_generate_uuid(self):
        """测试UUID生成"""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()

        assert isinstance(uuid1, str)
        assert isinstance(uuid2, str)
        assert len(uuid1) == 36  # UUID4 length
        assert len(uuid2) == 36
        assert uuid1 != uuid2  # 应该是唯一的

    def test_generate_hash_sha256(self):
        """测试SHA256哈希生成"""
        data = "test data"
        hash_result = generate_hash(data, "sha256")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64  # SHA256 hex length
        assert hash_result != generate_hash("different data")

    def test_generate_hash_md5(self):
        """测试MD5哈希生成"""
        data = "test data"
        hash_result = generate_hash(data, "md5")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 32  # MD5 hex length
        assert hash_result != generate_hash("different data")

    def test_generate_hash_sha1(self):
        """测试SHA1哈希生成"""
        data = "test data"
        hash_result = generate_hash(data, "sha1")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 40  # SHA1 hex length
        assert hash_result != generate_hash("different data")

    def test_safe_get_dict(self):
        """测试字典安全获取"""
        data = {"key1": "value1", "nested": {"key2": "value2"}}

        assert safe_get(data, "key1") == "value1"
        assert safe_get(data, "nonexistent") is None
        assert safe_get(data, "nonexistent", "default") == "default"

    def test_safe_get_nested_dict(self):
        """测试嵌套字典安全获取"""
        data = {"nested": {"deep": {"value": "found"}}}

        assert safe_get(data, "nested.deep.value") == "found"
        assert safe_get(data, "nested.nonexistent") is None
        assert safe_get(data, "nonexistent.deep.value") is None

    def test_safe_get_none_data(self):
        """测试空数据安全获取"""
        assert safe_get(None, "key") is None
        assert safe_get(None, "key", "default") == "default"

    def test_format_timestamp_default(self):
        """测试默认时间戳格式化"""
        result = format_timestamp()
        assert isinstance(result, str)
        assert "T" in result  # ISO format contains 'T'

    def test_format_timestamp_custom(self):
        """测试自定义时间戳格式化"""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = format_timestamp(dt)

        assert isinstance(result, str)
        assert result == "2023-01-01T12:00:00"

    def test_sanitize_string_normal(self):
        """测试正常字符串清理"""
        normal = "This is a normal string"
        result = sanitize_string(normal)
        assert result == normal

    def test_sanitize_string_dangerous(self):
        """测试危险字符串清理"""
        dangerous = "This has <script>alert('xss')</script> content"
        result = sanitize_string(dangerous)

        assert "<script>" not in result
        assert "</script>" not in result
        assert "This has alert('xss') content" in result

    def test_sanitize_string_empty(self):
        """测试空字符串清理"""
        assert sanitize_string("") == ""
        assert sanitize_string(None) == ""

    def test_sanitize_string_xss_patterns(self):
        """测试XSS模式清理"""
        test_cases = [
            ("text javascript:alert(1)", "text alert(1)"),
            ("onload=doSomething()", ""),
            ("onerror=handleError()", ""),
            ("</script>", ""),
        ]

        for input_str, expected_part in test_cases:
            result = sanitize_string(input_str)
            assert expected_part in result or expected_part == ""
