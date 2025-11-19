from typing import Optional

"""认证依赖模块
Authentication Dependencies Module.

提供API认证和授权相关的依赖注入功能。
Provides authentication and authorization dependency injection functionality for APIs.
"""


# 简单的token数据类
class TokenData:
    """Token数据类."""

    username: str = "test_user"
    user_id: str = "12345"


# 简单的速率限制器
class RateLimiter:
    """简单的速率限制器."""

    def is_allowed(self) -> bool:
        """检查是否允许请求."""
        return True


# 安全头部配置
class SecurityConfig:
    """安全头部配置."""

    def get_headers(self) -> dict[str, str]:
        """获取安全头部."""
        return {
            "x-Content-Type-Options": "nosniff",
            "x-Frame-Options": "DENY",
            "x-XSS-Protection": "1; mode=block",
        }


# 全局实例
rate_limiter = RateLimiter()
security_config = SecurityConfig()


def get_current_user() -> TokenData:
    """获取当前用户."""
    # 这里应该解析JWT token,暂时返回模拟数据
    return TokenData()


def get_current_user_optional() -> TokenData | None:
    """获取当前用户(可选)."""
    # 尝试从Authorization头获取token
    return TokenData()


def require_admin() -> bool:
    """需要管理员权限."""
    return True


__all__ = [
    "TokenData",
    "RateLimiter",
    "SecurityConfig",
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
    "rate_limiter",
    "security_config",
]
