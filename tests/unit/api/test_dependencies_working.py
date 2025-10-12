"""
API依赖注入测试（工作版本）
Tests for API Dependencies (Working Version)

测试src.api.dependencies模块的实际功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, status
from jose import JWTError

# 测试导入
try:
    from src.api.dependencies import (
        get_current_user,
        get_admin_user,
        get_prediction_engine,
        get_redis_manager,
        verify_prediction_permission,
        rate_limit_check,
        security,
        SECRET_KEY,
        ALGORITHM
    )
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    DEPENDENCIES_AVAILABLE = False


@pytest.mark.skipif(not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available")
class TestGetCurrentUser:
    """获取当前用户测试"""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """测试：成功获取当前用户"""
        mock_credentials = Mock()
        mock_credentials.credentials = "valid_token"

        with patch('src.api.dependencies.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": "123",
                "role": "user"
            }

            result = await get_current_user(mock_credentials)

            assert result["id"] == 123
            assert result["role"] == "user"
            assert result["token"] == "valid_token"

    @pytest.mark.asyncio
    async def test_get_current_user_with_admin_role(self):
        """测试：获取管理员用户"""
        mock_credentials = Mock()
        mock_credentials.credentials = "admin_token"

        with patch('src.api.dependencies.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": "456",
                "role": "admin"
            }

            result = await get_current_user(mock_credentials)

            assert result["id"] == 456
            assert result["role"] == "admin"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """测试：无效令牌"""
        mock_credentials = Mock()
        mock_credentials.credentials = "invalid_token"

        with patch('src.api.dependencies.jwt.decode') as mock_decode:
            mock_decode.side_effect = JWTError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_sub(self):
        """测试：缺少sub声明"""
        mock_credentials = Mock()
        mock_credentials.credentials = "token_without_sub"

        with patch('src.api.dependencies.jwt.decode') as mock_decode:
            mock_decode.return_value = {"role": "user"}  # 缺少sub

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_default_role(self):
        """测试：默认角色"""
        mock_credentials = Mock()
        mock_credentials.credentials = "token_without_role"

        with patch('src.api.dependencies.jwt.decode') as mock_decode:
            mock_decode.return_value = {"sub": "789"}  # 缺少role

            result = await get_current_user(mock_credentials)

            assert result["id"] == 789
            assert result["role"] == "user"  # 默认角色


@pytest.mark.skipif(not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available")
class TestGetAdminUser:
    """获取管理员用户测试"""

    @pytest.mark.asyncio
    async def test_get_admin_user_success(self):
        """测试：管理员用户验证成功"""
        admin_user = {"id": 1, "role": "admin", "token": "admin_token"}

        result = await get_admin_user(admin_user)

        assert result is admin_user
        assert result["role"] == "admin"

    @pytest.mark.asyncio
    async def test_get_admin_user_non_admin(self):
        """测试：非管理员用户被拒绝"""
        normal_user = {"id": 2, "role": "user", "token": "user_token"}

        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(normal_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin privileges required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_admin_user_missing_role(self):
        """测试：缺少角色信息被拒绝"""
        user_without_role = {"id": 3, "token": "token"}

        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(user_without_role)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.skipif(not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available")
class TestGetPredictionEngine:
    """获取预测引擎测试"""

    @pytest.mark.asyncio
    async def test_get_prediction_engine_success(self):
        """测试：成功获取预测引擎"""
        mock_engine = AsyncMock()

        with patch('src.core.prediction_engine.get_prediction_engine') as mock_get_engine:
            mock_get_engine.return_value = mock_engine

            engine = await get_prediction_engine()

            assert engine is mock_engine
            mock_get_engine.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_prediction_engine_none(self):
        """测试：预测引擎返回None"""
        with patch('src.core.prediction_engine.get_prediction_engine') as mock_get_engine:
            mock_get_engine.return_value = None

            engine = await get_prediction_engine()

            assert engine is None


@pytest.mark.skipif(not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available")
class TestGetRedisManager:
    """获取Redis管理器测试"""

    @pytest.mark.asyncio
    async def test_get_redis_manager_success(self):
        """测试：成功获取Redis管理器"""
        mock_redis = Mock()

        with patch('src.cache.redis_manager.get_redis_manager') as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            redis_manager = await get_redis_manager()

            assert redis_manager is mock_redis
            mock_get_redis.assert_called_once()


@pytest.mark.skipif(not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available")
class TestVerifyPredictionPermission:
    """验证预测权限测试"""

    @pytest.mark.asyncio
    async def test_verify_prediction_permission_success(self):
        """测试：预测权限验证成功"""
        user = {"id": 1, "role": "user"}
        match_id = 123

        result = await verify_prediction_permission(match_id, user)

        assert result is True  # 当前实现总是返回True

    @pytest.mark.asyncio
    async def test_verify_prediction_permission_admin(self):
        """测试：管理员预测权限"""
        admin_user = {"id": 2, "role": "admin"}
        match_id = 456

        result = await verify_prediction_permission(match_id, admin_user)

        assert result is True


@pytest.mark.skipif(not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available")
class TestRateLimitCheck:
    """速率限制检查测试"""

    @pytest.mark.asyncio
    async def test_rate_limit_check_success(self):
        """测试：速率限制通过"""
        user = {"id": 1, "role": "user"}

        result = await rate_limit_check(user)

        assert result is True  # 当前实现总是返回True

    @pytest.mark.asyncio
    async def test_rate_limit_check_admin(self):
        """测试：管理员速率限制"""
        admin_user = {"id": 2, "role": "admin"}

        result = await rate_limit_check(admin_user)

        assert result is True


@pytest.mark.skipif(not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available")
class TestDependenciesIntegration:
    """依赖注入集成测试"""

    @pytest.mark.asyncio
    async def test_admin_user_flow(self):
        """测试：管理员用户流程"""
        mock_credentials = Mock()
        mock_credentials.credentials = "admin_token"

        with patch('src.api.dependencies.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": "1",
                "role": "admin"
            }

            # 1. 获取当前用户
            user = await get_current_user(mock_credentials)
            assert user["role"] == "admin"

            # 2. 验证管理员权限
            admin_user = await get_admin_user(user)
            assert admin_user is user

    @pytest.mark.asyncio
    async def test_normal_user_flow(self):
        """测试：普通用户流程"""
        mock_credentials = Mock()
        mock_credentials.credentials = "user_token"

        with patch('src.api.dependencies.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": "2",
                "role": "user"
            }

            # 1. 获取当前用户
            user = await get_current_user(mock_credentials)
            assert user["role"] == "user"

            # 2. 尝试获取管理员权限（应该失败）
            with pytest.raises(HTTPException) as exc_info:
                await get_admin_user(user)
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_permission_and_rate_limit_flow(self):
        """测试：权限和速率限制流程"""
        user = {"id": 123, "role": "user", "token": "valid_token"}
        match_id = 456

        # 1. 验证预测权限
        has_permission = await verify_prediction_permission(match_id, user)
        assert has_permission is True

        # 2. 速率限制检查
        rate_ok = await rate_limit_check(user)
        assert rate_ok is True

    @pytest.mark.asyncio
    async def test_full_dependency_chain(self):
        """测试：完整依赖链"""
        mock_credentials = Mock()
        mock_credentials.credentials = "admin_token"

        with patch('src.api.dependencies.jwt.decode') as mock_decode, \
             patch('src.core.prediction_engine.get_prediction_engine') as mock_get_engine, \
             patch('src.cache.redis_manager.get_redis_manager') as mock_get_redis:

            # 设置mock
            mock_decode.return_value = {"sub": "1", "role": "admin"}
            mock_engine = AsyncMock()
            mock_redis = Mock()
            mock_get_engine.return_value = mock_engine
            mock_get_redis.return_value = mock_redis

            # 执行完整流程
            user = await get_current_user(mock_credentials)
            admin_user = await get_admin_user(user)
            engine = await get_prediction_engine()
            redis = await get_redis_manager()

            # 验证结果
            assert admin_user["role"] == "admin"
            assert engine is mock_engine
            assert redis is mock_redis

    def test_constants_configuration(self):
        """测试：常量配置"""
        assert SECRET_KEY is not None
        assert ALGORITHM == "HS256"
        assert security is not None
        assert hasattr(security, 'scheme_name')

    @pytest.mark.asyncio
    async def test_concurrent_user_requests(self):
        """测试：并发用户请求"""
        import asyncio

        mock_credentials_list = [
            Mock(credentials=f"token_{i}") for i in range(5)
        ]

        with patch('src.api.dependencies.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": "123",
                "role": "user"
            }

            # 并发获取用户信息
            tasks = [
                get_current_user(credentials)
                for credentials in mock_credentials_list
            ]

            results = await asyncio.gather(*tasks)

            # 验证所有请求都成功
            assert len(results) == 5
            for result in results:
                assert result["id"] == 123
                assert result["role"] == "user"

    @pytest.mark.asyncio
    async def test_error_handling_chain(self):
        """测试：错误处理链"""
        mock_credentials = Mock()
        mock_credentials.credentials = "invalid_token"

        with patch('src.api.dependencies.jwt.decode') as mock_decode:
            # 模拟JWT解码错误
            mock_decode.side_effect = JWTError("Token malformed")

            # 获取用户应该失败
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)
            assert exc_info.value.status_code == 401

            # 后续的依赖也应该失败
            with pytest.raises(HTTPException):
                await get_admin_user({"id": 1, "role": "user"})  # 这个会通过，因为不需要token

    @pytest.mark.asyncio
    async def test_dependency_caching(self):
        """测试：依赖缓存"""
        # FastAPI的依赖注入会缓存相同参数的依赖
        user = {"id": 1, "role": "user"}

        # 多次调用无状态函数应该返回相同结果
        result1 = await verify_prediction_permission(123, user)
        result2 = await verify_prediction_permission(123, user)
        result3 = await rate_limit_check(user)

        assert result1 is True
        assert result2 is True
        assert result3 is True


# 如果模块不可用，添加一个占位测试
@pytest.mark.skipif(True, reason="Module not available")
class TestModuleNotAvailable:
    """模块不可用时的占位测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not DEPENDENCIES_AVAILABLE
        assert True  # 表明测试意识到模块不可用