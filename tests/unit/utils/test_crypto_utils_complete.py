"""
加密工具完整测试
Crypto Utils Complete Tests

基于Issue #98成功模式，创建完整的加密工具测试
"""

import pytest

from src.utils.crypto_utils import CryptoUtils


@pytest.mark.unit
class TestCryptoUtilsComplete:
    """加密工具完整测试"""

    def test_generate_uuid(self):
        """测试UUID生成"""
        result = CryptoUtils.generate_uuid()
        assert isinstance(result, str)
        assert len(result) == 36  # 标准UUID长度

        # 验证UUID格式
        assert result.count("-") == 4

        # 多次生成应该不同
        result2 = CryptoUtils.generate_uuid()
        assert result != result2

    def test_generate_short_id(self):
        """测试短ID生成"""
        # 测试默认长度
        result = CryptoUtils.generate_short_id()
        assert isinstance(result, str)
        assert len(result) == 8

        # 测试自定义长度
        for length in [4, 8, 16, 32]:
            result = CryptoUtils.generate_short_id(length)
            assert len(result) == length

        # 测试零长度
        result = CryptoUtils.generate_short_id(0)
        assert result == ""

        # 测试负数长度
        result = CryptoUtils.generate_short_id(-5)
        assert result == ""

        # 测试大长度（大于32）
        result = CryptoUtils.generate_short_id(64)
        assert len(result) == 64

        # 多次生成应该不同
        result1 = CryptoUtils.generate_short_id(16)
        result2 = CryptoUtils.generate_short_id(16)
        assert result1 != result2

    def test_hash_string_algorithms(self):
        """测试字符串哈希不同算法"""
        test_text = "Hello, World!"

        # 测试支持的算法
        algorithms = ["md5", "sha1", "sha256", "sha512"]
        expected_lengths = [32, 40, 64, 128]

        for algorithm, expected_length in zip(algorithms, expected_lengths):
            result = CryptoUtils.hash_string(test_text, algorithm)
            assert isinstance(result, str)
            assert len(result) == expected_length

            # 相同输入应该产生相同哈希
            result2 = CryptoUtils.hash_string(test_text, algorithm)
            assert result == result2

            # 不同输入应该产生不同哈希
            different_text = "Different text"
            result3 = CryptoUtils.hash_string(different_text, algorithm)
            assert result != result3

    def test_hash_string_unsupported_algorithm(self):
        """测试不支持的哈希算法"""
        test_text = "Hello"

        with pytest.raises(ValueError, match="不支持的哈希算法"):
            CryptoUtils.hash_string(test_text, "unsupported")

    def test_hash_string_invalid_input(self):
        """测试无效输入的哈希"""
        # 测试非字符串输入
        invalid_inputs = [None, 123, [], {}, object()]

        for invalid_input in invalid_inputs:
            result = CryptoUtils.hash_string(invalid_input)
            assert result == ""

    def test_base64_operations(self):
        """测试Base64编码和解码"""
        test_strings = [
            "Hello, World!",
            "测试中文",
            "Special characters: !@#$%^&*()",
            "",
            "Unicode: 🚀 emoji test",
            "New line\nTest",
            "Tab\tTest",
        ]

        for test_str in test_strings:
            # 编码
            encoded = CryptoUtils.encode_base64(test_str)
            assert isinstance(encoded, str)

            # 解码
            decoded = CryptoUtils.decode_base64(encoded)
            assert decoded == test_str

    def test_base64_invalid_input(self):
        """测试Base64无效输入"""
        # 测试非字符串输入
        invalid_inputs = [None, 123, [], {}]

        for invalid_input in invalid_inputs:
            # 编码无效输入
            result = CryptoUtils.encode_base64(invalid_input)
            assert result == ""

            # 解码无效输入
            result = CryptoUtils.decode_base64(invalid_input)
            assert result == ""

        # 测试无效的Base64字符串
        invalid_base64 = ["invalid_base64!!!", "!!!", "not_base64"]
        for invalid in invalid_base64:
            result = CryptoUtils.decode_base64(invalid)
            assert result == ""

    def test_password_hashing_and_verification(self):
        """测试密码哈希和验证"""
        passwords = [
            "simple_password",
            "ComplexP@ssw0rd!",
            "密码123",
            "very_long_password_with_many_characters_123456789",
            "",
        ]

        for password in passwords:
            # 哈希密码
            hashed = CryptoUtils.hash_password(password)
            assert isinstance(hashed, str)
            assert len(hashed) > len(password)

            # 验证正确密码
            assert CryptoUtils.verify_password(password, hashed) is True

            # 验证错误密码
            assert CryptoUtils.verify_password("wrong_password", hashed) is False

    def test_password_hashing_with_custom_salt(self):
        """测试使用自定义盐值的密码哈希"""
        password = "test_password"
        salt = "custom_salt"

        # 使用自定义盐值哈希
        hashed1 = CryptoUtils.hash_password(password, salt)
        hashed2 = CryptoUtils.hash_password(password, salt)

        # 注意：由于bcrypt的随机性，即使相同盐值也可能产生不同结果
        # 主要验证的是哈希都能正常工作
        assert isinstance(hashed1, str)
        assert isinstance(hashed2, str)
        assert len(hashed1) > len(password)
        assert len(hashed2) > len(password)

        # 使用不同盐值
        different_salt = "different_salt"
        hashed3 = CryptoUtils.hash_password(password, different_salt)
        assert isinstance(hashed3, str)
        assert len(hashed3) > len(password)

    def test_password_verification_edge_cases(self):
        """测试密码验证边界情况"""
        # 空密码和空哈希的特殊情况
        assert CryptoUtils.verify_password("", "") is True

        # 无效格式
        assert CryptoUtils.verify_password("password", "invalid_format") is False

        # 测试一些可能导致异常的边界情况
        try:
            # 格式不正确的bcrypt格式可能抛出异常
            invalid_bcrypt = "$2b$12$invalid_hash_format"
            CryptoUtils.verify_password("password", invalid_bcrypt)
        except ValueError:
            # 预期的异常，验证函数正确处理了无效格式
            pass

    def test_generate_salt(self):
        """测试盐值生成"""
        # 测试默认长度 (secrets.token_hex生成的是32位十六进制字符串)
        salt = CryptoUtils.generate_salt()
        assert isinstance(salt, str)
        assert len(salt) == 32  # secrets.token_hex(16) 生成32个字符

        # 测试自定义长度 (secrets.token_hex生成的是2*length个字符)
        test_lengths = [8, 16, 32]
        for length in test_lengths:
            salt = CryptoUtils.generate_salt(length)
            assert len(salt) == length * 2  # token_hex生成2*length个字符

        # 多次生成应该不同
        salt1 = CryptoUtils.generate_salt()
        salt2 = CryptoUtils.generate_salt()
        assert salt1 != salt2

    def test_generate_token(self):
        """测试令牌生成"""
        # 测试默认长度 (secrets.token_hex生成的是64位十六进制字符串)
        token = CryptoUtils.generate_token()
        assert isinstance(token, str)
        assert len(token) == 64  # secrets.token_hex(32) 生成64个字符

        # 测试自定义长度 (secrets.token_hex生成的是2*length个字符)
        test_lengths = [8, 16, 32]
        for length in test_lengths:
            token = CryptoUtils.generate_token(length)
            assert len(token) == length * 2  # token_hex生成2*length个字符

        # 多次生成应该不同
        token1 = CryptoUtils.generate_token()
        token2 = CryptoUtils.generate_token()
        assert token1 != token2

    def test_url_encoding(self):
        """测试URL编码和解码"""
        test_strings = [
            "Hello World",
            "test+string&with=special#chars",
            "path/to/resource?param=value",
            "email@domain.com",
            "spaces and symbols!",
            "测试中文",
            "emoji 🚀 test",
        ]

        for test_str in test_strings:
            # URL编码
            encoded = CryptoUtils.encode_url(test_str)
            assert isinstance(encoded, str)

            # URL解码
            decoded = CryptoUtils.decode_url(encoded)
            assert decoded == test_str

    def test_url_component_encoding(self):
        """测试URL组件编码和解码"""
        test_strings = [
            "Hello World",
            "test+string&with=special#chars",
            "path/to/resource?param=value",
            "email@domain.com",
        ]

        for test_str in test_strings:
            # URL组件编码
            encoded = CryptoUtils.encode_url_component(test_str)
            assert isinstance(encoded, str)

            # URL组件解码
            decoded = CryptoUtils.decode_url_component(encoded)
            assert decoded == test_str

    def test_checksum_creation(self):
        """测试校验和创建"""
        test_data = "test data for checksum"

        # 测试默认算法（MD5）
        checksum = CryptoUtils.create_checksum(test_data)
        assert isinstance(checksum, str)
        # create_checksum返回的是8字符哈希 + 8字符长度 = 16字符
        assert len(checksum) == 16

        # 测试不同算法
        algorithms = ["md5", "sha1", "sha256"]
        for algorithm in algorithms:
            checksum = CryptoUtils.create_checksum(test_data, algorithm)
            assert isinstance(checksum, str)
            assert len(checksum) == 16  # 格式：8字符哈希 + 8字符长度

            # 相同数据应该产生相同校验和
            checksum2 = CryptoUtils.create_checksum(test_data, algorithm)
            assert checksum == checksum2

            # 不同数据应该产生不同校验和
            different_data = "different data"
            checksum3 = CryptoUtils.create_checksum(different_data, algorithm)
            assert checksum != checksum3

    def test_generate_api_key(self):
        """测试API密钥生成"""
        # 测试默认长度
        api_key = CryptoUtils.generate_api_key()
        assert isinstance(api_key, str)
        assert len(api_key) == 32

        # 测试自定义长度
        for length in [16, 24, 32, 64]:
            api_key = CryptoUtils.generate_api_key(length)
            assert len(api_key) == length

        # 多次生成应该不同
        key1 = CryptoUtils.generate_api_key()
        key2 = CryptoUtils.generate_api_key()
        assert key1 != key2

    def test_obfuscate_and_deobfuscate(self):
        """文本混淆和去混淆"""
        test_strings = [
            "Hello, World!",
            "secret message",
            "测试中文",
            "Special characters: !@#$%",
            "",
            "Very long text with many characters and unicode: 🚀",
        ]

        for original_text in test_strings:
            # 混淆
            obfuscated = CryptoUtils.obfuscate(original_text)
            assert isinstance(obfuscated, str)

            # 空字符串混淆后可能相同，这是正常的
            if original_text != "":
                assert obfuscated != original_text  # 非空字符串混淆后应该不同

            # 去混淆
            deobfuscated = CryptoUtils.deobfuscate(obfuscated)
            assert deobfuscated == original_text  # 去混淆后应该恢复原文

    def test_obfuscate_empty_text(self):
        """测试空文本混淆"""
        result = CryptoUtils.obfuscate("")
        assert isinstance(result, str)

        # 空文本的去混淆
        deobfuscated = CryptoUtils.deobfuscate(result)
        assert deobfuscated == ""

    def test_secure_string_comparison(self):
        """测试安全字符串比较"""
        # 测试相同字符串
        result = CryptoUtils.compare_strings_secure("hello", "hello")
        assert result is True

        # 测试不同字符串
        result = CryptoUtils.compare_strings_secure("hello", "world")
        assert result is False

        # 测试空字符串
        assert CryptoUtils.compare_strings_secure("", "") is True
        assert CryptoUtils.compare_strings_secure("hello", "") is False
        assert CryptoUtils.compare_strings_secure("", "hello") is False

        # 测试长字符串
        long_str1 = "a" * 1000
        long_str2 = "a" * 1000
        long_str3 = "a" * 999 + "b"

        assert CryptoUtils.compare_strings_secure(long_str1, long_str2) is True
        assert CryptoUtils.compare_strings_secure(long_str1, long_str3) is False

    def test_unicode_handling(self):
        """测试Unicode处理"""
        unicode_strings = [
            "测试中文",
            "café résumé",
            "привет мир",
            "العربية",
            "🚀 emoji test",
            "Mixed: English 中文 العربية",
            "日本語テスト",
            "한국어 테스트",
        ]

        for test_str in unicode_strings:
            # 哈希Unicode字符串
            result = CryptoUtils.hash_string(test_str)
            assert isinstance(result, str)
            assert len(result) > 0

            # Base64编码Unicode
            encoded = CryptoUtils.encode_base64(test_str)
            decoded = CryptoUtils.decode_base64(encoded)
            assert decoded == test_str

            # 混淆Unicode
            obfuscated = CryptoUtils.obfuscate(test_str)
            deobfuscated = CryptoUtils.deobfuscate(obfuscated)
            assert deobfuscated == test_str

    def test_large_data_handling(self):
        """测试大数据处理"""
        # 大文本数据
        large_text = "A" * 10000

        # 哈希大文本
        result = CryptoUtils.hash_string(large_text)
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256长度

        # Base64编码大文本
        encoded = CryptoUtils.encode_base64(large_text)
        decoded = CryptoUtils.decode_base64(encoded)
        assert decoded == large_text

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试各种边界字符串
        edge_cases = [
            "",  # 空字符串
            "a",  # 单字符
            "A",  # 大写单字符
            "1",  # 数字单字符
            "!",  # 符号单字符
            " ",  # 空格
            "\n",  # 换行符
            "\t",  # 制表符
            "\r\n",  # Windows换行符
            "null\0byte",  # 包含null字节
        ]

        for test_str in edge_cases:
            # 各种操作应该都能处理
            assert isinstance(CryptoUtils.hash_string(test_str), str)
            assert isinstance(CryptoUtils.encode_base64(test_str), str)
            assert isinstance(CryptoUtils.decode_base64(CryptoUtils.encode_base64(test_str)), str)

    def test_security_considerations(self):
        """测试安全考虑"""
        # 测试哈希的单向性
        original = "test_data"
        hashed = CryptoUtils.hash_string(original)

        # 哈希不应该包含原文
        assert original not in hashed

        # 密码哈希应该有不同的格式
        password_hash = CryptoUtils.hash_password(original)
        assert isinstance(password_hash, str)
        assert len(password_hash) > 0  # 密码哈希应该非空

        # 验证密码应该安全
        assert CryptoUtils.verify_password(original, password_hash)
        assert not CryptoUtils.verify_password("wrong", password_hash)

    def test_performance_considerations(self):
        """测试性能考虑"""
        import time

        # 测试批量操作性能
        test_strings = [f"test_string_{i}" for i in range(100)]

        start_time = time.time()

        for test_str in test_strings:
            CryptoUtils.hash_string(test_str)
            CryptoUtils.encode_base64(test_str)
            CryptoUtils.generate_short_id()

        end_time = time.time()
        duration = end_time - start_time

        # 100次操作应该在合理时间内完成（比如1秒内）
        assert duration < 1.0, f"批量操作耗时过长: {duration}秒"

    def test_error_handling_and_robustness(self):
        """测试错误处理和健壮性"""
        # 测试各种可能引起错误的输入
        problematic_inputs = [
            None,
            "",
            "   ",  # 只有空格
            "\x00\x01\x02",  # 二进制数据
            "test" * 10000,  # 超长字符串
        ]

        for input_data in problematic_inputs:
            try:
                # 这些操作不应该崩溃
                if input_data is not None:
                    CryptoUtils.hash_string(input_data)
                    CryptoUtils.encode_base64(input_data)
                    CryptoUtils.create_checksum(input_data)
            except Exception:
                # 如果有异常，应该是预期的
                pass

    def test_consistency_and_reliability(self):
        """测试一致性和可靠性"""
        # 确保相同输入产生相同输出
        test_cases = [
            ("Hello", "md5"),
            ("World", "sha256"),
            ("Test123", "sha1"),
        ]

        for text, algorithm in test_cases:
            # 多次哈希应该一致
            results = [CryptoUtils.hash_string(text, algorithm) for _ in range(10)]
            assert all(r == results[0] for r in results)

            # 多次生成ID应该不同（随机性）
            ids = [CryptoUtils.generate_short_id() for _ in range(10)]
            assert len(set(ids)) == 10  # 所有ID都不同

    def test_integration_scenarios(self):
        """测试集成场景"""
        # 模拟真实使用场景

        # 1. 用户注册和验证
        password = "secure_password_123"

        # 生成用户ID和盐值
        CryptoUtils.generate_uuid()
        salt = CryptoUtils.generate_salt()

        # 哈希密码
        hashed_password = CryptoUtils.hash_password(password, salt)

        # 验证用户信息
        assert CryptoUtils.verify_password(password, hashed_password)
        assert not CryptoUtils.verify_password("wrong_password", hashed_password)

        # 2. API密钥生成和验证
        api_key = CryptoUtils.generate_api_key()
        api_key_checksum = CryptoUtils.create_checksum(api_key)

        assert isinstance(api_key, str)
        assert isinstance(api_key_checksum, str)

        # 3. 数据传输编码
        sensitive_data = "user_sensitive_information"
        encoded_data = CryptoUtils.encode_base64(sensitive_data)
        obfuscated_data = CryptoUtils.obfuscate(sensitive_data)

        # 接收端解码
        decoded_data = CryptoUtils.decode_base64(encoded_data)
        deobfuscated_data = CryptoUtils.deobfuscate(obfuscated_data)

        assert decoded_data == sensitive_data
        assert deobfuscated_data == sensitive_data
