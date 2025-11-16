from enum import Enum

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import BaseModel

"""
球队模型

存储足球队伍的基础信息,如曼联,巴塞罗那等.
"""

# Match model imported locally to avoid circular imports


class TeamForm(Enum):
    """球队状态枚举"""

    GOOD = "good"  # 状态良好
    AVERAGE = "average"  # 状态一般
    POOR = "poor"  # 状态不佳


class Team(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "teams"

    # 基本字段
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    founded_year: Mapped[int] = mapped_column(Integer, nullable=True)
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 关系
    features = relationship("Features", back_populates="team")
