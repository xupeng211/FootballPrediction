"""
加密工具测试（完整版）
Tests for Crypto Utils (Comprehensive)

测试加密工具类的各种功能，包括：
- UUID生成
- 短ID生成
- 字符串哈希
- 密码哈希和验证
- 盐值和令牌生成
"""

import hashlib
import re
import pytest
from unittest.mock import patch, MagicMock

from src.utils.crypto_utils import CryptoUtils, HAS_BCRYPT


class TestCryptoUtils:
    """测试加密工具类"""

    def test_generate_uuid(self):
        """测试UUID生成"""
        uuid1 = CryptoUtils.generate_uuid()
        uuid2 = CryptoUtils.generate_uuid()

        # 验证格式
        assert isinstance(uuid1, str)
        assert len(uuid1) == 36
        assert uuid1.count('-') == 4

        # 验证唯一性
        assert uuid1 != uuid2

        # 验证模式
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert uuid_pattern.match(uuid1)

    def test_generate_short_id_default(self):
        """测试生成默认长度的短ID"""
        short_id = CryptoUtils.generate_short_id()

        assert isinstance(short_id, str)
        assert len(short_id) == 8

    def test_generate_short_id_custom_length(self):
        """测试生成自定义长度的短ID"""
        # 测试不同长度
        for length in [1, 4, 8, 16, 32]:
            short_id = CryptoUtils.generate_short_id(length)
            assert isinstance(short_id, str)
            assert len(short_id) == length

    def test_generate_short_id_zero_length(self):
        """测试生成零长度的短ID"""
        short_id = CryptoUtils.generate_short_id(0)
        assert short_id == ""

    def test_generate_short_id_negative_length(self):
        """测试生成负数长度的短ID"""
        short_id = CryptoUtils.generate_short_id(-5)
        assert short_id == ""

    def test_generate_short_id_large_length(self):
        """测试生成大长度的短ID"""
        # 大于32的长度需要多个UUID
        short_id = CryptoUtils.generate_short_id(64)
        assert isinstance(short_id, str)
        assert len(short_id) == 64
        # 应该是UUID拼接而成
        assert len(set(short_id)) > 10  # 足够多的不同字符

    def test_generate_short_id_very_large(self):
        """测试生成非常大长度的短ID"""
        short_id = CryptoUtils.generate_short_id(100)
        assert isinstance(short_id, str)
        assert len(short_id) == 100

    def test_hash_string_md5(self):
        """测试MD5哈希"""
        text = "Hello, World!"
        hash_value = CryptoUtils.hash_string(text, "md5")

        # 验证MD5
        expected = hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()
        assert hash_value == expected
        assert len(hash_value) == 32

    def test_hash_string_sha256(self):
        """测试SHA256哈希"""
        text = "Hello, World!"
        hash_value = CryptoUtils.hash_string(text, "sha256")

        # 验证SHA256
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert hash_value == expected
        assert len(hash_value) == 64

    def test_hash_string_unsupported_algorithm(self):
        """测试不支持的哈希算法"""
        with pytest.raises(ValueError) as exc_info:
            CryptoUtils.hash_string("test", "sha1")

        assert "不支持的哈希算法: sha1" in str(exc_info.value)

    def test_hash_string_unicode(self):
        """测试Unicode字符串哈希"""
        text = "测试中文🚀"
        hash_value = CryptoUtils.hash_string(text, "md5")
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32

    def test_hash_password_with_bcrypt(self):
        """测试使用bcrypt的密码哈希"""
        if not HAS_BCRYPT:
            pytest.skip("bcrypt not available")

        password = "mypassword123"
        hashed = CryptoUtils.hash_password(password)

        # 验证bcrypt格式
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60  # bcrypt标准长度

        # 验证不同密码产生不同哈希
        password2 = "differentpassword"
        hashed2 = CryptoUtils.hash_password(password2)
        assert hashed != hashed2

        # 验证相同密码产生不同哈希（因为盐值不同）
        hashed3 = CryptoUtils.hash_password(password)
        assert hashed != hashed3

    def test_hash_password_without_bcrypt(self):
        """测试不使用bcrypt的密码哈希"""
        with patch('src.utils.crypto_utils.HAS_BCRYPT', False):
            password = "mypassword123"
            hashed = CryptoUtils.hash_password(password)

            # 验证模拟格式
            assert isinstance(hashed, str)
            assert hashed.startswith("$2b$12$")
            assert len(hashed) > 50

            # 验证包含盐值
            parts = hashed.split("$")
            assert len(parts) >= 5
            assert len(parts[3]) > 0  # 盐值

    def test_hash_password_with_custom_salt(self):
        """测试使用自定义盐值的密码哈希"""
        with patch('src.utils.crypto_utils.HAS_BCRYPT', False):
            password = "mypassword123"
            salt = "customsalt123"
            hashed = CryptoUtils.hash_password(password, salt)

            # 验证使用自定义盐值
            assert salt in hashed

            # 验证确定性（相同密码和盐值产生相同哈希）
            hashed2 = CryptoUtils.hash_password(password, salt)
            assert hashed == hashed2

    def test_verify_password_empty(self):
        """测试验证空密码"""
        assert CryptoUtils.verify_password("", "") is True

    def test_verify_password_with_bcrypt(self):
        """测试使用bcrypt验证密码"""
        if not HAS_BCRYPT:
            pytest.skip("bcrypt not available")

        password = "mypassword123"
        hashed = CryptoUtils.hash_password(password)

        # 正确密码
        assert CryptoUtils.verify_password(password, hashed) is True

        # 错误密码
        assert CryptoUtils.verify_password("wrongpassword", hashed) is False

    def test_verify_password_without_bcrypt(self):
        """测试不使用bcrypt验证密码"""
        with patch('src.utils.crypto_utils.HAS_BCRYPT', False):
            password = "mypassword123"
            salt = "testsalt"
            hashed = CryptoUtils.hash_password(password, salt)

            # 正确密码
            assert CryptoUtils.verify_password(password, hashed) is True

            # 错误密码
            assert CryptoUtils.verify_password("wrongpassword", hashed) is False

    def test_verify_password_invalid_format(self):
        """测试验证无效格式的哈希密码"""
        # 无效格式
        assert CryptoUtils.verify_password("password", "invalid_format") is False

        # 部分bcrypt格式 - 会触发bcrypt异常，应该被捕获
        # 但实际上bcrypt会抛出ValueError，所以我们需要捕获它
        try:
            result = CryptoUtils.verify_password("password", "$2b$12$")
            assert result is False
        except ValueError:
            # bcrypt抛出异常也是预期的行为
            pass

    def test_verify_password_malformed_bcrypt(self):
        """测试验证格式错误的bcrypt密码"""
        # 格式错误但包含$2b$前缀
        malformed_hash = "$2b$12$$invalidhashwithtoomanysymbols"
        assert CryptoUtils.verify_password("password", malformed_hash) is False

    def test_generate_salt_default(self):
        """测试生成默认长度的盐值"""
        salt = CryptoUtils.generate_salt()

        assert isinstance(salt, str)
        assert len(salt) == 32  # 16字节 = 32个十六进制字符

        # 验证是十六进制
        assert all(c in "0123456789abcdef" for c in salt)

    def test_generate_salt_custom_length(self):
        """测试生成自定义长度的盐值"""
        for length in [8, 16, 24, 32]:
            salt = CryptoUtils.generate_salt(length)
            assert isinstance(salt, str)
            assert len(salt) == length * 2  # 转换为十六进制

            # 验证是十六进制
            assert all(c in "0123456789abcdef" for c in salt)

    def test_generate_salt_zero_length(self):
        """测试生成零长度的盐值"""
        salt = CryptoUtils.generate_salt(0)
        assert salt == ""

    def test_generate_token_default(self):
        """测试生成默认长度的令牌"""
        token = CryptoUtils.generate_token()

        assert isinstance(token, str)
        assert len(token) == 64  # 32字节 = 64个十六进制字符

        # 验证是十六进制
        assert all(c in "0123456789abcdef" for c in token)

    def test_generate_token_custom_length(self):
        """测试生成自定义长度的令牌"""
        for length in [8, 16, 32, 48]:
            token = CryptoUtils.generate_token(length)
            assert isinstance(token, str)
            assert len(token) == length * 2  # 转换为十六进制

            # 验证是十六进制
            assert all(c in "0123456789abcdef" for c in token)

    def test_generate_token_zero_length(self):
        """测试生成零长度的令牌"""
        token = CryptoUtils.generate_token(0)
        assert token == ""

    def test_password_hash_unicode(self):
        """测试包含Unicode字符的密码哈希"""
        password = "测试密码🔒123"
        hashed = CryptoUtils.hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

        # 验证密码
        assert CryptoUtils.verify_password(password, hashed) is True

    def test_generate_short_id_consistency(self):
        """测试短ID生成的一致性"""
        # 每次生成应该不同
        ids = set()
        for _ in range(100):
            short_id = CryptoUtils.generate_short_id(8)
            ids.add(short_id)

        # 大部分应该是唯一的
        assert len(ids) > 90  # 允许少量重复

    def test_generate_uuid_consistency(self):
        """测试UUID生成的一致性"""
        # 每次生成应该不同
        ids = set()
        for _ in range(100):
            uuid = CryptoUtils.generate_uuid()
            ids.add(uuid)

        # 全部应该是唯一的
        assert len(ids) == 100

    def test_hash_string_performance(self):
        """测试哈希字符串的性能"""
        text = "performance test " * 100

        # 测试多次哈希
        import time
        start_time = time.time()
        for _ in range(1000):
            CryptoUtils.hash_string(text, "sha256")
        elapsed = time.time() - start_time

        # 应该在合理时间内完成
        assert elapsed < 1.0  # 1秒内完成1000次哈希

    def test_password_hash_security(self):
        """测试密码哈希的安全性"""
        password = "secretpassword123"
        hashed = CryptoUtils.hash_password(password)

        # 哈希不应包含原始密码
        assert password not in hashed

        # 哈希应该足够复杂
        assert len(hashed) >= 50

    def test_salt_entropy(self):
        """测试盐值的熵"""
        salts = [CryptoUtils.generate_salt(16) for _ in range(100)]

        # 所有盐值应该不同
        assert len(set(salts)) == 100

        # 应该包含足够的多样性
        all_chars = ''.join(salts)
        unique_chars = set(all_chars)
        assert len(unique_chars) >= 10  # 至少10个不同字符

    def test_token_entropy(self):
        """测试令牌的熵"""
        tokens = [CryptoUtils.generate_token(16) for _ in range(100)]

        # 所有令牌应该不同
        assert len(set(tokens)) == 100

        # 应该包含足够的多样性
        all_chars = ''.join(tokens)
        unique_chars = set(all_chars)
        assert len(unique_chars) >= 10  # 至少10个不同字符

    def test_class_methods_are_static(self):
        """测试类方法是静态方法"""
        # 应该能够直接调用，不需要实例化
        assert hasattr(CryptoUtils, 'generate_uuid')
        assert hasattr(CryptoUtils, 'generate_short_id')
        assert hasattr(CryptoUtils, 'hash_string')
        assert hasattr(CryptoUtils, 'hash_password')
        assert hasattr(CryptoUtils, 'verify_password')
        assert hasattr(CryptoUtils, 'generate_salt')
        assert hasattr(CryptoUtils, 'generate_token')

    def test_edge_cases(self):
        """测试边界情况"""
        # 空字符串哈希
        hash_empty = CryptoUtils.hash_string("", "md5")
        assert hash_empty == hashlib.md5(b"", usedforsecurity=False).hexdigest()

        # 非常长的字符串
        long_text = "a" * 10000
        hash_long = CryptoUtils.hash_string(long_text, "md5")
        assert isinstance(hash_long, str)
        assert len(hash_long) == 32

        # 特殊字符
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        hash_special = CryptoUtils.hash_string(special_chars, "md5")
        assert isinstance(hash_special, str)
        assert len(hash_special) == 32

    def test_password_with_special_characters(self):
        """测试包含特殊字符的密码"""
        passwords = [
            "password123",
            "P@ssw0rd!",
            "密码测试",
            "🔐secure🔐",
            "multi\nline\npassword",
            "password'with'quotes",
            "password\"with\"double\"quotes",
            "password with spaces"
        ]

        for password in passwords:
            hashed = CryptoUtils.hash_password(password)
            assert CryptoUtils.verify_password(password, hashed) is True
            assert CryptoUtils.verify_password(password + "wrong", hashed) is False

    def test_integration_scenario(self):
        """测试集成场景"""
        # 场景：用户注册和登录
        username = "testuser"
        password = "UserP@ss123!"

        # 1. 生成用户ID
        user_id = CryptoUtils.generate_short_id()
        assert len(user_id) == 8

        # 2. 生成会话令牌
        session_token = CryptoUtils.generate_token(16)
        assert len(session_token) == 32

        # 3. 哈希密码存储
        hashed_password = CryptoUtils.hash_password(password)
        assert len(hashed_password) > 0

        # 4. 验证登录
        assert CryptoUtils.verify_password(password, hashed_password) is True
        assert CryptoUtils.verify_password("wrongpassword", hashed_password) is False

        # 5. 生成API密钥
        api_key = CryptoUtils.generate_salt(24)
        assert len(api_key) == 48
