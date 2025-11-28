"""数据库仓储层测试 - 实现90%+覆盖率.

测试 src/database/repositories/base.py 的 BaseRepository CRUD 操作
"""

from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import DatabaseError, SQLAlchemyError

from src.database.repositories.base import BaseRepository


class MockModel:
    """模拟SQLAlchemy模型类."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"MockModel(id={self.id})"

    # 模拟SQLAlchemy的属性和列
    id = None
    name = None
    email = None
    created_at = None

    # 添加模拟的SQLAlchemy属性
    __table__ = type('MockTable', (), {'name': 'mock_model'})()
    __tablename__ = 'mock_model'


class MockDatabaseManager:
    """模拟数据库管理器."""

    def __init__(self):
        self.get_async_session_call_count = 0

    def get_async_session(self):
        """返回模拟的异步会话."""
        self.get_async_session_call_count += 1
        return MockAsyncSession()


class MockAsyncSession:
    """模拟异步数据库会话."""

    def __init__(self):
        self.added_objects = []
        self.committed = False
        self.rolled_back = False
        self.refreshed_objects = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def add(self, obj):
        """添加对象到会话."""
        self.added_objects.append(obj)

    def add_all(self, objects):
        """批量添加对象到会话."""
        self.added_objects.extend(objects)

    async def commit(self):
        """提交事务."""
        self.committed = True

    async def rollback(self):
        """回滚事务."""
        self.rolled_back = True

    async def refresh(self, obj):
        """刷新对象."""
        self.refreshed_objects.append(obj)

    async def execute(self, stmt):
        """执行SQL语句."""
        return MockExecuteResult()


class MockExecuteResult:
    """模拟SQL执行结果."""

    def __init__(self):
        self.scalar_one_or_none_result = None
        self.scalars_all_result = []
        self.rowcount = 1

    def scalar_one_or_none(self):
        """返回单个标量结果或None."""
        return self.scalar_one_or_none_result

    def scalars(self):
        """返回标量结果集合."""
        return MockScalars(self.scalars_all_result)

    def __getattr__(self, name):
        """处理其他属性."""
        return lambda: None


class MockScalars:
    """模拟SQLAlchemy scalars结果."""

    def __init__(self, results):
        self.results = results

    def all(self):
        """返回所有结果."""
        return self.results


class MockException(Exception):
    """模拟异常."""
    pass


class ConcreteRepository(BaseRepository):
    """具体的仓储实现，用于测试."""

    async def get_related_data(self, obj_id, relation_name, session=None):
        """实现抽象方法."""
        return {"obj_id": obj_id, "relation_name": relation_name}


class TestBaseRepository:
    """BaseRepository测试."""

    def setup_method(self):
        """设置测试方法."""
        self.model_class = MockModel
        self.db_manager = MockDatabaseManager()
        self.repository = ConcreteRepository(self.model_class, self.db_manager)

    def test_initialization_with_db_manager(self):
        """测试带数据库管理器的初始化."""
        repo = ConcreteRepository(self.model_class, self.db_manager)
        assert repo.model_class == self.model_class
        assert repo.db_manager == self.db_manager
        assert repo.get_model_name() == "MockModel"

    def test_initialization_without_db_manager(self):
        """测试不带数据库管理器的初始化."""
        with patch('src.database.repositories.base.DatabaseManager') as mock_dm:
            mock_dm.return_value = MockDatabaseManager()
            repo = ConcreteRepository(self.model_class)
            assert repo.db_manager is not None
            mock_dm.assert_called_once()

    def test_get_model_class(self):
        """测试获取模型类."""
        assert self.repository.get_model_class() == self.model_class

    def test_get_model_name(self):
        """测试获取模型名称."""
        assert self.repository.get_model_name() == "MockModel"

    @pytest.mark.asyncio
    async def test_create_success(self):
        """测试成功创建记录."""
        obj_data = {"name": "Test Object", "email": "test@example.com"}

        result = await self.repository.create(obj_data)

        assert isinstance(result, MockModel)
        assert result.name == "Test Object"
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_create_with_session(self):
        """测试使用外部会话创建记录."""
        obj_data = {"name": "Test Object"}
        mock_session = MockAsyncSession()

        result = await self.repository.create(obj_data, session=mock_session)

        assert isinstance(result, MockModel)
        assert result.name == "Test Object"

    @pytest.mark.asyncio
    async def test_get_by_id_success(self):
        """测试根据ID成功获取记录."""
        mock_result = MockExecuteResult()
        mock_model = MockModel(id=1, name="Test")
        mock_result.scalar_one_or_none_result = mock_model

        with patch.object(self.repository, 'find_one_by') as mock_find:
            mock_find.return_value = mock_model

            result = await self.repository.get_by_id(1)

            assert result == mock_model
            mock_find.assert_called_once_with({"id": 1}, session=None)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """测试根据ID未找到记录."""
        with patch.object(self.repository, 'find_one_by') as mock_find:
            mock_find.return_value = None

            result = await self.repository.get_by_id(999)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_with_session(self):
        """测试使用外部会话根据ID获取记录."""
        mock_session = MockAsyncSession()

        with patch.object(self.repository, 'find_one_by') as mock_find:
            mock_find.return_value = MockModel(id=1)

            result = await self.repository.get_by_id(1, session=mock_session)

            assert result is not None
            mock_find.assert_called_once_with({"id": 1}, session=mock_session)

    @pytest.mark.asyncio
    async def test_get_all_success(self):
        """测试成功获取所有记录."""
        mock_models = [MockModel(id=1), MockModel(id=2)]

        with patch.object(self.repository, 'find_by') as mock_find:
            mock_find.return_value = mock_models

            result = await self.repository.get_all()

            assert len(result) == 2
            mock_find.assert_called_once_with({}, limit=None, offset=None, order_by=None, session=None)

    @pytest.mark.asyncio
    async def test_get_all_with_limit_offset(self):
        """测试带限制和偏移量的获取所有记录."""
        mock_models = [MockModel(id=1)]

        with patch.object(self.repository, 'find_by') as mock_find:
            mock_find.return_value = mock_models

            result = await self.repository.get_all(limit=10, offset=5)

            assert len(result) == 1
            mock_find.assert_called_once_with({}, limit=10, offset=5, order_by=None, session=None)

    @pytest.mark.asyncio
    async def test_get_all_with_session(self):
        """测试使用外部会话获取所有记录."""
        mock_session = MockAsyncSession()

        with patch.object(self.repository, 'find_by') as mock_find:
            mock_find.return_value = []

            result = await self.repository.get_all(session=mock_session)

            assert isinstance(result, list)
            mock_find.assert_called_once_with({}, limit=None, offset=None, order_by=None, session=mock_session)

    @pytest.mark.asyncio
    async def test_update_success(self):
        """测试成功更新记录."""
        mock_model = MockModel(id=1, name="Updated")
        update_data = {"name": "Updated Name"}

        # 模拟数据库执行
        with patch('sqlalchemy.select') as mock_select, \
             patch('sqlalchemy.update') as mock_update, \
             patch.object(self.db_manager, 'get_async_session') as mock_get_session:

            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 模拟执行结果
            mock_result = MockExecuteResult()
            mock_result.scalar_one_or_none_result = mock_model
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await self.repository.update(1, update_data)

            assert result == mock_model

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        """测试更新不存在的记录."""
        update_data = {"name": "Updated Name"}

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 模拟执行结果为None
            mock_result = MockExecuteResult()
            mock_result.scalar_one_or_none_result = None
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await self.repository.update(999, update_data)

            assert result is None

    @pytest.mark.asyncio
    async def test_update_with_session(self):
        """测试使用外部会话更新记录."""
        mock_session = MockAsyncSession()
        update_data = {"name": "Updated Name"}

        # 模拟执行结果
        mock_result = MockExecuteResult()
        mock_result.scalar_one_or_none_result = MockModel(id=1)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await self.repository.update(1, update_data, session=mock_session)

        assert result is not None

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """测试成功删除记录."""
        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 模拟删除成功
            mock_result = MockExecuteResult()
            mock_result.rowcount = 1
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await self.repository.delete(1)

            assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """测试删除不存在的记录."""
        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 模拟删除失败（没有影响行）
            mock_result = MockExecuteResult()
            mock_result.rowcount = 0
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await self.repository.delete(999)

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_with_session(self):
        """测试使用外部会话删除记录."""
        mock_session = MockAsyncSession()

        # 模拟删除成功
        mock_result = MockExecuteResult()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await self.repository.delete(1, session=mock_session)

        assert result is True

    @pytest.mark.asyncio
    async def test_find_by_success(self):
        """测试根据条件查找记录."""
        filters = {"name": "Test"}
        mock_models = [MockModel(id=1, name="Test")]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 模拟执行结果
            mock_result = MockExecuteResult()
            mock_result.scalars_all_result = mock_models
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await self.repository.find_by(filters)

            assert len(result) == 1
            assert result[0].name == "Test"

    @pytest.mark.asyncio
    async def test_find_by_with_limit_offset_order(self):
        """测试带限制、偏移和排序的查找."""
        filters = {"name": "Test"}
        mock_models = [MockModel(id=1, name="Test")]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            mock_result = MockExecuteResult()
            mock_result.scalars_all_result = mock_models
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await self.repository.find_by(
                filters, limit=10, offset=5, order_by="created_at"
            )

            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_find_by_invalid_filters(self):
        """测试使用无效过滤条件查找."""
        filters = {"invalid_field": "value"}

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            mock_result = MockExecuteResult()
            mock_result.scalars_all_result = []
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await self.repository.find_by(filters)

            assert result == []

    @pytest.mark.asyncio
    async def test_find_one_by_success(self):
        """测试根据条件查找单个记录."""
        filters = {"name": "Test"}
        mock_model = MockModel(id=1, name="Test")

        with patch.object(self.repository, 'find_by') as mock_find:
            mock_find.return_value = [mock_model]

            result = await self.repository.find_one_by(filters)

            assert result == mock_model
            mock_find.assert_called_once_with(filters, limit=1, session=None)

    @pytest.mark.asyncio
    async def test_find_one_by_not_found(self):
        """测试根据条件未找到单个记录."""
        filters = {"name": "NonExistent"}

        with patch.object(self.repository, 'find_by') as mock_find:
            mock_find.return_value = []

            result = await self.repository.find_one_by(filters)

            assert result is None

    @pytest.mark.asyncio
    async def test_find_one_by_with_session(self):
        """测试使用外部会话查找单个记录."""
        mock_session = MockAsyncSession()
        filters = {"name": "Test"}

        with patch.object(self.repository, 'find_by') as mock_find:
            mock_find.return_value = [MockModel(id=1)]

            result = await self.repository.find_one_by(filters, session=mock_session)

            assert result is not None
            mock_find.assert_called_once_with(filters, limit=1, session=mock_session)

    @pytest.mark.asyncio
    async def test_count_success(self):
        """测试统计记录数量."""
        mock_models = [MockModel(id=1), MockModel(id=2), MockModel(id=3)]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            mock_result = MockExecuteResult()
            mock_result.scalars_all_result = mock_models
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await self.repository.count()

            assert result == 3

    @pytest.mark.asyncio
    async def test_count_with_filters(self):
        """测试带过滤条件统计记录数量."""
        filters = {"name": "Test"}
        mock_models = [MockModel(id=1)]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            mock_result = MockExecuteResult()
            mock_result.scalars_all_result = mock_models
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await self.repository.count(filters)

            assert result == 1

    @pytest.mark.asyncio
    async def test_count_with_session(self):
        """测试使用外部会话统计记录数量."""
        mock_session = MockAsyncSession()

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            # 因为传入了session，不应该调用get_async_session
            result = await self.repository.count(session=mock_session)

            # 结果应该是一个整数
            assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_exists_true(self):
        """测试记录存在（返回True）."""
        with patch.object(self.repository, 'count') as mock_count:
            mock_count.return_value = 5

            result = await self.repository.exists({"name": "Test"})

            assert result is True
            mock_count.assert_called_once_with({"name": "Test"}, session=None)

    @pytest.mark.asyncio
    async def test_exists_false(self):
        """测试记录不存在（返回False）."""
        with patch.object(self.repository, 'count') as mock_count:
            mock_count.return_value = 0

            result = await self.repository.exists({"name": "NonExistent"})

            assert result is False

    @pytest.mark.asyncio
    async def test_exists_with_session(self):
        """测试使用外部会话检查记录存在."""
        mock_session = MockAsyncSession()

        with patch.object(self.repository, 'count') as mock_count:
            mock_count.return_value = 1

            result = await self.repository.exists({"name": "Test"}, session=mock_session)

            assert result is True
            mock_count.assert_called_once_with({"name": "Test"}, session=mock_session)

    @pytest.mark.asyncio
    async def test_bulk_create_success(self):
        """测试批量创建记录成功."""
        objects_data = [
            {"name": "Test1", "email": "test1@example.com"},
            {"name": "Test2", "email": "test2@example.com"},
        ]

        result = await self.repository.bulk_create(objects_data)

        assert len(result) == 2
        assert all(isinstance(obj, MockModel) for obj in result)
        assert result[0].name == "Test1"
        assert result[1].name == "Test2"

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(self):
        """测试批量创建空列表."""
        result = await self.repository.bulk_create([])

        assert result == []

    @pytest.mark.asyncio
    async def test_bulk_create_with_session(self):
        """测试使用外部会话批量创建."""
        mock_session = MockAsyncSession()
        objects_data = [{"name": "Test"}]

        result = await self.repository.bulk_create(objects_data, session=mock_session)

        assert len(result) == 1
        assert result[0].name == "Test"

    @pytest.mark.asyncio
    async def test_bulk_update_success(self):
        """测试批量更新记录成功."""
        updates = [
            {"id": 1, "name": "Updated1"},
            {"id": 2, "name": "Updated2"},
        ]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 模拟每次更新影响1行
            mock_result = MockExecuteResult()
            mock_result.rowcount = 1
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await self.repository.bulk_update(updates)

            assert result == 2

    @pytest.mark.asyncio
    async def test_bulk_update_empty_list(self):
        """测试批量更新空列表."""
        result = await self.repository.bulk_update([])

        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_update_without_id(self):
        """测试批量更新不包含ID的记录."""
        updates = [{"name": "Updated"}]  # 没有id字段

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await self.repository.bulk_update(updates)

            assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_update_with_session(self):
        """测试使用外部会话批量更新."""
        mock_session = MockAsyncSession()
        updates = [{"id": 1, "name": "Updated"}]

        mock_result = MockExecuteResult()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await self.repository.bulk_update(updates, session=mock_session)

        assert result == 1

    @pytest.mark.asyncio
    async def test_bulk_delete_success(self):
        """测试批量删除记录成功."""
        ids = [1, 2, 3]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            mock_result = MockExecuteResult()
            mock_result.rowcount = 3
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await self.repository.bulk_delete(ids)

            assert result == 3

    @pytest.mark.asyncio
    async def test_bulk_delete_empty_list(self):
        """测试批量删除空列表."""
        result = await self.repository.bulk_delete([])

        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_delete_with_session(self):
        """测试使用外部会话批量删除."""
        mock_session = MockAsyncSession()
        ids = [1, 2]

        mock_result = MockExecuteResult()
        mock_result.rowcount = 2
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await self.repository.bulk_delete(ids, session=mock_session)

        assert result == 2

    @pytest.mark.asyncio
    async def test_execute_in_transaction_success(self):
        """测试在事务中执行多个操作成功."""
        async def operation1(session):
            return "result1"

        async def operation2(session):
            return "result2"

        operations = [operation1, operation2]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await self.repository.execute_in_transaction(operations)

            assert result == ["result1", "result2"]
            assert mock_session.committed is True
            assert mock_session.rolled_back is False

    @pytest.mark.asyncio
    async def test_execute_in_transaction_with_session(self):
        """测试使用外部会话在事务中执行操作."""
        mock_session = MockAsyncSession()

        async def operation(session):
            return "result"

        result = await self.repository.execute_in_transaction([operation], session=mock_session)

        assert result == ["result"]
        assert mock_session.committed is True

    @pytest.mark.asyncio
    async def test_execute_in_transaction_with_sqlalchemy_error(self):
        """测试事务中发生SQLAlchemy错误."""
        async def failing_operation(session):
            raise SQLAlchemyError("Database error")

        operations = [failing_operation]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with pytest.raises(SQLAlchemyError):
                await self.repository.execute_in_transaction(operations)

            assert mock_session.committed is False
            assert mock_session.rolled_back is True

    @pytest.mark.asyncio
    async def test_execute_in_transaction_with_database_error(self):
        """测试事务中发生数据库错误."""
        async def failing_operation(session):
            raise DatabaseError("Database connection error", None, None)

        operations = [failing_operation]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with pytest.raises(DatabaseError):
                await self.repository.execute_in_transaction(operations)

            assert mock_session.rolled_back is True

    @pytest.mark.asyncio
    async def test_execute_in_transaction_with_connection_error(self):
        """测试事务中发生连接错误."""
        async def failing_operation(session):
            raise ConnectionError("Connection lost")

        operations = [failing_operation]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with pytest.raises(ConnectionError):
                await self.repository.execute_in_transaction(operations)

            assert mock_session.rolled_back is True

    @pytest.mark.asyncio
    async def test_execute_in_transaction_with_timeout_error(self):
        """测试事务中发生超时错误."""
        async def failing_operation(session):
            raise TimeoutError("Operation timeout")

        operations = [failing_operation]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with pytest.raises(TimeoutError):
                await self.repository.execute_in_transaction(operations)

            assert mock_session.rolled_back is True

    @pytest.mark.asyncio
    async def test_execute_in_transaction_with_other_exception(self):
        """测试事务中发生其他异常（不应该回滚）."""
        async def failing_operation(session):
            raise ValueError("Invalid value")

        operations = [failing_operation]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # ValueError不在捕获的异常列表中，应该正常抛出但不回滚
            with pytest.raises(ValueError):
                await self.repository.execute_in_transaction(operations)

            # 注意：根据代码实现，非指定异常不会触发回滚
            assert mock_session.committed is False  # 因为异常导致commit没有执行

    @pytest.mark.asyncio
    async def test_get_related_data_implementation(self):
        """测试抽象方法的具体实现."""
        result = await self.repository.get_related_data(1, "test_relation")

        assert result == {"obj_id": 1, "relation_name": "test_relation"}

    @pytest.mark.asyncio
    async def test_get_related_data_with_session(self):
        """测试带会话的关联数据获取."""
        mock_session = MockAsyncSession()

        result = await self.repository.get_related_data(1, "test_relation", session=mock_session)

        assert result == {"obj_id": 1, "relation_name": "test_relation"}

    @pytest.mark.asyncio
    async def test_integration_create_and_get(self):
        """集成测试：创建记录并获取."""
        obj_data = {"name": "Integration Test", "email": "integration@test.com"}

        # 创建记录
        created = await self.repository.create(obj_data)
        assert created is not None
        assert created.name == "Integration Test"

        # 根据ID获取记录
        with patch.object(self.repository, 'find_one_by') as mock_find:
            mock_find.return_value = created

            retrieved = await self.repository.get_by_id(created.id)
            assert retrieved == created

    @pytest.mark.asyncio
    async def test_integration_bulk_operations(self):
        """集成测试：批量操作."""
        # 批量创建
        objects_data = [
            {"name": f"Test{i}", "email": f"test{i}@example.com"}
            for i in range(5)
        ]

        created = await self.repository.bulk_create(objects_data)
        assert len(created) == 5

        # 批量更新
        updates = [
            {"id": i + 1, "name": f"Updated{i}"} for i in range(5)
        ]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            mock_result = MockExecuteResult()
            mock_result.rowcount = 1
            mock_session.execute = AsyncMock(return_value=mock_result)

            updated_count = await self.repository.bulk_update(updates)
            assert updated_count == 5

        # 批量删除
        ids = [1, 2, 3, 4, 5]

        with patch.object(self.db_manager, 'get_async_session') as mock_get_session:
            mock_session = MockAsyncSession()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            mock_result = MockExecuteResult()
            mock_result.rowcount = 5
            mock_session.execute = AsyncMock(return_value=mock_result)

            deleted_count = await self.repository.bulk_delete(ids)
            assert deleted_count == 5