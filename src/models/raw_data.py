"""
原始数据模型
Raw Data Models
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class RawMatchData(Base):
    """原始比赛数据表"""
    __tablename__ = "raw_match_data"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(100), unique=True, index=True, nullable=False)
    home_team = Column(String(100), nullable=False)
    away_team = Column(String(100), nullable=False)
    league = Column(String(100), nullable=False)
    season = Column(String(20), nullable=False)
    match_date = Column(DateTime, nullable=False)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="scheduled")
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RawOddsData(Base):
    """原始赔率数据表"""
    __tablename__ = "raw_odds_data"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(100), index=True, nullable=False)
    bookmaker = Column(String(100), nullable=False)
    market = Column(String(100), nullable=False)
    outcome = Column(String(100), nullable=False)
    odds = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RawStatisticsData(Base):
    """原始统计数据表"""
    __tablename__ = "raw_statistics_data"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(100), index=True, nullable=False)
    team = Column(String(100), nullable=False)
    stat_type = Column(String(100), nullable=False)
    stat_value = Column(Float, nullable=True)
    stat_text = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic模型用于API
class RawMatchDataCreate(BaseModel):
    """创建原始比赛数据"""
    match_id: str = Field(..., description="比赛ID")
    home_team: str = Field(..., description="主队")
    away_team: str = Field(..., description="客队")
    league: str = Field(..., description="联赛")
    season: str = Field(..., description="赛季")
    match_date: datetime = Field(..., description="比赛时间")
    home_score: Optional[int] = Field(None, description="主队得分")
    away_score: Optional[int] = Field(None, description="客队得分")
    status: str = Field("scheduled", description="比赛状态")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始数据")


class RawMatchDataResponse(BaseModel):
    """原始比赛数据响应"""
    id: int
    match_id: str
    home_team: str
    away_team: str
    league: str
    season: str
    match_date: datetime
    home_score: Optional[int]
    away_score: Optional[int]
    status: str
    raw_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RawOddsDataCreate(BaseModel):
    """创建原始赔率数据"""
    match_id: str = Field(..., description="比赛ID")
    bookmaker: str = Field(..., description="博彩公司")
    market: str = Field(..., description="市场类型")
    outcome: str = Field(..., description="结果类型")
    odds: float = Field(..., description="赔率")
    timestamp: datetime = Field(..., description="时间戳")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始数据")


class RawOddsDataResponse(BaseModel):
    """原始赔率数据响应"""
    id: int
    match_id: str
    bookmaker: str
    market: str
    outcome: str
    odds: float
    timestamp: datetime
    raw_data: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class RawStatisticsDataCreate(BaseModel):
    """创建原始统计数据"""
    match_id: str = Field(..., description="比赛ID")
    team: str = Field(..., description="队伍")
    stat_type: str = Field(..., description="统计类型")
    stat_value: Optional[float] = Field(None, description="统计值")
    stat_text: Optional[str] = Field(None, description="统计文本")
    source: str = Field(..., description="数据源")
    timestamp: datetime = Field(..., description="时间戳")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始数据")


class RawStatisticsDataResponse(BaseModel):
    """原始统计数据响应"""
    id: int
    match_id: str
    team: str
    stat_type: str
    stat_value: Optional[float]
    stat_text: Optional[str]
    source: str
    timestamp: datetime
    raw_data: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True