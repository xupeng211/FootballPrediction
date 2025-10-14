"""加密工具基础测试"""

import pytest
import re
from src.utils.crypto_utils import CryptoUtils


class TestCryptoUtilsBasic:
    """加密工具基础测试"""

    def test_generate_uuid(self):
        """测试生成UUID"""
        result = CryptoUtils.generate_uuid()

        # 验证是有效的UUID格式
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, result, re.IGNORECASE)

        # 验证两次生成的UUID不同
        result2 = CryptoUtils.generate_uuid()
        assert result != result2

    def test_generate_short_id(self):
        """测试生成短ID"""
        # 默认长度
        result = CryptoUtils.generate_short_id()
        assert len(result) == 8
        assert result.isalnum()

        # 自定义长度
        result = CryptoUtils.generate_short_id(16)
        assert len(result) == 16
        assert result.isalnum()

        # 长度为0
        result = CryptoUtils.generate_short_id(0)
        assert result == ""

        # 负长度
        result = CryptoUtils.generate_short_id(-5)
        assert result == ""

        # 长度大于32
        result = CryptoUtils.generate_short_id(40)
        assert len(result) == 40
        assert result.isalnum()

        # 验证两次生成的ID不同
        result2 = CryptoUtils.generate_short_id(8)
        assert result != result2

    def test_hash_string_md5(self):
        """测试MD5哈希"""
        text = "Hello World"
        result = CryptoUtils.hash_string(text, "md5")

        # 验证MD5格式
        assert len(result) == 32
        assert all(c in "0123456789abcdef" for c in result)

        # 验证相同输入产生相同输出
        result2 = CryptoUtils.hash_string(text, "md5")
        assert result == result2

        # 验证不同输入产生不同输出
        result3 = CryptoUtils.hash_string("Different text", "md5")
        assert result != result3

    def test_hash_string_sha256(self):
        """测试SHA256哈希"""
        text = "Hello World"
        result = CryptoUtils.hash_string(text, "sha256")

        # 验证SHA256格式
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

        # 验证相同输入产生相同输出
        result2 = CryptoUtils.hash_string(text, "sha256")
        assert result == result2

    def test_hash_string_default(self):
        """测试默认哈希算法"""
        text = "Hello World"
        result = CryptoUtils.hash_string(text)

        # 默认应该是MD5
        expected = CryptoUtils.hash_string(text, "md5")
        assert result == expected

    def test_hash_string_unknown_algorithm(self):
        """测试未知哈希算法"""
        text = "Hello World"

        # 应该抛出ValueError
        with pytest.raises(ValueError, match="不支持的哈希算法"):
            CryptoUtils.hash_string(text, "unknown")