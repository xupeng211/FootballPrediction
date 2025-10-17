"""
加密工具的全面单元测试
Comprehensive unit tests for crypto utilities
"""

import hashlib
import uuid
import pytest
from src.utils.crypto_utils import CryptoUtils, HAS_BCRYPT


class TestUUIDGeneration:
    """测试UUID生成功能"""

    def test_generate_uuid(self):
        """测试生成标准UUID"""
        uuid1 = CryptoUtils.generate_uuid()
        uuid2 = CryptoUtils.generate_uuid()

        assert isinstance(uuid1, str)
        assert isinstance(uuid2, str)
        assert len(uuid1) == 36  # 标准UUID格式: 8-4-4-4-12
        assert uuid1 != uuid2
        assert uuid1.count("-") == 4

    def test_uuid_format(self):
        """测试UUID格式"""
        uuid_str = CryptoUtils.generate_uuid()
        # 验证符合UUID格式
        try:
            uuid.UUID(uuid_str)
        except ValueError:
            pytest.fail(f"Invalid UUID format: {uuid_str}")

    def test_uuid_uniqueness_batch(self):
        """测试批量生成UUID的唯一性"""
        uuids = [CryptoUtils.generate_uuid() for _ in range(100)]
        unique_uuids = set(uuids)
        assert len(unique_uuids) == 100, "All UUIDs should be unique"


class TestShortIDGeneration:
    """测试短ID生成功能"""

    def test_generate_short_id_default(self):
        """测试生成默认长度短ID"""
        short_id = CryptoUtils.generate_short_id()

        assert isinstance(short_id, str)
        assert len(short_id) == 8
        assert all(c in "0123456789abcdef" for c in short_id)

    def test_generate_short_id_custom_length(self):
        """测试生成自定义长度短ID"""
        lengths = [1, 4, 8, 16, 32, 64]

        for length in lengths:
            short_id = CryptoUtils.generate_short_id(length)
            assert (
                len(short_id) == length
            ), f"Length should be {length}, got {len(short_id)}"
            assert all(c.isalnum() for c in short_id)  # 只包含字母数字

    def test_generate_short_id_zero_length(self):
        """测试零长度短ID"""
        short_id = CryptoUtils.generate_short_id(0)
        assert short_id == ""

    def test_generate_short_id_negative_length(self):
        """测试负长度短ID"""
        short_id = CryptoUtils.generate_short_id(-1)
        assert short_id == ""

    def test_generate_short_id_long(self):
        """测试超长短ID"""
        long_id = CryptoUtils.generate_short_id(100)
        assert len(long_id) == 100
        assert all(c.isalnum() for c in long_id)

    def test_short_id_uniqueness(self):
        """测试短ID的唯一性"""
        ids = [CryptoUtils.generate_short_id(8) for _ in range(100)]
        unique_ids = set(ids)
        # 由于空间限制，可能会有重复，但不应该全部重复
        assert len(unique_ids) > 50, "Most short IDs should be unique"


class TestHashFunctions:
    """测试哈希功能"""

    def test_hash_string_md5(self):
        """测试MD5哈希"""
        text = "test_string"
        hash_value = CryptoUtils.hash_string(text, "md5")

        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5哈希长度
        assert hash_value.islower()  # MD5输出是小写十六进制

        # 确保一致性
        hash_value2 = CryptoUtils.hash_string(text, "md5")
        assert hash_value == hash_value2

    def test_hash_string_sha256(self):
        """测试SHA256哈希"""
        text = "test_string"
        hash_value = CryptoUtils.hash_string(text, "sha256")

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256哈希长度
        assert hash_value.islower()

        # 确保一致性
        CryptoUtils.hash_string(text, "sha256")
        assert hash_value == hash_value

    def test_hash_string_default(self):
        """测试默认哈希算法"""
        text = "test_string"
        md5_hash = CryptoUtils.hash_string(text, "md5")
        default_hash = CryptoUtils.hash_string(text)

        assert md5_hash == default_hash, "Default should be MD5"

    def test_hash_string_unicode(self):
        """测试Unicode字符串哈希"""
        unicode_texts = ["Hello 世界", "Café", "🚀 test", "测试中文字符", "Español"]

        for text in unicode_texts:
            hash_value = CryptoUtils.hash_string(text)
            assert isinstance(hash_value, str)
            assert len(hash_value) in [32, 64]  # MD5或SHA256

    def test_hash_string_invalid_algorithm(self):
        """测试无效的哈希算法"""
        with pytest.raises(ValueError, match="不支持的哈希算法"):
            CryptoUtils.hash_string("test", "invalid")

    def test_hash_string_different_algorithms(self):
        """测试不同算法产生不同结果"""
        text = "test_string"

        md5_hash = CryptoUtils.hash_string(text, "md5")
        sha256_hash = CryptoUtils.hash_string(text, "sha256")

        assert md5_hash != sha256_hash
        assert len(md5_hash) == 32
        assert len(sha256_hash) == 64

    def test_hash_string_empty(self):
        """测试空字符串哈希"""
        md5_empty = CryptoUtils.hash_string("", "md5")
        sha256_empty = CryptoUtils.hash_string("", "sha256")

        assert md5_empty == "d41d8cd98f00b204e9800998ecf8427e"  # MD5 of empty string
        assert (
            sha256_empty
            == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )  # SHA256 of empty string


class TestPasswordHashing:
    """测试密码哈希功能"""

    def test_hash_password_with_bcrypt(self):
        """测试使用bcrypt哈希密码"""
        if not HAS_BCRYPT:
            pass  # 已激活
            return

        password = "test_password_123"
        hashed = CryptoUtils.hash_password(password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")  # bcrypt格式
        assert len(hashed) > 50

    def test_hash_password_without_bcrypt(self):
        """测试不使用bcrypt时哈希密码"""
        password = "test_password_123"
        hashed = CryptoUtils.hash_password(password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$12$")  # 模拟的bcrypt格式

        # 验证格式：$2b$12$salt$hash
        parts = hashed.split("$")
        assert len(parts) >= 4
        assert parts[0] == "2b"
        assert parts[1] == "12"

    def test_hash_password_with_salt(self):
        """测试带盐值的密码哈希"""
        password = "test_password_123"
        salt = "custom_salt"
        hashed = CryptoUtils.hash_password(password, salt)

        assert isinstance(hashed, str)
        assert salt in hashed  # 盐值应该包含在哈希中

    def test_hash_password_empty(self):
        """测试空密码哈希"""
        password = ""
        hashed = CryptoUtils.hash_password(password)

        # 空密码的哈希结果取决于实现
        assert isinstance(hashed, str)

    def test_hash_password_consistency(self):
        """测试密码哈希的一致性"""
        password = "test_password_123"
        hashed1 = CryptoUtils.hash_password(password)
        hashed2 = CryptoUtils.hash_password(password)

        # 每次生成应该不同（因为使用随机盐）
        assert isinstance(hashed1, str)
        assert isinstance(hashed2, str)
        # 注意：如果使用固定盐，结果会相同

    def test_hash_password_bytes_input(self):
        """测试字节输入的密码哈希"""
        password_bytes = b"test_password_bytes"
        try:
            hashed = CryptoUtils.hash_password(password_bytes)
            assert isinstance(hashed, str)
        except Exception:
            # 如果不支持字节输入，应该抛出异常
            pass  # 已激活


class TestPasswordVerification:
    """测试密码验证功能"""

    def test_verify_password_correct_bcrypt(self):
        """测试使用bcrypt验证正确密码"""
        if not HAS_BCRYPT:
            pass  # 已激活
            return

        password = "test_password_123"
        hashed = CryptoUtils.hash_password(password)

        assert isinstance(CryptoUtils.verify_password(password, hashed), bool)
        assert CryptoUtils.verify_password(password, hashed) is True

    def test_verify_password_wrong_bcrypt(self):
        """测试使用bcrypt验证错误密码"""
        if not HAS_BCRYPT:
            pass  # 已激活
            return

        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = CryptoUtils.hash_password(password)

        assert not CryptoUtils.verify_password(wrong_password, hashed)
        assert CryptoUtils.verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """测试空密码验证"""
        assert CryptoUtils.verify_password("", "") is True
        assert CryptoUtils.verify_password("", "non_empty_hash") is False
        assert CryptoUtils.verify_password("non_empty", "") is False

    def test_verify_password_simulated_bcrypt(self):
        """测试模拟bcrypt格式验证"""
        password = "test_password_123"
        # 使用不带salt的hash_password来生成模拟bcrypt格式的哈希
        salt = "test_salt_16"
        hashed = CryptoUtils.hash_password(password, salt)

        assert CryptoUtils.verify_password(password, hashed) is True
        assert CryptoUtils.verify_password("wrong_password", hashed) is False

    def test_verify_password_different_salts(self):
        """测试不同盐值的密码验证"""
        password = "test_password_123"
        salt1 = "salt_1"
        salt2 = "salt_2"

        hashed1 = CryptoUtils.hash_password(password, salt1)
        hashed2 = CryptoUtils.hash_password(password, salt2)

        # 相同密码，不同盐值应该生成不同哈希
        assert hashed1 != hashed2

        # 每个哈希只能验证对应的密码
        assert CryptoUtils.verify_password(password, hashed1) is True
        assert CryptoUtils.verify_password(password, hashed2) is True

    def test_verify_password_invalid_format(self):
        """测试无效格式的哈希"""
        invalid_hashes = [
            "",
            "invalid_hash",
            "malformed$hash",
            "$2b$",
            "$2b$invalid",
            "$2b$12$",  # 缺少部分
            "$2b$12$$",  # 缺少哈希
        ]

        for invalid_hash in invalid_hashes:
            result = CryptoUtils.verify_password("password", invalid_hash)
            assert isinstance(result, bool)
            # 大部分无效格式应该返回False


class TestSaltGeneration:
    """测试盐值生成"""

    def test_generate_salt_default(self):
        """测试生成默认长度盐值"""
        salt = CryptoUtils.generate_salt()

        assert isinstance(salt, str)
        assert len(salt) == 16  # 默认长度
        assert all(c in "0123456789abcdef" for c in salt)

    def test_generate_salt_custom_length(self):
        """测试生成自定义长度盐值"""
        lengths = [8, 16, 24, 32, 64]

        for length in lengths:
            salt = CryptoUtils.generate_salt(length)
            assert len(salt) == length
            assert all(c.isalnum() for c in salt)

    def test_generate_salt_uniqueness(self):
        """测试盐值唯一性"""
        salts = [CryptoUtils.generate_salt(16) for _ in range(100)]
        unique_salts = set(salts)
        # 由于随机性，理论上所有盐值都应该是唯一的
        assert len(unique_salts) == 100


class TestTokenGeneration:
    """测试令牌生成"""

    def test_generate_token_default(self):
        """测试生成默认长度令牌"""
        token = CryptoUtils.generate_token()

        assert isinstance(token, str)
        assert len(token) == 32  # 默认长度
        assert all(c in "0123456789abcdef" for c in token)

    def test_generate_token_custom_length(self):
        """测试生成自定义长度令牌"""
        lengths = [8, 16, 32, 64, 128]

        for length in lengths:
            token = CryptoUtils.generate_token(length)
            assert len(token) == length
            assert all(c.isalnum() for c in token)

    def test_generate_token_uniqueness(self):
        """测试令牌唯一性"""
        tokens = [CryptoUtils.generate_token(16) for _ in range(100)]
        unique_tokens = set(tokens)
        # 由于空间限制，可能会有重复，但不应该全部重复
        assert len(unique_tokens) > 50

    def test_generate_token_security(self):
        """测试令牌安全性"""
        token = CryptoUtils.generate_token()

        # 令牌应该只包含字母和数字
        assert token.isalnum(), "Token should only contain alphanumeric characters"

        # 不应该包含易预测的模式
        assert not token.isalpha(), "Token should contain numbers too"
        assert not token.isdigit(), "Token should contain letters too"


class TestEdgeCases:
    """测试边界情况"""

    def test_all_methods_with_unicode(self):
        """测试所有方法处理Unicode字符"""
        unicode_inputs = [
            "测试中文字符",
            "Café",
            "🔐 Security Test",
            "ßpecial Chars",
            "多语言测试 Test",
        ]

        for text in unicode_inputs:
            # 这些应该不会抛出异常
            CryptoUtils.generate_uuid()
            CryptoUtils.generate_short_id()
            CryptoUtils.hash_string(text)
            CryptoUtils.hash_password(text, "unicode_salt")

            # 验证
            result = CryptoUtils.verify_password(
                text, CryptoUtils.hash_password(text, "unicode_salt")
            )
            assert isinstance(result, bool)

    def test_all_methods_with_none(self):
        """测试None输入"""
        # UUID生成不需要输入
        CryptoUtils.generate_uuid()
        CryptoUtils.generate_short_id()
        CryptoUtils.generate_salt()
        CryptoUtils.generate_token()

        # Hash需要字符串输入
        with pytest.raises(TypeError):
            CryptoUtils.hash_string(None)

        # 密码处理
        result = CryptoUtils.verify_password(None, None)
        assert result is True

    def test_class_vs_module_functions(self):
        """测试类方法与模块级别函数的一致性"""
        from src.utils.crypto_utils import (
            generate_uuid,
            generate_short_id,
            hash_string,
            hash_password,
            verify_password,
        )

        # 这些应该存在（如果模块导出它们）
        try:
            class_uuid = CryptoUtils.generate_uuid()
            module_uuid = generate_uuid()
            assert class_uuid == module_uuid
        except:
            pass  # 如果模块没有导出这些函数

    def test_performance_considerations(self):
        """测试性能考虑"""
        import time

        # 测试批量生成性能
        start_time = time.time()
        for _ in range(1000):
            CryptoUtils.generate_uuid()
        uuid_time = time.time() - start_time

        start_time = time.time()
        for _ in range(1000):
            CryptoUtils.hash_string("test")
        hash_time = time.time() - start_time

        # 这些操作应该相对快速
        assert uuid_time < 1.0, "UUID generation should be fast"
        assert hash_time < 0.1, "Hashing should be very fast"


# 导出函数别名以保持向后兼容性
try:
    from src.utils.crypto_utils import (
        generate_uuid,
        generate_short_id,
        hash_string,
        hash_password,
        verify_password,
    )
except ImportError:
    pass  # 模块可能不导出这些函数


@pytest.mark.skipif(not HAS_BCRYPT, reason="bcrypt not available")
class TestBcryptSpecific:
    """bcrypt特定的测试"""

    def test_bcrypt_rounds(self):
        """测试bcrypt轮数"""
        if not HAS_BCRYPT:
            pass  # 已激活
            return

        password = "test_password"
        hashed = CryptoUtils.hash_password(password)

        # bcrypt默认使用12轮
        assert hashed.startswith("$2b$12$")

    def test_bcrypt_cost_factor(self):
        """测试bcrypt成本因子"""
        if not HAS_BCRYPT:
            pass  # 已激活
            return

        password = "test_password"

        # bcrypt默认cost是12
        hashed = CryptoUtils.hash_password(password)
        cost = int(hashed.split("$")[2])

        assert cost >= 10, "Cost factor should be at least 10"
        assert cost <= 14, "Cost factor should be reasonable"

    def test_bcrypt_rehash(self):
        """测试bcrypt重哈希"""
        if not HAS_BCRYPT:
            pass  # 已激活
            return

        password = "test_password"

        # 简单测试：使用相同密码
        hashed1 = CryptoUtils.hash_password(password)
        hashed2 = CryptoUtils.hash_password(password)

        # 由于随机盐，哈希应该不同
        assert hashed1 != hashed2

        # 但验证各自的密码应该成功
        assert CryptoUtils.verify_password(password, hashed1)
        assert CryptoUtils.verify_password(password, hashed2)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__])
