"""
Features - 数据库模块

提供 features 相关的数据库功能。

主要功能：
- 特征实体管理
- 特征元数据管理
- 特征类型定义

使用示例：
    from database.models.features import FeatureEntity, FeatureMetadata
    # 使用示例代码

注意事项：
- 使用SQLAlchemy 2.0语法
"""

from typing import Any, Optional
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    Boolean,
    DECIMAL,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import BaseModel
from datetime import datetime


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
    """特征实体"""

    __tablename__ = "feature_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[FeatureEntityType] = mapped_column(
        SQLEnum(FeatureEntityType), nullable=False
    )
    value: Mapped[float] = mapped_column(DECIMAL(10, 4), nullable=True)
    metadata_json: Mapped[Optional[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 关系
    metadata_records: Mapped[list["FeatureMetadata"] = relationship(
        "FeatureMetadata", back_populates="feature_entity", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<FeatureEntity(id={self.id}, name={self.name}, type={self.entity_type})>"
        )


class FeatureMetadata(BaseModel):
    """特征元数据"""

    __tablename__ = "feature_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feature_entity_id: Mapped[int] = mapped_column(
        ForeignKey("feature_entities.id"), nullable=False
    )
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(String(50), default="float")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    feature_entity: Mapped[FeatureEntity] = relationship(
        "FeatureEntity", back_populates="metadata_records"
    )

    def __repr__(self) -> str:
        return f"<FeatureMetadata(id={self.id}, name={self.feature_name})>"


# 为了向后兼容，保留原始的名称
feature_entity = FeatureEntity
feature_metadata = FeatureMetadata

# 简化的特征类型定义
feature_types = {
    "numerical": ["float", "int", "decimal"],
    "categorical": ["str", "enum"],
    "boolean": ["bool"],
    "temporal": ["datetime", "date", "time"],
}

# 简化的模型字典
models = {"FeatureEntity": FeatureEntity, "FeatureMetadata": FeatureMetadata}


# 为了向后兼容，添加简化的 Features 类
class Features(BaseModel):
    """简化的 Features 类以保持向后兼容"""

    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[Optional[int] = mapped_column(Integer, nullable=True)
    team_id: Mapped[Optional[int] = mapped_column(Integer, nullable=True)
    feature_data: Mapped[Optional[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Features(id={self.id})>"


__all__ = [
    "FeatureEntity",
    "FeatureMetadata",
    "FeatureEntityType",
    "Features",  # 添加到导出列表
    "TeamType",  # 添加到导出列表
    "feature_entity",
    "feature_metadata",
    "feature_types",
    "models",
]
