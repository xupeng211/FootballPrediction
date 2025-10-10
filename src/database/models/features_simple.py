"""
简化的Features模型定义

提供基本的Features和TeamType类以避免导入错误。
"""

from enum import Enum
from typing import Dict, Any, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TeamType(Enum):
    """球队类型"""

    HOME = "home"
    AWAY = "away"
    NEUTRAL = "neutral"


class Features(Base):
    """特征模型"""

    __tablename__ = "features"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    match_id = Column(Integer, ForeignKey("matches.id"))
    feature_type = Column(String(50))
    value = Column(Float)
    feature_metadata = Column(JSON)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    def __repr__(self):
        return f"<Features(team_id={self.team_id}, type={self.feature_type}, value={self.value})>"
