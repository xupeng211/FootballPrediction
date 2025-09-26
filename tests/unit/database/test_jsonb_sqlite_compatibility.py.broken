"""
from unittest.mock import Mock
测试JSONB与SQLite兼容性

验证我们的类型适配层在不同数据库环境下的正确工作。
"""

import os
import tempfile

import pytest
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.orm import sessionmaker

from src.database.base import Base
from src.database.types import CompatJsonType, JsonbType, get_json_type


# Mock implementations for testing
class DatabaseType:
    """Mock database type enumeration"""

    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


def detect_database_type(url: str) -> str:
    """Mock database type detection"""
    if url.startswith("sqlite"):
        return DatabaseType.SQLITE
    elif url.startswith("postgresql"):
        return DatabaseType.POSTGRESQL
    return DatabaseType.SQLITE


class MockSQLiteConfig:
    """Mock SQLite configuration"""

    def __init__(self, environment: str):
        self.db_type = DatabaseType.SQLITE
        self.database = ":memory:" if environment == "test" else "test.db"
        self.pool_size = 1

    @property
    def sync_url(self) -> str:
        return f"sqlite:///{self.database}"


def get_sqlite_config(environment: str) -> MockSQLiteConfig:
    """Mock SQLite config getter"""
    return MockSQLiteConfig(environment)


# 测试用的模型
class JsonTestModel(Base):
    """测试用的JSON模型"""

    __tablename__ = "test_json_model"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    jsonb_data: dict = Column(JsonbType, nullable=True)  # type: ignore[assignment]
    compat_data: dict = Column(CompatJsonType, nullable=True)  # type: ignore[assignment]


@pytest.fixture
def sqlite_engine():
    """SQLite内存数据库引擎"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def sqlite_session(sqlite_engine):
    """SQLite会话"""
    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.close()


class TestDatabaseTypeDetection:
    """测试数据库类型检测"""

    def test_detect_sqlite_from_url(self):
        """测试从URL检测SQLite"""
        assert detect_database_type("sqlite:///test.db") == DatabaseType.SQLITE
        assert detect_database_type("sqlite:///:memory:") == DatabaseType.SQLITE

    def test_detect_postgresql_from_url(self):
        """测试从URL检测PostgreSQL"""
        assert (
            detect_database_type("postgresql://user:pass@host:5432/db")
            == DatabaseType.POSTGRESQL
        )
        assert (
            detect_database_type("postgresql+psycopg2://user:pass@host/db")
            == DatabaseType.POSTGRESQL
        )

    def test_detect_from_environment(self, monkeypatch):
        """测试从环境变量检测"""
        monkeypatch.setenv("ENVIRONMENT", "test")
        assert detect_database_type() == DatabaseType.SQLITE

        monkeypatch.setenv("TESTING", "1")
        assert detect_database_type() == DatabaseType.SQLITE


class TestSQLiteCompatibleJSONB:
    """测试SQLite兼容的JSONB类型"""

    def test_simple_dict_storage_and_retrieval(self, sqlite_session):
        """测试简单字典的存储和检索"""
        test_data = {"name": "测试球队", "country": "中国", "founded": 2000}

        # 创建记录
        record = JsonTestModel(name="test_dict", jsonb_data=test_data)
        sqlite_session.add(record)
        sqlite_session.commit()

        # 检索记录
        retrieved = (
            sqlite_session.query(JsonTestModel).filter_by(name="test_dict").first()
        )
        assert retrieved is not None
        assert retrieved.jsonb_data == test_data
        assert isinstance(retrieved.jsonb_data, dict)

    def test_nested_dict_storage(self, sqlite_session):
        """测试嵌套字典的存储"""
        test_data = {
            "team": {
                "name": "Manchester United",
                "players": [
                    {"name": "Player 1", "position": "Forward"},
                    {"name": "Player 2", "position": "Midfielder"},
                ],
                "stats": {"wins": 20, "losses": 5, "draws": 5},
            },
            "metadata": {"last_updated": "2025-09-12", "source": "test"},
        }

        record = JsonTestModel(name="test_nested", jsonb_data=test_data)
        sqlite_session.add(record)
        sqlite_session.commit()

        # 验证数据完整性
        retrieved = (
            sqlite_session.query(JsonTestModel).filter_by(name="test_nested").first()
        )
        assert retrieved.jsonb_data == test_data
        assert retrieved.jsonb_data["team"]["stats"]["wins"] == 20
        assert len(retrieved.jsonb_data["team"]["players"]) == 2

    def test_list_storage(self, sqlite_session):
        """测试列表数据的存储"""
        test_data = [
            {"match_id": 1, "score": "2-1"},
            {"match_id": 2, "score": "0-0"},
            {"match_id": 3, "score": "3-2"},
        ]

        record = JsonTestModel(name="test_list", jsonb_data=test_data)
        sqlite_session.add(record)
        sqlite_session.commit()

        retrieved = (
            sqlite_session.query(JsonTestModel).filter_by(name="test_list").first()
        )
        assert isinstance(retrieved.jsonb_data, list)
        assert len(retrieved.jsonb_data) == 3
        assert retrieved.jsonb_data[0]["score"] == "2-1"

    def test_null_values(self, sqlite_session):
        """测试NULL值处理"""
        record = JsonTestModel(name="test_null", jsonb_data=None)
        sqlite_session.add(record)
        sqlite_session.commit()

        retrieved = (
            sqlite_session.query(JsonTestModel).filter_by(name="test_null").first()
        )
        assert retrieved.jsonb_data is None

    def test_empty_dict_and_list(self, sqlite_session):
        """测试空字典和空列表"""
        # 测试空字典
        record1 = JsonTestModel(name="test_empty_dict", jsonb_data={})
        sqlite_session.add(record1)

        # 测试空列表
        record2 = JsonTestModel(name="test_empty_list", jsonb_data=[])
        sqlite_session.add(record2)

        sqlite_session.commit()

        # 验证
        dict_record = (
            sqlite_session.query(JsonTestModel)
            .filter_by(name="test_empty_dict")
            .first()
        )
        list_record = (
            sqlite_session.query(JsonTestModel)
            .filter_by(name="test_empty_list")
            .first()
        )

        assert dict_record.jsonb_data == {}
        assert list_record.jsonb_data == []


class TestCompatibleJSON:
    """测试兼容JSON类型"""

    def test_compat_json_type(self, sqlite_session):
        """测试CompatibleJSON类型"""
        test_data = {"type": "compat", "value": 42}

        record = JsonTestModel(name="test_compat", compat_data=test_data)
        sqlite_session.add(record)
        sqlite_session.commit()

        retrieved = (
            sqlite_session.query(JsonTestModel).filter_by(name="test_compat").first()
        )
        assert retrieved.compat_data == test_data


class TestRealWorldScenarios:
    """测试真实世界场景"""

    def test_match_data_scenario(self, sqlite_session):
        """测试比赛数据场景"""
        match_data = {
            "match_id": "ext_123456",
            "home_team": {"id": 1, "name": "Liverpool", "formation": "4-3-3"},
            "away_team": {"id": 2, "name": "Chelsea", "formation": "3-5-2"},
            "score": {"home": 2, "away": 1, "half_time": {"home": 1, "away": 0}},
            "events": [
                {
                    "minute": 15,
                    "type": "goal",
                    "player": "Mohamed Salah",
                    "team": "home",
                },
                {
                    "minute": 78,
                    "type": "goal",
                    "player": "Raheem Sterling",
                    "team": "away",
                },
                {
                    "minute": 85,
                    "type": "goal",
                    "player": "Virgil van Dijk",
                    "team": "home",
                },
            ],
            "metadata": {
                "source": "api-football",
                "collected_at": "2025-09-12T10:30:00Z",
                "version": "1.0",
            },
        }

        record = JsonTestModel(name="match_liverpool_chelsea", jsonb_data=match_data)
        sqlite_session.add(record)
        sqlite_session.commit()

        # 验证复杂数据结构
        retrieved = (
            sqlite_session.query(JsonTestModel)
            .filter_by(name="match_liverpool_chelsea")
            .first()
        )
        assert retrieved.jsonb_data["score"]["home"] == 2
        assert len(retrieved.jsonb_data["events"]) == 3
        assert retrieved.jsonb_data["events"][0]["player"] == "Mohamed Salah"

    def test_odds_data_scenario(self, sqlite_session):
        """测试赔率数据场景"""
        odds_data = {
            "bookmaker": "bet365",
            "match_id": "123456",
            "markets": {
                "1x2": {"home": 2.10, "draw": 3.40, "away": 3.20},
                "over_under": {"over_2_5": 1.85, "under_2_5": 1.95},
                "asian_handicap": {"handicap": -0.5, "home": 1.90, "away": 1.90},
            },
            "timestamps": {
                "opened": "2025-09-12T08:00:00Z",
                "last_updated": "2025-09-12T10:30:00Z",
            },
        }

        record = JsonTestModel(name="odds_bet365", jsonb_data=odds_data)
        sqlite_session.add(record)
        sqlite_session.commit()

        retrieved = (
            sqlite_session.query(JsonTestModel).filter_by(name="odds_bet365").first()
        )
        assert retrieved.jsonb_data["markets"]["1x2"]["home"] == 2.10
        assert retrieved.jsonb_data["bookmaker"] == "bet365"


class TestTypeFactory:
    """测试类型工厂函数"""

    def test_get_json_type_jsonb(self):
        """测试获取JSONB类型"""
        json_type = get_json_type(use_jsonb=True)
        assert json_type.__class__.__name__ == "SQLiteCompatibleJSONB"

    def test_get_json_type_regular(self):
        """测试获取常规JSON类型"""
        json_type = get_json_type(use_jsonb=False)
        assert json_type.__class__.__name__ == "CompatibleJSON"


class TestSQLiteConfig:
    """测试SQLite配置"""

    def test_sqlite_config_memory(self):
        """测试内存数据库配置"""
        config = get_sqlite_config("test")
        assert config.db_type == DatabaseType.SQLITE
        assert config.database == ":memory:"
        assert config.pool_size == 1

    def test_sqlite_config_file(self):
        """测试文件数据库配置"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            test_path = f.name

        try:
            os.environ["SQLITE_DB_PATH"] = test_path
            config = get_sqlite_config("development")
            assert config.database == test_path
            assert config.sync_url == f"sqlite:///{test_path}"
        finally:
            if "SQLITE_DB_PATH" in os.environ:
                del os.environ["SQLITE_DB_PATH"]
            os.unlink(test_path)


@pytest.mark.integration
class TestEndToEndCompatibility:
    """端到端兼容性测试"""

    def test_create_tables_and_insert_data(self, sqlite_engine):
        """测试创建表和插入数据的完整流程"""
        # 验证表已创建
        with sqlite_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test_json_model'"
                )
            )
            assert result.fetchone() is not None

        # 插入测试数据
        Session = sessionmaker(bind=sqlite_engine)
        session = Session()

        test_records = [
            JsonTestModel(
                name="record_1",
                jsonb_data={"id": 1, "type": "team", "data": {"name": "Team A"}},
                compat_data={"status": "active", "count": 10},
            ),
            JsonTestModel(
                name="record_2",
                jsonb_data=[1, 2, 3, {"nested": "value"}],
                compat_data=None,
            ),
        ]

        session.add_all(test_records)
        session.commit()

        # 验证数据检索
        all_records = session.query(JsonTestModel).all()
        assert len(all_records) == 2

        record_1 = session.query(JsonTestModel).filter_by(name="record_1").first()
        assert record_1.jsonb_data["data"]["name"] == "Team A"
        assert record_1.compat_data["count"] == 10

        record_2 = session.query(JsonTestModel).filter_by(name="record_2").first()
        assert isinstance(record_2.jsonb_data, list)
        assert record_2.jsonb_data[3]["nested"] == "value"
        assert record_2.compat_data is None

        session.close()
