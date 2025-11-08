from typing import Any

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

"""
认证API模块
"""

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


async def login(username: str, password: str) -> dict[str, Any]:
    """用户登录"""
    # 简化的登录逻辑
    return {
        "access_token": "sample_token",
        "token_type": "bearer",
        "user_id": 1,
        "username": username,
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """获取当前用户信息"""
    # 简化的用户信息
    return {
        "id": 1,
        "username": "demo_user",
        "email": "demo@example.com",
        "is_active": True,
    }


async def logout() -> dict[str, str]:
    """用户登出"""
    return {"message": "Successfully logged out"}
