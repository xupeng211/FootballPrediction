from unittest.mock import patch, MagicMock
"""
测试密钥管理器
"""

import pytest
from src.security.key_manager import KeyManager


@pytest.mark.unit

def test_key_manager_get_key():
    """测试获取密钥"""
    manager = KeyManager()

    # 测试获取存在的密钥
    with patch.dict("os.environ", {"API_KEY": "secret123"}):
    with patch.dict("os.environ", {"API_KEY": "secret123"}):
    with patch.dict("os.environ", {"API_KEY": "secret123"}):
        key = manager.get_key("API_KEY")
        assert key == "secret123"

    # 测试获取不存在的密钥
    key = manager.get_key("NON_EXISTENT_KEY")
    assert key is None


def test_key_manager_set_key():
    """测试设置密钥"""
    manager = KeyManager()

    # 注意：这里实际上不应该设置环境变量
    # 在真实实现中，应该使用安全的密钥存储
    with patch("os.environ") as mock_env:
    with patch("os.environ") as mock_env:
    with patch("os.environ") as mock_env:
        manager.set_key("TEST_KEY", "test_value")
        mock_env.__setitem__.assert_called_with("TEST_KEY", "test_value")


def test_key_manager_get_encrypted_key():
    """测试获取加密密钥"""
    manager = KeyManager()

    # 模拟加密的密钥
    with patch.object(manager, "_decrypt_key", return_value="decrypted_value"):
        with patch.dict("os.environ", {"ENCRYPTED_KEY": "encrypted_value"}):
            key = manager.get_encrypted_key("ENCRYPTED_KEY")
            assert key == "decrypted_value"


def test_key_manager_rotate_key():
    """测试密钥轮换"""
    manager = KeyManager()

    with patch("os.environ") as mock_env:
    with patch("os.environ") as mock_env:
    with patch("os.environ") as mock_env:
        # 模拟生成新密钥
        with patch.object(manager, "_generate_new_key", return_value="new_key_value"):
            new_key = manager.rotate_key("TEST_KEY")
            assert new_key == "new_key_value"
            mock_env.__setitem__.assert_called_with("TEST_KEY", "new_key_value")
