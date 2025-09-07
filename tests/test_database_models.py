"""数据库模型测试"""

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
    MatchStatus,
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


class TestDatabaseModels:
    """数据库模型测试类"""

    def test_league_model(self, session):
        """测试联赛模型"""
        league = League(
            league_name="英超", league_code="EPL", country="英格兰", level=1
        )
        session.add(league)
        session.commit()

        assert league.id is not None
        assert league.league_name == "英超"
        assert league.is_top_league

    def test_team_model(self, session):
        """测试球队模型"""
        # 先创建联赛
        league = League(league_name="英超", league_code="EPL")
        session.add(league)
        session.flush()

        team = Team(
            team_name="曼联", team_code="MUN", league_id=league.id, country="英格兰"
        )
        session.add(team)
        session.commit()

        assert team.id is not None
        assert team.team_name == "曼联"
        assert "曼联" in team.display_name

    def test_match_model(self, session):
        """测试比赛模型"""
        # 创建联赛和球队
        league = League(league_name="英超", league_code="EPL")
        session.add(league)
        session.flush()

        home_team = Team(team_name="曼联", team_code="MUN", league_id=league.id)
        away_team = Team(team_name="切尔西", team_code="CHE", league_id=league.id)
        session.add_all([home_team, away_team])
        session.commit()

        # 创建比赛
        match_date = datetime.now() + timedelta(days=1)
        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id,
            season="2023-24",
            match_date=match_date,
            match_status=MatchStatus.SCHEDULED,
            venue="老特拉福德",
        )
        session.add(match)
        session.commit()

        assert match.id is not None
        assert match.match_status == MatchStatus.SCHEDULED
        assert match.is_upcoming

        # 测试比分更新
        match.update_score(2, 1)
        assert match.home_score == 2
        assert match.away_score == 1

    def test_odds_model(self, session):
        """测试赔率模型"""
        # 创建联赛、球队和比赛
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

        # 创建赔率
        odds = Odds(
            match_id=match.id,
            bookmaker="Bet365",
            market_type=MarketType.ONE_X_TWO,
            home_odds=Decimal("2.50"),
            draw_odds=Decimal("3.20"),
            away_odds=Decimal("2.80"),
            collected_at=datetime.now(),
        )
        session.add(odds)
        session.commit()

        assert odds.id is not None
        assert odds.bookmaker == "Bet365"
        assert odds.is_1x2_market
        assert odds.home_odds == Decimal("2.50")

    def test_features_model(self, session):
        """测试特征模型"""
        # 创建联赛、球队和比赛
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
            match_date=datetime.now() + timedelta(days=1),
        )
        session.add(match)
        session.flush()

        # 创建特征
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

        assert features.id is not None
        assert features.is_home_team
        assert features.recent_5_points == 10  # 3*3 + 1*1
        assert features.recent_5_win_rate() == 0.6  # 3/5

    def test_predictions_model(self, session):
        """测试预测模型"""
        # 创建联赛、球队和比赛
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
        session.flush()

        # 创建预测
        prediction = Predictions(
            match_id=match.id,
            model_name="XGBoost",
            model_version="1.0",
            predicted_result=PredictedResult.HOME_WIN,
            home_win_probability=Decimal("0.6500"),
            draw_probability=Decimal("0.2000"),
            away_win_probability=Decimal("0.1500"),
            confidence_score=Decimal("0.8500"),
        )
        session.add(prediction)
        session.commit()

        assert prediction.id is not None
        assert prediction.predicted_result == PredictedResult.HOME_WIN
        assert float(prediction.max_probability) == float(
            prediction.home_win_probability
        )
        assert prediction.prediction_confidence_level == "Medium"

    def test_model_relationships(self, session):
        """测试模型关系"""
        # 创建完整的数据层次结构
        league = League(league_name="英超", league_code="EPL")
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

        # 验证关系
        assert match.home_team.team_name == "曼联"
        assert match.away_team.team_name == "切尔西"
        assert match.league.league_name == "英超"

    def test_model_validation(self, session):
        """测试模型验证和约束"""
        # 测试概率约束（应该接近1.0）
        league = League(league_name="测试联赛")
        session.add(league)
        session.flush()

        team = Team(team_name="测试队", league_id=league.id)
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

        # 创建预测数据验证概率和
        prediction = Predictions(
            match_id=match.id,
            model_name="TestModel",
            model_version="1.0",
            predicted_result=PredictedResult.HOME_WIN,
            home_win_probability=Decimal("0.5000"),
            draw_probability=Decimal("0.3000"),
            away_win_probability=Decimal("0.2000"),
        )
        session.add(prediction)
        session.commit()

        # 验证概率和
        total_prob = (
            prediction.home_win_probability
            + prediction.draw_probability
            + prediction.away_win_probability
        )
        assert abs(float(total_prob) - 1.0) < 0.01  # 允许小误差
