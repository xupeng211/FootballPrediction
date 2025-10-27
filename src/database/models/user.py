from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String

from ..base import BaseModel

"""用户数据模型。"""

from sqlalchemy import Column, DateTime, Integer, String

from src.database.base import BaseModel


class User(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "users"
