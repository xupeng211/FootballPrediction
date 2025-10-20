"""
使用Faker的数据库模型测试
Database Models Tests with Faker

使用Faker生成动态测试数据来测试数据库模型。
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from src.database.base import Base
from src.database.models.team import Team
from src.database.models.predictions import Predictions as Prediction

# 尝试导入Match模型，如果不存在则跳过
try:
    from src.database.models.match import Match
except ImportError:
    Match = None
# 导入Faker工厂
try:
    from tests.factories.fake_data_improved import FootballDataFactory
except ImportError:
    # 如果改进版本不存在，尝试旧版本
    try:
        from tests.factories.fake_data import FootballDataFactory
    except ImportError:
        # 如果都不存在，创建一个简单的工厂
        from faker import Faker

        fake = Faker()

        class FootballDataFactory:
            @staticmethod
            def team():
                return {
                    "name": fake.company(),
                    "league": fake.word(),
                    "founded_year": fake.year(),
                    "home_city": fake.city(),
                    "stadium": fake.company(),
                    "capacity": fake.random_int(1000, 80000),
                    "manager": fake.name(),
                    "website": fake.url(),
                    "created_at": fake.date_time_this_year(),
                }

            @staticmethod
            def match():
                return {
                    "match_id": fake.random_int(1000, 9999),
                    "home_team": fake.company(),
                    "away_team": fake.company(),
                    "home_score": fake.random_int(0, 5),
                    "away_score": fake.random_int(0, 5),
                    "match_date": fake.date_time_this_year(),
                    "league": fake.word(),
                    "venue": fake.company(),
                }

            @staticmethod
            def prediction():
                return {
                    "match_id": fake.random_int(1000, 9999),
                    "home_win_prob": round(fake.random_uniform(0, 1), 2),
                    "draw_prob": round(fake.random_uniform(0, 1), 2),
                    "away_win_prob": round(fake.random_uniform(0, 1), 2),
                    "predicted_outcome": fake.random_element(["home", "draw", "away"]),
                    "confidence": round(fake.random_uniform(0.5, 1), 2),
                    "model_version": f"v{fake.random_int(1, 9)}.{fake.random_int(0, 9)}",
                    "predicted_at": fake.date_time_this_year(),
                }

            @staticmethod
            def batch_teams(count):
                return [FootballDataFactory.team() for _ in range(count)]

            @staticmethod
            def batch_matches(count):
                return [FootballDataFactory.match() for _ in range(count)]

            @staticmethod
            def batch_predictions(count):
                return [FootballDataFactory.prediction() for _ in range(count)]


@pytest.mark.unit
@pytest.mark.fast
class TestMatchModel:
    """测试Match模型"""

    @pytest.fixture(autouse=True)
    def check_match_model(self):
        """检查Match模型是否可用"""
        if Match is None:
            pytest.skip("Match model not available")

    @pytest.fixture
    def db_session(self):
        """创建测试数据库会话"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_create_match_with_fake_data(self, db_session):
        """使用假数据创建比赛记录"""
        fake_match = FootballDataFactory.match()

        # 创建数据库记录
        match = Match(
            id=fake_match["match_id"],
            home_team_name=fake_match["home_team"],
            away_team_name=fake_match["away_team"],
            home_score=fake_match["home_score"],
            away_score=fake_match["away_score"],
            match_date=fake_match["match_date"],
            league=fake_match["league"],
            venue=fake_match["venue"],
            status="completed",
        )

        db_session.add(match)
        db_session.commit()

        # 验证记录
        retrieved = db_session.query(Match).filter_by(id=fake_match["match_id"]).first()
        assert retrieved is not None
        assert retrieved.home_team_name == fake_match["home_team"]
        assert retrieved.away_team_name == fake_match["away_team"]
        assert retrieved.home_score == fake_match["home_score"]
        assert retrieved.away_score == fake_match["away_score"]

    def test_match_model_validation(self, db_session):
        """测试比赛模型验证"""
        match = Match(
            home_team_name="Team A",
            away_team_name="Team B",
            match_date=datetime.utcnow(),
            league="Test League",
        )

        db_session.add(match)
        db_session.commit()

        # 验证必需字段
        assert match.home_team_name is not None
        assert match.away_team_name is not None
        assert match.match_date is not None
        assert match.league is not None

    def test_match_relationships(self, db_session):
        """测试比赛关系"""
        # 先创建球队
        home_team = Team(name="Team A", league="Test League")
        away_team = Team(name="Team B", league="Test League")
        db_session.add_all([home_team, away_team])
        db_session.commit()

        # 创建比赛
        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_team_name="Team A",
            away_team_name="Team B",
            match_date=datetime.utcnow(),
            league="Test League",
        )

        db_session.add(match)
        db_session.commit()

        # 验证关系
        retrieved_match = db_session.query(Match).first()
        assert retrieved_match.home_team.id == home_team.id
        assert retrieved_match.away_team.id == away_team.id


@pytest.mark.unit
@pytest.mark.fast
class TestTeamModel:
    """测试Team模型"""

    @pytest.fixture
    def db_session(self):
        """创建测试数据库会话"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_create_team_with_fake_data(self, db_session):
        """使用假数据创建球队记录"""
        fake_team = FootballDataFactory.team()

        team = Team(
            name=fake_team["name"],
            league=fake_team["league"],
            founded_year=fake_team["founded_year"],
            home_city=fake_team["home_city"],
            stadium=fake_team["stadium"],
            capacity=fake_team["capacity"],
            manager=fake_team["manager"],
            website=fake_team["website"],
            created_at=fake_team["created_at"],
        )

        db_session.add(team)
        db_session.commit()

        # 验证记录
        retrieved = db_session.query(Team).filter_by(name=fake_team["name"]).first()
        assert retrieved is not None
        assert retrieved.league == fake_team["league"]
        assert retrieved.founded_year == fake_team["founded_year"]
        assert retrieved.stadium == fake_team["stadium"]

    def test_team_model_validation(self, db_session):
        """测试球队模型验证"""
        team = Team(name="Test Team", league="Test League", founded_year=2000)

        db_session.add(team)
        db_session.commit()

        # 验证字段
        assert team.name == "Test Team"
        assert team.league == "Test League"
        assert team.founded_year == 2000
        assert team.id is not None

    def test_team_unique_name(self, db_session):
        """测试球队名称唯一性"""
        team1 = Team(name="Unique Team", league="League A")
        team2 = Team(name="Unique Team", league="League B")

        db_session.add(team1)
        db_session.commit()

        # 第二个同名球队应该失败（如果设置了唯一约束）
        db_session.add(team2)
        with pytest.raises(Exception):  # 可能是IntegrityError或其他异常
            db_session.commit()


@pytest.mark.unit
@pytest.mark.fast
class TestPredictionModel:
    """测试Prediction模型"""

    @pytest.fixture
    def db_session(self):
        """创建测试数据库会话"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_create_prediction_with_fake_data(self, db_session):
        """使用假数据创建预测记录"""
        fake_prediction = FootballDataFactory.prediction()

        prediction = Prediction(
            match_id=fake_prediction["match_id"],
            home_win_prob=fake_prediction["home_win_prob"],
            draw_prob=fake_prediction["draw_prob"],
            away_win_prob=fake_prediction["away_win_prob"],
            predicted_outcome=fake_prediction["predicted_outcome"],
            confidence=fake_prediction["confidence"],
            model_version=fake_prediction["model_version"],
            predicted_at=fake_prediction["predicted_at"],
        )

        db_session.add(prediction)
        db_session.commit()

        # 验证记录
        retrieved = (
            db_session.query(Prediction)
            .filter_by(match_id=fake_prediction["match_id"])
            .first()
        )
        assert retrieved is not None
        assert retrieved.home_win_prob == fake_prediction["home_win_prob"]
        assert retrieved.predicted_outcome == fake_prediction["predicted_outcome"]
        assert retrieved.confidence == fake_prediction["confidence"]

    def test_prediction_model_validation(self, db_session):
        """测试预测模型验证"""
        prediction = Prediction(
            match_id=123,
            home_win_prob=0.5,
            draw_prob=0.3,
            away_win_prob=0.2,
            predicted_outcome="home",
            confidence=0.75,
            model_version="v1.0",
            predicted_at=datetime.utcnow(),
        )

        db_session.add(prediction)
        db_session.commit()

        # 验证概率总和
        total_prob = (
            prediction.home_win_prob + prediction.draw_prob + prediction.away_win_prob
        )
        assert abs(total_prob - 1.0) < 0.01

        # 验证预测结果
        assert prediction.predicted_outcome in ["home", "draw", "away"]

        # 验证置信度范围
        assert 0 <= prediction.confidence <= 1

    def test_prediction_multiple_per_match(self, db_session):
        """测试一场比赛的多个预测"""
        match_id = 456

        # 创建多个预测（不同模型版本）
        predictions = [
            Prediction(
                match_id=match_id,
                home_win_prob=0.6,
                draw_prob=0.3,
                away_win_prob=0.1,
                predicted_outcome="home",
                confidence=0.8,
                model_version="v1.0",
                predicted_at=datetime.utcnow(),
            ),
            Prediction(
                match_id=match_id,
                home_win_prob=0.55,
                draw_prob=0.35,
                away_win_prob=0.1,
                predicted_outcome="home",
                confidence=0.75,
                model_version="v2.0",
                predicted_at=datetime.utcnow(),
            ),
        ]

        db_session.add_all(predictions)
        db_session.commit()

        # 验证所有预测都被保存
        retrieved = db_session.query(Prediction).filter_by(match_id=match_id).all()
        assert len(retrieved) == 2
        assert all(p.match_id == match_id for p in retrieved)


@pytest.mark.unit
@pytest.mark.fast
class TestModelQueries:
    """测试模型查询"""

    @pytest.fixture
    def db_session_with_data(self):
        """创建包含测试数据的数据库会话"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        # 添加测试数据
        fake_teams = FootballDataFactory.batch_teams(5)
        teams = []
        for team_data in fake_teams:
            team = Team(
                name=team_data["name"],
                league=team_data["league"],
                founded_year=team_data["founded_year"],
            )
            teams.append(team)
        session.add_all(teams)
        session.commit()

        # 只有Match模型可用时才添加比赛数据
        if Match is not None:
            fake_matches = FootballDataFactory.batch_matches(10)
            matches = []
            for match_data in fake_matches:
                match = Match(
                    home_team_name=match_data["home_team"],
                    away_team_name=match_data["away_team"],
                    home_score=match_data["home_score"],
                    away_score=match_data["away_score"],
                    match_date=match_data["match_date"],
                    league=match_data["league"],
                    status="completed",
                )
                matches.append(match)
            session.add_all(matches)
            session.commit()

        yield session
        session.close()

    def test_query_matches_by_date_range(self, db_session_with_data):
        """测试按日期范围查询比赛"""
        if Match is None:
            pytest.skip("Match model not available")

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow() + timedelta(days=7)

        matches = (
            db_session_with_data.query(Match)
            .filter(Match.match_date >= start_date, Match.match_date <= end_date)
            .all()
        )

        assert len(matches) > 0

    def test_query_teams_by_league(self, db_session_with_data):
        """测试按联赛查询球队"""
        league_name = "Test League"
        teams = db_session_with_data.query(Team).filter_by(league=league_name).all()

        # 所有查询的球队都应该属于指定联赛
        assert all(team.league == league_name for team in teams)

    def test_query_predictions_by_confidence(self, db_session_with_data):
        """测试按置信度查询预测"""
        # 先添加一些预测
        fake_predictions = FootballDataFactory.batch_predictions(5)
        for pred_data in fake_predictions:
            prediction = Prediction(
                match_id=pred_data["match_id"],
                home_win_prob=pred_data["home_win_prob"],
                draw_prob=pred_data["draw_prob"],
                away_win_prob=pred_data["away_win_prob"],
                predicted_outcome=pred_data["predicted_outcome"],
                confidence=pred_data["confidence"],
                model_version=pred_data["model_version"],
                predicted_at=pred_data["predicted_at"],
            )
            db_session_with_data.add(prediction)
        db_session_with_data.commit()

        # 查询高置信度预测
        high_confidence = (
            db_session_with_data.query(Prediction)
            .filter(Prediction.confidence >= 0.8)
            .all()
        )

        # 验证结果
        assert all(p.confidence >= 0.8 for p in high_confidence)

    def test_order_and_limit_queries(self, db_session_with_data):
        """测试排序和限制查询"""
        if Match is None:
            pytest.skip("Match model not available")

        # 查询最近的5场比赛
        recent_matches = (
            db_session_with_data.query(Match)
            .order_by(Match.match_date.desc())
            .limit(5)
            .all()
        )

        assert len(recent_matches) <= 5

        # 验证排序
        for i in range(len(recent_matches) - 1):
            assert recent_matches[i].match_date >= recent_matches[i + 1].match_date

    def test_aggregate_queries(self, db_session_with_data):
        """测试聚合查询"""
        if Match is None:
            pytest.skip("Match model not available")

        # 统计每个联赛的比赛数量
        from sqlalchemy import func

        match_counts = (
            db_session_with_data.query(
                Match.league, func.count(Match.id).label("match_count")
            )
            .group_by(Match.league)
            .all()
        )

        assert len(match_counts) > 0
        for league, count in match_counts:
            assert isinstance(league, str)
            assert isinstance(count, int)
            assert count > 0
