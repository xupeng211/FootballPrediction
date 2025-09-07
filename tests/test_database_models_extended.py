"""扩展的数据库模型测试"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.base import Base
from src.database.models import (
    League,
    Team,
    Match,
    Odds,
    Features,
    Predictions,
    MarketType,
    TeamType,
    PredictedResult,
)


@pytest.fixture(scope="function")
def session():
    """创建临时数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


class TestBaseModelMethods:
    """测试BaseModel的方法"""

    def test_to_dict_method(self, session):
        """测试to_dict方法"""
        league = League(league_name="英超", league_code="EPL", country="英格兰")
        session.add(league)
        session.commit()

        result = league.to_dict()
        assert isinstance(result, dict)
        assert result["league_name"] == "英超"
        assert result["league_code"] == "EPL"
        assert result["country"] == "英格兰"
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_to_dict_exclude_fields(self, session):
        """测试to_dict方法排除字段"""
        league = League(league_name="英超", league_code="EPL")
        session.add(league)
        session.commit()

        result = league.to_dict(exclude_fields={"created_at", "updated_at"})
        assert "league_name" in result
        assert "created_at" not in result
        assert "updated_at" not in result

    def test_from_dict_method(self, session):
        """测试from_dict方法"""
        data = {"league_name": "西甲", "league_code": "LALIGA", "country": "西班牙"}

        league = League.from_dict(data)
        assert league.league_name == "西甲"
        assert league.league_code == "LALIGA"
        assert league.country == "西班牙"

    def test_update_from_dict_method(self, session):
        """测试update_from_dict方法"""
        league = League(league_name="英超", league_code="EPL")
        session.add(league)
        session.commit()

        update_data = {"country": "英格兰", "level": 1}

        league.update_from_dict(update_data)
        assert league.country == "英格兰"
        assert league.level == 1
        assert league.league_name == "英超"  # 未更新的字段保持原值


class TestMatchModelMethods:
    """测试Match模型的额外方法"""

    def test_match_name_property(self, session):
        """测试match_name属性"""
        league = League(league_name="英超")
        session.add(league)
        session.flush()

        home_team = Team(team_name="曼联", league_id=league.id)
        away_team = Team(team_name="切尔西", league_id=league.id)
        session.add_all([home_team, away_team])
        session.flush()

        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id,
            season="2023-24",
            match_date=datetime.now() + timedelta(days=1),
        )
        session.add(match)
        session.commit()

        assert match.match_name == "曼联 vs 切尔西"

    def test_final_score_property(self, session):
        """测试final_score属性"""
        league = League(league_name="英超")
        session.add(league)
        session.flush()

        home_team = Team(team_name="曼联", league_id=league.id)
        away_team = Team(team_name="切尔西", league_id=league.id)
        session.add_all([home_team, away_team])
        session.flush()

        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id,
            season="2023-24",
            match_date=datetime.now(),
            home_score=2,
            away_score=1,
        )
        session.add(match)
        session.commit()

        assert match.final_score == "2-1"

        # 测试无比分情况
        match.home_score = None
        match.away_score = None
        assert match.final_score == "未开始"

    def test_get_result_method(self, session):
        """测试get_result方法"""
        league = League(league_name="英超")
        session.add(league)
        session.flush()

        home_team = Team(team_name="曼联", league_id=league.id)
        away_team = Team(team_name="切尔西", league_id=league.id)
        session.add_all([home_team, away_team])
        session.flush()

        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id,
            season="2023-24",
            match_date=datetime.now(),
            home_score=2,
            away_score=1,
        )
        session.add(match)
        session.commit()

        assert match.get_result() == "home_win"

        match.home_score = 1
        match.away_score = 2
        assert match.get_result() == "away_win"

        match.home_score = 1
        match.away_score = 1
        assert match.get_result() == "draw"

    def test_get_total_goals_method(self, session):
        """测试get_total_goals方法"""
        league = League(league_name="英超")
        session.add(league)
        session.flush()

        home_team = Team(team_name="曼联", league_id=league.id)
        away_team = Team(team_name="切尔西", league_id=league.id)
        session.add_all([home_team, away_team])
        session.flush()

        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id,
            season="2023-24",
            match_date=datetime.now(),
            home_score=2,
            away_score=1,
        )
        session.add(match)
        session.commit()

        assert match.get_total_goals() == 3


class TestOddsModelMethods:
    """测试Odds模型的额外方法"""

    def test_get_implied_probabilities(self, session):
        """测试get_implied_probabilities方法"""
        league = League(league_name="英超")
        session.add(league)
        session.flush()

        home_team = Team(team_name="曼联", league_id=league.id)
        away_team = Team(team_name="切尔西", league_id=league.id)
        session.add_all([home_team, away_team])
        session.flush()

        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id,
            season="2023-24",
            match_date=datetime.now(),
        )
        session.add(match)
        session.flush()

        odds = Odds(
            match_id=match.id,
            bookmaker="Bet365",
            market_type=MarketType.ONE_X_TWO,
            home_odds=Decimal("2.00"),
            draw_odds=Decimal("3.00"),
            away_odds=Decimal("4.00"),
            collected_at=datetime.now(),
        )
        session.add(odds)
        session.commit()

        probabilities = odds.get_implied_probabilities()
        assert isinstance(probabilities, dict)
        assert "home_win" in probabilities
        assert "draw" in probabilities
        assert "away_win" in probabilities
        assert "bookmaker_margin" in probabilities

        # 验证概率计算正确性
        assert abs(probabilities["home_win"] - 0.5) < 0.01  # 1/2.00 = 0.5


class TestFeaturesModelMethods:
    """测试Features模型的额外方法"""

    def test_calculate_team_strength(self, session):
        """测试calculate_team_strength方法"""
        league = League(league_name="英超")
        session.add(league)
        session.flush()

        team = Team(team_name="曼联", league_id=league.id)
        session.add(team)
        session.flush()

        match = Match(
            home_team_id=team.id,
            away_team_id=team.id,
            league_id=league.id,
            season="2023-24",
            match_date=datetime.now(),
        )
        session.add(match)
        session.flush()

        features = Features(
            match_id=match.id,
            team_id=team.id,
            team_type=TeamType.HOME,
            recent_5_wins=4,
            recent_5_draws=1,
            recent_5_losses=0,
            recent_5_goals_for=10,
            recent_5_goals_against=2,
            home_wins=8,
            home_draws=2,
            home_losses=0,
            home_games_played=10,
            avg_goals_per_game=Decimal("2.5"),
            avg_goals_conceded=Decimal("0.8"),
        )
        session.add(features)
        session.commit()

        strength = features.calculate_team_strength()
        assert isinstance(strength, float)
        assert 0.0 <= strength <= 100.0
        assert strength > 50.0  # 应该是一个强队

    def test_get_feature_vector(self, session):
        """测试get_feature_vector方法"""
        league = League(league_name="英超")
        session.add(league)
        session.flush()

        team = Team(team_name="曼联", league_id=league.id)
        session.add(team)
        session.flush()

        match = Match(
            home_team_id=team.id,
            away_team_id=team.id,
            league_id=league.id,
            season="2023-24",
            match_date=datetime.now(),
        )
        session.add(match)
        session.flush()

        features = Features(
            match_id=match.id,
            team_id=team.id,
            team_type=TeamType.HOME,
            recent_5_wins=3,
            recent_5_draws=1,
            recent_5_losses=1,
            recent_5_goals_for=8,
            recent_5_goals_against=4,
        )
        session.add(features)
        session.commit()

        vector = features.get_feature_vector()
        assert isinstance(vector, dict)
        assert "recent_5_wins" in vector
        assert "recent_5_draws" in vector
        assert "recent_5_losses" in vector
        assert "is_home" in vector
        assert vector["is_home"] == 1.0  # 是主队


class TestPredictionsModelMethods:
    """测试Predictions模型的额外方法"""

    def test_max_probability_property(self, session):
        """测试max_probability属性"""
        league = League(league_name="英超")
        session.add(league)
        session.flush()

        home_team = Team(team_name="曼联", league_id=league.id)
        away_team = Team(team_name="切尔西", league_id=league.id)
        session.add_all([home_team, away_team])
        session.flush()

        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id,
            season="2023-24",
            match_date=datetime.now(),
        )
        session.add(match)
        session.flush()

        prediction = Predictions(
            match_id=match.id,
            model_name="XGBoost",
            model_version="1.0",
            predicted_result=PredictedResult.HOME_WIN,
            home_win_probability=Decimal("0.6"),
            draw_probability=Decimal("0.25"),
            away_win_probability=Decimal("0.15"),
        )
        session.add(prediction)
        session.commit()

        assert float(prediction.max_probability) == 0.6

    def test_get_probabilities_dict(self, session):
        """测试get_probabilities_dict方法"""
        league = League(league_name="英超")
        session.add(league)
        session.flush()

        home_team = Team(team_name="曼联", league_id=league.id)
        away_team = Team(team_name="切尔西", league_id=league.id)
        session.add_all([home_team, away_team])
        session.flush()

        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id,
            season="2023-24",
            match_date=datetime.now(),
        )
        session.add(match)
        session.flush()

        prediction = Predictions(
            match_id=match.id,
            model_name="XGBoost",
            model_version="1.0",
            predicted_result=PredictedResult.HOME_WIN,
            home_win_probability=Decimal("0.6"),
            draw_probability=Decimal("0.25"),
            away_win_probability=Decimal("0.15"),
        )
        session.add(prediction)
        session.commit()

        probs = prediction.get_probabilities_dict()
        assert isinstance(probs, dict)
        assert probs["home_win"] == 0.6
        assert probs["draw"] == 0.25
        assert probs["away_win"] == 0.15
