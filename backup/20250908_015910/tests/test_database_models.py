"""
数据库模型测试

测试所有数据模型的基本功能和关系。
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.base import Base
from src.database.models import (
    Features,
    League,
    MarketType,
    Match,
    MatchStatus,
    Odds,
    PredictedResult,
    Predictions,
    Team,
    TeamType,
)


@pytest.fixture
def engine():
    """创建内存SQLite数据库用于测试"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """创建数据库会话"""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestDatabaseModels:
    """数据库模型测试类"""

    def test_league_model(self, session):
        """测试联赛模型"""
        league = League(
            league_name="英格兰超级联赛",
            league_code="EPL",
            country="England",
            level=1,
            season_start_month=8,
            season_end_month=5,
            is_active=True,
        )

        session.add(league)
        session.commit()

        # 验证数据保存成功
        saved_league = session.query(League).filter_by(league_code="EPL").first()
        assert saved_league is not None
        assert saved_league.league_name == "英格兰超级联赛"
        assert saved_league.is_top_league() is True
        assert "England" in saved_league.display_name

    def test_team_model(self, session):
        """测试球队模型"""
        # 创建联赛
        league = League(
            league_name="英格兰超级联赛", league_code="EPL", country="England"
        )
        session.add(league)
        session.commit()

        # 创建球队
        team = Team(
            team_name="曼彻斯特联",
            team_code="MUN",
            country="England",
            league_id=league.id,
            founded_year=1878,
            stadium="老特拉福德球场",
            is_active=True,
        )

        session.add(team)
        session.commit()

        # 验证数据和关系
        saved_team = session.query(Team).filter_by(team_code="MUN").first()
        assert saved_team is not None
        assert saved_team.league.league_name == "英格兰超级联赛"
        assert saved_team.display_name == "曼彻斯特联 (英格兰超级联赛)"

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

        # 验证数据和关系
        saved_match = session.query(Match).first()
        assert saved_match is not None
        assert saved_match.home_team.team_name == "曼联"
        assert saved_match.away_team.team_name == "切尔西"
        assert saved_match.is_upcoming is True
        assert saved_match.match_name == "曼联 vs 切尔西"

        # 测试更新比分
        saved_match.update_score(2, 1, 1, 0)
        assert saved_match.final_score == "2-1"
        assert saved_match.ht_score == "1-0"
        assert saved_match.get_result() == "home_win"
        assert saved_match.get_total_goals() == 3
        assert saved_match.is_over_2_5_goals() is True
        assert saved_match.both_teams_scored() is True

    def test_odds_model(self, session):
        """测试赔率模型"""
        # 创建必要的前置数据
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
            match_date=datetime.now() + timedelta(days=1),
        )
        session.add(match)
        session.commit()

        # 创建赔率
        odds = Odds(
            match_id=match.id,
            bookmaker="Bet365",
            market_type=MarketType.ONE_X_TWO,
            home_odds=Decimal("2.10"),
            draw_odds=Decimal("3.20"),
            away_odds=Decimal("3.50"),
            collected_at=datetime.now(),
        )

        session.add(odds)
        session.commit()

        # 验证数据
        saved_odds = session.query(Odds).first()
        assert saved_odds is not None
        assert saved_odds.is_1x2_market is True
        assert saved_odds.bookmaker == "Bet365"

        # 测试隐含概率计算
        probabilities = saved_odds.get_implied_probabilities()
        assert probabilities is not None
        assert "home_win" in probabilities
        assert "bookmaker_margin" in probabilities
        assert probabilities["home_win"] > 0
        assert probabilities["home_win"] < 1

    def test_features_model(self, session):
        """测试特征模型"""
        # 创建必要的前置数据
        league = League(league_name="英超")
        session.add(league)
        session.flush()

        team = Team(team_name="曼联", league_id=league.id)
        session.add(team)
        session.flush()

        match = Match(
            home_team_id=team.id,
            away_team_id=team.id,  # 简化测试
            league_id=league.id,
            match_date=datetime.now(),
        )
        session.add(match)
        session.commit()

        # 创建特征
        features = Features(
            match_id=match.id,
            team_id=team.id,
            team_type=TeamType.HOME,
            recent_5_wins=4,
            recent_5_draws=1,
            recent_5_losses=0,
            recent_5_goals_for=12,
            recent_5_goals_against=3,
            home_wins=10,
            home_draws=3,
            home_losses=2,
            league_position=2,
            points=45,
            goal_difference=15,
            is_derby=False,
            avg_possession=Decimal("65.5"),
            win_streak=3,
            unbeaten_streak=8,
        )

        session.add(features)
        session.commit()

        # 验证数据和计算属性
        saved_features = session.query(Features).first()
        assert saved_features is not None
        assert saved_features.is_home_team is True
        assert saved_features.recent_5_points == 13  # 4*3 + 1*1
        assert saved_features.recent_5_win_rate == 0.8  # 4/5
        assert saved_features.recent_5_goal_difference == 9  # 12-3

        # 测试特征向量
        feature_vector = saved_features.get_feature_vector()
        assert isinstance(feature_vector, dict)
        assert feature_vector["recent_5_wins"] == 4
        assert feature_vector["avg_possession"] == 65.5

        # 测试球队实力计算
        strength = saved_features.calculate_team_strength()
        assert isinstance(strength, float)
        assert 0 <= strength <= 100

    def test_predictions_model(self, session):
        """测试预测模型"""
        # 创建必要的前置数据
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
            match_date=datetime.now() + timedelta(days=1),
        )
        session.add(match)
        session.commit()

        # 创建预测
        prediction = Predictions(
            match_id=match.id,
            model_name="XGBoost",
            model_version="1.0.0",
            predicted_result=PredictedResult.HOME_WIN,
            home_win_probability=Decimal("0.6500"),
            draw_probability=Decimal("0.2000"),
            away_win_probability=Decimal("0.1500"),
            predicted_home_score=Decimal("2.1"),
            predicted_away_score=Decimal("1.3"),
            over_2_5_probability=Decimal("0.7200"),
            both_teams_score_probability=Decimal("0.6800"),
            confidence_score=Decimal("0.8500"),
            feature_importance={
                "recent_form": 0.25,
                "h2h_record": 0.20,
                "home_advantage": 0.15,
            },
        )

        session.add(prediction)
        session.commit()

        # 验证数据
        saved_prediction = session.query(Predictions).first()
        assert saved_prediction is not None
        assert saved_prediction.model_name == "XGBoost"
        assert saved_prediction.max_probability == 0.65
        assert saved_prediction.prediction_confidence_level == "中"
        assert "主队获胜" in saved_prediction.prediction_summary

        # 测试概率字典
        probs = saved_prediction.get_probabilities_dict()
        assert probs["home_win"] == 0.65
        assert probs["draw"] == 0.20
        assert probs["away_win"] == 0.15

        # 测试特征重要性
        top_features = saved_prediction.get_top_features(3)
        assert len(top_features) == 3
        assert top_features[0]["feature"] == "recent_form"
        assert top_features[0]["importance"] == 0.25

        # 测试准确性计算（模拟实际结果）
        accuracy = saved_prediction.calculate_accuracy("home_win")
        assert accuracy["prediction_correct"] is True
        assert accuracy["predicted_probability"] == 0.65

        # 测试投注建议
        odds_data = {"home_win": 2.0, "draw": 4.0, "away_win": 8.0}
        recommendations = saved_prediction.get_betting_recommendations(odds_data)
        assert len(recommendations) == 3
        assert recommendations[0]["outcome"] == "home_win"  # 最高期望价值

    def test_model_relationships(self, session):
        """测试模型之间的关系"""
        # 创建完整的数据链
        league = League(league_name="英超", league_code="EPL")
        session.add(league)
        session.flush()

        home_team = Team(team_name="曼联", team_code="MUN", league_id=league.id)
        away_team = Team(team_name="切尔西", team_code="CHE", league_id=league.id)
        session.add_all([home_team, away_team])
        session.flush()

        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id,
            match_date=datetime.now(),
        )
        session.add(match)
        session.commit()

        # 验证关系
        assert league.teams.count() == 2
        assert home_team.league.league_name == "英超"
        assert match.home_team.team_name == "曼联"
        assert match.league.league_code == "EPL"

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
            match_date=datetime.now(),
        )
        session.add(match)
        session.flush()

        # 创建预测（概率总和为1.0）
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

        # 验证概率总和
        saved_prediction = session.query(Predictions).first()
        probs = saved_prediction.get_probabilities_dict()
        total_prob = sum(probs.values())
        assert abs(total_prob - 1.0) < 0.001  # 容差为0.001
