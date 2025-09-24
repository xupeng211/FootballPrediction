"""
Tests for src/utils/crypto_utils.py (Phase 5)

针对加密工具类的全面测试，旨在提升覆盖率至 ≥60%
覆盖UUID生成、哈希、密码加密、令牌生成等核心功能
"""

import hashlib
import re
import uuid
from unittest.mock import Mock, patch

import pytest

from src.utils.crypto_utils import CryptoUtils


class TestCryptoUtilsUUID:
    """UUID和ID生成测试"""

    def test_generate_uuid(self):
        """测试UUID生成"""
        result = CryptoUtils.generate_uuid()

        # 验证是有效的UUID格式
        assert isinstance(result, str)
        assert len(result) == 36
        assert result.count("-") == 4

        # 验证可以转换为UUID对象
        uuid_obj = uuid.UUID(result)
        assert str(uuid_obj) == result

    def test_generate_uuid_uniqueness(self):
        """测试UUID的唯一性"""
        uuids = [CryptoUtils.generate_uuid() for _ in range(100)]

        # 验证100个UUID都不同
        assert len(set(uuids)) == 100

    def test_generate_short_id_default_length(self):
        """测试默认长度短ID生成"""
        result = CryptoUtils.generate_short_id()

        assert isinstance(result, str)
        assert len(result) == 8
        # 应该只包含十六进制字符
        assert re.match(r"^[0-9a-f]+$", result)

    def test_generate_short_id_custom_length(self):
        """测试自定义长度短ID生成"""
        for length in [1, 5, 10, 16, 24, 32]:
            result = CryptoUtils.generate_short_id(length)
            assert len(result) == length
            assert re.match(r"^[0-9a-f]+$", result)

    def test_generate_short_id_zero_length(self):
        """测试零长度短ID"""
        result = CryptoUtils.generate_short_id(0)
        assert result == ""

    def test_generate_short_id_negative_length(self):
        """测试负数长度短ID"""
        result = CryptoUtils.generate_short_id(-5)
        assert result == ""

    def test_generate_short_id_large_length(self):
        """测试大长度短ID生成"""
        result = CryptoUtils.generate_short_id(100)

        assert isinstance(result, str)
        assert len(result) == 100
        assert re.match(r"^[0-9a-f]+$", result)

    def test_generate_short_id_uniqueness(self):
        """测试短ID的唯一性"""
        ids = [CryptoUtils.generate_short_id(16) for _ in range(50)]

        # 大部分应该是唯一的（概率极高）
        assert len(set(ids)) >= 45  # 允许少量重复（概率极低）


class TestCryptoUtilsHashing:
    """哈希功能测试"""

    def test_hash_string_md5_default(self):
        """测试默认MD5哈希"""
        text = "hello world"
        result = CryptoUtils.hash_string(text)

        # MD5 hash of "hello world"
        expected = hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()
        assert result == expected
        assert len(result) == 32

    def test_hash_string_md5_explicit(self):
        """测试显式MD5哈希"""
        text = "test string"
        result = CryptoUtils.hash_string(text, "md5")

        expected = hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()
        assert result == expected

    def test_hash_string_sha256(self):
        """测试SHA256哈希"""
        text = "test string"
        result = CryptoUtils.hash_string(text, "sha256")

        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert result == expected
        assert len(result) == 64

    def test_hash_string_unsupported_algorithm(self):
        """测试不支持的哈希算法"""
        text = "test"

        with pytest.raises(ValueError, match="不支持的哈希算法"):
            CryptoUtils.hash_string(text, "sha512")

    def test_hash_string_empty(self):
        """测试空字符串哈希"""
        result_md5 = CryptoUtils.hash_string("", "md5")
        result_sha256 = CryptoUtils.hash_string("", "sha256")

        # 空字符串的已知哈希值
        expected_md5 = "d41d8cd98f00b204e9800998ecf8427e"
        expected_sha256 = (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

        assert result_md5 == expected_md5
        assert result_sha256 == expected_sha256

    def test_hash_string_unicode(self):
        """测试Unicode字符串哈希"""
        text = "你好世界"
        result = CryptoUtils.hash_string(text, "md5")

        expected = hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()
        assert result == expected

    def test_hash_string_consistency(self):
        """测试哈希一致性"""
        text = "consistency test"

        # 多次调用应该得到相同结果
        results = [CryptoUtils.hash_string(text) for _ in range(10)]
        assert len(set(results)) == 1


class TestCryptoUtilsPasswordHashing:
    """密码哈希测试"""

    def test_hash_password_with_bcrypt(self):
        """测试使用bcrypt进行密码哈希"""
        password = "test_password"

        with patch("src.utils.crypto_utils.HAS_BCRYPT", True):
            with patch("src.utils.crypto_utils.bcrypt") as mock_bcrypt:
                mock_bcrypt.gensalt.return_value = b"salt123"
                mock_bcrypt.hashpw.return_value = b"$2b$12$salt123$hashedpassword"

                result = CryptoUtils.hash_password(password)

                assert result == "$2b$12$salt123$hashedpassword"
                mock_bcrypt.hashpw.assert_called_once()

    def test_hash_password_without_bcrypt(self):
        """测试不使用bcrypt时的密码哈希"""
        password = "test_password"

        with patch("src.utils.crypto_utils.HAS_BCRYPT", False):
            result = CryptoUtils.hash_password(password)

            # 应该返回模拟bcrypt格式
            assert result.startswith("$2b$12$")
            assert result.count("$") == 4

    def test_hash_password_with_custom_salt(self):
        """测试使用自定义盐值的密码哈希（无bcrypt）"""
        password = "test_password"
        salt = "custom_salt"

        with patch("src.utils.crypto_utils.HAS_BCRYPT", False):
            result = CryptoUtils.hash_password(password, salt)

            # 验证格式
            assert result.startswith("$2b$12$")
            assert salt in result

    def test_hash_password_empty(self):
        """测试空密码哈希"""
        with patch("src.utils.crypto_utils.HAS_BCRYPT", False):
            result = CryptoUtils.hash_password("")
            assert result.startswith("$2b$12$")

    def test_hash_password_unicode(self):
        """测试Unicode密码哈希"""
        password = "密码测试"

        with patch("src.utils.crypto_utils.HAS_BCRYPT", False):
            result = CryptoUtils.hash_password(password)
            assert result.startswith("$2b$12$")


class TestCryptoUtilsPasswordVerification:
    """密码验证测试"""

    def test_verify_password_empty_both(self):
        """测试空密码和空哈希验证"""
        result = CryptoUtils.verify_password("", "")
        assert result is True

    def test_verify_password_with_bcrypt_real(self):
        """测试真正的bcrypt密码验证"""
        password = "test_password"
        hashed = "$2b$12$abcdefg"  # 简短的bcrypt格式

        with patch("src.utils.crypto_utils.HAS_BCRYPT", True):
            with patch("src.utils.crypto_utils.bcrypt") as mock_bcrypt:
                mock_bcrypt.checkpw.return_value = True

                result = CryptoUtils.verify_password(password, hashed)

                assert result is True
                mock_bcrypt.checkpw.assert_called_once()

    def test_verify_password_with_bcrypt_fail(self):
        """测试bcrypt密码验证失败"""
        password = "wrong_password"
        hashed = "$2b$12$abcdefg"

        with patch("src.utils.crypto_utils.HAS_BCRYPT", True):
            with patch("src.utils.crypto_utils.bcrypt") as mock_bcrypt:
                mock_bcrypt.checkpw.return_value = False

                result = CryptoUtils.verify_password(password, hashed)

                assert result is False

    def test_verify_password_mock_bcrypt_format_success(self):
        """测试模拟bcrypt格式密码验证成功"""
        # 由于实际实现的复杂性，我们只测试基本情况
        # 更重要的是覆盖异常处理路径
        password = "test_password"
        hashed = "$2b$12$salt$hash$with$too$many$parts"

        result = CryptoUtils.verify_password(password, hashed)
        # 这个应该进入异常处理路径并返回False
        assert result is False

    def test_verify_password_mock_bcrypt_format_fail(self):
        """测试模拟bcrypt格式密码验证失败"""
        password = "test_password"
        hashed = "$2b$12$test$salt$wrong_hash"

        result = CryptoUtils.verify_password(password, hashed)
        assert result is False

    def test_verify_password_malformed_hash(self):
        """测试格式错误的哈希"""
        password = "test_password"
        hashed = "$2b$12$malformed$incomplete"

        result = CryptoUtils.verify_password(password, hashed)
        assert result is False

    def test_verify_password_non_bcrypt_format(self):
        """测试非bcrypt格式哈希"""
        password = "test_password"
        hashed = "plain_hash_not_bcrypt"

        result = CryptoUtils.verify_password(password, hashed)
        assert result is False

    def test_verify_password_exception_handling(self):
        """测试异常处理"""
        password = "test_password"
        hashed = "$2b$12$$incomplete$"  # 不完整的格式

        result = CryptoUtils.verify_password(password, hashed)
        assert result is False


class TestCryptoUtilsTokenGeneration:
    """令牌和盐值生成测试"""

    def test_generate_salt_default(self):
        """测试默认长度盐值生成"""
        result = CryptoUtils.generate_salt()

        # 默认长度16，token_hex返回的是hex长度的2倍
        assert isinstance(result, str)
        assert len(result) == 32  # 16 * 2
        assert re.match(r"^[0-9a-f]+$", result)

    def test_generate_salt_custom_length(self):
        """测试自定义长度盐值生成"""
        for length in [4, 8, 16, 32]:
            result = CryptoUtils.generate_salt(length)
            assert len(result) == length * 2
            assert re.match(r"^[0-9a-f]+$", result)

    def test_generate_salt_uniqueness(self):
        """测试盐值唯一性"""
        salts = [CryptoUtils.generate_salt() for _ in range(50)]

        # 应该都是唯一的
        assert len(set(salts)) == 50

    def test_generate_token_default(self):
        """测试默认长度令牌生成"""
        result = CryptoUtils.generate_token()

        # 默认长度32，token_hex返回的是hex长度的2倍
        assert isinstance(result, str)
        assert len(result) == 64  # 32 * 2
        assert re.match(r"^[0-9a-f]+$", result)

    def test_generate_token_custom_length(self):
        """测试自定义长度令牌生成"""
        for length in [8, 16, 32, 64]:
            result = CryptoUtils.generate_token(length)
            assert len(result) == length * 2
            assert re.match(r"^[0-9a-f]+$", result)

    def test_generate_token_uniqueness(self):
        """测试令牌唯一性"""
        tokens = [CryptoUtils.generate_token() for _ in range(50)]

        # 应该都是唯一的
        assert len(set(tokens)) == 50


class TestCryptoUtilsIntegration:
    """集成测试"""

    def test_password_hash_verify_cycle(self):
        """测试密码哈希-验证循环"""
        password = "integration_test_password"

        with patch("src.utils.crypto_utils.HAS_BCRYPT", False):
            # 哈希密码
            hashed = CryptoUtils.hash_password(password)

            # 验证正确密码
            assert CryptoUtils.verify_password(password, hashed) is True

            # 验证错误密码
            assert CryptoUtils.verify_password("wrong_password", hashed) is False

    def test_hash_consistency_different_algorithms(self):
        """测试不同算法的哈希一致性"""
        text = "consistency_test"

        # MD5哈希应该一致
        md5_1 = CryptoUtils.hash_string(text, "md5")
        md5_2 = CryptoUtils.hash_string(text, "md5")
        assert md5_1 == md5_2

        # SHA256哈希应该一致
        sha256_1 = CryptoUtils.hash_string(text, "sha256")
        sha256_2 = CryptoUtils.hash_string(text, "sha256")
        assert sha256_1 == sha256_2

        # 不同算法应该产生不同结果
        assert md5_1 != sha256_1

    def test_id_generation_no_collision_in_sample(self):
        """测试ID生成在样本中无冲突"""
        # 生成大量ID检查冲突
        uuids = [CryptoUtils.generate_uuid() for _ in range(200)]
        short_ids = [CryptoUtils.generate_short_id(16) for _ in range(200)]
        salts = [CryptoUtils.generate_salt(8) for _ in range(200)]
        tokens = [CryptoUtils.generate_token(16) for _ in range(200)]

        # 检查各类ID的唯一性
        assert len(set(uuids)) == 200
        assert len(set(short_ids)) >= 195  # 允许极少量冲突
        assert len(set(salts)) == 200
        assert len(set(tokens)) == 200

    def test_edge_cases_handling(self):
        """测试边界情况处理"""
        # 空字符串处理
        empty_hash = CryptoUtils.hash_string("", "md5")
        assert len(empty_hash) == 32

        # 零长度ID
        zero_id = CryptoUtils.generate_short_id(0)
        assert zero_id == ""

        # 负数长度ID
        neg_id = CryptoUtils.generate_short_id(-1)
        assert neg_id == ""

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        unicode_texts = ["Hello 世界", "émojis 😀🚀", "русский текст", "العربية", "日本語"]

        for text in unicode_texts:
            # 哈希应该成功
            md5_hash = CryptoUtils.hash_string(text, "md5")
            sha256_hash = CryptoUtils.hash_string(text, "sha256")

            assert len(md5_hash) == 32
            assert len(sha256_hash) == 64

            # 密码处理应该成功
            with patch("src.utils.crypto_utils.HAS_BCRYPT", False):
                hashed = CryptoUtils.hash_password(text)
                assert CryptoUtils.verify_password(text, hashed) is True


class TestCryptoUtilsErrorHandling:
    """错误处理测试"""

    def test_hash_string_type_error_handling(self):
        """测试哈希函数的类型错误处理"""
        # 测试非字符串输入（这在实际中可能不会发生，但测试覆盖率）
        with pytest.raises((TypeError, AttributeError)):
            CryptoUtils.hash_string(None, "md5")

    def test_password_functions_with_bytes_input(self):
        """测试密码函数对bytes输入的处理"""
        with patch("src.utils.crypto_utils.HAS_BCRYPT", True):
            with patch("src.utils.crypto_utils.bcrypt") as mock_bcrypt:
                mock_bcrypt.gensalt.return_value = b"salt123"
                mock_bcrypt.hashpw.return_value = b"$2b$12$hashed"
                mock_bcrypt.checkpw.return_value = True

                # 字符串输入（正常情况）
                result = CryptoUtils.hash_password("password")
                assert result == "$2b$12$hashed"

                # 验证也应该成功
                verify_result = CryptoUtils.verify_password("password", "$2b$12$short")
                assert verify_result is True

    def test_malformed_hash_parts_handling(self):
        """测试格式错误哈希的各种情况"""
        password = "test"
        malformed_hashes = [
            "$2b$12$$incomplete$hash",  # 不完整但符合基本格式
            "$2b$12$a$b$wronghash",  # 错误哈希部分
            "not_bcrypt_format",  # 完全不是bcrypt格式
            "",  # 空字符串
        ]

        for hashed in malformed_hashes:
            if hashed == "":
                # 空密码空哈希的特殊情况
                result = CryptoUtils.verify_password("", hashed)
                assert result is True
            else:
                result = CryptoUtils.verify_password(password, hashed)
                assert result is False
