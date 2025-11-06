"""
认证依赖模块
Authentication Dependencies Module
"""

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


# 简单的token数据类
class TokenData:
    def __init__(self, user_id: int = None, username: str = None, role: str = None):
        self.user_id = user_id
        self.username = username
        self.role = role


# 简单的速率限制器
class RateLimiter:
    """简单的速率限制器"""

    def __init__(self):
        self.requests = {}

    def is_allowed(self, key: str, limit: int = 100) -> bool:
        """检查是否允许请求"""
        return True


# 安全头部配置
class SecurityHeaders:
    """安全头部配置"""

    def __init__(self):
        self.headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
        }


# 全局实例
rate_limiter = RateLimiter()
security_headers = SecurityHeaders()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    """获取当前用户"""
    try:
        # 这里应该解析JWT token，暂时返回模拟数据
        token_data = TokenData(user_id=1, username="test_user", role="user")
        return token_data
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    request: Request,
):
    """获取当前用户（可选）"""
    # 尝试从Authorization头获取token
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    try:
        if not auth_header.startswith("Bearer "):
            return None

        auth_header.split(" ")[1]
        # 这里应该解析JWT token，暂时返回模拟数据用于测试
        token_data = TokenData(user_id=1, username="test_user", role="user")
        return token_data
    except Exception:
        return None


async def require_admin(current_user: TokenData = Depends(get_current_user)):
    """需要管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user
