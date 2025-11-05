"""
认证API模块
"""

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

@router.post("/login")
async def login(username: str, password: str) -> Dict[str, Any]:
    """用户登录"""
    # 简化的登录逻辑
    return {
        "access_token": "sample_token",
        "token_type": "bearer",
        "user_id": 1,
        "username": username
    }

@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """获取当前用户信息"""
    # 简化的用户信息
    return {
        "id": 1,
        "username": "demo_user",
        "email": "demo@example.com",
        "is_active": True
    }

@router.post("/logout")
async def logout() -> Dict[str, str]:
    """用户登出"""
    return {"message": "Successfully logged out"}