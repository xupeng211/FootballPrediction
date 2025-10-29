"""
用户认证API包

提供完整的用户认证功能，包括：
- 用户注册和登录
- JWT令牌管理
- 密码重置和邮箱验证
- 权限控制
"""

from .router import router

__all__ = ["router"]
