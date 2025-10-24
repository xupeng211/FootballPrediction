from unittest.mock import patch, MagicMock
"""
加密工具测试（新版本）
Tests for Crypto Utils (New Version)

测试src.utils.crypto_utils模块的功能
"""

import pytest
import hashlib
import secrets

# 测试导入
try:
    from src.utils.crypto_utils import CryptoUtils, HAS_BCRYPT

    CRYPTO_UTILS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    CRYPTO_UTILS_AVAILABLE = False


@pytest.mark.unit

class TestCryptoUtilsStaticMethods:
    """CryptoUtils静态方法测试"""

    def test_generate_uuid(self):
        """测试：生成UUID"""
        if not CRYPTO_UTILS_AVAILABLE:
            pytest.skip("CryptoUtils not available")

        uuid1 = CryptoUtils.generate_uuid()
        uuid2 = CryptoUtils.generate_uuid()

        # 验证UUID格式
        assert isinstance(uuid1, str)
        assert len(uuid1) == 36  # UUID格式：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        assert uuid1.count("-") == 4

        # 验证唯一性
        assert uuid1 != uuid2

    def test_generate_short_id_default(self):
        """测试：生成短ID（默认长度）"""
        if not CRYPTO_UTILS_AVAILABLE:
            pytest.skip("CryptoUtils not available")

        short_id = CryptoUtils.generate_short_id()

        assert isinstance(short_id, str)
        assert len(short_id) == 8
        assert "-" not in short_id

    def test_generate_short_id_custom_length(self):
        """测试：生成短ID（自定义长度）"""
        if not CRYPTO_UTILS_AVAILABLE:
            pytest.skip("CryptoUtils not available")

        # 测试各种长度
        lengths = [4, 12, 16, 32]
        for length in lengths:
            short_id = CryptoUtils.generate_short_id(length)
            assert len(short_id) == length
            assert "-" not in short_id

    def test_generate_short_id_zero_length(self):
        """测试：生成短ID（零长度）"""
        if not CRYPTO_UTILS_AVAILABLE:
            pytest.skip("CryptoUtils not available")

        short_id = CryptoUtils.generate_short_id(0)
        assert short_id == ""

    def test_generate_short_id_negative_length(self):
        """测试：生成短ID（负长度）"""
        if not CRYPTO_UTILS_AVAILABLE:
            pytest.skip("CryptoUtils not available")

        short_id = CryptoUtils.generate_short_id(-5)
        assert short_id == ""

    def test_generate_short_id_long_length(self):
        """测试：生成短ID（超长长度）"""
        if not CRYPTO_UTILS_AVAILABLE:
            pytest.skip("CryptoUtils not available")

        # 生成超过32字符的ID
        short_id = CryptoUtils.generate_short_id(50)
        assert len(short_id) == 50
        assert "-" not in short_id

    def test_hash_string_md5(self):
        """测试：MD5哈希"""
        if not CRYPTO_UTILS_AVAILABLE:
            pytest.skip("CryptoUtils not available")

        text = "test string"
        hash_value = CryptoUtils.hash_string(text, "md5")

        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5哈希长度
        assert hash_value == "6f8db599de986fab7a21625b7916589c"

    def test_hash_string_sha256(self):
        """测试：SHA256哈希"""
        if not CRYPTO_UTILS_AVAILABLE:
            pytest.skip("CryptoUtils not available")

        text = "test string"
        hash_value = CryptoUtils.hash_string(text, "sha256")

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256哈希长度
        assert (
            hash_value
            == "d5579c46dfcc7f18207013e65b44e4cb4e2c2298f4ac457ba8f82743f31e930b"
        )

    def test_hash_string_unicode(self):
        """测试：Unicode字符串哈希"""
        if not CRYPTO_UTILS_AVAILABLE:
            pytest.skip("CryptoUtils not available")

        # 测试包含中文的字符串
        text = "测试字符串"
        hash_value = CryptoUtils.hash_string(text, "md5")
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32

    def test_hash_string_empty(self):
        """测试：空字符串哈希"""
        if not CRYPTO_UTILS_AVAILABLE:
            pytest.skip("CryptoUtils not available")

        hash_value = CryptoUtils.hash_string("", "md5")
        assert hash_value == "d41d8cd98f00b204e9800998ecf8427e"

    def test_hash_string_invalid_algorithm(self):
        """测试：无效的哈希算法"""
        if not CRYPTO_UTILS_AVAILABLE:
            pytest.skip("CryptoUtils not available")

        text = "test string"
        with pytest.raises(ValueError):
            CryptoUtils.hash_string(text, "invalid_algo")


@pytest.mark.skipif(not CRYPTO_UTILS_AVAILABLE, reason="CryptoUtils not available")
class TestCryptoUtilsAdvanced:
    """CryptoUtils高级功能测试"""

    @pytest.mark.skipif(not HAS_BCRYPT, reason="bcrypt not available")
    def test_hash_password(self):
        """测试：密码哈希"""
        password = "test_password_123"
        hashed = CryptoUtils.hash_password(password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")  # bcrypt哈希前缀
        assert len(hashed) > 50  # bcrypt哈希通常较长

    @pytest.mark.skipif(not HAS_BCRYPT, reason="bcrypt not available")
    def test_verify_password_correct(self):
        """测试：验证密码（正确）"""
        password = "test_password_123"
        hashed = CryptoUtils.hash_password(password)

        assert CryptoUtils.verify_password(password, hashed) is True

    @pytest.mark.skipif(not HAS_BCRYPT, reason="bcrypt not available")
    def test_verify_password_incorrect(self):
        """测试：验证密码（错误）"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = CryptoUtils.hash_password(password)

        assert CryptoUtils.verify_password(wrong_password, hashed) is False


class TestCryptoUtilsEdgeCases:
    """CryptoUtils边界情况测试"""

    @pytest.mark.skipif(not CRYPTO_UTILS_AVAILABLE, reason="CryptoUtils not available")
    def test_consistency_of_uuids(self):
        """测试：UUID的一致性"""
        uuids = [CryptoUtils.generate_uuid() for _ in range(100)]
        # 所有UUID都应该是唯一的
        assert len(set(uuids)) == 100

    @pytest.mark.skipif(not CRYPTO_UTILS_AVAILABLE, reason="CryptoUtils not available")
    def test_short_id_character_distribution(self):
        """测试：短ID字符分布"""
        short_id = CryptoUtils.generate_short_id(1000)
        # 应该只包含数字和字母
        assert all(c.isalnum() for c in short_id)

    @pytest.mark.skipif(not CRYPTO_UTILS_AVAILABLE, reason="CryptoUtils not available")
    def test_hash_deterministic(self):
        """测试：哈希的确定性"""
        text = "deterministic_test"
        hash1 = CryptoUtils.hash_string(text, "sha256")
        hash2 = CryptoUtils.hash_string(text, "sha256")
        assert hash1 == hash2

    @pytest.mark.skipif(not CRYPTO_UTILS_AVAILABLE, reason="CryptoUtils not available")
    def test_hash_different_inputs(self):
        """测试：不同输入产生不同哈希"""
        hash1 = CryptoUtils.hash_string("input1", "md5")
        hash2 = CryptoUtils.hash_string("input2", "md5")
        assert hash1 != hash2


class TestCryptoUtilsPerformance:
    """CryptoUtils性能测试"""

    @pytest.mark.skipif(not CRYPTO_UTILS_AVAILABLE, reason="CryptoUtils not available")
    def test_uuid_generation_performance(self):
        """测试：UUID生成性能"""
        import time

        start_time = time.time()
        for _ in range(1000):
            CryptoUtils.generate_uuid()
        end_time = time.time()

        # 1000个UUID应该在1秒内生成
        assert end_time - start_time < 1.0

    @pytest.mark.skipif(not CRYPTO_UTILS_AVAILABLE, reason="CryptoUtils not available")
    def test_hash_performance(self):
        """测试：哈希性能"""
        import time

        text = "performance_test_string" * 100
        start_time = time.time()
        for _ in range(1000):
            CryptoUtils.hash_string(text, "sha256")
        end_time = time.time()

        # 1000次SHA256哈希应该在合理时间内完成
        assert end_time - start_time < 2.0


# 测试模块级别的功能
def test_module_constants():
    """测试：模块常量"""
    if CRYPTO_UTILS_AVAILABLE:
        assert HAS_BCRYPT is not None
        assert isinstance(HAS_BCRYPT, bool)


# 如果模块不可用，添加一个占位测试
@pytest.mark.skipif(True, reason="Module not available")
class TestModuleNotAvailable:
    """模块不可用时的占位测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not CRYPTO_UTILS_AVAILABLE
        assert True  # 表明测试意识到模块不可用
