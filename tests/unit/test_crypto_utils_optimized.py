"""
优化后的crypto_utils测试
"""

import pytest
from src.utils.crypto_utils import CryptoUtils, HAS_BCRYPT

class TestBasicCryptoOperations:
    """基础加密操作测试"""

    def test_uuid_generation(self):
        """测试UUID生成"""
        uuid1 = CryptoUtils.generate_uuid()
        uuid2 = CryptoUtils.generate_uuid()

        assert isinstance(uuid1, str)
        assert len(uuid1) == 36
        assert uuid1 != uuid2
        assert uuid1.count('-') == 4

    def test_hash_string_basic(self):
        """测试基础字符串哈希"""
        text = "test_string"

        # 测试MD5
        md5_hash = CryptoUtils.hash_string(text, "md5")
        assert isinstance(md5_hash, str)
        assert len(md5_hash) == 32

        # 测试SHA256
        sha256_hash = CryptoUtils.hash_string(text, "sha256")
        assert isinstance(sha256_hash, str)
        assert len(sha256_hash) == 64

    def test_file_hash_basic(self):
        """测试文件哈希（使用临时文件）"""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_content = b"test content for hashing"
            f.write(test_content)
            temp_path = f.name

        try:
            file_hash = CryptoUtils.get_file_hash(temp_path)
            assert isinstance(file_hash, str)
            assert len(file_hash) == 32  # MD5 length
        finally:
            os.unlink(temp_path)

    def test_short_id_generation(self):
        """测试短ID生成"""
        short_id = CryptoUtils.generate_short_id(8)
        assert len(short_id) == 8
        assert short_id.isalnum()

    @pytest.mark.skipif(not HAS_BCRYPT, reason="bcrypt not available")
    def test_password_hashing_with_bcrypt(self):
        """测试密码哈希（如果有bcrypt）"""
        password = "test_password_123"

        hashed = CryptoUtils.hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 50

        # 验证密码
        assert CryptoUtils.verify_password(password, hashed)

if __name__ == "__main__":
    pytest.main([__file__])
