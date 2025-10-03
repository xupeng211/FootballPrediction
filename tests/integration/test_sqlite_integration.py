"""SQLite集成测试"""

import pytest
import tempfile
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


@pytest.mark.integration
@pytest.mark.asyncio
class TestSQLiteIntegration:
    """使用SQLite进行集成测试"""

    @pytest.fixture(scope="class")
    def temp_db(self):
        """创建临时SQLite数据库"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_file.close()
        yield temp_file.name
        os.unlink(temp_file.name)

    @pytest.fixture(scope="class")
    def engine(self, temp_db):
        """创建数据库引擎"""
        return create_engine(f"sqlite:///{temp_db}")

    @pytest.fixture(scope="class")
    def session(self, engine):
        """创建数据库会话"""
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def test_sqlite_connection(self, engine):
        """测试SQLite连接"""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_create_tables(self, session):
        """测试创建表"""
        # 创建测试表
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                match_date DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """))

        session.execute(text("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                home_win_prob REAL,
                draw_prob REAL,
                away_win_prob REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches (id)
            );
        """))
        session.commit()

        # 验证表已创建
        result = session.execute(text("""
            SELECT name FROM sqlite_master WHERE type='table' AND name IN ('matches', 'predictions');
        """)).scalars().all()
        assert len(result) == 2

    def test_insert_and_query_data(self, session):
        """测试插入和查询数据"""
        # 插入测试数据
        session.execute(text("""
            INSERT INTO matches (home_team, away_team, match_date)
            VALUES ('Team A', 'Team B', datetime('now'));
        """))
        session.execute(text("""
            INSERT INTO matches (home_team, away_team, match_date)
            VALUES ('Team C', 'Team D', datetime('now', '+1 day'));
        """))
        session.commit()

        # 查询数据
        result = session.execute(text("SELECT COUNT(*) FROM matches")).scalar()
        assert result == 2

        # 插入预测数据
        session.execute(text("""
            INSERT INTO predictions (match_id, home_win_prob, draw_prob, away_win_prob)
            VALUES (1, 0.5, 0.3, 0.2);
        """))
        session.commit()

        # 查询预测
        result = session.execute(text("SELECT COUNT(*) FROM predictions")).scalar()
        assert result == 1

    async def test_api_with_sqlite(self, temp_db):
        """测试API与SQLite集成"""
        # 创建一个简单的FastAPI应用用于测试
        from fastapi import FastAPI
        import sqlite3

        app = FastAPI(title = os.getenv("TEST_SQLITE_INTEGRATION_TITLE_110"))

        @app.get("/health")
        async def health():
            return {"status": "healthy", "database": "sqlite"}

        @app.get("/matches/count")
        async def count_matches():
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM matches")
            count = cursor.fetchone()[0]
            conn.close()
            return {"count": count}

        # 使用TestClient测试API
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # 测试健康检查
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

        # 测试数据查询
        response = client.get("/matches/count")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data

    def test_alert_manager_integration(self):
        """测试告警管理器集成"""
        from src.monitoring.alert_manager import AlertManager, AlertLevel

        manager = AlertManager()

        # 创建一些告警
        alert1 = manager.fire_alert(
            title = os.getenv("TEST_SQLITE_INTEGRATION_TITLE_148"),
            message = os.getenv("TEST_SQLITE_INTEGRATION_MESSAGE_149"),
            level=AlertLevel.INFO,
            source = os.getenv("TEST_SQLITE_INTEGRATION_SOURCE_150")
        )

        alert2 = manager.fire_alert(
            title = os.getenv("TEST_SQLITE_INTEGRATION_TITLE_151"),
            message = os.getenv("TEST_SQLITE_INTEGRATION_MESSAGE_152"),
            level=AlertLevel.WARNING,
            source = os.getenv("TEST_SQLITE_INTEGRATION_SOURCE_150")
        )

        # 验证告警
        assert alert1 is not None
        assert alert2 is not None
        assert len(manager.get_active_alerts()) >= 2

        # 获取摘要
        summary = manager.get_alert_summary()
        assert summary["total_alerts"] >= 2
        assert summary["by_level"]["info"] >= 1
        assert summary["by_level"]["warning"] >= 1