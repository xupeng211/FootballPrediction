from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String
from ..base import BaseModel

"""用户数据模型。"""

from src.database.base import BaseModel
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

class User(BaseModel):
    __table_args__ = {'extend_existing': True}