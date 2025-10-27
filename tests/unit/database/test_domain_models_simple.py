from unittest.mock import MagicMock

"""
简化的领域模型单元测试
"""

from datetime import datetime, timedelta

import pytest

from src.domain_simple import (League, LeagueTable, MarketType, Match,
                               MatchResult, MatchStatus, Odds, Prediction,
                               PredictionConfidence, PredictionType, Team,
                               TeamStatistics, User, UserPreferences,
                               UserProfile, ValueBet)


@pytest.mark.unit
@pytest.mark.database
class TestMatch:
    """比赛领域模型测试"""

    def test_match_creation(self):
        """测试比赛创建"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            scheduled_at=datetime.now() + timedelta(days=1),
        )

        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.league_id == 10
        assert match.scheduled_at is not None

    def test_match_status(self):
        """测试比赛状态"""
        Match(home_team_id=1, away_team_id=2)

        # 测试状态枚举
        assert MatchStatus.SCHEDULED.value == "scheduled"
        assert MatchStatus.LIVE.value == "live"
        assert MatchStatus.FINISHED.value == "finished"
        assert MatchStatus.CANCELLED.value == "cancelled"

    def test_match_result(self):
        """测试比赛结果"""
        # 测试结果枚举
        assert MatchResult.HOME_WIN.value == "home_win"
        assert MatchResult.DRAW.value == "draw"
        assert MatchResult.AWAY_WIN.value == "away_win"


class TestTeam:
    """球队领域模型测试"""

    def test_team_creation(self):
        """测试球队创建"""
        team = Team(name="Test Team", league_id=10)

        assert team.name == "Test Team"
        assert team.league_id == 10

    def test_team_statistics(self):
        """测试球队统计"""
        _stats = TeamStatistics()

        assert stats.played == 0
        assert stats.won == 0
        assert stats.drawn == 0
        assert stats.lost == 0
        assert stats.points == 0

    def test_update_team_stats(self):
        """测试更新球队统计"""
        _stats = TeamStatistics()
        stats.update(won=1, goals_for=2, goals_against=0)

        assert stats.won == 1
        assert stats.goals_for == 2
        assert stats.goals_against == 0
        assert stats.points == 3


class TestPrediction:
    """预测领域模型测试"""

    def test_prediction_creation(self):
        """测试预测创建"""
        _prediction = Prediction(
            match_id=123,
            user_id=456,
            prediction_type=PredictionType.MATCH_RESULT,
            confidence=PredictionConfidence.HIGH,
        )

        assert prediction.match_id == 123
        assert prediction.user_id == 456
        assert prediction.prediction_type == PredictionType.MATCH_RESULT
        assert prediction.confidence == PredictionConfidence.HIGH

    def test_prediction_type(self):
        """测试预测类型"""
        assert PredictionType.MATCH_RESULT.value == "match_result"
        assert PredictionType.SCORE.value == "score"
        assert PredictionType.OVER_UNDER.value == "over_under"

    def test_prediction_confidence(self):
        """测试预测置信度"""
        assert PredictionConfidence.LOW.value == "low"
        assert PredictionConfidence.MEDIUM.value == "medium"
        assert PredictionConfidence.HIGH.value == "high"


class TestLeague:
    """联赛领域模型测试"""

    def test_league_creation(self):
        """测试联赛创建"""
        league = League(name="Test League", country="Test Country")

        assert league.name == "Test League"
        assert league.country == "Test Country"

    def test_league_table(self):
        """测试联赛积分榜"""
        table = LeagueTable(league_id=1, season="2023/2024")

        assert table.league_id == 1
        assert table.season == "2023/2024"


class TestUser:
    """用户领域模型测试"""

    def test_user_creation(self):
        """测试用户创建"""
        _user = User(username="testuser", email="test@example.com")

        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_user_profile(self):
        """测试用户档案"""
        profile = UserProfile(user_id=1)

        assert profile.user_id == 1
        assert profile.first_name is None
        assert profile.last_name is None

    def test_user_preferences(self):
        """测试用户偏好"""
        preferences = UserPreferences(user_id=1)

        assert preferences.user_id == 1
        assert preferences.favorite_teams == []
        assert preferences.notification_settings == {}

    def test_add_experience(self):
        """测试添加经验值"""
        _user = User(username="test")
        user.add_experience(150)

        assert user.experience_points == 150
        assert user.level == 2  # 150 // 100 + 1 = 2

    def test_add_achievement(self):
        """测试添加成就"""
        _user = User(username="test")
        user.add_achievement("first_prediction")

        assert "first_prediction" in user.achievements

    def test_get_full_name(self):
        """测试获取全名"""
        _user = User(username="test", first_name="John", last_name="Doe")

        full_name = user.get_full_name()
        assert full_name == "John Doe"

        # 只有用户名的情况
        user_no_name = User(username="testuser")
        assert user_no_name.get_full_name() == "testuser"


class TestOdds:
    """赔率领域模型测试"""

    def test_odds_creation(self):
        """测试赔率创建"""
        odds = Odds(
            match_id=123,
            market_type=MarketType.MATCH_RESULT,
            bookmaker="Bookmaker1",
            home_odds=2.10,
            draw_odds=3.40,
            away_odds=3.20,
        )

        assert odds.match_id == 123
        assert odds.market_type == MarketType.MATCH_RESULT
        assert odds.bookmaker == "Bookmaker1"
        assert odds.home_odds == 2.10
        assert odds.draw_odds == 3.40
        assert odds.away_odds == 3.20

    def test_market_type(self):
        """测试市场类型"""
        assert MarketType.MATCH_RESULT.value == "match_result"
        assert MarketType.OVER_UNDER.value == "over_under"
        assert MarketType.ASIAN_HANDICAP.value == "asian_handicap"

    def test_get_implied_probability(self):
        """测试获取隐含概率"""
        odds = Odds(home_odds=2.0, draw_odds=4.0, away_odds=4.0)

        probabilities = odds.get_implied_probability()

        assert probabilities["home"] == 50.0
        assert probabilities["draw"] == 25.0
        assert probabilities["away"] == 25.0

    def test_suspend_and_resume(self):
        """测试暂停和恢复"""
        odds = Odds(home_odds=2.0)
        assert odds.is_active is True

        odds.suspend()
        assert odds.is_active is False

        odds.resume()
        assert odds.is_active is True


class TestValueBet:
    """价值投注测试"""

    def test_value_bet_creation(self):
        """测试价值投注创建"""
        value_bet = ValueBet(odds=2.10, probability=0.55)

        assert value_bet.odds == 2.10
        assert value_bet.probability == 0.55

    def test_calculate_expected_value(self):
        """测试计算期望值"""
        value_bet = ValueBet(odds=2.10, probability=0.55)
        ev = value_bet.calculate_expected_value()

        expected = (2.10 * 0.55) - 1
        assert abs(ev - expected) < 0.01
