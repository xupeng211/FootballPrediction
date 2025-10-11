"""
Features - 数据库模块

提供 features 相关的数据库功能。

主要功能：
- [待补充 - Features的主要功能]

使用示例：
    from database.models import Features
    # 使用示例代码

注意事项：
- [待补充 - 使用注意事项]
"""

from typing import Optional
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    Boolean,
    DECIMAL,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

"""
features.py
features

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings
from sqlalchemy import DECIMAL, Boolean
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from ..base import BaseModel
from .feature_mod import feature_entity
from .feature_mod import feature_metadata
from .feature_mod import feature_types
from .feature_mod import models
from sqlalchemy import Boolean
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


# 添加原始的类定义以保持兼容性
class TeamType(Enum):
    """球队类型枚举"""

    HOME = "home"  # 主队
    AWAY = "away"  # 客队


class Features(BaseModel):
    """
    特征数据表模型

    存储用于机器学习预测的各种特征
    """

    __tablename__ = "features"

    # 关联信息
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, comment="比赛ID"
    )

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, comment="球队ID"
    )

    team_type: Mapped[TeamType] = mapped_column(
        SQLEnum(TeamType), nullable=False, comment="球队类型（主队/客队）"
    )

    # 近期表现（最近5场）
    recent_5_wins: Mapped[int] = mapped_column(
        Integer, default=0, comment="近5场胜利数"
    )

    recent_5_draws: Mapped[int] = mapped_column(
        Integer, default=0, comment="近5场平局数"
    )

    recent_5_losses: Mapped[int] = mapped_column(
        Integer, default=0, comment="近5场失败数"
    )

    recent_5_goals_for: Mapped[int] = mapped_column(
        Integer, default=0, comment="近5场进球数"
    )

    recent_5_goals_against: Mapped[int] = mapped_column(
        Integer, default=0, comment="近5场失球数"
    )

    # 主客场记录
    home_wins: Mapped[int] = mapped_column(Integer, default=0, comment="主场胜利数")
    home_draws: Mapped[int] = mapped_column(Integer, default=0, comment="主场平局数")
    home_losses: Mapped[int] = mapped_column(Integer, default=0, comment="主场失败数")
    away_wins: Mapped[int] = mapped_column(Integer, default=0, comment="客场胜利数")
    away_draws: Mapped[int] = mapped_column(Integer, default=0, comment="客场平局数")
    away_losses: Mapped[int] = mapped_column(Integer, default=0, comment="客场失败数")

    # 对战历史
    h2h_wins = mapped_column(Integer, default=0, comment="对战历史胜利数")
    h2h_draws = mapped_column(Integer, default=0, comment="对战历史平局数")
    h2h_losses = mapped_column(Integer, default=0, comment="对战历史失败数")
    h2h_goals_for = mapped_column(Integer, default=0, comment="对战历史进球数")
    h2h_goals_against = mapped_column(Integer, default=0, comment="对战历史失球数")

    # 联赛排名和积分
    league_position = mapped_column(Integer, nullable=True, comment="当前联赛排名")
    points = mapped_column(Integer, nullable=True, comment="当前积分")
    goal_difference = mapped_column(Integer, nullable=True, comment="净胜球")

    # 其他特征
    days_since_last_match = mapped_column(
        Integer, nullable=True, comment="距离上场比赛天数"
    )

    is_derby = mapped_column(Boolean, nullable=True, comment="是否为德比战")

    avg_possession: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="平均控球率"
    )

    avg_shots_per_game: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均射门次数"
    )

    # 扩展特征
    avg_goals_per_game: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均进球数"
    )

    avg_shots_on_target: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均射正次数"
    )

    avg_corners_per_game: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均角球数"
    )

    avg_goals_conceded: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均失球数"
    )

    clean_sheets: Mapped[int] = mapped_column(Integer, default=0, comment="零封场次")

    avg_cards_per_game: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="场均红黄牌数"
    )

    # 连胜/连败记录
    current_form: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="当前状态（如 WWDLW）"
    )

    win_streak = mapped_column(Integer, default=0, comment="连胜场次")
    unbeaten_streak = mapped_column(Integer, default=0, comment="不败场次")

    # 关系定义
    match = relationship("Match", back_populates="features")
    team = relationship("Team", back_populates="features")


warnings.warn(
    "直接从 features 导入已弃用。" "请从 src/database/models/feature_mod 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容

# 导出所有类
__all__ = [
    "Features",
    "TeamType",
    "feature_entity",
    "feature_types",
    "feature_metadata",
    "models",
]
