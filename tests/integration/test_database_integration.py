import os
"""数据库集成测试"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseIntegration:
    """测试数据库集成"""

    @pytest.fixture(scope="class")
    def db_url(self):
        """获取数据库URL"""
        return "sqlite://"

    @pytest.fixture(scope="class")
    def engine(self, db_url):
        """创建数据库引擎"""
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    @pytest.fixture(scope="class")
    def session(self, engine):
        """创建数据库会话"""
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture(scope="class", autouse=True)
    def prepare_schema(self, engine):
        """为测试准备基础表结构"""
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        home_team TEXT,
                        away_team TEXT
                    )
                    """
                )
            )

    def test_database_connection(self, engine):
        """测试数据库连接"""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_table_exists(self, session):
        """测试核心表是否存在"""
        # 检查matches表是否存在
        result = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name = os.getenv("TEST_DATABASE_INTEGRATION_NAME_64")")
        )
        assert result.scalar() == "matches"

    def test_can_insert_and_query(self, session):
        """测试插入和查询数据"""
        # 创建一个临时测试表
        session.execute(text("DROP TABLE IF EXISTS test_integration"))
        session.execute(text("""
            CREATE TABLE test_integration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # 插入数据
        session.execute(text("INSERT INTO test_integration (name) VALUES ('test1');"))
        session.commit()

        # 查询数据
        result = session.execute(text("SELECT name FROM test_integration WHERE name = 'test1'"))
        assert result.scalar() == "test1"
