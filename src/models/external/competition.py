"""
外部联赛数据模型
External Competition Data Model
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ExternalCompetition(Base):
    """外部联赛数据模型"""

    __tablename__ = "external_competitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(
        Integer, unique=True, nullable=False, index=True, comment="外部API的联赛ID"
    )
    name = Column(String(100), nullable=False, comment="联赛名称")
    code = Column(String(10), nullable=True, comment="联赛代码")
    type = Column(String(20), nullable=True, comment="联赛类型")
    emblem = Column(Text, nullable=True, comment="联赛徽章URL")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    def __repr__(self):
        return f"<ExternalCompetition(id={self.id}, external_id={self.external_id}, name={self.name})>"
