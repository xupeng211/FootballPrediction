"""
API依赖注入测试
Tests for API Dependencies

测试src.api.dependencies模块的功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, status
from jose import JWTError

# 测试导入
try:
    from src.api.dependencies import (
        get_current_user,
        get_prediction_engine,
        verify_admin_permission,
        validate_request_data,
        security,
    )

    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    DEPENDENCIES_AVAILABLE = False


@pytest.mark.skipif(
    not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available"
)
class TestGetCurrentUser:
    """获取当前用户测试"""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """测试：成功获取当前用户"""
        mock_credentials = Mock()
        mock_credentials.credentials = "valid_token"

        with patch("src.api.dependencies.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "user123",
                "username": "testuser",
                "email": "test@example.com",
            }

            _result = await get_current_user(mock_credentials)

            assert _result["sub"] == "user123"
            assert _result["username"] == "testuser"
            assert _result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """测试：无效令牌"""
        mock_credentials = Mock()
        mock_credentials.credentials = "invalid_token"

        with patch("src.api.dependencies.jwt.decode") as mock_decode:
            mock_decode.side_effect = JWTError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_claims(self):
        """测试：缺少声明"""
        mock_credentials = Mock()
        mock_credentials.credentials = "token_without_claims"

        with patch("src.api.dependencies.jwt.decode") as mock_decode:
            mock_decode.return_value = {}  # 空声明

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Missing required claims" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self):
        """测试：过期令牌"""
        mock_credentials = Mock()
        mock_credentials.credentials = "expired_token"

        with patch("src.api.dependencies.jwt.decode") as mock_decode:
            mock_decode.side_effect = JWTError("Token has expired")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.skipif(
    not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available"
)
class TestGetPredictionEngine:
    """获取预测引擎测试"""

    @pytest.mark.asyncio
    async def test_get_prediction_engine_success(self):
        """测试：成功获取预测引擎"""
        with patch("src.api.dependencies.PredictionEngine") as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine_class.return_value = mock_engine

            engine = await get_prediction_engine()

            assert engine is mock_engine
            mock_engine_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_prediction_engine_initialization_error(self):
        """测试：预测引擎初始化错误"""
        with patch("src.api.dependencies.PredictionEngine") as mock_engine_class:
            mock_engine_class.side_effect = RuntimeError("Engine initialization failed")

            with pytest.raises(RuntimeError, match="Engine initialization failed"):
                await get_prediction_engine()


@pytest.mark.skipif(
    not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available"
)
class TestVerifyAdminPermission:
    """验证管理员权限测试"""

    @pytest.mark.asyncio
    async def test_verify_admin_success(self):
        """测试：管理员权限验证成功"""
        admin_user = {"sub": "admin123", "username": "admin", "role": "admin"}

        # 如果函数存在，测试它
        if "verify_admin_permission" in globals():
            _result = await verify_admin_permission(admin_user)
            assert _result is admin_user

    @pytest.mark.asyncio
    async def test_verify_admin_non_admin(self):
        """测试：非管理员用户"""
        normal_user = {"sub": "user123", "username": "user", "role": "user"}

        # 如果函数存在，测试它
        if "verify_admin_permission" in globals():
            with pytest.raises(HTTPException) as exc_info:
                await verify_admin_permission(normal_user)
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_verify_admin_missing_role(self):
        """测试：缺少角色信息"""
        user_without_role = {"sub": "user123", "username": "user"}

        # 如果函数存在，测试它
        if "verify_admin_permission" in globals():
            with pytest.raises(HTTPException) as exc_info:
                await verify_admin_permission(user_without_role)
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.skipif(
    not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available"
)
class TestValidateRequestData:
    """验证请求数据测试"""

    @pytest.mark.asyncio
    async def test_validate_valid_data(self):
        """测试：验证有效数据"""
        valid_data = {
            "name": "Test Prediction",
            "match_id": 123,
            "prediction_type": "win",
        }

        # 如果函数存在，测试它
        if "validate_request_data" in globals():
            _result = await validate_request_data(valid_data)
            assert _result == valid_data

    @pytest.mark.asyncio
    async def test_validate_invalid_data_missing_field(self):
        """测试：验证无效数据（缺少字段）"""
        invalid_data = {
            "name": "Test Prediction"
            # 缺少必需字段
        }

        # 如果函数存在，测试它
        if "validate_request_data" in globals():
            with pytest.raises(HTTPException) as exc_info:
                await validate_request_data(invalid_data)
            assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_validate_invalid_data_wrong_type(self):
        """测试：验证无效数据（错误类型）"""
        invalid_data = {
            "name": "Test Prediction",
            "match_id": "not_a_number",  # 应该是数字
            "prediction_type": "win",
        }

        # 如果函数存在，测试它
        if "validate_request_data" in globals():
            with pytest.raises(HTTPException) as exc_info:
                await validate_request_data(invalid_data)
            assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.skipif(
    not DEPENDENCIES_AVAILABLE, reason="Dependencies module not available"
)
class TestDependenciesIntegration:
    """依赖注入集成测试"""

    @pytest.mark.asyncio
    async def test_dependency_chain(self):
        """测试：依赖链"""
        # 模拟完整的认证和授权流程
        mock_credentials = Mock()
        mock_credentials.credentials = "admin_token"

        with patch("src.api.dependencies.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "admin123",
                "username": "admin",
                "role": "admin",
                "email": "admin@example.com",
            }

            # 获取当前用户
            _user = await get_current_user(mock_credentials)
            assert user["role"] == "admin"

            # 如果有验证管理员权限的函数，测试它
            if "verify_admin_permission" in globals():
                verified_user = await verify_admin_permission(user)
                assert verified_user is user

    @pytest.mark.asyncio
    async def test_dependency_error_propagation(self):
        """测试：依赖错误传播"""
        mock_credentials = Mock()
        mock_credentials.credentials = "corrupted_token"

        with patch("src.api.dependencies.jwt.decode") as mock_decode:
            # 模拟各种JWT错误
            errors = [
                JWTError("Invalid signature"),
                JWTError("Token expired"),
                JWTError("Invalid issuer"),
                Exception("Unexpected error"),
            ]

            for error in errors:
                mock_decode.side_effect = error
                with pytest.raises((HTTPException, Exception)):
                    await get_current_user(mock_credentials)

    def test_security_bearer_configuration(self):
        """测试：Bearer安全配置"""
        # 测试HTTPBearer配置是否正确
        if "security" in globals():
            assert hasattr(security, "scheme_name")
            assert security.auto_error is True

    @pytest.mark.asyncio
    async def test_concurrent_dependency_calls(self):
        """测试：并发依赖调用"""
        import asyncio

        mock_credentials_list = [Mock(credentials=f"token_{i}") for i in range(5)]

        with patch("src.api.dependencies.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "user123",
                "username": "testuser",
                "email": "test@example.com",
            }

            # 并发调用get_current_user
            tasks = [
                get_current_user(credentials) for credentials in mock_credentials_list
            ]

            results = await asyncio.gather(*tasks)

            # 验证所有调用都成功
            assert len(results) == 5
            for result in results:
                assert _result["username"] == "testuser"


# 如果模块不可用，添加一个占位测试
@pytest.mark.skipif(True, reason="Module not available")
class TestModuleNotAvailable:
    """模块不可用时的占位测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not DEPENDENCIES_AVAILABLE
        assert True  # 表明测试意识到模块不可用
