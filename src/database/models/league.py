"""
联赛模型

存储足球联赛的基础信息,如英超,西甲等.
"""

from ..base import BaseModel


class League(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "leagues"
