"""
API依赖注入
API Dependencies

提供FastAPI依赖注入函数，包括：
- 用户认证
- 预测引擎
- 权限检查
- 请求验证

Provides FastAPI dependency injection functions, including:
- User authentication
- Prediction engine
- Permission checks
- Request validation
"""

from typing import Any,  Dict[str, Any],  Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from src.core.prediction_engine import PredictionEngine
from src.core.logger import get_logger

logger = get_logger(__name__)

# JWT配置
SECRET_KEY = "your-secret-key-here"  # 从环境变量获取
ALGORITHM = "HS256"
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    获取当前用户

    Args:
        credentials: HTTP认证凭据

    Returns:
        Dict[str, Any]: 用户信息

    Raises:
        HTTPException: 认证失败
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 解码JWT token
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id: str = payload.get("sub")
        role: str = payload.get("role", "user")

        if user_id is None:
            raise credentials_exception

        return {"id": int(user_id), "role": role, "token": credentials.credentials}

    except JWTError:
        raise credentials_exception


async def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    获取管理员用户

    Args:
        current_user: 当前用户

    Returns:
        Dict[str, Any]: 管理员用户信息

    Raises:
        HTTPException: 权限不足
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


async def get_prediction_engine() -> Optional["PredictionEngine"]:
    """
    获取预测引擎实例

    Returns:
        PredictionEngine: 预测引擎
    """
    from src.core.prediction_engine import get_prediction_engine

    return await get_prediction_engine()  # type: ignore


async def get_redis_manager() -> Optional[Any]:
    """获取Redis管理器"""
    from src.cache.redis_manager import get_redis_manager

    return get_redis_manager()


async def verify_prediction_permission(
    match_id: int, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    验证预测权限

    Args:
        match_id: 比赛ID
        current_user: 当前用户

    Returns:
        bool: 是否有权限
    """
    # 这里可以实现更复杂的权限逻辑
    # 例如：检查用户是否有访问特定比赛的权限
    return True


async def rate_limit_check(current_user: Dict[str, Any] = Depends(get_current_user)) -> None:
    """
    速率限制检查

    Args:
        current_user: 当前用户

    Returns:
        bool: 是否通过限制
    """
    # 这里可以实现速率限制逻辑
    # 例如：检查用户在时间窗口内的请求次数
    return True
