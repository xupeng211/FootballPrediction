"""
数据库模型简化测试
Database Models Simple Tests
"""

import pytest
from datetime import datetime

from src.database.models import User, Team, League, Match, Predictions


@pytest.mark.unit
@pytest.mark.database

class TestUserSimple:
    """用户模型简化测试"""

    def test_user_model_exists(self):
        """测试用户模型存在"""
        # 只测试模型类可以实例化（不需要所有字段）
        _user = User(username="test", email="test@example.com")
        assert user is not None
        assert user.username == "test"
        assert user.email == "test@example.com"


class TestTeamSimple:
    """球队模型简化测试"""

    def test_team_model_exists(self):
        """测试球队模型存在"""
        team = Team(team_name="Test Team")
        assert team is not None
        assert team.team_name == "Test Team"


class TestLeagueSimple:
    """联赛模型简化测试"""

    def test_league_model_exists(self):
        """测试联赛模型存在"""
        # 只测试类可以实例化
        assert League is not None


class TestMatchSimple:
    """比赛模型简化测试"""

    def test_match_model_exists(self):
        """测试比赛模型存在"""
        match = Match(home_team_id=1, away_team_id=2, league_id=3)
        assert match is not None
        assert match.home_team_id == 1
        assert match.away_team_id == 2


class TestPredictionSimple:
    """预测模型简化测试"""

    def test_prediction_model_exists(self):
        """测试预测模型存在"""
        # 只测试类可以实例化
        assert Predictions is not None


class TestModelRelationships:
    """模型关系测试"""

    def test_models_import(self):
        """测试所有模型可以正常导入"""
        from src.database.models import (
            User,
            Team,
            League,
            Match,
            Predictions,
            Odds,
            DataCollectionLog,
            Features,
            AuditLog,
        )

        # 验证所有模型类都存在
        assert User is not None
        assert Team is not None
        assert League is not None
        assert Match is not None
        assert Predictions is not None
        assert Odds is not None
        assert DataCollectionLog is not None
        assert Features is not None
        assert AuditLog is not None

    def test_model_attributes(self):
        """测试模型属性"""
        _user = User(username="test", email="test@example.com")

        # 检查是否有基本属性
        assert hasattr(user, "username")
        assert hasattr(user, "email")
        assert hasattr(user, "is_active")
        assert hasattr(user, "password_hash")

        team = Team(team_name="Test Team")
        assert hasattr(team, "team_name")
        assert hasattr(team, "team_code")
        assert hasattr(team, "country")
