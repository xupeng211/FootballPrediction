"""内存数据库集成测试"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime


@pytest.mark.integration
class TestMemoryDatabase:
    """测试内存数据库操作"""

    @pytest.fixture(scope="class")
    def memory_db(self):
        """创建内存数据库"""
        conn = sqlite3.connect(":memory:")
        yield conn
        conn.close()

    @pytest.fixture(scope="class")
    def temp_db(self):
        """创建临时数据库"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_file.close()
        yield temp_file.name
        os.unlink(temp_file.name)

    def test_memory_db_connection(self, memory_db):
        """测试内存数据库连接"""
        cursor = memory_db.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1

    def test_create_tables(self, memory_db):
        """测试创建表"""
        cursor = memory_db.cursor()

        # 创建matches表
        cursor.execute("DROP TABLE IF EXISTS matches")
        cursor.execute("""
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                match_date DATETIME,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建predictions表
        cursor.execute("""
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                home_win_prob REAL,
                draw_prob REAL,
                away_win_prob REAL,
                confidence REAL,
                model_version TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches (id)
            )
        """)

        # 创建alerts表
        cursor.execute("""
            CREATE TABLE alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                level TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME
            )
        """)

        memory_db.commit()

        # 验证表已创建
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "matches" in tables
        assert "predictions" in tables
        assert "alerts" in tables

    def test_insert_match_data(self, memory_db):
        """测试插入比赛数据"""
        cursor = memory_db.cursor()
        cursor.execute("DROP TABLE IF EXISTS matches")
        cursor.execute("""
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                match_date DATETIME,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        memory_db.commit()

        # 插入测试数据
        cursor.execute("""
            INSERT INTO matches (home_team, away_team, match_date, status)
            VALUES (?, ?, ?, ?)
        """, ("Team A", "Team B", datetime.now(), "scheduled"))

        cursor.execute("""
            INSERT INTO matches (home_team, away_team, match_date, status)
            VALUES (?, ?, ?, ?)
        """, ("Team C", "Team D", datetime.now(), "completed"))

        memory_db.commit()

        # 验证数据
        cursor.execute("SELECT COUNT(*) FROM matches")
        count = cursor.fetchone()[0]
        assert count == 2

        # 验证具体数据
        cursor.execute("SELECT home_team, away_team FROM matches WHERE status = os.getenv("TEST_MEMORY_DATABASE_STATUS_126")")
        match = cursor.fetchone()
        assert match[0] == "Team A"
        assert match[1] == "Team B"

    def test_insert_prediction_data(self, memory_db):
        """测试插入预测数据"""
        cursor = memory_db.cursor()

        # 创建表
        cursor.execute("DROP TABLE IF EXISTS matches")
        cursor.execute("""
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL
            )
        """)

        cursor.execute("DROP TABLE IF EXISTS predictions")
        cursor.execute("""
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                home_win_prob REAL,
                draw_prob REAL,
                away_win_prob REAL,
                confidence REAL,
                model_version TEXT
            )
        """)
        memory_db.commit()

        # 插入比赛
        cursor.execute("INSERT INTO matches (home_team, away_team) VALUES (?, ?)",
                      ("Team X", "Team Y"))
        match_id = cursor.lastrowid

        # 插入预测
        cursor.execute("""
            INSERT INTO predictions (match_id, home_win_prob, draw_prob, away_win_prob, confidence, model_version)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (match_id, 0.6, 0.25, 0.15, 0.85, "v1.2.3"))
        memory_db.commit()

        # 验证预测数据
        cursor.execute("""
            SELECT home_win_prob, model_version
            FROM predictions
            WHERE match_id = ?
        """, (match_id,))
        pred = cursor.fetchone()
        assert pred[0] == 0.6
        assert pred[1] == "v1.2.3"

    def test_alert_operations(self, memory_db):
        """测试告警操作"""
        cursor = memory_db.cursor()

        cursor.execute("DROP TABLE IF EXISTS alerts")

        cursor.execute("""
            CREATE TABLE alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                level TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME
            )
        """)
        memory_db.commit()

        # 插入告警
        cursor.execute("""
            INSERT INTO alerts (title, message, level, source)
            VALUES (?, ?, ?, ?)
        """, ("Test Alert", "This is a test", "warning", "test_source"))

        cursor.execute("""
            INSERT INTO alerts (title, message, level, source)
            VALUES (?, ?, ?, ?)
        """, ("Critical Alert", "This is critical", "critical", "monitor"))

        memory_db.commit()

        # 查询活跃告警
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = os.getenv("TEST_MEMORY_DATABASE_STATUS_215")")
        active_count = cursor.fetchone()[0]
        assert active_count == 2

        # 解决一个告警
        cursor.execute("""
            UPDATE alerts
            SET status = os.getenv("TEST_MEMORY_DATABASE_STATUS_220"), resolved_at = ?
            WHERE title = ?
        """, (datetime.now(), "Test Alert"))
        memory_db.commit()

        # 验证告警已解决
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = os.getenv("TEST_MEMORY_DATABASE_STATUS_215")")
        active_count = cursor.fetchone()[0]
        assert active_count == 1

        cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = os.getenv("TEST_MEMORY_DATABASE_STATUS_220")")
        resolved_count = cursor.fetchone()[0]
        assert resolved_count == 1

    def test_transaction_rollback(self, memory_db):
        """测试事务回滚"""
        cursor = memory_db.cursor()

        cursor.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        memory_db.commit()

        # 开始事务
        cursor.execute("BEGIN")

        try:
            # 插入数据
            cursor.execute("INSERT INTO test_table (id, value) VALUES (1, 'test')")
            # 故意触发错误
            cursor.execute("INSERT INTO test_table (id, value) VALUES (1, 'duplicate')")
        except sqlite3.IntegrityError:
            # 回滚事务
            cursor.execute("ROLLBACK")

        # 验证数据未被插入
        cursor.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        assert count == 0
