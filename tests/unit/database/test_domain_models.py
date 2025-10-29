"""
领域模型单元测试
"""

from datetime import datetime, timedelta

import pytest

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
            scheduled_at=datetime.now() + timedelta(days=1),
        )

        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.status == MatchStatus.SCHEDULED
        assert not match.is_started()
        assert not match.is_finished()

    def test_match_start(self):
        """测试比赛开始"""
        match = Match(home_team_id=1, away_team_id=2)
        match.start_match()

        assert match.status == MatchStatus.LIVE
        assert match.is_started()
        assert match.start_time is not None
        assert not match.is_finished()

    def test_match_end(self):
        """测试比赛结束"""
        match = Match(home_team_id=1, away_team_id=2)
        match.start_match()
        match.end_match(2, 1)

        assert match.status == MatchStatus.FINISHED
        assert match.is_finished()
        assert match.current_score.home == 2
        assert match.current_score.away == 1

    def test_match_cancel(self):
        """测试比赛取消"""
        match = Match(home_team_id=1, away_team_id=2)
        match.cancel_match()

        assert match.status == MatchStatus.CANCELLED

    def test_set_score(self):
        """测试设置比分"""
        match = Match(home_team_id=1, away_team_id=2)
        match.set_score(3, 0)

        assert match.current_score.home == 3
        assert match.current_score.away == 0

    def test_get_duration(self):
        """测试获取比赛时长"""
        match = Match(home_team_id=1, away_team_id=2)
        datetime.now()
        match.start_match()

        duration = match.get_duration()
        assert duration >= 0

    def test_to_dict(self):
        """测试转换为字典"""
        match = Match(
            home_team_id=1, away_team_id=2, league_id=10, scheduled_at=datetime.now()
        )

        _data = match.to_dict()
        assert _data["home_team_id"] == 1
        assert _data["away_team_id"] == 2
        assert _data["status"] == "scheduled"

    def test_from_dict(self):
        """测试从字典创建"""
        _data = {
            "home_team_id": 1,
            "away_team_id": 2,
            "league_id": 10,
            "status": "scheduled",
            "scheduled_at": datetime.now().isoformat(),
        }

        match = Match.from_dict(data)
        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.status == MatchStatus.SCHEDULED


class TestTeam:
    """球队领域模型测试"""

    def test_team_creation(self):
        """测试球队创建"""
        team = Team(name="Test Team", league_id=10)

        assert team.name == "Test Team"
        assert team.league_id == 10
        assert team.stats.played == 0

    def test_update_stats(self):
        """测试更新统计"""
        team = Team(name="Test Team")
        team.update_stats(played=1, won=1, goals_for=2, goals_against=0)

        assert team.stats.played == 1
        assert team.stats.won == 1
        assert team.stats.goals_for == 2
        assert team.stats.points == 3

    def test_get_form(self):
        """测试获取近期状态"""
        team = Team(name="Test Team")
        team.add_form_result("W")
        team.add_form_result("D")
        team.add_form_result("L")

        form = team.get_form()
        assert len(form) == 3
        assert form == ["W", "D", "L"]

    def test_get_win_rate(self):
        """测试获取胜率"""
        team = Team(name="Test Team")
        team.update_stats(played=10, won=5, drawn=3)

        win_rate = team.get_win_rate()
        assert win_rate == 50.0

    def test_calculate_strength(self):
        """测试计算球队实力"""
        team = Team(name="Test Team")
        team.update_stats(played=10, won=5, drawn=3, goals_for=20, goals_against=10)

        strength = team.calculate_strength()
        assert 0 <= strength <= 100

    def test_to_dict(self):
        """测试转换为字典"""
        team = Team(name="Test Team", league_id=10)
        _data = team.to_dict()

        assert _data["name"] == "Test Team"
        assert _data["league_id"] == 10
        assert "stats" in _data


class TestPrediction:
    """预测领域模型测试"""

    def test_prediction_creation(self):
        """测试预测创建"""
        _prediction = Prediction(
            match_id=123,
            user_id=456,
            prediction_type="match_result",
            predicted_outcome="home_win",
        )

        assert prediction.match_id == 123
        assert prediction.user_id == 456
        assert prediction.status == PredictionStatus.PENDING

    def test_settle_prediction_correct(self):
        """测试结算预测（正确）"""
        _prediction = Prediction(
            match_id=123,
            user_id=456,
            prediction_type="match_result",
            predicted_outcome="home_win",
            odds=2.0,
        )

        prediction.settle("home_win", 2.0)

        assert prediction.status == PredictionStatus.SETTLED
        assert prediction.is_correct is True
        assert prediction.settled_at is not None

    def test_settle_prediction_incorrect(self):
        """测试结算预测（错误）"""
        _prediction = Prediction(
            match_id=123,
            user_id=456,
            prediction_type="match_result",
            predicted_outcome="home_win",
            odds=2.0,
        )

        prediction.settle("away_win", 2.0)

        assert prediction.status == PredictionStatus.SETTLED
        assert prediction.is_correct is False

    def test_cancel_prediction(self):
        """测试取消预测"""
        _prediction = Prediction(
            match_id=123,
            user_id=456,
            prediction_type="match_result",
            predicted_outcome="home_win",
        )

        prediction.cancel()

        assert prediction.status == PredictionStatus.CANCELLED

    def test_calculate_confidence(self):
        """测试计算置信度"""
        _prediction = Prediction(
            match_id=123,
            user_id=456,
            prediction_type="match_result",
            predicted_outcome="home_win",
            confidence=0.75,
        )

        confidence_score = prediction.calculate_confidence()
        assert confidence_score == 75.0

    def test_get_potential_return(self):
        """测试获取潜在回报"""
        _prediction = Prediction(match_id=123, user_id=456, stake=100, odds=2.0)

        potential_return = prediction.get_potential_return()
        assert potential_return == 200.0


class TestLeague:
    """联赛领域模型测试"""

    def test_league_creation(self):
        """测试联赛创建"""
        league = League(name="Test League", country="Test Country")

        assert league.name == "Test League"
        assert league.country == "Test Country"
        assert league.seasons == []

    def test_add_season(self):
        """测试添加赛季"""
        league = League(name="Test League")
        league.add_season("2023/2024")

        assert len(league.seasons) == 1
        assert league.seasons[0].name == "2023/2024"

    def test_get_current_season(self):
        """测试获取当前赛季"""
        league = League(name="Test League")
        league.add_season("2022/2023")
        league.add_season("2023/2024")

        current_season = league.get_current_season()
        assert current_season.name == "2023/2024"

    def test_get_standings(self):
        """测试获取积分榜"""
        league = League(name="Test League")
        season = league.add_season("2023/2024")

        standings = league.get_standings(season.id)
        assert isinstance(standings, list)

    def test_to_dict(self):
        """测试转换为字典"""
        league = League(name="Test League", country="Test Country")
        _data = league.to_dict()

        assert _data["name"] == "Test League"
        assert _data["country"] == "Test Country"
        assert len(_data["seasons"]) == 0


class TestUser:
    """用户领域模型测试"""

    def test_user_creation(self):
        """测试用户创建"""
        _user = User(username="testuser", email="test@example.com")

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.USER
        assert user.level == 1
        assert user.experience_points == 0

    def test_is_premium(self):
        """测试是否为高级用户"""
        _user = User(username="test", role=UserRole.USER)
        assert not user.is_premium()

        premium_user = User(username="premium", role=UserRole.PREMIUM)
        assert premium_user.is_premium()

    def test_is_admin(self):
        """测试是否为管理员"""
        _user = User(username="test", role=UserRole.USER)
        assert not user.is_admin()

        admin_user = User(username="admin", role=UserRole.ADMIN)
        assert admin_user.is_admin()

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

    def test_to_dict(self):
        """测试转换为字典"""
        _user = User(username="testuser", email="test@example.com")
        _data = user.to_dict()

        assert _data["username"] == "testuser"
        assert _data["email"] == "test@example.com"
        assert _data["is_premium"] is False
        assert _data["level"] == 1


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
        assert odds.home_odds == 2.10
        assert odds.is_active is True

    def test_update_odds(self):
        """测试更新赔率"""
        odds = Odds(match_id=123, home_odds=2.10, draw_odds=3.40, away_odds=3.20)

        odds.update_odds(home_odds=2.05, draw_odds=3.50)

        assert odds.home_odds == 2.05
        assert odds.draw_odds == 3.50
        assert odds.away_odds == 3.20  # 未更新
        assert len(odds.movements) == 1

    def test_get_implied_probability(self):
        """测试获取隐含概率"""
        odds = Odds(home_odds=2.0, draw_odds=4.0, away_odds=4.0)

        probabilities = odds.get_implied_probability()

        assert probabilities["home"] == 50.0
        assert probabilities["draw"] == 25.0
        assert probabilities["away"] == 25.0

    def test_get_vig_percentage(self):
        """测试获取抽水百分比"""
        odds = Odds(home_odds=2.0, draw_odds=3.0, away_odds=4.0)

        vig = odds.get_vig_percentage()
        expected_vig = (50.0 + 33.33 + 25.0) - 100
        assert abs(vig - expected_vig) < 0.1

    def test_get_true_probability(self):
        """测试获取真实概率"""
        odds = Odds(home_odds=2.0, draw_odds=4.0, away_odds=4.0)

        true_probs = odds.get_true_probability()
        assert abs(true_probs["home"] - 50.0) < 0.1
        assert abs(true_probs["draw"] - 25.0) < 0.1
        assert abs(true_probs["away"] - 25.0) < 0.1

    def test_find_value_bets(self):
        """测试寻找价值投注"""
        odds = Odds(home_odds=2.10, draw_odds=3.40, away_odds=3.20)
        predicted_probs = {"home": 0.55, "draw": 0.25, "away": 0.20}

        value_bets = odds.find_value_bets(predicted_probs)

        # 主胜有优势（隐含概率47.6% < 预测55%）
        assert len(value_bets) > 0
        assert value_bets[0].is_value()

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


class TestOddsMovement:
    """赔率变化测试"""

    def test_odds_movement_creation(self):
        """测试赔率变化创建"""
        movement = OddsMovement(old_odds=2.10, new_odds=2.05, timestamp=datetime.now())

        assert movement.old_odds == 2.10
        assert movement.new_odds == 2.05
        assert movement.change == -0.05
        assert movement.change_percent < 0

    def test_is_significant(self):
        """测试是否为显著变化"""
        # 5%变化（阈值）
        movement = OddsMovement(2.0, 2.1, datetime.now())
        assert movement.is_significant(5.0) is True

        # 2%变化（小于阈值）
        movement2 = OddsMovement(2.0, 2.04, datetime.now())
        assert movement2.is_significant(5.0) is False


class TestValueBet:
    """价值投注测试"""

    def test_value_bet_creation(self):
        """测试价值投注创建"""
        value_bet = ValueBet(odds=2.10, probability=0.55, threshold=1.0)

        assert value_bet.odds == 2.10
        assert value_bet.probability == 0.55
        assert value_bet.expected_value == (2.10 * 0.55) - 1

    def test_is_value(self):
        """测试是否为价值投注"""
        # 正期望值
        value_bet = ValueBet(odds=2.10, probability=0.55, threshold=1.0)
        assert value_bet.is_value() is True

        # 负期望值
        value_bet2 = ValueBet(odds=1.80, probability=0.50, threshold=1.0)
        assert value_bet2.is_value() is False

    def test_get_confidence(self):
        """测试获取价值置信度"""
        # 高价值
        value_bet = ValueBet(odds=3.0, probability=0.40, threshold=1.0)
        confidence = value_bet.get_confidence()
        assert confidence > 0.5

        # 低价值
        value_bet2 = ValueBet(odds=2.05, probability=0.51, threshold=1.0)
        confidence2 = value_bet2.get_confidence()
        assert confidence2 < 0.5

        # 无价值
        value_bet3 = ValueBet(odds=1.90, probability=0.50, threshold=1.0)
        confidence3 = value_bet3.get_confidence()
        assert confidence3 == 0.0
