"""
仓储模式单元测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.database.repositories.base import BaseRepository, RepositoryConfig, QueryResult
from src.database.repositories.match import MatchRepository
from src.database.repositories.prediction import PredictionRepository


class TestRepositoryConfig:
    """RepositoryConfig测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = RepositoryConfig()
        assert config.default_page_size == 20
        assert config.max_page_size == 100
        assert config.enable_cache is True
        assert config.cache_ttl == 300
        assert config.enable_query_logging is False

    def test_custom_config(self):
        """测试自定义配置"""
        config = RepositoryConfig(
            default_page_size=10,
            max_page_size=50,
            enable_cache=False,
            cache_ttl=600,
            enable_query_logging=True,
        )
        assert config.default_page_size == 10
        assert config.max_page_size == 50
        assert config.enable_cache is False
        assert config.cache_ttl == 600
        assert config.enable_query_logging is True


class TestQueryResult:
    """QueryResult测试"""

    def test_query_result_creation(self):
        """测试查询结果创建"""
        items = ["item1", "item2", "item3"]
        result = QueryResult(
            items=items, total=100, page=1, page_size=10, has_next=True, has_prev=False
        )

        assert result.items == items
        assert result.total == 100
        assert result.page == 1
        assert result.page_size == 10
        assert result.has_next is True
        assert result.has_prev is False

    def test_total_pages_calculation(self):
        """测试总页数计算"""
        # 100条记录，每页20条，应该有5页
        result = QueryResult(
            items=[], total=100, page=1, page_size=20, has_next=True, has_prev=False
        )
        assert result.total_pages == 5

        # 95条记录，每页20条，应该有5页
        result = QueryResult(
            items=[], total=95, page=1, page_size=20, has_next=True, has_prev=False
        )
        assert result.total_pages == 5


@pytest.mark.asyncio
class TestBaseRepository:
    """BaseRepository测试"""

    async def test_create_entity(self):
        """测试创建实体"""
        # 创建模拟session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # 创建测试实体类
        class TestEntity:
            def __init__(self, name):
                self.id = None
                self.name = name

        # 创建仓储
        repo = BaseRepository(mock_session, TestEntity)
        entity = TestEntity("test")

        # 调用创建方法
        result = await repo.create(entity)

        # 验证调用
        mock_session.add.assert_called_once_with(entity)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(entity)
        assert result == entity

    async def test_get_by_id(self):
        """测试根据ID获取实体"""
        # 创建模拟session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = "mock_entity"
        mock_session.execute.return_value = mock_result

        # 创建测试实体类
        class TestEntity:
            id = None

        # 创建仓储
        repo = BaseRepository(mock_session, TestEntity)

        # 调用方法
        result = await repo.get_by_id(1)

        # 验证结果
        assert result == "mock_entity"
        mock_session.execute.assert_called_once()

    async def test_find_with_filters(self):
        """测试根据条件查找"""
        # 创建模拟session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = ["entity1", "entity2"]
        mock_session.execute.return_value = mock_result

        # 创建测试实体类
        class TestEntity:
            name = None
            active = None

        # 创建仓储
        repo = BaseRepository(mock_session, TestEntity)

        # 调用查找方法
        result = await repo.find({"name": "test", "active": True})

        # 验证结果
        assert result == ["entity1", "entity2"]
        mock_session.execute.assert_called_once()

    async def test_paginate(self):
        """测试分页查询"""
        # 创建模拟session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = ["item1", "item2"]
        mock_session.execute.return_value = mock_result

        # 创建计数查询模拟
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 50
        mock_session.execute.side_effect = [mock_count_result, mock_result]

        # 创建测试实体类
        class TestEntity:
            pass

        # 创建仓储
        repo = BaseRepository(mock_session, TestEntity)

        # 调用分页方法
        result = await repo.paginate(page=1, page_size=10)

        # 验证结果
        assert isinstance(result, QueryResult)
        assert result.items == ["item1", "item2"]
        assert result.total == 50
        assert result.page == 1
        assert result.page_size == 10
        assert result.has_next is True
        assert result.has_prev is False

    async def test_count(self):
        """测试统计数量"""
        # 创建模拟session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 25
        mock_session.execute.return_value = mock_result

        # 创建测试实体类
        class TestEntity:
            pass

        # 创建仓储
        repo = BaseRepository(mock_session, TestEntity)

        # 调用统计方法
        result = await repo.count()

        # 验证结果
        assert result == 25
        mock_session.execute.assert_called_once()


@pytest.mark.asyncio
class TestMatchRepository:
    """MatchRepository测试"""

    async def test_get_upcoming_matches(self):
        """测试获取即将到来的比赛"""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # 创建仓储
        repo = MatchRepository(mock_session)

        # 调用方法
        result = await repo.get_upcoming_matches(days=7, limit=10)

        # 验证
        assert isinstance(result, list)
        mock_session.execute.assert_called_once()

    async def test_get_team_matches(self):
        """测试获取球队比赛"""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # 创建仓储
        repo = MatchRepository(mock_session)

        # 调用方法
        result = await repo.get_team_matches(team_id=1, limit=10)

        # 验证
        assert isinstance(result, list)
        mock_session.execute.assert_called_once()


@pytest.mark.asyncio
class TestPredictionRepository:
    """PredictionRepository测试"""

    async def test_get_by_match_id(self):
        """测试根据比赛ID获取预测"""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # 创建仓储
        repo = PredictionRepository(mock_session)

        # 调用方法
        result = await repo.get_by_match_id(match_id=1)

        # 验证
        assert isinstance(result, list)
        mock_session.execute.assert_called_once()

    async def test_get_high_confidence_predictions(self):
        """测试获取高置信度预测"""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # 创建仓储
        repo = PredictionRepository(mock_session)

        # 调用方法
        result = await repo.get_high_confidence_predictions(threshold=0.8, limit=20)

        # 验证
        assert isinstance(result, list)
        mock_session.execute.assert_called_once()

    async def test_bulk_create_predictions(self):
        """测试批量创建预测"""
        mock_session = AsyncMock()
        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # 创建仓储
        repo = PredictionRepository(mock_session)

        # 准备数据
        predictions_data = [
            {"match_id": 1, "user_id": 1, "predicted_result": "home_win"}
        ]

        # 调用方法
        result = await repo.bulk_create_predictions(predictions_data)

        # 验证
        assert isinstance(result, list)
        mock_session.add_all.assert_called_once()
        mock_session.commit.assert_called_once()
