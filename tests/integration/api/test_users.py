"""
用户 API 集成测试
测试用户 API 与数据库的交互
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timezone


class TestUserAPIIntegration:
    """用户 API 集成测试"""

    @pytest.mark.asyncio
    async def test_register_user(self, api_client: AsyncClient, db_session):
        """测试用户注册"""
        user_data = {
            "username": "test_integration_user",
            "email": "integration@example.com",
            "password": "secure_password_123",
            "role": "user",
        }

        # 发送注册请求
        response = await api_client.post("/api/v1/auth/register", json=user_data)

        # 验证响应
        assert response.status_code == 201
        _data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["role"] == user_data["role"]
        assert "password" not in data  # 密码不应返回
        assert "id" in data
        assert "created_at" in data

        # 验证数据库中的用户
        from src.database.models import User

        _user = await db_session.execute(
            select(User).where(User.username == user_data["username"])
        )
        _user = user.scalar_one_or_none()
        assert user is not None
        assert user.email == user_data["email"]
        assert user.role == user_data["role"]

    @pytest.mark.asyncio
    async def test_login_user(self, api_client: AsyncClient, db_session):
        """测试用户登录"""
        # 先注册用户
        user_data = {
            "username": "login_test_user",
            "email": "login@example.com",
            "password": "test_password_123",
        }

        await api_client.post("/api/v1/auth/register", json=user_data)

        # 登录
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"],
        }

        response = await api_client.post("/api/v1/auth/login", _data=login_data)

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    @pytest.mark.asyncio
    async def test_get_current_user(
        self, api_client: AsyncClient, test_user_token, auth_headers: dict
    ):
        """测试获取当前用户信息"""
        response = await api_client.get("/api/v1/users/me", headers=auth_headers)

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert "username" in data
        assert "email" in data
        assert "role" in data
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_update_user_profile(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """测试更新用户资料"""
        update_data = {
            "email": "updated@example.com",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = await api_client.patch(
            "/api/v1/users/me", json=update_data, headers=auth_headers
        )

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert data["email"] == update_data["email"]
        assert data["first_name"] == update_data["first_name"]
        assert data["last_name"] == update_data["last_name"]

    @pytest.mark.asyncio
    async def test_change_password(self, api_client: AsyncClient, auth_headers: dict):
        """测试修改密码"""
        password_data = {
            "current_password": "test_pass_123",
            "new_password": "new_secure_password_456",
        }

        response = await api_client.post(
            "/api/v1/users/me/change-password", json=password_data, headers=auth_headers
        )

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert "message" in data

        # 使用新密码登录
        login_response = await api_client.post(
            "/api/v1/auth/login",
            _data={
                "username": "test_integration_user",
                "password": password_data["new_password"],
            },
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_user_predictions(
        self,
        api_client: AsyncClient,
        db_session,
        sample_prediction_data,
        auth_headers: dict,
    ):
        """测试获取用户预测历史"""
        _user = sample_prediction_data["user"]

        # 获取用户预测
        response = await api_client.get(
            "/api/v1/users/me/predictions", headers=auth_headers
        )

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) >= 1

    @pytest.mark.asyncio
    async def test_get_user_statistics(
        self,
        api_client: AsyncClient,
        db_session,
        sample_prediction_data,
        auth_headers: dict,
    ):
        """测试获取用户统计信息"""
        _user = sample_prediction_data["user"]

        # 创建更多预测数据
        from src.database.models import Prediction

        predictions = [
            Prediction(
                user_id=user.id,
                match_id=sample_prediction_data["prediction"].match_id,
                _prediction="DRAW",
                confidence=0.6,
                status="COMPLETED",
                is_correct=True,
                created_at=datetime.now(timezone.utc),
            ),
            Prediction(
                user_id=user.id,
                match_id=sample_prediction_data["prediction"].match_id,
                _prediction="AWAY_WIN",
                confidence=0.7,
                status="COMPLETED",
                is_correct=False,
                created_at=datetime.now(timezone.utc),
            ),
        ]

        for pred in predictions:
            db_session.add(pred)
        await db_session.commit()

        # 获取统计
        response = await api_client.get(
            "/api/v1/users/me/statistics", headers=auth_headers
        )

        # 验证响应
        assert response.status_code == 200
        _stats = response.json()
        assert "total_predictions" in stats
        assert "correct_predictions" in stats
        assert "accuracy" in stats
        assert "streak" in stats
        assert stats["total_predictions"] >= 3
        assert "accuracy" in stats
        assert 0 <= stats["accuracy"] <= 1

    @pytest.mark.asyncio
    async def test_admin_get_users(
        self, api_client: AsyncClient, db_session, auth_headers: dict
    ):
        """测试管理员获取用户列表"""
        # 创建多个用户
        from src.database.models import User

        users = []
        for i in range(5):
            _user = User(
                username=f"test_user_{i}",
                email=f"user{i}@example.com",
                password_hash="hashed_password",
                role="user",
            )
            users.append(user)
            db_session.add(user)

        await db_session.commit()

        # 获取用户列表
        response = await api_client.get("/api/v1/users", headers=auth_headers)

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) >= 5

        # 按角色过滤
        response = await api_client.get(
            "/api/v1/users", params={"role": "user"}, headers=auth_headers
        )
        assert response.status_code == 200
        filtered_data = response.json()
        assert all(u["role"] == "user" for u in filtered_data["data"])

    @pytest.mark.asyncio
    async def test_deactivate_user(
        self, api_client: AsyncClient, db_session, auth_headers: dict
    ):
        """测试停用用户"""
        # 创建要停用的用户
        from src.database.models import User

        _user = User(
            username="to_deactivate",
            email="deactivate@example.com",
            password_hash="hashed_password",
            role="user",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()

        # 停用用户
        response = await api_client.patch(
            f"/api/v1/users/{user.id}/deactivate", headers=auth_headers
        )

        # 验证响应
        assert response.status_code == 200

        # 验证数据库
        await db_session.refresh(user)
        assert user.is_active is False

    @pytest.mark.asyncio
    async def test_user_validation(self, api_client: AsyncClient):
        """测试用户数据验证"""
        # 无效的邮箱
        response = await api_client.post(
            "/api/v1/auth/register",
            json={
                "username": "test_user",
                "email": "invalid_email",
                "password": "password123",
            },
        )
        assert response.status_code == 422

        # 密码太短
        response = await api_client.post(
            "/api/v1/auth/register",
            json={
                "username": "test_user",
                "email": "test@example.com",
                "password": "123",
            },
        )
        assert response.status_code == 422

        # 用户名太短
        response = await api_client.post(
            "/api/v1/auth/register",
            json={
                "username": "ab",
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_duplicate_registration(self, api_client: AsyncClient):
        """测试重复注册"""
        user_data = {
            "username": "duplicate_user",
            "email": "duplicate@example.com",
            "password": "password123",
        }

        # 第一次注册
        response1 = await api_client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201

        # 第二次注册相同用户名
        user_data2 = {
            "username": "duplicate_user",
            "email": "different@example.com",
            "password": "password123",
        }
        response2 = await api_client.post("/api/v1/auth/register", json=user_data2)
        assert response2.status_code == 400

        # 第二次注册相同邮箱
        user_data3 = {
            "username": "different_user",
            "email": "duplicate@example.com",
            "password": "password123",
        }
        response3 = await api_client.post("/api/v1/auth/register", json=user_data3)
        assert response3.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_login(self, api_client: AsyncClient):
        """测试无效登录"""
        # 用户不存在
        response = await api_client.post(
            "/api/v1/auth/login",
            _data={"username": "nonexistent_user", "password": "password123"},
        )
        assert response.status_code == 401

        # 密码错误
        # 先注册用户
        await api_client.post(
            "/api/v1/auth/register",
            json={
                "username": "test_user_invalid",
                "email": "invalid@example.com",
                "password": "correct_password",
            },
        )

        # 使用错误密码登录
        response = await api_client.post(
            "/api/v1/auth/login",
            _data={"username": "test_user_invalid", "password": "wrong_password"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_refresh(self, api_client: AsyncClient, test_user_token):
        """测试刷新令牌"""
        # 使用 refresh token 获取新的 access token
        response = await api_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": test_user_token}
        )

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert "access_token" in data
        assert "token_type" in data
