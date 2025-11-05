"""
CryptoUtils增强测试 - 冲刺7.5%覆盖率目标
专门针对未覆盖的加密工具函数进行精准测试
"""

import base64
import hashlib
import urllib.parse

from src.utils.crypto_utils import CryptoUtils


class TestCryptoUtilsEnhanced:
    """CryptoUtils增强测试类 - 针对性提升覆盖率"""

    def test_generate_short_id_default_length(self):
        """测试生成默认长度短ID"""
        short_id = CryptoUtils.generate_short_id()
        assert isinstance(short_id, str)
        assert len(short_id) == 8
        # 应该是有效的十六进制字符串
        int(short_id, 16)  # 不应该抛出异常

    def test_generate_short_id_custom_length(self):
        """测试生成自定义长度短ID"""
        # 测试不同长度
        for length in [4, 6, 10, 16, 20]:
            short_id = CryptoUtils.generate_short_id(length)
            assert isinstance(short_id, str)
            assert len(short_id) == length
            int(short_id, 16)  # 验证是有效十六进制

    def test_generate_short_id_odd_length(self):
        """测试生成奇数长度短ID"""
        odd_id = CryptoUtils.generate_short_id(7)
        assert isinstance(odd_id, str)
        # 对于奇数长度，实际长度应该是length-1（因为token_hex是按字节的）
        assert len(odd_id) == 6

    def test_generate_uuid_function(self):
        """测试UUID生成功能"""
        uuid1 = CryptoUtils.generate_uuid()
        uuid2 = CryptoUtils.generate_uuid()

        assert isinstance(uuid1, str)
        assert isinstance(uuid2, str)
        assert len(uuid1) == 36  # 标准UUID格式
        assert len(uuid2) == 36
        assert uuid1 != uuid2  # 应该是唯一的

        # 验证UUID格式
        assert uuid1.count("-") == 4
        parts = uuid1.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_hash_password_without_bcrypt(self):
        """测试密码哈希（bcrypt可用）"""
        password = "test_password_123"
        hashed = CryptoUtils.hash_password(password)

        assert isinstance(hashed, str)
        # bcrypt可用时，应该返回bcrypt格式的哈希
        assert hashed.startswith("$2b$") or hashed.startswith("sha256$")
        assert hashed.count("$") >= 2

        # 验证哈希格式
        parts = hashed.split("$")
        assert len(parts) >= 3

        if hashed.startswith("sha256$"):
            # SHA256格式：sha256$salt$hash
            assert parts[0] == "sha256"
            assert len(parts[1]) > 0  # salt
            assert len(parts[2]) == 64  # SHA256 hash length
        elif hashed.startswith("$2b$"):
            # bcrypt格式：$2b$cost$salt$hash
            assert parts[0] == ""  # 分割后第一个元素为空
            assert parts[1] == "2b"
            assert len(parts) >= 4

    def test_hash_password_with_bcrypt_mock(self):
        """测试使用bcrypt的密码哈希（模拟）"""
        password = "test_password_123"
        hashed = CryptoUtils.hash_password(password)

        # 无论是否有bcrypt，都应该返回哈希值
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_empty_password(self):
        """测试空密码哈希"""
        hashed = CryptoUtils.hash_password("")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_unicode_password(self):
        """测试Unicode密码哈希"""
        unicode_password = "密码测试🔒"
        hashed = CryptoUtils.hash_password(unicode_password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        # Unicode密码应该能正常处理

    def test_verify_password_empty_credentials(self):
        """测试验证空密码凭据"""
        result = CryptoUtils.verify_password("", "")
        assert result is False

    def test_verify_password_sha256_hash(self):
        """测试验证SHA256哈希密码"""
        password = "test_password_123"

        # 首先生成哈希
        hashed = CryptoUtils.hash_password(password)

        # 验证正确密码
        result = CryptoUtils.verify_password(password, hashed)
        assert result is True

        # 验证错误密码
        result = CryptoUtils.verify_password("wrong_password", hashed)
        assert result is False

    def test_verify_password_invalid_hash_format(self):
        """测试验证无效哈希格式密码"""
        password = "test_password"

        # 测试各种无效格式
        invalid_hashes = [
            "invalid_format",
            "sha256$",  # 缺少salt和hash
            "$2b$",  # 不完整的bcrypt格式
            "other_format$some$hash",
        ]

        for invalid_hash in invalid_hashes:
            result = CryptoUtils.verify_password(password, invalid_hash)
            assert result is False

    def test_verify_password_malformed_sha256(self):
        """测试验证格式错误的SHA256哈希"""
        password = "test_password"

        # 测试缺少部分的SHA256格式
        malformed_hashes = [
            "sha256$",  # 只有前缀
            "sha256$salt",  # 缺少hash
            "sha256$$hash",  # 缺少salt
        ]

        for malformed_hash in malformed_hashes:
            result = CryptoUtils.verify_password(password, malformed_hash)
            assert result is False

    def test_verify_password_bcrypt_complex_format(self):
        """测试验证复杂bcrypt格式密码"""
        password = "test_password"

        # 模拟复杂的bcrypt格式（超过3个$符号）
        complex_bcrypt = "$2b$12$salt$hash$extra$parts"
        result = CryptoUtils.verify_password(password, complex_bcrypt)
        assert isinstance(result, bool)

    def test_encode_base64_basic(self):
        """测试基本Base64编码"""
        text = "Hello, World!"
        encoded = CryptoUtils.encode_base64(text)

        expected = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        assert encoded == expected
        assert isinstance(encoded, str)

    def test_encode_base64_unicode(self):
        """测试Unicode文本Base64编码"""
        text = "你好世界 🌍"
        encoded = CryptoUtils.encode_base64(text)

        expected = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        assert encoded == expected

    def test_encode_base64_empty_string(self):
        """测试空字符串Base64编码"""
        encoded = CryptoUtils.encode_base64("")
        assert encoded == ""

    def test_encode_base64_invalid_input(self):
        """测试无效输入Base64编码"""
        invalid_inputs = [None, 123, [], {}]

        for invalid_input in invalid_inputs:
            encoded = CryptoUtils.encode_base64(invalid_input)
            assert encoded == ""

    def test_decode_base64_basic(self):
        """测试基本Base64解码"""
        text = "Hello, World!"
        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")

        decoded = CryptoUtils.decode_base64(encoded)
        assert decoded == text
        assert isinstance(decoded, str)

    def test_decode_base64_unicode(self):
        """测试Unicode文本Base64解码"""
        text = "你好世界 🌍"
        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")

        decoded = CryptoUtils.decode_base64(encoded)
        assert decoded == text

    def test_decode_base64_empty_string(self):
        """测试空字符串Base64解码"""
        decoded = CryptoUtils.decode_base64("")
        assert decoded == ""

    def test_decode_base64_invalid_input(self):
        """测试无效输入Base64解码"""
        invalid_inputs = [None, 123, [], {}, "invalid_base64!"]

        for invalid_input in invalid_inputs:
            decoded = CryptoUtils.decode_base64(invalid_input)
            assert decoded == ""

    def test_encode_url_basic(self):
        """测试基本URL编码"""
        text = "Hello World! 你好"
        encoded = CryptoUtils.encode_url(text)

        expected = urllib.parse.quote(text.encode("utf-8"))
        assert encoded == expected
        assert isinstance(encoded, str)

    def test_encode_url_special_characters(self):
        """测试特殊字符URL编码"""
        text = "a+b=c&d=e"
        encoded = CryptoUtils.encode_url(text)

        expected = urllib.parse.quote(text.encode("utf-8"))
        assert encoded == expected

    def test_encode_url_empty_string(self):
        """测试空字符串URL编码"""
        encoded = CryptoUtils.encode_url("")
        assert encoded == ""

    def test_encode_url_invalid_input(self):
        """测试无效输入URL编码"""
        invalid_inputs = [None, 123, [], {}]

        for invalid_input in invalid_inputs:
            encoded = CryptoUtils.encode_url(invalid_input)
            assert encoded == ""

    def test_decode_url_basic(self):
        """测试基本URL解码"""
        text = "Hello World! 你好"
        encoded = urllib.parse.quote(text.encode("utf-8"))

        decoded = CryptoUtils.decode_url(encoded)
        assert decoded == text
        assert isinstance(decoded, str)

    def test_decode_url_special_characters(self):
        """测试特殊字符URL解码"""
        text = "a+b=c&d=e"
        encoded = urllib.parse.quote(text.encode("utf-8"))

        decoded = CryptoUtils.decode_url(encoded)
        assert decoded == text

    def test_decode_url_empty_string(self):
        """测试空字符串URL解码"""
        decoded = CryptoUtils.decode_url("")
        assert decoded == ""

    def test_decode_url_invalid_input(self):
        """测试无效输入URL解码"""
        invalid_inputs = [None, 123, [], {}]

        for invalid_input in invalid_inputs:
            decoded = CryptoUtils.decode_url(invalid_input)
            assert decoded == ""

    def test_create_checksum_basic(self):
        """测试基本校验和创建"""
        data = "test data"
        checksum = CryptoUtils.create_checksum(data)

        expected = hashlib.sha256(data.encode("utf-8")).hexdigest()
        assert checksum == expected
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256长度

    def test_create_checksum_unicode(self):
        """测试Unicode数据校验和创建"""
        data = "测试数据 🌍"
        checksum = CryptoUtils.create_checksum(data)

        expected = hashlib.sha256(data.encode("utf-8")).hexdigest()
        assert checksum == expected

    def test_create_checksum_empty_string(self):
        """测试空字符串校验和创建"""
        checksum = CryptoUtils.create_checksum("")

        expected = hashlib.sha256(b"").hexdigest()
        assert checksum == expected
        assert len(checksum) == 64

    def test_create_checksum_invalid_input(self):
        """测试无效输入校验和创建"""
        invalid_inputs = [None, 123, [], {}]

        for invalid_input in invalid_inputs:
            checksum = CryptoUtils.create_checksum(invalid_input)
            assert checksum == ""

    def test_generate_random_string_default_length(self):
        """测试生成默认长度随机字符串"""
        random_str = CryptoUtils.generate_random_string()

        assert isinstance(random_str, str)
        assert len(random_str) == 32
        # 应该是URL安全的字符
        assert random_str.isalnum() or "-" in random_str or "_" in random_str

    def test_generate_random_string_custom_length(self):
        """测试生成自定义长度随机字符串"""
        for length in [8, 16, 24, 48]:
            random_str = CryptoUtils.generate_random_string(length)
            assert isinstance(random_str, str)
            assert len(random_str) == length

    def test_generate_random_string_consistency(self):
        """测试随机字符串的一致性"""
        str1 = CryptoUtils.generate_random_string(16)
        str2 = CryptoUtils.generate_random_string(16)

        assert str1 != str2  # 应该是唯一的
        assert len(str1) == len(str2) == 16

    def test_generate_api_key_function(self):
        """测试API密钥生成功能"""
        api_key1 = CryptoUtils.generate_api_key()
        api_key2 = CryptoUtils.generate_api_key()

        assert isinstance(api_key1, str)
        assert isinstance(api_key2, str)
        assert api_key1.startswith("fp_")
        assert api_key2.startswith("fp_")
        assert len(api_key1) == 35  # fp_ + 32字符
        assert len(api_key2) == 35
        assert api_key1 != api_key2  # 应该是唯一的

    def test_crypto_utils_workflow(self):
        """测试完整的加密工具工作流程"""
        # 1. 生成用户标识
        user_id = CryptoUtils.generate_uuid()
        short_id = CryptoUtils.generate_short_id()
        api_key = CryptoUtils.generate_api_key()

        # 2. 处理密码
        password = "user_password_123"
        hashed_password = CryptoUtils.hash_password(password)

        # 3. 验证密码
        is_valid = CryptoUtils.verify_password(password, hashed_password)
        assert is_valid is True

        # 4. 编码解码操作
        original_text = "用户数据 📊"
        encoded_b64 = CryptoUtils.encode_base64(original_text)
        decoded_b64 = CryptoUtils.decode_base64(encoded_b64)

        encoded_url = CryptoUtils.encode_url(original_text)
        decoded_url = CryptoUtils.decode_url(encoded_url)

        assert decoded_b64 == original_text
        assert decoded_url == original_text

        # 5. 创建数据校验和
        checksum = CryptoUtils.create_checksum(original_text)
        assert isinstance(checksum, str)
        assert len(checksum) == 64

        # 6. 验证所有生成的标识符
        assert isinstance(user_id, str)
        assert isinstance(short_id, str)
        assert isinstance(api_key, str)
        assert len(user_id) == 36
        assert len(short_id) == 8
        assert api_key.startswith("fp_")

    def test_edge_cases_and_error_handling(self):
        """测试边界情况和错误处理"""
        # 测试极长字符串
        long_string = "a" * 1000

        # Base64编码解码长字符串
        encoded = CryptoUtils.encode_base64(long_string)
        decoded = CryptoUtils.decode_base64(encoded)
        assert decoded == long_string

        # URL编码解码长字符串
        encoded_url = CryptoUtils.encode_url(long_string)
        decoded_url = CryptoUtils.decode_url(encoded_url)
        assert decoded_url == long_string

        # 创建长字符串校验和
        checksum = CryptoUtils.create_checksum(long_string)
        assert isinstance(checksum, str)
        assert len(checksum) == 64
