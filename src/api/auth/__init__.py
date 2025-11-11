"""
用户认证API包

提供完整的用户认证功能,包括:
- 用户注册和登录
- JWT令牌管理
- 密码重置和邮箱验证
- 权限控制
"""

import os
import secrets
from .router import router

# 生产环境使用环境变量，测试环境使用安全的默认值
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "test@example.com")
TEST_USER_PASSWORD_HASH = os.getenv(
    "TEST_USER_PASSWORD_HASH",
    "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4QF8xq4.8K"
)

# 测试用的模拟用户数据 (仅用于开发测试)
MOCK_USERS = {
    TEST_USER_EMAIL: {
        "id": 1,
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD_HASH,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
    },
    "admin@example.com": {
        "id": 2,
        "email": "admin@example.com",
        "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4QF8xq4.8K",  # password123
        "is_active": True,
        "is_admin": True,
        "created_at": "2024-01-01T00:00:00Z",
    },
}


# 模拟的Pydantic模型（用于测试）
class UserRegister:
    def __init__(self, email: str, password: str, full_name: str = None):
        self.email = email
        self.password = password
        self.full_name = full_name


class UserLogin:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password


class UserResponse:
    def __init__(
        self, user_id: int, email: str, is_active: bool, full_name: str = None
    ):
        self.id = user_id
        self.email = email
        self.is_active = is_active
        self.full_name = full_name


class TokenResponse:
    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        token_type: str = "bearer",
        expires_in: int = 1800,
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expires_in = expires_in


class RefreshTokenRequest:
    def __init__(self, refresh_token: str):
        self.refresh_token = refresh_token


class PasswordResetRequest:
    def __init__(self, email: str):
        self.email = email


class PasswordResetConfirm:
    def __init__(self, token: str, new_password: str):
        self.token = token
        self.new_password = new_password


class PasswordChangeRequest:
    def __init__(self, current_password: str, new_password: str):
        self.current_password = current_password
        self.new_password = new_password


# 模拟的认证函数（用于测试）
def authenticate_user(email: str, password: str):
    """模拟用户认证函数"""
    user = MOCK_USERS.get(email)
    if user and user["email"] == email:
        return user
    return None


def create_user(email: str, password: str, **kwargs):
    """模拟创建用户函数"""
    user_id = max(user["id"] for user in MOCK_USERS.values()) + 1 if MOCK_USERS else 1
    return {
        "id": user_id,
        "email": email,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        **kwargs,
    }


def get_user_by_id(user_id: int):
    """模拟根据ID获取用户函数"""
    for user in MOCK_USERS.values():
        if user["id"] == user_id:
            return user
    return None


__all__ = [
    "router",
    "MOCK_USERS",
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "RefreshTokenRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "PasswordChangeRequest",
    "authenticate_user",
    "create_user",
    "get_user_by_id",
]
