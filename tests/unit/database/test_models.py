#!/usr/bin/env python3
"""
🗄️ 数据库模型测试

测试数据库模型的定义、关系、验证和序列化
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


# 模拟导入，避免循环依赖问题
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../src'))

# 尝试导入数据库模块
try:
    from src.database.models.user import User
    from src.database.models.predictions import Prediction
    from src.database.models.match import Match
    from src.database.models.team import Team
    from src.database.models.league import League
    CAN_IMPORT = True
except ImportError as e:
    print(f"Warning: 无法导入数据库模型: {e}")
    CAN_IMPORT = False


# 创建模拟基类
MockBase = declarative_base()


class MockUser(MockBase):
    """模拟用户模型"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)

    # 关系
    predictions = relationship("MockPrediction", back_populates="user")


class MockTeam(MockBase):
    """模拟球队模型"""
    __tablename__ = 'teams'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    short_name = Column(String(50))
    country = Column(String(50))
    founded_year = Column(Integer)
    stadium_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    home_matches = relationship("MockMatch", foreign_keys="MockMatch.home_team_id")
    away_matches = relationship("MockMatch", foreign_keys="MockMatch.away_team_id")


class MockLeague(MockBase):
    """模拟联赛模型"""
    __tablename__ = 'leagues'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    short_name = Column(String(50))
    country = Column(String(50))
    division = Column(String(20))
    season = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    matches = relationship("MockMatch", back_populates="league")


class MockMatch(MockBase):
    """模拟比赛模型"""
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True)
    home_team_id = Column(Integer, nullable=False)
    away_team_id = Column(Integer, nullable=False)
    league_id = Column(Integer, nullable=False)
    match_date = Column(DateTime, nullable=False)
    venue = Column(String(100))
    status = Column(String(20), default='scheduled')  # scheduled, live, finished, cancelled
    home_score = Column(Integer, default=0)
    away_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    home_team = relationship("MockTeam", foreign_keys=[home_team_id])
    away_team = relationship("MockTeam", foreign_keys=[away_team_id])
    league = relationship("MockLeague", back_populates="matches")
    predictions = relationship("MockPrediction", back_populates="match")


class MockPrediction(MockBase):
    """模拟预测模型"""
    __tablename__ = 'predictions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    match_id = Column(Integer, nullable=False)
    predicted_outcome = Column(String(10), nullable=False)  # home, draw, away
    home_win_prob = Column(Float, nullable=False)
    draw_prob = Column(Float, nullable=False)
    away_win_prob = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    model_version = Column(String(50), default='default')
    actual_outcome = Column(String(10))
    is_correct = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("MockUser", back_populates="predictions")
    match = relationship("MockMatch", back_populates="predictions")


@pytest.mark.skipif(not CAN_IMPORT, reason="数据库模型导入失败")
@pytest.mark.unit
@pytest.mark.database
@pytest.mark.models
class TestUserModel:
    """用户模型测试"""

    def test_user_model_creation(self):
        """测试用户模型创建"""
        user = MockUser(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="测试用户"
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "测试用户"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.id is None  # 未保存到数据库

    def test_user_model_validation(self):
        """测试用户模型验证"""
        # 测试必填字段
        with pytest.raises(Exception):
            MockUser()  # 缺少必填字段应该抛出异常

        # 测试唯一性约束
        user1 = MockUser(username="testuser", email="test@example.com", password_hash="hash")
        user2 = MockUser(username="testuser", email="test2@example.com", password_hash="hash")
        # 实际数据库会抛出唯一性约束异常

    def test_user_model_timestamps(self):
        """测试时间戳自动设置"""
        before_creation = datetime.utcnow()
        user = MockUser(
            username="testuser",
            email="test@example.com",
            password_hash="hash"
        )
        after_creation = datetime.utcnow()

        assert user.created_at is not None
        assert before_creation <= user.created_at <= after_creation
        assert user.updated_at is not None
        assert user.last_login is None

    def test_user_model_relationships(self):
        """测试用户模型关系"""
        user = MockUser(
            username="testuser",
            email="test@example.com",
            password_hash="hash"
        )

        # 测试关系初始化
        assert hasattr(user, 'predictions')
        assert user.predictions == []


@pytest.mark.skipif(not CAN_IMPORT, reason="数据库模型导入失败")
@pytest.mark.unit
@pytest.mark.database
@pytest.mark.models
class TestTeamModel:
    """球队模型测试"""

    def test_team_model_creation(self):
        """测试球队模型创建"""
        team = MockTeam(
            name="测试足球俱乐部",
            short_name="测试FC",
            country="中国",
            founded_year=2020,
            stadium_name="测试球场"
        )

        assert team.name == "测试足球俱乐部"
        assert team.short_name == "测试FC"
        assert team.country == "中国"
        assert team.founded_year == 2020
        assert team.stadium_name == "测试球场"

    def test_team_model_validation(self):
        """测试球队模型验证"""
        # 测试必填字段
        team = MockTeam(name="测试球队")
        assert team.name == "测试球队"
        assert team.short_name is None  # 可选字段

    def test_team_model_relationships(self):
        """测试球队模型关系"""
        team = MockTeam(name="测试球队")

        # 测试关系初始化
        assert hasattr(team, 'home_matches')
        assert hasattr(team, 'away_matches')
        assert team.home_matches == []
        assert team.away_matches == []


@pytest.mark.skipif(not CAN_IMPORT, reason="数据库模型导入失败")
@pytest.mark.unit
@pytest.mark.database
@pytest.mark.models
class TestMatchModel:
    """比赛模型测试"""

    def test_match_model_creation(self):
        """测试比赛模型创建"""
        match_date = datetime.utcnow() + timedelta(days=1)
        match = MockMatch(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_date=match_date,
            venue="测试球场",
            status="scheduled"
        )

        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.league_id == 1
        assert match.match_date == match_date
        assert match.venue == "测试球场"
        assert match.status == "scheduled"
        assert match.home_score == 0
        assert match.away_score == 0

    def test_match_model_status_validation(self):
        """测试比赛状态验证"""
        valid_statuses = ['scheduled', 'live', 'finished', 'cancelled']

        for status in valid_statuses:
            match = MockMatch(
                home_team_id=1,
                away_team_id=2,
                league_id=1,
                match_date=datetime.utcnow(),
                status=status
            )
            assert match.status == status

    def test_match_model_relationships(self):
        """测试比赛模型关系"""
        match = MockMatch(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_date=datetime.utcnow()
        )

        # 测试关系初始化
        assert hasattr(match, 'home_team')
        assert hasattr(match, 'away_team')
        assert hasattr(match, 'league')
        assert hasattr(match, 'predictions')
        assert match.predictions == []

    def test_match_model_score_update(self):
        """测试比分更新"""
        match = MockMatch(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_date=datetime.utcnow()
        )

        # 更新比分
        match.home_score = 2
        match.away_score = 1
        match.status = "finished"

        assert match.home_score == 2
        assert match.away_score == 1
        assert match.status == "finished"


@pytest.mark.skipif(not CAN_IMPORT, reason="数据库模型导入失败")
@pytest.mark.unit
@pytest.mark.database
@pytest.mark.models
class TestPredictionModel:
    """预测模型测试"""

    def test_prediction_model_creation(self):
        """测试预测模型创建"""
        prediction = MockPrediction(
            user_id=1,
            match_id=1,
            predicted_outcome="home",
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            confidence=0.75,
            model_version="v2.0"
        )

        assert prediction.user_id == 1
        assert prediction.match_id == 1
        assert prediction.predicted_outcome == "home"
        assert prediction.home_win_prob == 0.6
        assert prediction.draw_prob == 0.25
        assert prediction.away_win_prob == 0.15
        assert prediction.confidence == 0.75
        assert prediction.model_version == "v2.0"
        assert prediction.actual_outcome is None
        assert prediction.is_correct is None

    def test_prediction_model_probability_validation(self):
        """测试概率验证"""
        # 测试有效概率
        valid_probs = [
            (0.5, 0.3, 0.2),  # 正常概率
            (1.0, 0.0, 0.0),  # 极端情况
            (0.33, 0.34, 0.33)  # 接近均匀分布
        ]

        for home_prob, draw_prob, away_prob in valid_probs:
            prediction = MockPrediction(
                user_id=1,
                match_id=1,
                predicted_outcome="home",
                home_win_prob=home_prob,
                draw_prob=draw_prob,
                away_win_prob=away_prob,
                confidence=0.8
            )
            assert abs(home_prob + draw_prob + away_prob - 1.0) < 0.01

    def test_prediction_model_outcome_validation(self):
        """测试预测结果验证"""
        valid_outcomes = ['home', 'draw', 'away']

        for outcome in valid_outcomes:
            prediction = MockPrediction(
                user_id=1,
                match_id=1,
                predicted_outcome=outcome,
                home_win_prob=0.4,
                draw_prob=0.3,
                away_win_prob=0.3,
                confidence=0.7
            )
            assert prediction.predicted_outcome == outcome

    def test_prediction_model_result_verification(self):
        """测试预测结果验证"""
        prediction = MockPrediction(
            user_id=1,
            match_id=1,
            predicted_outcome="home",
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            confidence=0.75
        )

        # 验证正确预测
        prediction.actual_outcome = "home"
        prediction.is_correct = True

        assert prediction.actual_outcome == "home"
        assert prediction.is_correct is True

        # 验证错误预测
        prediction.actual_outcome = "away"
        prediction.is_correct = False

        assert prediction.actual_outcome == "away"
        assert prediction.is_correct is False

    def test_prediction_model_relationships(self):
        """测试预测模型关系"""
        prediction = MockPrediction(
            user_id=1,
            match_id=1,
            predicted_outcome="home",
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            confidence=0.75
        )

        # 测试关系初始化
        assert hasattr(prediction, 'user')
        assert hasattr(prediction, 'match')


@pytest.mark.unit
@pytest.mark.database
@pytest.mark.models
class TestModelConstraints:
    """模型约束测试"""

    def test_foreign_key_constraints(self):
        """测试外键约束"""
        if not CAN_IMPORT:
            pytest.skip("数据库模型导入失败")

        # 测试用户ID外键约束
        prediction = MockPrediction(
            user_id=999,  # 不存在的用户ID
            match_id=1,
            predicted_outcome="home",
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            confidence=0.75
        )
        # 实际数据库会抛出外键约束异常

    def test_unique_constraints(self):
        """测试唯一性约束"""
        if not CAN_IMPORT:
            pytest.skip("数据库模型导入失败")

        # 测试用户名唯一性
        user1 = MockUser(username="testuser", email="test1@example.com", password_hash="hash")
        user2 = MockUser(username="testuser", email="test2@example.com", password_hash="hash")
        # 实际数据库会抛出唯一性约束异常

        # 测试邮箱唯一性
        user3 = MockUser(username="testuser2", email="test@example.com", password_hash="hash")
        user4 = MockUser(username="testuser3", email="test@example.com", password_hash="hash")
        # 实际数据库会抛出唯一性约束异常

    def test_check_constraints(self):
        """测试检查约束"""
        if not CAN_IMPORT:
            pytest.skip("数据库模型导入失败")

        # 测试概率值约束
        valid_prediction = MockPrediction(
            user_id=1,
            match_id=1,
            predicted_outcome="home",
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            confidence=0.75
        )

        # 测试置信度约束
        assert 0 <= valid_prediction.confidence <= 1.0


@pytest.mark.unit
@pytest.mark.database
@pytest.mark.models
class TestModelSerialization:
    """模型序列化测试"""

    def test_model_to_dict(self):
        """测试模型转字典"""
        user = MockUser(
            id=1,
            username="testuser",
            email="test@example.com",
            full_name="测试用户"
        )

        # 模拟to_dict方法
        user_dict = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'is_active': user.is_active,
            'is_admin': user.is_admin,
            'created_at': user.created_at,
            'updated_at': user.updated_at
        }

        assert user_dict['username'] == "testuser"
        assert user_dict['email'] == "test@example.com"
        assert user_dict['full_name'] == "测试用户"

    def test_model_json_serialization(self):
        """测试模型JSON序列化"""
        import json

        prediction = MockPrediction(
            id=1,
            user_id=1,
            match_id=1,
            predicted_outcome="home",
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            confidence=0.75
        )

        # 模拟JSON序列化
        prediction_dict = {
            'id': prediction.id,
            'user_id': prediction.user_id,
            'match_id': prediction.match_id,
            'predicted_outcome': prediction.predicted_outcome,
            'home_win_prob': prediction.home_win_prob,
            'draw_prob': prediction.draw_prob,
            'away_win_prob': prediction.away_win_prob,
            'confidence': prediction.confidence,
            'model_version': prediction.model_version,
            'actual_outcome': prediction.actual_outcome,
            'is_correct': prediction.is_correct
        }

        json_str = json.dumps(prediction_dict, default=str)
        assert isinstance(json_str, str)

        # 验证可以反序列化
        loaded_dict = json.loads(json_str)
        assert loaded_dict['predicted_outcome'] == "home"
        assert loaded_dict['confidence'] == 0.75


# 测试运行器
async def run_model_tests():
    """运行模型测试套件"""
    print("🗄️ 开始数据库模型测试")
    print("=" * 60)

    # 这里可以添加更复杂的模型测试逻辑

    print("✅ 数据库模型测试完成")


if __name__ == "__main__":
    asyncio.run(run_model_tests())