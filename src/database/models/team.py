from enum import Enum

from src.database.base import BaseModel

"""
球队模型

存储足球队伍的基础信息,如曼联,巴塞罗那等.
"""


class TeamForm(Enum):
    """球队状态枚举"""

    GOOD = "good"  # 状态良好
    AVERAGE = "average"  # 状态一般
    POOR = "poor"  # 状态不佳


class Team(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "teams"
