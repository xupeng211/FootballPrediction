"""
Features - 数据库模块

提供 features 相关的数据库功能.

主要功能：
- 特征实体管理
- 特征元数据管理
- 特征类型定义

使用示例:
    from database.models.features import FeatureEntity, FeatureMetadata
    # 使用示例代码

注意事项:
- 使用SQLAlchemy 2.0语法
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .match import Match
    from .team import Team

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DECIMAL, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import BaseModel


class TeamType(str, Enum):
    """球队类型枚举"""

    HOME = "home"  # 主队
    AWAY = "away"  # 客队


class FeatureEntityType(str, Enum):
    """特征实体类型"""

    MATCH = "match"
    TEAM = "team"
    PLAYER = "player"
    LEAGUE = "league"


class FeatureEntity(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "feature_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_numeric: Mapped[Decimal | None] = mapped_column(
        DECIMAL(10, 4), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 索引
    __table_args__ = (
        Index("idx_feature_entity", "entity_type", "entity_id"),
        Index("idx_feature_name", "feature_name"),
        {"extend_existing": True},
    )


class Features(BaseModel):
    """特征数据模型"""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, nullable=False)
    team_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feature_type: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_data: Mapped[dict[str, Any] | None] = mapped_column(
        Text, nullable=True
    )  # JSON as text
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 关系
    match: Mapped[Optional["Match"]] = relationship("Match", back_populates="features")
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="features")

    # 索引
    __table_args__ = (
        Index("idx_features_match", "match_id"),
        Index("idx_features_team", "team_id"),
        Index("idx_features_type", "feature_type"),
        {"extend_existing": True},
    )
