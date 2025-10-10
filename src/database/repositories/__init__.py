"""
数据库仓储模块

实现Repository模式，提供数据访问的抽象层。
"""

from .base import BaseRepository, RepositoryConfig
from .match import MatchRepository
from .prediction import PredictionRepository
from .user import UserRepository
from .team import TeamRepository

__all__ = [
    "BaseRepository",
    "RepositoryConfig",
    "MatchRepository",
    "PredictionRepository",
    "UserRepository",
    "TeamRepository",
]
