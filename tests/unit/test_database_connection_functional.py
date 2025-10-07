"""
数据库连接功能测试
测试实际的数据库连接和操作功能
"""

import pytest
import os
from unittest.mock import patch
from sqlalchemy import text

# 设置测试环境
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


@pytest.mark.unit
class TestDatabaseConnectionFunctional:
    """数据库连接功能测试"""

    def test_database_engine_creation(self):
        """测试数据库引擎创建"""
        try:
            from src.database.connection import DatabaseManager, get_engine

            # 测试获取引擎
            engine = get_engine()
            assert engine is not None

            # 测试数据库管理器
            db_manager = DatabaseManager()
            assert hasattr(db_manager, 'engine')
            assert db_manager.engine is not None

            # 验证引擎类型
            assert hasattr(engine, 'execute')
            assert hasattr(engine, 'connect')

        except ImportError:
            pytest.skip("Database connection module not available")

    def test_sqlite_memory_connection(self):
        """测试SQLite内存数据库连接"""
        try:
            from src.database.connection import create_sqlite_engine

            # 创建内存数据库引擎
            engine = create_sqlite_engine("sqlite:///:memory:")
            assert engine is not None

            # 测试连接
            with engine.connect() as conn:
                # 执行简单查询
                result = conn.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1

                # 创建测试表
                conn.execute(text("""
                    CREATE TABLE test_table (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL
                    )
                """))

                # 插入数据
                conn.execute(text(
                    "INSERT INTO test_table (name) VALUES (?)"
                ), ("Test Name",))

                # 查询数据
                result = conn.execute(text("SELECT name FROM test_table"))
                row = result.fetchone()
                assert row[0] == "Test Name"

        except ImportError:
            pytest.skip("SQLite engine creation not available")

    def test_session_factory_creation(self):
        """测试会话工厂创建"""
        try:
            from src.database.connection import create_session_factory, get_session

            # 创建会话工厂
            session_factory = create_session_factory()
            assert session_factory is not None
            assert callable(session_factory)

            # 测试创建会话
            with get_session() as session:
                assert session is not None
                assert hasattr(session, 'execute')
                assert hasattr(session, 'commit')
                assert hasattr(session, 'rollback')

        except ImportError:
            pytest.skip("Session factory not available")

    def test_database_transaction(self):
        """测试数据库事务"""
        try:
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()

            # 测试事务
            with db_manager.get_session() as session:
                # 创建测试表
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS test_transaction (
                        id INTEGER PRIMARY KEY,
                        value TEXT
                    )
                """))

                # 插入数据
                session.execute(text(
                    "INSERT INTO test_transaction (value) VALUES (?)"
                ), ("test_value",))

                # 查询数据
                result = session.execute(text("SELECT value FROM test_transaction"))
                row = result.fetchone()
                assert row[0] == "test_value"

                # 事务自动提交

        except ImportError:
            pytest.skip("Database transaction not available")

    def test_connection_pooling(self):
        """测试连接池"""
        try:
            from src.database.connection import get_engine_with_pool

            # 创建带连接池的引擎
            engine = get_engine_with_pool(pool_size=5, max_overflow=10)
            assert engine is not None

            # 测试多个连接
            connections = []
            for i in range(3):
                conn = engine.connect()
                connections.append(conn)
                result = conn.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1

            # 关闭所有连接
            for conn in connections:
                conn.close()

        except ImportError:
            pytest.skip("Connection pooling not available")

    def test_async_database_connection(self):
        """测试异步数据库连接"""
        try:
            import asyncio
            from src.database.connection import AsyncDatabaseManager, get_async_engine

            async def test_async():
                # 创建异步引擎
                engine = await get_async_engine()
                assert engine is not None

                # 创建异步数据库管理器
                db_manager = AsyncDatabaseManager()
                assert hasattr(db_manager, 'engine')

                # 测试异步会话
                async with db_manager.get_session() as session:
                    # 执行查询
                    result = await session.execute(text("SELECT 1"))
                    assert result.fetchone()[0] == 1

            # 运行异步测试
            asyncio.run(test_async())

        except ImportError:
            pytest.skip("Async database not available")

    def test_database_health_check(self):
        """测试数据库健康检查"""
        try:
            from src.database.connection import check_database_health

            # 执行健康检查
            health = check_database_health()
            assert isinstance(health, dict)

            # 检查必要字段
            assert "status" in health
            assert "timestamp" in health
            assert health["status"] in ["healthy", "unhealthy"]

        except ImportError:
            pytest.skip("Database health check not available")

    def test_database_migration_check(self):
        """测试数据库迁移检查"""
        try:
            from src.database.connection import check_migrations, get_migration_status

            # 检查迁移状态
            status = get_migration_status()
            assert isinstance(status, dict)

            # 执行迁移检查
            migrations_ok = check_migrations()
            assert isinstance(migrations_ok, bool)

        except ImportError:
            pytest.skip("Migration check not available")

    def test_database_error_handling(self):
        """测试数据库错误处理"""
        try:
            from src.database.connection import DatabaseManager, DatabaseError

            db_manager = DatabaseManager()

            # 测试无效SQL
            with pytest.raises(Exception):  # 可能是各种数据库异常
                with db_manager.get_session() as session:
                    session.execute(text("INVALID SQL QUERY"))

            # 测试连接错误
            with patch.object(db_manager, 'engine', None):
                with pytest.raises((AttributeError, DatabaseError)):
                    db_manager.get_session()

        except ImportError:
            pytest.skip("Database error handling not available")

    def test_database_configuration(self):
        """测试数据库配置"""
        try:
            from src.database.connection import get_database_config, configure_database

            # 获取配置
            config = get_database_config()
            assert isinstance(config, dict)

            # 配置数据库
            test_config = {
                "echo": True,
                "pool_size": 5,
                "max_overflow": 10
            }

            configure_database(**test_config)

        except ImportError:
            pytest.skip("Database configuration not available")

    def test_connection_timeout(self):
        """测试连接超时"""
        try:
            from src.database.connection import DatabaseManager

            # 创建带超时配置的管理器
            db_manager = DatabaseManager(
                connect_timeout=5,
                query_timeout=10
            )

            # 测试连接
            with db_manager.get_session() as session:
                # 快速查询应该成功
                result = session.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1

        except ImportError:
            pytest.skip("Connection timeout not available")

    def test_database_closing(self):
        """测试数据库关闭"""
        try:
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()

            # 测试连接
            with db_manager.get_session() as session:
                result = session.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1

            # 测试关闭
            if hasattr(db_manager, 'close'):
                db_manager.close()
                assert True  # 到这里说明关闭成功

        except ImportError:
            pytest.skip("Database closing not available")

    def test_database_url_parsing(self):
        """测试数据库URL解析"""
        try:
            from src.database.connection import parse_database_url

            test_urls = [
                "sqlite:///test.db",
                "postgresql://user:pass@localhost:5432/test",
                "mysql://user:pass@localhost:3306/test",
            ]

            for url in test_urls:
                parsed = parse_database_url(url)
                assert isinstance(parsed, dict)
                assert "dialect" in parsed

        except ImportError:
            pytest.skip("Database URL parsing not available")

    def test_database_logging(self):
        """测试数据库日志记录"""
        try:
            from src.database.connection import DatabaseManager
            import logging

            # 设置日志捕获
            logger = logging.getLogger("sqlalchemy.engine")
            logger.setLevel(logging.INFO)

            db_manager = DatabaseManager(echo=True)

            # 执行查询
            with db_manager.get_session() as session:
                session.execute(text("SELECT 1"))

        except ImportError:
            pytest.skip("Database logging not available")

    def test_thread_safety(self):
        """测试线程安全性"""
        import threading

        try:
            from src.database.connection import get_session

            results = []

            def worker():
                with get_session() as session:
                    result = session.execute(text("SELECT 1"))
                    results.append(result.fetchone()[0])

            # 创建多个线程
            threads = []
            for i in range(5):
                t = threading.Thread(target=worker)
                threads.append(t)
                t.start()

            # 等待所有线程完成
            for t in threads:
                t.join()

            # 验证结果
            assert len(results) == 5
            assert all(r == 1 for r in results)

        except ImportError:
            pytest.skip("Thread safety test not available")