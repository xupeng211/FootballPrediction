"""
Football Prediction数据库模型定义

包含所有业务数据模型，使用SQLAlchemy ORM。
"""

from sqlalchemy import Column, Float, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship

from src.database.base import BaseModel


class Odds(BaseModel):
    """
    赔率数据模型

    存储来自不同博彩公司的赔率数据，用于特征工程和模型训练。
    """

    __tablename__ = "odds"

    # 比赛基础信息
    match_id = Column(String(100), nullable=False, index=True, comment="比赛ID")
    home_team = Column(String(100), nullable=False, comment="主队名称")
    away_team = Column(String(100), nullable=False, comment="客队名称")
    match_date = Column(DateTime, nullable=False, comment="比赛时间")
    league = Column(String(100), nullable=True, comment="联赛名称")

    # 赔率数据
    bookmaker = Column(String(100), nullable=False, comment="博彩公司")
    home_odds = Column(Float, nullable=True, comment="主胜赔率")
    draw_odds = Column(Float, nullable=True, comment="平局赔率")
    away_odds = Column(Float, nullable=True, comment="客胜赔率")

    # 计算得出的隐含概率
    implied_home_prob = Column(Float, nullable=True, comment="主胜隐含概率")
    implied_draw_prob = Column(Float, nullable=True, comment="平局隐含概率")
    implied_away_prob = Column(Float, nullable=True, comment="客胜隐含概率")

    # 元数据
    data_source = Column(String(50), nullable=True, comment="数据来源")
    collected_at = Column(DateTime, nullable=True, comment="数据收集时间")
    is_active = Column(Boolean, default=True, comment="是否有效")

    def __repr__(self) -> str:
        return f"<Odds(match_id='{self.match_id}', bookmaker='{self.bookmaker}')>"


# 导出所有模型
__all__ = ["Odds"]