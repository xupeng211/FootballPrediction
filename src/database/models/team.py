from typing import Dict, List, Optional
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Session, relationship
from ..base import BaseModel
from enum import Enum

"""
球队模型

存储足球队伍的基础信息，如曼联、巴塞罗那等。
"""

# Match model imported locally to avoid circular imports

class TeamForm(Enum):
    """球队状态枚举"""

    GOOD = "good"  # 状态良好
    AVERAGE = "average"  # 状态一般
    POOR = "poor"  # 状态不佳

class Team(BaseModel):
    __table_args__ = {'extend_existing': True}
    __tablename__ = "teams"