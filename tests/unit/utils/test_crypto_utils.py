import pytest
from src.utils.crypto_utils import CryptoUtils

"""
测试加密工具模块
"""


class TestCryptoUtils:
    """测试CryptoUtils类"""

    def test_generate_uuid(self):
        """测试生成UUID"""
        uid = CryptoUtils.generate_uuid()
        assert isinstance(uid, str)
        assert len(uid) == 36  # UUID格式: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        assert uid.count("-") == 4

    def test_generate_uuid_unique(self):
        """测试UUID唯一性"""
        uids = {CryptoUtils.generate_uuid() for _ in range(100)}
        assert len(uids) == 100  # 所有UUID都应该不同

    def test_generate_short_id_default_length(self):
        """测试生成默认长度的短ID"""
        short_id = CryptoUtils.generate_short_id()
        assert isinstance(short_id, str)
        assert len(short_id) == 8

    def test_generate_short_id_custom_length(self):
        """测试生成自定义长度的短ID"""
        for length in [4, 12, 16, 32]:
            short_id = CryptoUtils.generate_short_id(length)
            assert len(short_id) == length

    def test_generate_short_id_zero_length(self):
        """测试长度为0的情况"""
        short_id = CryptoUtils.generate_short_id(0)
        assert short_id == ""

    def test_generate_short_id_negative_length(self):
        """测试负长度"""
        short_id = CryptoUtils.generate_short_id(-5)
        assert short_id == ""

    def test_generate_short_id_long_length(self):
        """测试超长ID"""
        long_id = CryptoUtils.generate_short_id(100)
        assert len(long_id) == 100
        # 应该只包含数字和字母
        assert long_id.isalnum()

    def test_hash_string_md5(self):
        """测试MD5哈希"""
        text = "hello"
        hash_value = CryptoUtils.hash_string(text, "md5")
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32
        assert hash_value == "5d41402abc4b2a76b9719d911017c592"

    def test_hash_string_sha256(self):
        """测试SHA256哈希"""
        text = "hello"
        hash_value = CryptoUtils.hash_string(text, "sha256")
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64

    def test_hash_string_unsupported_algorithm(self):
        """测试不支持的哈希算法"""
        with pytest.raises(ValueError, match="不支持的哈希算法"):
            CryptoUtils.hash_string("test", "sha1")

    def test_hash_password_without_bcrypt(self):
        """测试无bcrypt时的密码哈希"""
        password = "testpassword123"
        hashed = CryptoUtils.hash_password(password)
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$12$")
        assert "$" in hashed
        assert len(hashed) > 30

    def test_hash_password_with_salt(self):
        """测试使用指定盐值的密码哈希"""
        password = "testpassword123"
        salt = "testsalt123"
        hashed = CryptoUtils.hash_password(password, salt)
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$12$")
        assert salt in hashed

    def test_verify_password_empty(self):
        """测试空密码验证"""
        assert CryptoUtils.verify_password("", "")

    def test_verify_password_false(self):
        """测试错误的密码验证"""
        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = CryptoUtils.hash_password(password)
        assert not CryptoUtils.verify_password(wrong_password, hashed)

    def test_generate_salt(self):
        """测试生成盐值"""
        salt = CryptoUtils.generate_salt()
        assert isinstance(salt, str)
        assert len(salt) == 32  # 16 bytes * 2 (hex)

    def test_generate_salt_custom_length(self):
        """测试生成自定义长度的盐值"""
        salt = CryptoUtils.generate_salt(10)
        assert isinstance(salt, str)
        assert len(salt) == 20  # 10 bytes * 2 (hex)

    def test_generate_token(self):
        """测试生成令牌"""
        token = CryptoUtils.generate_token()
        assert isinstance(token, str)
        assert len(token) == 64  # 32 bytes * 2 (hex)

    def test_generate_token_custom_length(self):
        """测试生成自定义长度的令牌"""
        token = CryptoUtils.generate_token(10)
        assert isinstance(token, str)
        assert len(token) == 20  # 10 bytes * 2 (hex)

    def test_generate_token_unique(self):
        """测试令牌唯一性"""
        tokens = {CryptoUtils.generate_token() for _ in range(100)}
        assert len(tokens) == 100  # 所有令牌都应该不同

    def test_hash_string_unicode(self):
        """测试Unicode字符串哈希"""
        text = "你好，世界！"
        md5_hash = CryptoUtils.hash_string(text, "md5")
        sha256_hash = CryptoUtils.hash_string(text, "sha256")
        assert isinstance(md5_hash, str)
        assert isinstance(sha256_hash, str)
        assert len(md5_hash) == 32
        assert len(sha256_hash) == 64
