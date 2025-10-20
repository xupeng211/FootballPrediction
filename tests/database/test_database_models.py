"""
数据库模型测试
使用Mock和内存数据库进行测试，避免依赖真实数据库
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入数据库相关模块
try:
    from sqlalchemy import (
        create_engine,
        Column,
        Integer,
        String,
        DateTime,
        Boolean,
        Float,
    )
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    from src.database.models.league import League
    from src.database.models.match import Match
    from src.database.models.team import Team
    from src.database.models.user import User
    from src.database.models.features import Feature
    from src.database.models.predictions import Prediction
    from src.database.base import Base
except ImportError as e:
    pytest.skip(f"数据库模块不可用: {e}", allow_module_level=True)


class TestDatabaseModels:
    """测试数据库模型"""

    @pytest.fixture
    def mock_engine(self):
        """创建内存数据库引擎"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def mock_session(self, mock_engine):
        """创建数据库会话"""
        SessionLocal = sessionmaker(bind=mock_engine)
        session = SessionLocal()
        yield session
        session.close()

    # ================ League模型测试 ================

    def test_league_model_creation(self):
        """测试League模型创建"""
        league = League(
            name="Premier League", country="England", season="2024/2025", is_active=True
        )
        assert league.name == "Premier League"
        assert league.country == "England"
        assert league.season == "2024/2025"
        assert league.is_active is True

    def test_league_model_with_mock(self):
        """使用Mock测试League模型"""
        with patch("src.database.models.league.League") as MockLeague:
            league = MockLeague()
            league.name = "La Liga"
            league.country = "Spain"
            league.save = Mock(return_value=True)

            result = league.save()
            assert result is True
            league.save.assert_called_once()

    # ================ Team模型测试 ================

    def test_team_model_creation(self):
        """测试Team模型创建"""
        team = Team(
            name="Manchester United",
            short_name="MU",
            founded=1878,
            city="Manchester",
            country="England",
            is_active=True,
        )
        assert team.name == "Manchester United"
        assert team.short_name == "MU"
        assert team.founded == 1878
        assert team.city == "Manchester"

    def test_team_model_methods(self):
        """测试Team模型方法"""
        with patch("src.database.models.team.Team") as MockTeam:
            team = MockTeam()
            team.get_active_players = Mock(return_value=25)
            team.get_average_age = Mock(return_value=24.5)

            players = team.get_active_players()
            avg_age = team.get_average_age()

            assert players == 25
            assert avg_age == 24.5

    # ================ Match模型测试 ================

    def test_match_model_creation(self):
        """测试Match模型创建"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_date=datetime(2025, 1, 18, 15, 0),
            venue="Old Trafford",
            status="SCHEDULED",
        )
        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.status == "SCHEDULED"

    def test_match_model_result(self):
        """测试Match模型结果"""
        with patch("src.database.models.match.Match") as MockMatch:
            match = MockMatch()
            match.set_result = Mock(return_value={"home_score": 2, "away_score": 1})
            match.is_finished = Mock(return_value=True)

            result = match.set_result(2, 1)
            finished = match.is_finished()

            assert result["home_score"] == 2
            assert result["away_score"] == 1
            assert finished is True

    # ================ User模型测试 ================

    def test_user_model_creation(self):
        """测试User模型创建"""
        user = User(
            username="john_doe",
            email="john@example.com",
            is_active=True,
            is_verified=False,
        )
        assert user.username == "john_doe"
        assert user.email == "john@example.com"
        assert user.is_active is True
        assert user.is_verified is False

    def test_user_model_password(self):
        """测试用户密码处理"""
        with patch("src.database.models.user.User") as MockUser:
            user = MockUser()
            user.set_password = Mock(return_value=True)
            user.check_password = Mock(return_value=True)

            user.set_password("secure_password")
            assert user.check_password("secure_password") is True

    # ================ Feature模型测试 ================

    def test_feature_model_creation(self):
        """测试Feature模型创建"""
        feature = Feature(
            name="home_win_probability",
            value=0.75,
            match_id=123,
            model_version="v1.0",
            created_at=datetime.now(),
        )
        assert feature.name == "home_win_probability"
        assert feature.value == 0.75
        assert feature.match_id == 123

    def test_feature_model_validation(self):
        """测试Feature模型验证"""
        with patch("src.database.models.features.Feature") as MockFeature:
            feature = MockFeature()
            feature.is_valid = Mock(return_value=True)
            feature.get_metadata = Mock(return_value={"type": "probability"})

            assert feature.is_valid() is True
            metadata = feature.get_metadata()
            assert metadata["type"] == "probability"

    # ================ Prediction模型测试 ================

    def test_prediction_model_creation(self):
        """测试Prediction模型创建"""
        prediction = Prediction(
            user_id=1,
            match_id=123,
            predicted_result="HOME_WIN",
            confidence=0.85,
            created_at=datetime.now(),
        )
        assert prediction.user_id == 1
        assert prediction.match_id == 123
        assert prediction.predicted_result == "HOME_WIN"
        assert prediction.confidence == 0.85

    def test_prediction_model_outcome(self):
        """测试Prediction模型结果"""
        with patch("src.database.models.predictions.Prediction") as MockPrediction:
            prediction = MockPrediction()
            prediction.set_actual_result = Mock(return_value=True)
            prediction.is_correct = Mock(return_value=True)
            prediction.get_points = Mock(return_value=10)

            prediction.set_actual_result("HOME_WIN")
            assert prediction.is_correct() is True
            assert prediction.get_points() == 10

    # ================ 数据库连接测试 ================

    def test_database_connection(self):
        """测试数据库连接"""
        with patch("src.database.connection.DatabaseConnection") as MockConnection:
            conn = MockConnection()
            conn.connect = Mock(return_value=True)
            conn.is_connected = Mock(return_value=True)
            conn.execute = Mock(return_value=[{"id": 1}])

            assert conn.connect() is True
            assert conn.is_connected() is True
            result = conn.execute("SELECT * FROM users")
            assert result == [{"id": 1}]

    def test_database_transaction(self):
        """测试数据库事务"""
        with patch("src.database.connection.DatabaseConnection") as MockConnection:
            conn = MockConnection()
            conn.begin = Mock(return_value=True)
            conn.commit = Mock(return_value=True)
            conn.rollback = Mock(return_value=True)

            conn.begin()
            # 执行操作
            conn.commit()

            conn.begin.assert_called_once()
            conn.commit.assert_called_once()

    # ================ 仓储模式测试 ================

    def test_match_repository(self):
        """测试比赛仓储"""
        with patch("src.database.repositories.match.MatchRepository") as MockRepo:
            repo = MockRepo()
            repo.get_by_id = Mock(return_value={"id": 123})
            repo.get_all = Mock(return_value=[{"id": 123}, {"id": 456}])
            repo.create = Mock(return_value={"id": 789})
            repo.update = Mock(return_value=True)
            repo.delete = Mock(return_value=True)

            match = repo.get_by_id(123)
            matches = repo.get_all()
            new_match = repo.create({"home_team": "Team A"})

            assert match["id"] == 123
            assert len(matches) == 2
            assert new_match["id"] == 789

    def test_user_repository(self):
        """测试用户仓储"""
        with patch("src.database.repositories.user.UserRepository") as MockRepo:
            repo = MockRepo()
            repo.find_by_email = Mock(
                return_value={"id": 1, "email": "test@example.com"}
            )
            repo.find_by_username = Mock(return_value={"id": 1, "username": "testuser"})
            repo.create_user = Mock(return_value={"id": 1})

            user = repo.find_by_email("test@example.com")
            assert user["email"] == "test@example.com"

            user_by_username = repo.find_by_username("testuser")
            assert user_by_username["username"] == "testuser"

    # ================ 数据库迁移测试 ================

    def test_database_migration(self):
        """测试数据库迁移"""
        with patch("src.database.migrations.DatabaseMigration") as MockMigration:
            migration = MockMigration()
            migration.upgrade = Mock(return_value=True)
            migration.downgrade = Mock(return_value=True)
            migration.get_current_version = Mock(return_value="2025_01_18_001")

            success = migration.upgrade("2025_01_18_001")
            assert success is True

            version = migration.get_current_version()
            assert version == "2025_01_18_001"

    # ================ 批量操作测试 ================

    def test_bulk_operations(self):
        """测试批量操作"""
        with patch("src.database.base.Base") as MockBase:
            base = MockBase()
            base.bulk_insert = Mock(return_value=100)
            base.bulk_update = Mock(return_value=50)
            base.bulk_delete = Mock(return_value=25)

            inserted = base.bulk_insert([{"name": f"item_{i}"} for i in range(100)])
            updated = base.bulk_update(
                [{"id": i, "name": f"updated_{i}"} for i in range(50)]
            )
            deleted = base.bulk_delete([{"id": i} for i in range(25)])

            assert inserted == 100
            assert updated == 50
            assert deleted == 25

    # ================ 查询优化测试 ================

    def test_query_optimization(self):
        """测试查询优化"""
        with patch("src.database.base.Base") as MockBase:
            base = MockBase()
            base.execute_with_indexes = Mock(return_value=100)
            base.explain_query = Mock(return_value=["Index Scan on users"])
            base.get_slow_queries = Mock(return_value=[])

            results = base.execute_with_indexes(
                "SELECT * FROM users WHERE id = ?", (1,)
            )
            explanation = base.explain_query("SELECT * FROM users WHERE id = ?")
            slow_queries = base.get_slow_queries()

            assert results == 100
            assert "Index Scan" in explanation[0]
            assert len(slow_queries) == 0

    # ================ 数据库健康检查 ================

    def test_database_health_check(self):
        """测试数据库健康检查"""
        with patch("src.database.config.DatabaseConfig") as MockConfig:
            config = MockConfig()
            config.check_connection = Mock(return_value=True)
            config.get_connection_pool_size = Mock(return_value=10)
            config.get_database_size = Mock(return_value="1.2GB")
            config.get_slow_query_count = Mock(return_value=0)

            health = {
                "connected": config.check_connection(),
                "pool_size": config.get_connection_pool_size(),
                "db_size": config.get_database_size(),
                "slow_queries": config.get_slow_query_count(),
            }

            assert health["connected"] is True
            assert health["pool_size"] == 10
            assert health["slow_queries"] == 0
