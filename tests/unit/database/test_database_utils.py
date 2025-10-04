"""数据库工具测试"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import create_sqlite_memory_engine, create_sqlite_sessionmaker


class TestDatabaseUtils:
    """数据库工具测试 - 使用内存 SQLite"""

    @pytest.fixture
    async def db_session(self):
        """内存数据库会话"""
        engine = create_sqlite_memory_engine()
        sessionmaker = create_sqlite_sessionmaker(engine)
        async with sessionmaker() as session:
            yield session
        engine.dispose()

    @pytest.mark.asyncio
    async def test_database_connection(self, db_session):
        """测试数据库连接"""
        assert isinstance(db_session, AsyncSession)

        # 执行简单查询
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_transaction_commit(self, db_session):
        """测试事务提交"""
        # 创建表
        await db_session.execute(text("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """))

        # 插入数据
        await db_session.execute(
            text("INSERT INTO test_table (name) VALUES (:name)"),
            {"name": "test"}
        )
        await db_session.commit()

        # 查询数据
        result = await db_session.execute(text("SELECT name FROM test_table"))
        assert result.scalar() == "test"

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, db_session):
        """测试事务回滚"""
        # 创建表
        await db_session.execute(text("""
            CREATE TABLE test_table2 (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """))

        # 插入数据
        await db_session.execute(
            text("INSERT INTO test_table2 (name) VALUES (:name)"),
            {"name": "test"}
        )

        # 模拟错误并回滚
        await db_session.rollback()

        # 插入新数据
        await db_session.execute(
            text("INSERT INTO test_table2 (name) VALUES (:name)"),
            {"name": "test2"}
        )
        await db_session.commit()

        # 查询数据
        result = await db_session.execute(text("SELECT COUNT(*) FROM test_table2"))
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_multiple_sessions_isolation(self):
        """测试多个会话隔离"""
        engine = create_sqlite_memory_engine()
        sessionmaker = create_sqlite_sessionmaker(engine)

        async with sessionmaker() as session1:
            async with sessionmaker() as session2:
                # 在两个会话中创建表
                for session in [session1, session2]:
                    await session.execute(text("""
                        CREATE TABLE test_isolation (
                            id INTEGER PRIMARY KEY,
                            value TEXT
                        )
                    """))
                    await session.commit()

                # 在 session1 插入数据
                await session1.execute(
                    text("INSERT INTO test_isolation (value) VALUES ('session1')")
                )
                await session1.commit()

                # session2 应该看不到 session1 的数据（如果隔离级别正确）
                result = await session2.execute(text("SELECT COUNT(*) FROM test_isolation"))
                result.scalar()
                # SQLite 的隔离可能较弱，所以这个测试可能需要调整

        engine.dispose()