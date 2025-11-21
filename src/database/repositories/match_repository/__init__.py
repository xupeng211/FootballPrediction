"""Match Repository module.

提供比赛数据的异步访问接口，使用SQLAlchemy 2.0语法.
遵循Repository模式，封装数据访问逻辑.
"""

from .repository import MatchRepository

__all__ = ["MatchRepository"]
