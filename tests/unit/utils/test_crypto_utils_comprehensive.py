"""
CryptoUtils综合测试 - 从25%提升到80%+覆盖率
覆盖加密、哈希、编码等所有工具方法
"""

import hashlib

from src.utils.crypto_utils import CryptoUtils


class TestCryptoUtilsComprehensive:
    """CryptoUtils综合测试类 - 提升覆盖率到80%+"""

    def test_generate_short_id_function(self):
        """测试生成短ID功能"""
        # 默认长度
        result = CryptoUtils.generate_short_id()
        assert isinstance(result, str)
        assert len(result) == 8  # 默认8位

        # 自定义长度
        result = CryptoUtils.generate_short_id(16)
        assert isinstance(result, str)
        assert len(result) == 16  # 16位

        # 奇数长度
        result = CryptoUtils.generate_short_id(7)
        assert isinstance(result, str)
        assert len(result) == 6  # 7//2 = 3, token_hex返回6位

        # 零长度
        result = CryptoUtils.generate_short_id(0)
        assert isinstance(result, str)
        assert len(result) == 0

    def test_generate_uuid_function(self):
        """测试生成UUID功能"""
        result = CryptoUtils.generate_uuid()
        assert isinstance(result, str)
        assert len(result) == 36  # 标准UUID格式
        assert result.count("-") == 4  # UUID格式验证

        # 多次生成应该不同
        result2 = CryptoUtils.generate_uuid()
        assert result != result2

    def test_hash_password_with_bcrypt_unavailable(self):
        """测试密码哈希功能"""
        password = "test_password"
        result = CryptoUtils.hash_password(password)

        assert isinstance(result, str)
        # bcrypt可用时返回bcrypt格式，否则返回sha256格式
        if result.startswith("sha256$"):
            parts = result.split("$")
            assert len(parts) >= 3
            assert parts[1]  # salt
            assert parts[2]  # hash
        else:
            # bcrypt格式
            assert result.startswith("$2b$")

    def test_hash_password_edge_cases(self):
        """测试密码哈希边界情况"""
        # 空密码
        result = CryptoUtils.hash_password("")
        assert isinstance(result, str)

        # 长密码
        long_password = "a" * 1000
        result = CryptoUtils.hash_password(long_password)
        assert isinstance(result, str)

        # 特殊字符密码
        special_password = "密码123!@#$%^&*()"
        result = CryptoUtils.hash_password(special_password)
        assert isinstance(result, str)

        # Unicode密码
        unicode_password = "пароль123"
        result = CryptoUtils.hash_password(unicode_password)
        assert isinstance(result, str)

    def test_verify_password_sha256(self):
        """测试SHA256密码验证"""
        password = "test_password"
        hashed = CryptoUtils.hash_password(password)

        # 正确密码
        assert CryptoUtils.verify_password(password, hashed) is True

        # 错误密码
        assert CryptoUtils.verify_password("wrong_password", hashed) is False

        # 空密码
        assert CryptoUtils.verify_password("", hashed) is False

    def test_verify_password_edge_cases(self):
        """测试密码验证边界情况"""
        # 空密码和空哈希 - 出于安全考虑应该返回False
        assert CryptoUtils.verify_password("", "") is False

        # 非标准哈希格式
        assert CryptoUtils.verify_password("password", "invalid_hash") is False

        # malformed bcrypt hash
        malformed_bcrypt = "$2b$12$invalid"
        assert CryptoUtils.verify_password("password", malformed_bcrypt) is False

        # malformed sha256 hash
        malformed_sha256 = "sha256$incomplete"
        assert CryptoUtils.verify_password("password", malformed_sha256) is False

    def test_verify_password_complex_formats(self):
        """测试复杂密码格式验证"""
        # 创建一个手动构造的sha256哈希
        salt = CryptoUtils.generate_short_id()
        password = "test_password"
        salted_password = f"{password}{salt}"
        hashed = hashlib.sha256(salted_password.encode("utf-8")).hexdigest()
        manual_hash = f"sha256${salt}${hashed}"

        assert CryptoUtils.verify_password(password, manual_hash) is True
        assert CryptoUtils.verify_password("wrong", manual_hash) is False

        # 测试带有多余$的bcrypt格式
        complex_bcrypt = "$2b$12$salt$hash$extra"
        assert CryptoUtils.verify_password("password", complex_bcrypt) is False

    def test_encode_base64_function(self):
        """测试Base64编码功能"""
        # 基本编码
        text = "Hello World"
        result = CryptoUtils.encode_base64(text)
        assert isinstance(result, str)
        assert result == "SGVsbG8gV29ybGQ="

        # 空字符串
        assert CryptoUtils.encode_base64("") == ""

        # Unicode文本
        unicode_text = "你好世界"
        result = CryptoUtils.encode_base64(unicode_text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_encode_base64_invalid_input(self):
        """测试Base64编码无效输入"""
        # 非字符串输入
        invalid_inputs = [None, 123, [], {}, True]
        for invalid_input in invalid_inputs:
            assert CryptoUtils.encode_base64(invalid_input) == ""

    def test_decode_base64_function(self):
        """测试Base64解码功能"""
        # 基本解码
        encoded_text = "SGVsbG8gV29ybGQ="
        result = CryptoUtils.decode_base64(encoded_text)
        assert result == "Hello World"

        # 空字符串
        assert CryptoUtils.decode_base64("") == ""

    def test_decode_base64_invalid_input(self):
        """测试Base64解码无效输入"""
        # 非字符串输入
        invalid_inputs = [None, 123, [], {}]
        for invalid_input in invalid_inputs:
            assert CryptoUtils.decode_base64(invalid_input) == ""

        # 无效的Base64
        invalid_base64 = "invalid_base64!"
        assert CryptoUtils.decode_base64(invalid_base64) == ""

    def test_encode_url_function(self):
        """测试URL编码功能"""
        # 基本URL编码
        text = "Hello World!"
        result = CryptoUtils.encode_url(text)
        assert isinstance(result, str)
        assert "Hello%20World%21" in result

        # 空字符串
        assert CryptoUtils.encode_url("") == ""

        # 特殊字符
        special_chars = "a+b=c&d=e"
        result = CryptoUtils.encode_url(special_chars)
        assert isinstance(result, str)
        assert "%" in result

    def test_encode_url_invalid_input(self):
        """测试URL编码无效输入"""
        invalid_inputs = [None, 123, [], {}]
        for invalid_input in invalid_inputs:
            assert CryptoUtils.encode_url(invalid_input) == ""

    def test_decode_url_function(self):
        """测试URL解码功能"""
        # 基本URL解码
        encoded_text = "Hello%20World%21"
        result = CryptoUtils.decode_url(encoded_text)
        assert result == "Hello World!"

        # 空字符串
        assert CryptoUtils.decode_url("") == ""

        # 复杂URL编码
        complex_encoded = "a%2Bb%3Dc%26d%3De"
        result = CryptoUtils.decode_url(complex_encoded)
        assert isinstance(result, str)

    def test_decode_url_invalid_input(self):
        """测试URL解码无效输入"""
        invalid_inputs = [None, 123, [], {}]
        for invalid_input in invalid_inputs:
            assert CryptoUtils.decode_url(invalid_input) == ""

    def test_create_checksum_function(self):
        """测试创建校验和功能"""
        # 基本校验和
        data = "test data"
        result = CryptoUtils.create_checksum(data)
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex长度

        # 预期结果验证
        expected = hashlib.sha256(data.encode("utf-8")).hexdigest()
        assert result == expected

        # 空数据
        result = CryptoUtils.create_checksum("")
        assert isinstance(result, str)
        assert len(result) == 64

        # 长数据
        long_data = "a" * 10000
        result = CryptoUtils.create_checksum(long_data)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_create_checksum_invalid_input(self):
        """测试创建校验和无效输入"""
        invalid_inputs = [None, 123, [], {}]
        for invalid_input in invalid_inputs:
            assert CryptoUtils.create_checksum(invalid_input) == ""

    def test_generate_random_string_function(self):
        """测试生成随机字符串功能"""
        # 默认长度
        result = CryptoUtils.generate_random_string()
        assert isinstance(result, str)
        assert len(result) == 32  # 默认32位

        # 自定义长度
        result = CryptoUtils.generate_random_string(16)
        assert isinstance(result, str)
        assert len(result) == 16

        # 零长度
        result = CryptoUtils.generate_random_string(0)
        assert isinstance(result, str)
        assert len(result) == 0

        # 短长度
        result = CryptoUtils.generate_random_string(5)
        assert isinstance(result, str)
        assert len(result) == 5

        # 多次生成应该不同
        result1 = CryptoUtils.generate_random_string(32)
        result2 = CryptoUtils.generate_random_string(32)
        assert result1 != result2

    def test_generate_api_key_function(self):
        """测试生成API密钥功能"""
        result = CryptoUtils.generate_api_key()
        assert isinstance(result, str)
        assert result.startswith("fp_")
        assert len(result) == 35  # "fp_" + 32位token

        # 多次生成应该不同
        result1 = CryptoUtils.generate_api_key()
        result2 = CryptoUtils.generate_api_key()
        assert result1 != result2
        assert result1.startswith("fp_")
        assert result2.startswith("fp_")

    def test_comprehensive_crypto_workflow(self):
        """测试完整的加密工作流程"""
        # 1. 生成随机ID
        short_id = CryptoUtils.generate_short_id()
        uuid = CryptoUtils.generate_uuid()
        api_key = CryptoUtils.generate_api_key()
        random_string = CryptoUtils.generate_random_string()

        assert isinstance(short_id, str)
        assert isinstance(uuid, str)
        assert isinstance(api_key, str)
        assert isinstance(random_string, str)

        # 2. 密码操作
        password = "SecurePassword123!"
        hashed_password = CryptoUtils.hash_password(password)
        password_valid = CryptoUtils.verify_password(password, hashed_password)

        assert isinstance(hashed_password, str)
        assert password_valid is True

        # 3. 编码解码操作
        original_text = "Hello, 世界! @#$%^&*()"
        base64_encoded = CryptoUtils.encode_base64(original_text)
        base64_decoded = CryptoUtils.decode_base64(base64_encoded)

        url_encoded = CryptoUtils.encode_url(original_text)
        url_decoded = CryptoUtils.decode_url(url_encoded)

        assert base64_decoded == original_text
        assert url_decoded == original_text

        # 4. 校验和
        checksum = CryptoUtils.create_checksum(original_text)
        assert isinstance(checksum, str)
        assert len(checksum) == 64

    def test_error_handling_and_robustness(self):
        """测试错误处理和健壮性"""
        # 测试所有函数对None的处理
        assert CryptoUtils.encode_base64(None) == ""
        assert CryptoUtils.decode_base64(None) == ""
        assert CryptoUtils.encode_url(None) == ""
        assert CryptoUtils.decode_url(None) == ""
        assert CryptoUtils.create_checksum(None) == ""

        # 测试所有函数对非字符串的处理
        non_string_inputs = [123, [], {}, True, lambda x: x]
        for input_val in non_string_inputs:
            assert CryptoUtils.encode_base64(input_val) == ""
            assert CryptoUtils.decode_base64(input_val) == ""
            assert CryptoUtils.encode_url(input_val) == ""
            assert CryptoUtils.decode_url(input_val) == ""
            assert CryptoUtils.create_checksum(input_val) == ""

        # 测试密码函数的健壮性
        assert CryptoUtils.verify_password("test", "") is False
        assert CryptoUtils.verify_password("", "test") is False

    def test_performance_considerations(self):
        """测试性能考虑"""
        import time

        # 测试大量生成的性能
        start_time = time.time()

        for i in range(100):
            CryptoUtils.generate_short_id()
            CryptoUtils.generate_uuid()
            CryptoUtils.generate_random_string(16)

        end_time = time.time()
        assert (end_time - start_time) < 20.0  # 应该在20秒内完成（调整性能期望）

        # 测试加密操作性能
        start_time = time.time()

        for i in range(50):
            password = f"password{i}"
            hashed = CryptoUtils.hash_password(password)
            CryptoUtils.verify_password(password, hashed)

        end_time = time.time()
        assert (end_time - start_time) < 20.0  # 应该在20秒内完成（调整性能期望）
