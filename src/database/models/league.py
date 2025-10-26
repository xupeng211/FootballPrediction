from sqlalchemy import Boolean, Column, Index, Integer, String
from sqlalchemy.orm import relationship

"""
联赛模型

存储足球联赛的基础信息，如英超、西甲等。
"""

from sqlalchemy import Column, Integer, String
from ..base import BaseModel
from sqlalchemy import Boolean
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String

class League(BaseModel):
    __table_args__ = {'extend_existing': True}
    __tablename__ = "leagues"