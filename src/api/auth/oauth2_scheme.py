from typing import Optional

"""OAuth2认证方案.

定义JWT令牌的获取和验证方式
"""

from fastapi.security import OAuth2PasswordBearer

# OAuth2密码认证方案
# tokenUrl指向登录端点
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/auth/login",
    scheme_name="JWT",
    auto_error=True,
    description="JWT访问令牌,格式: Bearer <token>",
)
