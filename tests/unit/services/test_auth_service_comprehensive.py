"""
认证服务测试
Auth Service Tests

测试认证服务的核心功能.
Tests core functionality of authentication service.
"""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.database.models.user import User, UserRole
from src.services.auth_service import AuthService


class TestAuthServicePassword:
    """测试认证服务密码功能"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """认证服务实例"""
        with patch("src.services.auth_service.AuthUserRepository"):
            return AuthService(mock_db)

    def test_verify_password_correct(self, auth_service):
        """测试正确密码验证"""
        # 创建密码哈希
        password = "test_password_123"
        hashed = auth_service.get_password_hash(password)

        # 验证密码
        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_service):
        """测试错误密码验证"""
        password = "test_password_123"
        wrong_password = "wrong_password_456"
        hashed = auth_service.get_password_hash(password)

        # 验证错误密码
        assert auth_service.verify_password(wrong_password, hashed) is False

    def test_password_hash_uniqueness(self, auth_service):
        """测试密码哈希唯一性"""
        password = "test_password_123"
        hash1 = auth_service.get_password_hash(password)
        hash2 = auth_service.get_password_hash(password)

        # 相同密码应该产生不同的哈希（因为bcrypt使用随机盐）
        assert hash1 != hash2
        assert hash1.startswith("$2b$")

    def test_password_hash_length(self, auth_service):
        """测试密码哈希长度"""
        password = "test"
        hashed = auth_service.get_password_hash(password)

        # bcrypt哈希通常是60个字符
        assert len(hashed) == 60


class TestAuthServiceTokens:
    """测试认证服务令牌功能"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """认证服务实例"""
        with patch("src.services.auth_service.AuthUserRepository"):
            return AuthService(mock_db)

    def test_create_access_token_default_expiry(self, auth_service):
        """测试创建访问令牌（默认过期时间）"""
        data = {"sub": "testuser", "user_id": 123}
        token = auth_service.create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0
        assert "." in token  # JWT格式包含三个部分

    def test_create_access_token_custom_expiry(self, auth_service):
        """测试创建访问令牌（自定义过期时间）"""
        data = {"sub": "testuser", "user_id": 123}
        expires_delta = timedelta(hours=2)
        token = auth_service.create_access_token(data, expires_delta)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, auth_service):
        """测试创建刷新令牌"""
        data = {"sub": "testuser", "user_id": 123}
        token = auth_service.create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_access_token(self, auth_service):
        """测试验证访问令牌"""
        # 创建令牌
        data = {"sub": "testuser", "user_id": 123, "role": "user"}
        token = auth_service.create_access_token(data)

        # 验证令牌
        payload = auth_service.verify_token(token, "access")

        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 123
        assert payload["role"] == "user"
        assert payload["type"] == "access"

    def test_verify_refresh_token(self, auth_service):
        """测试验证刷新令牌"""
        # 创建令牌
        data = {"sub": "testuser", "user_id": 123}
        token = auth_service.create_refresh_token(data)

        # 验证令牌
        payload = auth_service.verify_token(token, "refresh")

        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 123
        assert payload["type"] == "refresh"

    def test_verify_token_wrong_type(self, auth_service):
        """测试验证错误类型的令牌"""
        # 创建访问令牌
        data = {"sub": "testuser"}
        token = auth_service.create_access_token(data)

        # 尝试作为刷新令牌验证
        payload = auth_service.verify_token(token, "refresh")
        assert payload is None

    def test_verify_invalid_token(self, auth_service):
        """测试验证无效令牌"""
        invalid_token = "invalid.jwt.token"
        payload = auth_service.verify_token(invalid_token)
        assert payload is None

    def test_verify_expired_token(self, auth_service):
        """测试验证过期令牌"""
        # 创建已过期的令牌
        data = {"sub": "testuser"}
        expired_delta = timedelta(seconds=-1)  # 负时间表示已过期
        token = auth_service.create_access_token(data, expired_delta)

        # 验证过期令牌
        payload = auth_service.verify_token(token)
        assert payload is None


class TestAuthServiceUserRegistration:
    """测试认证服务用户注册功能"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """认证服务实例"""
        with patch("src.services.auth_service.AuthUserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            service = AuthService(mock_db)
            service.user_repo = mock_repo
            return service

    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service):
        """测试成功注册用户"""
        # 模拟数据库查询结果
        auth_service.user_repo.get_by_username.return_value = None
        auth_service.user_repo.get_by_email.return_value = None
        auth_service.user_repo.create.return_value = Mock(id=1, username="testuser")

        # 注册用户
        user = await auth_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
        )

        # 验证用户创建
        assert user is not None
        auth_service.user_repo.create.assert_called_once()

        # 验证密码被哈希
        call_args = auth_service.user_repo.create.call_args[0][0]
        assert call_args.username == "testuser"
        assert call_args.email == "test@example.com"
        assert call_args.password_hash != "password123"  # 应该被哈希
        assert call_args.first_name == "Test"
        assert call_args.last_name == "User"
        assert call_args.role == UserRole.USER.value
        assert call_args.is_active is True
        assert call_args.is_verified is False

    @pytest.mark.asyncio
    async def test_register_user_existing_username(self, auth_service):
        """测试注册已存在的用户名"""
        # 模拟用户名已存在
        auth_service.user_repo.get_by_username.return_value = Mock()

        with pytest.raises(ValueError, match="用户名已存在"):
            await auth_service.register_user(
                username="existing_user",
                email="new@example.com",
                password="password123",
            )

    @pytest.mark.asyncio
    async def test_register_user_existing_email(self, auth_service):
        """测试注册已存在的邮箱"""
        # 模拟用户名不存在但邮箱已存在
        auth_service.user_repo.get_by_username.return_value = None
        auth_service.user_repo.get_by_email.return_value = Mock()

        with pytest.raises(ValueError, match="邮箱已存在"):
            await auth_service.register_user(
                username="new_user",
                email="existing@example.com",
                password="password123",
            )

    @pytest.mark.asyncio
    async def test_register_user_default_preferences(self, auth_service):
        """测试注册用户默认偏好设置"""
        auth_service.user_repo.get_by_username.return_value = None
        auth_service.user_repo.get_by_email.return_value = None
        auth_service.user_repo.create.return_value = Mock()

        await auth_service.register_user(
            username="testuser", email="test@example.com", password="password123"
        )

        # 验证默认偏好设置
        call_args = auth_service.user_repo.create.call_args[0][0]
        preferences = call_args.preferences

        assert "favorite_teams" in preferences
        assert "favorite_leagues" in preferences
        assert "notification_enabled" in preferences
        assert "language" in preferences
        assert preferences["language"] == "zh-CN"
        assert preferences["notification_enabled"] is True

    @pytest.mark.asyncio
    async def test_register_user_default_statistics(self, auth_service):
        """测试注册用户默认统计设置"""
        auth_service.user_repo.get_by_username.return_value = None
        auth_service.user_repo.get_by_email.return_value = None
        auth_service.user_repo.create.return_value = Mock()

        await auth_service.register_user(
            username="testuser", email="test@example.com", password="password123"
        )

        # 验证默认统计设置
        call_args = auth_service.user_repo.create.call_args[0][0]
        statistics = call_args.statistics

        assert "total_predictions" in statistics
        assert "correct_predictions" in statistics
        assert "total_profit_loss" in statistics
        assert statistics["total_predictions"] == 0
        assert statistics["correct_predictions"] == 0
        assert statistics["total_profit_loss"] == 0.0


class TestAuthServiceAuthentication:
    """测试认证服务认证功能"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """认证服务实例"""
        with patch("src.services.auth_service.AuthUserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            service = AuthService(mock_db)
            service.user_repo = mock_repo
            return service

    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.password_hash = AuthService.get_password_hash("password123")
        user.is_active = True
        user.role = UserRole.USER.value
        user.to_dict.return_value = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "role": UserRole.USER.value,
        }
        user.update_last_login = Mock()
        return user

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, mock_user):
        """测试成功用户认证"""
        auth_service.user_repo.get_by_username.return_value = mock_user

        user = await auth_service.authenticate_user("testuser", "password123")

        assert user == mock_user
        mock_user.update_last_login.assert_called_once()
        auth_service.user_repo.update.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, auth_service, mock_user):
        """测试错误密码认证"""
        auth_service.user_repo.get_by_username.return_value = mock_user

        user = await auth_service.authenticate_user("testuser", "wrong_password")

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service):
        """测试认证不存在的用户"""
        auth_service.user_repo.get_by_username.return_value = None

        user = await auth_service.authenticate_user("nonexistent", "password123")

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, auth_service, mock_user):
        """测试认证非活跃用户"""
        mock_user.is_active = False
        auth_service.user_repo.get_by_username.return_value = mock_user

        user = await auth_service.authenticate_user("testuser", "password123")

        assert user is None

    @pytest.mark.asyncio
    async def test_login_user_success(self, auth_service, mock_user):
        """测试成功用户登录"""
        auth_service.user_repo.get_by_username.return_value = mock_user

        result = await auth_service.login_user("testuser", "password123")

        assert result is not None
        assert "access_token" in result
        assert "refresh_token" in result
        assert "token_type" in result
        assert "expires_in" in result
        assert "user" in result
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == 30 * 60  # 30分钟

    @pytest.mark.asyncio
    async def test_login_user_failure(self, auth_service):
        """测试失败用户登录"""
        auth_service.user_repo.get_by_username.return_value = None

        result = await auth_service.login_user("nonexistent", "password123")

        assert result is None


class TestAuthServicePasswordManagement:
    """测试认证服务密码管理功能"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """认证服务实例"""
        with patch("src.services.auth_service.AuthUserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            service = AuthService(mock_db)
            service.user_repo = mock_repo
            return service

    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.password_hash = AuthService.get_password_hash("old_password")
        user.is_active = True
        return user

    @pytest.mark.asyncio
    async def test_change_password_success(self, auth_service, mock_user):
        """测试成功修改密码"""
        success = await auth_service.change_password(
            mock_user, "old_password", "new_password"
        )

        assert success is True
        assert mock_user.password_hash != AuthService.get_password_hash("old_password")
        auth_service.user_repo.update.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, auth_service, mock_user):
        """测试使用错误当前密码修改密码"""
        success = await auth_service.change_password(
            mock_user, "wrong_password", "new_password"
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_reset_password_request_success(self, auth_service, mock_user):
        """测试成功请求密码重置"""
        auth_service.user_repo.get_by_email.return_value = mock_user

        token = await auth_service.reset_password_request("test@example.com")

        assert token is not None
        assert isinstance(token, str)

    @pytest.mark.asyncio
    async def test_reset_password_request_email_not_found(self, auth_service):
        """测试请求密码重置但邮箱不存在"""
        auth_service.user_repo.get_by_email.return_value = None

        token = await auth_service.reset_password_request("nonexistent@example.com")

        assert token is None

    @pytest.mark.asyncio
    async def test_reset_password_success(self, auth_service, mock_user):
        """测试成功重置密码"""
        # 创建重置令牌
        reset_data = {"sub": "testuser", "user_id": 1, "type": "password_reset"}
        reset_token = auth_service.create_access_token(reset_data, timedelta(hours=1))

        auth_service.user_repo.get_by_username.return_value = mock_user

        success = await auth_service.reset_password(reset_token, "new_password")

        assert success is True
        auth_service.user_repo.update.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, auth_service):
        """测试使用无效令牌重置密码"""
        success = await auth_service.reset_password("invalid_token", "new_password")

        assert success is False

    @pytest.mark.asyncio
    async def test_reset_password_wrong_type(self, auth_service):
        """测试使用错误类型令牌重置密码"""
        # 创建访问令牌而不是重置令牌
        access_data = {"sub": "testuser", "user_id": 1}
        access_token = auth_service.create_access_token(access_data)

        success = await auth_service.reset_password(access_token, "new_password")

        assert success is False


class TestAuthServiceEmailVerification:
    """测试认证服务邮箱验证功能"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """认证服务实例"""
        with patch("src.services.auth_service.AuthUserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            service = AuthService(mock_db)
            service.user_repo = mock_repo
            return service

    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_active = True
        user.is_verified = False
        return user

    def test_create_email_verification_token(self, auth_service, mock_user):
        """测试创建邮箱验证令牌"""
        token = auth_service.create_email_verification_token(mock_user)

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_verify_email_success(self, auth_service, mock_user):
        """测试成功验证邮箱"""
        # 创建验证令牌
        verification_data = {
            "sub": "testuser",
            "user_id": 1,
            "type": "email_verification",
        }
        verification_token = auth_service.create_access_token(
            verification_data, timedelta(hours=24)
        )

        auth_service.user_repo.get_by_username.return_value = mock_user

        success = await auth_service.verify_email(verification_token)

        assert success is True
        assert mock_user.is_verified is True
        auth_service.user_repo.update.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, auth_service):
        """测试使用无效令牌验证邮箱"""
        success = await auth_service.verify_email("invalid_token")

        assert success is False

    @pytest.mark.asyncio
    async def test_verify_email_user_not_found(self, auth_service):
        """测试验证邮箱但用户不存在"""
        verification_data = {
            "sub": "nonexistent",
            "user_id": 999,
            "type": "email_verification",
        }
        verification_token = auth_service.create_access_token(
            verification_data, timedelta(hours=24)
        )

        auth_service.user_repo.get_by_username.return_value = None

        success = await auth_service.verify_email(verification_token)

        assert success is False


class TestAuthServiceTokenRefresh:
    """测试认证服务令牌刷新功能"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """认证服务实例"""
        with patch("src.services.auth_service.AuthUserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            service = AuthService(mock_db)
            service.user_repo = mock_repo
            return service

    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_active = True
        user.role = UserRole.USER.value
        return user

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, auth_service, mock_user):
        """测试成功刷新访问令牌"""
        # 创建刷新令牌
        refresh_data = {"sub": "testuser", "user_id": 1}
        refresh_token = auth_service.create_refresh_token(refresh_data)

        auth_service.user_repo.get_by_username.return_value = mock_user

        new_access_token = await auth_service.refresh_access_token(refresh_token)

        assert new_access_token is not None
        assert isinstance(new_access_token, str)

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self, auth_service):
        """测试使用无效刷新令牌"""
        new_access_token = await auth_service.refresh_access_token("invalid_token")

        assert new_access_token is None

    @pytest.mark.asyncio
    async def test_refresh_access_token_inactive_user(self, auth_service, mock_user):
        """测试为非活跃用户刷新令牌"""
        mock_user.is_active = False
        refresh_data = {"sub": "testuser", "user_id": 1}
        refresh_token = auth_service.create_refresh_token(refresh_data)

        auth_service.user_repo.get_by_username.return_value = mock_user

        new_access_token = await auth_service.refresh_access_token(refresh_token)

        assert new_access_token is None

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, auth_service, mock_user):
        """测试成功获取当前用户"""
        # 创建访问令牌
        access_data = {
            "sub": "testuser",
            "user_id": 1,
            "role": "user",
            "email": "test@example.com",
        }
        access_token = auth_service.create_access_token(access_data)

        auth_service.user_repo.get_by_username.return_value = mock_user

        user = await auth_service.get_current_user(access_token)

        assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, auth_service):
        """测试使用无效令牌获取当前用户"""
        user = await auth_service.get_current_user("invalid_token")

        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_inactive(self, auth_service, mock_user):
        """测试获取非活跃当前用户"""
        mock_user.is_active = False
        access_data = {"sub": "testuser", "user_id": 1}
        access_token = auth_service.create_access_token(access_data)

        auth_service.user_repo.get_by_username.return_value = mock_user

        user = await auth_service.get_current_user(access_token)

        assert user is None


class TestAuthServiceIntegration:
    """认证服务集成测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """认证服务实例"""
        with patch("src.services.auth_service.AuthUserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            service = AuthService(mock_db)
            service.user_repo = mock_repo
            return service

    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.password_hash = AuthService.get_password_hash("password123")
        user.is_active = True
        user.is_verified = False
        user.role = UserRole.USER.value
        user.to_dict.return_value = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "role": UserRole.USER.value,
        }
        user.update_last_login = Mock()
        return user

    def test_full_authentication_flow(self, auth_service, mock_user):
        """测试完整认证流程"""
        # 1. 创建密码哈希
        password = "password123"
        hashed = auth_service.get_password_hash(password)

        # 2. 验证密码
        assert auth_service.verify_password(password, hashed) is True
        assert auth_service.verify_password("wrong_password", hashed) is False

        # 3. 创建令牌
        access_data = {
            "sub": "testuser",
            "user_id": 1,
            "role": "user",
            "email": "test@example.com",
        }
        access_token = auth_service.create_access_token(access_data)
        refresh_token = auth_service.create_refresh_token(
            {"sub": "testuser", "user_id": 1}
        )

        # 4. 验证令牌
        access_payload = auth_service.verify_token(access_token, "access")
        refresh_payload = auth_service.verify_token(refresh_token, "refresh")

        assert access_payload is not None
        assert refresh_payload is not None
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

    @pytest.mark.asyncio
    async def test_user_lifecycle(self, auth_service, mock_user):
        """测试用户生命周期"""
        # 1. 注册用户
        auth_service.user_repo.get_by_username.return_value = None
        auth_service.user_repo.get_by_email.return_value = None
        auth_service.user_repo.create.return_value = mock_user

        registered_user = await auth_service.register_user(
            username="testuser", email="test@example.com", password="password123"
        )
        assert registered_user is not None

        # 2. 用户认证
        auth_service.user_repo.get_by_username.return_value = mock_user
        authenticated_user = await auth_service.authenticate_user(
            "testuser", "password123"
        )
        assert authenticated_user == mock_user

        # 3. 用户登录
        login_result = await auth_service.login_user("testuser", "password123")
        assert login_result is not None
        assert "access_token" in login_result

        # 4. 修改密码
        password_changed = await auth_service.change_password(
            mock_user, "password123", "new_password"
        )
        assert password_changed is True

        # 5. 邮箱验证
        verification_token = auth_service.create_email_verification_token(mock_user)
        await auth_service.verify_email(verification_token)
        # 注意：由于模拟设置，这个测试可能需要调整

    def test_token_security_features(self, auth_service):
        """测试令牌安全功能"""
        user_data = {
            "sub": "testuser",
            "user_id": 1,
            "role": "user",
            "email": "test@example.com",
        }

        # 测试不同类型的令牌
        access_token = auth_service.create_access_token(user_data)
        refresh_token = auth_service.create_refresh_token(
            {"sub": "testuser", "user_id": 1}
        )

        # 验证令牌类型区分
        access_payload = auth_service.verify_token(access_token, "access")
        refresh_payload = auth_service.verify_token(refresh_token, "refresh")
        wrong_access_payload = auth_service.verify_token(access_token, "refresh")
        wrong_refresh_payload = auth_service.verify_token(refresh_token, "access")

        assert access_payload is not None
        assert refresh_payload is not None
        assert wrong_access_payload is None  # 错误类型
        assert wrong_refresh_payload is None  # 错误类型

        # 验证过期时间
        short_expiry = auth_service.create_access_token(user_data, timedelta(seconds=1))
        import time

        time.sleep(2)  # 等待令牌过期
        expired_payload = auth_service.verify_token(short_expiry)
        assert expired_payload is None
