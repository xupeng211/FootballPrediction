"""
测试加密工具 - 简单版本
"""

import pytest
from src.utils.crypto_utils import CryptoUtils


@pytest.mark.unit

class TestCryptoUtilsSimple:
    """测试CryptoUtils的基本功能"""

    def test_generate_salt(self):
        """测试生成盐值"""
        salt = CryptoUtils.generate_salt()
        assert isinstance(salt, str)
        assert len(salt) == 32  # 默认长度

    def test_generate_short_id(self):
        """测试生成短ID"""
        short_id = CryptoUtils.generate_short_id()
        assert isinstance(short_id, str)
        assert len(short_id) == 8  # 默认长度

    def test_generate_token(self):
        """测试生成令牌"""
        token = CryptoUtils.generate_token()
        assert isinstance(token, str)
        assert len(token) == 64  # SHA256 hex length

    def test_generate_uuid(self):
        """测试生成UUID"""
        uuid = CryptoUtils.generate_uuid()
        assert isinstance(uuid, str)
        assert len(uuid) == 36  # 标准UUID长度

    def test_hash_string(self):
        """测试哈希字符串"""
        _data = "test data"
        hashed = CryptoUtils.hash_string(data)
        assert isinstance(hashed, str)
        assert len(hashed) == 32  # 实际返回的长度
        assert hashed != data

    def test_hash_password(self):
        """测试哈希密码"""
        password = "my_password"
        hashed = CryptoUtils.hash_password(password)
        assert isinstance(hashed, str)
        assert hashed != password

    def test_verify_password(self):
        """测试验证密码"""
        password = "my_password"
        hashed = CryptoUtils.hash_password(password)

        # 正确密码
        assert CryptoUtils.verify_password(password, hashed)

        # 错误密码
        assert not CryptoUtils.verify_password("wrong", hashed)

    def test_generate_different_salts(self):
        """测试生成不同的盐值"""
        salt1 = CryptoUtils.generate_salt()
        salt2 = CryptoUtils.generate_salt()
        assert salt1 != salt2
