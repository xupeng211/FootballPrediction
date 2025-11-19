from typing import Optional

"""仓储模式实现
Repository Pattern Implementation.

提供数据访问的抽象层.
Provides abstraction layer for data access.
"""

from .base import BaseRepository, QuerySpec

# 导入依赖类型
try:
    from .dependencies import (
        MatchRepoDep,
        PredictionRepoDep,
        ReadOnlyMatchRepoDep,
        ReadOnlyPredictionRepoDep,
    )
except ImportError:
    # 如果依赖模块不存在，提供占位符
    MatchRepoDep = None
    PredictionRepoDep = None
    ReadOnlyMatchRepoDep = None
    ReadOnlyPredictionRepoDep = None

__all__ = [
    "BaseRepository",
    "QuerySpec",
    "MatchRepoDep",
    "PredictionRepoDep",
    "ReadOnlyMatchRepoDep",
    "ReadOnlyPredictionRepoDep",
]
