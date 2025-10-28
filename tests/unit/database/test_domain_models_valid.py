"""
有效的领域模型单元测试
基于实际实现编写
"""

from datetime import datetime, timedelta

import pytest

from src.domain_simple import (
    League,
    LeagueTable,
    MarketType,
    Match,
    MatchResult,
    MatchStatus,
    Odds,
    Prediction,
    PredictionConfidence,
    PredictionType,
    Team,
    TeamStatistics,
    User,
    UserPreferences,
    UserProfile,
    ValueBet,
)


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
            scheduled_time=datetime.now() + timedelta(days=1),
        )

        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.league_id == 10
        assert match.scheduled_time is not None
        assert match.status == MatchStatus.SCHEDULED

    def test_match_status(self):
        """测试比赛状态枚举"""
        assert MatchStatus.SCHEDULED.value == "scheduled"
        assert MatchStatus.IN_PROGRESS.value == "in_progress"
        assert MatchStatus.COMPLETED.value == "completed"
        assert MatchStatus.CANCELLED.value == "cancelled"
        assert MatchStatus.POSTPONED.value == "postponed"

    def test_match_result(self):
        """测试比赛结果枚举"""
        assert MatchResult.HOME_WIN.value == "home_win"
        assert MatchResult.DRAW.value == "draw"
        assert MatchResult.AWAY_WIN.value == "away_win"
        assert MatchResult.UNKNOWN.value == "unknown"

    def test_match_methods(self):
        """测试比赛方法"""
        match = Match(home_team_id=1, away_team_id=2)

        # 测试开始比赛
        match.start_match()
        assert match.status == MatchStatus.IN_PROGRESS
        assert match.start_time is not None

        # 测试结束比赛
        match.end_match(2, 1)
        assert match.status == MatchStatus.COMPLETED
        assert match.home_score == 2
        assert match.away_score == 1

        # 测试取消比赛
        match2 = Match(home_team_id=3, away_team_id=4)
        match2.cancel_match()
        assert match2.status == MatchStatus.CANCELLED


class TestTeam:
    """球队领域模型测试"""

    def test_team_creation(self):
        """测试球队创建"""
        team = Team(name="Test Team", league_id=10)

        assert team.name == "Test Team"
        assert team.league_id == 10
        assert team.id is None

    def test_team_statistics(self):
        """测试球队统计"""
        _stats = TeamStatistics()

        assert stats.matches_played == 0
        assert stats.wins == 0
        assert stats.draws == 0
        assert stats.losses == 0
        assert stats.goals_for == 0
        assert stats.goals_against == 0
        assert stats.points == 0

    def test_update_team_stats(self):
        """测试更新球队统计"""
        _stats = TeamStatistics()
        stats.record_match(2, 1, True)  # 主队2:1获胜

        assert stats.matches_played == 1
        assert stats.wins == 1
        assert stats.goals_for == 2
        assert stats.goals_against == 1
        assert stats.points == 3

        # 测试平局
        stats.record_match(1, 1, False)
        assert stats.draws == 1
        assert stats.points == 4


class TestPrediction:
    """预测领域模型测试"""

    def test_prediction_creation(self):
        """测试预测创建"""
        _prediction = Prediction(
            match_id=123,
            user_id=456,
            prediction_type=PredictionType.MATCH_RESULT,
            confidence=0.75,
        )

        assert prediction.match_id == 123
        assert prediction.user_id == 456
        assert prediction.prediction_type == PredictionType.MATCH_RESULT
        assert prediction.confidence == 0.75

    def test_prediction_type(self):
        """测试预测类型枚举"""
        assert PredictionType.MATCH_RESULT.value == "match_result"
        assert PredictionType.SCORE_PREDICTION.value == "score_prediction"

    def test_prediction_confidence(self):
        """测试预测置信度枚举"""
        assert PredictionConfidence.LOW.value == 0.3
        assert PredictionConfidence.MEDIUM.value == 0.6
        assert PredictionConfidence.HIGH.value == 0.9

    def test_settle_prediction(self):
        """测试结算预测"""
        _prediction = Prediction(
            match_id=123, user_id=456, predicted_outcome="home_win", confidence=0.8
        )

        # 正确预测
        prediction.settle("home_win", True)
        assert prediction.is_correct is True
        assert prediction.settled_at is not None

        # 错误预测
        prediction2 = Prediction(
            match_id=124, user_id=456, predicted_outcome="away_win"
        )
        prediction2.settle("home_win", False)
        assert prediction2.is_correct is False


class TestLeague:
    """联赛领域模型测试"""

    def test_league_creation(self):
        """测试联赛创建"""
        league = League(name="Test League", country="Test Country")

        assert league.name == "Test League"
        assert league.country == "Test Country"
        assert league.id is None

    def test_league_table(self):
        """测试联赛积分榜"""
        table = LeagueTable()

        assert table.league_id is None
        assert table.season is None
        assert isinstance(table.standings, list)


class TestUser:
    """用户领域模型测试"""

    def test_user_creation(self):
        """测试用户创建"""
        _user = User(username="testuser", email="test@example.com")

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.id is None
        assert user.created_at is not None

    def test_user_profile(self):
        """测试用户档案"""
        profile = UserProfile()

        assert profile.user_id is None
        assert profile.first_name is None
        assert profile.last_name is None
        assert profile.avatar_url is None

    def test_user_preferences(self):
        """测试用户偏好"""
        preferences = UserPreferences()

        assert preferences.user_id is None
        assert isinstance(preferences.favorite_teams, list)
        assert isinstance(preferences.notification_settings, dict)

    def test_add_experience(self):
        """测试添加经验值"""
        _user = User(username="test")
        initial_level = user.level
        user.add_experience(150)

        assert user.experience_points == 150
        assert user.level > initial_level

    def test_add_achievement(self):
        """测试添加成就"""
        _user = User(username="test")
        user.add_achievement("first_prediction")

        assert "first_prediction" in user.achievements

    def test_get_full_name(self):
        """测试获取全名"""
        # 通过profile设置名字
        _user = User(username="test")
        user.profile.first_name = "John"
        user.profile.last_name = "Doe"

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
        assert odds.is_active is True

    def test_market_type(self):
        """测试市场类型枚举"""
        assert MarketType.MATCH_RESULT.value == "1X2"
        assert MarketType.OVER_UNDER.value == "over_under"
        assert MarketType.ASIAN_HANDICAP.value == "asian_handicap"

    def test_get_implied_probability(self):
        """测试获取隐含概率"""
        odds = Odds(home_odds=2.0, draw_odds=4.0, away_odds=4.0)

        probabilities = odds.get_implied_probability()

        assert probabilities["home"] == 50.0
        assert probabilities["draw"] == 25.0
        assert probabilities["away"] == 25.0

    def test_update_odds(self):
        """测试更新赔率"""
        odds = Odds(home_odds=2.0, draw_odds=3.0, away_odds=4.0)

        # 更新赔率
        odds.update_odds(home_odds=1.95, draw_odds=3.10)

        assert odds.home_odds == 1.95
        assert odds.draw_odds == 3.10
        assert odds.away_odds == 4.0  # 未改变

    def test_suspend_and_resume(self):
        """测试暂停和恢复"""
        odds = Odds(home_odds=2.0)
        assert odds.is_active is True

        odds.suspend()
        assert odds.is_active is False
        assert odds.is_suspended is True

        odds.resume()
        assert odds.is_active is True
        assert odds.is_suspended is False


class TestValueBet:
    """价值投注测试"""

    def test_value_bet_creation(self):
        """测试价值投注创建"""
        value_bet = ValueBet(odds=2.10, probability=0.55)

        assert value_bet.odds == 2.10
        assert value_bet.probability == 0.55
        assert value_bet.expected_value == (2.10 * 0.55) - 1

    def test_is_value(self):
        """测试是否为价值投注"""
        # 正期望值
        value_bet = ValueBet(odds=2.10, probability=0.55)
        assert value_bet.is_value() is True

        # 负期望值
        value_bet2 = ValueBet(odds=1.80, probability=0.50)
        assert value_bet2.is_value() is False
