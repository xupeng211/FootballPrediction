"""
用户管理服务测试
User Management Service Tests

测试用户管理的核心功能，包括注册、登录、信息更新等。
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.exceptions import (InvalidCredentialsError,
                                 UserAlreadyExistsError, UserNotFoundError)
from src.services.user_management_service import (UserAuthResponse,
                                                  UserCreateRequest,
                                                  UserManagementService,
                                                  UserResponse,
                                                  UserUpdateRequest)


@pytest.fixture
def mock_user_repository():
    """模拟用户仓储"""
    mock_repo = Mock()
    mock_repo.get_by_id = AsyncMock()
    mock_repo.get_by_email = AsyncMock()
    mock_repo.create = AsyncMock()
    mock_repo.update = AsyncMock()
    mock_repo.delete = AsyncMock()
    mock_repo.get_list = AsyncMock()
    mock_repo.search = AsyncMock()
    mock_repo.count = AsyncMock()
    return mock_repo


@pytest.fixture
def user_service(mock_user_repository):
    """用户管理服务实例"""
    return UserManagementService(mock_user_repository)


@pytest.fixture
def sample_user():
    """示例用户数据"""
    user = Mock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.is_active = True
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    user.password_hash = "hashed_password"
    return user


class TestUserManagementService:
    """用户管理服务测试类"""

    @pytest.mark.unit
    @pytest.mark.services
    async def test_create_user_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试成功创建用户"""
        # 准备测试数据
        mock_user_repository.get_by_email.return_value = None
        mock_user_repository.create.return_value = sample_user

        request = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="SecurePass123!",
            full_name="Test User",
        )

        # 执行测试
        result = await user_service.create_user(request)

        # 验证结果
        assert isinstance(result, UserResponse)
        assert result.id == 1
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        assert result.full_name == "Test User"
        assert result.is_active is True

        # 验证调用
        mock_user_repository.get_by_email.assert_called_once_with("test@example.com")
        mock_user_repository.create.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.services
    async def test_create_user_email_already_exists(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试创建用户时邮箱已存在"""
        # 准备测试数据
        mock_user_repository.get_by_email.return_value = sample_user

        request = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="SecurePass123!",
            full_name="Test User",
        )

        # 执行测试并验证异常
        with pytest.raises(
            UserAlreadyExistsError, match="用户邮箱 test@example.com 已存在"
        ):
            await user_service.create_user(request)

        # 验证调用
        mock_user_repository.get_by_email.assert_called_once_with("test@example.com")
        mock_user_repository.create.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.services
    async def test_create_user_invalid_username(self, user_service):
        """测试创建用户时用户名无效"""
        request = UserCreateRequest(
            username="ab",  # 用户名太短
            email="test@example.com",
            password="SecurePass123!",
            full_name="Test User",
        )

        # 执行测试并验证异常
        with pytest.raises(ValueError, match="用户名至少需要3个字符"):
            await user_service.create_user(request)

    @pytest.mark.unit
    @pytest.mark.services
    async def test_authenticate_user_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试成功认证用户"""
        # 准备测试数据
        mock_user_repository.get_by_email.return_value = sample_user

        with patch(
            "src.services.user_management_service.verify_password"
        ) as mock_verify:
            mock_verify.return_value = True

            # 执行测试
            result = await user_service.authenticate_user(
                "test@example.com", "SecurePass123!"
            )

            # 验证结果
            assert isinstance(result, UserAuthResponse)
            assert result.token_type == "bearer"
            assert result.expires_in == 3600
            assert result.user.email == "test@example.com"

            # 验证调用
            mock_user_repository.get_by_email.assert_called_once_with(
                "test@example.com"
            )
            mock_verify.assert_called_once_with("SecurePass123!", "hashed_password")

    @pytest.mark.unit
    @pytest.mark.services
    async def test_authenticate_user_not_found(
        self, user_service, mock_user_repository
    ):
        """测试认证不存在的用户"""
        # 准备测试数据
        mock_user_repository.get_by_email.return_value = None

        # 执行测试并验证异常
        with pytest.raises(UserNotFoundError, match="用户邮箱 test@example.com 不存在"):
            await user_service.authenticate_user("test@example.com", "SecurePass123!")

        # 验证调用
        mock_user_repository.get_by_email.assert_called_once_with("test@example.com")

    @pytest.mark.unit
    @pytest.mark.services
    async def test_authenticate_user_invalid_password(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试认证时密码错误"""
        # 准备测试数据
        mock_user_repository.get_by_email.return_value = sample_user

        with patch(
            "src.services.user_management_service.verify_password"
        ) as mock_verify:
            mock_verify.return_value = False

            # 执行测试并验证异常
            with pytest.raises(InvalidCredentialsError, match="密码错误"):
                await user_service.authenticate_user(
                    "test@example.com", "WrongPassword"
                )

            # 验证调用
            mock_user_repository.get_by_email.assert_called_once_with(
                "test@example.com"
            )
            mock_verify.assert_called_once_with("WrongPassword", "hashed_password")

    @pytest.mark.unit
    @pytest.mark.services
    async def test_get_user_by_id_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试根据ID获取用户成功"""
        # 准备测试数据
        mock_user_repository.get_by_id.return_value = sample_user

        # 执行测试
        result = await user_service.get_user_by_id(1)

        # 验证结果
        assert isinstance(result, UserResponse)
        assert result.id == 1
        assert result.username == "testuser"

        # 验证调用
        mock_user_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.unit
    @pytest.mark.services
    async def test_get_user_by_id_not_found(self, user_service, mock_user_repository):
        """测试根据ID获取用户失败"""
        # 准备测试数据
        mock_user_repository.get_by_id.return_value = None

        # 执行测试并验证异常
        with pytest.raises(UserNotFoundError, match="用户ID 1 不存在"):
            await user_service.get_user_by_id(1)

        # 验证调用
        mock_user_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.unit
    @pytest.mark.services
    async def test_update_user_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试成功更新用户"""
        # 准备测试数据
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.get_by_email.return_value = None
        mock_user_repository.update.return_value = sample_user

        request = UserUpdateRequest(full_name="Updated Name", is_active=False)

        # 执行测试
        result = await user_service.update_user(1, request)

        # 验证结果
        assert isinstance(result, UserResponse)
        assert result.id == 1

        # 验证调用
        mock_user_repository.get_by_id.assert_called_once_with(1)
        mock_user_repository.update.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.services
    async def test_update_user_email_already_exists(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试更新用户时邮箱已被其他用户使用"""
        # 准备测试数据
        other_user = Mock()
        other_user.id = 2
        other_user.email = "other@example.com"

        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.get_by_email.return_value = other_user

        request = UserUpdateRequest(email="other@example.com")

        # 执行测试并验证异常
        with pytest.raises(
            UserAlreadyExistsError, match="邮箱 other@example.com 已被其他用户使用"
        ):
            await user_service.update_user(1, request)

        # 验证调用
        mock_user_repository.get_by_id.assert_called_once_with(1)
        mock_user_repository.get_by_email.assert_called_once_with("other@example.com")
        mock_user_repository.update.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.services
    async def test_delete_user_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试成功删除用户"""
        # 准备测试数据
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.delete.return_value = True

        # 执行测试
        result = await user_service.delete_user(1)

        # 验证结果
        assert result is True

        # 验证调用
        mock_user_repository.get_by_id.assert_called_once_with(1)
        mock_user_repository.delete.assert_called_once_with(1)

    @pytest.mark.unit
    @pytest.mark.services
    async def test_delete_user_not_found(self, user_service, mock_user_repository):
        """测试删除不存在的用户"""
        # 准备测试数据
        mock_user_repository.get_by_id.return_value = None

        # 执行测试并验证异常
        with pytest.raises(UserNotFoundError, match="用户ID 1 不存在"):
            await user_service.delete_user(1)

        # 验证调用
        mock_user_repository.get_by_id.assert_called_once_with(1)
        mock_user_repository.delete.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.services
    async def test_get_users_success(self, user_service, mock_user_repository):
        """测试成功获取用户列表"""
        # 准备测试数据
        sample_users = [
            Mock(id=i, username=f"user{i}", email=f"user{i}@example.com")
            for i in range(3)
        ]
        for i, user in enumerate(sample_users):
            user.full_name = f"User {i}"
            user.is_active = True
            user.created_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()

        mock_user_repository.get_list.return_value = sample_users

        # 执行测试
        result = await user_service.get_users(skip=0, limit=10, active_only=True)

        # 验证结果
        assert len(result) == 3
        assert all(isinstance(user, UserResponse) for user in result)

        # 验证调用
        mock_user_repository.get_list.assert_called_once_with(
            skip=0, limit=10, active_only=True
        )

    @pytest.mark.unit
    @pytest.mark.services
    async def test_change_password_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试成功修改密码"""
        # 准备测试数据
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user

        with patch(
            "src.services.user_management_service.verify_password"
        ) as mock_verify:
            mock_verify.return_value = True
            with patch(
                "src.services.user_management_service.validate_password_strength"
            ) as mock_validate:
                mock_validate.return_value = None

                # 执行测试
                result = await user_service.change_password(
                    1, "OldPass123!", "NewPass123!"
                )

                # 验证结果
                assert result is True

                # 验证调用
                mock_user_repository.get_by_id.assert_called_once_with(1)
                mock_verify.assert_called_once_with("OldPass123!", "hashed_password")
                mock_validate.assert_called_once_with("NewPass123!")
                mock_user_repository.update.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.services
    async def test_change_password_invalid_old_password(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试修改密码时旧密码错误"""
        # 准备测试数据
        mock_user_repository.get_by_id.return_value = sample_user

        with patch(
            "src.services.user_management_service.verify_password"
        ) as mock_verify:
            mock_verify.return_value = False

            # 执行测试并验证异常
            with pytest.raises(InvalidCredentialsError, match="旧密码错误"):
                await user_service.change_password(1, "WrongOldPass", "NewPass123!")

            # 验证调用
            mock_user_repository.get_by_id.assert_called_once_with(1)
            mock_verify.assert_called_once_with("WrongOldPass", "hashed_password")
            mock_user_repository.update.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.services
    async def test_get_user_stats_success(self, user_service, mock_user_repository):
        """测试成功获取用户统计信息"""
        # 准备测试数据
        with patch.object(mock_user_repository, "count") as mock_count:
            mock_count.side_effect = [100, 80]  # 第一次返回总数，第二次返回活跃数

            # 执行测试
            result = await user_service.get_user_stats()

            # 验证结果
            assert result["total_users"] == 100
            assert result["active_users"] == 80
            assert result["inactive_users"] == 20
            assert result["activity_rate"] == 80.0

            # 验证调用次数
            assert mock_count.call_count == 2

    @pytest.mark.unit
    @pytest.mark.services
    async def test_deactivate_user_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试成功停用用户"""
        # 准备测试数据
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user

        # 执行测试
        result = await user_service.deactivate_user(1)

        # 验证结果
        assert isinstance(result, UserResponse)
        assert result.id == 1

        # 验证调用
        mock_user_repository.get_by_id.assert_called_once_with(1)
        mock_user_repository.update.assert_called_once()

        # 验证更新数据
        call_args = mock_user_repository.update.call_args[0][1]
        assert call_args["is_active"] is False
        assert "updated_at" in call_args

    @pytest.mark.unit
    @pytest.mark.services
    async def test_activate_user_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试成功激活用户"""
        # 准备测试数据
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user

        # 执行测试
        result = await user_service.activate_user(1)

        # 验证结果
        assert isinstance(result, UserResponse)
        assert result.id == 1

        # 验证调用
        mock_user_repository.get_by_id.assert_called_once_with(1)
        mock_user_repository.update.assert_called_once()

        # 验证更新数据
        call_args = mock_user_repository.update.call_args[0][1]
        assert call_args["is_active"] is True
        assert "updated_at" in call_args

    @pytest.mark.unit
    @pytest.mark.services
    async def test_authenticate_user_empty_credentials(
        self, user_service, mock_user_repository
    ):
        """测试认证时邮箱和密码为空"""
        # 执行测试并验证异常
        with pytest.raises(InvalidCredentialsError, match="邮箱和密码不能为空"):
            await user_service.authenticate_user("", "password")

        with pytest.raises(InvalidCredentialsError, match="邮箱和密码不能为空"):
            await user_service.authenticate_user("email@example.com", "")

        with pytest.raises(InvalidCredentialsError, match="邮箱和密码不能为空"):
            await user_service.authenticate_user("", "")

    @pytest.mark.unit
    @pytest.mark.services
    async def test_get_user_by_email_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试成功根据邮箱获取用户"""
        # 准备测试数据
        mock_user_repository.get_by_email.return_value = sample_user

        # 执行测试
        result = await user_service.get_user_by_email("test@example.com")

        # 验证结果
        assert isinstance(result, UserResponse)
        assert result.email == "test@example.com"

        # 验证调用
        mock_user_repository.get_by_email.assert_called_once_with("test@example.com")

    @pytest.mark.unit
    @pytest.mark.services
    async def test_get_user_by_email_not_found(
        self, user_service, mock_user_repository
    ):
        """测试根据邮箱获取用户时用户不存在"""
        # 准备测试数据
        mock_user_repository.get_by_email.return_value = None

        # 执行测试并验证异常
        with pytest.raises(UserNotFoundError, match="用户邮箱 test@example.com 不存在"):
            await user_service.get_user_by_email("test@example.com")

        # 验证调用
        mock_user_repository.get_by_email.assert_called_once_with("test@example.com")

    @pytest.mark.unit
    @pytest.mark.services
    async def test_search_users_success(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试成功搜索用户"""
        # 准备测试数据
        mock_user_repository.search.return_value = [sample_user]

        # 执行测试
        result = await user_service.search_users("test", limit=10)

        # 验证结果
        assert len(result) == 1
        assert isinstance(result[0], UserResponse)
        assert result[0].username == "testuser"

        # 验证调用
        mock_user_repository.search.assert_called_once_with("test", 10)

    @pytest.mark.unit
    @pytest.mark.services
    async def test_search_users_empty_result(self, user_service, mock_user_repository):
        """测试搜索用户时无结果"""
        # 准备测试数据
        mock_user_repository.search.return_value = []

        # 执行测试
        result = await user_service.search_users("nonexistent", limit=10)

        # 验证结果
        assert len(result) == 0
        assert isinstance(result, list)

        # 验证调用
        mock_user_repository.search.assert_called_once_with("nonexistent", 10)

    @pytest.mark.unit
    @pytest.mark.services
    async def test_change_password_user_not_found(
        self, user_service, mock_user_repository
    ):
        """测试修改密码时用户不存在"""
        # 准备测试数据
        mock_user_repository.get_by_id.return_value = None

        # 执行测试并验证异常
        with pytest.raises(UserNotFoundError, match="用户ID 1 不存在"):
            await user_service.change_password(1, "oldpass", "newpass")

        # 验证调用
        mock_user_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.unit
    @pytest.mark.services
    async def test_change_password_weak_new_password(
        self, user_service, mock_user_repository, sample_user
    ):
        """测试修改密码时新密码强度不足"""
        # 准备测试数据
        mock_user_repository.get_by_id.return_value = sample_user

        with patch(
            "src.services.user_management_service.verify_password"
        ) as mock_verify:
            mock_verify.return_value = True
            with patch(
                "src.services.user_management_service.validate_password_strength"
            ) as mock_validate:
                mock_validate.side_effect = ValueError("密码强度不足")

                # 执行测试并验证异常
                with pytest.raises(ValueError, match="密码强度不足"):
                    await user_service.change_password(1, "oldpass", "weak")
