from .base import (
    BaseRepository,
    QuerySpec,
)
from .di import (
    MatchRepoDep,
    PredictionRepoDep,
    ReadOnlyMatchRepoDep,
    ReadOnlyPredictionRepoDep,
    ReadOnlyUserRepoDep,
    RepositoryDep,
    UserRepoDep,
    get_read_only_match_repository,
    get_read_only_prediction_repository,
    get_read_only_user_repository,
)
from .di import get_match_repository as get_match_repo_dep
from .di import get_prediction_repository as get_prediction_repo_dep
from .di import get_user_repository as get_user_repo_dep
from .match import MatchRepository, MatchRepositoryInterface, ReadOnlyMatchRepository
from .prediction import (
    PredictionRepository,
    PredictionRepositoryInterface,
    ReadOnlyPredictionRepository,
)
from .provider import (
    DefaultRepositoryFactory,
    RepositoryFactory,
    RepositoryProvider,
    get_match_repository,
    get_prediction_repository,
    get_repository_provider,
    get_user_repository,
    set_repository_provider,
)
from .user import ReadOnlyUserRepository, UserRepository, UserRepositoryInterface

"""
仓储模式实现
Repository Pattern Implementation

提供数据访问的抽象层.
Provides abstraction layer for data access.
"""

__all__ = [
    # Base classes
    "BaseRepository",
    "QuerySpec",
    # Repository interfaces
    "PredictionRepositoryInterface",
    "UserRepositoryInterface",
    "MatchRepositoryInterface",
    # Repository implementations
    "PredictionRepository",
    "ReadOnlyPredictionRepository",
    "UserRepository",
    "ReadOnlyUserRepository",
    "MatchRepository",
    "ReadOnlyMatchRepository",
    # Provider and factory
    "RepositoryFactory",
    "DefaultRepositoryFactory",
    "RepositoryProvider",
    "get_repository_provider",
    "set_repository_provider",
    "get_prediction_repository",
    "get_user_repository",
    "get_match_repository",
    # Dependency injection
    "get_prediction_repo_dep",
    "get_read_only_prediction_repository",
    "get_user_repo_dep",
    "get_read_only_user_repository",
    "get_match_repo_dep",
    "get_read_only_match_repository",
    "PredictionRepoDep",
    "ReadOnlyPredictionRepoDep",
    "UserRepoDep",
    "ReadOnlyUserRepoDep",
    "MatchRepoDep",
    "ReadOnlyMatchRepoDep",
    "RepositoryDep",
]
