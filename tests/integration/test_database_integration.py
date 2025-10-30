"""""""
数据库集成测试
Database Integration Tests

测试数据库集成和仓储模式
"""""""

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 测试导入
try:
    from src.database.config import get_database_url
    from src.database.connection import DatabaseManager
    from src.database.models import Base
    from src.database.repositories import BaseRepository

    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    DATABASE_AVAILABLE = False
    DatabaseManager = None
    BaseRepository = None
    Base = None
    get_database_url = None


@pytest.mark.skipif(not DATABASE_AVAILABLE, reason="Database modules not available")
@pytest.mark.integration
class TestDatabaseConnection:
    """数据库连接测试"""

    @pytest.fixture
    async def test_engine(self):
        """创建测试数据库引擎"""
        # 使用SQLite内存数据库进行测试
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)

        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine

        # 清理
        await engine.dispose()

    @pytest.fixture
    async def test_session(self, test_engine):
        """创建测试数据库会话"""
        async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            yield session

    async def test_database_connection(self):
        """测试：数据库连接"""
        # 使用内存SQLite数据库
        db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:")

        # 应该能够创建连接
        async with db_manager.get_session() as session:
            assert session is not None
            assert isinstance(session, AsyncSession)

    async def test_database_manager_context_manager(self):
        """测试：数据库管理器上下文管理器"""
        db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:")

        async with db_manager.get_session() as session:
            # 执行简单查询
            _result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    async def test_database_transaction(self, test_session):
        """测试：数据库事务"""
        # 开始事务
        async with test_session.begin():
            # 执行插入
            await test_session.execute(
                text("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, value TEXT)")
            )
            await test_session.execute(
                text("INSERT INTO test_table (value) VALUES (:value)"),
                {"value": "test_value"},
            )

        # 验证数据已提交
        _result = await test_session.execute(text("SELECT value FROM test_table"))
        assert result.scalar() == "test_value"

    async def test_database_transaction_rollback(self, test_session):
        """测试：数据库事务回滚"""
        # 创建测试表
        await test_session.execute(
            text("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, value TEXT)")
        )

        try:
            # 开始事务
            async with test_session.begin():
                # 插入数据
                await test_session.execute(
                    text("INSERT INTO test_table (value) VALUES (:value)"),
                    {"value": "rollback_test"},
                )
                # 故意抛出异常触发回滚
                raise Exception("Test rollback")
        except Exception:
            pass

        # 验证数据未被提交
        _result = await test_session.execute(
            text("SELECT COUNT(*) FROM test_table WHERE value = :value"),
            {"value": "rollback_test"},
        )
        assert result.scalar() == 0


@pytest.mark.skipif(not DATABASE_AVAILABLE, reason="Database modules not available")
@pytest.mark.integration
class TestBaseRepository:
    """基础仓储测试"""

    @pytest.fixture
    async def repo_session(self):
        """创建仓储测试会话"""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)

        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            yield session

        await engine.dispose()

    async def test_base_repository_creation(self, repo_session):
        """测试：基础仓储创建"""
        # BaseRepository是抽象类，不能直接实例化
        # 但可以测试其接口
        assert hasattr(BaseRepository, "__abstract__")

        # 创建具体实现
        class TestRepository(BaseRepository):
            model_class = None

            async def create(self, **kwargs):
                return await super().create(**kwargs)

            async def get_by_id(self, id):
                return await super().get_by_id(id)

            async def get_all(self):
                return await super().get_all()

            async def update(self, id, **kwargs):
                return await super().update(id, **kwargs)

            async def delete(self, id):
                return await super().delete(id)

        repo = TestRepository(repo_session)
        assert repo.session is repo_session

    async def test_base_repository_session_management(self, repo_session):
        """测试：基础仓储会话管理"""

        class TestRepository(BaseRepository):
            model_class = None

        repo = TestRepository(repo_session)
        assert repo.session is repo_session

        # 会话应该是AsyncSession类型
        assert isinstance(repo_session, AsyncSession)

    async def test_base_repository_methods_exist(self, repo_session):
        """测试：基础仓储方法存在"""

        class TestRepository(BaseRepository):
            model_class = None

        repo = TestRepository(repo_session)

        # 检查所有CRUD方法
        assert hasattr(repo, "create")
        assert hasattr(repo, "get_by_id")
        assert hasattr(repo, "get_all")
        assert hasattr(repo, "update")
        assert hasattr(repo, "delete")
        assert hasattr(repo, "count")
        assert hasattr(repo, "exists")


@pytest.mark.skipif(not DATABASE_AVAILABLE, reason="Database modules not available")
@pytest.mark.integration
class TestDatabaseConfig:
    """数据库配置测试"""

    def test_get_database_url(self):
        """测试：获取数据库URL"""
        if get_database_url:
            url = get_database_url()
            assert url is not None
            assert isinstance(url, str)
            # 应该包含数据库驱动信息
            assert any(db in url for db in ["postgresql", "mysql", "sqlite"])

    def test_database_url_parsing(self):
        """测试：数据库URL解析"""
        # 测试各种数据库URL格式
        test_urls = [
            "postgresql+asyncpg://user:pass@localhost/db",
            "mysql+aiomysql://user:pass@localhost/db",
            "sqlite+aiosqlite:///test.db",
        ]

        for url in test_urls:
            # 应该能够解析URL
            assert "+" in url  # 异步驱动标识
            assert "://" in url  # URL格式

    @patch.dict(os.environ, {"DATABASE_URL": "sqlite+aiosqlite:///test.db"})
    def test_database_url_from_env(self):
        """测试：从环境变量获取数据库URL"""
        if get_database_url:
            url = get_database_url()
            assert url       == "sqlite+aiosqlite:///test.db"


@pytest.mark.skipif(not DATABASE_AVAILABLE, reason="Database modules not available")
@pytest.mark.integration
class TestDatabasePerformance:
    """数据库性能测试"""

    async def test_connection_pool(self):
        """测试：数据库连接池"""
        # 使用连接池配置
        db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:", pool_size=5, max_overflow=10)

        # 应该能够获取多个连接
        sessions = []
        for _ in range(3):
            session = await db_manager.get_session().__aenter__()
            sessions.append(session)

        # 关闭所有连接
        for session in sessions:
            await session.close()

    async def test_bulk_operations(self):
        """测试：批量操作"""
        db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:")

        async with db_manager.get_session() as session:
            # 创建测试表
            await session.execute(
                text(
                    """""""
                CREATE TABLE test_bulk (
                    id INTEGER PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """""""
                )
            )

            # 批量插入
            test_data = [{"value": f"item_{i}"} for i in range(100)]

            import time

            start_time = time.time()

            # 使用execute_many进行批量插入
            await session.execute(text("INSERT INTO test_bulk (value) VALUES (:value)"), test_data)

            end_time = time.time()

            # 批量操作应该很快
            assert end_time - start_time < 1.0

            # 验证数据
            _result = await session.execute(text("SELECT COUNT(*) FROM test_bulk"))
            assert result.scalar() == 100

    async def test_concurrent_operations(self):
        """测试：并发操作"""
        db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:")

        async def concurrent_query(session_id):
            async with db_manager.get_session() as session:
                # 创建测试表
                await session.execute(
                    text(
                        f"""""""
                    CREATE TABLE IF NOT EXISTS test_concurrent_{session_id} (
                        id INTEGER PRIMARY KEY,
                        value TEXT
                    )
                """""""
                    )
                )

                # 插入数据
                await session.execute(
                    text(f"INSERT INTO test_concurrent_{session_id} (value) VALUES (:value)"),
                    {"value": f"session_{session_id}"},
                )

                # 查询数据
                _result = await session.execute(
                    text(f"SELECT value FROM test_concurrent_{session_id}")
                )
                return result.scalar()

        # 并发执行多个查询
        tasks = [concurrent_query(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # 所有查询都应该成功
        assert len(results) == 10
        for i, result in enumerate(results):
            assert _result       == f"session_{i}"


@pytest.mark.skipif(DATABASE_AVAILABLE, reason="Database modules should be available")
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not DATABASE_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports(
    client,
):
    """测试：模块导入"""
    if DATABASE_AVAILABLE:
from src.database.connection import DatabaseManager
from src.database.models import Base
from src.database.repositories import BaseRepository

        assert DatabaseManager is not None
        assert BaseRepository is not None
        assert Base is not None


def test_database_manager_class(
    client,
):
    """测试：数据库管理器类"""
    if DATABASE_AVAILABLE:
        assert DatabaseManager is not None
        assert hasattr(DatabaseManager, "get_session")
        assert hasattr(DatabaseManager, "close")


@pytest.mark.skipif(not DATABASE_AVAILABLE, reason="Database modules not available")
class TestDatabaseErrorHandling:
    """数据库错误处理测试"""

    async def test_invalid_connection_string(self):
        """测试：无效连接字符串"""
        # 使用无效的连接字符串
        invalid_url = "invalid://connection/string"

        # 应该抛出适当的异常
        with pytest.raises(Exception):
            db_manager = DatabaseManager(invalid_url)
            async with db_manager.get_session() as session:
                await session.execute(text("SELECT 1"))

    async def test_connection_timeout(self):
        """测试：连接超时"""
        # 使用不存在的数据库（应该超时）
        timeout_url = "postgresql+asyncpg://user:pass@localhost:99999/nonexistent"

        try:
            db_manager = DatabaseManager(timeout_url, connect_timeout=1)
            async with db_manager.get_session() as session:
                await session.execute(text("SELECT 1"))
        except Exception:
            # 预期的连接错误
            pass

    async def test_sql_injection_prevention(self):
        """测试：SQL注入防护"""
        db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:")

        async with db_manager.get_session() as session:
            # 创建测试表
            await session.execute(
                text(
                    """""""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    email TEXT
                )
            """""""
                )
            )

            # 插入测试数据
            await session.execute(
                text("INSERT INTO users (username, email) VALUES (:username, :email)"),
                {"username": "testuser", "email": "test@example.com"},
            )

            # 尝试SQL注入（使用参数化查询应该安全）
            malicious_input = "testuser'; DROP TABLE users; --"'
            _result = await session.execute(
                text("SELECT * FROM users WHERE username = :username"),
                {"username": malicious_input},
            )

            # 应该没有结果（注入失败）
            users = result.fetchall()
            assert len(users) == 0

            # 验证表仍然存在
            _result = await session.execute(text("SELECT COUNT(*) FROM users"))
            assert result.scalar() == 1
