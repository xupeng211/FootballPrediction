"""""""
🧪 MVP核心功能单元测试

测试足球预测系统的核心MVP功能
"""""""

import pytest
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.api.simple_auth import SimpleAuthService, SimpleUser
from src.api.data_router import TeamInfo, MatchInfo, LeagueInfo, OddsInfo


class TestSimpleAuth:
    """简化的认证系统测试"""

    def test_create_user(self):
        """测试创建用户"""
        user = SimpleUser(
            username="testuser",
            email="test@example.com",
            password="test123",
            role="user",
            is_active=True
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.is_active is True

    def test_auth_service_user_storage(self):
        """测试认证服务的用户存储"""
        service = SimpleAuthService()

        # 测试用户存储
        user = SimpleUser("testuser", "test@example.com", "test123", "user", True)
        service.store_user(user)

        # 验证用户存储
        stored_user = service.get_user("testuser")
        assert stored_user is not None
        assert stored_user.username == "testuser"

    def test_auth_service_password_validation(self):
        """测试密码验证"""
        service = SimpleAuthService()

        # 测试密码验证
        assert service.verify_password("test123", "test123") is True
        assert service.verify_password("test123", "wrong") is False

    def test_auth_service_token_generation(self):
        """测试令牌生成"""
        service = SimpleAuthService()

        # 测试令牌生成
        user = SimpleUser("testuser", "test@example.com", "test123", "user", True)
        token = service.generate_token(user)

        assert token is not None
        assert "Bearer" in token

    def test_auth_service_token_validation(self):
        """测试令牌验证"""
        service = SimpleAuthService()

        # 测试令牌验证
        user = SimpleUser("testuser", "test@example.com", "test123", "user", True)
        token = service.generate_token(user)

        # 验证有效令牌
        valid_user = service.verify_token(token)
        assert valid_user is not None
        assert valid_user.username == "testuser"

        # 验证无效令牌
        invalid_user = service.verify_token("invalid_token")
        assert invalid_user is None


class TestDataModels:
    """数据模型测试"""

    def test_team_info_model(self):
        """测试球队信息模型"""
        team = TeamInfo(
            id=1,
            name="Test Team",
            short_name="TT",
            logo_url=None,
            country="Test Country",
            league_id=None,
            founded_year=2000,
            stadium_name="Test Stadium",
            stadium_capacity=50000,
            website_url="https://testteam.com",
            team_color="Red"
        )

        assert team.id == 1
        assert team.name == "Test Team"
        assert team.short_name == "TT"
        assert team.founded_year == 2000
        assert team.stadium_name == "Test Stadium"
        assert team.stadium_capacity == 50000
        assert team.website_url == "https://testteam.com"
        assert team.team_color == "Red"

    def test_match_info_model(self):
        """测试比赛信息模型"""
        match = MatchInfo(
            id=1,
            home_team_id=2,
            away_team_id=3,
            home_team_name="Home Team",
            away_team_name="Away Team",
            league_id=1,
            league_name="Test League",
            match_date="2025-01-01T00:00:00",
            status="pending",
            home_score=None,
            away_score=None,
            attendance=25000,
            referee="Test Referee",
            weather="Sunny",
            venue="Test Venue",
            match_week=1,
            home_team_form="W-D-W-L-D",
            away_team_form="L-W-D-W-W"
        )

        assert match.id == 1
        assert match.home_team_name == "Home Team"
        assert match.away_team_name == "Away Team"
        assert match.league_id == 1
        assert match.league_name == "Test League"
        assert match.status == "pending"
        assert match.attendance == 25000
        assert match.referee == "Test Referee"
        assert match.weather == "Sunny"
        assert match.venue == "Test Venue"
        assert match.match_week == 1
        assert match.home_team_form == "W-D-W-L-D"
        assert match.away_team_form == "L-W-D-W-W"

    def test_league_info_model(self):
        """测试联赛信息模型"""
        league = LeagueInfo(
            id=1,
            name="Test League",
            country="Test Country",
            logo_url=None,
            season="2024-25"
        )

        assert league.id == 1
        assert league.name == "Test League"
        assert league.country == "Test Country"
        assert league.season == "2024-25"

    def test_odds_info_model(self):
        """测试赔率信息模型"""
        odds = OddsInfo(
            id=1,
            match_id=1,
            bookmaker="Test Bookmaker",
            home_win=1.95,
            draw=3.2,
            away_win=4.4,
            updated_at="2025-01-01T00:00:00"
        )

        assert odds.id == 1
        assert odds.match_id == 1
        assert odds.bookmaker == "Test Bookmaker"
        assert odds.home_win == 1.95
        assert odds.draw == 3.2
        assert odds.away_win == 4.4
        assert odds.updated_at == "2025-01-01T00:00:00"


class TestDataValidation:
    """数据验证测试"""

    def test_team_data_validation(self):
        """测试球队数据验证"""
        # 测试必需字段
        team_data = {
            "id": 1,
            "name": "Test Team",
            "short_name": "TT"
        }

        team = TeamInfo(**team_data)
        assert team.id == 1
        assert team.name == "Test Team"
        assert team.short_name == "TT"

    def test_match_data_validation(self):
        """测试比赛数据验证"""
        # 测试必需字段
        match_data = {
            "id": 1,
            "home_team_id": 2,
            "away_team_id": 3,
            "home_team_name": "Home Team",
            "away_team_name": "Away Team",
            "league_id": 1,
            "league_name": "Test League",
            "match_date": "2025-01-01T00:00:00",
            "status": "pending"
        }

        match = MatchInfo(**match_data)
        assert match.id == 1
        assert match.home_team_name == "Home Team"
        assert match.away_team_name == "Away Team"
        assert match.status == "pending"

    def test_odds_data_validation(self):
        """测试赔率数据验证"""
        # 测试必需字段
        odds_data = {
            "id": 1,
            "match_id": 1,
            "bookmaker": "Test Bookmaker",
            "home_win": 1.95,
            "draw": 3.2,
            "away_win": 4.4
        }

        odds = OddsInfo(**odds_data)
        assert odds.id == 1
        assert odds.match_id == 1
        assert odds.bookmaker == "Test Bookmaker"
        assert odds.home_win == 1.95
        assert odds.draw == 3.2
        assert odds.away_win == 4.4


class TestBusinessLogic:
    """业务逻辑测试"""

    def test_user_registration_flow(self):
        """测试用户注册流程"""
        service = SimpleAuthService()

        # 步骤1: 创建用户
        user = SimpleUser("newuser", "new@example.com", "password123", "user", True)

        # 步骤2: 存储用户
        service.store_user(user)

        # 步骤3: 生成令牌
        token = service.generate_token(user)

        # 步骤4: 验证令牌
        verified_user = service.verify_token(token)

        assert user.username == "newuser"
        assert token is not None
        assert verified_user is not None
        assert verified_user.username == "newuser"

    def test_enhanced_team_data_value(self):
        """测试增强数据的价值"""
        team = TeamInfo(
            id=1,
            name="Premium Team",
            short_name="PT",
            founded_year=1990,
            stadium_name="Premium Stadium",
            stadium_capacity=60000,
            website_url="https://premiumteam.com",
            team_color="Blue"
        )

        # 验证增强数据的价值
        assert team.founded_year == 1990  # 历史价值
        assert team.stadium_capacity == 60000  # 实用价值
        assert team.website_url is not None  # 商业价值
        assert team.team_color == "Blue"  # 品牌价值

    def test_enhanced_match_data_analysis(self):
        """测试增强比赛数据的分析价值"""
        match = MatchInfo(
            id=1,
            home_team_name="Analysis Team",
            away_team_name="Stats Team",
            attendance=45000,
            referee="Professional Referee",
            weather="Clear",
            venue="Analysis Stadium",
            home_team_form="W-D-W-L-D",
            away_team_form="L-W-D-W-W"
        )

        # 验证分析数据的价值
        assert match.attendance == 45000  # 商业价值
        assert match.referee is not None  # 专业价值
        assert match.weather == "Clear"  # 影响因素
        assert match.home_team_form is not None  # 预测价值
        assert match.away_team_form is not None  # 预测价值


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__], "-v"])