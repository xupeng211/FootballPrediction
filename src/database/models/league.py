"""联赛模型.

存储足球联赛的基础信息,如英超,西甲等.
"""

from datetime import datetime

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import BaseModel


class League(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "leagues"

    # 基本字段
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    season: Mapped[str] = mapped_column(String(20), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """安全的__repr__方法，只访问自己的列字段."""
        return (
            f"League(id={self.id}, "
            f"name={self.name!r}, "
            f"country={self.country!r}, "
            f"season={self.season!r})"
        )
