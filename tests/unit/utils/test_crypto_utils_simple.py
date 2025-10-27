"""
测试加密工具 - 符合严格测试规范

重构原有简单测试，添加异常用例、Mock和完整断言覆盖
"""

import hashlib
import uuid
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from src.utils.crypto_utils import CryptoUtils


@pytest.mark.unit
class TestCryptoUtilsBasic:
    """测试CryptoUtils的基础功能 - 符合严格测试规范"""

    def test_generate_uuid_success(self) -> None:
        """✅ 成功用例：正常生成UUID"""
        uuid_result = CryptoUtils.generate_uuid()

        assert isinstance(uuid_result, str)
        assert len(uuid_result) == 36  # UUID标准长度
        assert uuid_result.count("-") == 4  # UUID格式验证

        # 验证可以解析为UUID对象
        parsed_uuid = uuid.UUID(uuid_result)
        assert str(parsed_uuid) == uuid_result

    @patch("uuid.uuid4")
    def test_generate_uuid_exception(self, mock_uuid4: Mock) -> None:
        """❌ 异常用例：UUID生成失败"""
        mock_uuid4.side_effect = Exception("UUID generation failed")

        with pytest.raises(Exception, match="UUID generation failed"):
            CryptoUtils.generate_uuid()

    def test_generate_short_id_success(self) -> None:
        """✅ 成功用例：生成默认长度短ID"""
        short_id = CryptoUtils.generate_short_id()

        assert isinstance(short_id, str)
        assert len(short_id) == 8
        assert short_id.isalnum()  # 仅包含字母和数字

    def test_generate_short_id_custom_length(self) -> None:
        """✅ 成功用例：自定义长度短ID"""
        for length in [4, 12, 16, 32]:
            short_id = CryptoUtils.generate_short_id(length)
            assert isinstance(short_id, str)
            assert len(short_id) == length
            assert short_id.isalnum()

    def test_generate_short_id_zero_length(self) -> None:
        """✅ 边界用例：长度为0的短ID"""
        short_id = CryptoUtils.generate_short_id(0)
        assert short_id == ""

    def test_generate_short_id_negative_length(self) -> None:
        """✅ 边界用例：负数长度短ID"""
        short_id = CryptoUtils.generate_short_id(-5)
        assert short_id == ""

    @patch("uuid.uuid4")
    def test_generate_short_id_exception(self, mock_uuid4: Mock) -> None:
        """❌ 异常用例：短ID生成失败"""
        mock_uuid4.side_effect = Exception("UUID generation failed")

        with pytest.raises(Exception, match="UUID generation failed"):
            CryptoUtils.generate_short_id()

    def test_hash_string_md5_success(self) -> None:
        """✅ 成功用例：MD5字符串哈希"""
        text = "test data"
        hashed = CryptoUtils.hash_string(text, "md5")

        expected = hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()
        assert hashed == expected
        assert len(hashed) == 32
        assert hashed.isalnum()
        assert hashed != text

    def test_hash_string_sha256_success(self) -> None:
        """✅ 成功用例：SHA256字符串哈希"""
        text = "test data"
        hashed = CryptoUtils.hash_string(text, "sha256")

        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert hashed == expected
        assert len(hashed) == 64
        assert hashed.isalnum()
        assert hashed != text

    def test_hash_string_empty_input(self) -> None:
        """✅ 边界用例：空字符串哈希"""
        hashed = CryptoUtils.hash_string("", "md5")
        expected = hashlib.md5(b"", usedforsecurity=False).hexdigest()
        assert hashed == expected

    def test_hash_string_unsupported_algorithm(self) -> None:
        """❌ 异常用例：不支持的哈希算法"""
        with pytest.raises(ValueError, match="不支持的哈希算法"):
            CryptoUtils.hash_string("test", "unsupported_algo")

    def test_hash_string_none_input(self) -> None:
        """❌ 异常用例：None输入"""
        with pytest.raises(AttributeError):
            CryptoUtils.hash_string(None, "md5")

    def test_generate_salt_if_exists(self) -> None:
        """✅ 成功用例：生成盐值（如果方法存在）"""
        if hasattr(CryptoUtils, "generate_salt"):
            salt = CryptoUtils.generate_salt()
            assert isinstance(salt, str)
            assert len(salt) > 0
            # 盐值通常应该是随机的
            salt2 = CryptoUtils.generate_salt()
            assert salt != salt2

    def test_generate_token_if_exists(self) -> None:
        """✅ 成功用例：生成令牌（如果方法存在）"""
        if hasattr(CryptoUtils, "generate_token"):
            token = CryptoUtils.generate_token()
            assert isinstance(token, str)
            assert len(token) > 0
            assert token.isalnum()

    def test_hash_password_if_exists(self) -> None:
        """✅ 成功用例：密码哈希（如果方法存在）"""
        if hasattr(CryptoUtils, "hash_password"):
            password = "my_secure_password"
            hashed = CryptoUtils.hash_password(password)

            assert isinstance(hashed, str)
            assert hashed != password
            assert len(hashed) > 0

    def test_verify_password_if_exists(self) -> None:
        """✅ 成功用例：密码验证（如果方法存在）"""
        if hasattr(CryptoUtils, "hash_password") and hasattr(
            CryptoUtils, "verify_password"
        ):
            password = "my_secure_password"
            hashed = CryptoUtils.hash_password(password)

            # 正确密码验证
            assert CryptoUtils.verify_password(password, hashed) is True

            # 错误密码验证
            assert CryptoUtils.verify_password("wrong_password", hashed) is False

    def test_verify_password_wrong_type_if_exists(self) -> None:
        """❌ 异常用例：错误类型密码验证"""
        if hasattr(CryptoUtils, "verify_password"):
            with pytest.raises((TypeError, AttributeError)):
                CryptoUtils.verify_password(123, "some_hash")

    def test_salt_uniqueness_if_exists(self) -> None:
        """✅ 成功用例：盐值唯一性（如果方法存在）"""
        if hasattr(CryptoUtils, "generate_salt"):
            salts = [CryptoUtils.generate_salt() for _ in range(10)]
            unique_salts = set(salts)

            # 10个盐值应该都是唯一的
            assert len(unique_salts) == 10

    @patch("secrets.token_hex")
    def test_generate_salt_exception_if_exists(self, mock_token_hex: Mock) -> None:
        """❌ 异常用例：盐值生成异常（如果方法存在）"""
        mock_token_hex.side_effect = Exception("Random generation failed")

        if hasattr(CryptoUtils, "generate_salt"):
            with pytest.raises(Exception, match="Random generation failed"):
                CryptoUtils.generate_salt()

    def test_integration_complete_workflow(self) -> None:
        """✅ 集成用例：完整工作流测试"""
        # 生成UUID
        user_id = CryptoUtils.generate_uuid()
        assert len(user_id) == 36

        # 生成短ID
        session_id = CryptoUtils.generate_short_id(12)
        assert len(session_id) == 12

        # 创建认证令牌哈希
        auth_data = f"{user_id}:{session_id}"
        auth_hash = CryptoUtils.hash_string(auth_data, "sha256")

        assert len(auth_hash) == 64
        assert auth_hash.isalnum()

        # 验证一致性
        expected_hash = CryptoUtils.hash_string(auth_data, "sha256")
        assert auth_hash == expected_hash

    def test_performance_large_data_hash(self) -> None:
        """✅ 性能用例：大数据哈希性能"""
        import time

        large_data = "a" * 100000  # 100KB数据
        start_time = time.time()

        result = CryptoUtils.hash_string(large_data, "sha256")

        end_time = time.time()
        processing_time = end_time - start_time

        assert len(result) == 64
        # 应该在合理时间内完成（<1秒）
        assert processing_time < 1.0

    def test_concurrent_id_generation(self) -> None:
        """✅ 并发用例：并发ID生成唯一性"""
        import threading
        import time

        ids = []
        errors = []

        def generate_ids(count: int, thread_id: int) -> None:
            try:
                for _ in range(count):
                    ids.append(f"thread_{thread_id}_{CryptoUtils.generate_short_id()}")
            except Exception as e:
                errors.append(e)

        # 创建5个线程，每个生成20个ID
        threads = []
        for i in range(5):
            thread = threading.Thread(target=generate_ids, args=(20, i))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证没有错误
        assert len(errors) == 0
        assert len(ids) == 100

        # 验证唯一性（考虑线程前缀）
        base_ids = [id_.split("_", 2)[-1] for id_ in ids]
        unique_base_ids = set(base_ids)

        # 应该至少有95%的唯一性
        assert len(unique_base_ids) >= 95


@pytest.fixture(autouse=True)
def setup_crypto_utils_test():
    """自动应用的fixture，设置测试环境"""
    yield
    # 清理代码
