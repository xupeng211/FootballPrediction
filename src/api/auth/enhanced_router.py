from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .enhanced_security import (
    EnhancedSecurity,
    PasswordManager,
    Permission,
    RefreshTokenRequest,
    TokenManager,
    TokenResponse,
    UserCredentials,
    UserInfo,
    create_user_tokens,
    get_client_identifier,
    rate_limiter,
    user_store,
)

"""
增强的认证API路由器
Enhanced Authentication API Router

提供企业级的用户认证、令牌管理、权限控制等功能。
"""

router = APIRouter(prefix="/auth", tags=["authentication"])


async def login(request: Request, credentials: UserCredentials) -> TokenResponse:
    """
    用户登录

    - **username**: 用户名（3-50字符）
    - **password**: 密码（8-128字符，必须包含大小写字母和数字）

    返回访问令牌和刷新令牌。
    """
    # 速率限制检查
    client_id = get_client_identifier(request)
    if not rate_limiter.is_allowed(
        f"login:{client_id}", limit=5, window=300
    ):  # 5次/5分钟
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录尝试过于频繁，请稍后再试",
        )

    # 验证用户凭据
    user = user_store.verify_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )

    # 创建令牌
    tokens = create_user_tokens(credentials.username)

    return tokens


async def refresh_token(
    request: Request, token_request: RefreshTokenRequest
) -> TokenResponse:
    """
    刷新访问令牌

    使用刷新令牌获取新的访问令牌。
    """
    # 速率限制检查
    client_id = get_client_identifier(request)
    if not rate_limiter.is_allowed(
        f"refresh:{client_id}", limit=10, window=300
    ):  # 10次/5分钟
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="刷新令牌请求过于频繁"
        )

    try:
        # 验证刷新令牌
        payload = TokenManager.verify_token(token_request.refresh_token, "refresh")
        username = payload.get("sub")

        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌"
            )

        # 验证刷新令牌是否在存储中
        user_id = user_store.verify_refresh_token(token_request.refresh_token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌已撤销或不存在",
            )

        # 撤销旧令牌
        user_store.revoke_refresh_token(token_request.refresh_token)

        # 创建新令牌
        tokens = create_user_tokens(username)

        return tokens

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌刷新失败"
        ) from e


async def logout(
    request: RefreshTokenRequest, current_user: UserInfo = Depends(EnhancedSecurity())
) -> dict[str, str]:
    """
    用户登出

    撤销刷新令牌，使其无法再用于获取新的访问令牌。
    """
    try:
        # 验证并撤销刷新令牌
        TokenManager.verify_token(request.refresh_token, "refresh")
        user_store.revoke_refresh_token(request.refresh_token)

        return {"message": "成功登出"}

    except Exception:
        # 即使令牌无效也返回成功，避免泄露信息
        return {"message": "成功登出"}


async def get_current_user(
    current_user: UserInfo = Depends(EnhancedSecurity()),
) -> UserInfo:
    """
    获取当前用户信息

    需要有效的访问令牌。
    """
    return current_user


async def change_password(
    current_password: str,
    new_password: str,
    current_user: UserInfo = Depends(EnhancedSecurity([Permission.WRITE])),
) -> dict[str, str]:
    """
    修改密码

    需要写权限。
    """
    # 验证新密码格式
    try:
        UserCredentials(username=current_user.username, password=new_password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"新密码格式无效: {str(e)}"
        ) from None

    # 获取当前用户数据
    user_data = user_store.get_user(current_user.username)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 验证当前密码
    if not PasswordManager.verify_password(
        current_password, user_data["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误"
        )

    # 更新密码
    user_data["password_hash"] = PasswordManager.hash_password(new_password)
    user_store.users[current_user.username] = user_data

    return {"message": "密码修改成功"}


async def verify_token(
    current_user: UserInfo = Depends(EnhancedSecurity()),
) -> dict[str, Any]:
    """
    验证令牌有效性

    检查当前访问令牌是否有效并返回令牌信息。
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "permissions": current_user.permissions,
        "expires_at": None,  # 可以从令牌中解析过期时间
    }


async def revoke_all_tokens(
    current_user: UserInfo = Depends(EnhancedSecurity([Permission.ADMIN])),
) -> dict[str, str]:
    """
    撤销用户所有刷新令牌

    需要管理员权限。
    """
    # 清除所有刷新令牌
    user_store.refresh_tokens.clear()

    return {"message": "所有刷新令牌已撤销"}


async def auth_health() -> dict[str, Any]:
    """
    认证系统健康检查
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "2.0.0",
        "features": {
            "jwt_authentication": True,
            "password_encryption": True,
            "rate_limiting": True,
            "permission_control": True,
            "token_refresh": True,
        },
    }


async def auth_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """认证异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(UTC).isoformat(),
            "path": str(request.url),
        },
    )


async def rate_limit_middleware(request: Request, call_next):
    """速率限制中间件"""
    # 对认证相关的端点应用速率限制
    if "/auth/" in str(request.url):
        client_id = get_client_identifier(request)

        # 全局速率限制
        if not rate_limiter.is_allowed(f"global:{client_id}", limit=100, window=3600):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": True,
                    "message": "请求过于频繁，请稍后再试",
                    "retry_after": 3600,
                },
            )

    response = await call_next(request)
    return response
