"""
JWT认证管理器测试
JWT Auth Manager Tests

测试JWT认证系统的核心功能
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from src.security.jwt_auth import JWTAuthManager, TokenData


class TestJWTAuthManager:
    """JWT认证管理器测试类"""

    @pytest.fixture
    def auth_manager(self):
        """创建JWT认证管理器实例"""
        return JWTAuthManager(
            secret_key="test-secret-key-for-testing-only",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )

    def test_init_auth_manager(self, auth_manager):
        """测试JWT认证管理器初始化"""
        assert auth_manager.secret_key == "test-secret-key-for-testing-only"
        assert auth_manager.algorithm == "HS256"
        assert auth_manager.access_token_expire_minutes == 30
        assert auth_manager.refresh_token_expire_days == 7

    def test_create_access_token(self, auth_manager):
        """测试创建访问令牌"""
        data = {
            "sub": "123",
            "username": "testuser",
            "email": "test@example.com",
            "role": "user"
        }

        token = auth_manager.create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, auth_manager):
        """测试创建刷新令牌"""
        data = {"sub": "123"}

        token = auth_manager.create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_verify_access_token(self, auth_manager):
        """测试验证访问令牌"""
        data = {
            "sub": "123",
            "username": "testuser",
            "email": "test@example.com",
            "role": "admin"
        }

        token = auth_manager.create_access_token(data)
        token_data = await auth_manager.verify_token(token)

        assert isinstance(token_data, TokenData)
        assert token_data.user_id == 123
        assert token_data.username == "testuser"
        assert token_data.email == "test@example.com"
        assert token_data.role == "admin"
        assert token_data.token_type == "access"

    @pytest.mark.asyncio
    async def test_verify_refresh_token(self, auth_manager):
        """测试验证刷新令牌"""
        data = {"sub": "123"}

        token = auth_manager.create_refresh_token(data)
        token_data = await auth_manager.verify_token(token)

        assert token_data.user_id == 123
        assert token_data.token_type == "refresh"

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, auth_manager):
        """测试验证无效令牌"""
        invalid_token = "invalid.token.here"

        with pytest.raises(ValueError, match="Invalid token"):
            await auth_manager.verify_token(invalid_token)

    @pytest.mark.asyncio
    async def test_verify_expired_token(self, auth_manager):
        """测试验证过期令牌"""
        data = {"sub": "123"}

        # 创建一个已过期的令牌
        expired_delta = timedelta(seconds=-1)  # 已经过期
        token = auth_manager.create_access_token(data, expires_delta=expired_delta)

        with pytest.raises(ValueError, match="Token has expired"):
            await auth_manager.verify_token(token)

    def test_hash_password(self, auth_manager):
        """测试密码哈希"""
        password = "testpassword123"
        hashed = auth_manager.hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 50  # bcrypt哈希长度
        assert hashed != password

    def test_verify_password_correct(self, auth_manager):
        """测试密码验证（正确密码）"""
        password = "testpassword123"
        hashed = auth_manager.hash_password(password)

        assert auth_manager.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_manager):
        """测试密码验证（错误密码）"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = auth_manager.hash_password(password)

        assert auth_manager.verify_password(wrong_password, hashed) is False

    def test_generate_password_reset_token(self, auth_manager):
        """测试生成密码重置令牌"""
        email = "test@example.com"
        token = auth_manager.generate_password_reset_token(email)

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_valid(self, auth_manager):
        """测试验证密码重置令牌（有效）"""
        email = "test@example.com"
        token = auth_manager.generate_password_reset_token(email)

        result_email = await auth_manager.verify_password_reset_token(token)
        assert result_email == email

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_invalid(self, auth_manager):
        """测试验证密码重置令牌（无效）"""
        invalid_token = "invalid.reset.token"

        with pytest.raises(ValueError, match="Invalid password reset token"):
            await auth_manager.verify_password_reset_token(invalid_token)

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_expired(self, auth_manager):
        """测试验证密码重置令牌（过期）"""
        email = "test@example.com"

        # 手动创建已过期的重置令牌
        import jwt
        expired_delta = timedelta(seconds=-1)
        expire = datetime.utcnow() + expired_delta

        to_encode = {
            "email": email,
            "type": "password_reset",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": "test-jti"
        }

        expired_token = jwt.encode(to_encode, auth_manager.secret_key, algorithm=auth_manager.algorithm)

        with pytest.raises(ValueError, match="Password reset token has expired"):
            await auth_manager.verify_password_reset_token(expired_token)

    def test_validate_password_strength_valid(self, auth_manager):
        """测试密码强度验证（有效密码）"""
        valid_passwords = [
            "StrongP@ss123",
            "MySecurePassword2025!",
            "Test@Password123",
            "ComplexPassw0rd!"
        ]

        for password in valid_passwords:
            is_valid, errors = auth_manager.validate_password_strength(password)
            assert is_valid is True, f"Password '{password}' should be valid"
            assert len(errors) == 0, f"Password '{password}' should have no errors"

    def test_validate_password_strength_invalid(self, auth_manager):
        """测试密码强度验证（无效密码）"""
        test_cases = [
            ("short", ["密码长度至少8位"]),
            ("alllowercase", ["密码必须包含至少一个大写字母", "密码必须包含至少一个数字", "密码必须包含至少一个特殊字符"]),
            ("ALLUPPERCASE", ["密码必须包含至少一个小写字母", "密码必须包含至少一个数字", "密码必须包含至少一个特殊字符"]),
            ("NoNumbers!", ["密码必须包含至少一个数字"]),
            ("NoSpecial123", ["密码必须包含至少一个特殊字符"]),
            ("toolong" * 20, ["密码长度不能超过128位"])
        ]

        for password, expected_errors in test_cases:
            is_valid, errors = auth_manager.validate_password_strength(password)
            assert is_valid is False, f"Password '{password}' should be invalid"
            assert len(errors) > 0, f"Password '{password}' should have errors"

    def test_custom_expiry_times(self, auth_manager):
        """测试自定义过期时间"""
        data = {"sub": "123"}

        # 自定义访问令牌过期时间
        custom_expire = timedelta(minutes=60)
        token = auth_manager.create_access_token(data, expires_delta=custom_expire)

        # 验证令牌并检查过期时间
        token_data = asyncio.run(auth_manager.verify_token(token))

        # 检查过期时间是否在预期范围内（允许几秒误差）
        expected_expire = datetime.utcnow() + custom_expire
        actual_expire = token_data.exp
        time_diff = abs((actual_expire - expected_expire).total_seconds())

        assert time_diff < 5, f"Token expiry time mismatch: {time_diff} seconds difference"

    def test_token_contains_required_fields(self, auth_manager):
        """测试令牌包含必需字段"""
        data = {
            "sub": "123",
            "username": "testuser",
            "email": "test@example.com",
            "role": "user"
        }

        token = auth_manager.create_access_token(data)
        token_data = asyncio.run(auth_manager.verify_token(token))

        # 检查必需字段
        assert hasattr(token_data, 'user_id')
        assert hasattr(token_data, 'username')
        assert hasattr(token_data, 'email')
        assert hasattr(token_data, 'role')
        assert hasattr(token_data, 'token_type')
        assert hasattr(token_data, 'exp')
        assert hasattr(token_data, 'iat')
        assert hasattr(token_data, 'jti')

        # 检查字段值
        assert token_data.user_id == 123
        assert token_data.username == "testuser"
        assert token_data.email == "test@example.com"
        assert token_data.role == "user"
        assert token_data.token_type == "access"
        assert token_data.jti is not None
        assert len(token_data.jti) > 0


class TestJWTAuthManagerIntegration:
    """JWT认证管理器集成测试"""

    @pytest.fixture
    def auth_manager_with_redis(self):
        """创建带Redis的JWT认证管理器"""
        return JWTAuthManager(
            secret_key="test-secret-key",
            redis_url="redis://localhost:6379/1"  # 测试数据库
        )

    @pytest.mark.asyncio
    async def test_token_blacklist_without_redis(self):
        """测试没有Redis时的token黑名单功能"""
        auth_manager = JWTAuthManager(secret_key="test-key")

        data = {"sub": "123", "username": "testuser"}
        token = auth_manager.create_access_token(data)
        token_data = await auth_manager.verify_token(token)

        # 没有Redis时，黑名单功能应该静默失败
        await auth_manager.blacklist_token(token_data.jti, token_data.exp)

        # Token仍然应该有效
        token_data2 = await auth_manager.verify_token(token)
        assert token_data2.user_id == token_data.user_id

    @pytest.mark.asyncio
    async def test_close_connection(self, auth_manager_with_redis):
        """测试关闭Redis连接"""
        # 这个测试可能在Redis不可用时跳过
        try:
            await auth_manager_with_redis.close()
            # 如果没有异常，测试通过
        except Exception:
            # Redis不可用，跳过测试
            pytest.skip("Redis not available for testing")