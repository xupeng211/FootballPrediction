"""
仓储提供者
Repository Provider

提供仓储实例的创建和依赖注入配置。
Provides creation and dependency injection configuration for repository instances.
"""

from typing import TypeVar, Type, Protocol, runtime_checkable
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, Repository
from .prediction import PredictionRepository, ReadOnlyPredictionRepository
from .user import UserRepository, ReadOnlyUserRepository
from .match import MatchRepository, ReadOnlyMatchRepository
from ..database.models import Prediction, User, Match


T = TypeVar("T")
ID = TypeVar("ID")


@runtime_checkable
class RepositoryFactory(Protocol):
    """仓储工厂协议"""

    def create_prediction_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> Repository[Prediction, int]:
        """创建预测仓储"""
        ...

    def create_user_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> Repository[User, int]:
        """创建用户仓储"""
        ...

    def create_match_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> Repository[Match, int]:
        """创建比赛仓储"""
        ...


class DefaultRepositoryFactory:
    """默认仓储工厂实现"""

    @staticmethod
    def create_prediction_repository(
        session: AsyncSession, read_only: bool = False
    ) -> Repository[Prediction, int]:
        """创建预测仓储"""
        if read_only:
            return ReadOnlyPredictionRepository(session, Prediction)  # type: ignore
        return PredictionRepository(session, Prediction)

    @staticmethod
    def create_user_repository(
        session: AsyncSession, read_only: bool = False
    ) -> Repository[User, int]:
        """创建用户仓储"""
        if read_only:
            return ReadOnlyUserRepository(session, User)  # type: ignore
        return UserRepository(session, User)

    @staticmethod
    def create_match_repository(
        session: AsyncSession, read_only: bool = False
    ) -> Repository[Match, int]:
        """创建比赛仓储"""
        if read_only:
            return ReadOnlyMatchRepository(session, Match)  # type: ignore
        return MatchRepository(session, Match)


class RepositoryProvider:
    """仓储提供者

    管理仓储实例的创建和生命周期。
    Manages creation and lifecycle of repository instances.
    """

    def __init__(self, factory: RepositoryFactory = None):
        self._factory = factory or DefaultRepositoryFactory()
        self._repositories = {}  # type: ignore

    def get_prediction_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> Repository[Prediction, int]:
        """获取预测仓储实例"""
        key = f"prediction_{id(session)}_{read_only}"
        if key not in self._repositories:
            self._repositories[key] = self._factory.create_prediction_repository(
                session, read_only
            )
        return self._repositories[key]  # type: ignore

    def get_user_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> Repository[User, int]:
        """获取用户仓储实例"""
        key = f"user_{id(session)}_{read_only}"
        if key not in self._repositories:
            self._repositories[key] = self._factory.create_user_repository(
                session, read_only
            )
        return self._repositories[key]  # type: ignore

    def get_match_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> Repository[Match, int]:
        """获取比赛仓储实例"""
        key = f"match_{id(session)}_{read_only}"
        if key not in self._repositories:
            self._repositories[key] = self._factory.create_match_repository(
                session, read_only
            )
        return self._repositories[key]  # type: ignore

    def clear_cache(self):
        """清除仓储缓存"""
        self._repositories.clear()

    def set_factory(self, factory: RepositoryFactory):
        """设置仓储工厂"""
        self._factory = factory
        self.clear_cache()


# 全局仓储提供者实例
_provider: RepositoryProvider = None  # type: ignore


def get_repository_provider() -> RepositoryProvider:
    """获取全局仓储提供者"""
    global _provider
    if _provider is None:
        _provider = RepositoryProvider()  # type: ignore
    return _provider


def set_repository_provider(provider: RepositoryProvider):
    """设置全局仓储提供者"""
    global _provider
    _provider = provider


@lru_cache(maxsize=32)
def _get_repository_cached(
    repository_type: str, session_id: int, read_only: bool
) -> Type[BaseRepository]:
    """缓存的仓储类型获取"""
    if repository_type == "prediction":
        return ReadOnlyPredictionRepository if read_only else PredictionRepository
    elif repository_type == "user":
        return ReadOnlyUserRepository if read_only else UserRepository
    elif repository_type == "match":
        return ReadOnlyMatchRepository if read_only else MatchRepository
    else:
        raise ValueError(f"Unknown repository type: {repository_type}")


# 便捷函数
def get_prediction_repository(
    session: AsyncSession, read_only: bool = False
) -> Repository[Prediction, int]:
    """便捷函数：获取预测仓储"""
    return get_repository_provider().get_prediction_repository(session, read_only)


def get_user_repository(
    session: AsyncSession, read_only: bool = False
) -> Repository[User, int]:
    """便捷函数：获取用户仓储"""
    return get_repository_provider().get_user_repository(session, read_only)


def get_match_repository(
    session: AsyncSession, read_only: bool = False
) -> Repository[Match, int]:
    """便捷函数：获取比赛仓储"""
    return get_repository_provider().get_match_repository(session, read_only)
