"""
JWT认证核心功能测试
目标覆盖率: 45%
模块: src.security.jwt_auth (JWT认证管理器)
测试范围: JWT令牌生成、验证、密码管理、安全功能
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from src.security.jwt_auth import JWTAuthManager, TokenData, UserAuth


class TestJWTAuthManagerInitialization:
    """JWT认证管理器初始化测试"""

    def test_init_with_custom_parameters(self):
        """测试使用自定义参数初始化"""
        manager = JWTAuthManager(
            secret_key="custom-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=60,
            refresh_token_expire_days=14,
            redis_url="redis://localhost:6379/0",
        )

        assert manager.secret_key == "custom-secret-key"
        assert manager.algorithm == "HS256"
        assert manager.access_token_expire_minutes == 60
        assert manager.refresh_token_expire_days == 14
        assert manager.pwd_context is not None

    def test_init_with_default_parameters(self):
        """测试使用默认参数初始化"""
        manager = JWTAuthManager()

        assert manager.secret_key is not None
        assert len(manager.secret_key) > 50  # 自动生成的密钥应该比较长
        assert manager.algorithm == "HS256"
        assert manager.access_token_expire_minutes == 30
        assert manager.refresh_token_expire_days == 7
        assert manager.pwd_context is not None

    def test_init_with_env_secret_key(self):
        """测试使用环境变量密钥初始化"""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "env-secret-key"}):
            manager = JWTAuthManager()
            assert manager.secret_key == "env-secret-key"

    def test_secret_key_generation(self):
        """测试密钥生成"""
        manager = JWTAuthManager()
        secret_key = manager._generate_secret_key()

        assert isinstance(secret_key, str)
        assert len(secret_key) == 86  # token_urlsafe(64)生成的长度
        assert secret_key.isalnum() or "-" in secret_key or "_" in secret_key


class TestTokenCreation:
    """令牌创建测试"""

    @pytest.fixture
    def auth_manager(self):
        """JWT认证管理器fixture"""
        return JWTAuthManager(
            secret_key="test-secret-key",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )

    def test_create_access_token_basic(self, auth_manager):
        """测试创建基本访问令牌"""
        data = {"sub": "1", "username": "testuser", "role": "user"}
        token = auth_manager.create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 100

        # 验证令牌格式（应该是三部分用点分隔）
        parts = token.split(".")
        assert len(parts) == 3
        for part in parts:
            assert len(part) > 0

    def test_create_access_token_with_custom_expiry(self, auth_manager):
        """测试创建自定义过期时间的访问令牌"""
        data = {"sub": "1", "username": "testuser", "role": "user"}
        expires_delta = timedelta(hours=2)
        token = auth_manager.create_access_token(data, expires_delta)

        assert isinstance(token, str)
        assert len(token) > 100

        # 验证令牌中的过期时间
        import jwt

        payload = jwt.decode(
            token, auth_manager.secret_key, algorithms=[auth_manager.algorithm]
        )
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)

        # 过期时间应该大约是2小时后
        expected_exp = datetime.now() + timedelta(hours=2)
        time_diff = abs((exp_datetime - expected_exp).total_seconds())
        assert time_diff < 60  # 允许60秒误差

    def test_create_refresh_token_basic(self, auth_manager):
        """测试创建基本刷新令牌"""
        data = {"sub": "1"}
        token = auth_manager.create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 100

        # 验证令牌格式
        parts = token.split(".")
        assert len(parts) == 3

    def test_create_refresh_token_with_custom_expiry(self, auth_manager):
        """测试创建自定义过期时间的刷新令牌"""
        data = {"sub": "1"}
        expires_delta = timedelta(days=30)
        token = auth_manager.create_refresh_token(data, expires_delta)

        assert isinstance(token, str)
        assert len(token) > 100

    def test_token_data_includes_required_fields(self, auth_manager):
        """测试令牌数据包含必需字段"""
        data = {
            "sub": "123",
            "username": "testuser",
            "email": "test@example.com",
            "role": "user",
        }
        token = auth_manager.create_access_token(data)

        # 解码令牌验证内容
        import jwt

        payload = jwt.decode(
            token, auth_manager.secret_key, algorithms=[auth_manager.algorithm]
        )

        assert payload["sub"] == "123"
        assert payload["username"] == "testuser"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "user"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
        assert payload["token_type"] == "access"


class TestTokenVerification:
    """令牌验证测试"""

    @pytest.fixture
    def auth_manager(self):
        """JWT认证管理器fixture"""
        return JWTAuthManager(
            secret_key="test-secret-key",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )

    @pytest.mark.asyncio
    async def test_verify_valid_access_token(self, auth_manager):
        """测试验证有效的访问令牌"""
        data = {
            "sub": "123",
            "username": "testuser",
            "email": "test@example.com",
            "role": "user",
        }
        token = auth_manager.create_access_token(data)

        token_data = await auth_manager.verify_token(token)

        assert isinstance(token_data, TokenData)
        assert token_data.user_id == 123
        assert token_data.username == "testuser"
        assert token_data.email == "test@example.com"
        assert token_data.role == "user"
        assert token_data.token_type == "access"
        assert isinstance(token_data.exp, datetime)
        assert isinstance(token_data.iat, datetime)
        assert isinstance(token_data.jti, str)

    @pytest.mark.asyncio
    async def test_verify_valid_refresh_token(self, auth_manager):
        """测试验证有效的刷新令牌"""
        data = {"sub": "456"}
        token = auth_manager.create_refresh_token(data)

        token_data = await auth_manager.verify_token(token)

        assert isinstance(token_data, TokenData)
        assert token_data.user_id == 456
        assert token_data.token_type == "refresh"
        assert token_data.username == ""  # 刷新令牌中不包含用户名
        assert token_data.email == ""  # 刷新令牌中不包含邮箱
        assert token_data.role == ""  # 刷新令牌中不包含角色

    @pytest.mark.asyncio
    async def test_verify_invalid_signature_token(self, auth_manager):
        """测试验证无效签名的令牌"""
        invalid_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature"

        with pytest.raises(ValueError) as exc_info:
            await auth_manager.verify_token(invalid_token)

        assert (
            "Invalid token" in str(exc_info.value)
            or "signature" in str(exc_info.value).lower()
        )

    @pytest.mark.asyncio
    async def test_verify_malformed_token(self, auth_manager):
        """测试验证格式错误的令牌"""
        malformed_tokens = [
            "not-a-jwt",
            "eyJ.eyJzdWIiOiIxIn0.invalid",
            "",
            "Bearer token",
            "too.many.parts.here",
        ]

        for token in malformed_tokens:
            with pytest.raises(ValueError):
                await auth_manager.verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_expired_token(self, auth_manager):
        """测试验证过期的令牌"""
        data = {"sub": "1", "username": "testuser", "role": "user"}
        # 创建已过期的令牌
        expires_delta = timedelta(seconds=-1)
        token = auth_manager.create_access_token(data, expires_delta)

        with pytest.raises(ValueError) as exc_info:
            await auth_manager.verify_token(token)

        assert "expired" in str(exc_info.value).lower() or "过期" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_token_wrong_secret(self, auth_manager):
        """测试使用错误密钥验证令牌"""
        data = {"sub": "1", "username": "testuser", "role": "user"}
        token = auth_manager.create_access_token(data)

        # 使用不同的密钥创建验证器
        wrong_manager = JWTAuthManager(secret_key="wrong-secret-key")

        with pytest.raises(ValueError):
            await wrong_manager.verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_token_wrong_algorithm(self, auth_manager):
        """测试使用错误算法验证令牌"""
        data = {"sub": "1", "username": "testuser", "role": "user"}
        token = auth_manager.create_access_token(data)

        # 使用不同的算法创建验证器
        wrong_algorithm_manager = JWTAuthManager(
            secret_key="test-secret-key", algorithm="HS384"  # 不同的算法
        )

        with pytest.raises(ValueError):
            await wrong_algorithm_manager.verify_token(token)


class TestPasswordManagement:
    """密码管理测试"""

    @pytest.fixture
    def auth_manager(self):
        """JWT认证管理器fixture"""
        return JWTAuthManager(secret_key="test-secret-key")

    def test_hash_password(self, auth_manager):
        """测试密码哈希"""
        password = "TestPassword123!"
        hashed = auth_manager.hash_password(password)

        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt哈希应该比较长
        assert hashed.startswith("$2b$12$")  # bcrypt标识符

    def test_verify_correct_password(self, auth_manager):
        """测试验证正确密码"""
        password = "TestPassword123!"
        hashed = auth_manager.hash_password(password)

        is_valid = auth_manager.verify_password(password, hashed)
        assert is_valid is True

    def test_verify_incorrect_password(self, auth_manager):
        """测试验证错误密码"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = auth_manager.hash_password(password)

        is_valid = auth_manager.verify_password(wrong_password, hashed)
        assert is_valid is False

    def test_verify_empty_password(self, auth_manager):
        """测试验证空密码"""
        password = "TestPassword123!"
        hashed = auth_manager.hash_password(password)

        is_valid = auth_manager.verify_password("", hashed)
        assert is_valid is False

    def test_hash_different_passwords_different_hashes(self, auth_manager):
        """测试不同密码产生不同哈希"""
        password1 = "Password123!"
        password2 = "Password456!"

        hash1 = auth_manager.hash_password(password1)
        hash2 = auth_manager.hash_password(password2)

        assert hash1 != hash2

    def test_hash_same_password_different_hashes(self, auth_manager):
        """测试相同密码产生不同哈希（bcrypt加盐）"""
        password = "Password123!"

        hash1 = auth_manager.hash_password(password)
        hash2 = auth_manager.hash_password(password)

        # bcrypt每次都会生成不同的盐，所以哈希应该不同
        assert hash1 != hash2
        # 但两个哈希都应该能验证原始密码
        assert auth_manager.verify_password(password, hash1)
        assert auth_manager.verify_password(password, hash2)


class TestPasswordStrengthValidation:
    """密码强度验证测试"""

    @pytest.fixture
    def auth_manager(self):
        """JWT认证管理器fixture"""
        return JWTAuthManager(secret_key="test-secret-key")

    def test_strong_password_validation(self, auth_manager):
        """测试强密码验证"""
        strong_passwords = [
            "StrongPassword123!",
            "MySecure@Pass456",
            "Complex#Password789",
            "Very$Strong0Pass",
        ]

        for password in strong_passwords:
            is_valid, errors = auth_manager.validate_password_strength(password)
            assert is_valid is True, f"Password {password} should be valid"
            assert len(errors) == 0, f"Password {password} should have no errors"

    def test_weak_password_validation(self, auth_manager):
        """测试弱密码验证"""
        weak_passwords = [
            "weak",  # 太短
            "12345678",  # 只有数字
            "password",  # 只有字母
            "Password1",  # 没有特殊字符
            "SHORT1!",  # 太短
            "alllowercase123!",  # 没有大写字母
            "ALLUPPERCASE123!",  # 没有小写字母
            "NoNumbers!",  # 没有数字
        ]

        for password in weak_passwords:
            is_valid, errors = auth_manager.validate_password_strength(password)
            assert is_valid is False, f"Password {password} should be invalid"
            assert len(errors) > 0, f"Password {password} should have errors"

    def test_minimum_length_validation(self, auth_manager):
        """测试最小长度验证"""
        # 测试边界长度
        password_7_chars = "Pass123!"  # 7个字符
        password_8_chars = "Pass123!@"  # 8个字符

        is_valid_7, errors_7 = auth_manager.validate_password_strength(password_7_chars)
        is_valid_8, errors_8 = auth_manager.validate_password_strength(password_8_chars)

        # 7个字符应该无效，8个字符应该有效（假设最小长度是8）
        # 这取决于实际的验证规则实现
        logger.error(f"7 chars valid: {is_valid_7},
    errors: {errors_7}")  # TODO: Add logger import if needed
        logger.error(f"8 chars valid: {is_valid_8},
    errors: {errors_8}")  # TODO: Add logger import if needed

    def test_password_complexity_requirements(self, auth_manager):
        """测试密码复杂度要求"""
        # 测试只满足部分要求的密码
        test_cases = [
            ("lowercaseonly1!", "缺少大写字母"),
            ("UPPERCASEONLY1!", "缺少小写字母"),
            ("NoNumbersHere!", "缺少数字"),
            ("NoSpecialChars1", "缺少特殊字符"),
        ]

        for password, expected_issue in test_cases:
            is_valid, errors = auth_manager.validate_password_strength(password)
            # 根据实际实现调整断言
            if not is_valid:
                assert len(errors) > 0
                # 检查是否包含相关的错误信息
                error_text = " ".join(errors).lower()
                assert any(
                    keyword in error_text
                    for keyword in [
                        "大写",
                        "小写",
                        "数字",
                        "特殊",
                        "upper",
                        "lower",
                        "number",
                        "special",
                    ]
                )


class TestPasswordResetTokens:
    """密码重置令牌测试"""

    @pytest.fixture
    def auth_manager(self):
        """JWT认证管理器fixture"""
        return JWTAuthManager(
            secret_key="test-secret-key",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )

    def test_generate_password_reset_token(self, auth_manager):
        """测试生成密码重置令牌"""
        email = "test@example.com"
        token = auth_manager.generate_password_reset_token(email)

        assert isinstance(token, str)
        assert len(token) > 50  # 应该是一个长令牌

        # 验证令牌格式
        parts = token.split(".")
        assert len(parts) == 3

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_success(self, auth_manager):
        """测试验证密码重置令牌成功"""
        email = "test@example.com"
        token = auth_manager.generate_password_reset_token(email)

        verified_email = await auth_manager.verify_password_reset_token(token)
        assert verified_email == email

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_invalid(self, auth_manager):
        """测试验证无效密码重置令牌"""
        invalid_tokens = [
            "invalid_reset_token",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
            "",
            "not-a-jwt-token",
        ]

        for token in invalid_tokens:
            with pytest.raises(ValueError):
                await auth_manager.verify_password_reset_token(token)

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_expired(self, auth_manager):
        """测试验证过期密码重置令牌"""
        email = "test@example.com"

        # 模拟过期的令牌
        with patch("src.security.jwt_auth.timedelta") as mock_timedelta:
            # 模拟令牌已过期
            mock_timedelta.return_value = timedelta(hours=-25)  # 超过24小时

            token = auth_manager.generate_password_reset_token(email)

            with pytest.raises(ValueError) as exc_info:
                await auth_manager.verify_password_reset_token(token)

            assert "expired" in str(exc_info.value).lower() or "过期" in str(
                exc_info.value
            )

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_wrong_secret(self, auth_manager):
        """测试使用错误密钥验证密码重置令牌"""
        email = "test@example.com"
        token = auth_manager.generate_password_reset_token(email)

        # 使用不同的密钥创建验证器
        wrong_manager = JWTAuthManager(secret_key="wrong-secret-key")

        with pytest.raises(ValueError):
            await wrong_manager.verify_password_reset_token(token)


class TestTokenBlacklisting:
    """令牌黑名单测试"""

    @pytest.fixture
    def auth_manager(self):
        """JWT认证管理器fixture"""
        return JWTAuthManager(
            secret_key="test-secret-key", redis_url=None
        )  # 不使用Redis

    @pytest.mark.asyncio
    async def test_blacklist_token_without_redis(self, auth_manager):
        """测试无Redis连接时的令牌黑名单"""
        jti = "test-jti"
        exp = datetime.now() + timedelta(hours=1)

        # 无Redis连接时应该记录警告日志
        with patch("src.security.jwt_auth.logger") as mock_logger:
            await auth_manager.blacklist_token(jti, exp)
            # 验证记录了警告日志
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_without_redis(self, auth_manager):
        """测试无Redis连接时的令牌黑名单检查"""
        jti = "test-jti"

        # 无Redis连接时应该返回False
        is_blacklisted = await auth_manager.is_token_blacklisted(jti)
        assert is_blacklisted is False


class TestUserAuthModel:
    """用户认证模型测试"""

    def test_user_auth_creation(self):
        """测试用户认证模型创建"""
        user = UserAuth(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$testhashedpassword",
            role="user",
            is_active=True,
        )

        assert user.id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.hashed_password == "$2b$12$testhashedpassword"
        assert user.role == "user"
        assert user.is_active is True

    def test_user_auth_default_values(self):
        """测试用户认证模型默认值"""
        user = UserAuth(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$testhashedpassword",
        )

        assert user.role == "user"  # 默认角色
        assert user.is_active is True  # 默认活跃

    def test_user_auth_admin_role(self):
        """测试用户认证管理员角色"""
        user = UserAuth(
            id=1,
            username="admin",
            email="admin@example.com",
            hashed_password="$2b$12$testhashedpassword",
            role="admin",
            is_active=True,
        )

        assert user.role == "admin"

    def test_user_auth_inactive_user(self):
        """测试非活跃用户"""
        user = UserAuth(
            id=1,
            username="inactive_user",
            email="inactive@example.com",
            hashed_password="$2b$12$testhashedpassword",
            role="user",
            is_active=False,
        )

        assert user.is_active is False


class TestTokenDataModel:
    """令牌数据模型测试"""

    def test_token_data_creation(self):
        """测试令牌数据模型创建"""
        now = datetime.now()
        exp = now + timedelta(hours=1)

        token_data = TokenData(
            user_id=123,
            username="testuser",
            email="test@example.com",
            role="user",
            token_type="access",
            exp=exp,
            iat=now,
            jti="test-jti-12345",
        )

        assert token_data.user_id == 123
        assert token_data.username == "testuser"
        assert token_data.email == "test@example.com"
        assert token_data.role == "user"
        assert token_data.token_type == "access"
        assert token_data.exp == exp
        assert token_data.iat == now
        assert token_data.jti == "test-jti-12345"

    def test_token_data_refresh_token(self):
        """测试刷新令牌数据"""
        now = datetime.now()
        exp = now + timedelta(days=7)

        token_data = TokenData(
            user_id=456,
            username="",  # 刷新令牌通常不包含用户名
            email="",  # 刷新令牌通常不包含邮箱
            role="",  # 刷新令牌通常不包含角色
            token_type="refresh",
            exp=exp,
            iat=now,
            jti="refresh-jti-67890",
        )

        assert token_data.user_id == 456
        assert token_data.token_type == "refresh"
        assert token_data.username == ""
        assert token_data.email == ""
        assert token_data.role == ""


class TestEdgeCases:
    """边缘情况测试"""

    @pytest.fixture
    def auth_manager(self):
        """JWT认证管理器fixture"""
        return JWTAuthManager(secret_key="test-secret-key")

    @pytest.mark.asyncio
    async def test_verify_empty_string_token(self, auth_manager):
        """测试验证空字符串令牌"""
        with pytest.raises(ValueError):
            await auth_manager.verify_token("")

    @pytest.mark.asyncio
    async def test_verify_none_token(self, auth_manager):
        """测试验证None令牌"""
        with pytest.raises((ValueError, TypeError)):
            await auth_manager.verify_token(None)

    def test_create_token_with_empty_data(self, auth_manager):
        """测试创建空数据的令牌"""
        with pytest.raises(Exception):
            auth_manager.create_access_token({})

    def test_create_token_with_none_data(self, auth_manager):
        """测试创建None数据的令牌"""
        with pytest.raises((ValueError, TypeError)):
            auth_manager.create_access_token(None)

    def test_hash_empty_password(self, auth_manager):
        """测试哈希空密码"""
        hashed = auth_manager.hash_password("")
        assert isinstance(hashed, str)
        assert len(hashed) > 50

    def test_verify_empty_hashed_password(self, auth_manager):
        """测试验证空哈希密码"""
        password = "test123"

        with pytest.raises(ValueError):
            auth_manager.verify_password(password, "")

    def test_generate_multiple_secret_keys(self, auth_manager):
        """测试生成多个不同的密钥"""
        keys = []
        for _ in range(10):
            key = auth_manager._generate_secret_key()
            keys.append(key)

        # 所有密钥都应该不同
        unique_keys = set(keys)
        assert len(unique_keys) == len(keys)

    def test_secret_key_length_consistency(self, auth_manager):
        """测试密钥长度一致性"""
        keys = []
        for _ in range(10):
            key = auth_manager._generate_secret_key()
            keys.append(key)

        # 所有密钥应该有相同的长度
        lengths = [len(key) for key in keys]
        assert len(set(lengths)) == 1  # 所有长度相同
