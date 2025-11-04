"""
用户管理路由测试
User Management Routes Tests

测试用户管理API端点的功能。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from src.api.routes.user_management import router
from src.services.user_management_service import (
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    UserAuthResponse,
)
from src.core.exceptions import (
    UserNotFoundError,
    UserAlreadyExistsError,
    InvalidCredentialsError,
)
from src.api.dependencies import get_user_management_service


@pytest.fixture
def client(mock_user_service):
    """测试客户端"""
    from fastapi import FastAPI

    app = FastAPI()

    # 模拟依赖注入
    async def mock_get_user_management_service():
        return mock_user_service

    app.dependency_overrides[get_user_management_service] = mock_get_user_management_service
    app.include_router(router, prefix="/api/v1/users")

    return TestClient(app)


@pytest.fixture
def mock_user_service():
    """模拟用户管理服务"""
    return Mock()


@pytest.fixture
def sample_user_response():
    """示例用户响应数据"""
    return UserResponse(
        id=1,
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
    )


class TestUserManagementRoutes:
    """用户管理路由测试类"""

    @pytest.mark.unit
    @pytest.mark.api
    def test_register_user_success(self, client, mock_user_service, sample_user_response):
        """测试成功注册用户"""
        # 准备模拟数据
        mock_user_service.create_user = AsyncMock(return_value=sample_user_response)

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class:
            mock_service_class.return_value = mock_user_service

            # 发送请求
            response = client.post(
                "/api/v1/users/register",
                json={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                    "full_name": "Test User",
                },
            )

            # 验证响应
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 1
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert data["full_name"] == "Test User"
            assert data["is_active"] is True

    @pytest.mark.unit
    @pytest.mark.api
    def test_register_user_email_exists(self, client, mock_user_service):
        """测试注册用户时邮箱已存在"""
        # 准备模拟数据
        mock_user_service.create_user = AsyncMock(
            side_effect=UserAlreadyExistsError("用户邮箱 test@example.com 已存在")
        )

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class:
            mock_service_class.return_value = mock_user_service

            # 发送请求
            response = client.post(
                "/api/v1/users/register",
                json={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                    "full_name": "Test User",
                },
            )

            # 验证响应
            assert response.status_code == 409
            data = response.json()
            assert "用户邮箱 test@example.com 已存在" in data["detail"]

    @pytest.mark.unit
    @pytest.mark.api
    def test_register_user_invalid_data(self, client, mock_user_service):
        """测试注册用户时数据无效"""
        # 准备模拟数据
        mock_user_service.create_user = AsyncMock(
            side_effect=ValueError("用户名至少需要3个字符")
        )

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class:
            mock_service_class.return_value = mock_user_service

            # 发送请求
            response = client.post(
                "/api/v1/users/register",
                json={
                    "username": "ab",  # 用户名太短
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                    "full_name": "Test User",
                },
            )

            # 验证响应
            assert response.status_code == 400
            data = response.json()
            assert "用户名至少需要3个字符" in data["detail"]

    @pytest.mark.unit
    @pytest.mark.api
    def test_login_user_success(self, client, mock_user_service, sample_user_response):
        """测试成功登录用户"""
        # 准备模拟数据
        auth_response = UserAuthResponse(
            access_token="test_token",
            token_type="bearer",
            expires_in=3600,
            user=sample_user_response,
        )
        mock_user_service.authenticate_user = AsyncMock(return_value=auth_response)

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class:
            mock_service_class.return_value = mock_user_service

            # 发送请求
            response = client.post(
                "/api/v1/users/login",
                json={
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                },
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "test_token"
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 3600
            assert data["user"]["id"] == 1
            assert data["user"]["email"] == "test@example.com"

    @pytest.mark.unit
    @pytest.mark.api
    def test_login_user_invalid_credentials(self, client, mock_user_service):
        """测试登录时凭据无效"""
        # 准备模拟数据
        mock_user_service.authenticate_user = AsyncMock(
            side_effect=InvalidCredentialsError("密码错误")
        )

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class:
            mock_service_class.return_value = mock_user_service

            # 发送请求
            response = client.post(
                "/api/v1/users/login",
                json={
                    "email": "test@example.com",
                    "password": "WrongPassword",
                },
            )

            # 验证响应
            assert response.status_code == 401
            data = response.json()
            assert "密码错误" in data["detail"]

    @pytest.mark.unit
    @pytest.mark.api
    def test_login_user_not_found(self, client, mock_user_service):
        """测试登录时用户不存在"""
        # 准备模拟数据
        mock_user_service.authenticate_user = AsyncMock(
            side_effect=UserNotFoundError("用户邮箱 test@example.com 不存在")
        )

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class:
            mock_service_class.return_value = mock_user_service

            # 发送请求
            response = client.post(
                "/api/v1/users/login",
                json={
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                },
            )

            # 验证响应
            assert response.status_code == 401
            data = response.json()
            assert "用户邮箱 test@example.com 不存在" in data["detail"]

    @pytest.mark.unit
    @pytest.mark.api
    def test_get_user_by_id_success(self, client, mock_user_service, sample_user_response):
        """测试成功根据ID获取用户"""
        # 准备模拟数据
        mock_user_service.get_user_by_id = AsyncMock(return_value=sample_user_response)

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class:
            mock_service_class.return_value = mock_user_service

            # 发送请求
            response = client.get("/api/v1/users/1")

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"

    @pytest.mark.unit
    @pytest.mark.api
    def test_get_user_by_id_not_found(self, client, mock_user_service):
        """测试根据ID获取用户时用户不存在"""
        # 准备模拟数据
        mock_user_service.get_user_by_id = AsyncMock(
            side_effect=UserNotFoundError("用户ID 1 不存在")
        )

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class:
            mock_service_class.return_value = mock_user_service

            # 发送请求
            response = client.get("/api/v1/users/1")

            # 验证响应
            assert response.status_code == 404
            data = response.json()
            assert "用户ID 1 不存在" in data["detail"]

    @pytest.mark.unit
    @pytest.mark.api
    def test_update_user_success(self, client, mock_user_service, sample_user_response):
        """测试成功更新用户"""
        # 准备模拟数据
        updated_user = sample_user_response
        updated_user.full_name = "Updated Name"
        mock_user_service.update_user = AsyncMock(return_value=updated_user)

        # 模拟认证用户
        mock_current_user = {"id": 1, "is_admin": False}

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class, \
             patch("src.api.routes.user_management.get_current_user") as mock_auth:
            mock_service_class.return_value = mock_user_service
            mock_auth.return_value = mock_current_user

            # 发送请求
            response = client.put(
                "/api/v1/users/1",
                json={
                    "full_name": "Updated Name",
                    "is_active": False,
                },
                headers={"Authorization": "Bearer test_token"},
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            # 注意：这里我们验证的是更新后的数据结构

    @pytest.mark.unit
    @pytest.mark.api
    def test_update_user_forbidden(self, client, mock_user_service):
        """测试更新用户时权限不足"""
        # 模拟认证用户（ID不匹配）
        mock_current_user = {"id": 2, "is_admin": False}

        with patch("src.api.routes.user_management.get_current_user") as mock_auth:
            mock_auth.return_value = mock_current_user

            # 发送请求
            response = client.put(
                "/api/v1/users/1",
                json={"full_name": "Updated Name"},
                headers={"Authorization": "Bearer test_token"},
            )

            # 验证响应
            assert response.status_code == 403
            data = response.json()
            assert "只能更新自己的用户信息" in data["detail"]

    @pytest.mark.unit
    @pytest.mark.api
    def test_change_password_success(self, client, mock_user_service):
        """测试成功修改密码"""
        # 准备模拟数据
        mock_user_service.change_password = AsyncMock(return_value=True)

        # 模拟认证用户
        mock_current_user = {"id": 1, "is_admin": False}

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class, \
             patch("src.api.routes.user_management.get_current_user") as mock_auth:
            mock_service_class.return_value = mock_user_service
            mock_auth.return_value = mock_current_user

            # 发送请求
            response = client.post(
                "/api/v1/users/change-password",
                json={
                    "old_password": "OldPass123!",
                    "new_password": "NewPass123!",
                },
                headers={"Authorization": "Bearer test_token"},
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert "密码修改成功" in data["message"]

    @pytest.mark.unit
    @pytest.mark.api
    def test_change_password_invalid_old_password(self, client, mock_user_service):
        """测试修改密码时旧密码错误"""
        # 准备模拟数据
        mock_user_service.change_password = AsyncMock(
            side_effect=InvalidCredentialsError("旧密码错误")
        )

        # 模拟认证用户
        mock_current_user = {"id": 1, "is_admin": False}

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class, \
             patch("src.api.routes.user_management.get_current_user") as mock_auth:
            mock_service_class.return_value = mock_user_service
            mock_auth.return_value = mock_current_user

            # 发送请求
            response = client.post(
                "/api/v1/users/change-password",
                json={
                    "old_password": "WrongOldPass",
                    "new_password": "NewPass123!",
                },
                headers={"Authorization": "Bearer test_token"},
            )

            # 验证响应
            assert response.status_code == 400
            data = response.json()
            assert "旧密码错误" in data["detail"]

    @pytest.mark.unit
    @pytest.mark.api
    def test_get_users_admin_success(self, client, mock_user_service):
        """测试管理员获取用户列表"""
        # 准备模拟数据
        sample_users = [
            UserResponse(
                id=1,
                username="user1",
                email="user1@example.com",
                full_name="User One",
                is_active=True,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
            UserResponse(
                id=2,
                username="user2",
                email="user2@example.com",
                full_name="User Two",
                is_active=True,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
        ]
        mock_user_service.get_users = AsyncMock(return_value=sample_users)

        # 模拟管理员用户
        mock_current_user = {"id": 1, "is_admin": True}

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class, \
             patch("src.api.routes.user_management.get_current_user") as mock_auth:
            mock_service_class.return_value = mock_user_service
            mock_auth.return_value = mock_current_user

            # 发送请求
            response = client.get(
                "/api/v1/users/",
                headers={"Authorization": "Bearer test_token"},
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["username"] == "user1"
            assert data[1]["username"] == "user2"

    @pytest.mark.unit
    @pytest.mark.api
    def test_get_users_non_admin_forbidden(self, client, mock_user_service):
        """测试非管理员获取用户列表时权限不足"""
        # 模拟非管理员用户
        mock_current_user = {"id": 1, "is_admin": False}

        with patch("src.api.routes.user_management.get_current_user") as mock_auth:
            mock_auth.return_value = mock_current_user

            # 发送请求
            response = client.get(
                "/api/v1/users/",
                headers={"Authorization": "Bearer test_token"},
            )

            # 验证响应
            assert response.status_code == 403
            data = response.json()
            assert "只有管理员可以查看用户列表" in data["detail"]

    @pytest.mark.unit
    @pytest.mark.api
    def test_deactivate_user_admin_success(self, client, mock_user_service, sample_user_response):
        """测试管理员成功停用用户"""
        # 准备模拟数据
        mock_user_service.deactivate_user = AsyncMock(return_value=sample_user_response)

        # 模拟管理员用户
        mock_current_user = {"id": 1, "is_admin": True}

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class, \
             patch("src.api.routes.user_management.get_current_user") as mock_auth:
            mock_service_class.return_value = mock_user_service
            mock_auth.return_value = mock_current_user

            # 发送请求
            response = client.post(
                "/api/v1/users/1/deactivate",
                headers={"Authorization": "Bearer test_token"},
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1

    @pytest.mark.unit
    @pytest.mark.api
    def test_deactivate_user_non_admin_forbidden(self, client, mock_user_service):
        """测试非管理员停用用户时权限不足"""
        # 模拟非管理员用户
        mock_current_user = {"id": 1, "is_admin": False}

        with patch("src.api.routes.user_management.get_current_user") as mock_auth:
            mock_auth.return_value = mock_current_user

            # 发送请求
            response = client.post(
                "/api/v1/users/1/deactivate",
                headers={"Authorization": "Bearer test_token"},
            )

            # 验证响应
            assert response.status_code == 403
            data = response.json()
            assert "只有管理员可以停用用户" in data["detail"]

    @pytest.mark.unit
    @pytest.mark.api
    def test_get_user_stats_admin_success(self, client, mock_user_service):
        """测试管理员获取用户统计信息"""
        # 准备模拟数据
        stats_data = {
            "total_users": 100,
            "active_users": 80,
            "inactive_users": 20,
            "activity_rate": 80.0,
        }
        mock_user_service.get_user_stats = AsyncMock(return_value=stats_data)

        # 模拟管理员用户
        mock_current_user = {"id": 1, "is_admin": True}

        with patch("src.api.routes.user_management.UserManagementService") as mock_service_class, \
             patch("src.api.routes.user_management.get_current_user") as mock_auth:
            mock_service_class.return_value = mock_user_service
            mock_auth.return_value = mock_current_user

            # 发送请求
            response = client.get(
                "/api/v1/users/stats",
                headers={"Authorization": "Bearer test_token"},
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["total_users"] == 100
            assert data["active_users"] == 80
            assert data["inactive_users"] == 20
            assert data["activity_rate"] == 80.0

    @pytest.mark.unit
    @pytest.mark.api
    def test_get_user_stats_non_admin_forbidden(self, client, mock_user_service):
        """测试非管理员获取用户统计信息时权限不足"""
        # 模拟非管理员用户
        mock_current_user = {"id": 1, "is_admin": False}

        with patch("src.api.routes.user_management.get_current_user") as mock_auth:
            mock_auth.return_value = mock_current_user

            # 发送请求
            response = client.get(
                "/api/v1/users/stats",
                headers={"Authorization": "Bearer test_token"},
            )

            # 验证响应
            assert response.status_code == 403
            data = response.json()
            assert "只有管理员可以查看用户统计" in data["detail"]