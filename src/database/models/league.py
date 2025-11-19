from typing import Optional

"""联赛模型.

存储足球联赛的基础信息,如英超,西甲等.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import BaseModel


class League(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "leagues"

    # 基本字段
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
