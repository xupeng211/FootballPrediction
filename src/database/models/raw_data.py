from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from ..base import BaseModel
from ..types import JsonbType


class RawData(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "raw_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False)
    data_type = Column(String(50), nullable=False)
    raw_data = Column(JsonbType, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())


class RawMatchData(BaseModel):
    """原始比赛数据模型"""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "raw_match_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(100), nullable=False, unique=True)
    source = Column(String(100), nullable=False)
    match_data = Column(JsonbType, nullable=False)
    collected_at = Column(DateTime, nullable=False, default=func.now())
    processed = Column(Boolean, default=False)


class RawOddsData(BaseModel):
    """原始赔率数据模型"""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "raw_odds_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_match_id = Column(String(100), nullable=False)
    bookmaker = Column(String(100), nullable=False)
    odds_data = Column(JsonbType, nullable=False)
    collected_at = Column(DateTime, nullable=False, default=func.now())
    processed = Column(Boolean, default=False)


class RawScoresData(BaseModel):
    """原始比分数据模型"""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "raw_scores_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_match_id = Column(String(100), nullable=False)
    source = Column(String(100), nullable=False)
    scores_data = Column(JsonbType, nullable=False)
    collected_at = Column(DateTime, nullable=False, default=func.now())
    processed = Column(Boolean, default=False)
