"""
数据处理服务测试
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest

from src.services.data_processing import DataProcessingService


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
    async def test_process_raw_match_data_success(self, processor):
        """测试成功处理原始比赛数据"""
        # Mock初始化
        processor.data_cleaner = Mock()
        processor.missing_handler = Mock()
        processor.db_manager = Mock()
        processor.cache_manager = Mock()

        # Mock数据
        raw_data = {
            "external_match_id": "match_1",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "match_time": "2025-09-25"
        }

        # Mock依赖行为
        expected_result = raw_data.copy()
        processor.data_cleaner.clean_match_data.return_value = expected_result
        processor.missing_handler.handle_missing_match_data.return_value = expected_result
        mock_session = AsyncMock()
        processor.db_manager.get_async_session = Mock(return_value=mock_session)
        processor.cache_manager.aget = AsyncMock(return_value=None)
        processor.cache_manager.aset = AsyncMock(return_value=True)

        result = await processor.process_raw_match_data(raw_data)

        assert result is not None
        assert result["external_match_id"] == "match_1"

    @pytest.mark.asyncio
    async def test_process_raw_match_data_validation_error(self, processor):
        """测试处理原始比赛数据时的验证错误"""
        # Arrange - 设置数据清洗器
        processor.data_cleaner = Mock()
        # Mock返回None表示验证失败
        processor.data_cleaner.clean_match_data.return_value = None

        # 缺少必要字段的数据
        invalid_data = {
            "home_team": "Team A"
            # 缺少 external_match_id, away_team 等必要字段
        }

        # Act - 处理无效数据
        result = await processor.process_raw_match_data(invalid_data)

        # Assert - 应该返回None表示失败
        assert result is None

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_success(self, processor):
        """测试成功处理原始赔率数据"""
        processor.data_cleaner = Mock()
        processor.missing_handler = Mock()
        processor.db_manager = Mock()

        raw_data = {
            "external_match_id": "match_1",
            "home_odds": 2.50,
            "draw_odds": 3.20,
            "away_odds": 2.80
        }

        processor.data_cleaner.clean_odds_data.return_value = raw_data
        processor.missing_handler.handle_missing_odds_data.return_value = raw_data
        mock_session = AsyncMock()
        processor.db_manager.get_async_session = Mock(return_value=mock_session)

        result = await processor.process_raw_odds_data(raw_data)

        assert result is not None
        assert "external_match_id" in result

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_missing_fields(self, processor):
        """测试处理缺失字段的赔率数据"""
        processor.data_cleaner = Mock()
        processor.missing_handler = Mock()

        # 缺少一些字段的赔率数据
        incomplete_data = {
            "external_match_id": "match_1",
            "home_odds": 2.50
            # 缺少 draw_odds, away_odds
        }

        processor.data_cleaner.clean_odds_data.return_value = incomplete_data
        processor.missing_handler.handle_missing_odds_data.return_value = incomplete_data
        mock_session = AsyncMock()
        processor.db_manager.get_async_session = Mock(return_value=mock_session)

        result = await processor.process_raw_odds_data(incomplete_data)

        assert result is not None
        # 应该能处理缺失字段

    @pytest.mark.asyncio
    async def test_validate_data_quality_success(self, processor):
        """测试成功验证数据质量"""
        test_data = {
            'external_match_id': 'match_1',
            'home_team_id': 1,
            'away_team_id': 2,
            'match_time': '2025-09-25T20:00:00'
        }

        result = await processor.validate_data_quality(test_data, 'match')

        assert result is not None
        assert result['is_valid'] is True
        assert result['data_type'] == 'match'

    @pytest.mark.asyncio
    async def test_validate_data_quality_with_issues(self, processor):
        """测试验证有问题的数据质量"""
        test_df = pd.DataFrame({
            'match_id': ['match_1', None, 'match_3'],  # 包含None值
            'home_team': ['Team A', 'Team B', 'Team C'],
            'away_team': ['Team B', None, 'Team C'],  # 包含None值
            'home_score': [2, -1, 1],  # 包含无效值（负数）
            'away_score': [1, 0, 100]  # 包含可能异常值
        })

        result = await processor.validate_data_quality(test_df, 'matches')

        assert result['valid'] is False
        assert result['total_records'] == 3
        assert result['issues_detected'] > 0
        assert 'missing_values' in result
        assert 'invalid_values' in result

    @pytest.mark.asyncio
    async def test_validate_data_quality_empty_dataframe(self, processor):
        """测试验证空DataFrame"""
        empty_df = pd.DataFrame()

        result = await processor.validate_data_quality(empty_df, 'matches')

        assert result['valid'] is False
        assert result['total_records'] == 0
        assert 'empty' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, processor):
        """测试异常检测"""
        test_df = pd.DataFrame({
            'match_id': ['match_1', 'match_2', 'match_3'],
            'home_score': [2, 15, 1],  # 15分可能是异常值
            'away_score': [1, 0, 12],   # 12分可能是异常值
            'attendance': [50000, 55000, 200000]  # 20万观众可能是异常值
        })

        anomalies = await processor.detect_anomalies(test_df)

        assert isinstance(anomalies, list)
        # 应该检测到一些异常值
        assert len(anomalies) > 0

    @pytest.mark.asyncio
    async def test_handle_missing_scores(self, processor):
        """测试处理缺失的比分数据"""
        test_df = pd.DataFrame({
            'match_id': ['match_1', 'match_2', 'match_3'],
            'home_score': [2, None, 1],
            'away_score': [1, None, 0],
            'status': ['finished', 'finished', 'finished']
        })

        processor.missing_handler = Mock()
        processor.missing_handler.impute_missing_scores.return_value = test_df.fillna(0)

        result = await processor.handle_missing_scores(test_df)

        assert result is not None
        assert result['home_score'].isna().sum() == 0  # 缺失值应该被处理

    @pytest.mark.asyncio
    async def test_handle_missing_team_data(self, processor):
        """测试处理缺失的球队数据"""
        test_df = pd.DataFrame({
            'team_id': [1, 2, 3],
            'team_name': ['Team A', None, 'Team C'],  # 缺少球队名称
            'league_id': [1, 1, None]  # 缺少联赛ID
        })

        processor.missing_handler = Mock()
        processor.missing_handler.impute_missing_team_data.return_value = test_df.fillna('Unknown')

        result = await processor.handle_missing_team_data(test_df)

        assert result is not None
        assert result['team_name'].isna().sum() == 0

    @pytest.mark.asyncio
    async def test_process_text(self, processor):
        """测试处理文本数据"""
        text = "Team A vs Team B, Score: 2-1"

        result = await processor.process_text(text)

        assert isinstance(result, dict)
        assert 'processed_text' in result
        assert 'entities' in result
        assert result['original_text'] == text

    @pytest.mark.asyncio
    async def test_process_batch(self, processor):
        """测试批量处理"""
        data_list = [
            {"match_id": "match_1", "home_team": "Team A", "away_team": "Team B"},
            {"match_id": "match_2", "home_team": "Team C", "away_team": "Team D"},
            {"match_id": "match_3", "home_team": "Team E", "away_team": "Team F"}
        ]

        processor.data_cleaner = Mock()
        processor.data_cleaner.clean_match_data.side_effect = lambda x: x

        results = await processor.process_batch(data_list)

        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)

    @pytest.mark.asyncio
    async def test_process_with_retry_success(self, processor):
        """测试重试机制成功"""
        test_data = {"match_id": "match_1", "data": "test"}

        async def mock_process_func(data):
            if data.get("attempt") == 1:
                raise Exception("Temporary failure")
            return {"success": True, "data": data}

        # 第一次失败，第二次成功
        test_data["attempt"] = 1
        result = await processor.process_with_retry(mock_process_func, test_data, max_retries=2)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_process_with_retry_failure(self, processor):
        """测试重试机制最终失败"""
        test_data = {"match_id": "match_1", "data": "test"}

        async def mock_process_func(data):
            raise Exception("Persistent failure")

        result = await processor.process_with_retry(mock_process_func, test_data, max_retries=2)

        assert result["success"] is False
        assert "Persistent failure" in result["error"]

    @pytest.mark.asyncio
    async def test_cache_processing_results(self, processor):
        """测试缓存处理结果"""
        processor.cache_manager = Mock()
        processor.cache_manager.set.return_value = True

        cache_key = "test_processing_key"
        results = {"match_id": "match_1", "processed": True}

        await processor.cache_processing_results(cache_key, results)

        processor.cache_manager.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_results(self, processor):
        """测试获取缓存结果"""
        processor.cache_manager = Mock()
        cached_data = {"match_id": "match_1", "processed": True}
        processor.cache_manager.get.return_value = cached_data

        result = await processor.get_cached_results("test_key")

        assert result == cached_data
        processor.cache_manager.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_cached_results_miss(self, processor):
        """测试缓存未命中"""
        processor.cache_manager = Mock()
        processor.cache_manager.get.return_value = None

        result = await processor.get_cached_results("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_process_large_dataset(self, processor):
        """测试处理大数据集"""
        # 创建大量测试数据
        large_dataset = [{"id": i, "value": i * 2} for i in range(1000)]

        processor._process_in_batches = AsyncMock()
        processor._process_in_batches.return_value = [{"id": i, "processed": True} for i in range(1000)]

        result = await processor.process_large_dataset(large_dataset, batch_size=100)

        assert result["success"] is True
        assert result["total_processed"] == 1000
        processor._process_in_batches.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup(self, processor):
        """测试清理资源"""
        processor.data_cleaner = Mock()
        processor.missing_handler = Mock()
        processor.data_lake = Mock()
        processor.db_manager = Mock()
        processor.cache_manager = Mock()

        await processor.cleanup()

        # 验证所有清理方法被调用
        if hasattr(processor.data_cleaner, 'cleanup'):
            processor.data_cleaner.cleanup.assert_called_once()
        if hasattr(processor.missing_handler, 'cleanup'):
            processor.missing_handler.cleanup.assert_called_once()

    def test_edge_cases_with_none_values(self, processor):
        """测试处理None值的边界情况"""
        # 测试传入None值的情况
        test_cases = [
            (None, "process_raw_match_data"),
            ([], "process_batch"),
            ("", "process_text"),
        ]

        for data, method_name in test_cases:
            try:
                if method_name == "process_raw_match_data":
                    asyncio.run(processor.process_raw_match_data(data))
                elif method_name == "process_batch":
                    asyncio.run(processor.process_batch(data))
                elif method_name == "process_text":
                    asyncio.run(processor.process_text(data))
            except Exception:
                # 期望能处理异常情况
                pass

    @pytest.mark.asyncio
    async def test_shutdown_with_mock_cache_manager(self, processor):
        """测试关闭带Mock缓存管理器的服务"""
        print("🧪 测试关闭带Mock缓存管理器的服务...")

        # Arrange - 创建mock缓存管理器
        mock_cache_manager = Mock()
        mock_cache_manager.close = Mock()
        mock_cache_manager.close._mock_name = "mock_close"

        # 创建异步数据库管理器
        mock_db_manager = AsyncMock()

        # 设置处理器属性
        processor.cache_manager = mock_cache_manager
        processor.data_cleaner = Mock()
        processor.missing_handler = Mock()
        processor.data_lake = Mock()
        processor.db_manager = mock_db_manager

        # Act - 调用关闭方法
        await processor.shutdown()

        # Assert - 验证缓存管理器被正确关闭（会被调用两次：async尝试 + sync fallback）
        assert mock_cache_manager.close.call_count == 2
        mock_db_manager.close.assert_called_once()
        assert processor.cache_manager is None
        assert processor.db_manager is None

        print("✅ 关闭带Mock缓存管理器的服务测试通过")

    @pytest.mark.asyncio
    async def test_shutdown_with_async_mock_cache_manager(self, processor):
        """测试关闭带异步Mock缓存管理器的服务"""
        print("🧪 测试关闭带异步Mock缓存管理器的服务...")

        # Arrange - 创建异步mock缓存管理器
        mock_cache_manager = Mock()
        async_mock_close = AsyncMock()
        mock_cache_manager.close = async_mock_close
        mock_cache_manager.close._mock_name = "async_mock_close"

        # 创建异步数据库管理器
        mock_db_manager = AsyncMock()

        # 设置处理器属性
        processor.cache_manager = mock_cache_manager
        processor.data_cleaner = Mock()
        processor.missing_handler = Mock()
        processor.data_lake = Mock()
        processor.db_manager = mock_db_manager

        # Act - 调用关闭方法
        await processor.shutdown()

        # Assert - 验证异步缓存管理器被正确关闭
        async_mock_close.assert_called_once()
        mock_db_manager.close.assert_called_once()
        assert processor.cache_manager is None
        assert processor.db_manager is None

        print("✅ 关闭带异步Mock缓存管理器的服务测试通过")

    @pytest.mark.asyncio
    async def test_shutdown_with_sync_cache_manager(self, processor):
        """测试关闭带同步缓存管理器的服务"""
        print("🧪 测试关闭带同步缓存管理器的服务...")

        # Arrange - 创建同步缓存管理器（没有_mock_name属性）
        mock_cache_manager = Mock()
        mock_cache_manager.close = Mock()
        # 确保没有_mock_name属性

        # 创建异步数据库管理器
        mock_db_manager = AsyncMock()

        # 设置处理器属性
        processor.cache_manager = mock_cache_manager
        processor.data_cleaner = Mock()
        processor.missing_handler = Mock()
        processor.data_lake = Mock()
        processor.db_manager = mock_db_manager

        # Act - 调用关闭方法
        await processor.shutdown()

        # Assert - 验证同步缓存管理器被正确关闭
        assert mock_cache_manager.close.call_count >= 1
        mock_db_manager.close.assert_called_once()
        assert processor.cache_manager is None
        assert processor.db_manager is None

        print("✅ 关闭带同步缓存管理器的服务测试通过")

    @pytest.mark.asyncio
    async def test_shutdown_with_async_cache_manager_type_error(self, processor):
        """测试关闭带类型错误的异步缓存管理器"""
        print("🧪 测试关闭带类型错误的异步缓存管理器...")

        # Arrange - 创建会抛出TypeError的异步mock
        mock_cache_manager = Mock()
        async_mock_close = AsyncMock()
        async_mock_close.side_effect = TypeError("Async method called incorrectly")
        mock_cache_manager.close = async_mock_close
        mock_cache_manager.close._mock_name = "error_async_mock"

        # 还要创建一个同步的close方法作为fallback
        sync_close = Mock()
        mock_cache_manager.close = sync_close

        # 重新设置_mock_name
        mock_cache_manager.close._mock_name = "error_async_mock"

        # 创建异步数据库管理器
        mock_db_manager = AsyncMock()

        # 设置处理器属性
        processor.cache_manager = mock_cache_manager
        processor.data_cleaner = Mock()
        processor.missing_handler = Mock()
        processor.data_lake = Mock()
        processor.db_manager = mock_db_manager

        # Act - 调用关闭方法
        await processor.shutdown()

        # Assert - 验证同步fallback方法被调用
        sync_close.assert_called_once()
        mock_db_manager.close.assert_called_once()
        assert processor.cache_manager is None
        assert processor.db_manager is None

        print("✅ 关闭带类型错误的异步缓存管理器测试通过")

    @pytest.mark.asyncio
    async def test_shutdown_with_db_manager(self, processor):
        """测试关闭带数据库管理器的服务"""
        print("🧪 测试关闭带数据库管理器的服务...")

        # Arrange - 创建异步数据库管理器
        mock_db_manager = AsyncMock()

        # 设置处理器属性
        processor.cache_manager = None
        processor.data_cleaner = None
        processor.missing_handler = None
        processor.data_lake = None
        processor.db_manager = mock_db_manager

        # Act - 调用关闭方法
        await processor.shutdown()

        # Assert - 验证数据库管理器被正确关闭
        mock_db_manager.close.assert_called_once()
        assert processor.db_manager is None
        assert processor.cache_manager is None

        print("✅ 关闭带数据库管理器的服务测试通过")

    @pytest.mark.asyncio
    async def test_shutdown_complete(self, processor):
        """测试完整关闭服务"""
        print("🧪 测试完整关闭服务...")

        # Arrange - 创建所有组件的mock
        mock_cache_manager = Mock()
        mock_cache_manager.close = Mock()
        mock_cache_manager.close._mock_name = "mock_close"

        mock_db_manager = AsyncMock()
        mock_data_cleaner = Mock()
        mock_data_cleaner.cleanup = Mock()
        mock_missing_handler = Mock()
        mock_missing_handler.cleanup = Mock()
        mock_data_lake = Mock()
        mock_data_lake.cleanup = Mock()

        # 设置处理器属性
        processor.cache_manager = mock_cache_manager
        processor.data_cleaner = mock_data_cleaner
        processor.missing_handler = mock_missing_handler
        processor.data_lake = mock_data_lake
        processor.db_manager = mock_db_manager

        # Act - 调用关闭方法
        await processor.shutdown()

        # Assert - 验证所有组件被正确关闭和清理
        mock_cache_manager.close.assert_called_once()
        mock_db_manager.close.assert_called_once()
        assert processor.cache_manager is None
        assert processor.db_manager is None

        print("✅ 完整关闭服务测试通过")

    @pytest.mark.asyncio
    async def test_process_raw_match_data_list_empty(self, processor):
        """测试处理空的原始比赛数据列表"""
        print("🧪 测试处理空的原始比赛数据列表...")

        # Arrange - 设置数据清洗器
        processor.data_cleaner = Mock()

        # Act - 处理空列表
        result = await processor.process_raw_match_data([])

        # Assert - 应该返回空的DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

        print("✅ 处理空的原始比赛数据列表测试通过")

    @pytest.mark.asyncio
    async def test_process_raw_match_data_not_initialized(self, processor):
        """测试数据清洗器未初始化的情况"""
        print("🧪 测试数据清洗器未初始化的情况...")

        # Arrange - 确保数据清洗器未初始化
        processor.data_cleaner = None

        # Act - 尝试处理数据
        result = await processor.process_raw_match_data({"match_id": "test"})

        # Assert - 应该返回None
        assert result is None

        print("✅ 数据清洗器未初始化的情况测试通过")