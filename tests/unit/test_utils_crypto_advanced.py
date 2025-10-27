# 加密工具高级测试
import pytest

from src.utils.crypto_utils import CryptoUtils


@pytest.mark.unit
def test_hash_password():
    password = "test123"
    hashed = CryptoUtils.hash_password(password)
    assert hashed != password
    assert len(hashed) > 0


def test_generate_token():
    token = CryptoUtils.generate_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_token():
    token = CryptoUtils.generate_token()
    assert CryptoUtils.verify_token(token) is True
    assert CryptoUtils.verify_token("invalid") is False


def test_encrypt_decrypt():
    data = "secret message"
    encrypted = CryptoUtils.encrypt(data)
    decrypted = CryptoUtils.decrypt(encrypted)
    assert decrypted == data


def test_generate_id():
    id1 = CryptoUtils.generate_id()
    id2 = CryptoUtils.generate_id()
    assert id1 != id2
    assert isinstance(id1, str)
    assert len(id1) > 0
