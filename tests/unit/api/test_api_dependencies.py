from unittest.mock import patch, AsyncMock, MagicMock
"""
API依赖注入模块测试
"""

pytest_plugins = "asyncio"

import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from typing import Dict

from src.api.dependencies import (
    get_current_user,
    get_admin_user,
    get_prediction_engine,
    get_redis_manager,
    verify_prediction_permission,
    rate_limit_check,
    SECRET_KEY,
    ALGORITHM,
)


@pytest.mark.unit

class TestGetCurrentUser:
    """获取当前用户测试"""

    @pytest.fixture
    def valid_token(self):
        """有效的JWT token"""
        payload = {
            "sub": "123",
            "role": "user",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @pytest.fixture
    def admin_token(self):
        """管理员JWT token"""
        payload = {
            "sub": "456",
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @pytest.fixture
    def expired_token(self):
        """过期的JWT token"""
        payload = {
            "sub": "789",
            "role": "user",
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @pytest.fixture
    def invalid_token(self):
        """无效的token"""
        return "invalid.token.here"

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, valid_token):
        """测试有效token获取用户"""
        credentials = HTTPAuthorizationCredentials(
            scheme="bearer", credentials=valid_token
        )

        _user = await get_current_user(credentials)

        assert user["id"] == 123
        assert user["role"] == "user"
        assert user["token"] == valid_token

    @pytest.mark.asyncio
    async def test_get_current_user_admin_token(self, admin_token):
        """测试管理员token获取用户"""
        credentials = HTTPAuthorizationCredentials(
            scheme="bearer", credentials=admin_token
        )

        _user = await get_current_user(credentials)

        assert user["id"] == 456
        assert user["role"] == "admin"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, invalid_token):
        """测试无效token"""
        credentials = HTTPAuthorizationCredentials(
            scheme="bearer", credentials=invalid_token
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials)

        assert exc.value.status_code == 401
        assert "Could not validate credentials" in exc.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, expired_token):
        """测试过期token"""
        credentials = HTTPAuthorizationCredentials(
            scheme="bearer", credentials=expired_token
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials)

        assert exc.value.status_code == 401
        assert "Could not validate credentials" in exc.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_missing_subject(self):
        """测试缺少subject的token"""
        payload = {"role": "user", "exp": datetime.utcnow() + timedelta(hours=1)}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        credentials = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials)

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_default_role(self):
        """测试默认角色"""
        payload = {"sub": "999", "exp": datetime.utcnow() + timedelta(hours=1)}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        credentials = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)

        _user = await get_current_user(credentials)

        assert user["id"] == 999
        assert user["role"] == "user"  # 默认角色


class TestGetAdminUser:
    """获取管理员用户测试"""

    @pytest.mark.asyncio
    async def test_get_admin_user_success(self):
        """测试管理员用户验证成功"""
        admin_user = {"id": 456, "role": "admin", "token": "admin_token"}

        _result = await get_admin_user(admin_user)

        assert _result == admin_user

    @pytest.mark.asyncio
    async def test_get_admin_user_insufficient_privileges(self):
        """测试权限不足"""
        normal_user = {"id": 123, "role": "user", "token": "user_token"}

        with pytest.raises(HTTPException) as exc:
            await get_admin_user(normal_user)

        assert exc.value.status_code == 403
        assert "Admin privileges required" in exc.value.detail

    @pytest.mark.asyncio
    async def test_get_admin_user_missing_role(self):
        """测试缺少角色信息"""
        user_no_role = {"id": 789, "token": "test_token"}

        with pytest.raises(HTTPException) as exc:
            await get_admin_user(user_no_role)

        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_admin_user_empty_role(self):
        """测试空角色"""
        user_empty_role = {"id": 999, "role": "", "token": "test_token"}

        with pytest.raises(HTTPException) as exc:
            await get_admin_user(user_empty_role)

        assert exc.value.status_code == 403


class TestGetPredictionEngine:
    """获取预测引擎测试"""

    @pytest.mark.asyncio
    async def test_get_prediction_engine(self):
        """测试获取预测引擎"""
        with patch("src.api.dependencies.get_prediction_engine") as mock_get:
            mock_engine = MagicMock()
            mock_get.return_value = mock_engine

            engine = await get_prediction_engine()

            assert engine is mock_engine
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_prediction_engine_with_exception(self):
        """测试获取预测引擎时发生异常"""
        with patch("src.api.dependencies.get_prediction_engine") as mock_get:
            mock_get.side_effect = Exception("Engine error")

            with pytest.raises(Exception, match="Engine error"):
                await get_prediction_engine()


class TestGetRedisManager:
    """获取Redis管理器测试"""

    @pytest.mark.asyncio
    async def test_get_redis_manager(self):
        """测试获取Redis管理器"""
        with patch("src.api.dependencies.get_redis_manager") as mock_get:
            mock_redis = MagicMock()
            mock_get.return_value = mock_redis

            redis = await get_redis_manager()

            assert redis is mock_redis
            mock_get.assert_called_once()


class TestVerifyPredictionPermission:
    """验证预测权限测试"""

    @pytest.mark.asyncio
    async def test_verify_prediction_permission_success(self):
        """测试权限验证成功"""
        _user = {"id": 123, "role": "user"}
        match_id = 456

        _result = await verify_prediction_permission(match_id, user)

        assert _result is True

    @pytest.mark.asyncio
    async def test_verify_prediction_permission_admin(self):
        """测试管理员权限验证"""
        admin = {"id": 456, "role": "admin"}
        match_id = 789

        _result = await verify_prediction_permission(match_id, admin)

        assert _result is True

    @pytest.mark.asyncio
    async def test_verify_prediction_permission_different_matches(self):
        """测试不同比赛的权限"""
        _user = {"id": 123, "role": "user"}
        _matches = [100, 200, 300, 400]

        for match_id in matches:
            _result = await verify_prediction_permission(match_id, user)
            assert _result is True


class TestRateLimitCheck:
    """速率限制检查测试"""

    @pytest.mark.asyncio
    async def test_rate_limit_check_success(self):
        """测试速率限制检查通过"""
        _user = {"id": 123, "role": "user"}

        _result = await rate_limit_check(user)

        assert _result is True

    @pytest.mark.asyncio
    async def test_rate_limit_check_admin(self):
        """测试管理员速率限制"""
        admin = {"id": 456, "role": "admin"}

        _result = await rate_limit_check(admin)

        assert _result is True

    @pytest.mark.asyncio
    async def test_rate_limit_check_multiple_requests(self):
        """测试多次请求的速率限制"""
        _user = {"id": 789, "role": "user"}

        # 模拟多次请求
        for _ in range(10):
            _result = await rate_limit_check(user)
            assert _result is True


class TestConstants:
    """常量测试"""

    def test_secret_key(self):
        """测试密钥常量"""
        assert SECRET_KEY is not None
        assert isinstance(SECRET_KEY, str)
        assert len(SECRET_KEY) > 0

    def test_algorithm(self):
        """测试算法常量"""
        assert ALGORITHM == "HS256"

    def test_security_bearer(self):
        """测试security对象"""
        from src.api.dependencies import security

        assert security is not None
        assert hasattr(security, "scheme")


class TestJWTIntegration:
    """JWT集成测试"""

    def test_jwt_token_creation_and_validation(self):
        """测试JWT token创建和验证"""
        payload = {
            "sub": "123",
            "role": "user",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
        }

        # 创建token
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        # 验证token
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert decoded["sub"] == "123"
        assert decoded["role"] == "user"

    def test_jwt_token_with_custom_claims(self):
        """测试包含自定义声明的JWT token"""
        payload = {
            "sub": "456",
            "role": "admin",
            "permissions": ["read", "write", "delete"],
            "department": "prediction",
            "exp": datetime.utcnow() + timedelta(hours=2),
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert decoded["permissions"] == ["read", "write", "delete"]
        assert decoded["department"] == "prediction"
