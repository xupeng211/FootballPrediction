import os
"""加密工具模块测试"""

import pytest
import re

from src.utils.crypto_utils import CryptoUtils, HAS_BCRYPT


class TestCryptoUtils:
    """测试加密工具类"""

    def test_generate_uuid(self):
        """测试生成UUID"""
        uuid1 = CryptoUtils.generate_uuid()
        uuid2 = CryptoUtils.generate_uuid()

        # 验证UUID格式
        assert isinstance(uuid1, str)
        assert len(uuid1) == 36
        assert uuid1.count("-") == 4

        # 验证UUID4的格式（版本应为4）
        assert uuid1[14] == "4"
        assert uuid1[19] in {"8", "9", "a", "b"}

        # 验证两个UUID不同
        assert uuid1 != uuid2

        # 验证正则表达式匹配
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, uuid1) is not None

    def test_generate_short_id(self):
        """测试生成短ID"""
        # 测试默认长度
        short_id = CryptoUtils.generate_short_id()
        assert isinstance(short_id, str)
        assert len(short_id) == 8

        # 测试自定义长度
        short_id_4 = CryptoUtils.generate_short_id(4)
        assert len(short_id_4) == 4

        short_id_16 = CryptoUtils.generate_short_id(16)
        assert len(short_id_16) == 16

        # 测试长度为32（一个UUID去掉连字符的长度）
        short_id_32 = CryptoUtils.generate_short_id(32)
        assert len(short_id_32) == 32

        # 测试大于32的长度
        short_id_40 = CryptoUtils.generate_short_id(40)
        assert len(short_id_40) == 40

        # 测试零长度
        assert CryptoUtils.generate_short_id(0) == ""

        # 测试负长度
        assert CryptoUtils.generate_short_id(-1) == ""

    def test_generate_short_id_uniqueness(self):
        """测试短ID的唯一性"""
        ids = set()
        for _ in range(100):
            short_id = CryptoUtils.generate_short_id(8)
            ids.add(short_id)

        # 100个8字符的ID应该大部分都是唯一的
        assert len(ids) > 90  # 允许少量重复（概率很小）

    def test_hash_string_md5(self):
        """测试MD5哈希"""
        text = os.getenv("TEST_CRYPTO_UTILS_TEXT_73")
        hashed = CryptoUtils.hash_string(text, "md5")

        assert isinstance(hashed, str)
        assert len(hashed) == 32  # MD5哈希长度

        # 验证相同的输入产生相同的输出
        hashed2 = CryptoUtils.hash_string(text, "md5")
        assert hashed == hashed2

        # 验证不同输入产生不同输出
        different = CryptoUtils.hash_string("different string", "md5")
        assert hashed != different

        # 验证已知值的哈希
        assert CryptoUtils.hash_string("", "md5") == "d41d8cd98f00b204e9800998ecf8427e"
        assert CryptoUtils.hash_string("hello", "md5") == "5d41402abc4b2a76b9719d911017c592"

    def test_hash_string_sha256(self):
        """测试SHA256哈希"""
        text = os.getenv("TEST_CRYPTO_UTILS_TEXT_73")
        hashed = CryptoUtils.hash_string(text, "sha256")

        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA256哈希长度

        # 验证相同的输入产生相同的输出
        hashed2 = CryptoUtils.hash_string(text, "sha256")
        assert hashed == hashed2

        # 验证不同输入产生不同输出
        different = CryptoUtils.hash_string("different string", "sha256")
        assert hashed != different

    def test_hash_string_invalid_algorithm(self):
        """测试无效的哈希算法"""
        with pytest.raises(ValueError, match = os.getenv("TEST_CRYPTO_UTILS_MATCH_108")):
            CryptoUtils.hash_string("test", "invalid")

        with pytest.raises(ValueError, match = os.getenv("TEST_CRYPTO_UTILS_MATCH_108")):
            CryptoUtils.hash_string("test", "sha1")

    def test_hash_password(self):
        """测试密码哈希"""
        password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_113")

        # 测试哈希密码
        hashed = CryptoUtils.hash_password(password)

        assert isinstance(hashed, str)
        assert hashed != password  # 哈希后的密码不应该等于原密码
        assert len(hashed) > 50  # 哈希后的密码应该足够长

        # 验证bcrypt格式（如果可用）或模拟格式
        assert hashed.startswith("$2b$12$")

        # 相同的密码应该产生不同的哈希（因为有随机盐）
        hashed2 = CryptoUtils.hash_password(password)
        assert hashed != hashed2

    def test_hash_password_with_salt(self):
        """测试带盐的密码哈希"""
        password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_130")
        salt = os.getenv("TEST_CRYPTO_UTILS_SALT_131")

        hashed = CryptoUtils.hash_password(password, salt)

        assert isinstance(hashed, str)
        assert salt in hashed  # 盐应该包含在哈希中

    def test_verify_password_success(self):
        """测试密码验证成功"""
        password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_138")

        # 生成哈希
        hashed = CryptoUtils.hash_password(password)

        # 验证密码
        assert CryptoUtils.verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """测试密码验证失败"""
        password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_138")
        wrong_password = os.getenv("TEST_CRYPTO_UTILS_WRONG_PASSWORD_148")

        # 生成哈希
        hashed = CryptoUtils.hash_password(password)

        # 验证错误的密码
        assert CryptoUtils.verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """测试空密码验证"""
        # 空密码和空哈希
        assert CryptoUtils.verify_password("", "") is True

        # 空密码和非空哈希
        hashed = CryptoUtils.hash_password("password")
        assert CryptoUtils.verify_password("", hashed) is False

    def test_verify_password_invalid_format(self):
        """测试验证无效格式的哈希"""
        # 不是bcrypt格式的哈希
        invalid_hash = os.getenv("TEST_CRYPTO_UTILS_INVALID_HASH_167")

        assert CryptoUtils.verify_password("password", invalid_hash) is False

    def test_generate_salt(self):
        """测试生成盐值"""
        # 测试默认长度
        salt = CryptoUtils.generate_salt()
        assert isinstance(salt, str)
        assert len(salt) == 32  # 16字节 = 32个十六进制字符

        # 测试自定义长度
        salt_8 = CryptoUtils.generate_salt(8)
        assert len(salt_8) == 16  # 8字节 = 16个十六进制字符

        # 验证盐值是十六进制字符串
        try:
            int(salt, 16)
        except ValueError:
            pytest.fail("盐值应该是有效的十六进制字符串")

        # 验证生成的盐值是唯一的
        salt1 = CryptoUtils.generate_salt()
        salt2 = CryptoUtils.generate_salt()
        assert salt1 != salt2

    def test_generate_token(self):
        """测试生成令牌"""
        # 测试默认长度
        token = CryptoUtils.generate_token()
        assert isinstance(token, str)
        assert len(token) == 64  # 32字节 = 64个十六进制字符

        # 测试自定义长度
        token_16 = CryptoUtils.generate_token(16)
        assert len(token_16) == 32  # 16字节 = 32个十六进制字符

        # 验证令牌是十六进制字符串
        try:
            int(token, 16)
        except ValueError:
            pytest.fail("令牌应该是有效的十六进制字符串")

        # 验证生成的令牌是唯一的
        token1 = CryptoUtils.generate_token()
        token2 = CryptoUtils.generate_token()
        assert token1 != token2

    def test_password_hashing_consistency(self):
        """测试密码哈希的一致性"""
        password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_215")

        # 生成多个哈希
        hashes = [CryptoUtils.hash_password(password) for _ in range(5)]

        # 所有哈希都应该能够验证原密码
        for hashed in hashes:
            assert CryptoUtils.verify_password(password, hashed) is True

        # 所有哈希应该互不相同（因为有随机盐）
        assert len(set(hashes)) == len(hashes)

    def test_unicode_passwords(self):
        """测试Unicode密码"""
        unicode_password = os.getenv("TEST_CRYPTO_UTILS_UNICODE_PASSWORD_229")

        # 哈希Unicode密码
        hashed = CryptoUtils.hash_password(unicode_password)

        # 验证Unicode密码
        assert CryptoUtils.verify_password(unicode_password, hashed) is True

        # 验证错误的Unicode密码
        assert CryptoUtils.verify_password("错误的密码", hashed) is False

    def test_long_passwords(self):
        """测试长密码"""
        long_password = "a" * 1000

        # 哈希长密码
        hashed = CryptoUtils.hash_password(long_password)

        # 验证长密码
        assert CryptoUtils.verify_password(long_password, hashed) is True

    def test_short_id_character_distribution(self):
        """测试短ID的字符分布"""
        short_id = CryptoUtils.generate_short_id(1000)

        # 应该只包含小写字母和数字
        valid_chars = set("0123456789abcdef")
        assert all(c in valid_chars for c in short_id)

        # 应该包含数字和字母的混合
        assert any(c.isdigit() for c in short_id)
        assert any(c.isalpha() for c in short_id)

    def test_hash_case_sensitivity(self):
        """测试哈希的大小写敏感性"""
        text1 = "Hello"
        text2 = "hello"

        hash1 = CryptoUtils.hash_string(text1, "md5")
        hash2 = CryptoUtils.hash_string(text2, "md5")

        # 大小写不同的文本应该产生不同的哈希
        assert hash1 != hash2

    def test_hash_whitespace(self):
        """测试包含空格的文本哈希"""
        text1 = os.getenv("TEST_CRYPTO_UTILS_TEXT1_271")
        text2 = os.getenv("TEST_CRYPTO_UTILS_TEXT2_273")  # 双空格
        text3 = os.getenv("TEST_CRYPTO_UTILS_TEXT3_274")  # 尾部空格

        hash1 = CryptoUtils.hash_string(text1, "md5")
        hash2 = CryptoUtils.hash_string(text2, "md5")
        hash3 = CryptoUtils.hash_string(text3, "md5")

        # 空格不同的文本应该产生不同的哈希
        assert hash1 != hash2
        assert hash1 != hash3


class TestCryptoUtilsEdgeCases:
    """测试加密工具的边界情况"""

    def test_empty_string_hash(self):
        """测试空字符串哈希"""
        assert CryptoUtils.hash_string("", "md5") == "d41d8cd98f00b204e9800998ecf8427e"
        assert CryptoUtils.hash_string("", "sha256") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_single_character_hash(self):
        """测试单字符哈希"""
        assert len(CryptoUtils.hash_string("a", "md5")) == 32
        assert len(CryptoUtils.hash_string("a", "sha256")) == 64

    def test_very_long_string_hash(self):
        """测试非常长的字符串哈希"""
        long_text = "a" * 10000

        # 应该能处理长字符串
        assert len(CryptoUtils.hash_string(long_text, "md5")) == 32
        assert len(CryptoUtils.hash_string(long_text, "sha256")) == 64

    def test_special_characters_hash(self):
        """测试特殊字符哈希"""
        special_chars = os.getenv("TEST_CRYPTO_UTILS_SPECIAL_CHARS_309"):\",./<>?"

        # 应该能处理特殊字符
        assert len(CryptoUtils.hash_string(special_chars, "md5")) == 32
        assert len(CryptoUtils.hash_string(special_chars, "sha256")) == 64

    def test_newline_and_tab_hash(self):
        """测试换行符和制表符哈希"""
        text_with_newlines = os.getenv("TEST_CRYPTO_UTILS_TEXT_WITH_NEWLINES_317")
        text_with_tabs = os.getenv("TEST_CRYPTO_UTILS_TEXT_WITH_TABS_318")

        # 应该能处理换行符和制表符
        assert len(CryptoUtils.hash_string(text_with_newlines, "md5")) == 32
        assert len(CryptoUtils.hash_string(text_with_tabs, "md5")) == 32

    def test_maximum_short_id_length(self):
        """测试最大短ID长度"""
        # 测试非常大的长度
        very_long_id = CryptoUtils.generate_short_id(1000)
        assert len(very_long_id) == 1000

    def test_zero_length_token(self):
        """测试零长度令牌"""
        token = CryptoUtils.generate_token(0)
        assert token == ""

    def test_salt_length_edge_cases(self):
        """测试盐长度的边界情况"""
        # 测试长度为1
        salt_1 = CryptoUtils.generate_salt(1)
        assert len(salt_1) == 2

        # 测试长度为0
        salt_0 = CryptoUtils.generate_salt(0)
        assert salt_0 == ""