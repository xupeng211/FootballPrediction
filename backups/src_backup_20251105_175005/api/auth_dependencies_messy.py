"""认证依赖模块 (测试版本)
Authentication Dependencies Module (Test Version).
"""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


# 简单的token数据类
class TokenData:
    def __init__(self, user_id: int = None, username: str = None, role: str = None):
        self.user_id = user_id
        self.username = username
        self.role = role


# 简单的速率限制器
class RateLimiter:
    """简单的速率限制器."""

    def __init__(self):
        self.requests = {}

    @staticmethod
    def check_limit(key: str, limit: int = 100) -> bool:
        """检查限制."""
        return True


# 安全头部配置
class SecurityHeaders:
    """安全头部配置."""

    @staticmethod
    def get_headers() -> dict:
        """获取安全头部."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
        }


# 认证上下文管理器
class AuthContext:
    """认证上下文管理器."""

    @staticmethod
    def create_context(user_data: dict) -> dict:
        """创建认证上下文."""
        return {
            "user_id": user_data.get("user_id"),
            "username": user_data.get("username"),
            "role": user_data.get("role", "user"),
            "timestamp": "2025-01-01T00:00:00Z",
        }


# 全局实例
rate_limiter_messy = RateLimiter()
security_headers_messy = SecurityHeaders()
security_messy = HTTPBearer()


async def get_current_user_messy(
    credentials: HTTPAuthorizationCredentials = Security(security_messy),
):
    """获取当前用户 (测试版本)."""
    try:
        # 模拟用户数据
        token_data = TokenData(user_id=1, username="test_user_messy", role="user")
        return token_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
