"""
Tests for src/services/data_processing.py (Phase 5)

针对数据处理服务的全面测试，旨在提升覆盖率至 ≥60%
覆盖初始化、数据处理、清洗、缺失值处理等核心功能
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest

from src.services.data_processing import DataProcessingService


class TestDataProcessingServiceBasic:
    """基础功能测试"""

    @pytest.fixture
    def service(self):
        """创建数据处理服务实例"""
        return DataProcessingService()

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.name == "DataProcessingService"
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.db_manager is None
        assert service.cache_manager is None

    @pytest.mark.asyncio
    async def test_initialize_success(self, service):
        """测试成功初始化"""
        with patch.multiple(
            'src.services.data_processing',
            FootballDataCleaner=Mock(),
            MissingDataHandler=Mock(),
            DataLakeStorage=Mock(),
            DatabaseManager=Mock(),
            RedisManager=Mock()
        ):
            result = await service.initialize()
            assert result is True
            assert service.data_cleaner is not None
            assert service.missing_handler is not None
            assert service.data_lake is not None
            assert service.db_manager is not None
            assert service.cache_manager is not None

    @pytest.mark.asyncio
    async def test_initialize_failure(self, service):
        """测试初始化失败"""
        with patch('src.services.data_processing.FootballDataCleaner', side_effect=Exception("初始化失败")):
            result = await service.initialize()
            assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_with_mocked_managers(self, service):
        """测试关闭服务（使用mock管理器）"""
        # 模拟已初始化的状态
        mock_cache = Mock()
        mock_cache.close = Mock()
        mock_db = Mock()
        mock_db.close = AsyncMock()

        service.cache_manager = mock_cache
        service.db_manager = mock_db
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()

        await service.shutdown()

        # 验证清理操作
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.cache_manager is None
        assert service.db_manager is None
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_with_async_cache_close(self, service):
        """测试关闭服务（异步缓存关闭）"""
        mock_cache = Mock()
        mock_cache.close = AsyncMock()
        mock_cache.close._mock_name = "mock_close"  # 标记为mock

        service.cache_manager = mock_cache

        await service.shutdown()

        mock_cache.close.assert_called_once()
        assert service.cache_manager is None


class TestDataProcessingServiceDataOperations:
    """数据操作测试"""

    @pytest.fixture
    async def initialized_service(self):
        """创建已初始化的服务实例"""
        service = DataProcessingService()

        with patch.multiple(
            'src.services.data_processing',
            FootballDataCleaner=Mock(),
            MissingDataHandler=Mock(),
            DataLakeStorage=Mock(),
            DatabaseManager=Mock(),
            RedisManager=Mock()
        ):
            await service.initialize()

        return service

    @pytest.mark.asyncio
    async def test_process_raw_match_data_single_dict_success(self, initialized_service):
        """测试处理单个比赛数据成功"""
        service = initialized_service

        # 模拟原始数据
        raw_data = {
            "external_match_id": "12345",
            "home_team": "Team A",
            "away_team": "Team B",
            "match_date": "2024-01-01"
        }

        # 模拟清洗器返回清洗后的数据
        cleaned_data = {
            "external_match_id": "12345",
            "home_team": "TEAM_A",
            "away_team": "TEAM_B",
            "match_date": datetime(2024, 1, 1)
        }

        service.data_cleaner.clean_match_data = Mock(return_value=cleaned_data)
        service.missing_handler.handle_missing_match_data = Mock(return_value=cleaned_data)
        service.cache_manager.aget = AsyncMock(return_value=None)  # 缓存未命中
        service.cache_manager.aset = AsyncMock()

        result = await service.process_raw_match_data(raw_data)

        assert result == cleaned_data
        service.data_cleaner.clean_match_data.assert_called_once_with(raw_data)

    @pytest.mark.asyncio
    async def test_process_raw_match_data_list_success(self, initialized_service):
        """测试处理比赛数据列表成功"""
        service = initialized_service

        raw_data = [
            {"external_match_id": "12345", "home_team": "Team A"},
            {"external_match_id": "12346", "home_team": "Team B"}
        ]

        cleaned_data = {"external_match_id": "12345", "home_team": "TEAM_A"}

        service.data_cleaner.clean_match_data = Mock(return_value=cleaned_data)
        service.missing_handler.handle_missing_match_data = Mock(return_value=cleaned_data)
        service.cache_manager.aget = AsyncMock(return_value=None)
        service.cache_manager.aset = AsyncMock()

        result = await service.process_raw_match_data(raw_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_process_raw_match_data_empty_list(self, initialized_service):
        """测试处理空数据列表"""
        service = initialized_service

        result = await service.process_raw_match_data([])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_process_raw_match_data_no_cleaner(self, initialized_service):
        """测试数据清洗器未初始化"""
        service = initialized_service
        service.data_cleaner = None

        raw_data = {"match_id": "12345"}

        result = await service.process_raw_match_data(raw_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_process_raw_match_data_with_cache_hit(self, initialized_service):
        """测试缓存命中情况"""
        service = initialized_service

        raw_data = {"external_match_id": "12345"}
        cached_data = {"external_match_id": "12345", "cached": True}

        service.cache_manager.aget = AsyncMock(return_value=cached_data)

        result = await service.process_raw_match_data(raw_data)

        assert result == cached_data
        service.cache_manager.aget.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_success(self, initialized_service):
        """测试处理原始赔率数据成功"""
        service = initialized_service

        raw_odds = [
            {"match_id": "12345", "odds": 1.5},
            {"match_id": "12346", "odds": 2.0}
        ]

        cleaned_odds = [
            {"match_id": "12345", "odds": 1.5, "cleaned": True},
            {"match_id": "12346", "odds": 2.0, "cleaned": True}
        ]

        service.data_cleaner.clean_odds_data = Mock(return_value=cleaned_odds)

        result = await service.process_raw_odds_data(raw_odds)

        assert result == cleaned_odds
        service.data_cleaner.clean_odds_data.assert_called_once_with(raw_odds)

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_no_cleaner(self, initialized_service):
        """测试赔率数据清洗器未初始化"""
        service = initialized_service
        service.data_cleaner = None

        result = await service.process_raw_odds_data([])

        assert result == []

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_failure(self, initialized_service):
        """测试处理赔率数据失败"""
        service = initialized_service

        service.data_cleaner.clean_odds_data = Mock(side_effect=Exception("清洗失败"))

        result = await service.process_raw_odds_data([{"match_id": "12345"}])

        assert result == []

    @pytest.mark.asyncio
    async def test_process_features_data_success(self, initialized_service):
        """测试处理特征数据成功"""
        service = initialized_service

        match_id = 12345
        features_df = pd.DataFrame({'feature1': [1, 2, 3], 'feature2': [4, 5, 6]})
        processed_df = pd.DataFrame({'feature1': [1, 2, 3], 'feature2': [4, 5, 6], 'processed': True})

        service.missing_handler.handle_missing_features = AsyncMock(return_value=processed_df)

        result = await service.process_features_data(match_id, features_df)

        assert isinstance(result, pd.DataFrame)
        service.missing_handler.handle_missing_features.assert_called_once_with(match_id, features_df)

    @pytest.mark.asyncio
    async def test_process_features_data_no_handler(self, initialized_service):
        """测试特征数据处理器未初始化"""
        service = initialized_service
        service.missing_handler = None

        features_df = pd.DataFrame({'feature1': [1, 2, 3]})

        result = await service.process_features_data(12345, features_df)

        assert result.equals(features_df)

    @pytest.mark.asyncio
    async def test_process_features_data_failure(self, initialized_service):
        """测试处理特征数据失败"""
        service = initialized_service

        features_df = pd.DataFrame({'feature1': [1, 2, 3]})
        service.missing_handler.handle_missing_features = AsyncMock(side_effect=Exception("处理失败"))

        result = await service.process_features_data(12345, features_df)

        # 应该返回原始数据
        assert result.equals(features_df)

    @pytest.mark.asyncio
    async def test_process_batch_matches_success(self, initialized_service):
        """测试批量处理比赛数据成功"""
        service = initialized_service

        raw_matches = [
            {"external_match_id": "12345", "home_team": "Team A"},
            {"external_match_id": "12346", "home_team": "Team B"}
        ]

        processed_match = {"external_match_id": "12345", "processed": True}

        # Mock处理结果
        with patch.object(service, 'process_raw_match_data', return_value=processed_match):
            result = await service.process_batch_matches(raw_matches)

        assert len(result) == 2
        assert all(match['processed'] for match in result)

    @pytest.mark.asyncio
    async def test_process_batch_matches_partial_failure(self, initialized_service):
        """测试批量处理部分失败"""
        service = initialized_service

        raw_matches = [
            {"external_match_id": "12345"},
            {"external_match_id": "12346"}
        ]

        processed_match = {"external_match_id": "12345", "processed": True}

        # Mock第一个成功，第二个失败
        side_effects = [processed_match, Exception("处理失败")]
        with patch.object(service, 'process_raw_match_data', side_effect=side_effects):
            result = await service.process_batch_matches(raw_matches)

        assert len(result) == 1
        assert result[0]['processed'] is True


class TestDataProcessingServiceCacheOperations:
    """缓存操作测试"""

    @pytest.fixture
    async def service_with_cache(self):
        """创建带缓存的服务实例"""
        service = DataProcessingService()

        mock_cache = Mock()
        mock_cache.aget = AsyncMock()
        mock_cache.aset = AsyncMock()

        with patch.multiple(
            'src.services.data_processing',
            FootballDataCleaner=Mock(),
            MissingDataHandler=Mock(),
            DataLakeStorage=Mock(),
            DatabaseManager=Mock(),
            RedisManager=Mock(return_value=mock_cache)
        ):
            await service.initialize()
            service.cache_manager = mock_cache

        return service

    @pytest.mark.asyncio
    async def test_single_match_data_with_cache_miss(self, service_with_cache):
        """测试单个比赛数据处理缓存未命中"""
        service = service_with_cache

        raw_data = {"external_match_id": "12345"}
        cleaned_data = {"external_match_id": "12345", "cleaned": True}

        service.cache_manager.aget = AsyncMock(return_value=None)  # 缓存未命中
        service.data_cleaner.clean_match_data = Mock(return_value=cleaned_data)
        service.missing_handler.handle_missing_match_data = Mock(return_value=cleaned_data)

        result = await service._process_single_match_data(raw_data)

        assert result == cleaned_data
        service.cache_manager.aget.assert_called_once()
        service.cache_manager.aset.assert_called_once()

    @pytest.mark.asyncio
    async def test_single_match_data_cleaning_returns_none(self, service_with_cache):
        """测试单个比赛数据清洗返回None"""
        service = service_with_cache

        raw_data = {"external_match_id": "12345"}

        service.cache_manager.aget = AsyncMock(return_value=None)
        service.data_cleaner.clean_match_data = Mock(return_value=None)

        result = await service._process_single_match_data(raw_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_single_match_data_no_cache_manager(self):
        """测试没有缓存管理器的单个数据处理"""
        service = DataProcessingService()

        with patch.multiple(
            'src.services.data_processing',
            FootballDataCleaner=Mock(),
            MissingDataHandler=Mock(),
            DataLakeStorage=Mock(),
            DatabaseManager=Mock(),
            RedisManager=Mock()
        ):
            await service.initialize()
            service.cache_manager = None  # 设置为None

        raw_data = {"external_match_id": "12345"}
        cleaned_data = {"external_match_id": "12345", "cleaned": True}

        service.data_cleaner.clean_match_data = Mock(return_value=cleaned_data)
        service.missing_handler.handle_missing_match_data = Mock(return_value=cleaned_data)

        result = await service._process_single_match_data(raw_data)

        assert result == cleaned_data

    @pytest.mark.asyncio
    async def test_single_match_data_no_match_id(self, service_with_cache):
        """测试单个比赛数据没有match_id"""
        service = service_with_cache

        raw_data = {"home_team": "Team A"}  # 没有external_match_id
        cleaned_data = {"home_team": "TEAM_A", "cleaned": True}

        service.data_cleaner.clean_match_data = Mock(return_value=cleaned_data)
        service.missing_handler.handle_missing_match_data = Mock(return_value=cleaned_data)

        result = await service._process_single_match_data(raw_data)

        assert result == cleaned_data
        # 没有match_id，不应该调用缓存
        service.cache_manager.aget.assert_not_called()


class TestDataProcessingServiceAsyncBehavior:
    """异步行为测试"""

    @pytest.fixture
    async def service_with_async_handlers(self):
        """创建具有异步处理器的服务"""
        service = DataProcessingService()

        mock_cleaner = Mock()
        mock_handler = Mock()

        with patch.multiple(
            'src.services.data_processing',
            FootballDataCleaner=Mock(return_value=mock_cleaner),
            MissingDataHandler=Mock(return_value=mock_handler),
            DataLakeStorage=Mock(),
            DatabaseManager=Mock(),
            RedisManager=Mock()
        ):
            await service.initialize()

        return service, mock_cleaner, mock_handler

    @pytest.mark.asyncio
    async def test_async_clean_match_data(self, service_with_async_handlers):
        """测试异步清洗匹配数据"""
        service, mock_cleaner, mock_handler = service_with_async_handlers

        async def async_clean(data):
            return {"external_match_id": "12345", "async_cleaned": True}

        raw_data = {"external_match_id": "12345"}
        mock_cleaner.clean_match_data = async_clean
        mock_handler.handle_missing_match_data = Mock(return_value={"processed": True})
        service.cache_manager.aget = AsyncMock(return_value=None)
        service.cache_manager.aset = AsyncMock()

        result = await service._process_single_match_data(raw_data)

        assert result["processed"] is True

    @pytest.mark.asyncio
    async def test_async_handle_missing_data(self, service_with_async_handlers):
        """测试异步处理缺失数据"""
        service, mock_cleaner, mock_handler = service_with_async_handlers

        async def async_handle(data):
            return {"external_match_id": "12345", "async_handled": True}

        raw_data = {"external_match_id": "12345"}
        cleaned_data = {"external_match_id": "12345", "cleaned": True}

        mock_cleaner.clean_match_data = Mock(return_value=cleaned_data)
        mock_handler.handle_missing_match_data = async_handle
        service.cache_manager.aget = AsyncMock(return_value=None)
        service.cache_manager.aset = AsyncMock()

        result = await service._process_single_match_data(raw_data)

        assert result["async_handled"] is True

    @pytest.mark.asyncio
    async def test_async_clean_odds_data(self):
        """测试异步清洗赔率数据"""
        service = DataProcessingService()

        async def async_clean_odds(data):
            return [{"match_id": "12345", "async_cleaned_odds": True}]

        mock_cleaner = Mock()
        mock_cleaner.clean_odds_data = async_clean_odds

        with patch.multiple(
            'src.services.data_processing',
            FootballDataCleaner=Mock(return_value=mock_cleaner),
            MissingDataHandler=Mock(),
            DataLakeStorage=Mock(),
            DatabaseManager=Mock(),
            RedisManager=Mock()
        ):
            await service.initialize()

        raw_odds = [{"match_id": "12345", "odds": 1.5}]

        result = await service.process_raw_odds_data(raw_odds)

        assert len(result) == 1
        assert result[0]["async_cleaned_odds"] is True


class TestDataProcessingServiceErrorHandling:
    """错误处理测试"""

    @pytest.fixture
    def service(self):
        return DataProcessingService()

    @pytest.mark.asyncio
    async def test_initialization_partial_failure(self, service):
        """测试部分初始化失败"""
        with patch('src.services.data_processing.FootballDataCleaner', Mock()):
            with patch('src.services.data_processing.MissingDataHandler', side_effect=Exception("Handler失败")):
                result = await service.initialize()
                assert result is False

    @pytest.mark.asyncio
    async def test_process_match_data_exception_handling(self):
        """测试处理比赛数据时的异常处理"""
        service = DataProcessingService()

        with patch.multiple(
            'src.services.data_processing',
            FootballDataCleaner=Mock(),
            MissingDataHandler=Mock(),
            DataLakeStorage=Mock(),
            DatabaseManager=Mock(),
            RedisManager=Mock()
        ):
            await service.initialize()

        # 模拟处理过程中抛出异常
        with patch.object(service, '_process_single_match_data', side_effect=Exception("处理异常")):
            result = await service.process_raw_match_data({"external_match_id": "12345"})

        assert result is None

    @pytest.mark.asyncio
    async def test_single_match_data_processing_exception(self):
        """测试单个比赛数据处理异常"""
        service = DataProcessingService()

        with patch.multiple(
            'src.services.data_processing',
            FootballDataCleaner=Mock(),
            MissingDataHandler=Mock(),
            DataLakeStorage=Mock(),
            DatabaseManager=Mock(),
            RedisManager=Mock()
        ):
            await service.initialize()

        service.data_cleaner.clean_match_data = Mock(side_effect=Exception("清洗异常"))

        result = await service._process_single_match_data({"external_match_id": "12345"})

        assert result is None

    @pytest.mark.asyncio
    async def test_shutdown_with_none_managers(self, service):
        """测试关闭包含None管理器的服务"""
        # 设置部分管理器为None
        service.cache_manager = None
        service.db_manager = None
        service.data_cleaner = Mock()

        # 应该不会抛出异常
        await service.shutdown()

        assert service.data_cleaner is None


class TestDataProcessingServiceIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_processing_pipeline_success(self):
        """测试完整的数据处理流程成功"""
        service = DataProcessingService()

        # 创建带有异步close方法的Mock
        mock_db = Mock()
        mock_db.close = AsyncMock()

        # 模拟初始化
        with patch.multiple(
            'src.services.data_processing',
            FootballDataCleaner=Mock(),
            MissingDataHandler=Mock(),
            DataLakeStorage=Mock(),
            DatabaseManager=Mock(return_value=mock_db),
            RedisManager=Mock()
        ):
            init_result = await service.initialize()
            assert init_result is True

        # 模拟处理流程
        raw_data = {"external_match_id": "12345", "dirty_data": "needs_cleaning"}
        cleaned_data = {"external_match_id": "12345", "clean_data": "cleaned"}

        service.data_cleaner.clean_match_data = Mock(return_value=cleaned_data)
        service.missing_handler.handle_missing_match_data = Mock(return_value=cleaned_data)
        service.cache_manager.aget = AsyncMock(return_value=None)
        service.cache_manager.aset = AsyncMock()

        # 执行处理流程
        processed = await service.process_raw_match_data(raw_data)

        assert processed == cleaned_data

        # 清理
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_service_lifecycle(self):
        """测试服务生命周期"""
        service = DataProcessingService()

        # 初始状态检查
        assert service.get_status() in ["running", "stopped"]

        # 创建带有异步close方法的Mock
        mock_db = Mock()
        mock_db.close = AsyncMock()

        # 初始化
        with patch.multiple(
            'src.services.data_processing',
            FootballDataCleaner=Mock(),
            MissingDataHandler=Mock(),
            DataLakeStorage=Mock(),
            DatabaseManager=Mock(return_value=mock_db),
            RedisManager=Mock()
        ):
            result = await service.initialize()
            assert result is True

        # 关闭
        await service.shutdown()

        # 验证资源清理
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.cache_manager is None
        assert service.db_manager is None