"""
增强API安全系统测试
Enhanced API Security System Tests

测试JWT认证、权限控制、输入验证等安全功能。
"""

import pytest
from fastapi import HTTPException, status

from src.api.auth.enhanced_security import (
    PasswordManager,
    Permission,
    TokenManager,
    TokenResponse,
    UserCredentials,
    user_store,
)
from src.api.validation.input_validators import (
    BaseValidator,
    FileUploadValidator,
    SQLInjectionProtector,
    XSSProtector,
    comprehensive_security_check,
)


class TestPasswordManager:
    """密码管理器测试"""

    def test_hash_password(self):
        """测试密码加密"""
        password = "TestPassword123!"
        hashed = PasswordManager.hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 50  # bcrypt哈希长度
        assert hashed != password

    def test_verify_password_correct(self):
        """测试密码验证（正确密码）"""
        password = "TestPassword123!"
        hashed = PasswordManager.hash_password(password)

        assert PasswordManager.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试密码验证（错误密码）"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = PasswordManager.hash_password(password)

        assert PasswordManager.verify_password(wrong_password, hashed) is False

    def test_verify_password_invalid_hash(self):
        """测试密码验证（无效哈希）"""
        password = "TestPassword123!"
        invalid_hash = "invalid_hash"

        assert PasswordManager.verify_password(password, invalid_hash) is False


class TestTokenManager:
    """令牌管理器测试"""

    def test_create_access_token(self):
        """测试创建访问令牌"""
        data = {"sub": "testuser", "user_id": 1}
        token = TokenManager.create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 100  # JWT令牌长度

    def test_verify_valid_token(self):
        """测试验证有效令牌"""
        data = {"sub": "testuser", "user_id": 1}
        token = TokenManager.create_access_token(data)

        payload = TokenManager.verify_token(token, "access")
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 1
        assert payload["type"] == "access"

    def test_verify_invalid_token(self):
        """测试验证无效令牌"""
        invalid_token = "invalid.jwt.token"

        with pytest.raises(HTTPException) as exc_info:
            TokenManager.verify_token(invalid_token, "access")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_expired_token(self):
        """测试验证过期令牌"""
        from datetime import timedelta

        data = {"sub": "testuser", "user_id": 1}
        # 创建已过期的令牌
        token = TokenManager.create_access_token(
            data, expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(HTTPException) as exc_info:
            TokenManager.verify_token(token, "access")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserCredentials:
    """用户凭据模型测试"""

    def test_valid_credentials(self):
        """测试有效凭据"""
        credentials = UserCredentials(username="testuser", password="TestPassword123!")
        assert credentials.username == "testuser"
        assert credentials.password == "TestPassword123!"

    def test_invalid_username_too_short(self):
        """测试用户名过短"""
        with pytest.raises(ValueError) as exc_info:
            UserCredentials(username="ab", password="TestPassword123!")

        assert "min_length" in str(exc_info.value)

    def test_invalid_username_too_long(self):
        """测试用户名过长"""
        with pytest.raises(ValueError) as exc_info:
            UserCredentials(username="a" * 51, password="TestPassword123!")  # 51个字符

        assert "max_length" in str(exc_info.value)

    def test_invalid_password_no_uppercase(self):
        """测试密码没有大写字母"""
        with pytest.raises(ValueError) as exc_info:
            UserCredentials(username="testuser", password="testpassword123!")

        assert "大写字母" in str(exc_info.value)

    def test_invalid_password_no_lowercase(self):
        """测试密码没有小写字母"""
        with pytest.raises(ValueError) as exc_info:
            UserCredentials(username="testuser", password="TESTPASSWORD123!")

        assert "小写字母" in str(exc_info.value)

    def test_invalid_password_no_digit(self):
        """测试密码没有数字"""
        with pytest.raises(ValueError) as exc_info:
            UserCredentials(username="testuser", password="TestPassword!")

        assert "数字" in str(exc_info.value)

    def test_invalid_password_too_short(self):
        """测试密码过短"""
        with pytest.raises(ValueError) as exc_info:
            UserCredentials(username="testuser", password="Test1!")

        assert "min_length" in str(exc_info.value)


class TestBaseValidator:
    """基础验证器测试"""

    def test_sanitize_string(self):
        """测试字符串清理"""
        dirty_string = "<script>alert('xss')</script>"
        clean_string = BaseValidator.sanitize_string(dirty_string)

        assert "<script>" not in clean_string
        assert "alert" not in clean_string

    def test_validate_email_valid(self):
        """测试有效邮箱验证"""
        assert BaseValidator.validate_email("test@example.com") is True
        assert BaseValidator.validate_email("user.name+tag@domain.co.uk") is True

    def test_validate_email_invalid(self):
        """测试无效邮箱验证"""
        assert BaseValidator.validate_email("invalid-email") is False
        assert BaseValidator.validate_email("@domain.com") is False
        assert BaseValidator.validate_email("user@") is False

    def test_validate_username_valid(self):
        """测试有效用户名验证"""
        assert BaseValidator.validate_username("testuser") is True
        assert BaseValidator.validate_username("user_123") is True

    def test_validate_username_invalid(self):
        """测试无效用户名验证"""
        assert BaseValidator.validate_username("ab") is False  # 太短
        assert BaseValidator.validate_username("user@name") is False  # 非法字符
        assert BaseValidator.validate_username("a" * 51) is False  # 太长

    def test_validate_password_strength(self):
        """测试密码强度验证"""
        # 强密码
        is_valid, errors = BaseValidator.validate_password_strength("StrongPass123!")
        assert is_valid is True
        assert len(errors) == 0

        # 弱密码 - 没有大写字母
        is_valid, errors = BaseValidator.validate_password_strength("weakpass123!")
        assert is_valid is False
        assert any("大写字母" in error for error in errors)

        # 弱密码 - 常见密码
        is_valid, errors = BaseValidator.validate_password_strength("password123!")
        assert is_valid is False
        assert any("过于简单" in error for error in errors)


class TestSQLInjectionProtector:
    """SQL注入防护器测试"""

    def test_detect_sql_injection_union_select(self):
        """测试检测UNION SELECT注入"""
        malicious_input = "1' UNION SELECT * FROM users--"
        is_injection, message = SQLInjectionProtector.is_sql_injection(malicious_input)

        assert is_injection is True
        assert "UNION SELECT" in message

    def test_detect_sql_injection_drop_table(self):
        """测试检测DROP TABLE注入"""
        malicious_input = "'; DROP TABLE users;--"
        is_injection, message = SQLInjectionProtector.is_sql_injection(malicious_input)

        assert is_injection is True
        assert "DROP" in message

    def test_safe_input(self):
        """测试安全输入"""
        safe_input = "john.doe@example.com"
        is_injection, message = SQLInjectionProtector.is_sql_injection(safe_input)

        assert is_injection is False
        assert message == ""

    def test_sanitize_sql_input(self):
        """测试SQL输入清理"""
        malicious_input = "'; DROP TABLE users;--"
        sanitized = SQLInjectionProtector.sanitize_sql_input(malicious_input)

        assert "'" not in sanitized
        assert ";" not in sanitized
        assert "--" not in sanitized


class TestXSSProtector:
    """XSS防护器测试"""

    def test_detect_xss_script_tag(self):
        """测试检测script标签XSS"""
        malicious_input = "<script>alert('xss')</script>"
        is_xss, message = XSSProtector.is_xss_attack(malicious_input)

        assert is_xss is True
        assert "script" in message

    def test_detect_xss_javascript_protocol(self):
        """测试检测javascript协议XSS"""
        malicious_input = "javascript:alert('xss')"
        is_xss, message = XSSProtector.is_xss_attack(malicious_input)

        assert is_xss is True
        assert "javascript" in message

    def test_detect_xss_event_handler(self):
        """测试检测事件处理器XSS"""
        malicious_input = "<img onload='alert(\"xss\")'>"
        is_xss, message = XSSProtector.is_xss_attack(malicious_input)

        assert is_xss is True

    def test_safe_html_input(self):
        """测试安全HTML输入"""
        safe_input = "<p>This is safe content</p>"
        is_xss, message = XSSProtector.is_xss_attack(safe_input)

        assert is_xss is False
        assert message == ""

    def test_sanitize_html_input(self):
        """测试HTML输入清理"""
        malicious_input = "<script>alert('xss')</script><p>Safe content</p>"
        sanitized = XSSProtector.sanitize_html_input(malicious_input)

        assert "<script>" not in sanitized
        assert "alert" not in sanitized
        assert "Safe content" in sanitized


class TestFileUploadValidator:
    """文件上传验证器测试"""

    def test_validate_safe_image_extension(self):
        """测试验证安全图片扩展名"""
        is_valid, error = FileUploadValidator.validate_file_extension(
            "test.jpg", "image"
        )
        assert is_valid is True
        assert error == ""

    def test_validate_dangerous_extension(self):
        """测试验证危险扩展名"""
        is_valid, error = FileUploadValidator.validate_file_extension(
            "malware.exe", "image"
        )
        assert is_valid is False
        assert "不允许上传" in error

    def test_validate_unsupported_extension(self):
        """测试验证不支持的扩展名"""
        is_valid, error = FileUploadValidator.validate_file_extension(
            "test.xyz", "image"
        )
        assert is_valid is False
        assert "不支持的文件类型" in error

    def test_validate_file_size_valid(self):
        """测试验证有效文件大小"""
        is_valid, error = FileUploadValidator.validate_file_size(
            1024 * 1024, "image"
        )  # 1MB
        assert is_valid is True
        assert error == ""

    def test_validate_file_size_too_large(self):
        """测试验证文件过大"""
        is_valid, error = FileUploadValidator.validate_file_size(
            20 * 1024 * 1024, "image"
        )  # 20MB
        assert is_valid is False
        assert "超过限制" in error

    def test_validate_filename_safe(self):
        """测试验证安全文件名"""
        is_valid, error = FileUploadValidator.validate_filename("safe_file.jpg")
        assert is_valid is True
        assert error == ""

    def test_validate_filename_dangerous_chars(self):
        """测试验证危险字符文件名"""
        is_valid, error = FileUploadValidator.validate_filename("../../../etc/passwd")
        assert is_valid is False
        assert "非法字符" in error


class TestComprehensiveSecurityCheck:
    """综合安全检查测试"""

    def test_safe_input_data(self):
        """测试安全输入数据"""
        safe_data = {
            "username": "john_doe",
            "email": "john@example.com",
            "comment": "This is a safe comment",
        }

        result = comprehensive_security_check(safe_data)

        assert result["is_safe"] is True
        assert len(result["issues"]) == 0
        assert "sanitized_data" in result

    def test_malicious_input_data(self):
        """测试恶意输入数据"""
        malicious_data = {
            "username": "admin",
            "query": "1' UNION SELECT * FROM users--",
            "comment": "<script>alert('xss')</script>",
        }

        result = comprehensive_security_check(malicious_data)

        assert result["is_safe"] is False
        assert len(result["issues"]) >= 2  # SQL注入和XSS
        assert "sanitized_data" in result

    def test_mixed_input_data(self):
        """测试混合输入数据（部分安全，部分恶意）"""
        mixed_data = {
            "safe_field": "safe value",
            "dangerous_field": "'; DROP TABLE users;--",
        }

        result = comprehensive_security_check(mixed_data)

        assert result["is_safe"] is False
        assert len(result["issues"]) >= 1
        assert result["sanitized_data"]["safe_field"] == "safe value"


class TestUserStore:
    """用户存储测试"""

    def test_verify_valid_user(self):
        """测试验证有效用户"""
        user = user_store.verify_user("admin", "Admin123!")
        assert user is not None
        assert user["username"] == "admin"
        assert user["id"] == 1

    def test_verify_invalid_user(self):
        """测试验证无效用户"""
        user = user_store.verify_user("nonexistent", "wrongpassword")
        assert user is None

    def test_verify_wrong_password(self):
        """测试验证错误密码"""
        user = user_store.verify_user("admin", "wrongpassword")
        assert user is None

    def test_get_user(self):
        """测试获取用户"""
        user = user_store.get_user("admin")
        assert user is not None
        assert user["username"] == "admin"

    def test_get_nonexistent_user(self):
        """测试获取不存在的用户"""
        user = user_store.get_user("nonexistent")
        assert user is None


class TestTokenResponse:
    """令牌响应模型测试"""

    def test_valid_token_response(self):
        """测试有效令牌响应"""
        token_response = TokenResponse(
            access_token="sample_access_token",
            refresh_token="sample_refresh_token",
            token_type="bearer",
            expires_in=3600,
            scope="read write",
        )

        assert token_response.access_token == "sample_access_token"
        assert token_response.refresh_token == "sample_refresh_token"
        assert token_response.token_type == "bearer"
        assert token_response.expires_in == 3600
        assert token_response.scope == "read write"


# ============================================================================
# 集成测试
# ============================================================================


class TestSecurityIntegration:
    """安全系统集成测试"""

    def test_complete_authentication_flow(self):
        """测试完整认证流程"""
        # 1. 验证用户凭据
        user = user_store.verify_user("user", "User123!")
        assert user is not None

        # 2. 创建令牌
        from src.api.auth.enhanced_security import create_user_tokens

        tokens = create_user_tokens("user")
        assert isinstance(tokens, TokenResponse)

        # 3. 验证访问令牌
        payload = TokenManager.verify_token(tokens.access_token, "access")
        assert payload["sub"] == "user"

        # 4. 验证刷新令牌
        refresh_payload = TokenManager.verify_token(tokens.refresh_token, "refresh")
        assert refresh_payload["sub"] == "user"

    def test_permission_system(self):
        """测试权限系统"""
        # 检查权限常量
        assert Permission.READ == "read"
        assert Permission.WRITE == "write"
        assert Permission.ADMIN == "admin"
        assert Permission.PREDICT == "predict"

        # 验证用户权限
        admin_user = user_store.get_user("admin")
        assert Permission.ADMIN in admin_user["permissions"]
        assert Permission.PREDICT in admin_user["permissions"]

        regular_user = user_store.get_user("user")
        assert Permission.ADMIN not in regular_user["permissions"]
        assert Permission.PREDICT in regular_user["permissions"]

    def test_security_validation_pipeline(self):
        """测试安全验证管道"""
        # 模拟API请求数据
        request_data = {
            "username": "test_user",
            "email": "test@example.com",
            "search_query": "safe search term",
            "comment": "This is a safe comment",
        }

        # 1. 基础验证
        assert BaseValidator.validate_email(request_data["email"])
        assert BaseValidator.validate_username(request_data["username"])

        # 2. SQL注入检查
        for key, value in request_data.items():
            if isinstance(value, str):
                is_injection, _ = SQLInjectionProtector.is_sql_injection(value)
                assert not is_injection, f"SQL injection detected in {key}"

        # 3. XSS检查
        for key, value in request_data.items():
            if isinstance(value, str):
                is_xss, _ = XSSProtector.is_xss_attack(value)
                assert not is_xss, f"XSS attack detected in {key}"

        # 4. 综合安全检查
        result = comprehensive_security_check(request_data)
        assert result["is_safe"], f"Security issues found: {result['issues']}"
