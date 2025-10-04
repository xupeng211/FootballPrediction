"""数据库模型测试模板"""

import pytest
from datetime import datetime

from tests.helpers import create_sqlite_memory_engine, create_sqlite_sessionmaker


class TestDatabaseModels:
    """数据库模型测试 - 使用内存 SQLite"""

    @pytest.fixture
    async def db_session(self):
        """内存数据库会话"""
        engine = create_sqlite_memory_engine()
        sessionmaker = create_sqlite_sessionmaker(engine)
        async with sessionmaker() as session:
            yield session
        engine.dispose()

    @pytest.fixture
    async def setup_tables(self, db_session):
        """创建测试表"""
        # 创建模型表（这里用示例表结构）
        await db_session.execute(text("""
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                match_date DATETIME,
                league_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        await db_session.execute(text("""
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                predicted_home_score INTEGER,
                predicted_away_score INTEGER,
                confidence REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches (id)
            )
        """))

        await db_session.commit()

    @pytest.mark.asyncio
    async def test_create_match(self, db_session, setup_tables):
        """测试创建比赛记录"""
        # 插入比赛
        result = await db_session.execute(text("""
            INSERT INTO matches (home_team, away_team, match_date, league_id)
            VALUES (:home, :away, :date, :league)
        """), {
            "home": "Team A",
            "away": "Team B",
            "date": datetime.now(),
            "league": 1
        })

        match_id = result.lastrowid
        await db_session.commit()

        # 查询验证
        result = await db_session.execute(
            text("SELECT * FROM matches WHERE id = :id"),
            {"id": match_id}
        )
        match = result.fetchone()

        assert match is not None
        assert match["home_team"] == "Team A"
        assert match["away_team"] == "Team B"

    @pytest.mark.asyncio
    async def test_create_prediction(self, db_session, setup_tables):
        """测试创建预测记录"""
        # 先创建比赛
        await db_session.execute(text("""
            INSERT INTO matches (home_team, away_team, match_date)
            VALUES (:home, :away, :date)
        """), {
            "home": "Team A",
            "away": "Team B",
            "date": datetime.now()
        })
        match_id = (await db_session.execute(text("SELECT last_insert_rowid()"))).scalar()

        # 创建预测
        result = await db_session.execute(text("""
            INSERT INTO predictions (match_id, predicted_home_score, predicted_away_score, confidence)
            VALUES (:match_id, :home_score, :away_score, :confidence)
        """), {
            "match_id": match_id,
            "home_score": 2,
            "away_score": 1,
            "confidence": 0.75
        })

        prediction_id = result.lastrowid
        await db_session.commit()

        # 查询验证
        result = await db_session.execute(
            text("""
                SELECT p.*, m.home_team, m.away_team
                FROM predictions p
                JOIN matches m ON p.match_id = m.id
                WHERE p.id = :id
            """),
            {"id": prediction_id}
        )
        prediction = result.fetchone()

        assert prediction is not None
        assert prediction["predicted_home_score"] == 2
        assert prediction["predicted_away_score"] == 1
        assert prediction["confidence"] == 0.75
        assert prediction["home_team"] == "Team A"
        assert prediction["away_team"] == "Team B"

    @pytest.mark.asyncio
    async def test_foreign_key_constraint(self, db_session, setup_tables):
        """测试外键约束"""
        # 尝试插入不存在的 match_id 的预测
        with pytest.raises(Exception):  # SQLite 会抛出 IntegrityError
            await db_session.execute(text("""
                INSERT INTO predictions (match_id, predicted_home_score, predicted_away_score)
                VALUES (999, 1, 1)
            """))
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_update_prediction_status(self, db_session, setup_tables):
        """测试更新预测状态"""
        # 创建测试数据
        await db_session.execute(text("""
            INSERT INTO matches (home_team, away_team, match_date)
            VALUES (:home, :away, :date)
        """), {
            "home": "Team A",
            "away": "Team B",
            "date": datetime.now()
        })
        match_id = (await db_session.execute(text("SELECT last_insert_rowid()"))).scalar()

        await db_session.execute(text("""
            INSERT INTO predictions (match_id, predicted_home_score, predicted_away_score)
            VALUES (:match_id, :home_score, :away_score)
        """), {
            "match_id": match_id,
            "home_score": 2,
            "away_score": 1
        })
        prediction_id = (await db_session.execute(text("SELECT last_insert_rowid()"))).scalar()
        await db_session.commit()

        # 更新状态
        await db_session.execute(text("""
            UPDATE predictions
            SET status = 'completed',
                actual_home_score = 2,
                actual_away_score = 1
            WHERE id = :id
        """), {"id": prediction_id})
        await db_session.commit()

        # 验证更新
        result = await db_session.execute(
            text("SELECT * FROM predictions WHERE id = :id"),
            {"id": prediction_id}
        )
        prediction = result.fetchone()

        assert prediction["status"] == "completed"

    @pytest.mark.asyncio
    async def test_query_with_join(self, db_session, setup_tables):
        """测试复杂查询"""
        # 插入多条测试数据
        teams = [("Team A", "Team B"), ("Team C", "Team D"), ("Team E", "Team F")]
        for home, away in teams:
            await db_session.execute(text("""
                INSERT INTO matches (home_team, away_team, match_date)
                VALUES (:home, :away, :date)
            """), {
                "home": home,
                "away": away,
                "date": datetime.now()
            })

        await db_session.commit()

        # 执行 JOIN 查询
        result = await db_session.execute(text("""
            SELECT m.id, m.home_team, m.away_team, p.predicted_home_score
            FROM matches m
            LEFT JOIN predictions p ON m.id = p.match_id
            WHERE m.home_team LIKE :pattern
            ORDER BY m.id
        """), {"pattern": "Team%"})

        matches = result.fetchall()
        assert len(matches) == 3
        assert matches[0]["home_team"] == "Team A"
        assert matches[0]["predicted_home_score"] is None  # 无预测