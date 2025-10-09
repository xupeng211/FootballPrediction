"""加密工具测试"""

import pytest
from src.utils.crypto_utils import CryptoUtils


class TestCryptoUtils:
    """加密工具测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test123"
        hashed = CryptoUtils.hash_password(password)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password(self):
        """测试密码验证"""
        password = "test123"
        hashed = CryptoUtils.hash_password(password)
        assert CryptoUtils.verify_password(password, hashed) is True
        assert CryptoUtils.verify_password("wrong", hashed) is False

    def test_generate_token(self):
        """测试生成令牌"""
        token = CryptoUtils.generate_token()
        assert len(token) > 0
        assert isinstance(token, str)
