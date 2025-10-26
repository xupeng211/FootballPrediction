"""
Repository模式实现
Repository Pattern Implementation

提供数据访问层的抽象，实现仓储模式以进一步解耦数据访问层。
Provides data access layer abstraction, implementing repository pattern for further decoupling.
"""

from .base import BaseRepository, T
from .match import MatchRepository
from .prediction import PredictionRepository
from .user import UserRepository
from .team_repository import TeamRepository

__all__ = [
    "BaseRepository",
    "T",
    "MatchRepository",
    "PredictionRepository",
    "UserRepository",
    "TeamRepository",
]
