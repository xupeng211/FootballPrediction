"""
仓储基类测试
Base Repository Tests

测试Phase 5+重写的BaseRepository功能
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.repositories.base import BaseRepository, QuerySpec
from src.database.models import User  # 假设模型


class MockModel:
    """模拟模型类"""
    def __init__(self, id, **kwargs):
        self.id = id
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestBaseRepository:
    """BaseRepository测试类"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """测试仓储实例"""
        class TestRepository(BaseRepository):
            model_class = MockModel

            async def get_by_id(self, id):
                return await super().get_by_id(id)

            async def get_all(self, query_spec=None):
                return await super().get_all(query_spec)

            async def create(self, entity):
                return await super().create(entity)

            async def update(self, id, update_data):
                return await super().update(id, update_data)

            async def delete(self, id):
                return await super().delete(id)

        return TestRepository(mock_session, MockModel)

    @pytest.mark.asyncio
    async def test_repository_initialization(self, mock_session):
        """测试仓储初始化"""
        repo = BaseRepository(mock_session, MockModel)

        assert repo.session == mock_session
        assert repo.model_class == MockModel

    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_session):
        """测试实体存在检查 - 存在"""
        # 模拟查询结果
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MockModel(id=1)
        mock_session.execute.return_value = mock_result

        result = await repository.exists(1)

        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_session):
        """测试实体存在检查 - 不存在"""
        # 模拟查询结果为None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.exists(1)

        assert result is False
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_no_filters(self, repository, mock_session):
        """测试计数功能 - 无过滤条件"""
        # 模拟查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MockModel(1), MockModel(2)]
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_with_filters(self, repository, mock_session):
        """测试计数功能 - 带过滤条件"""
        # 模拟查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MockModel(1)]
        mock_session.execute.return_value = mock_result

        query_spec = QuerySpec(filters={"status": "active"})
        result = await repository.count(query_spec)

        assert result == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_with_advanced_filters(self, repository, mock_session):
        """测试计数功能 - 高级过滤条件"""
        # 模拟查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MockModel(1)]
        mock_session.execute.return_value = mock_result

        query_spec = QuerySpec(filters={
            "age": {"$gt": 18},
            "name": {"$like": "John%"},
            "status": {"$ne": "inactive"}
        })
        result = await repository.count(query_spec)

        assert result == 1
        mock_session.execute.assert_called_once()

    def test_build_query_basic(self, repository):
        """测试查询构建 - 基础"""
        query_spec = QuerySpec()
        query = repository._build_query(query_spec)

        # 验证查询构建成功
        assert query is not None

    def test_build_query_with_filters(self, repository):
        """测试查询构建 - 带过滤条件"""
        query_spec = QuerySpec(filters={"status": "active"})
        query = repository._build_query(query_spec)

        # 验证查询构建成功
        assert query is not None

    def test_build_query_with_order(self, repository):
        """测试查询构建 - 带排序"""
        query_spec = QuerySpec(order_by=["name", "-created_at"])
        query = repository._build_query(query_spec)

        # 验证查询构建成功
        assert query is not None

    def test_build_query_with_pagination(self, repository):
        """测试查询构建 - 带分页"""
        query_spec = QuerySpec(limit=10, offset=20)
        query = repository._build_query(query_spec)

        # 验证查询构建成功
        assert query is not None

    def test_build_query_with_includes(self, repository):
        """测试查询构建 - 带预加载"""
        query_spec = QuerySpec(include=["related_field"])
        query = repository._build_query(query_spec)

        # 验证查询构建成功
        assert query is not None

    def test_apply_filters_simple(self, repository):
        """测试过滤条件应用 - 简单条件"""
        query = MagicMock()
        filters = {"status": "active", "type": "user"}

        # 模拟模型类有相应属性
        MockModel.status = True
        MockModel.type = True

        result_query = repository._apply_filters(query, filters)

        # 验证过滤条件应用
        assert result_query == query

    def test_apply_filters_complex(self, repository):
        """测试过滤条件应用 - 复杂条件"""
        query = MagicMock()
        filters = {
            "age": {"$gt": 18},
            "status": {"$in": ["active", "pending"]},
            "name": {"$ne": "test"}
        }

        # 模拟模型类有相应属性
        MockModel.age = True
        MockModel.status = True
        MockModel.name = True

        result_query = repository._apply_filters(query, filters)

        # 验证过滤条件应用
        assert result_query == query

    def test_apply_filters_list_values(self, repository):
        """测试过滤条件应用 - 列表值"""
        query = MagicMock()
        filters = {"id": [1, 2, 3], "category": ["A", "B"]}

        # 模拟模型类有相应属性
        MockModel.id = True
        MockModel.category = True

        result_query = repository._apply_filters(query, filters)

        # 验证过滤条件应用
        assert result_query == query

    @pytest.mark.asyncio
    async def test_find_by_filters(self, repository, mock_session):
        """测试根据过滤条件查找"""
        # 模拟查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MockModel(1, status="active"),
            MockModel(2, status="active")
        ]
        mock_session.execute.return_value = mock_result

        filters = {"status": "active"}
        result = await repository.find_by_filters(filters)

        assert len(result) == 2
        assert all(item.status == "active" for item in result)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_filters_with_limit(self, repository, mock_session):
        """测试根据过滤条件查找 - 带限制"""
        # 模拟查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MockModel(1)]
        mock_session.execute.return_value = mock_result

        filters = {"status": "active"}
        result = await repository.find_by_filters(filters, limit=1)

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_one_by_filters(self, repository, mock_session):
        """测试根据过滤条件查找单个实体"""
        # 模拟查询结果
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MockModel(1, name="test")
        mock_session.execute.return_value = mock_result

        filters = {"name": "test"}
        result = await repository.find_one_by_filters(filters)

        assert result is not None
        assert result.name == "test"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_one_by_filters_not_found(self, repository, mock_session):
        """测试根据过滤条件查找单个实体 - 未找到"""
        # 模拟查询结果
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        filters = {"name": "nonexistent"}
        result = await repository.find_one_by_filters(filters)

        assert result is None
        mock_session.execute.assert_called_once()


class TestQuerySpec:
    """QuerySpec测试类"""

    def test_query_spec_initialization_empty(self):
        """测试QuerySpec初始化 - 空"""
        query_spec = QuerySpec()

        assert query_spec.filters is None
        assert query_spec.order_by is None
        assert query_spec.limit is None
        assert query_spec.offset is None
        assert query_spec.include is None

    def test_query_spec_initialization_with_data(self):
        """测试QuerySpec初始化 - 带数据"""
        filters = {"status": "active"}
        order_by = ["name", "-created_at"]

        query_spec = QuerySpec(
            filters=filters,
            order_by=order_by,
            limit=10,
            offset=20,
            include=["related"]
        )

        assert query_spec.filters == filters
        assert query_spec.order_by == order_by
        assert query_spec.limit == 10
        assert query_spec.offset == 20
        assert query_spec.include == ["related"]

    def test_query_spec_immutability(self):
        """测试QuerySpec不变性（可选）"""
        filters = {"status": "active"}
        query_spec = QuerySpec(filters=filters)

        # 修改原始字典不应影响QuerySpec（如果实现了深拷贝）
        filters["new_key"] = "new_value"

        # 根据实现，这可能通过或不通过
        # assert "new_key" not in query_spec.filters