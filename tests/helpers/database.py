"""
数据库测试辅助工具
提供测试数据库连接,清理和数据操作功能
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_sqlite_memory_engine():
    """创建内存SQLite引擎"""
    return create_engine("sqlite:///:memory:", echo=False)


def create_sqlite_sessionmaker():
    """创建SQLite会话工厂"""
    engine = create_sqlite_memory_engine()
    return sessionmaker(bind=engine)


class TestDatabaseHelper:
    """测试数据库辅助类"""

    def __init__(self):
        self.session = None
        self.engine = None
        self.connection = None
        self._data_cache = {}

    def get_mock_session(self) -> AsyncMock:
        """获取模拟数据库会话"""
        session = AsyncMock()

        # 模拟基本的数据库操作
        session.execute.return_value.fetchone.return_value = None
        session.execute.return_value.fetchall.return_value = []
        session.commit.return_value = None
        session.rollback.return_value = None
        session.close.return_value = None
        session.refresh.return_value = None

        # 模拟查询操作
        session.query.return_value.filter.return_value.first.return_value = None
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.get.return_value = None

        return session

    def get_mock_connection(self) -> Mock:
        """获取模拟数据库连接"""
        connection = Mock()
        connection.execute.return_value.fetchone.return_value = None
        connection.execute.return_value.fetchall.return_value = []
        connection.commit.return_value = None
        connection.rollback.return_value = None
        connection.close.return_value = None
        return connection

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncMock, None]:
        """获取异步会话上下文管理器"""
        session = self.get_mock_session()
        try:
            yield session
        finally:
            await session.close()

    def create_mock_engine(self) -> Mock:
        """创建模拟数据库引擎"""
        engine = Mock()
        engine.connect.return_value = self.get_mock_connection()
        engine.dispose.return_value = None
        return engine

    def setup_test_data(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        """设置测试数据"""
        if table_name not in self._data_cache:
            self._data_cache[table_name] = []
        self._data_cache[table_name].extend(data)

    def get_test_data(self, table_name: str) -> List[Dict[str, Any]]:
        """获取测试数据"""
        return self._data_cache.get(table_name, [])

    def clear_test_data(self, table_name: Optional[str] = None) -> None:
        """清理测试数据"""
        if table_name:
            self._data_cache.pop(table_name, None)
        else:
            self._data_cache.clear()

    def create_mock_result(self, data: List[Dict[str, Any]], single: bool = False) -> Mock:
        """创建模拟查询结果"""
        result = Mock()

        if single and data:
            result.fetchone.return_value = data[0]
            result.fetchall.return_value = data
        else:
            result.fetchone.return_value = None
            result.fetchall.return_value = data

        return result

    @asynccontextmanager
    async def transaction_scope(self) -> AsyncGenerator[AsyncMock, None]:
        """事务作用域管理器"""
        session = self.get_mock_session()
        try:
            yield session
            await session.commit()
            except Exception:
            await session.rollback()
            raise


class DatabaseTestMixin:
    """数据库测试混入类"""

    @pytest.fixture
    async def db_helper(self) -> TestDatabaseHelper:
        """数据库辅助工具fixture"""
        return TestDatabaseHelper()

    @pytest.fixture
    async def mock_session(self, db_helper: TestDatabaseHelper) -> AsyncMock:
        """模拟会话fixture"""
        return db_helper.get_mock_session()

    @pytest.fixture
    async def mock_engine(self, db_helper: TestDatabaseHelper) -> Mock:
        """模拟引擎fixture"""
        return db_helper.create_mock_engine()

    def assert_query_called(
        self, mock_session: AsyncMock, table: str, operation: str = "select"
    ) -> None:
        """断言查询被调用"""
        if operation == "select":
            mock_session.execute.assert_called()
        elif operation == "insert":
            mock_session.add.assert_called()
        elif operation == "update":
            mock_session.query.assert_called()

    def assert_transaction_committed(self, mock_session: AsyncMock) -> None:
        """断言事务已提交"""
        mock_session.commit.assert_called()


# 全局实例
test_db_helper = TestDatabaseHelper()
