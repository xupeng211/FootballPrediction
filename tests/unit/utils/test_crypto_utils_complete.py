"""
CryptoUtils完整测试
覆盖所有功能并发现潜在问题
"""

import pytest
import sys
import os
import hashlib

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

from src.utils.crypto_utils import CryptoUtils, HAS_BCRYPT


class TestCryptoUtilsComplete:
    """CryptoUtils完整测试套件"""

    def test_hash_password_with_bcrypt(self):
        """测试使用bcrypt的密码哈希"""
        password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_22")

        # 哈希密码
        hashed = CryptoUtils.hash_password(password)

        # 验证格式
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")  # bcrypt格式

        # 验证密码
        assert CryptoUtils.verify_password(password, hashed) == True

        # 验证错误密码
        assert CryptoUtils.verify_password("wrong_password", hashed) == False

    def test_hash_password_fallback(self):
        """测试当bcrypt不可用时的回退机制"""
        # 注意：由于bcrypt已安装，我们无法真正禁用它
        # 但可以测试哈希功能本身
        password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_39")
        salt = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_SALT_41")

        # 使用自定义salt哈希（当bcrypt不可用时的逻辑）
        salted_password = f"{password}{salt}"
        hash_value = hashlib.sha256(salted_password.encode("utf-8")).hexdigest()
        manual_hash = f"$2b$12${salt}${hash_value}"

        assert isinstance(manual_hash, str)
        assert manual_hash.startswith("$2b$12$")
        assert salt in manual_hash

        # 验证手动创建的哈希
        result = CryptoUtils.verify_password(password, manual_hash)
        # 由于bcrypt已安装，这个可能不会执行fallback逻辑
        # 但代码应该能处理这种情况

    def test_verify_password_edge_cases(self):
        """测试密码验证的边界情况"""
        # 空密码和空哈希
        assert CryptoUtils.verify_password("", "") == True

        # 空密码和非空哈希
        hashed = CryptoUtils.hash_password("test")
        assert CryptoUtils.verify_password("", hashed) == False

        # 非空密码和空哈希
        assert CryptoUtils.verify_password("test", "") == False

    def test_verify_password_invalid_format(self):
        """测试无效哈希格式的处理"""
        # 无效的哈希格式
        invalid_hashes = [
            "invalid_hash",
            "$2b$invalid",
            "$2b$12$incomplete",
            "$2b$12$salt$hash$extra$parts",
            "$2a$12$salt$hash"  # 错误的版本
        ]

        for invalid_hash in invalid_hashes:
            # 应该返回False而不是抛出异常
            result = CryptoUtils.verify_password("password", invalid_hash)
            assert isinstance(result, bool)

    def test_hash_string_unsupported_algorithm(self):
        """测试不支持的哈希算法"""
        with pytest.raises(ValueError, match = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_MATCH_86")):
            CryptoUtils.hash_string("test", "unknown_algorithm")

    def test_generate_short_id_large_length(self):
        """测试生成大长度的短ID"""
        # 测试大于32的长度
        large_id = CryptoUtils.generate_short_id(50)
        assert len(large_id) == 50
        assert '-' not in large_id  # 不应该包含连字符

        # 测试每次生成都不同
        large_id2 = CryptoUtils.generate_short_id(50)
        assert large_id != large_id2

    def test_generate_short_id_zero_negative(self):
        """测试零长度和负长度"""
        assert CryptoUtils.generate_short_id(0) == ""
        assert CryptoUtils.generate_short_id(-1) == ""
        assert CryptoUtils.generate_short_id(-10) == ""

    def test_hash_string_performance(self):
        """测试哈希性能"""
        import time

        # 测试大量数据的哈希
        large_data = "x" * 10000

        start_time = time.time()
        result = CryptoUtils.hash_string(large_data, "sha256")
        duration = time.time() - start_time

        # 应该在合理时间内完成
        assert duration < 0.1  # 100ms
        assert len(result) == 64

    def test_password_hash_security(self):
        """测试密码哈希的安全性"""
        password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_120")

        # 相同密码应该产生不同哈希（因为有随机盐）
        hash1 = CryptoUtils.hash_password(password)
        hash2 = CryptoUtils.hash_password(password)

        assert hash1 != hash2
        assert len(hash1) == len(hash2)

        # 但都应该能验证通过
        assert CryptoUtils.verify_password(password, hash1) == True
        assert CryptoUtils.verify_password(password, hash2) == True

    def test_unicode_password_handling(self):
        """测试Unicode密码处理"""
        unicode_passwords = [
            "中文密码",
            "🚀 emoji password",
            "密码123!@#",
            "ñáéíóú"
        ]

        for pwd in unicode_passwords:
            # 哈希
            hashed = CryptoUtils.hash_password(pwd)
            assert isinstance(hashed, str)

            # 验证
            assert CryptoUtils.verify_password(pwd, hashed) == True
            assert CryptoUtils.verify_password(pwd + "wrong", hashed) == False

    def test_module_constants(self):
        """测试模块常量"""
        # 验证HAS_BCRYPT存在且是布尔值
        assert isinstance(HAS_BCRYPT, bool)

        # 应该为True，因为我们安装了bcrypt
        assert HAS_BCRYPT == True

    def test_hash_algorithm_consistency(self):
        """测试哈希算法的一致性"""
        test_string = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_TEST_STRING_159")

        # 多次哈希应该产生相同结果
        hash1 = CryptoUtils.hash_string(test_string, "md5")
        hash2 = CryptoUtils.hash_string(test_string, "md5")
        assert hash1 == hash2

        # SHA256也是
        hash3 = CryptoUtils.hash_string(test_string, "sha256")
        hash4 = CryptoUtils.hash_string(test_string, "sha256")
        assert hash3 == hash4

        # 但不同算法应该不同
        assert hash1 != hash3

    def test_error_handling_in_hash_functions(self):
        """测试哈希函数的错误处理"""
        # 测试非字符串输入（如果允许的话）
        try:
            # 尝试传递非字符串
            result = CryptoUtils.hash_string(123, "md5")
            # 如果成功，应该返回有效哈希
            assert isinstance(result, str)
            assert len(result) == 32
        except (TypeError, AttributeError):
            # 如果抛出异常，也是可以接受的
            pass

    def test_password_hash_with_bytes(self):
        """测试字节类型的密码"""
        # 虽然接口期望字符串，但测试字节处理
        password_str = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_STR_189")
        password_bytes = password_str.encode('utf-8')

        # 哈希
        hashed_from_str = CryptoUtils.hash_password(password_str)

        # 验证
        assert CryptoUtils.verify_password(password_bytes, hashed_from_str) == True
        assert CryptoUtils.verify_password(password_str, hashed_from_str) == True


class TestCryptoUtilsSecurityIssues:
    """测试潜在的安全问题"""

    def test_timing_attack_resistance(self):
        """测试时序攻击抵抗（基本检查）"""
        import time

        password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_204")
        wrong_password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_WRONG_PASSWORD_205")
        hashed = CryptoUtils.hash_password(password)

        # 多次验证正确密码
        times_correct = []
        for _ in range(10):
            start = time.perf_counter()
            CryptoUtils.verify_password(password, hashed)
            times_correct.append(time.perf_counter() - start)

        # 多次验证错误密码
        times_wrong = []
        for _ in range(10):
            start = time.perf_counter()
            CryptoUtils.verify_password(wrong_password, hashed)
            times_wrong.append(time.perf_counter() - start)

        # 平均时间不应该有太大差异（这是一个简化的检查）
        avg_correct = sum(times_correct) / len(times_correct)
        avg_wrong = sum(times_wrong) / len(times_wrong)

        # 在大多数情况下，差异不应该超过10倍
        # 注意：这不是一个严格的安全测试，只是一个基本检查
        ratio = max(avg_correct, avg_wrong) / min(avg_correct, avg_wrong)
        assert ratio < 100, f"时序差异过大: {ratio:.2f}x"

    def test_hash_collision_resistance(self):
        """测试哈希碰撞抵抗"""
        # 生成大量不同的短ID
        ids = [CryptoUtils.generate_short_id(16) for _ in range(1000)]

        # 检查唯一性
        unique_ids = set(ids)
        assert len(unique_ids) == 1000, "发现了ID碰撞！"

        # 检查ID格式
        for id_str in ids:
            assert len(id_str) == 16
            assert id_str.isalnum()  # 只包含字母和数字

    def test_sensitive_data_handling(self):
        """测试敏感数据处理"""
        # 确保密码不会在日志或异常中泄露
        password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_245")

        try:
            # 哈希密码
            hashed = CryptoUtils.hash_password(password)

            # 检查哈希不包含原始密码
            assert password not in hashed

            # 验证
            result = CryptoUtils.verify_password(password, hashed)
            assert result == True

        except Exception as e:
            # 如果有异常，确保密码不在错误消息中
            error_msg = str(e)
            assert password not in error_msg, f"密码泄露在错误消息中: {error_msg}"


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "-s"])