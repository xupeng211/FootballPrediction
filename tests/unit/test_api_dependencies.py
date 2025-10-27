#!/usr/bin/env python3
"""
API依赖注入测试
测试 src.api.dependencies 模块的功能
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.api.dependencies import get_current_user, validate_secret_key


@pytest.mark.unit
class TestAPIDependencies:
    """API依赖注入测试"""

    @patch("src.api.dependencies.jwt.decode")
    @patch("src.api.dependencies.HTTPAuthorizationCredentials")
    def test_get_current_user_valid_token(self, mock_credentials, mock_jwt_decode):
        """测试有效token的用户获取"""
        # 模拟有效token
        mock_credentials.scheme = "Bearer"
        mock_credentials.credentials = "valid_token_here"

        # 模拟JWT解码结果
        mock_jwt_decode.return_value = {"sub": "123", "role": "user"}

        with patch("src.api.dependencies.SECRET_KEY", "test-secret-key"):
            with patch("src.api.dependencies.ALGORITHM", "HS256"):
                result = get_current_user(mock_credentials)

        # 验证返回用户信息
        assert result["id"] == 123
        assert result["role"] == "user"
        assert result["token"] == "valid_token_here"

    @patch("src.api.dependencies.jwt.decode")
    @patch("src.api.dependencies.HTTPAuthorizationCredentials")
    def test_get_current_user_invalid_token(self, mock_credentials, mock_jwt_decode):
        """测试无效token的用户获取"""
        from fastapi import HTTPException

        from src.api.dependencies import JWTError

        mock_credentials.scheme = "Bearer"
        mock_credentials.credentials = "invalid_token"

        # 模拟JWT解码失败
        mock_jwt_decode.side_effect = JWTError("Invalid token")

        with patch("src.api.dependencies.SECRET_KEY", "test-secret-key"):
            with patch("src.api.dependencies.ALGORITHM", "HS256"):
                with pytest.raises(HTTPException) as exc_info:
                    get_current_user(mock_credentials)

        # 验证抛出认证异常
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @patch("src.api.dependencies.HTTPAuthorizationCredentials")
    def test_get_current_user_no_token(self, mock_credentials):
        """测试没有token的用户获取"""
        from fastapi import HTTPException

        mock_credentials.scheme = "Bearer"
        mock_credentials.credentials = None

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials)

        # 验证抛出认证异常
        assert exc_info.value.status_code == 401

    def test_verify_admin_permission_admin_user(self):
        """测试管理员权限验证 - 管理员用户"""
        admin_user = {
            "sub": "admin123",
            "username": "admin",
            "roles": ["admin", "user"],
        }

        # 管理员用户应该通过验证
        result = verify_admin_permission(admin_user)
        assert result is True

    def test_verify_admin_permission_regular_user(self):
        """测试管理员权限验证 - 普通用户"""
        regular_user = {"sub": "user123", "username": "regularuser", "roles": ["user"]}

        # 普通用户应该权限验证失败
        result = verify_admin_permission(regular_user)
        assert result is False

    def test_verify_admin_permission_no_roles(self):
        """测试管理员权限验证 - 无角色用户"""
        user_no_roles = {"sub": "user123", "username": "norolesuser"}

        # 无角色用户应该权限验证失败
        result = verify_admin_permission(user_no_roles)
        assert result is False

    def test_verify_admin_permission_empty_roles(self):
        """测试管理员权限验证 - 空角色用户"""
        user_empty_roles = {"sub": "user123", "username": "emptyrolesuser", "roles": []}

        # 空角色用户应该权限验证失败
        result = verify_admin_permission(user_empty_roles)
        assert result is False

    def test_verify_admin_permission_case_insensitive(self):
        """测试管理员权限验证 - 大小写不敏感"""
        admin_user_caps = {"sub": "admin123", "username": "ADMIN", "roles": ["ADMIN"]}

        # 大写的ADMIN角色应该被识别为管理员
        result = verify_admin_permission(admin_user_caps)
        assert result is True

    @patch("src.api.dependencies.SessionLocal")
    def test_get_db_session(self, mock_session_local):
        """测试获取数据库会话"""
        Mock()
        mock_db = Mock()
        mock_session_local.return_value = mock_db

        with patch("src.api.dependencies.SessionLocal", mock_session_local):
            result = get_db_session()

        # 验证返回数据库会话
        assert result == mock_db
        mock_session_local.assert_called_once()

    def test_environment_variables(self):
        """测试环境变量配置"""
        # 测试默认值
        with patch.dict(os.environ, {}, clear=True):
            from src.api.dependencies import ALGORITHM, SECRET_KEY

            assert SECRET_KEY == "your-secret-key-here"
            assert ALGORITHM == "HS256"

        # 测试自定义值
        with patch.dict(
            os.environ, {"JWT_SECRET_KEY": "custom-secret-key", "ALGORITHM": "RS256"}
        ):
            # 重新导入模块以测试环境变量
            import importlib

            import src.api.dependencies

            importlib.reload(src.api.dependencies)

            assert src.api.dependencies.SECRET_KEY == "custom-secret-key"
            assert src.api.dependencies.ALGORITHM == "RS256"

    def test_jwt_import_fallback(self):
        """测试JWT导入失败的回退机制"""
        # 测试在缺少python-jose时的情况
        with patch.dict("sys.modules", {"jose": None}):
            try:
                # 重新导入模块触发回退
                import importlib

                import src.api.dependencies

                importlib.reload(src.api.dependencies)

                # 验证回退类存在
                assert hasattr(src.api.dependencies, "JWTError")
            except ImportError:
                # 预期的导入错误，这是正常的
                pass

    def test_security_scheme(self):
        """测试安全方案配置"""
        from src.api.dependencies import security

        # 验证安全方案是HTTPBearer
        assert hasattr(security, "scheme")
        assert security.scheme == "bearer"

    def test_logger_configuration(self):
        """测试日志配置"""
        from src.api.dependencies import logger

        # 验证logger已配置
        assert logger is not None
        assert hasattr(logger, "info") or hasattr(logger, "log")
