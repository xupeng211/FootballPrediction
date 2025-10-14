"""
认证模块测试
"""

import pytest
import time
from datetime import datetime, timedelta
from jose import jwt, JWTError

from src.security.auth import (
    AuthManager,
    Role,
    Permission,
    TokenType,
    ROLE_PERMISSIONS,
    get_user_permissions,
    get_auth_manager,
)


class TestAuthManager:
    """认证管理器测试"""

    def setup_method(self):
        """设置测试环境"""
        self.secret_key = "test-secret-key-for-testing-only"
        self.auth = AuthManager(secret_key=self.secret_key)

    def test_create_access_token(self):
        """测试创建访问令牌"""
        data = {"sub": "user123", "roles": [Role.USER]}
        token = self.auth.create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 50

        # 验证token可以解码
        payload = jwt.decode(token, self.secret_key, algorithms=[self.auth.algorithm])
        assert payload["sub"] == "user123"
        assert payload["type"] == TokenType.ACCESS
        assert "exp" in payload

    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        data = {"sub": "user123", "roles": [Role.USER]}
        token = self.auth.create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 50

        # 验证token可以解码
        payload = jwt.decode(token, self.secret_key, algorithms=[self.auth.algorithm])
        assert payload["sub"] == "user123"
        assert payload["type"] == TokenType.REFRESH

    def test_verify_token_valid(self):
        """测试验证有效令牌"""
        data = {"sub": "user123", "roles": [Role.USER]}
        token = self.auth.create_access_token(data)

        payload = self.auth.verify_token(token, TokenType.ACCESS)
        assert payload["sub"] == "user123"
        assert payload["roles"] == [Role.USER]
        assert payload["type"] == TokenType.ACCESS

    def test_verify_token_invalid_signature(self):
        """测试验证无效签名的令牌"""
        # 使用不同的密钥创建token
        other_auth = AuthManager(secret_key="other-secret")
        token = other_auth.create_access_token({"sub": "user123"})

        # 尝试验证
        with pytest.raises(JWTError):
            self.auth.verify_token(token)

    def test_verify_token_expired(self):
        """测试验证过期令牌"""
        # 创建过期的令牌
        data = {"sub": "user123"}
        token = self.auth.create_access_token(
            data,
            expires_delta=timedelta(seconds=-1),  # 已过期
        )

        with pytest.raises(JWTError) as exc_info:
            self.auth.verify_token(token)
        assert "expired" in str(exc_info.value).lower()

    def test_refresh_access_token(self):
        """测试刷新访问令牌"""
        data = {"sub": "user123", "roles": [Role.USER], "permissions": ["read"]}
        refresh_token = self.auth.create_refresh_token(data)

        new_access_token = self.auth.refresh_access_token(refresh_token)

        assert isinstance(new_access_token, str)
        assert new_access_token != refresh_token

        # 验证新token
        payload = self.auth.verify_token(new_access_token)
        assert payload["sub"] == "user123"
        assert payload["roles"] == [Role.USER]

    def test_refresh_with_invalid_token(self):
        """测试使用无效令牌刷新"""
        invalid_token = "invalid.token.here"

        with pytest.raises(JWTError):
            self.auth.refresh_access_token(invalid_token)

    def test_password_hashing(self):
        """测试密码哈希和验证"""
        password = "test_password_123"

        # 哈希密码
        hashed = self.auth.get_password_hash(password)
        assert hashed != password
        assert hashed.startswith("$2b$")

        # 验证密码
        assert self.auth.verify_password(password, hashed) is True
        assert self.auth.verify_password("wrong_password", hashed) is False

    def test_token_with_different_expiry(self):
        """测试不同过期时间的令牌"""
        data = {"sub": "user123"}

        # 短期令牌
        short_token = self.auth.create_access_token(
            data, expires_delta=timedelta(minutes=5)
        )

        # 长期令牌
        long_token = self.auth.create_access_token(
            data, expires_delta=timedelta(days=7)
        )

        assert short_token != long_token

        # 验证两个token都有效
        assert self.auth.verify_token(short_token) is not None
        assert self.auth.verify_token(long_token) is not None


class TestPermissions:
    """权限测试"""

    def test_role_permissions_mapping(self):
        """测试角色权限映射"""
        # 管理员应该有所有权限
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.CREATE_PREDICTION in admin_perms
        assert Permission.DELETE_USER in admin_perms
        assert Permission.MANAGE_USERS in admin_perms

        # 访客应该只有读取权限
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.READ_PREDICTION in viewer_perms
        assert Permission.CREATE_PREDICTION not in viewer_perms
        assert Permission.DELETE_USER not in viewer_perms

    def test_get_user_permissions(self):
        """测试获取用户所有权限"""
        # 用户角色
        user_perms = get_user_permissions([Role.USER])
        assert Permission.CREATE_PREDICTION in user_perms
        assert Permission.READ_PREDICTION in user_perms
        assert Permission.MANAGE_USERS not in user_perms

        # 多个角色
        multi_perms = get_user_permissions([Role.USER, Role.MODERATOR])
        assert Permission.CREATE_PREDICTION in multi_perms
        assert Permission.UPDATE_USER in multi_perms

        # 空角色列表
        empty_perms = get_user_permissions([])
        assert empty_perms == []

    def test_permission_hierarchy(self):
        """测试权限层级"""
        admin_perms = set(get_user_permissions([Role.ADMIN]))
        mod_perms = set(get_user_permissions([Role.MODERATOR]))
        user_perms = set(get_user_permissions([Role.USER]))
        viewer_perms = set(get_user_permissions([Role.VIEWER]))

        # 权限层级：admin > mod > user > viewer
        assert viewer_perms.issubset(user_perms)
        assert user_perms.issubset(mod_perms)
        assert mod_perms.issubset(admin_perms)


class TestGetAuthManager:
    """测试全局认证管理器"""

    def test_get_auth_manager_singleton(self):
        """测试认证管理器单例"""
        auth1 = get_auth_manager()
        auth2 = get_auth_manager()
        assert auth1 is auth2

    def test_auth_manager_with_env_secret(self, monkeypatch):
        """测试使用环境变量密钥"""
        # 设置环境变量
        monkeypatch.setenv("FP_JWT_SECRET_KEY", "env-secret-key")

        # 获取认证管理器
        auth = get_auth_manager()
        assert auth.secret_key == "env-secret-key"

    def test_auth_manager_generates_secret(self):
        """测试无密钥时生成临时密钥"""
        # 清除环境变量
        if "FP_JWT_SECRET_KEY" in os.environ:
            del os.environ["FP_JWT_SECRET_KEY"]

        # 获取认证管理器（会生成临时密钥）
        auth = get_auth_manager()
        assert auth.secret_key is not None
        assert len(auth.secret_key) >= 32


class TestIntegration:
    """集成测试"""

    def test_complete_auth_flow(self):
        """测试完整的认证流程"""
        auth = AuthManager(secret_key="test-secret-key")

        # 1. 用户登录数据
        user_data = {
            "sub": "user123",
            "roles": [Role.USER],
            "permissions": get_user_permissions([Role.USER]),
        }

        # 2. 创建令牌
        access_token = auth.create_access_token(user_data)
        refresh_token = auth.create_refresh_token(user_data)

        # 3. 验证访问令牌
        payload = auth.verify_token(access_token)
        assert payload["sub"] == "user123"
        assert Role.USER in payload["roles"]

        # 4. 刷新令牌
        new_access_token = auth.refresh_access_token(refresh_token)
        new_payload = auth.verify_token(new_access_token)
        assert new_payload["sub"] == "user123"

        # 5. 令牌应该不同
        assert access_token != new_access_token
        assert refresh_token != new_access_token

    def test_token_permissions(self):
        """测试令牌权限信息"""
        auth = AuthManager(secret_key="test-secret-key")

        # 创建带权限的令牌
        data = {
            "sub": "admin123",
            "roles": [Role.ADMIN],
            "permissions": [Permission.MANAGE_USERS, Permission.DELETE_USER],
        }
        token = auth.create_access_token(data)

        # 验证权限信息
        payload = auth.verify_token(token)
        assert Role.ADMIN in payload["roles"]
        assert Permission.MANAGE_USERS in payload["permissions"]
        assert Permission.DELETE_USER in payload["permissions"]

    def test_token_expiry_time(self):
        """测试令牌过期时间"""
        auth = AuthManager(secret_key="test-secret-key", access_token_expire_minutes=30)

        data = {"sub": "user123"}
        token = auth.create_access_token(data)

        # 解码token检查过期时间
        payload = jwt.decode(token, auth.secret_key, algorithms=[auth.algorithm])
        exp_time = datetime.fromtimestamp(payload["exp"])
        iat_time = datetime.fromtimestamp(payload["iat"])

        # 应该是30分钟后过期
        assert (exp_time - iat_time).seconds // 60 == 30


if __name__ == "__main__":
    pytest.main([__file__])
