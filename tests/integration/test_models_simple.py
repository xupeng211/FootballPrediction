from typing import Optional

"""
简化的测试数据模型
Simple Test Data Models

为集成测试提供简化的数据模型，避免复杂的SQLAlchemy关系.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class TestBase(AsyncAttrs, DeclarativeBase):
    """测试基础模型类"""

    __test__ = False  # 告诉pytest这不是测试类

    pass


class TestTeam(TestBase):
    """测试球队模型"""

    __test__ = False  # 告诉pytest这不是测试类
    __tablename__ = "test_teams"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    short_name = Column(String(10), nullable=False)
    country = Column(String(50), nullable=False)
    founded_year = Column(Integer, nullable=True)
    venue = Column(String(100), nullable=True)
    website = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TestMatch(TestBase):
    """测试比赛模型"""

    __test__ = False  # 告诉pytest这不是测试类
    __tablename__ = "test_matches"

    id = Column(Integer, primary_key=True)
    home_team_id = Column(Integer, nullable=False)
    away_team_id = Column(Integer, nullable=False)
    home_score = Column(Integer, default=0)
    away_score = Column(Integer, default=0)
    match_date = Column(DateTime, nullable=False)
    league = Column(String(100), nullable=False)
    status = Column(String(20), default="scheduled")
    venue = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TestPrediction(TestBase):
    """测试预测模型"""

    __test__ = False  # 告诉pytest这不是测试类
    __tablename__ = "test_predictions"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, nullable=False)
    home_win_prob = Column(Float, nullable=False)
    draw_prob = Column(Float, nullable=False)
    away_win_prob = Column(Float, nullable=False)
    predicted_outcome = Column(String(10), nullable=False)
    confidence = Column(Float, nullable=False)
    model_version = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
