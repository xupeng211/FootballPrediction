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

from typing import Optional, Dict, Any
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
    __table_args__ = {'extend_existing': True}