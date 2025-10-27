"""
仓储依赖注入配置
Repository Dependency Injection Configuration

为FastAPI提供仓储实例的依赖注入。
Provides dependency injection for repository instances in FastAPI.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_async_session
from .base import Repository
from .match import MatchRepository, ReadOnlyMatchRepository
from .prediction import PredictionRepository, ReadOnlyPredictionRepository
from .provider import RepositoryProvider, get_repository_provider
from .user import ReadOnlyUserRepository, UserRepository


# 仓储提供者依赖
async def get_repository_provider_dependency() -> RepositoryProvider:
    """获取仓储提供者依赖"""
    return get_repository_provider()


# 预测仓储依赖
async def get_prediction_repository(
    session: AsyncSession = Depends(get_async_session),
) -> PredictionRepository:
    """获取预测仓储依赖"""
    provider = get_repository_provider()
    return provider.get_prediction_repository(session, read_only=False)


async def get_read_only_prediction_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ReadOnlyPredictionRepository:
    """获取只读预测仓储依赖"""
    provider = get_repository_provider()
    return provider.get_prediction_repository(session, read_only=True)


# 用户仓储依赖
async def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    """获取用户仓储依赖"""
    provider = get_repository_provider()
    return provider.get_user_repository(session, read_only=False)


async def get_read_only_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ReadOnlyUserRepository:
    """获取只读用户仓储依赖"""
    provider = get_repository_provider()
    return provider.get_user_repository(session, read_only=True)


# 比赛仓储依赖
async def get_match_repository(
    session: AsyncSession = Depends(get_async_session),
) -> MatchRepository:
    """获取比赛仓储依赖"""
    provider = get_repository_provider()
    return provider.get_match_repository(session, read_only=False)


async def get_read_only_match_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ReadOnlyMatchRepository:
    """获取只读比赛仓储依赖"""
    provider = get_repository_provider()
    return provider.get_match_repository(session, read_only=True)


# 类型化依赖别名（更好的IDE支持和类型检查）
PredictionRepoDep = Annotated[PredictionRepository, Depends(get_prediction_repository)]
ReadOnlyPredictionRepoDep = Annotated[
    ReadOnlyPredictionRepository, Depends(get_read_only_prediction_repository)
]

UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
ReadOnlyUserRepoDep = Annotated[
    ReadOnlyUserRepository, Depends(get_read_only_user_repository)
]

MatchRepoDep = Annotated[MatchRepository, Depends(get_match_repository)]
ReadOnlyMatchRepoDep = Annotated[
    ReadOnlyMatchRepository, Depends(get_read_only_match_repository)
]

# 通用仓储依赖类型
RepositoryDep = Annotated[Repository, Depends(get_prediction_repository)]
