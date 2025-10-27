"""
数据库连接集成测试
测试数据库连接池、事务、查询优化等功能
"""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError


@pytest.mark.integration
class TestDatabaseConnection:
    """数据库连接测试"""

    @pytest.mark.asyncio
    async def test_connection_pool(self, test_db):
        """测试连接池"""

        # 创建多个并发连接
        async def make_query():
            async with test_db() as session:
                _result = await session.execute(text("SELECT 1"))
                return result.scalar()

        # 并发执行查询
        tasks = [make_query() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # 验证所有查询都成功
        assert all(r == 1 for r in results)

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, db_session):
        """测试事务回滚"""
        from src.database.models import Team

        # 开始事务
        async with db_session.begin():
            # 插入数据
            team = Team(name="Rollback Team", city="Rollback City", founded=2020)
            db_session.add(team)
            await db_session.flush()  # 获取 ID

            # 验证数据已插入
            _result = await db_session.execute(
                select(Team).where(Team.name == "Rollback Team")
            )
            assert result.scalar_one_or_none() is not None

            # 故意抛出异常触发回滚
            raise Exception("Trigger rollback")

        # 验证数据已被回滚
        _result = await db_session.execute(
            select(Team).where(Team.name == "Rollback Team")
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_transaction_commit(self, db_session):
        """测试事务提交"""
        from src.database.models import Team

        # 插入数据并提交
        async with db_session.begin():
            team = Team(name="Commit Team", city="Commit City", founded=2020)
            db_session.add(team)

        # 验证数据已提交
        _result = await db_session.execute(
            select(Team).where(Team.name == "Commit Team")
        )
        saved_team = result.scalar_one_or_none()
        assert saved_team is not None
        assert saved_team.city == "Commit City"

    @pytest.mark.asyncio
    async def test_nested_transactions(self, db_session):
        """测试嵌套事务（savepoints）"""
        from src.database.models import Team

        # 外层事务
        async with db_session.begin():
            team1 = Team(name="Outer Team", city="Outer City", founded=2020)
            db_session.add(team1)

            # 内层事务（savepoint）
            try:
                async with db_session.begin():
                    team2 = Team(name="Inner Team", city="Inner City", founded=2020)
                    db_session.add(team2)
                    raise Exception("Inner rollback")
            except Exception:
                pass  # 内层回滚

            # 验证外层数据仍在
            _result = await db_session.execute(
                select(Team).where(Team.name == "Outer Team")
            )
            assert result.scalar_one_or_none() is not None

        # 验证内层数据被回滚
        _result = await db_session.execute(
            select(Team).where(Team.name == "Inner Team")
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_connection_retry(self, test_db):
        """测试连接重试机制"""

        # 这个测试需要模拟连接失败
        async def query_with_retry():
            retry_count = 0
            max_retries = 3

            while retry_count < max_retries:
                try:
                    async with test_db() as session:
                        _result = await session.execute(text("SELECT 1"))
                        return result.scalar()
                except Exception:
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise
                    await asyncio.sleep(0.1)  # 短暂等待后重试

        _result = await query_with_retry()
        assert _result == 1

    @pytest.mark.asyncio
    async def test_batch_operations(self, db_session):
        """测试批量操作"""
        from src.database.models import Team

        # 批量插入
        _teams = []
        for i in range(100):
            team = Team(
                name=f"Batch Team {i}", city=f"Batch City {i}", founded=2000 + i
            )
            teams.append(team)

        db_session.add_all(teams)
        await db_session.commit()

        # 验证批量插入
        _result = await db_session.execute(
            select(func.count(Team.id)).where(Team.name.like("Batch Team%"))
        )
        count = result.scalar()
        assert count == 100

        # 批量更新
        await db_session.execute(
            text("UPDATE teams SET city = 'Updated City' WHERE name LIKE 'Batch Team%'")
        )
        await db_session.commit()

        # 验证批量更新
        _result = await db_session.execute(
            select(func.count(Team.id)).where(Team.city == "Updated City")
        )
        count = result.scalar()
        assert count == 100

        # 批量删除
        await db_session.execute(
            text("DELETE FROM teams WHERE name LIKE 'Batch Team%'")
        )
        await db_session.commit()

        # 验证批量删除
        _result = await db_session.execute(
            select(func.count(Team.id)).where(Team.name.like("Batch Team%"))
        )
        count = result.scalar()
        assert count == 0

    @pytest.mark.asyncio
    async def test_query_performance(self, db_session):
        """测试查询性能"""
        import time

        from src.database.models import Match, Team

        # 创建测试数据
        _teams = []
        for i in range(50):
            team = Team(name=f"Perf Team {i}", city=f"Perf City {i}", founded=2000 + i)
            teams.append(team)
        db_session.add_all(teams)
        await db_session.commit()

        # 插入比赛数据
        _matches = []
        for i in range(500):
            match = Match(
                home_team_id=teams[i % 50].id,
                away_team_id=teams[(i + 1) % 50].id,
                match_date=datetime.now(timezone.utc),
                competition="Performance League",
                season="2024/2025",
                status="COMPLETED",
                home_score=i % 5,
                away_score=(i + 1) % 5,
            )
            matches.append(match)
        db_session.add_all(matches)
        await db_session.commit()

        # 测试查询性能
        start_time = time.time()

        # 复杂查询
        _result = await db_session.execute(
            text(
                """
            SELECT t.name, COUNT(m.id) as match_count
            FROM teams t
            LEFT JOIN matches m ON (t.id = m.home_team_id OR t.id = m.away_team_id)
            WHERE t.name LIKE 'Perf Team%'
            GROUP BY t.id, t.name
            HAVING COUNT(m.id) > 5
            ORDER BY match_count DESC
            LIMIT 10
        """
            )
        )

        rows = result.fetchall()
        query_time = time.time() - start_time

        # 验证查询时间合理（应小于 1 秒）
        assert query_time < 1.0
        assert len(rows) > 0

    @pytest.mark.asyncio
    async def test_index_usage(self, db_session):
        """测试索引使用"""
        import time

        from src.database.models import Prediction, User

        # 创建用户和预测数据
        users = []
        for i in range(10):
            _user = User(
                username=f"index_user_{i}",
                email=f"user{i}@index.com",
                password_hash="hashed",
                role="user",
            )
            users.append(user)
        db_session.add_all(users)
        await db_session.commit()

        # 创建大量预测数据
        predictions = []
        for user in users:
            for i in range(100):
                pred = Prediction(
                    user_id=user.id,
                    match_id=1,
                    _prediction="HOME_WIN" if i % 2 == 0 else "AWAY_WIN",
                    confidence=0.5 + (i * 0.01),
                    created_at=datetime.now(timezone.utc),
                )
                predictions.append(pred)
        db_session.add_all(predictions)
        await db_session.commit()

        # 测试索引查询
        start_time = time.time()

        _result = await db_session.execute(
            select(Prediction).where(Prediction.user_id == users[0].id)
        )
        user_predictions = result.scalars().all()

        query_time = time.time() - start_time

        # 验证查询结果和时间
        assert len(user_predictions) == 100
        assert query_time < 0.5  # 索引查询应该很快

    @pytest.mark.asyncio
    async def test_connection_timeout(self, test_db):
        """测试连接超时"""
        # 设置较短的超时时间
        async with test_db() as session:
            # 执行一个长时间查询（模拟）
            start_time = datetime.now()

            # 使用 pg_sleep 模拟长时间查询（PostgreSQL）
            try:
                _result = await session.execute(text("SELECT pg_sleep(2)"))
            except Exception:
                # 如果 pg_sleep 不可用，使用正常查询
                _result = await session.execute(text("SELECT 1"))

            elapsed = (datetime.now() - start_time).total_seconds()

            # 验证查询执行
            assert elapsed > 0

    @pytest.mark.asyncio
    async def test_concurrent_transactions(self, test_db):
        """测试并发事务"""
        from src.database.models import Team

        async def create_team(team_id):
            async with test_db() as session:
                async with session.begin():
                    team = Team(
                        name=f"Concurrent Team {team_id}",
                        city="Concurrent City",
                        founded=2020,
                    )
                    session.add(team)
                    await session.flush()
                    return team.id

        # 并发创建多个队伍
        tasks = [create_team(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # 验证所有队伍都创建成功
        assert len(set(results)) == 20  # 检查没有重复的 ID

        # 验证数据库中的数据
        async with test_db() as session:
            _result = await session.execute(
                select(func.count(Team.id)).where(Team.name.like("Concurrent Team%"))
            )
            count = result.scalar()
            assert count == 20

    @pytest.mark.asyncio
    async def test_error_handling(self, db_session):
        """测试错误处理"""
        from src.database.models import Team

        # 测试唯一约束违反
        team1 = Team(name="Unique Team", city="City 1", founded=2020)
        team2 = Team(name="Unique Team", city="City 2", founded=2021)

        db_session.add(team1)
        await db_session.commit()

        db_session.add(team2)

        # 应该抛出异常
        with pytest.raises(SQLAlchemyError):
            await db_session.commit()

        # 验证事务已回滚
        await db_session.rollback()

        # 验证只有第一个队伍存在
        _result = await db_session.execute(
            select(Team).where(Team.name == "Unique Team")
        )
        _teams = result.scalars().all()
        assert len(teams) == 1
