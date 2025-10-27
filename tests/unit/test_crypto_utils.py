#!/usr/bin/env python3
"""
加密工具测试
测试 src.utils.crypto_utils 模块的功能
"""

import pytest

from src.utils.crypto_utils import CryptoUtils


@pytest.mark.unit
class TestCryptoUtils:
    """加密工具测试"""

    def test_generate_salt(self):
        """测试生成盐值"""
        salt1 = CryptoUtils.generate_salt()
        salt2 = CryptoUtils.generate_salt()

        # 验证返回的是字符串
        assert isinstance(salt1, str)
        assert isinstance(salt2, str)

        # 验证长度合理
        assert len(salt1) > 0
        assert len(salt2) > 0

        # 验证每次生成的盐值都不同
        assert salt1 != salt2

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test_password_123"
        salt = "test_salt_456"

        hashed = CryptoUtils.hash_password(password, salt)

        # 验证返回的是字符串
        assert isinstance(hashed, str)

        # 验证哈希值不为空
        assert len(hashed) > 0

        # 验证相同密码和盐产生相同哈希
        hashed2 = CryptoUtils.hash_password(password, salt)
        assert hashed == hashed2

    def test_hash_password_different_inputs(self):
        """测试不同输入的哈希结果"""
        password1 = "password1"
        password2 = "password2"
        salt = "same_salt"

        hashed1 = CryptoUtils.hash_password(password1, salt)
        hashed2 = CryptoUtils.hash_password(password2, salt)

        # 不同密码应该产生不同哈希
        assert hashed1 != hashed2

    def test_hash_password_different_salts(self):
        """测试不同盐值的哈希结果"""
        password = "same_password"
        salt1 = "salt1"
        salt2 = "salt2"

        hashed1 = CryptoUtils.hash_password(password, salt1)
        hashed2 = CryptoUtils.hash_password(password, salt2)

        # 不同盐应该产生不同哈希
        assert hashed1 != hashed2

    def test_verify_password(self):
        """测试密码验证"""
        password = "correct_password"
        salt = CryptoUtils.generate_salt()
        hashed = CryptoUtils.hash_password(password, salt)

        # 正确密码应该验证通过
        assert CryptoUtils.verify_password(password, salt, hashed) is True

        # 错误密码应该验证失败
        assert CryptoUtils.verify_password("wrong_password", salt, hashed) is False

    def test_verify_password_wrong_salt(self):
        """测试错误盐值的密码验证"""
        password = "test_password"
        salt1 = "salt1"
        salt2 = "salt2"
        hashed = CryptoUtils.hash_password(password, salt1)

        # 使用错误盐应该验证失败
        assert CryptoUtils.verify_password(password, salt2, hashed) is False

    def test_hash_empty_password(self):
        """测试空密码哈希"""
        empty_password = ""
        salt = "test_salt"

        hashed = CryptoUtils.hash_password(empty_password, salt)

        # 空密码也应该能哈希
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_unicode_password(self):
        """测试Unicode密码哈希"""
        unicode_password = "测试密码🔐"
        salt = "test_salt"

        hashed = CryptoUtils.hash_password(unicode_password, salt)

        # Unicode密码应该能哈希
        assert isinstance(hashed, str)
        assert len(hashed) > 0

        # 应该能验证
        assert CryptoUtils.verify_password(unicode_password, salt, hashed) is True

    def test_consistent_hashing(self):
        """测试哈希的一致性"""
        password = "consistent_test"
        salt = "consistent_salt"

        # 多次哈希应该产生相同结果
        hash1 = CryptoUtils.hash_password(password, salt)
        hash2 = CryptoUtils.hash_password(password, salt)
        hash3 = CryptoUtils.hash_password(password, salt)

        assert hash1 == hash2 == hash3

    def test_salt_length_consistency(self):
        """测试盐值长度一致性"""
        salts = [CryptoUtils.generate_salt() for _ in range(10)]

        # 所有盐值应该有相同长度
        lengths = [len(salt) for salt in salts]
        assert len(set(lengths)) == 1  # 所有长度相同

        # 盐值应该包含多种字符
        for salt in salts:
            assert any(c.isalpha() for c in salt)  # 包含字母
            assert any(c.isdigit() for c in salt)  # 包含数字
