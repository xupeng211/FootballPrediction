"""认证API模块."""

from typing import Any, Optional

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Mock用户数据
MOCK_USERS = {
    1: {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "password": "admin123",
        "is_active": True,
        "role": "admin",
    }
}


async def get_user_by_id(user_id: int):
    """根据ID获取用户.

    Args:
        user_id: 用户ID

    Returns:
        用户对象或None
    """
    user_data = MOCK_USERS.get(user_id)
    if user_data:
        return type("User", (), user_data)()  # 创建简单的用户对象
    return None


@router.post("/login")
async def login(username: str, password: str) -> dict[str, Any]:
    """用户登录."""
    # 简化的登录逻辑
    return {
        "access_token": "sample_token",
        "token_type": "bearer",
        "user_id": 1,
        "username": username,
    }


@router.get("/me")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """获取当前用户信息."""
    # 简化的用户信息
    return {
        "id": 1,
        "username": "demo_user",
        "email": "demo@example.com",
        "is_active": True,
    }


@router.post("/logout")
async def logout() -> dict[str, str]:
    """用户登出."""
    return {"message": "Successfully logged out"}
