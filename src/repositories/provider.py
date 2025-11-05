"""
仓储提供者
BaseRepository Provider

提供仓储实例的创建和依赖注入配置.
Provides creation and dependency injection configuration for repository instances.
"""

from functools import lru_cache
from typing import Protocol, TypeVar, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Match, Prediction, User

from .base import BaseRepository
from .match import MatchRepository, ReadOnlyMatchRepository
from .prediction import PredictionRepository, ReadOnlyPredictionRepository
from .user import ReadOnlyUserRepository, UserRepository

T = TypeVar("T")
ID = TypeVar("ID")


@runtime_checkable
class BaseRepositoryFactory(Protocol):
    """仓储工厂协议"""

    def create_prediction_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> BaseRepository[Prediction, int]:
        """创建预测仓储"""
        ...

    def create_user_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> BaseRepository[User, int]:
        """创建用户仓储"""
        ...

    def create_match_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> BaseRepository[Match, int]:
        """创建比赛仓储"""
        ...


class DefaultBaseRepositoryFactory:
    """类文档字符串"""

    pass  # 添加pass语句
    """默认仓储工厂实现"""

    @staticmethod
    def create_prediction_repository(
        session: AsyncSession, read_only: bool = False
    ) -> BaseRepository[Prediction, int]:
        """创建预测仓储"""
        if read_only:
            return ReadOnlyPredictionRepository(session, Prediction)
        return PredictionRepository(session, Prediction)

    @staticmethod
    def create_user_repository(
        session: AsyncSession, read_only: bool = False
    ) -> BaseRepository[User, int]:
        """创建用户仓储"""
        if read_only:
            return ReadOnlyUserRepository(session, User)
        return UserRepository(session, User)

    @staticmethod
    def create_match_repository(
        session: AsyncSession, read_only: bool = False
    ) -> BaseRepository[Match, int]:
        """创建比赛仓储"""
        if read_only:
            return ReadOnlyMatchRepository(session, Match)
        return MatchRepository(session, Match)


class BaseRepositoryProvider:
    """仓储提供者

    管理仓储实例的创建和生命周期.
    Manages creation and lifecycle of repository instances.
    """

    def __init__(self, factory: BaseRepositoryFactory = None):
        """函数文档字符串"""
        # 添加pass语句
        self._factory = factory or DefaultBaseRepositoryFactory()
        self._repositories = {}

    def get_prediction_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> BaseRepository[Prediction, int]:
        """获取预测仓储实例"""
        key = f"prediction_{id(session)}_{read_only}"
        if key not in self._repositories:
            self._repositories[key] = self._factory.create_prediction_repository(
                session, read_only
            )
        return self._repositories[key]

    def get_user_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> BaseRepository[User, int]:
        """获取用户仓储实例"""
        key = f"user_{id(session)}_{read_only}"
        if key not in self._repositories:
            self._repositories[key] = self._factory.create_user_repository(
                session, read_only
            )
        return self._repositories[key]

    def get_match_repository(
        self, session: AsyncSession, read_only: bool = False
    ) -> BaseRepository[Match, int]:
        """获取比赛仓储实例"""
        key = f"match_{id(session)}_{read_only}"
        if key not in self._repositories:
            self._repositories[key] = self._factory.create_match_repository(
                session, read_only
            )
        return self._repositories[key]

    def clear_cache(self):
        """函数文档字符串"""
        # 添加pass语句
        """清除仓储缓存"""
        self._repositories.clear()

    def set_factory(self, factory: BaseRepositoryFactory):
        """函数文档字符串"""
        # 添加pass语句
        """设置仓储工厂"""
        self._factory = factory
        self.clear_cache()


# 全局仓储提供者实例
_provider: BaseRepositoryProvider = None


def get_repository_provider() -> BaseRepositoryProvider:
    """获取全局仓储提供者"""
    global _provider
    if _provider is None:
        _provider = BaseRepositoryProvider()
    return _provider


def set_repository_provider(provider: BaseRepositoryProvider):
    """函数文档字符串"""
    pass  # 添加pass语句
    """设置全局仓储提供者"""
    global _provider
    _provider = provider


@lru_cache(maxsize=32)
def _get_repository_cached(
    repository_type: str, session_id: int, read_only: bool
) -> type[BaseRepository]:
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
) -> BaseRepository[Prediction, int]:
    """便捷函数:获取预测仓储"""
    return get_repository_provider().get_prediction_repository(session, read_only)


def get_user_repository(
    session: AsyncSession, read_only: bool = False
) -> BaseRepository[User, int]:
    """便捷函数:获取用户仓储"""
    return get_repository_provider().get_user_repository(session, read_only)


def get_match_repository(
    session: AsyncSession, read_only: bool = False
) -> BaseRepository[Match, int]:
    """便捷函数:获取比赛仓储"""
    return get_repository_provider().get_match_repository(session, read_only)


# 为向后兼容性提供别名
RepositoryProvider = BaseRepositoryProvider
RepositoryFactory = BaseRepositoryFactory  # 添加别名以支持旧的导入
DefaultRepositoryFactory = DefaultBaseRepositoryFactory  # 添加别名以支持旧的导入
