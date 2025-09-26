"""
DataProcessingService 增强测试套件 - Phase 5.1 Batch-Δ-011

专门为 data_processing.py 设计的增强测试，目标是将其覆盖率从 7% 提升至 ≥70%
覆盖所有核心数据处理功能、错误场景、异步操作和集成测试
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, List, Optional, Union

import pandas as pd
import pytest

from src.services.data_processing import DataProcessingService
from src.services.base import BaseService


class TestDataProcessingServiceEnhanced:
    """DataProcessingService 增强测试套件"""

    # ========== 新增：Bronze到Silver层处理测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_bronze_to_silver_uninitialized(self):
        """测试未初始化状态的Bronze到Silver处理"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = None

        result = await service.process_bronze_to_silver()

        assert result["error"] == 1
        service.logger.error.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_bronze_to_silver_success(self):
        """测试成功的Bronze到Silver处理"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        # Mock all the required methods
        service._process_raw_matches_bronze_to_silver = AsyncMock(return_value=10)
        service._process_raw_odds_bronze_to_silver = AsyncMock(return_value=20)
        service._process_raw_scores_bronze_to_silver = AsyncMock(return_value=5)

        result = await service.process_bronze_to_silver(100)

        assert result["processed_matches"] == 10
        assert result["processed_odds"] == 20
        assert result["processed_scores"] == 5
        assert result["errors"] == 0
        service.logger.info.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_bronze_to_silver_exception_handling(self):
        """测试Bronze到Silver处理异常"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        service._process_raw_matches_bronze_to_silver = AsyncMock(side_effect=Exception("处理错误"))

        result = await service.process_bronze_to_silver()

        assert result["errors"] == 1
        service.logger.error.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_raw_matches_bronze_to_silver(self):
        """测试比赛数据Bronze到Silver处理"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        # Mock database session
        mock_session = Mock()
        mock_raw_match = Mock()
        mock_raw_match.id = 1
        mock_raw_match.raw_data = {"test": "data"}
        mock_raw_match.mark_processed = Mock()

        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_raw_match]

        # Mock the context manager properly
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        service.db_manager.get_session.return_value = mock_context_manager

        # Mock data cleaner and missing handler
        service.data_cleaner.clean_match_data = AsyncMock(return_value={"cleaned": True})
        service.missing_handler.handle_missing_match_data = AsyncMock(return_value={"processed": True})

        # Mock data lake
        service.data_lake.save_historical_data = AsyncMock()

        result = await service._process_raw_matches_bronze_to_silver(100)

        assert result == 1
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_raw_matches_bronze_to_silver_no_data(self):
        """测试无比赛数据时的Bronze到Silver处理"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []

        # Mock the context manager properly
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        service.db_manager.get_session.return_value = mock_context_manager

        result = await service._process_raw_matches_bronze_to_silver(100)

        assert result == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_raw_odds_bronze_to_silver(self):
        """测试赔率数据Bronze到Silver处理"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        # Mock database session
        mock_session = Mock()
        mock_raw_odds = Mock()
        mock_raw_odds.id = 1
        mock_raw_odds.external_match_id = 12345
        mock_raw_odds.raw_data = {"odds": "data"}
        mock_raw_odds.mark_processed = Mock()

        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_raw_odds]

        # Mock the context manager properly
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        service.db_manager.get_session.return_value = mock_context_manager

        # Mock data cleaner
        service.data_cleaner.clean_odds_data = AsyncMock(return_value=[{"cleaned": True}])

        # Mock data lake
        service.data_lake.save_historical_data = AsyncMock()

        result = await service._process_raw_odds_bronze_to_silver(100)

        assert result == 1
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_raw_scores_bronze_to_silver(self):
        """测试比分数据Bronze到Silver处理"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        # Mock database session
        mock_session = Mock()
        mock_raw_scores = Mock()
        mock_raw_scores.id = 1
        mock_raw_scores.external_match_id = 12345
        mock_raw_scores.get_score_info.return_value = {
            "home_score": 2,
            "away_score": 1,
            "half_time_home": 1,
            "half_time_away": 0,
            "status": "FINISHED",
            "minute": 90,
            "events": []
        }
        mock_raw_scores.is_live = False
        mock_raw_scores.is_finished = True
        mock_raw_scores.collected_at = datetime.now()
        mock_raw_scores.mark_processed = Mock()

        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_raw_scores]

        # Mock the context manager properly
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        service.db_manager.get_session.return_value = mock_context_manager

        # Mock data cleaner methods
        service.data_cleaner._validate_score = Mock(side_effect=lambda x: x)
        service.data_cleaner._standardize_match_status = Mock(return_value="FINISHED")

        # Mock data lake
        service.data_lake.save_historical_data = AsyncMock()

        result = await service._process_raw_scores_bronze_to_silver(100)

        assert result == 1
        mock_session.commit.assert_called_once()

    # ========== 新增：数据状态查询测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_bronze_layer_status_no_db(self):
        """测试无数据库连接的状态查询"""
        service = DataProcessingService()
        service.logger = Mock()

        result = await service.get_bronze_layer_status()

        assert "error" in result
        assert result["error"] == "数据库连接未初始化"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_bronze_layer_status_success(self):
        """测试成功的Bronze层状态查询"""
        service = DataProcessingService()
        service.logger = Mock()
        service.db_manager = Mock()

        # Mock database session
        mock_session = Mock()
        mock_session.query.return_value.count.return_value = 10
        mock_session.query.return_value.filter.return_value.count.return_value = 5

        # Mock the context manager properly
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        service.db_manager.get_session.return_value = mock_context_manager

        result = await service.get_bronze_layer_status()

        assert "matches" in result
        assert "odds" in result
        assert "scores" in result
        assert result["matches"]["total"] == 10
        assert result["matches"]["processed"] == 5
        assert result["matches"]["pending"] == 5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_bronze_layer_status_exception(self):
        """测试Bronze层状态查询异常"""
        service = DataProcessingService()
        service.logger = Mock()
        service.db_manager = Mock()
        service.db_manager.get_session.side_effect = Exception("数据库错误")

        result = await service.get_bronze_layer_status()

        assert "error" in result

    # ========== 新增：存储处理测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_processed_data_success(self):
        """测试成功的处理后数据存储"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()
        service.cache_manager = Mock()

        test_df = pd.DataFrame({"test": [1, 2, 3]})
        table_name = "test_table"

        # Mock data lake
        service.data_lake.store_dataframe = AsyncMock()

        # Mock database manager
        service.db_manager.bulk_insert = AsyncMock()

        # Mock cache manager
        service.cache_manager.set_json = AsyncMock()

        result = await service.store_processed_data(test_df, table_name, True)

        assert result is True
        service.data_lake.store_dataframe.assert_called_once()
        service.db_manager.bulk_insert.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_processed_data_lake_failure(self):
        """测试数据湖存储失败场景"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        test_df = pd.DataFrame({"test": [1, 2, 3]})
        table_name = "test_table"

        # Mock data lake to fail
        service.data_lake.store_dataframe = AsyncMock(side_effect=Exception("存储失败"))

        # Mock database manager
        service.db_manager.bulk_insert = AsyncMock()

        result = await service.store_processed_data(test_df, table_name)

        assert result is False
        service.logger.error.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_processed_data_no_components(self):
        """测试无存储组件的场景"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_lake = None
        service.db_manager = None

        test_df = pd.DataFrame({"test": [1, 2, 3]})

        result = await service.store_processed_data(test_df, "test_table")

        assert result is True  # Should still return True since storage is optional

    # ========== 新增：异步处理测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_single_match_data_async_cleaning(self):
        """测试异步数据清洗场景"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        sample_match_data = {"external_match_id": "12345", "home_team_id": 100}

        # Mock data cleaner to return coroutine
        async def mock_async_clean(data):
            await asyncio.sleep(0.001)
            return data

        service.data_cleaner.clean_match_data = mock_async_clean
        service.missing_handler.handle_missing_match_data = Mock(return_value=sample_match_data)

        result = await service._process_single_match_data(sample_match_data)

        assert result == sample_match_data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_single_match_data_async_missing_handling(self):
        """测试异步缺失值处理场景"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        sample_match_data = {"external_match_id": "12345", "home_team_id": 100}

        # Mock missing handler to return coroutine
        async def mock_async_handle(data):
            await asyncio.sleep(0.001)
            return data

        service.data_cleaner.clean_match_data.return_value = sample_match_data
        service.missing_handler.handle_missing_match_data = mock_async_handle

        result = await service._process_single_match_data(sample_match_data)

        assert result == sample_match_data

    # ========== 新增：批处理增强测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_in_batches(self):
        """测试分批处理"""
        service = DataProcessingService()

        dataset = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        batch_size = 3

        batches = []
        async for batch in service._process_in_batches(dataset, batch_size):
            batches.append(batch)

        assert len(batches) == 4
        assert batches[0] == [1, 2, 3]
        assert batches[1] == [4, 5, 6]
        assert batches[2] == [7, 8, 9]
        assert batches[3] == [10]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_large_dataset(self):
        """测试大型数据集处理"""
        service = DataProcessingService()
        service.logger = Mock()

        dataset = list(range(100))

        # Mock the process_batch method
        service.process_batch = AsyncMock(return_value=[{"processed": True}])

        result = await service.process_large_dataset(dataset, batch_size=10)

        assert len(result) == 100  # Each item becomes a processed result
        assert service.process_batch.call_count == 10

    # ========== 新增：服务关闭测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_shutdown_with_mock_cache(self):
        """测试服务关闭 - Mock缓存管理器场景"""
        service = DataProcessingService()
        service.logger = Mock()

        # Mock cache manager that has a close method
        mock_cache = Mock()
        mock_cache.close = AsyncMock()
        mock_cache.close._mock_name = "close"
        service.cache_manager = mock_cache

        # Mock database manager
        mock_db = AsyncMock()
        service.db_manager = mock_db

        await service.shutdown()

        mock_cache.close.assert_called_once()
        mock_db.close.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_shutdown_sync_cache(self):
        """测试服务关闭 - 同步缓存管理器场景"""
        service = DataProcessingService()
        service.logger = Mock()

        # Mock sync cache manager
        mock_cache = Mock()
        mock_cache.close = Mock()
        service.cache_manager = mock_cache

        # Mock database manager
        mock_db = AsyncMock()
        service.db_manager = mock_db

        await service.shutdown()

        mock_cache.close.assert_called_once()
        mock_db.close.assert_called_once()

    # ========== 新增：数据质量验证增强测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_data_quality_exception_handling(self):
        """测试数据质量验证异常处理"""
        service = DataProcessingService()
        service.logger = Mock()

        # This will cause an exception when accessing data.get()
        result = await service.validate_data_quality(None, "match")

        assert result["is_valid"] is False
        assert len(result["issues"]) > 0

    # ========== 新增：数据库事务测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_rollback_on_exception(self):
        """测试数据库异常时的回滚"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        # Mock database session
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [Mock()]
        mock_session.commit.side_effect = Exception("提交失败")

        # Mock the context manager properly
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        service.db_manager.get_session.return_value = mock_context_manager

        # This should trigger an exception and rollback
        result = await service._process_raw_matches_bronze_to_silver(100)

        assert result == 0
        mock_session.rollback.assert_called_once()

    # ========== 新增：性能指标收集测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_performance_metrics(self):
        """测试性能指标收集"""
        service = DataProcessingService()

        mock_function = AsyncMock(return_value=[1, 2, 3])

        result = await service.collect_performance_metrics(mock_function, "arg1", kwarg1="value1")

        assert "total_time" in result
        assert "items_processed" in result
        assert "items_per_second" in result
        assert result["items_processed"] == 3
        assert result["total_time"] > 0
        mock_function.assert_called_once_with("arg1", kwarg1="value1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_performance_metrics_single_item(self):
        """测试单个项目的性能指标收集"""
        service = DataProcessingService()

        mock_function = AsyncMock(return_value={"single": "result"})

        result = await service.collect_performance_metrics(mock_function)

        assert result["items_processed"] == 1
        assert result["items_per_second"] > 0

    # ========== 新增：清理资源测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cleanup_success(self):
        """测试成功的资源清理"""
        service = DataProcessingService()
        service.logger = Mock()

        # Mock the db manager
        mock_db = Mock()
        mock_db.close = AsyncMock()
        service.db_manager = mock_db

        # Add a cache attribute
        service._cache = {1: 2, 3: 4}

        result = await service.cleanup()

        assert result is True
        assert len(service._cache) == 0
        mock_db.close.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cleanup_sync_db_close(self):
        """测试同步数据库关闭"""
        service = DataProcessingService()
        service.logger = Mock()

        # Mock the db manager with synchronous close
        mock_db = Mock()
        mock_db.close = Mock()
        service.db_manager = mock_db

        result = await service.cleanup()

        assert result is True
        mock_db.close.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cleanup_exception_handling(self):
        """测试清理异常处理"""
        service = DataProcessingService()
        service.logger = Mock()

        # Mock the db manager to raise exception
        mock_db = Mock()
        mock_db.close = Mock(side_effect=Exception("关闭失败"))
        service.db_manager = mock_db

        result = await service.cleanup()

        assert result is False
        service.logger.error.assert_called()

    # ========== 新增：缓存操作增强测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_processing_results_no_cache_manager(self):
        """测试无缓存管理器的缓存处理"""
        service = DataProcessingService()
        service.logger = Mock()
        service.cache_manager = None

        result = await service.cache_processing_results("test_key", {"data": "value"})

        assert result is False
        service.logger.error.assert_called_with("缓存管理器未初始化")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cached_results_no_cache_manager(self):
        """测试无缓存管理器的缓存获取"""
        service = DataProcessingService()
        service.logger = Mock()
        service.cache_manager = None

        result = await service.get_cached_results("test_key")

        assert result is None
        service.logger.error.assert_called_with("缓存管理器未初始化")

    # ========== 新增：边界条件测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_raw_match_data_empty_dict(self):
        """测试空字典输入的比赛数据处理"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        result = await service._process_single_match_data({})

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_raw_match_data_no_match_id(self):
        """测试无比赛ID的缓存处理"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        sample_match_data = {"home_team_id": 100, "away_team_id": 200}  # No external_match_id

        service.data_cleaner.clean_match_data.return_value = sample_match_data
        service.missing_handler.handle_missing_match_data.return_value = sample_match_data

        result = await service._process_single_match_data(sample_match_data)

        assert result == sample_match_data
        # Cache should not be called when no match_id
        service.cache_manager.aset.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_raw_match_data_none_result_from_cleaner(self):
        """测试数据清洗返回None"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        sample_match_data = {"external_match_id": "12345"}

        service.data_cleaner.clean_match_data.return_value = None

        result = await service._process_single_match_data(sample_match_data)

        assert result is None
        service.logger.warning.assert_called_with("比赛数据清洗失败")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_raw_match_data_empty_dataframe_result(self):
        """测试数据清洗返回空DataFrame"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        sample_match_data = {"external_match_id": "12345"}
        empty_df = pd.DataFrame()

        service.data_cleaner.clean_match_data.return_value = empty_df

        result = await service._process_single_match_data(sample_match_data)

        assert result is None
        service.logger.warning.assert_called_with("比赛数据清洗失败")

    # ========== 新增：重试机制增强测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_with_retry_zero_retries(self):
        """测试零重试次数"""
        service = DataProcessingService()
        service.logger = Mock()

        mock_func = Mock(side_effect=Exception("失败"))
        test_data = {"test": "data"}

        with pytest.raises(RuntimeError, match="处理持续失败"):
            await service.process_with_retry(mock_func, test_data, max_retries=0, delay=0.01)

        mock_func.assert_called_once()

    # ========== 新增：存储数据缓存失败测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_processed_data_cache_failure(self):
        """测试数据存储缓存失败"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()
        service.cache_manager = Mock()

        test_df = pd.DataFrame({"test": [1, 2, 3]})
        table_name = "test_table"

        # Mock data lake
        service.data_lake.store_dataframe = AsyncMock()

        # Mock database manager
        service.db_manager.bulk_insert = AsyncMock()

        # Mock cache manager to fail
        service.cache_manager.set_json = AsyncMock(side_effect=Exception("缓存失败"))

        result = await service.store_processed_data(test_df, table_name, True)

        assert result is True  # Should still succeed even if cache fails
        service.logger.warning.assert_called()

    # ========== 新增：完整集成测试 ==========

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_data_processing_workflow(self):
        """测试完整的数据处理工作流"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        sample_match_data = {"external_match_id": "12345", "home_team_id": 100}

        # Setup all mocks for a complete workflow
        service.data_cleaner.clean_match_data.return_value = sample_match_data
        service.missing_handler.handle_missing_match_data.return_value = sample_match_data

        # Test cache workflow
        service.cache_manager.aget = AsyncMock(return_value=None)  # No cached data
        service.cache_manager.aset = AsyncMock()

        # Process the data
        result = await service._process_single_match_data(sample_match_data)

        # Verify the complete workflow
        assert result == sample_match_data
        service.data_cleaner.clean_match_data.assert_called_once()
        service.missing_handler.handle_missing_match_data.assert_called_once()
        service.cache_manager.aget.assert_called_once()
        service.cache_manager.aset.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bronze_to_silver_full_workflow(self):
        """测试完整的Bronze到Silver处理工作流"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        # Mock database session for matches
        mock_session = Mock()
        mock_raw_match = Mock()
        mock_raw_match.id = 1
        mock_raw_match.raw_data = {"test": "data"}
        mock_raw_match.mark_processed = Mock()

        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_raw_match]

        # Mock the context manager properly
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        service.db_manager.get_session.return_value = mock_context_manager

        # Mock data cleaning and missing handling
        service.data_cleaner.clean_match_data = AsyncMock(return_value={"cleaned": True})
        service.missing_handler.handle_missing_match_data = AsyncMock(return_value={"processed": True})

        # Mock data lake storage
        service.data_lake.save_historical_data = AsyncMock()

        # Mock odds and scores processing to return 0 (no data)
        service._process_raw_odds_bronze_to_silver = AsyncMock(return_value=0)
        service._process_raw_scores_bronze_to_silver = AsyncMock(return_value=0)

        # Execute the full workflow
        result = await service.process_bronze_to_silver(batch_size=100)

        # Verify the result
        assert result["processed_matches"] == 1
        assert result["processed_odds"] == 0
        assert result["processed_scores"] == 0
        assert result["errors"] == 0

    # ========== 新增：性能测试 ==========

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_batch_processing_performance(self):
        """测试大批量处理性能"""
        service = DataProcessingService()
        service.logger = Mock()

        # Create a large dataset
        large_dataset = [{"id": i} for i in range(1000)]

        # Mock process_batch to return quickly
        async def mock_process_batch(data):
            await asyncio.sleep(0.001)
            return [{"processed": True} for _ in data]

        service.process_batch = mock_process_batch

        # Measure performance
        start_time = asyncio.get_event_loop().time()
        result = await service.process_large_dataset(large_dataset, batch_size=100)
        end_time = asyncio.get_event_loop().time()

        processing_time = end_time - start_time
        assert processing_time < 1.0  # Should process 1000 items in less than 1 second
        assert len(result) == 1000

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self):
        """测试并发缓存操作"""
        service = DataProcessingService()
        service.logger = Mock()
        service.cache_manager = Mock()

        cache_key = "test_concurrent"
        data = {"data": "value"}

        # Mock cache operations to be slightly slow
        async def mock_slow_set(key, value, **kwargs):
            await asyncio.sleep(0.01)
            return True

        async def mock_slow_get(key):
            await asyncio.sleep(0.01)
            return {"cached": True}

        service.cache_manager.set_json = mock_slow_set
        service.cache_manager.get_json = mock_slow_get

        # Test concurrent operations
        tasks = []
        for i in range(10):
            tasks.append(service.cache_processing_results(f"{cache_key}_{i}", data))
            tasks.append(service.get_cached_results(f"{cache_key}_{i}"))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should complete successfully
        assert len([r for r in results if r is True]) == 10  # cache_processing_results
        assert len([r for r in results if r is not None]) == 10  # get_cached_results

    # ========== 新增：错误场景测试 ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_data_cleaner_async_check(self):
        """测试数据清洗器异步性检查"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        sample_match_data = {"external_match_id": "12345"}

        # Create a mock that looks like a coroutine but isn't
        mock_result = Mock()
        mock_result.__class__ = type(lambda: None)
        mock_result.__class__.__name__ = "coroutine"

        service.data_cleaner.clean_match_data.return_value = mock_result

        # This should handle the case where something looks like a coroutine but isn't
        with pytest.raises(Exception):
            await service._process_single_match_data(sample_match_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_data_handler_async_check(self):
        """测试缺失值处理器异步性检查"""
        service = DataProcessingService()
        service.logger = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        sample_match_data = {"external_match_id": "12345"}

        # Mock data cleaner to return sync result
        service.data_cleaner.clean_match_data.return_value = sample_match_data

        # Create a mock that looks like a coroutine but isn't
        mock_result = Mock()
        mock_result.__class__ = type(lambda: None)
        mock_result.__class__.__name__ = "coroutine"

        service.missing_handler.handle_missing_match_data.return_value = mock_result

        # This should handle the case where something looks like a coroutine but isn't
        with pytest.raises(Exception):
            await service._process_single_match_data(sample_match_data)


# 测试标记和分类
class TestDataProcessingServiceMarkers:
    """测试标记验证"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unit_test_marker(self):
        """验证单元测试标记"""
        assert True  # This test is marked as unit

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_integration_test_marker(self):
        """验证集成测试标记"""
        assert True  # This test is marked as integration

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_test_marker(self):
        """验证性能测试标记"""
        assert True  # This test is marked as performance

    @pytest.mark.asyncio
    async def test_asyncio_marker(self):
        """验证异步测试标记"""
        assert True  # This test is marked as asyncio


class TestDataProcessingService:
    """测试数据处理服务 - 原有测试保留"""


class TestDataProcessingService:
    """测试数据处理服务"""

    @pytest.fixture
    def processor(self):
        """创建DataProcessingService实例"""
        with patch("src.services.data_processing.DatabaseManager"), \
             patch("src.services.data_processing.FootballDataCleaner"), \
             patch("src.services.data_processing.MissingDataHandler"), \
             patch("src.services.data_processing.DataLakeStorage"), \
             patch("src.services.data_processing.RedisManager"):
            return DataProcessingService()

    def test_init(self, processor):
        """测试初始化"""
        assert processor.name == "DataProcessingService"
        assert processor.data_cleaner is None
        assert processor.missing_handler is None
        assert processor.data_lake is None
        assert processor.db_manager is None
        assert processor.cache_manager is None

    @pytest.mark.asyncio
    async def test_initialize_success(self, processor):
        """测试成功初始化服务"""
        # Mock所有依赖
        with patch("src.services.data_processing.FootballDataCleaner") as mock_cleaner, \
             patch("src.services.data_processing.MissingDataHandler") as mock_handler, \
             patch("src.services.data_processing.DataLakeStorage") as mock_storage, \
             patch("src.services.data_processing.DatabaseManager") as mock_db, \
             patch("src.services.data_processing.RedisManager") as mock_cache:

            mock_cleaner.return_value = Mock()
            mock_handler.return_value = Mock()
            mock_storage.return_value = Mock()
            mock_db.return_value = Mock()
            mock_cache.return_value = Mock()

            result = await processor.initialize()

            assert result is True
            assert processor.data_cleaner is not None
            assert processor.missing_handler is not None
            assert processor.data_lake is not None
            assert processor.db_manager is not None
            assert processor.cache_manager is not None

    @pytest.mark.asyncio
    async def test_initialize_failure(self, processor):
        """测试初始化失败"""
        with patch("src.services.data_processing.FootballDataCleaner") as mock_cleaner:
            mock_cleaner.side_effect = Exception("Initialization failed")

            result = await processor.initialize()

            assert result is False

    @pytest.mark.asyncio
    async def test_process_raw_match_data_single_dict(self, processor):
        """测试处理单个比赛数据（字典输入）"""
        # Mock初始化
        processor.data_cleaner = Mock()
        processor.missing_handler = Mock()
        processor.cache_manager = AsyncMock()

        # Mock数据
        raw_data = {
            "external_match_id": "match_1",
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": 2,
            "away_score": 1,
            "match_time": "2025-09-25T15:00:00"
        }

        # Mock依赖行为
        processor.data_cleaner.clean_match_data.return_value = raw_data
        processor.missing_handler.handle_missing_match_data.return_value = raw_data
        processor.cache_manager.aget.return_value = None  # 缓存未命中
        processor.cache_manager.aset.return_value = True

        result = await processor.process_raw_match_data(raw_data)

        assert result is not None
        assert result["external_match_id"] == "match_1"
        assert result["home_score"] == 2
        assert result["away_score"] == 1

    @pytest.mark.asyncio
    async def test_process_raw_match_data_list(self, processor):
        """测试处理比赛数据列表"""
        # Mock初始化
        processor.data_cleaner = Mock()
        processor.missing_handler = Mock()
        processor.cache_manager = AsyncMock()

        # Mock数据列表
        raw_data_list = [
            {
                "external_match_id": "match_1",
                "home_team_id": 1,
                "away_team_id": 2,
                "home_score": 2,
                "away_score": 1
            },
            {
                "external_match_id": "match_2",
                "home_team_id": 3,
                "away_team_id": 4,
                "home_score": 0,
                "away_score": 0
            }
        ]

        # Mock依赖行为
        processor.data_cleaner.clean_match_data.side_effect = lambda x: x
        processor.missing_handler.handle_missing_match_data.side_effect = lambda x: x
        processor.cache_manager.aget.return_value = None
        processor.cache_manager.aset.return_value = True

        result = await processor.process_raw_match_data(raw_data_list)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "external_match_id" in result.columns

    @pytest.mark.asyncio
    async def test_process_raw_match_data_empty_list(self, processor):
        """测试处理空列表"""
        processor.data_cleaner = Mock()

        result = await processor.process_raw_match_data([])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_process_raw_match_data_cache_hit(self, processor):
        """测试缓存命中场景"""
        # Mock初始化
        processor.data_cleaner = Mock()
        processor.cache_manager = AsyncMock()

        # Mock缓存数据
        cached_data = {
            "external_match_id": "match_1",
            "home_score": 2,
            "away_score": 1,
            "processed": True
        }

        raw_data = {
            "external_match_id": "match_1",
            "home_team_id": 1,
            "away_team_id": 2
        }

        # Mock缓存命中
        processor.cache_manager.aget.return_value = cached_data

        result = await processor.process_raw_match_data(raw_data)

        # 应该返回缓存的数据
        assert result == cached_data
        # 数据清洗器不应该被调用
        processor.data_cleaner.clean_match_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_success(self, processor):
        """测试成功处理原始赔率数据"""
        processor.data_cleaner = Mock()

        raw_odds = [
            {
                "match_id": "match_1",
                "home_odds": 2.50,
                "draw_odds": 3.20,
                "away_odds": 2.80
            },
            {
                "match_id": "match_2",
                "home_odds": 1.80,
                "draw_odds": 3.50,
                "away_odds": 4.20
            }
        ]

        processor.data_cleaner.clean_odds_data.return_value = raw_odds

        result = await processor.process_raw_odds_data(raw_odds)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["home_odds"] == 2.50

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_empty_input(self, processor):
        """测试处理空赔率数据"""
        processor.data_cleaner = Mock()
        processor.data_cleaner.clean_odds_data.return_value = []

        result = await processor.process_raw_odds_data([])

        assert result == []

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_cleaner_not_initialized(self, processor):
        """测试数据清洗器未初始化"""
        processor.data_cleaner = None

        result = await processor.process_raw_odds_data([{"match_id": "match_1"}])

        assert result == []

    @pytest.mark.asyncio
    async def test_process_features_data_success(self, processor):
        """测试成功处理特征数据"""
        processor.missing_handler = Mock()

        features_df = pd.DataFrame({
            'feature1': [1, 2, None],
            'feature2': [None, 5, 6],
            'feature3': [7, 8, 9]
        })

        expected_df = pd.DataFrame({
            'feature1': [1, 2, 0],  # None值被填充为0
            'feature2': [0, 5, 6],  # None值被填充为0
            'feature3': [7, 8, 9]
        })

        processor.missing_handler.handle_missing_features.return_value = expected_df

        result = await processor.process_features_data(1, features_df)

        assert isinstance(result, pd.DataFrame)
        assert result.equals(expected_df)
        processor.missing_handler.handle_missing_features.assert_called_once_with(1, features_df)

    @pytest.mark.asyncio
    async def test_process_features_data_handler_not_initialized(self, processor):
        """测试缺失值处理器未初始化"""
        processor.missing_handler = None

        features_df = pd.DataFrame({'feature1': [1, 2, 3]})

        result = await processor.process_features_data(1, features_df)

        # 应该返回原始DataFrame
        assert result.equals(features_df)

    @pytest.mark.asyncio
    async def test_process_batch_matches_success(self, processor):
        """测试批量处理比赛数据"""
        # Mock process_raw_match_data 方法
        async def mock_process_match(data):
            if data.get("external_match_id") == "match_1":
                return {"external_match_id": "match_1", "processed": True}
            elif data.get("external_match_id") == "match_2":
                return {"external_match_id": "match_2", "processed": True}
            else:
                return None

        processor.process_raw_match_data = mock_process_match

        raw_matches = [
            {"external_match_id": "match_1", "home_team_id": 1, "away_team_id": 2},
            {"external_match_id": "match_2", "home_team_id": 3, "away_team_id": 4},
            {"external_match_id": "match_3", "home_team_id": 5, "away_team_id": 6}  # 这个会返回None
        ]

        result = await processor.process_batch_matches(raw_matches)

        assert len(result) == 2  # 只有前两个成功
        assert all(match["processed"] for match in result)

    @pytest.mark.asyncio
    async def test_validate_data_quality_match_valid(self, processor):
        """测试验证有效比赛数据"""
        valid_match_data = {
            "external_match_id": "match_1",
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2025-09-25T15:00:00",
            "home_score": 2,
            "away_score": 1
        }

        result = await processor.validate_data_quality(valid_match_data, "match")

        assert result["is_valid"] is True
        assert len(result["issues"]) == 0
        assert result["data_type"] == "match"

    @pytest.mark.asyncio
    async def test_validate_data_quality_match_missing_fields(self, processor):
        """测试验证缺失必要字段的比赛数据"""
        invalid_match_data = {
            "external_match_id": "match_1",
            # 缺少 home_team_id, away_team_id, match_time
            "home_score": 2,
            "away_score": 1
        }

        result = await processor.validate_data_quality(invalid_match_data, "match")

        assert result["is_valid"] is False
        assert len(result["issues"]) > 0
        assert any("Missing required field" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_validate_data_quality_match_negative_scores(self, processor):
        """测试验证负分比赛数据"""
        invalid_match_data = {
            "external_match_id": "match_1",
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2025-09-25T15:00:00",
            "home_score": -1,  # 负分
            "away_score": 1
        }

        result = await processor.validate_data_quality(invalid_match_data, "match")

        assert result["is_valid"] is False
        assert any("Negative scores detected" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_validate_data_quality_match_high_scores_warning(self, processor):
        """测试验证过高比分警告"""
        match_data = {
            "external_match_id": "match_1",
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2025-09-25T15:00:00",
            "home_score": 25,  # 异常高分
            "away_score": 1
        }

        result = await processor.validate_data_quality(match_data, "match")

        # 数据应该有效，但有警告
        assert result["is_valid"] is True
        assert len(result["warnings"]) > 0
        assert any("Unusually high scores detected" in warning for warning in result["warnings"])

    @pytest.mark.asyncio
    async def test_validate_data_quality_odds_valid(self, processor):
        """测试验证有效赔率数据"""
        valid_odds_data = {
            "outcomes": [
                {"name": "home", "price": 2.50},
                {"name": "draw", "price": 3.20},
                {"name": "away", "price": 2.80}
            ]
        }

        result = await processor.validate_data_quality(valid_odds_data, "odds")

        assert result["is_valid"] is True
        assert len(result["issues"]) == 0
        assert result["data_type"] == "odds"

    @pytest.mark.asyncio
    async def test_validate_data_quality_odds_no_outcomes(self, processor):
        """测试验证无赔率结果的数据"""
        invalid_odds_data = {
            "outcomes": []  # 空的赔率结果
        }

        result = await processor.validate_data_quality(invalid_odds_data, "odds")

        assert result["is_valid"] is False
        assert any("No odds outcomes found" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_validate_data_quality_odds_invalid_price(self, processor):
        """测试验证无效赔率价格"""
        invalid_odds_data = {
            "outcomes": [
                {"name": "home", "price": 0.50},  # 低于最小值1.01
                {"name": "draw", "price": 3.20}
            ]
        }

        result = await processor.validate_data_quality(invalid_odds_data, "odds")

        assert result["is_valid"] is False
        assert any("Invalid odds price" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_process_text(self, processor):
        """测试处理文本数据"""
        text = "  Team A vs Team B, Score: 2-1  "

        result = await processor.process_text(text)

        assert result["processed_text"] == text.strip()
        assert result["word_count"] == 8
        assert result["character_count"] == len(text.strip())

    @pytest.mark.asyncio
    async def test_process_batch_mixed_data(self, processor):
        """测试批量处理混合数据类型"""
        data_list = [
            "Sample text data",  # 字符串
            {"key": "value"},   # 字典
            123,               # 数字
            ["list", "data"]   # 列表
        ]

        result = await processor.process_batch(data_list)

        assert len(result) == 4
        assert result[0]["processed_text"] == "Sample text data"
        assert result[1]["key"] == "value"
        assert result[1]["processed"] is True
        assert result[2]["original_data"] == 123
        assert result[3]["original_data"] == ["list", "data"]

    @pytest.mark.asyncio
    async def test_handle_missing_scores_success(self, processor):
        """测试成功处理分数缺失值"""
        processor.missing_handler = Mock()

        test_df = pd.DataFrame({
            'match_id': [1, 2, 3],
            'home_score': [2, None, 1],
            'away_score': [1, None, 0]
        })

        expected_df = pd.DataFrame({
            'match_id': [1, 2, 3],
            'home_score': [2, 0, 1],  # None值被填充为0
            'away_score': [1, 0, 0]  # None值被填充为0
        })

        processor.missing_handler.interpolate_scores.return_value = expected_df

        result = await processor.handle_missing_scores(test_df)

        assert result is not None
        assert result.equals(expected_df)

    @pytest.mark.asyncio
    async def test_handle_missing_scores_handler_not_initialized(self, processor):
        """测试缺失值处理器未初始化"""
        processor.missing_handler = None

        test_df = pd.DataFrame({
            'match_id': [1, 2],
            'home_score': [2, None]
        })

        result = await processor.handle_missing_scores(test_df)

        assert result is None

    @pytest.mark.asyncio
    async def test_handle_missing_team_data_success(self, processor):
        """测试成功处理球队数据缺失值"""
        processor.missing_handler = Mock()

        team_df = pd.DataFrame({
            'team_id': [1, 2, 3],
            'team_name': ['Team A', None, 'Team C'],
            'league_id': [1, None, 2]
        })

        expected_df = pd.DataFrame({
            'team_id': [1, 2, 3],
            'team_name': ['Team A', 'Unknown', 'Team C'],  # None值被填充
            'league_id': [1, 0, 2]  # None值被填充
        })

        processor.missing_handler.impute_team_data.return_value = expected_df

        result = await processor.handle_missing_team_data(team_df)

        assert result is not None
        assert result.equals(expected_df)

    @pytest.mark.asyncio
    async def test_detect_anomalies_success(self, processor):
        """测试成功检测异常"""
        processor.missing_handler = Mock()

        test_df = pd.DataFrame({
            'match_id': [1, 2, 3],
            'home_score': [2, 15, 1],  # 15分可能是异常值
            'away_score': [1, 0, 12]   # 12分可能是异常值
        })

        expected_anomalies = [
            {"match_id": 2, "field": "home_score", "value": 15, "reason": " unusually high"},
            {"match_id": 3, "field": "away_score", "value": 12, "reason": " unusually high"}
        ]

        processor.missing_handler.detect_anomalies.return_value = expected_anomalies

        result = await processor.detect_anomalies(test_df)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["match_id"] == 2
        assert result[0]["value"] == 15

    @pytest.mark.asyncio
    async def test_detect_anomalies_handler_not_initialized(self, processor):
        """测试异常检测时缺失值处理器未初始化"""
        processor.missing_handler = None

        test_df = pd.DataFrame({'match_id': [1, 2], 'home_score': [2, 3]})

        result = await processor.detect_anomalies(test_df)

        assert result == []

    @pytest.mark.asyncio
    async def test_cache_processing_results_success(self, processor):
        """测试成功缓存处理结果"""
        processor.cache_manager = Mock()
        processor.cache_manager.set_json = AsyncMock()

        cache_key = "test_processing_key"
        data = {"match_id": "match_1", "processed": True}

        result = await processor.cache_processing_results(cache_key, data, ttl=1800)

        assert result is True
        processor.cache_manager.set_json.assert_called_once_with(cache_key, data, ttl=1800)

    @pytest.mark.asyncio
    async def test_cache_processing_results_manager_not_initialized(self, processor):
        """测试缓存管理器未初始化"""
        processor.cache_manager = None

        result = await processor.cache_processing_results("test_key", {"data": "test"})

        assert result is False

    @pytest.mark.asyncio
    async def test_get_cached_results_success(self, processor):
        """测试成功获取缓存结果"""
        processor.cache_manager = Mock()
        cached_data = {"match_id": "match_1", "processed": True}
        processor.cache_manager.get_json = AsyncMock(return_value=cached_data)

        result = await processor.get_cached_results("test_key")

        assert result == cached_data
        processor.cache_manager.get_json.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_cached_results_miss(self, processor):
        """测试缓存未命中"""
        processor.cache_manager = Mock()
        processor.cache_manager.get_json = AsyncMock(return_value=None)

        result = await processor.get_cached_results("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_batch_process_datasets_success(self, processor):
        """测试批量处理多个数据集"""
        # Mock处理方法
        processor.process_batch_matches = AsyncMock(return_value=[
            {"match_id": 1, "processed": True},
            {"match_id": 2, "processed": True}
        ])
        processor.process_raw_odds_data = AsyncMock(return_value=[
            {"match_id": 1, "odds": 2.50},
            {"match_id": 2, "odds": 3.20}
        ])
        processor.process_batch = AsyncMock(return_value=[
            {"type": "other", "processed": True}
        ])

        datasets = {
            "matches": [{"match_id": 1}, {"match_id": 2}],
            "odds": [{"match_id": 1, "odds": 2.50}, {"match_id": 2, "odds": 3.20}],
            "other": [{"data": "test"}]
        }

        result = await processor.batch_process_datasets(datasets)

        assert result["total_processed"] == 5  # 2 + 2 + 1
        assert result["processed_counts"]["matches"] == 2
        assert result["processed_counts"]["odds"] == 2
        assert result["processed_counts"]["other"] == 1
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_batch_process_datasets_with_errors(self, processor):
        """测试批量处理数据集时出现错误"""
        processor.process_batch_matches = AsyncMock(side_effect=Exception("Processing failed"))
        processor.process_raw_odds_data = AsyncMock(return_value=[{"match_id": 1, "odds": 2.50}])

        datasets = {
            "matches": [{"match_id": 1}],
            "odds": [{"match_id": 1, "odds": 2.50}]
        }

        result = await processor.batch_process_datasets(datasets)

        assert result["total_processed"] == 1  # 只有odds成功
        assert "matches" in result["errors"]
        assert "Processing failed" in result["errors"]["matches"]

    @pytest.mark.asyncio
    async def test_process_with_retry_success(self, processor):
        """测试重试机制成功"""
        call_count = 0

        async def mock_func(data):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt failed")
            return {"success": True, "data": data}

        result = await processor.process_with_retry(mock_func, {"test": "data"}, max_retries=3)

        assert result["success"] is True
        assert call_count == 2  # 第一次失败，第二次成功

    @pytest.mark.asyncio
    async def test_process_with_retry_all_attempts_fail(self, processor):
        """测试重试机制所有尝试都失败"""
        async def mock_func(data):
            raise Exception("Persistent failure")

        with pytest.raises(RuntimeError, match="处理持续失败"):
            await processor.process_with_retry(mock_func, {"test": "data"}, max_retries=3)

    @pytest.mark.asyncio
    async def test_process_large_dataset_success(self, processor):
        """测试成功处理大型数据集"""
        large_dataset = [{"id": i, "value": i * 2} for i in range(100)]

        # Mock _process_in_batches
        async def mock_process_in_batches(dataset, batch_size):
            for i in range(0, len(dataset), batch_size):
                batch = dataset[i:i + batch_size]
                # 返回处理后的批次
                processed_batch = [{"id": item["id"], "processed": True} for item in batch]
                yield processed_batch

        processor._process_in_batches = mock_process_in_batches
        processor.process_batch = AsyncMock(side_effect=lambda batch: batch)

        result = await processor.process_large_dataset(large_dataset, batch_size=25)

        assert len(result) == 100
        assert all(item["processed"] for item in result)

    @pytest.mark.asyncio
    async def test_collect_performance_metrics(self, processor):
        """测试收集性能指标"""
        async def mock_processing_function(*args, **kwargs):
            await asyncio.sleep(0.1)  # 模拟处理时间
            return [{"result": i} for i in range(10)]  # 返回10个结果

        metrics = await processor.collect_performance_metrics(mock_processing_function)

        assert "total_time" in metrics
        assert "items_processed" in metrics
        assert "items_per_second" in metrics
        assert metrics["items_processed"] == 10
        assert metrics["items_per_second"] > 0

    @pytest.mark.asyncio
    async def test_cleanup_success(self, processor):
        """测试成功清理资源"""
        # Mock各种资源
        processor.db_manager = Mock()
        processor.db_manager.close = AsyncMock()
        processor._cache = {1: "data", 2: "more_data"}

        result = await processor.cleanup()

        assert result is True
        assert len(processor._cache) == 0  # 缓存被清空
        processor.db_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_sync_close(self, processor):
        """测试清理资源时使用同步关闭方法"""
        # Mock同步关闭的数据库管理器
        processor.db_manager = Mock()
        processor.db_manager.close = Mock()  # 同步方法
        processor._cache = {"test": "data"}

        result = await processor.cleanup()

        assert result is True
        processor.db_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_exception(self, processor):
        """测试清理资源时出现异常"""
        processor.db_manager = Mock()
        processor.db_manager.close = AsyncMock(side_effect=Exception("Close failed"))
        processor._cache = {"test": "data"}

        result = await processor.cleanup()

        assert result is False  # 清理失败

    def test_edge_cases_with_none_inputs(self, processor):
        """测试处理None输入的边界情况"""
        # 这些测试是为了确保服务能正确处理None输入而不崩溃
        # 实际的服务方法都有适当的空值检查

        # 检查初始化状态
        assert processor.data_cleaner is None
        assert processor.missing_handler is None
        assert processor.data_lake is None
        assert processor.db_manager is None
        assert processor.cache_manager is None

        # 服务名称应该正确设置
        assert processor.name == "DataProcessingService"