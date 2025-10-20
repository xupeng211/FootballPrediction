import pytest
from src.utils.crypto_utils import CryptoUtils


def test_generate_uuid():
    """测试UUID生成"""
    uuid1 = CryptoUtils.generate_uuid()
    uuid2 = CryptoUtils.generate_uuid()
    assert uuid1 != uuid2
    assert len(uuid1) == 36  # UUID格式长度
    assert "-" in uuid1
    # 验证UUID格式 (8-4-4-4-12)
    parts = uuid1.split("-")
    assert len(parts) == 5
    assert len(parts[0]) == 8
    assert len(parts[1]) == 4
    assert len(parts[2]) == 4
    assert len(parts[3]) == 4
    assert len(parts[4]) == 12


def test_generate_short_id():
    """测试短ID生成"""
    id1 = CryptoUtils.generate_short_id()
    id2 = CryptoUtils.generate_short_id()
    assert id1 != id2
    assert len(id1) == 8
    assert id1.isalnum()
    # 测试自定义长度
    id_16 = CryptoUtils.generate_short_id(16)
    assert len(id_16) == 16
    id_4 = CryptoUtils.generate_short_id(4)
    assert len(id_4) == 4


def test_hash_string():
    """测试字符串哈希"""
    text = "hello world"
    hashed = CryptoUtils.hash_string(text)
    assert hashed != text
    assert len(hashed) == 32  # MD5长度
    # 测试一致性
    hashed2 = CryptoUtils.hash_string(text)
    assert hashed == hashed2
    # 测试不同算法
    sha256_hashed = CryptoUtils.hash_string(text, "sha256")
    assert len(sha256_hashed) == 64  # SHA256长度
    assert sha256_hashed != hashed


def test_hash_password():
    """测试密码哈希"""
    password = "test123"
    hashed = CryptoUtils.hash_password(password)
    assert hashed != password
    assert len(hashed) > 0
    # 测试验证
    assert CryptoUtils.verify_password(password, hashed) is True
    assert CryptoUtils.verify_password("wrong", hashed) is False
    # 测试自定义salt
    custom_hashed = CryptoUtils.hash_password(password, "custom_salt")
    assert custom_hashed != hashed
    assert CryptoUtils.verify_password(password, custom_hashed) is True


def test_encrypt_decrypt():
    """测试加密解密"""
    if hasattr(CryptoUtils, "encrypt") and hasattr(CryptoUtils, "decrypt"):
        text = "secret message"
        key = "test_key_123"
        encrypted = CryptoUtils.encrypt(text, key)
        assert encrypted != text
        decrypted = CryptoUtils.decrypt(encrypted, key)
        assert decrypted == text
        # 测试错误密钥
        with pytest.raises(Exception):
            CryptoUtils.decrypt(encrypted, "wrong_key")


def test_generate_token():
    """测试生成令牌"""
    if hasattr(CryptoUtils, "generate_token"):
        token1 = CryptoUtils.generate_token()
        token2 = CryptoUtils.generate_token()
        assert token1 != token2
        assert len(token1) > 20  # 令牌应该足够长
        # 测试自定义长度
        long_token = CryptoUtils.generate_token(64)
        assert len(long_token) == 64
