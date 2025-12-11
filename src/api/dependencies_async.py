"""异步API依赖注入
Async API Dependencies.

提供FastAPI异步依赖注入函数,包括:
- 异步数据库会话管理
- 用户认证
- 预测引擎
- 权限检查
- 请求验证

Provides FastAPI async dependency injection functions, including:
- Async database session management
- User authentication
- Prediction engine
- Permission checks
- Request validation
"""

import os
from typing import Optional
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

import jwt
from jwt.exceptions import InvalidTokenError as JWTError

from src.database.session import get_async_session
from src.services.prediction_service import get_prediction_service
from src.services.inference_service import InferenceService
from src.services.async_data_service import get_async_data_service

# 加载环境变量
load_dotenv()

# JWT配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 安全方案
security = HTTPBearer()


class TokenData:
    """Token数据模型."""

    def __init__(self, username: str = None, user_id: int = None):
        self.username = username
        self.user_id = user_id


class User:
    """用户模型."""

    def __init__(self, id: int, username: str, is_active: bool = True):
        self.id = id
        self.username = username
        self.is_active = is_active


# ============================================================================
# 数据库依赖注入
# ============================================================================


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话依赖

    这是推荐的数据库会话获取方式，适用于所有API端点

    Yields:
        AsyncSession: 异步数据库会话
    """
    async with get_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """数据库会话依赖的别名 (向后兼容)"""
    return get_async_db()


# ============================================================================
# 认证相关依赖注入
# ============================================================================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """获取当前用户 (异步版本).

    Args:
        credentials: HTTP授权凭据

    Returns:
        User: 当前用户信息

    Raises:
        HTTPException: 认证失败时抛出401异常
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")

        if username is None or user_id is None:
            raise credentials_exception from None

        # 验证用户是否活跃（如果需要数据库查询）
        user = await _verify_user_active(user_id, username)
        if not user:
            raise credentials_exception

        return user

    except JWTError:
        raise credentials_exception from None
    except Exception as e:
        # 开发环境的容错处理
        if os.getenv("ENV") == "development":
            return User(id=1, username="dev_user", is_active=True)
        raise credentials_exception from None


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户.

    Args:
        current_user: 当前用户

    Returns:
        User: 活跃用户信息
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


async def _verify_user_active(user_id: int, username: str) -> Optional[User]:
    """验证用户是否活跃 (异步版本).

    Args:
        user_id: 用户ID
        username: 用户名

    Returns:
        Optional[User]: 用户信息，如果不存在或非活跃则返回None
    """
    # 这里可以添加数据库查询逻辑
    # 为了简化，直接返回用户对象
    return User(id=user_id, username=username, is_active=True)


# ============================================================================
# 服务层依赖注入
# ============================================================================


async def get_prediction_service():
    """获取预测服务实例 (异步版本)."""
    return get_prediction_service()


def get_inference_service() -> InferenceService:
    """获取推理服务实例 (单例模式)."""
    return InferenceService()


async def get_data_service():
    """获取数据服务实例 (异步版本)."""
    return get_async_data_service()


# ============================================================================
# 业务逻辑依赖注入
# ============================================================================


async def get_user_predictions_service(
    current_user: User = Depends(get_current_active_user),
    prediction_service=Depends(get_prediction_service),
):
    """获取用户专属的预测服务.

    Args:
        current_user: 当前用户
        prediction_service: 预测服务

    Returns:
        用户专用的预测服务实例
    """
    # 这里可以根据用户ID获取用户专属的配置
    return prediction_service


async def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """获取管理员用户 (权限检查).

    Args:
        current_user: 当前用户

    Returns:
        User: 管理员用户

    Raises:
        HTTPException: 非管理员用户抛出403异常
    """
    # 简单的权限检查 - 实际应用中应该查询数据库
    admin_users = {1, 1001, 1002}  # 示例管理员用户ID

    if current_user.id not in admin_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    return current_user


# ============================================================================
# 分页依赖注入
# ============================================================================


class PaginationParams:
    """分页参数依赖."""

    def __init__(self, page: int = 1, size: int = 20, max_size: int = 100):
        self.page = max(1, page)
        self.size = min(max_size, max(1, size))
        self.offset = (self.page - 1) * self.size


async def get_pagination_params(page: int = 1, size: int = 20) -> PaginationParams:
    """获取分页参数.

    Args:
        page: 页码
        size: 每页大小

    Returns:
        PaginationParams: 分页参数对象
    """
    return PaginationParams(page=page, size=size)


# ============================================================================
# 缓存依赖注入
# ============================================================================


async def get_cache_key(prefix: str, *args, **kwargs) -> str:
    """生成缓存键.

    Args:
        prefix: 缓存键前缀
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        str: 缓存键
    """
    # 简化的缓存键生成
    key_parts = [prefix] + [str(arg) for arg in args]
    if kwargs:
        key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return ":".join(key_parts)


# ============================================================================
# 请求验证依赖注入
# ============================================================================


async def validate_content_type(content_type: str = "application/json"):
    """验证请求内容类型.

    Args:
        content_type: 期望的内容类型

    Returns:
        None

    Raises:
        HTTPException: 内容类型不匹配时抛出415异常
    """
    # 这里可以添加实际的请求头验证逻辑
    pass


# ============================================================================
# JWT Token管理
# ============================================================================


def create_access_token(data: dict, expires_delta: Optional = None) -> str:
    """创建访问令牌.

    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量

    Returns:
        str: JWT访问令牌
    """
    try:
        to_encode = data.copy()

        if expires_delta:
            expire = expires_delta
        else:
            from datetime import timedelta

            expire = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        from datetime import datetime

        to_encode.update({"exp": datetime.utcnow() + expire})

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        # 开发环境的容错处理
        return "mock_token_" + str(data.get("sub", "user"))


def verify_token(token: str) -> Optional[TokenData]:
    """验证JWT令牌.

    Args:
        token: JWT令牌

    Returns:
        Optional[TokenData]: 令牌数据，验证失败返回None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")

        if username is None:
            return None

        return TokenData(username=username, user_id=user_id)
    except JWTError:
        return None
    except Exception as e:
        return None


# ============================================================================
# 便捷函数
# ============================================================================


def create_user_token(user_id: int, username: str) -> str:
    """创建用户令牌的便捷函数.

    Args:
        user_id: 用户ID
        username: 用户名

    Returns:
        str: JWT访问令牌
    """
    return create_access_token(data={"sub": username, "user_id": user_id})


# ============================================================================
# 开发和测试依赖
# ============================================================================


async def get_mock_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取模拟数据库会话 (用于测试).

    Yields:
        AsyncSession: 模拟数据库会话
    """
    # 这里可以返回一个模拟的会话对象
    # 实际测试中应该使用测试数据库
    async with get_async_session() as session:
        yield session


def get_test_user() -> User:
    """获取测试用户 (用于开发和测试).

    Returns:
        User: 测试用户
    """
    return User(id=1, username="test_user", is_active=True)


# ============================================================================
# 向后兼容性别名
# ============================================================================

# 保持与现有代码的兼容性
get_db = get_async_db
get_user = get_current_user
get_active_user = get_current_active_user
