"""加密工具增强测试"""

import pytest
import hashlib
import hmac
import base64
from src.utils.crypto_utils import (
    generate_hash,
    verify_hash,
    encrypt_data,
    decrypt_data,
    generate_salt,
    hash_password,
    verify_password,
    generate_api_key,
    generate_secure_token,
    encode_base64,
    decode_base64
)


class TestCryptoUtilsEnhanced:
    """加密工具增强测试"""

    def test_generate_hash_different_algorithms(self):
        """测试不同哈希算法"""
        data = "test data"

        # 测试不同算法
        algorithms = ['sha256', 'sha512', 'md5']
        for algo in algorithms:
            hash_value = generate_hash(data, algorithm=algo)
            assert isinstance(hash_value, str)
            assert len(hash_value) > 0

    def test_verify_hash_valid(self):
        """测试哈希验证 - 有效情况"""
        data = "test data"
        hash_value = generate_hash(data)
        assert verify_hash(data, hash_value) is True

    def test_verify_hash_invalid(self):
        """测试哈希验证 - 无效情况"""
        data = "test data"
        wrong_hash = generate_hash("wrong data")
        assert verify_hash(data, wrong_hash) is False

    def test_encrypt_decrypt_roundtrip(self):
        """测试加密解密往返"""
        data = {"message": "secret", "number": 42}
        key = "test_key_123"

        # 加密
        encrypted = encrypt_data(data, key)
        assert isinstance(encrypted, str)
        assert encrypted != str(data)

        # 解密
        decrypted = decrypt_data(encrypted, key)
        assert decrypted == data

    def test_encrypt_with_different_keys(self):
        """测试不同密钥加密"""
        data = "test data"
        keys = ["key1", "key2", "key3"]

        encrypted_values = []
        for key in keys:
            encrypted = encrypt_data(data, key)
            encrypted_values.append(encrypted)

        # 不同密钥应该产生不同的加密结果
        assert len(set(encrypted_values)) == len(keys)

    def test_decrypt_with_wrong_key(self):
        """测试错误密钥解密"""
        data = "test data"
        key = "correct_key"
        wrong_key = "wrong_key"

        encrypted = encrypt_data(data, key)

        # 使用错误密钥解密应该失败
        with pytest.raises(Exception):
            decrypt_data(encrypted, wrong_key)

    def test_generate_salt_uniqueness(self):
        """测试盐的唯一性"""
        salts = [generate_salt() for _ in range(10)]
        assert len(set(salts)) == 10
        assert all(len(salt) >= 32 for salt in salts)

    def test_hash_password_with_salt(self):
        """测试密码哈希带盐"""
        password = "my_password_123"
        salt = generate_salt()

        hashed = hash_password(password, salt)
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """测试密码验证 - 正确情况"""
        password = "my_password_123"
        salt = generate_salt()
        hashed = hash_password(password, salt)

        assert verify_password(password, salt, hashed) is True

    def test_verify_password_incorrect(self):
        """测试密码验证 - 错误情况"""
        password = "my_password_123"
        wrong_password = "wrong_password"
        salt = generate_salt()
        hashed = hash_password(password, salt)

        assert verify_password(wrong_password, salt, hashed) is False

    def test_generate_api_key_format(self):
        """测试API密钥格式"""
        api_key = generate_api_key()
        assert isinstance(api_key, str)
        assert len(api_key) >= 32  # 至少32个字符
        # 应该只包含字母数字字符
        assert api_key.isalnum()

    def test_generate_api_key_prefix(self):
        """测试带前缀的API密钥"""
        prefix = "test_"
        api_key = generate_api_key(prefix=prefix)
        assert api_key.startswith(prefix)
        assert len(api_key) > len(prefix)

    def test_generate_secure_token_length(self):
        """测试安全令牌长度"""
        # 测试不同长度
        lengths = [16, 32, 64, 128]
        for length in lengths:
            token = generate_secure_token(length)
            assert len(token) == length
            assert token.isalnum()

    def test_base64_encode_decode(self):
        """测试Base64编码解码"""
        data = "Hello, World! 你好，世界！"

        # 编码
        encoded = encode_base64(data)
        assert isinstance(encoded, str)
        assert encoded != data

        # 解码
        decoded = decode_base64(encoded)
        assert decoded == data

    def test_base64_encode_bytes(self):
        """测试Base64编码字节数据"""
        data = b"binary data"

        encoded = encode_base64(data)
        decoded = decode_base64(encoded)
        assert decoded == data

    def test_hmac_signature(self):
        """测试HMAC签名"""
        message = "important message"
        secret_key = "secret_key_123"

        # 生成签名
        signature = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex长度

    def test_crypto_performance(self):
        """测试加密性能"""
        import time

        data = "test data" * 100  # 较大的数据
        key = "test_key"

        # 测试加密性能
        start = time.time()
        for _ in range(100):
            encrypt_data(data, key)
        encrypt_time = time.time() - start

        # 测试解密性能
        encrypted = encrypt_data(data, key)
        start = time.time()
        for _ in range(100):
            decrypt_data(encrypted, key)
        decrypt_time = time.time() - start

        # 性能应该在合理范围内
        assert encrypt_time < 1.0
        assert decrypt_time < 1.0