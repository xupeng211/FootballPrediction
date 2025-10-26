from datetime import timedelta
from sqlalchemy import or_

"""
Match - 数据库模块

提供 match 相关的数据库功能。

主要功能：
- [待补充 - Match的主要功能]

使用示例：
    from database.models import Match
    # 使用示例代码

注意事项：
- [待补充 - 使用注意事项]
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import BaseModel

"""
比赛模型

存储足球比赛的详细信息，包括比赛时间、比分、状态等。
"""


class MatchStatus(Enum):
    """比赛状态枚举"""

    SCHEDULED = "scheduled"  # 已安排
    LIVE = "live"  # 进行中
    FINISHED = "finished"  # 已结束
    CANCELLED = "cancelled"  # 已取消


class MatchResult(Enum):
    """比赛结果枚举"""

    HOME_WIN = "home_win"  # 主队获胜
    AWAY_WIN = "away_win"  # 客队获胜
    DRAW = "draw"  # 平局


class Match(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "matches"
