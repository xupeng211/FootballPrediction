"""
辅助函数测试
Helper Functions Tests

测试实际存在的辅助函数。
"""

from datetime import datetime

import pytest

from src.utils.helpers import (
    format_timestamp,
    generate_hash,
    generate_uuid,
    safe_get,
    sanitize_string,
)


@pytest.mark.unit
class TestHelpers:
    """测试辅助函数"""

    def test_generate_uuid(self):
        """测试生成UUID"""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()

        # 检查类型和长度
        assert isinstance(uuid1, str)
        assert isinstance(uuid2, str)
        assert len(uuid1) == 36  # 标准UUID4长度
        assert len(uuid2) == 36

        # 检查唯一性
        assert uuid1 != uuid2

        # 检查格式（UUID v4）
        import re

        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert uuid_pattern.match(uuid1) is not None
        assert uuid_pattern.match(uuid2) is not None

        # 生成多个UUID确保唯一性
        uuids = {generate_uuid() for _ in range(100)}
        assert len(uuids) == 100  # 所有UUID都应该是唯一的

    def test_generate_hash(self):
        """测试生成哈希"""
        # 测试基本哈希
        hash1 = generate_hash("hello")
        hash2 = generate_hash("world")
        hash3 = generate_hash("hello")

        # 检查类型和长度
        assert isinstance(hash1, str)
        assert isinstance(hash2, str)
        assert len(hash1) == 64  # SHA256 输出长度
        assert len(hash2) == 64

        # 相同输入应该产生相同哈希
        assert hash1 == hash3

        # 不同输入应该产生不同哈希
        assert hash1 != hash2

        # 测试空字符串
        empty_hash = generate_hash("")
        assert len(empty_hash) == 64
        assert empty_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        # 测试已知哈希值
        known_hash = generate_hash("test")
        assert known_hash == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

        # 测试长字符串
        long_text = "a" * 1000
        long_hash = generate_hash(long_text)
        assert len(long_hash) == 64

        # 测试特殊字符
        special_hash = generate_hash("你好世界!@#$%^&*()")
        assert len(special_hash) == 64

    def test_safe_get(self):
        """测试安全获取字典值"""
        _data = {
            "name": "John",
            "age": 30,
            "profile": {
                "email": "john@example.com",
            },
            "active": True,
            "score": None,
        }

        # 获取存在的键
        assert safe_get(_data, "name") == "John"
        assert safe_get(_data, "age") == 30
        assert safe_get(_data, "active") is True
        assert safe_get(_data, "score") is None

        # 获取不存在的键
        assert safe_get(_data, "nonexistent") is None
        assert safe_get(_data, "email") is None  # 不在顶层

        # 使用默认值
        assert safe_get(_data, "nonexistent", "default") == "default"
        assert safe_get(_data, "score", "no_score") is None  # 即使值为None

        # 测试空字典
        empty_data = {}
        assert safe_get(empty_data, "key") is None
        assert safe_get(empty_data, "key", "default") == "default"

        # 测试None字典
        assert safe_get(None, "key", "default") == "default"

        # 测试嵌套字典（此函数支持点号分隔的嵌套键）
        assert safe_get(_data, "profile.email") == "john@example.com"  # 支持嵌套访问

    def test_format_timestamp(self):
        """测试格式化时间戳"""
        # 测试默认行为（使用当前时间）
        timestamp1 = format_timestamp()
        assert isinstance(timestamp1, str)
        assert "T" in timestamp1  # ISO格式包含T

        # 解析时间戳
        parsed = datetime.fromisoformat(
            timestamp1.replace("Z", "+00:00") if timestamp1.endswith("Z") else timestamp1
        )
        assert isinstance(parsed, datetime)

        # 测试提供特定时间
        test_time = datetime(2025, 1, 11, 15, 30, 45)
        timestamp2 = format_timestamp(test_time)
        assert timestamp2 == "2025-01-11T15:30:45"

        # 测试带微秒的时间
        test_time = datetime(2025, 1, 11, 15, 30, 45, 123456)
        timestamp3 = format_timestamp(test_time)
        assert "2025-01-11T15:30:45" in timestamp3
        assert "123456" in timestamp3

        # 测试UTC时间
        utc_time = datetime.utcnow()
        utc_timestamp = format_timestamp(utc_time)
        assert isinstance(utc_timestamp, str)

    def test_sanitize_string(self):
        """测试清理字符串"""
        # 测试基本清理（sanitize_string只做XSS防护，不做大小写转换）
        assert sanitize_string("  Hello World  ") == "Hello World"
        assert sanitize_string("   TEST   ") == "TEST"

        # 测试大小写转换（sanitize_string不改变大小写）
        assert sanitize_string("HeLLo WoRLD") == "HeLLo WoRLD"

        # 测试空字符串
        assert sanitize_string("") == ""
        assert sanitize_string("   ") == ""

        # 测试None输入
        assert sanitize_string(None) == ""

        # 测试只有空白字符
        assert sanitize_string("\t\n  \r") == ""

        # 测试特殊字符
        assert sanitize_string("  Hello@World!  ") == "Hello@World!"
        assert sanitize_string("  Test_123  ") == "Test_123"

        # 测试Unicode字符
        assert sanitize_string("  你好世界  ") == "你好世界"

        # 测试混合空白
        assert sanitize_string("\tHello\nWorld\r\n") == "Hello\nWorld"

        # 测试保留内部空白
        assert sanitize_string("  Hello   World  ") == "Hello   World"

    def test_edge_cases(self):
        """测试边界情况"""
        # UUID边界情况
        for _ in range(10):
            uuid = generate_uuid()
            assert 32 <= len(uuid.replace("-", "")) <= 32  # 去掉连字符后32个字符

        # 哈希边界情况
        # 非常长的输入
        very_long = "x" * 100000
        hash1 = generate_hash(very_long)
        hash2 = generate_hash(very_long)
        assert hash1 == hash2
        assert len(hash1) == 64

        # 字节输入（如果支持）
        try:
            generate_hash(b"bytes")
        except (AttributeError, TypeError):
            pass  # 预期可能失败

        # safe_get边界情况
        class DictLike:
            def get(self, key, default=None):
                return default

        dict_like = DictLike()
        assert safe_get(dict_like, "key") is None

    def test_performance_considerations(self):
        """测试性能相关"""
        import time

        # UUID生成性能
        start = time.time()
        for _ in range(1000):
            generate_uuid()
        duration = time.time() - start
        assert duration < 1.0  # 1000个UUID应该在1秒内生成完

        # 哈希生成性能
        start = time.time()
        for i in range(1000):
            generate_hash(f"test_string_{i}")
        duration = time.time() - start
        assert duration < 0.5  # 1000个哈希应该在0.5秒内生成完

    def test_integration(self):
        """测试组合使用"""
        # 创建用户数据
        user_data = {
            "name": "John Doe",
            "email": "john@example.com",
        }

        # 清理名称
        clean_name = sanitize_string("  " + user_data["name"] + "  ")
        assert clean_name == "John Doe"

        # 生成用户ID和哈希
        user_id = generate_uuid()
        user_hash = generate_hash(user_data["email"])

        # 创建时间戳
        created_at = format_timestamp()

        # 构建用户记录
        user_record = {
            "id": user_id,
            "name": clean_name,
            "email": safe_get(user_data, "email"),
            "email_hash": user_hash,
            "created_at": created_at,
        }

        # 验证记录
        assert user_record["id"] == user_id
        assert user_record["name"] == "John Doe"
        assert user_record["email"] == "john@example.com"
        assert user_record["email_hash"] == generate_hash("john@example.com")
        assert "T" in user_record["created_at"]
