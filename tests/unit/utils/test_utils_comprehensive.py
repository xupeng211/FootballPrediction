"""
测试工具模块
"""

from src.utils.crypto_utils import CryptoUtils
from src.utils.data_validator import DataValidator


class TestCryptoUtils:
    """测试加密工具类"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test_password"
        hashed = CryptoUtils.hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        # bcrypt哈希应该以$2b$开头
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """测试验证正确密码"""
        password = "test_password"
        hashed = CryptoUtils.hash_password(password)

        result = CryptoUtils.verify_password(password, hashed)
        assert result is True

    def test_verify_password_incorrect(self):
        """测试验证错误密码"""
        password = "test_password"
        wrong_password = "wrong_password"
        hashed = CryptoUtils.hash_password(password)

        result = CryptoUtils.verify_password(wrong_password, hashed)
        assert result is False

    def test_generate_salt(self):
        """测试生成盐值"""
        salt1 = CryptoUtils.generate_salt()
        salt2 = CryptoUtils.generate_salt()

        assert len(salt1) == 32  # 16 bytes * 2 (hex)
        assert len(salt2) == 32
        assert salt1 != salt2  # 每次生成的盐值应该不同

    def test_generate_token(self):
        """测试生成令牌"""
        token1 = CryptoUtils.generate_token()
        token2 = CryptoUtils.generate_token()

        # 默认长度32字节
        assert len(token1) == 64  # 32 bytes * 2 (hex)
        assert len(token2) == 64
        assert token1 != token2  # 每次生成的令牌应该不同

    def test_generate_token_custom_length(self):
        """测试生成自定义长度令牌"""
        token = CryptoUtils.generate_token(16)
        assert len(token) == 32  # 16 bytes * 2 (hex)

    def test_different_passwords_different_hashes(self):
        """测试不同密码产生不同哈希"""
        password1 = "password1"
        password2 = "password2"

        hash1 = CryptoUtils.hash_password(password1)
        hash2 = CryptoUtils.hash_password(password2)

        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """测试相同密码产生不同哈希（因为盐值不同）"""
        password = "same_password"

        hash1 = CryptoUtils.hash_password(password)
        hash2 = CryptoUtils.hash_password(password)

        # 即使是相同密码，由于盐值不同，哈希也应该不同
        assert hash1 != hash2

        # 但两个哈希都应该能验证原始密码
        assert CryptoUtils.verify_password(password, hash1)
        assert CryptoUtils.verify_password(password, hash2)


class TestDataValidator:
    """测试数据验证器类"""

    def test_is_valid_email_valid(self):
        """测试有效邮箱验证"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@test.com",
        ]

        for email in valid_emails:
            assert DataValidator.is_valid_email(email), f"应该识别 {email} 为有效邮箱"

    def test_is_valid_email_invalid(self):
        """测试无效邮箱验证"""
        invalid_emails = [
            "invalid.email",
            "@example.com",
            "user@",
            "user space@example.com",
            "",
            "user@domain.",
            "user@.com",
        ]

        for email in invalid_emails:
            assert not DataValidator.is_valid_email(
                email
            ), f"应该识别 {email} 为无效邮箱"

    def test_is_valid_url_valid(self):
        """测试有效URL验证"""
        valid_urls = [
            "http://example.com",
            "https://www.example.com",
            "https://example.com/path/to/page",
            "http://localhost:8080",
            "https://api.example.com/v1/data?param=value",
        ]

        for url in valid_urls:
            assert DataValidator.is_valid_url(url), f"应该识别 {url} 为有效URL"

    def test_is_valid_url_invalid(self):
        """测试无效URL验证"""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # 只允许http/https
            "",
            "http://",
            "https://",
            "example.com",  # 缺少协议
        ]

        for url in invalid_urls:
            assert not DataValidator.is_valid_url(url), f"应该识别 {url} 为无效URL"

    def test_sanitize_input(self):
        """测试输入清理"""
        test_cases = [
            ("  hello world  ", "hello world"),
            ("\t\n  text  \r\n", "text"),
            ("normal text", "normal text"),
            ("", ""),
            ("   ", ""),
        ]

        for input_text, expected in test_cases:
            result = DataValidator.sanitize_input(input_text)
            assert result == expected, f"清理 '{input_text}' 应该得到 '{expected}'"

    def test_sanitize_input_none(self):
        """测试清理None输入"""
        result = DataValidator.sanitize_input(None)
        assert result == ""

    def test_validator_integration(self):
        """测试验证器集成使用"""
        # 测试完整的验证流程
        user_data = {
            "email": "  user@example.com  ",
            "website": "  https://example.com  ",
        }

        # 清理和验证邮箱
        clean_email = DataValidator.sanitize_input(user_data["email"])
        assert DataValidator.is_valid_email(clean_email)

        # 清理和验证URL
        clean_url = DataValidator.sanitize_input(user_data["website"])
        assert DataValidator.is_valid_url(clean_url)
