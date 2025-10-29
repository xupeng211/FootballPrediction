#!/usr/bin/env python3
"""
API依赖注入简化测试
测试 src.api.dependencies 模块的核心功能
"""

import os

import pytest

from src.api.dependencies import (
    ALGORITHM,
    SECRET_KEY,
    get_current_user,
    security,
    validate_secret_key,
)


@pytest.mark.unit
class TestAPIDependenciesSimple:
    """API依赖注入简化测试"""

    def test_secret_key_configuration(self):
        """测试密钥配置"""
        # 验证SECRET_KEY已配置
        assert SECRET_KEY is not None
        assert isinstance(SECRET_KEY, str)
        assert len(SECRET_KEY) > 0

    def test_algorithm_configuration(self):
        """测试算法配置"""
        # 验证ALGORITHM已配置
        assert ALGORITHM is not None
        assert isinstance(ALGORITHM, str)
        assert ALGORITHM in ["HS256", "RS256", "HS384", "HS512"]

    def test_security_scheme(self):
        """测试安全方案"""
        # 验证security对象已配置
        assert security is not None
        assert hasattr(security, "scheme")
        assert security.scheme == "bearer"

    def test_validate_secret_key_default_warning(self):
        """测试默认密钥警告"""
        with patch("src.api.dependencies.SECRET_KEY", "your-secret-key-here"):
            with patch("src.api.dependencies.logger") as mock_logger:
                validate_secret_key()
                mock_logger.warning.assert_called_with("⚠️ 使用默认JWT密钥，请立即更改！")

    def test_validate_secret_key_short_warning(self):
        """测试短密钥警告"""
        with patch("src.api.dependencies.SECRET_KEY", "short"):
            with patch("src.api.dependencies.logger") as mock_logger:
                validate_secret_key()
                mock_logger.warning.assert_called_with("⚠️ JWT密钥长度不足32位，建议使用更强的密钥")

    def test_validate_secret_key_valid(self):
        """测试有效密钥无警告"""
        valid_key = "this-is-a-very-secure-secret-key-32-chars-long"
        with patch("src.api.dependencies.SECRET_KEY", valid_key):
            with patch("src.api.dependencies.logger") as mock_logger:
                validate_secret_key()
                mock_logger.warning.assert_not_called()

    def test_environment_variables_loading(self):
        """测试环境变量加载"""
        # 验证从环境变量加载配置
        with patch.dict(os.environ, {"SECRET_KEY": "env-secret-key", "ALGORITHM": "RS256"}):
            # 重新导入模块测试环境变量
            import importlib

            import src.api.dependencies

            importlib.reload(src.api.dependencies)

            assert src.api.dependencies.SECRET_KEY == "env-secret-key"
            assert src.api.dependencies.ALGORITHM == "RS256"

    @patch("src.api.dependencies.jwt.decode")
    @patch("src.api.dependencies.HTTPAuthorizationCredentials")
    def test_get_current_user_structure(self, mock_credentials, mock_jwt_decode):
        """测试获取当前用户的基本结构"""
        # 设置模拟凭证
        mock_credentials.scheme = "Bearer"
        mock_credentials.credentials = "test_token"

        # 设置模拟JWT解码
        mock_jwt_decode.return_value = {"sub": "123", "role": "admin"}

        with patch("src.api.dependencies.SECRET_KEY", "test-secret-key"):
            with patch("src.api.dependencies.ALGORITHM", "HS256"):
                result = get_current_user(mock_credentials)

        # 验证返回结构
        assert isinstance(result, dict)
        assert "id" in result
        assert "role" in result
        assert "token" in result
        assert result["id"] == 123
        assert result["role"] == "admin"
        assert result["token"] == "test_token"

    @patch("src.api.dependencies.jwt.decode")
    @patch("src.api.dependencies.HTTPAuthorizationCredentials")
    def test_get_current_user_missing_sub(self, mock_credentials, mock_jwt_decode):
        """测试缺少sub字段的用户"""
        from fastapi import HTTPException

        mock_credentials.scheme = "Bearer"
        mock_credentials.credentials = "test_token"

        # JWT解码缺少sub字段
        mock_jwt_decode.return_value = {"role": "user"}

        with patch("src.api.dependencies.SECRET_KEY", "test-secret-key"):
            with patch("src.api.dependencies.ALGORITHM", "HS256"):
                with pytest.raises(HTTPException) as exc_info:
                    get_current_user(mock_credentials)

        # 验证抛出认证异常
        assert exc_info.value.status_code == 401

    def test_jwt_error_handling(self):
        """测试JWT错误处理"""
from src.api.dependencies import JWTError

        # 验证JWTError类存在
        assert JWTError is not None
        assert issubclass(JWTError, Exception)

    def test_import_fallback_mechanism(self):
        """测试导入回退机制"""
        # 验证模块即使缺少python-jose也能导入

        # 如果python-jose不存在，jwt函数会抛出ImportError
        # 而JWTError应该是一个自定义异常类
        assert JWTError is not None

    def test_module_structure(self):
        """测试模块结构完整性"""
        # 验证关键组件存在
        assert hasattr(get_current_user, "__call__")
        assert callable(validate_secret_key)

        # 验证配置变量存在
        assert "SECRET_KEY" in globals()
        assert "ALGORITHM" in globals()
        assert "security" in globals()

    def test_initialization_sequence(self):
        """测试初始化序列"""
        # 验证模块初始化时调用了validate_secret_key
        with patch("src.api.dependencies.validate_secret_key") as mock_validate:
            import importlib

            import src.api.dependencies

            importlib.reload(src.api.dependencies)

            # 模块重新加载时应该调用validate_secret_key
            assert mock_validate.called
