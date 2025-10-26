"""
Odds - 数据库模块

提供 odds 相关的数据库功能。

主要功能：
- [待补充 - Odds的主要功能]

使用示例：
    from database.models import Odds
    # 使用示例代码

注意事项：
- [待补充 - 使用注意事项]
"""

from ..base import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    CheckConstraint,
    DECIMAL,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

"""
足球比赛赔率数据模型

存储不同博彩公司的赔率信息，包括胜平负、大小球、让球等市场。
"""

from typing import Any, Dict, Optional
from sqlalchemy import DECIMAL, CheckConstraint, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, String, func
from src.database.base import BaseModel
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

class MarketType(Enum):
    """赔率市场类型"""

    ONE_X_TWO = "1x2"  # 胜平负
    OVER_UNDER = "over_under"  # 大小球
    ASIAN_HANDICAP = "asian_handicap"  # 亚洲让球
    BOTH_TEAMS_SCORE = "both_teams_score"  # 双方进球

class Odds(BaseModel):
    __table_args__ = {'extend_existing': True}
    __tablename__ = "odds"