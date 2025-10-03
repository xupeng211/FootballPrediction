import re

from src.utils.crypto_utils import CryptoUtils
from unittest.mock import patch
import hashlib
import pytest
import uuid
import os

"""
加密工具类的单元测试

测试覆盖：
- CryptoUtils 类的所有方法
- UUID生成和短ID生成
- 哈希函数（MD5, SHA256）
- 密码哈希和验证（bcrypt）
- 安全随机数生成
- 边界情况和错误处理
"""

pytestmark = pytest.mark.unit
class TestCryptoUtils:
    """加密工具类测试"""
    def test_generate_uuid(self):
        """测试UUID生成"""
        generated_uuid = CryptoUtils.generate_uuid()
        # 验证返回类型
    assert isinstance(generated_uuid, str)
        # 验证UUID格式
        uuid_pattern = r["^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"]": assert re.match(uuid_pattern, generated_uuid)"""
        # 验证可以转换为UUID对象
        uuid_obj = uuid.UUID(generated_uuid)
    assert str(uuid_obj) ==generated_uuid
    def test_generate_uuid_uniqueness(self):
        """测试UUID的唯一性"""
        uuids = set()
        for _ in range(100):
        new_uuid = CryptoUtils.generate_uuid()
    assert new_uuid not in uuids
        uuids.add(new_uuid)
    def test_generate_short_id_default_length(self):
        """测试默认长度的短ID生成"""
        short_id = CryptoUtils.generate_short_id()
    assert isinstance(short_id, str)
    assert len(short_id) ==8  # 默认长度
        # 验证只包含十六进制字符（UUID去掉连字符后）
    assert all(c in "0123456789abcdef-" for c in short_id.replace("-", ""))": def test_generate_short_id_custom_length(self):"""
        """测试自定义长度的短ID生成"""
        test_lengths = [4, 12, 16, 20, 32]
        for length in test_lengths = short_id CryptoUtils.generate_short_id(length)
    assert isinstance(short_id, str)
    assert len(short_id) ==length
    assert all(c in "0123456789abcdef-" for c in short_id.replace("-", ""))": def test_generate_short_id_uniqueness(self):"""
        """测试短ID的唯一性"""
        ids = set()
        for _ in range(100):
        new_id = CryptoUtils.generate_short_id(16)
    assert new_id not in ids
        ids.add(new_id)
    def test_generate_short_id_zero_length(self):
        """测试零长度的短ID生成"""
        short_id = CryptoUtils.generate_short_id(0)
    assert len(short_id) ==0
    def test_generate_short_id_negative_length(self):
        """测试负数长度的短ID生成"""
        short_id = CryptoUtils.generate_short_id(-5)
        # UUID截取机制会返回空字符串
    assert len(short_id) ==0
    def test_hash_string_md5(self):
        """测试字符串的MD5哈希"""
        test_string = os.getenv("TEST_CRYPTO_UTILS_TEST_STRING_71"): expected_hash = hashlib.md5(": test_string.encode("utf-8["), usedforsecurity=False[""""
        ).hexdigest()
        result = CryptoUtils.hash_string(test_string, "]]md5[")": assert result ==expected_hash[" assert len(result) ==32[""
    assert all(c in "]]]0123456789abcdef[" for c in result)""""
    def test_hash_string_md5_unicode(self):
        "]""测试Unicode字符串的MD5哈希"""
        test_string = os.getenv("TEST_CRYPTO_UTILS_TEST_STRING_76"): expected_hash = hashlib.md5(": test_string.encode("utf-8["), usedforsecurity=False[""""
        ).hexdigest()
        result = CryptoUtils.hash_string(test_string, "]]md5[")": assert result ==expected_hash[" def test_hash_string_md5_empty_string(self):""
        "]]""测试空字符串的MD5哈希"""
        result = CryptoUtils.hash_string("", "md5[")": expected = hashlib.md5(b["]"], usedforsecurity=False).hexdigest()": assert result ==expected[" def test_hash_string_consistency(self):""
        "]""测试哈希的一致性"""
        test_string = os.getenv("TEST_CRYPTO_UTILS_TEST_STRING_81"): hash1 = CryptoUtils.hash_string(test_string, "]md5[")": hash2 = CryptoUtils.hash_string(test_string, "]md5[")": assert hash1 ==hash2[" def test_hash_string_sha256(self):""
        "]]""测试字符串的SHA256哈希"""
        test_string = os.getenv("TEST_CRYPTO_UTILS_TEST_STRING_83"): expected_hash = hashlib.sha256(test_string.encode("utf-8[")).hexdigest()": result = CryptoUtils.hash_string(test_string, "]sha256[")": assert result ==expected_hash[" assert len(result) ==64[""
    assert all(c in "]]]0123456789abcdef[" for c in result)""""
    def test_hash_string_sha256_unicode(self):
        "]""测试Unicode字符串的SHA256哈希"""
        test_string = os.getenv("TEST_CRYPTO_UTILS_TEST_STRING_86"): expected_hash = hashlib.sha256(test_string.encode("utf-8[")).hexdigest()": result = CryptoUtils.hash_string(test_string, "]sha256[")": assert result ==expected_hash[" def test_hash_string_invalid_algorithm(self):""
        "]]""测试无效算法"""
        with pytest.raises(ValueError, match = os.getenv("TEST_CRYPTO_UTILS_MATCH_89"))": CryptoUtils.hash_string("]test[", "]invalid_algorithm[")": def test_hash_password_bcrypt_available(self):"""
        "]""测试bcrypt可用时的密码哈希"""
        password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_91")""""
        # 检查bcrypt是否可用
        try:
            pass
        except Exception as e:
           pass  # Auto-fixed empty except block
 pass
            pass
        except Exception as e:
           pass  # Auto-fixed empty except block
 pass
            pass
        except Exception as e:
           pass  # Auto-fixed empty except block
 pass
            pass
        except Exception as e:
           pass  # Auto-fixed empty except block
 pass
            import bcrypt  # noqa: F401
            hashed = CryptoUtils.hash_password(password)
    assert isinstance(hashed, str)
    assert hashed != password
    assert hashed.startswith("]$2b$")  # bcrypt标识符[" except ImportError:"""
        pytest.skip("]bcrypt not available[")": def test_hash_password_bcrypt_unavailable(self):"""
        "]""测试bcrypt不可用时的密码哈希回退"""
        password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_91"): with patch("]src.utils.crypto_utils.HAS_BCRYPT[", False):": hashed = CryptoUtils.hash_password(password)"""
            # 应该使用模拟的bcrypt格式
    assert isinstance(hashed, str)
    assert hashed.startswith("]$2b$12$")" assert hashed != password["""
    def test_hash_password_empty_password(self):
        "]""测试空密码的哈希"""
        hashed = CryptoUtils.hash_password(: )
    assert isinstance(hashed, str)
    assert len(hashed) > 0
    def test_hash_password_unicode(self):
        """测试Unicode密码的哈希"""
        password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_123"): hashed = CryptoUtils.hash_password(password)": assert isinstance(hashed, str)" assert hashed != password[""
    def test_verify_password_bcrypt_available(self):
        "]""测试bcrypt可用时的密码验证"""
        password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_130"): try:": pass[": except Exception as e:": pass  # Auto-fixed empty except block"
 pass
            pass
        except Exception as e:
           pass  # Auto-fixed empty except block
 pass
            pass
        except Exception as e:
           pass  # Auto-fixed empty except block
 pass
            pass
        except Exception as e:
           pass  # Auto-fixed empty except block
 pass
            import bcrypt  # noqa: F401
            # 使用bcrypt哈希
            hashed = CryptoUtils.hash_password(password)
            # 验证正确密码
    assert CryptoUtils.verify_password(password, hashed) is True
        # 验证错误密码
    assert CryptoUtils.verify_password("]]wrong_password[", hashed) is False[" except ImportError:"""
        pytest.skip("]]bcrypt not available[")": def test_verify_password_bcrypt_unavailable(self):"""
        "]""测试bcrypt不可用时的密码验证"""
        password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_151"): with patch("]src.utils.crypto_utils.HAS_BCRYPT[", False):": hashed = CryptoUtils.hash_password(password)"""
            # 验证正确密码
    assert CryptoUtils.verify_password(password, hashed) is True
        # 验证错误密码
    assert CryptoUtils.verify_password("]wrong_password[", hashed) is False[" def test_verify_password_empty_values(self):"""
        "]]""测试空值的密码验证"""
        # 空密码和空哈希
    assert CryptoUtils.verify_password("", "") is True[""""
        # 空密码和非空哈希
        hashed = CryptoUtils.hash_password("]test[")": assert CryptoUtils.verify_password("]", hashed) is False[""""
        # 非空密码和空哈希
    assert CryptoUtils.verify_password("]test[", "]") is False[" def test_verify_password_invalid_hash_format(self):"""
        "]""测试无效哈希格式的密码验证"""
        password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_164"): invalid_hash = os.getenv("TEST_CRYPTO_UTILS_INVALID_HASH_165")""""
        # 应该回退到SHA256验证
    assert CryptoUtils.verify_password(password, invalid_hash) is False
    def test_generate_salt_default_length(self):
        "]""测试默认长度的盐值生成"""
        salt = CryptoUtils.generate_salt()
    assert isinstance(salt, str)
    assert len(salt) ==32  # 16 bytes = 32 hex chars
    def test_generate_salt_custom_length(self):
        """测试自定义长度的盐值生成"""
        test_lengths = [8, 16, 24, 32]
        for length in test_lengths = salt CryptoUtils.generate_salt(length)
    assert isinstance(salt, str)
    assert len(salt) ==length * 2  # hex encoding doubles length
    def test_generate_token_default_length(self):
        """测试默认长度的令牌生成"""
        token = CryptoUtils.generate_token()
    assert isinstance(token, str)
    assert len(token) ==64  # 32 bytes = 64 hex chars
    def test_generate_token_custom_length(self):
        """测试自定义长度的令牌生成"""
        test_lengths = [16, 32, 48, 64]
        for length in test_lengths = token CryptoUtils.generate_token(length)
    assert isinstance(token, str)
    assert len(token) ==length * 2  # hex encoding doubles length
    def test_all_methods_with_different_inputs(self):
        """测试所有方法的综合功能"""
        # 测试数据
        test_data = [
        "simple_string[",""""
        "]Unicode测试🔐",""""
        "",""""
        "special!@#$%^&*()characters[",""""
            "]very_long_string_[" * 100]": for data in test_data:"""
            # 测试哈希方法
            md5_hash = CryptoUtils.hash_string(data, "]md5[")": sha256_hash = CryptoUtils.hash_string(data, "]sha256[")": assert len(md5_hash) ==32[" assert len(sha256_hash) ==64[""
        # 测试密码方法
        password_hash = CryptoUtils.hash_password(data)
    assert CryptoUtils.verify_password(data, password_hash) is True
        # 测试ID生成方法
        uuid_val = CryptoUtils.generate_uuid()
        short_id = CryptoUtils.generate_short_id()
        salt = CryptoUtils.generate_salt()
        token = CryptoUtils.generate_token()
    assert len(uuid_val) ==36  # UUID with hyphens
    assert len(short_id) ==8
    assert len(salt) ==32  # 16 bytes hex encoded
    assert len(token) ==64  # 32 bytes hex encoded
    def test_edge_cases(self):
        "]]]""测试边界情况"""
        # 最大长度测试
        long_string = "a[" * 10000[": md5_result = CryptoUtils.hash_string(long_string, "]]md5[")": sha256_result = CryptoUtils.hash_string(long_string, "]sha256[")": assert len(md5_result) ==32[" assert len(sha256_result) ==64[""
        # 极大长度的短ID
        large_id = CryptoUtils.generate_short_id(1000)
    assert len(large_id) ==1000
        # 极大长度的令牌
        large_token = CryptoUtils.generate_token(500)
    assert len(large_token) ==1000  # 500 bytes = 1000 hex chars
    @patch("]]]src.utils.crypto_utils.secrets.token_hex[")": def test_generate_salt_secrets_fallback(self, mock_token_hex):"""
        "]""测试secrets模块异常时的处理"""
        mock_token_hex.side_effect = Exception("secrets error[")""""
        # 应该有某种回退机制或抛出异常
        with pytest.raises(Exception):
            CryptoUtils.generate_salt()
    @patch("]src.utils.crypto_utils.secrets.token_hex[")": def test_generate_token_secrets_fallback(self, mock_token_hex):"""
        "]""测试secrets模块异常时的处理"""
        mock_token_hex.side_effect = Exception("secrets error[")"]"""
        # 应该有某种回退机制或抛出异常
        with pytest.raises(Exception):
            CryptoUtils.generate_token()
            import bcrypt  # noqa: F401
            import bcrypt  # noqa: F401