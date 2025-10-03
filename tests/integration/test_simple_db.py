"""简单数据库集成测试"""

import pytest
import sqlite3
import tempfile
import os


@pytest.mark.integration
class TestSimpleDB:
    """测试简单数据库操作"""

    @pytest.fixture
    def fresh_db(self):
        """每次测试都创建新的数据库"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_file.close()
        conn = sqlite3.connect(temp_file.name)
        yield conn
        conn.close()
        os.unlink(temp_file.name)

    def test_create_and_query_matches(self, fresh_db):
        """测试创建和查询比赛"""
        cursor = fresh_db.cursor()

        # 创建表
        cursor.execute("""
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY,
                home_team TEXT,
                away_team TEXT
            )
        """)

        # 插入数据
        cursor.execute("INSERT INTO matches (id, home_team, away_team) VALUES (1, 'Team A', 'Team B')")
        fresh_db.commit()

        # 查询数据
        cursor.execute("SELECT home_team, away_team FROM matches WHERE id = 1")
        result = cursor.fetchone()
        assert result == ('Team A', 'Team B')

    def test_predictions_workflow(self, fresh_db):
        """测试预测工作流"""
        cursor = fresh_db.cursor()

        # 创建表
        cursor.execute("""
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY,
                match_id INTEGER,
                prediction REAL,
                confidence REAL
            )
        """)

        # 插入预测
        cursor.execute("""
            INSERT INTO predictions (id, match_id, prediction, confidence)
            VALUES (1, 100, 0.75, 0.90)
        """)
        fresh_db.commit()

        # 查询并验证
        cursor.execute("SELECT prediction, confidence FROM predictions WHERE id = 1")
        result = cursor.fetchone()
        assert result[0] == 0.75
        assert result[1] == 0.90

    def test_alert_system(self, fresh_db):
        """测试告警系统"""
        cursor = fresh_db.cursor()

        # 创建告警表
        cursor.execute("""
            CREATE TABLE alerts (
                id INTEGER PRIMARY KEY,
                level TEXT,
                message TEXT,
                active INTEGER DEFAULT 1
            )
        """)

        # 插入告警
        cursor.execute("""
            INSERT INTO alerts (id, level, message)
            VALUES (1, 'warning', 'Test warning')
        """)
        cursor.execute("""
            INSERT INTO alerts (id, level, message)
            VALUES (2, 'critical', 'Test critical')
        """)
        fresh_db.commit()

        # 查询活跃告警
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE active = 1")
        count = cursor.fetchone()[0]
        assert count == 2

        # 解决一个告警
        cursor.execute("UPDATE alerts SET active = 0 WHERE id = 1")
        fresh_db.commit()

        # 验证
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE active = 1")
        count = cursor.fetchone()[0]
        assert count == 1

    def test_data_integrity(self, fresh_db):
        """测试数据完整性"""
        cursor = fresh_db.cursor()

        # 创建带约束的表
        cursor.execute("""
            CREATE TABLE teams (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # 插入团队
        cursor.execute("INSERT INTO teams (id, name) VALUES (1, 'Team A')")
        cursor.execute("INSERT INTO teams (id, name) VALUES (2, 'Team B')")
        fresh_db.commit()

        # 尝试插入重复名称（应该失败）
        try:
            cursor.execute("INSERT INTO teams (id, name) VALUES (3, 'Team A')")
            fresh_db.commit()
            assert False, "应该抛出IntegrityError"
        except sqlite3.IntegrityError:
            pass  # 预期的错误

    def test_aggregation_queries(self, fresh_db):
        """测试聚合查询"""
        cursor = fresh_db.cursor()

        # 创建测试数据
        cursor.execute("""
            CREATE TABLE test_data (
                category TEXT,
                value INTEGER
            )
        """)

        # 插入数据
        cursor.execute("INSERT INTO test_data VALUES ('A', 10)")
        cursor.execute("INSERT INTO test_data VALUES ('A', 20)")
        cursor.execute("INSERT INTO test_data VALUES ('B', 30)")
        fresh_db.commit()

        # 测试聚合
        cursor.execute("SELECT COUNT(*), AVG(value) FROM test_data WHERE category = 'A'")
        result = cursor.fetchone()
        assert result[0] == 2  # 计数
        assert result[1] == 15.0  # 平均值

        cursor.execute("SELECT SUM(value) FROM test_data")
        total = cursor.fetchone()[0]
        assert total == 60