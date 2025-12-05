"""
数据库集成测试
Database Integration Tests

测试新的异步数据库接口与实际PostgreSQL数据库的集成
使用Docker Compose环境运行
"""

import pytest
import asyncio
import os
from typing import Dict, Any, Optional
from sqlalchemy import text, create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from unittest.mock import patch

from src.database.async_manager import (
    initialize_database,
    get_database_manager,
    get_db_session,
    fetch_all,
    fetch_one,
    execute,
    AsyncDatabaseManager
)


class TestDatabaseIntegration:
    """数据库集成测试类"""

    @pytest.fixture(scope="class", autouse=True)
    async def setup_database(self):
        """设置集成测试数据库环境"""
        # 检查环境变量
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            pytest.skip("DATABASE_URL 环境变量未设置，跳过集成测试")

        # 如果是同步URL，转换为异步URL
        if "postgresql://" in db_url and "+asyncpg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

        # 初始化数据库
        initialize_database(db_url)

        # 创建测试表
        await self._create_test_tables()

        yield db_url

        # 清理
        await self._cleanup_test_tables()

    async def _create_test_tables(self):
        """创建测试表"""
        async with get_db_session() as session:
            # 创建测试用户表
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS integration_test_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """))

            # 创建测试比赛表
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS integration_test_matches (
                    id SERIAL PRIMARY KEY,
                    home_team VARCHAR(100) NOT NULL,
                    away_team VARCHAR(100) NOT NULL,
                    match_date TIMESTAMP,
                    competition VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # 创建测试预测表
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS integration_test_predictions (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER REFERENCES integration_test_matches(id),
                    predicted_home_score INTEGER,
                    predicted_away_score INTEGER,
                    confidence DECIMAL(5,4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            await session.commit()

    async def _cleanup_test_tables(self):
        """清理测试表"""
        try:
            async with get_db_session() as session:
                # 按依赖关系删除表
                await session.execute(text("DROP TABLE IF EXISTS integration_test_predictions CASCADE"))
                await session.execute(text("DROP TABLE IF EXISTS integration_test_matches CASCADE"))
                await session.execute(text("DROP TABLE IF EXISTS integration_test_users CASCADE"))
                await session.commit()
        except Exception as e:
            print(f"清理测试表时出错: {e}")

    async def test_database_connection(self, setup_database):
        """测试数据库连接"""
        manager = get_database_manager()

        # 检查管理器是否已初始化
        assert manager.is_initialized, "数据库管理器应该已初始化"

        # 检查连接健康状态
        status = await manager.check_connection()
        assert status["status"] == "healthy", f"数据库连接应该健康: {status}"
        assert status["response_time_ms"] is not None, "应该有响应时间"

    async def test_session_context_manager(self, setup_database):
        """测试会话上下文管理器"""
        async with get_db_session() as session:
            assert isinstance(session, AsyncSession), "应该返回AsyncSession实例"
            assert session.is_active, "会话应该是活跃状态"

            # 执行简单查询
            result = await session.execute(text("SELECT 1 as test_value"))
            row = result.fetchone()
            assert row["test_value"] == 1, "基本查询应该工作"

        # 会话应该自动关闭
        assert not session.is_active, "会话应该已关闭"

    async def test_crud_operations(self, setup_database):
        """测试CRUD操作"""
        # 创建用户
        await execute(
            text("""
                INSERT INTO integration_test_users (username, email, is_active)
                VALUES (:username, :email, :is_active)
                RETURNING id, username, email
            """),
            {
                "username": "testuser1",
                "email": "testuser1@example.com",
                "is_active": True
            }
        )

        # 读取用户
        user = await fetch_one(
            text("SELECT * FROM integration_test_users WHERE username = :username"),
            {"username": "testuser1"}
        )

        assert user is not None, "用户应该被创建"
        assert user["username"] == "testuser1", "用户名应该正确"
        assert user["email"] == "testuser1@example.com", "邮箱应该正确"
        assert user["is_active"] is True, "状态应该正确"

        # 更新用户
        await execute(
            text("UPDATE integration_test_users SET email = :new_email WHERE username = :username"),
            {"username": "testuser1", "new_email": "updated@example.com"}
        )

        # 验证更新
        updated_user = await fetch_one(
            text("SELECT * FROM integration_test_users WHERE username = :username"),
            {"username": "testuser1"}
        )
        assert updated_user["email"] == "updated@example.com", "邮箱应该已更新"

        # 删除用户
        await execute(
            text("DELETE FROM integration_test_users WHERE username = :username"),
            {"username": "testuser1"}
        )

        # 验证删除
        deleted_user = await fetch_one(
            text("SELECT * FROM integration_test_users WHERE username = :username"),
            {"username": "testuser1"}
        )
        assert deleted_user is None, "用户应该被删除"

    async def test_batch_operations(self, setup_database):
        """测试批量操作"""
        # 批量插入用户
        users_data = [
            {"username": f"user{i}", "email": f"user{i}@example.com", "is_active": i % 2 == 0}
            for i in range(1, 6)
        ]

        await execute(
            text("""
                INSERT INTO integration_test_users (username, email, is_active)
                VALUES (:username, :email, :is_active)
            """),
            users_data
        )

        # 验证批量插入
        all_users = await fetch_all(
            text("SELECT * FROM integration_test_users WHERE username LIKE 'user%' ORDER BY username")
        )

        assert len(all_users) == 5, "应该插入5个用户"
        assert all_users[0]["username"] == "user1", "用户应该按顺序插入"

        # 验证数据完整性
        active_users = await fetch_all(
            text("SELECT COUNT(*) as count FROM integration_test_users WHERE is_active = TRUE AND username LIKE 'user%'")
        )
        assert active_users[0]["count"] == 2, "应该有2个活跃用户"

    async def test_transaction_isolation(self, setup_database):
        """测试事务隔离"""
        # 创建测试匹配
        await execute(
            text("""
                INSERT INTO integration_test_matches (home_team, away_team, competition)
                VALUES ('Team A', 'Team B', 'Premier League')
                RETURNING id
            """)
        )

        # 获取匹配ID
        match = await fetch_one(
            text("SELECT id FROM integration_test_matches WHERE home_team = 'Team A'")
        )
        match_id = match["id"]

        # 测试成功事务
        async with get_db_session() as session:
            try:
                await session.execute(
                    text("""
                        INSERT INTO integration_test_predictions
                        (match_id, predicted_home_score, predicted_away_score, confidence)
                        VALUES (:match_id, :home_score, :away_score, :confidence)
                    """),
                    {
                        "match_id": match_id,
                        "home_score": 2,
                        "away_score": 1,
                        "confidence": 0.85
                    }
                )
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise

        # 验证事务提交
        prediction = await fetch_one(
            text("SELECT * FROM integration_test_predictions WHERE match_id = :match_id"),
            {"match_id": match_id}
        )
        assert prediction is not None, "预测应该被提交"
        assert prediction["predicted_home_score"] == 2, "预测应该正确"

        # 测试回滚事务
        async with get_db_session() as session:
            try:
                await session.execute(
                    text("""
                        INSERT INTO integration_test_predictions
                        (match_id, predicted_home_score, predicted_away_score, confidence)
                        VALUES (:match_id, :home_score, :away_score, :confidence)
                    """),
                    {
                        "match_id": match_id,
                        "home_score": 1,
                        "away_score": 2,
                        "confidence": 0.75
                    }
                )

                # 故意引发错误
                raise Exception("测试事务回滚")
            except Exception:
                await session.rollback()
                # 期望的回滚

        # 验证回滚
        predictions = await fetch_all(
            text("SELECT * FROM integration_test_predictions WHERE match_id = :match_id AND predicted_home_score = 1"),
            {"match_id": match_id}
        )
        assert len(predictions) == 0, "回滚的预测不应该存在"

    async def test_complex_join_query(self, setup_database):
        """测试复杂连接查询"""
        # 插入测试数据
        # 插入匹配
        await execute(
            text("""
                INSERT INTO integration_test_matches (home_team, away_team, competition) VALUES
                ('Manchester United', 'Liverpool', 'Premier League'),
                ('Chelsea', 'Arsenal', 'Premier League'),
                ('Barcelona', 'Real Madrid', 'La Liga')
            """)
        )

        # 插入预测
        await execute(
            text("""
                INSERT INTO integration_test_predictions (match_id, predicted_home_score, predicted_away_score, confidence)
                SELECT id, 2, 1, 0.85 FROM integration_test_matches WHERE home_team = 'Manchester United'
                UNION ALL
                SELECT id, 1, 1, 0.60 FROM integration_test_matches WHERE home_team = 'Chelsea'
                UNION ALL
                SELECT id, 3, 2, 0.75 FROM integration_test_matches WHERE home_team = 'Barcelona'
            """)
        )

        # 复杂连接查询
        results = await fetch_all(text("""
            SELECT
                m.home_team,
                m.away_team,
                m.competition,
                p.predicted_home_score,
                p.predicted_away_score,
                p.confidence,
                p.created_at as prediction_time
            FROM integration_test_matches m
            JOIN integration_test_predictions p ON m.id = p.match_id
            ORDER BY p.confidence DESC
        """))

        assert len(results) == 3, "应该有3个预测结果"
        assert results[0]["confidence"] == 0.85, "最高置信度应该是0.85"
        assert results[0]["home_team"] == "Manchester United", "最高置信度的预测应该是曼联"

    async def test_performance_benchmarks(self, setup_database):
        """测试性能基准"""
        import time

        # 测试插入性能
        start_time = time.time()

        batch_data = [
            {"username": f"perf_user_{i}", "email": f"perf_user_{i}@example.com", "is_active": True}
            for i in range(100)
        ]

        await execute(
            text("INSERT INTO integration_test_users (username, email, is_active) VALUES (:username, :email, :is_active)"),
            batch_data
        )

        insert_time = time.time() - start_time

        # 测试查询性能
        start_time = time.time()

        results = await fetch_all(text("""
            SELECT * FROM integration_test_users
            WHERE username LIKE 'perf_user_%'
            ORDER BY id
        """))

        query_time = time.time() - start_time

        # 性能断言
        assert len(results) == 100, "应该插入100条记录"
        assert insert_time < 5.0, f"批量插入应该在5秒内完成，实际耗时: {insert_time:.2f}秒"
        assert query_time < 1.0, f"查询应该在1秒内完成，实际耗时: {query_time:.2f}秒"

    async def test_connection_pool(self, setup_database):
        """测试连接池"""
        manager = get_database_manager()
        engine = manager.engine

        # 获取连接池状态（如果支持）
        if hasattr(engine.pool, 'size'):
            pool_size = engine.pool.size()
            assert pool_size > 0, "连接池应该有可用连接"

    async def test_database_schema_validation(self, setup_database):
        """测试数据库模式验证"""
        async with get_db_session() as session:
            # 检查表是否存在
            tables = await fetch_all(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE 'integration_test_%'
                ORDER BY table_name
            """))

            expected_tables = {
                'integration_test_matches',
                'integration_test_predictions',
                'integration_test_users'
            }

            found_tables = {table['table_name'] for table in tables}
            assert expected_tables.issubset(found_tables), f"应该包含所有测试表，找到: {found_tables}"

            # 检查表结构
            users_columns = await fetch_all(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'integration_test_users'
                ORDER BY ordinal_position
            """))

            expected_columns = {'id', 'username', 'email', 'created_at', 'is_active'}
            found_columns = {col['column_name'] for col in users_columns}
            assert expected_columns.issubset(found_columns), f"用户表应该包含所有期望的列，找到: {found_columns}"


class TestRealWorldScenarios:
    """真实世界场景测试"""

    async def test_football_prediction_workflow(self, setup_database):
        """测试足球预测工作流"""
        # 1. 创建比赛数据
        await execute(
            text("""
                INSERT INTO integration_test_matches (home_team, away_team, competition, match_date)
                VALUES
                ('Real Madrid', 'Barcelona', 'La Liga', '2024-01-15 20:00:00'),
                ('Manchester City', 'Liverpool', 'Premier League', '2024-01-16 15:00:00'),
                ('Bayern Munich', 'Borussia Dortmund', 'Bundesliga', '2024-01-17 18:30:00')
                RETURNING id, home_team, away_team
            """)
        )

        # 2. 创建预测数据（模拟预测算法）
        matches = await fetch_all(
            text("SELECT id, home_team, away_team FROM integration_test_matches ORDER BY id")
        )

        predictions = []
        for match in matches:
            # 模拟预测逻辑
            predicted_home = 2
            predicted_away = 1
            confidence = 0.75 + (len(match['home_team']) % 3) * 0.1  # 模拟置信度变化

            await execute(
                text("""
                    INSERT INTO integration_test_predictions
                    (match_id, predicted_home_score, predicted_away_score, confidence)
                    VALUES (:match_id, :home_score, :away_score, :confidence)
                """),
                {
                    "match_id": match["id"],
                    "home_score": predicted_home,
                    "away_score": predicted_away,
                    "confidence": min(confidence, 0.95)  # 确保不超过0.95
                }
            )
            predictions.append({
                "match_id": match["id"],
                "predicted_home_score": predicted_home,
                "predicted_away_score": predicted_away,
                "confidence": min(confidence, 0.95)
            })

        # 3. 验证预测结果
        stored_predictions = await fetch_all(
            text("""
                SELECT m.home_team, m.away_team, p.predicted_home_score, p.predicted_away_score, p.confidence
                FROM integration_test_matches m
                JOIN integration_test_predictions p ON m.id = p.match_id
                ORDER BY p.confidence DESC
            """)
        )

        assert len(stored_predictions) == 3, "应该有3个预测记录"
        assert stored_predictions[0]["confidence"] >= 0.85, "最高置信度应该≥0.85"

        # 4. 模拟预测分析
        avg_confidence = sum(p["confidence"] for p in predictions) / len(predictions)
        home_wins = sum(1 for p in predictions if p["predicted_home_score"] > p["predicted_away_score"])

        assert 0.7 <= avg_confidence <= 0.9, "平均置信度应该在合理范围"
        assert home_wins > 0, "应该有主队获胜的预测"

    async def test_data_migration_scenario(self, setup_database):
        """测试数据迁移场景"""
        # 1. 模拟旧表结构
        await execute(text("""
            CREATE TABLE IF NOT EXISTS old_users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                contact_info TEXT
            )
        """))

        # 2. 插入旧数据
        await execute(
            text("""
                INSERT INTO old_users (name, contact_info) VALUES
                ('Alice', 'alice@old.com'),
                ('Bob', 'bob@old.com'),
                ('Charlie', 'charlie@old.com')
            """)
        )

        # 3. 数据迁移 - 从旧表迁移到新表
        await execute(text("""
            INSERT INTO integration_test_users (username, email, is_active)
            SELECT
                LOWER(REPLACE(name, ' ', '_')),
                contact_info,
                TRUE
            FROM old_users
            WHERE contact_info LIKE '%@%'
        """))

        # 4. 验证迁移结果
        migrated_users = await fetch_all(text("""
            SELECT username, email, is_active
            FROM integration_test_users
            WHERE username IN ('alice', 'bob', 'charlie')
            ORDER BY username
        """))

        assert len(migrated_users) == 3, "应该迁移3个用户"
        assert migrated_users[0]["username"] == "alice", "用户名应该正确转换"
        assert migrated_users[0]["email"] == "alice@old.com", "邮箱应该正确迁移"

        # 5. 清理旧表（模拟迁移完成）
        await execute(text("DROP TABLE old_users"))

    async def test_concurrent_operations(self, setup_database):
        """测试并发操作"""
        import asyncio

        async def insert_user_batch(start_id: int, count: int):
            """批量插入用户的并发任务"""
            users = [
                {"username": f"concurrent_user_{start_id + i}",
                 "email": f"concurrent_user_{start_id + i}@example.com",
                 "is_active": True}
                for i in range(count)
            ]

            await execute(
                text("INSERT INTO integration_test_users (username, email, is_active) VALUES (:username, :email, :is_active)"),
                users
            )

        # 并发执行多个批量插入任务
        tasks = [
            insert_user_batch(0, 20),
            insert_user_batch(20, 20),
            insert_user_batch(40, 20),
            insert_user_batch(60, 20)
        ]

        await asyncio.gather(*tasks)

        # 验证并发插入结果
        total_users = await fetch_one(text("""
            SELECT COUNT(*) as count
            FROM integration_test_users
            WHERE username LIKE 'concurrent_user_%'
        """))

        assert total_users["count"] == 80, "并发插入应该成功创建80个用户"


# 测试标记
pytest.mark.integration = pytest.mark.integration
pytest.mark.database = pytest.mark.database
pytest.mark.asyncio = pytest.mark.asyncio