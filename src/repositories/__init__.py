"""
仓储模式实现
Repository Pattern Implementation

提供数据访问的抽象层.
Provides abstraction layer for data access.
"""

from .base import BaseRepository, QuerySpec
from .di import (
    MatchRepoDep,
    PredictionRepoDep,
    ReadOnlyMatchRepoDep,
    ReadOnlyPredictionRepoDep,
)

__all__ = [
    "BaseRepository",
    "QuerySpec",
    "MatchRepoDep",
    "PredictionRepoDep",
    "ReadOnlyMatchRepoDep",
    "ReadOnlyPredictionRepoDep",
]
