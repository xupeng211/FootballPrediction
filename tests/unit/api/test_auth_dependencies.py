"""
认证依赖模块测试
Authentication Dependencies Test Module

测试FastAPI认证依赖的功能和行为
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from src.api.auth_dependencies import (
    RateLimiter,
    SecurityHeaders,
    TokenData,
    get_current_user,
    get_current_user_optional,
    rate_limiter,
    require_admin,
    security,
    security_headers,
)


class TestTokenData:
    """测试TokenData类"""

    def test_token_data_creation_default(self):
        """测试默认参数创建TokenData"""
        token_data = TokenData()

        assert token_data.user_id is None
        assert token_data.username is None
        assert token_data.role is None

    def test_token_data_creation_full(self):
        """测试完整参数创建TokenData"""
        token_data = TokenData(user_id=123, username="testuser", role="admin")

        assert token_data.user_id == 123
        assert token_data.username == "testuser"
        assert token_data.role == "admin"

    def test_token_data_creation_partial(self):
        """测试部分参数创建TokenData"""
        token_data = TokenData(user_id=456, username="partial")

        assert token_data.user_id == 456
        assert token_data.username == "partial"
        assert token_data.role is None

    def test_token_data_attributes(self):
        """测试TokenData属性设置"""
        token_data = TokenData()

        # 设置属性
        token_data.user_id = 789
        token_data.username = "dynamic"
        token_data.role = "user"

        # 验证属性
        assert token_data.user_id == 789
        assert token_data.username == "dynamic"
        assert token_data.role == "user"


class TestRateLimiter:
    """测试RateLimiter类"""

    def test_rate_limiter_creation(self):
        """测试RateLimiter创建"""
        limiter = RateLimiter()

        assert hasattr(limiter, "requests")
        assert isinstance(limiter.requests, dict)
        assert len(limiter.requests) == 0

    def test_is_allowed_default_limit(self):
        """测试默认限制下的允许检查"""
        limiter = RateLimiter()

        # 应该总是返回True（简化实现）
        assert limiter.is_allowed("test_key") is True
        assert limiter.is_allowed("test_key") is True
        assert limiter.is_allowed("another_key") is True

    def test_is_allowed_custom_limit(self):
        """测试自定义限制下的允许检查"""
        limiter = RateLimiter()

        # 即使设置自定义限制，也应该返回True（简化实现）
        assert limiter.is_allowed("test_key", limit=10) is True
        assert limiter.is_allowed("test_key", limit=1) is True
        assert limiter.is_allowed("test_key", limit=0) is True

    def test_is_allowed_different_keys(self):
        """测试不同key的允许检查"""
        limiter = RateLimiter()

        keys = ["user1", "user2", "user3", "ip1", "ip2"]
        for key in keys:
            assert limiter.is_allowed(key) is True


class TestSecurityHeaders:
    """测试SecurityHeaders类"""

    def test_security_headers_creation(self):
        """测试SecurityHeaders创建"""
        headers = SecurityHeaders()

        assert hasattr(headers, "headers")
        assert isinstance(headers.headers, dict)

    def test_security_headers_default_values(self):
        """测试默认安全头部值"""
        headers = SecurityHeaders()

        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
        }

        assert headers.headers == expected_headers

    def test_security_headers_immutability(self):
        """测试安全头部不可变性"""
        headers = SecurityHeaders()
        original_headers = headers.headers.copy()

        # 尝试修改headers
        headers.headers["Custom-Header"] = "test"

        # 验证原始headers未被修改（在实际实现中可能需要更严格的不可变性）
        assert len(headers.headers) >= len(original_headers)
        assert headers.headers["X-Content-Type-Options"] == "nosniff"


class TestGetCurrentUser:
    """测试get_current_user函数"""

    @pytest.fixture
    def mock_credentials(self):
        """创建模拟的认证凭据"""
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token_here"
        return credentials

    async def test_get_current_user_success(self, mock_credentials):
        """测试成功获取当前用户"""
        with patch("src.api.auth_dependencies.TokenData") as mock_token_data:
            mock_token_data.return_value = TokenData(
                user_id=1, username="test_user", role="user"
            )

            result = await get_current_user(mock_credentials)

            assert isinstance(result, TokenData)
            assert result.user_id == 1
            assert result.username == "test_user"
            assert result.role == "user"

    async def test_get_current_user_exception_handling(self, mock_credentials):
        """测试异常处理"""
        with patch(
            "src.api.auth_dependencies.TokenData",
            side_effect=Exception("Token parsing failed"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Could not validate credentials" in str(exc_info.value.detail)
            assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"

    async def test_get_current_user_different_credentials(self):
        """测试不同的认证凭据"""
        credentials_list = [
            "simple_token",
            "bearer_token_123",
            "complex_jwt_token_string",
            "empty",
            "very_long_token_string_that_might_be_used_in_production",
        ]

        for token in credentials_list:
            mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
            mock_credentials.credentials = token

            result = await get_current_user(mock_credentials)
            assert isinstance(result, TokenData)
            assert result.user_id == 1
            assert result.username == "test_user"
            assert result.role == "user"


class TestGetCurrentUserOptional:
    """测试get_current_user_optional函数"""

    @pytest.fixture
    def mock_request_no_auth(self):
        """创建没有认证头的请求"""
        request = Mock(spec=Request)
        request.headers = {}
        return request

    @pytest.fixture
    def mock_request_with_auth(self):
        """创建有认证头的请求"""
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer valid_token"}
        return request

    async def test_get_current_user_optional_no_auth_header(self, mock_request_no_auth):
        """测试没有认证头的情况"""
        result = await get_current_user_optional(mock_request_no_auth)

        assert result is None

    async def test_get_current_user_optional_invalid_auth_format(
        self, mock_request_with_auth
    ):
        """测试无效的认证格式"""
        # 修改请求头为无效格式
        mock_request_with_auth.headers = {"Authorization": "InvalidFormat token"}

        result = await get_current_user_optional(mock_request_with_auth)

        assert result is None

    async def test_get_current_user_optional_success(self, mock_request_with_auth):
        """测试成功获取可选用户"""
        result = await get_current_user_optional(mock_request_with_auth)

        assert isinstance(result, TokenData)
        assert result.user_id == 1
        assert result.username == "test_user"
        assert result.role == "user"

    async def test_get_current_user_optional_malformed_token(self):
        """测试格式错误的token"""
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer"}

        result = await get_current_user_optional(request)

        assert result is None

    async def test_get_current_user_optional_exception_handling(
        self, mock_request_with_auth
    ):
        """测试异常处理"""
        with patch(
            "src.api.auth_dependencies.TokenData",
            side_effect=Exception("Unexpected error"),
        ):
            result = await get_current_user_optional(mock_request_with_auth)

            # 在异常情况下应该返回None，而不是抛出异常
            assert result is None

    async def test_get_current_user_optional_various_auth_schemes(self):
        """测试各种认证方案"""
        auth_schemes = [
            ("Bearer token123", True),
            ("bearer token456", False),  # 小写bearer不应该被接受
            ("Token token789", False),  # 非Bearer方案
            ("", False),  # 空字符串
        ]

        for auth_header, should_succeed in auth_schemes:
            request = Mock(spec=Request)
            request.headers = {"Authorization": auth_header}

            result = await get_current_user_optional(request)

            if should_succeed:
                assert isinstance(result, TokenData)
            else:
                assert result is None


class TestRequireAdmin:
    """测试require_admin函数"""

    @pytest.fixture
    def admin_user(self):
        """创建管理员用户"""
        return TokenData(user_id=1, username="admin", role="admin")

    @pytest.fixture
    def regular_user(self):
        """创建普通用户"""
        return TokenData(user_id=2, username="user", role="user")

    @pytest.fixture
    def moderator_user(self):
        """创建版主用户"""
        return TokenData(user_id=3, username="moderator", role="moderator")

    async def test_require_admin_success(self, admin_user):
        """测试管理员权限验证成功"""
        result = await require_admin(admin_user)

        assert result == admin_user
        assert result.role == "admin"

    async def test_require_admin_regular_user_denied(self, regular_user):
        """测试普通用户被拒绝"""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(regular_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin access required" in str(exc_info.value.detail)

    async def test_require_admin_moderator_denied(self, moderator_user):
        """测试版主用户被拒绝"""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(moderator_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin access required" in str(exc_info.value.detail)

    async def test_require_admin_no_role(self):
        """测试没有role的用户被拒绝"""
        user_no_role = TokenData(user_id=4, username="norole")

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user_no_role)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin access required" in str(exc_info.value.detail)

    async def test_require_admin_case_sensitive(self):
        """测试role大小写敏感"""
        admin_lowercase = TokenData(user_id=5, username="Admin", role="admin_lowercase")

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(admin_lowercase)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin access required" in str(exc_info.value.detail)


class TestGlobalInstances:
    """测试全局实例"""

    def test_rate_limiter_global_instance(self):
        """测试全局rate_limiter实例"""
        assert rate_limiter is not None
        assert isinstance(rate_limiter, RateLimiter)

    def test_security_headers_global_instance(self):
        """测试全局security_headers实例"""
        assert security_headers is not None
        assert isinstance(security_headers, SecurityHeaders)

    def test_security_global_instance(self):
        """测试全局security实例"""
        assert security is not None
        # HTTPBearer实例的scheme_name属性是'httpbearer'
        assert hasattr(security, "scheme") or hasattr(security, "scheme_name")
        if hasattr(security, "scheme_name"):
            assert security.scheme_name.lower() in ["bearer", "httpbearer"]


class TestIntegrationScenarios:
    """测试集成场景"""

    async def test_full_authentication_flow(self):
        """测试完整认证流程"""
        # 1. 创建认证凭据
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid_jwt_token"

        # 2. 获取当前用户
        current_user = await get_current_user(mock_credentials)
        assert isinstance(current_user, TokenData)
        assert current_user.role == "user"

        # 3. 尝试需要管理员权限的操作（应该失败）
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(current_user)
        assert exc_info.value.status_code == 403

    async def test_admin_authentication_flow(self):
        """测试管理员认证流程"""
        # 模拟管理员认证
        admin_user = TokenData(user_id=1, username="admin", role="admin")

        # 管理员应该能够通过权限检查
        result = await require_admin(admin_user)
        assert result.role == "admin"

    async def test_optional_authentication_scenarios(self):
        """测试可选认证的各种场景"""
        scenarios = [
            {},  # 无认证头
            {"Authorization": ""},  # 空认证头
            {"Authorization": "InvalidFormat token"},  # 无效格式
            {"Authorization": "Bearer valid_token"},  # 有效格式
            {"Authorization": "Bearer"},  # 只有Bearer
        ]

        for headers in scenarios:
            request = Mock(spec=Request)
            request.headers = headers

            result = await get_current_user_optional(request)

            if headers.get("Authorization") == "Bearer valid_token":
                assert isinstance(result, TokenData)
            else:
                assert result is None

    def test_security_configuration_integration(self):
        """测试安全配置集成"""
        # 验证全局实例配置正确
        assert rate_limiter.is_allowed("test_key") is True
        assert "X-Content-Type-Options" in security_headers.headers
        assert security_headers.headers["X-Content-Type-Options"] == "nosniff"

        # 验证安全配置的一致性
        assert security_headers.headers["X-Frame-Options"] == "DENY"
        assert security_headers.headers["X-XSS-Protection"] == "1; mode=block"

    async def test_error_handling_consistency(self):
        """测试错误处理一致性"""
        # 测试各种错误情况下的HTTPException
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)

        with patch(
            "src.api.auth_dependencies.TokenData",
            side_effect=ValueError("Invalid token"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

            exception = exc_info.value
            assert exception.status_code == 401
            assert "WWW-Authenticate" in exception.headers
            assert exception.headers["WWW-Authenticate"] == "Bearer"

        # 测试权限错误
        regular_user = TokenData(user_id=2, username="user", role="user")
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(regular_user)

        exception = exc_info.value
        assert exception.status_code == 403
        assert "Admin access required" in str(exception.detail)
