from typing import Optional

"""Repository模式实现
Repository Pattern Implementation.

提供数据访问层的抽象,实现仓储模式以进一步解耦数据访问层.
Provides data access layer abstraction, implementing repository pattern for further decoupling.
"""

from .base import BaseRepository, T
from .match import MatchRepository
from .prediction import PredictionRepository
from .team_repository import TeamRepository
from .user import UserRepository

__all__ = [
    "BaseRepository",
    "T",
    "MatchRepository",
    "PredictionRepository",
    "UserRepository",
    "TeamRepository",
]