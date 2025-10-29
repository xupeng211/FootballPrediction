"""
加密工具增强测试
补充 src.utils.crypto_utils 模块的测试覆盖，目标达到40%+覆盖率
"""

import threading
import time

import pytest

from src.utils.crypto_utils import CryptoUtils


@pytest.mark.unit
class TestCryptoUtilsEnhanced:
    """加密工具增强测试"""

    def test_generate_uuid_basic(self) -> None:
        """✅ 成功用例：基本UUID生成"""
        uuid1 = CryptoUtils.generate_uuid()
        uuid2 = CryptoUtils.generate_uuid()

        # 验证UUID格式和唯一性
        assert isinstance(uuid1, str)
        assert len(uuid1) == 36  # UUID格式
        assert uuid1 != uuid2  # 每次生成应该不同

    def test_generate_short_id_basic(self) -> None:
        """✅ 成功用例：基本短ID生成"""
        id1 = CryptoUtils.generate_short_id()
        id2 = CryptoUtils.generate_short_id()

        # 验证短ID格式和唯一性
        assert isinstance(id1, str)
        assert len(id1) == 8  # 默认长度
        assert id1 != id2  # 每次生成应该不同

    def test_generate_short_id_custom_length(self) -> None:
        """✅ 成功用例：自定义长度短ID生成"""
        short_id = CryptoUtils.generate_short_id(16)
        assert isinstance(short_id, str)
        assert len(short_id) == 16

    def test_generate_short_id_zero_length(self) -> None:
        """✅ 边界用例：零长度短ID"""
        result = CryptoUtils.generate_short_id(0)
        assert result == ""

    def test_generate_short_id_long_length(self) -> None:
        """✅ 成功用例：超长短ID生成"""
        long_id = CryptoUtils.generate_short_id(64)
        assert isinstance(long_id, str)
        assert len(long_id) == 64

    def test_hash_string_md5(self) -> None:
        """✅ 成功用例：MD5哈希生成"""
        text = "test_data"
        result = CryptoUtils.hash_string(text, "md5")

        # 验证MD5格式
        assert len(result) == 32  # MD5哈希长度
        assert isinstance(result, str)
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_string_sha256(self) -> None:
        """✅ 成功用例：SHA256哈希生成"""
        text = "test_data"
        result = CryptoUtils.hash_string(text, "sha256")

        # 验证SHA256格式
        assert len(result) == 64  # SHA256哈希长度
        assert isinstance(result, str)

    def test_hash_string_sha512(self) -> None:
        """✅ 成功用例：SHA512哈希生成"""
        text = "test_data"
        result = CryptoUtils.hash_string(text, "sha512")

        # 验证SHA512格式
        assert len(result) == 128  # SHA512哈希长度
        assert isinstance(result, str)

    def test_hash_string_unsupported_algorithm(self) -> None:
        """✅ 成功用例：不支持的哈希算法"""
        text = "test_data"
        with pytest.raises(ValueError, match="不支持的哈希算法"):
            CryptoUtils.hash_string(text, "unsupported_algo")

    def test_hash_string_empty_input(self) -> None:
        """✅ 边界用例：空字符串哈希"""
        result = CryptoUtils.hash_string("", "sha256")
        assert len(result) == 64

    def test_hash_string_non_string_input(self) -> None:
        """✅ 边界用例：非字符串输入"""
        result = CryptoUtils.hash_string(123, "sha256")
        assert result == ""

    def test_encode_base64_basic(self) -> None:
        """✅ 成功用例：基本Base64编码"""
        text = "Hello World"
        result = CryptoUtils.encode_base64(text)

        assert isinstance(result, str)
        assert result == "SGVsbG8gV29ybGQ="

    def test_decode_base64_basic(self) -> None:
        """✅ 成功用例：基本Base64解码"""
        encoded_text = "SGVsbG8gV29ybGQ="
        result = CryptoUtils.decode_base64(encoded_text)

        assert isinstance(result, str)
        assert result == "Hello World"

    def test_base64_round_trip(self) -> None:
        """✅ 成功用例：Base64编解码往返"""
        original = "测试中文🚀emoji"
        encoded = CryptoUtils.encode_base64(original)
        decoded = CryptoUtils.decode_base64(encoded)

        assert decoded == original

    def test_base64_non_string_input(self) -> None:
        """✅ 边界用例：Base64非字符串输入"""
        # 编码测试
        result = CryptoUtils.encode_base64(123)
        assert result == ""

        # 解码测试
        result = CryptoUtils.decode_base64(123)
        assert result == ""

    def test_generate_salt_basic(self) -> None:
        """✅ 成功用例：基本盐值生成"""
        salt1 = CryptoUtils.generate_salt()
        salt2 = CryptoUtils.generate_salt()

        # 验证盐值格式和唯一性
        assert isinstance(salt1, str)
        assert len(salt1) == 32  # 默认盐值长度
        assert salt1 != salt2  # 每次生成应该不同

    def test_generate_salt_custom_length(self) -> None:
        """✅ 成功用例：自定义长度盐值生成"""
        salt = CryptoUtils.generate_salt(16)
        assert isinstance(salt, str)
        assert len(salt) == 32  # token_hex返回的是length*2长度

    def test_generate_token_basic(self) -> None:
        """✅ 成功用例：基本令牌生成"""
        token1 = CryptoUtils.generate_token()
        token2 = CryptoUtils.generate_token()

        # 验证令牌格式和唯一性
        assert isinstance(token1, str)
        assert len(token1) == 64  # 默认token_hex(32)返回64长度
        assert token1 != token2  # 每次生成应该不同

    def test_generate_token_custom_length(self) -> None:
        """✅ 成功用例：自定义长度令牌生成"""
        token = CryptoUtils.generate_token(16)
        assert isinstance(token, str)
        assert len(token) == 32  # token_hex(16)返回32长度

    def test_hash_password_basic(self) -> None:
        """✅ 成功用例：基本密码哈希"""
        password = "test_password_123"
        hashed = CryptoUtils.hash_password(password)

        # 验证哈希结果
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_hash_password_with_salt(self) -> None:
        """✅ 成功用例：带盐值的密码哈希"""
        password = "test_password"
        salt = CryptoUtils.generate_short_id(16)
        hashed = CryptoUtils.hash_password(password, salt)

        assert isinstance(hashed, str)
        # 注意：bcrypt使用自己的盐值格式，所以我们检查哈希格式而不是具体盐值
        assert hashed.startswith("$2b$")  # bcrypt格式

    def test_verify_password_correct(self) -> None:
        """✅ 成功用例：正确密码验证"""
        password = "correct_password"
        hashed = CryptoUtils.hash_password(password)

        result = CryptoUtils.verify_password(password, hashed)
        assert result is True

    def test_verify_password_incorrect(self) -> None:
        """✅ 成功用例：错误密码验证"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = CryptoUtils.hash_password(password)

        result = CryptoUtils.verify_password(wrong_password, hashed)
        assert result is False

    def test_verify_password_empty_strings(self) -> None:
        """✅ 边界用例：空字符串密码验证"""
        result = CryptoUtils.verify_password("", "")
        assert result is True

    def test_edge_cases_empty_data(self) -> None:
        """✅ 边界用例：空数据处理"""
        # 空字符串哈希
        result = CryptoUtils.hash_string("", "sha256")
        assert len(result) == 64

        # 空字符串编码
        result = CryptoUtils.encode_base64("")
        assert result == ""

        # 空字符串解码
        result = CryptoUtils.decode_base64("")
        assert result == ""

        # 空字符串密码哈希
        hashed = CryptoUtils.hash_password("")
        assert isinstance(hashed, str)

    def test_edge_cases_long_data(self) -> None:
        """✅ 边界用例：长数据处理"""
        # 长字符串哈希
        long_string = "a" * 10000
        hashed = CryptoUtils.hash_string(long_string, "sha256")
        assert len(hashed) == 64

        # 长字符串编码
        encoded = CryptoUtils.encode_base64(long_string)
        decoded = CryptoUtils.decode_base64(encoded)
        assert decoded == long_string

        # 长密码（bcrypt限制为72字节）
        long_password = "a" * 50  # 使用50字节，在限制范围内
        hashed = CryptoUtils.hash_password(long_password)
        assert isinstance(hashed, str)

        # 测试超长密码的处理
        very_long_password = "a" * 100
        try:
            hashed = CryptoUtils.hash_password(very_long_password)
            # 如果bcrypt可用，会抛出ValueError
            # 如果bcrypt不可用，会使用简单的SHA256实现
            assert isinstance(hashed, str)
        except ValueError:
            # bcrypt抛出异常是预期的行为
            pass

    def test_unicode_handling(self) -> None:
        """✅ 边界用例：Unicode字符处理"""
        unicode_text = "测试中文🚀emoji"

        # Unicode哈希
        hashed = CryptoUtils.hash_string(unicode_text, "sha256")
        assert len(hashed) == 64

        # Unicode编码解码
        encoded = CryptoUtils.encode_base64(unicode_text)
        decoded = CryptoUtils.decode_base64(encoded)
        assert decoded == unicode_text

        # Unicode密码
        unicode_password = "测试密码🔒"
        hashed = CryptoUtils.hash_password(unicode_password)
        result = CryptoUtils.verify_password(unicode_password, hashed)
        assert result is True

    def test_performance_considerations(self) -> None:
        """✅ 性能用例：性能考虑"""
        # 测试哈希性能
        text = "test_data"

        start_time = time.perf_counter()
        for _ in range(100):
            CryptoUtils.hash_string(text, "sha256")
        end_time = time.perf_counter()

        # 100次哈希应该在1秒内完成
        assert end_time - start_time < 1.0

        # 测试UUID生成性能
        start_time = time.perf_counter()
        for _ in range(100):
            CryptoUtils.generate_uuid()
        end_time = time.perf_counter()

        # 100次UUID生成应该在1秒内完成
        assert end_time - start_time < 1.0

    def test_thread_safety(self) -> None:
        """✅ 并发用例：线程安全测试"""
        results = []
        errors = []

        def generate_ids(count: int, thread_id: int):
            try:
                for _ in range(count):
                    uuid_result = CryptoUtils.generate_uuid()
                    results.append(f"thread_{thread_id}_{uuid_result}")
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时生成UUID
        threads = []
        for i in range(5):
            thread = threading.Thread(target=generate_ids, args=(20, i))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有错误
        assert len(errors) == 0
        assert len(results) == 100

        # 验证唯一性
        uuid_values = [r.split("_", 2)[-1] for r in results]
        unique_uuids = set(uuid_values)
        assert len(unique_uuids) == 100  # 所有UUID都应该是唯一的

    def test_consistency_validation(self) -> None:
        """✅ 一致性验证：相同输入产生相同输出"""
        # 哈希一致性
        text = "consistent_test"
        hash1 = CryptoUtils.hash_string(text, "sha256")
        hash2 = CryptoUtils.hash_string(text, "sha256")
        assert hash1 == hash2

        # Base64编码一致性
        original = "consistent encoding test"
        encoded1 = CryptoUtils.encode_base64(original)
        encoded2 = CryptoUtils.encode_base64(original)
        assert encoded1 == encoded2

        # 短ID生成的唯一性（每次应该不同）
        id1 = CryptoUtils.generate_short_id(10)
        id2 = CryptoUtils.generate_short_id(10)
        assert id1 != id2  # 验证随机性

    def test_error_handling(self) -> None:
        """✅ 错误处理：各种异常情况"""
        # Base64解码错误处理
        invalid_base64 = "invalid_base64!"
        result = CryptoUtils.decode_base64(invalid_base64)
        assert result == ""  # 错误处理应该返回空字符串

        # 密码验证错误处理
        invalid_hash = "invalid_hash_format"
        result = CryptoUtils.verify_password("password", invalid_hash)
        assert result is False

    def test_comprehensive_workflow(self) -> None:
        """✅ 综合用例：完整的加密工作流"""
        # 1. 生成用户ID和令牌
        user_id = CryptoUtils.generate_uuid()
        token = CryptoUtils.generate_token(16)
        salt = CryptoUtils.generate_salt(8)

        # 2. 创建用户密码哈希
        password = "user_secure_password"
        password_hash = CryptoUtils.hash_password(password, salt)

        # 3. 验证密码
        is_valid = CryptoUtils.verify_password(password, password_hash)
        assert is_valid is True

        # 4. 创建用户数据的哈希摘要
        user_data = f"{user_id}:{token}"
        data_hash = CryptoUtils.hash_string(user_data, "sha256")

        # 5. 验证数据完整性
        assert len(data_hash) == 64
        assert isinstance(data_hash, str)

        # 6. 编码敏感数据
        sensitive_data = f"{user_id}:{password_hash}"
        encoded_data = CryptoUtils.encode_base64(sensitive_data)
        decoded_data = CryptoUtils.decode_base64(encoded_data)

        assert decoded_data == sensitive_data
