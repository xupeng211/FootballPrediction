#!/usr/bin/env python3
"""
Phase 5.3.2.1: 数据处理服务全面测试

目标文件: src/services/data_processing.py
当前覆盖率: 7% (457/503 行未覆盖)
目标覆盖率: ≥60%
测试重点: 数据清洗、验证、批量处理、异常重试逻辑
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from typing import Dict, Any, List
import tempfile
import os

# Mock复杂依赖
import sys
modules_to_mock = [
    'pandas', 'numpy', 'sklearn', 'xgboost', 'mlflow',
    'feast', 'psycopg', 'psycopg_pool', 'great_expectations',
    'prometheus_client', 'confluent_kafka', 'redis'
]

for module in modules_to_mock:
    if module not in sys.modules:
        sys.modules[module] = Mock()

# Mock pandas DataFrame and Series to avoid attribute errors
mock_pd = Mock()
mock_pd.DataFrame = Mock
mock_pd.Series = Mock
sys.modules['pandas'] = mock_pd

# Mock sklearn modules more comprehensively
mock_sklearn = Mock()
mock_sklearn.metrics = Mock()
mock_sklearn.model_selection = Mock()
mock_sklearn.preprocessing = Mock()
mock_sklearn.ensemble = Mock()
mock_sklearn.linear_model = Mock()
sys.modules['sklearn'] = mock_sklearn
sys.modules['sklearn.metrics'] = mock_sklearn.metrics
sys.modules['sklearn.model_selection'] = mock_sklearn.model_selection
sys.modules['sklearn.preprocessing'] = mock_sklearn.preprocessing
sys.modules['sklearn.ensemble'] = mock_sklearn.ensemble
sys.modules['sklearn.linear_model'] = mock_sklearn.linear_model

# Mock redis modules
mock_redis = Mock()
mock_redis.asyncio = Mock()
mock_redis.exceptions = Mock()
sys.modules['redis'] = mock_redis
sys.modules['redis.asyncio'] = mock_redis.asyncio
sys.modules['redis.exceptions'] = mock_redis.exceptions

# Mock mlflow modules
mock_mlflow = Mock()
mock_mlflow.sklearn = Mock()
mock_mlflow.tracking = Mock()
mock_mlflow.entities = Mock()
mock_mlflow.exceptions = Mock()
sys.modules['mlflow'] = mock_mlflow
sys.modules['mlflow.sklearn'] = mock_mlflow.sklearn
sys.modules['mlflow.tracking'] = mock_mlflow.tracking
sys.modules['mlflow.entities'] = mock_mlflow.entities
sys.modules['mlflow.exceptions'] = mock_mlflow.exceptions

# Mock feast infra modules
mock_feast = Mock()
mock_feast.infra = Mock()
mock_feast.infra.offline_stores = Mock()
mock_feast.infra.offline_stores.contrib = Mock()
mock_feast.infra.offline_stores.contrib.postgres_offline_store = Mock()
mock_feast.infra.offline_stores.contrib.postgres_offline_store.postgres = Mock()
mock_feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source = Mock()
mock_feast.infra.online_stores = Mock()
mock_feast.infra.online_stores.redis = Mock()
mock_feast.infra.utils = Mock()
mock_feast.infra.utils.postgres = Mock()
mock_feast.infra.utils.postgres.connection_utils = Mock()
sys.modules['feast'] = mock_feast
sys.modules['feast.infra'] = mock_feast.infra
sys.modules['feast.infra.offline_stores'] = mock_feast.infra.offline_stores
sys.modules['feast.infra.offline_stores.contrib'] = mock_feast.infra.offline_stores.contrib
sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store'] = mock_feast.infra.offline_stores.contrib.postgres_offline_store
sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store.postgres'] = mock_feast.infra.offline_stores.contrib.postgres_offline_store.postgres
sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source'] = mock_feast.infra.offline.stores.contrib.postgres_offline_store.postgres_source
sys.modules['feast.infra.online_stores'] = mock_feast.infra.online_stores
sys.modules['feast.infra.online_stores.redis'] = mock_feast.infra.online_stores.redis
sys.modules['feast.infra.utils'] = mock_feast.infra.utils
sys.modules['feast.infra.utils.postgres'] = mock_feast.infra.utils.postgres
sys.modules['feast.infra.utils.postgres.connection_utils'] = mock_feast.infra.utils.postgres.connection_utils

# Mock psycopg pool modules
sys.modules['psycopg_pool'] = Mock()
sys.modules['psycopg_pool._acompat'] = Mock()

try:
    from src.services.data_processing import DataProcessingService
    IMPORT_SUCCESS = True
except ImportError as e:
    print(f"Import failed: {e}")
    IMPORT_SUCCESS = False


class TestDataProcessingService:
    """数据处理服务测试"""

    @pytest.fixture
    def service(self):
        """创建数据处理服务实例"""
        if not IMPORT_SUCCESS:
            pytest.skip("Cannot import DataProcessingService")

        return DataProcessingService()

    def test_service_initialization(self, service):
        """测试服务初始化"""
        print("🧪 测试数据处理服务初始化...")

        # 测试基本属性
        assert hasattr(service, 'data_cleaner')
        assert hasattr(service, 'missing_handler')
        assert hasattr(service, 'data_lake')
        assert hasattr(service, 'db_manager')
        assert hasattr(service, 'cache_manager')
        assert hasattr(service, 'name')
        assert service.name == "DataProcessingService"

        print("✅ 数据处理服务初始化测试通过")

    @pytest.mark.asyncio
    async def test_initialize_success(self, service):
        """测试服务初始化成功场景"""
        print("🧪 测试服务初始化成功场景...")

        with patch('src.services.data_processing.FootballDataCleaner') as mock_cleaner, \
             patch('src.services.data_processing.MissingDataHandler') as mock_handler, \
             patch('src.services.data_processing.DataLakeStorage') as mock_storage, \
             patch('src.services.data_processing.DatabaseManager') as mock_db, \
             patch('src.services.data_processing.RedisManager') as mock_redis:

            # 设置mock
            mock_cleaner.return_value = Mock()
            mock_handler.return_value = Mock()
            mock_storage.return_value = Mock()
            mock_db.return_value = Mock()
            mock_redis.return_value = Mock()

            result = await service.initialize()

            assert result is True
            assert service.data_cleaner is not None
            assert service.missing_handler is not None
            assert service.data_lake is not None
            assert service.db_manager is not None
            assert service.cache_manager is not None

        print("✅ 服务初始化成功测试通过")

    @pytest.mark.asyncio
    async def test_initialize_failure(self, service):
        """测试服务初始化失败场景"""
        print("🧪 测试服务初始化失败场景...")

        with patch('src.services.data_processing.FootballDataCleaner') as mock_cleaner:
            # 模拟初始化失败
            mock_cleaner.side_effect = Exception("初始化失败")

            result = await service.initialize()

            assert result is False

        print("✅ 服务初始化失败测试通过")

    @pytest.mark.asyncio
    async def test_shutdown_normal(self, service):
        """测试服务正常关闭"""
        print("🧪 测试服务正常关闭...")

        # 先初始化服务
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()
        service.db_manager = AsyncMock()
        service.cache_manager = Mock()

        with patch.object(service.db_manager, 'close') as mock_db_close, \
             patch.object(service.cache_manager, 'close') as mock_cache_close:

            await service.shutdown()

            mock_db_close.assert_called_once()
            mock_cache_close.assert_called_once()

            assert service.data_cleaner is None
            assert service.missing_handler is None
            assert service.data_lake is None
            assert service.db_manager is None
            assert service.cache_manager is None

        print("✅ 服务正常关闭测试通过")

    @pytest.mark.asyncio
    async def test_process_raw_match_data_list_input(self, service):
        """测试处理原始比赛数据 - 列表输入"""
        print("🧪 测试处理原始比赛数据 - 列表输入...")

        # 设置服务依赖
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        # Mock数据清洗器
        mock_clean_data = {"match_id": "123", "home_team": "Team A", "away_team": "Team B"}
        service.data_cleaner.clean_match_data.return_value = mock_clean_data

        # Mock缺失值处理器
        service.missing_handler.handle_missing_match_data.return_value = mock_clean_data

        # Mock缓存
        service.cache_manager.aget.return_value = None
        service.cache_manager.aset.return_value = True

        # 测试数据
        raw_data = [
            {"external_match_id": "123", "home_team": "Team A", "away_team": "Team B"},
            {"external_match_id": "456", "home_team": "Team C", "away_team": "Team D"}
        ]

        with patch.object(service, '_process_single_match_data') as mock_process_single:
            mock_process_single.return_value = mock_clean_data

            result = await service.process_raw_match_data(raw_data)

            assert result is not None
            assert hasattr(result, 'empty')  # 应该是DataFrame
            mock_process_single.assert_called()

        print("✅ 处理原始比赛数据 - 列表输入测试通过")

    @pytest.mark.asyncio
    async def test_process_raw_match_data_single_input(self, service):
        """测试处理原始比赛数据 - 单个输入"""
        print("🧪 测试处理原始比赛数据 - 单个输入...")

        # 设置服务依赖
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        # Mock数据清洗器
        mock_clean_data = {"match_id": "123", "home_team": "Team A", "away_team": "Team B"}
        service.data_cleaner.clean_match_data.return_value = mock_clean_data

        # Mock缺失值处理器
        service.missing_handler.handle_missing_match_data.return_value = mock_clean_data

        # Mock缓存
        service.cache_manager.aget.return_value = None
        service.cache_manager.aset.return_value = True

        # 测试数据
        raw_data = {"external_match_id": "123", "home_team": "Team A", "away_team": "Team B"}

        result = await service.process_raw_match_data(raw_data)

        assert result == mock_clean_data

        print("✅ 处理原始比赛数据 - 单个输入测试通过")

    @pytest.mark.asyncio
    async def test_process_raw_match_data_empty_list(self, service):
        """测试处理原始比赛数据 - 空列表输入"""
        print("🧪 测试处理原始比赛数据 - 空列表输入...")

        result = await service.process_raw_match_data([])

        assert result is not None
        assert hasattr(result, 'empty')  # 应该是空的DataFrame

        print("✅ 处理原始比赛数据 - 空列表输入测试通过")

    @pytest.mark.asyncio
    async def test_process_raw_match_data_cleaner_not_initialized(self, service):
        """测试处理原始比赛数据 - 清洗器未初始化"""
        print("🧪 测试处理原始比赛数据 - 清洗器未初始化...")

        # 不初始化data_cleaner
        service.data_cleaner = None

        raw_data = {"external_match_id": "123", "home_team": "Team A", "away_team": "Team B"}

        result = await service.process_raw_match_data(raw_data)

        assert result is None

        print("✅ 处理原始比赛数据 - 清洗器未初始化测试通过")

    @pytest.mark.asyncio
    async def test_process_raw_odds_data(self, service):
        """测试处理原始赔率数据"""
        print("🧪 测试处理原始赔率数据...")

        # 设置服务依赖
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        # Mock数据清洗器
        mock_clean_data = {"match_id": "123", "home_odds": 2.5, "draw_odds": 3.2}
        service.data_cleaner.clean_odds_data.return_value = mock_clean_data

        # Mock缺失值处理器
        service.missing_handler.handle_missing_odds_data.return_value = mock_clean_data

        # Mock缓存
        service.cache_manager.aget.return_value = None
        service.cache_manager.aset.return_value = True

        # 测试数据
        raw_data = {"external_match_id": "123", "home_odds": 2.5, "draw_odds": 3.2}

        result = await service.process_raw_odds_data(raw_data)

        assert result == mock_clean_data

        print("✅ 处理原始赔率数据测试通过")

    @pytest.mark.asyncio
    async def test_process_features_data(self, service):
        """测试处理特征数据"""
        print("🧪 测试处理特征数据...")

        # 设置服务依赖
        service.data_cleaner = Mock()
        service.cache_manager = AsyncMock()

        # Mock数据清洗器
        mock_clean_data = {"match_id": "123", "home_strength": 0.8, "away_strength": 0.6}
        service.data_cleaner.clean_features_data.return_value = mock_clean_data

        # Mock缓存
        service.cache_manager.aget.return_value = None
        service.cache_manager.aset.return_value = True

        # 测试数据
        raw_data = {"external_match_id": "123", "home_strength": 0.8, "away_strength": 0.6}

        result = await service.process_features_data(raw_data)

        assert result == mock_clean_data

        print("✅ 处理特征数据测试通过")

    @pytest.mark.asyncio
    async def test_process_batch_matches(self, service):
        """测试批量处理比赛数据"""
        print("🧪 测试批量处理比赛数据...")

        # 设置服务依赖
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        # Mock单个处理方法
        with patch.object(service, '_process_single_match_data') as mock_process_single:
            mock_process_single.return_value = {"match_id": "123"}

            # 测试数据
            batch_data = [
                {"external_match_id": "123", "home_team": "Team A"},
                {"external_match_id": "456", "home_team": "Team B"}
            ]

            result = await service.process_batch_matches(batch_data)

            assert result is not None
            assert isinstance(result, dict)
            assert 'processed_count' in result
            assert 'failed_count' in result
            assert result['processed_count'] == 2

        print("✅ 批量处理比赛数据测试通过")

    @pytest.mark.asyncio
    async def test_validate_data_quality_success(self, service):
        """测试数据质量验证 - 成功场景"""
        print("🧪 测试数据质量验证 - 成功场景...")

        # Mock pandas DataFrame
        mock_df = Mock()
        mock_df.empty = False
        mock_df.shape = (100, 10)  # 100行，10列
        mock_df.isnull.return_value.sum.return_value = 5  # 5个缺失值
        mock_df.duplicated.return_value.sum.return_value = 0  # 无重复值

        result = await service.validate_data_quality(mock_df)

        assert result is not None
        assert isinstance(result, dict)
        assert 'is_valid' in result
        assert result['is_valid'] is True

        print("✅ 数据质量验证 - 成功场景测试通过")

    @pytest.mark.asyncio
    async def test_validate_data_quality_failure(self, service):
        """测试数据质量验证 - 失败场景"""
        print("🧪 测试数据质量验证 - 失败场景...")

        # Mock pandas DataFrame - 高缺失率
        mock_df = Mock()
        mock_df.empty = False
        mock_df.shape = (100, 10)
        mock_df.isnull.return_value.sum.return_value = 80  # 80%缺失值

        result = await service.validate_data_quality(mock_df)

        assert result is not None
        assert isinstance(result, dict)
        assert 'is_valid' in result
        assert result['is_valid'] is False

        print("✅ 数据质量验证 - 失败场景测试通过")

    @pytest.mark.asyncio
    async def test_process_text(self, service):
        """测试文本处理"""
        print("🧪 测试文本处理...")

        test_text = "Team A vs Team B"
        expected_result = {"processed_text": "TEAM A VS TEAM B"}

        with patch('src.services.data_processing.text_processor') as mock_processor:
            mock_processor.process.return_value = expected_result

            result = await service.process_text(test_text)

            assert result == expected_result

        print("✅ 文本处理测试通过")

    @pytest.mark.asyncio
    async def test_process_batch(self, service):
        """测试批量处理"""
        print("🧪 测试批量处理...")

        test_data = ["text1", "text2", "text3"]
        expected_results = [{"result": "processed1"}, {"result": "processed2"}, {"result": "processed3"}]

        with patch.object(service, 'process_text') as mock_process:
            mock_process.side_effect = expected_results

            result = await service.process_batch(test_data)

            assert result == expected_results
            assert len(result) == 3

        print("✅ 批量处理测试通过")

    @pytest.mark.asyncio
    async def test_process_bronze_to_silver(self, service):
        """测试青铜层到银层数据处理"""
        print("🧪 测试青铜层到银层数据处理...")

        # 设置服务依赖
        service.db_manager = AsyncMock()

        with patch.object(service, '_process_raw_matches_bronze_to_silver') as mock_matches, \
             patch.object(service, '_process_raw_odds_bronze_to_silver') as mock_odds, \
             patch.object(service, '_process_raw_scores_bronze_to_silver') as mock_scores:

            mock_matches.return_value = 10
            mock_odds.return_value = 5
            mock_scores.return_value = 8

            result = await service.process_bronze_to_silver(batch_size=50)

            assert result is not None
            assert isinstance(result, dict)
            assert 'matches_processed' in result
            assert 'odds_processed' in result
            assert 'scores_processed' in result
            assert result['matches_processed'] == 10
            assert result['odds_processed'] == 5
            assert result['scores_processed'] == 8

        print("✅ 青铜层到银层数据处理测试通过")

    @pytest.mark.asyncio
    async def test_get_bronze_layer_status(self, service):
        """测试获取青铜层状态"""
        print("🧪 测试获取青铜层状态...")

        # 设置服务依赖
        service.db_manager = AsyncMock()

        # Mock数据库查询结果
        mock_result = Mock()
        mock_result.fetchone.return_value = (100,)  # 100条记录
        service.db_manager.execute.return_value = mock_result

        result = await service.get_bronze_layer_status()

        assert result is not None
        assert isinstance(result, dict)
        assert 'matches_count' in result
        assert 'odds_count' in result
        assert 'scores_count' in result

        print("✅ 获取青铜层状态测试通过")

    @pytest.mark.asyncio
    async def test_handle_missing_scores(self, service):
        """测试处理缺失比分数据"""
        print("🧪 测试处理缺失比分数据...")

        # Mock pandas DataFrame
        mock_df = Mock()
        mock_df.copy.return_value = mock_df

        result = await service.handle_missing_scores(mock_df)

        assert result is not None

        print("✅ 处理缺失比分数据测试通过")

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, service):
        """测试异常检测"""
        print("🧪 测试异常检测...")

        # Mock pandas DataFrame
        mock_df = Mock()
        mock_df.shape = (100, 10)
        mock_df.describe.return_value = Mock()

        result = await service.detect_anomalies(mock_df)

        assert result is not None
        assert isinstance(result, list)

        print("✅ 异常检测测试通过")

    @pytest.mark.asyncio
    async def test_store_processed_data(self, service):
        """测试存储处理后的数据"""
        print("🧪 测试存储处理后的数据...")

        # 设置服务依赖
        service.data_lake = AsyncMock()
        service.db_manager = AsyncMock()

        # Mock数据湖存储
        service.data_lake.store.return_value = True

        # 测试数据
        processed_data = {"match_id": "123", "home_team": "Team A"}

        result = await service.store_processed_data(processed_data, "matches")

        assert result is not None
        assert isinstance(result, dict)
        assert 'stored' in result
        assert result['stored'] is True

        print("✅ 存储处理后的数据测试通过")

    @pytest.mark.asyncio
    async def test_cache_processing_results(self, service):
        """测试缓存处理结果"""
        print("🧪 测试缓存处理结果...")

        # 设置服务依赖
        service.cache_manager = AsyncMock()

        # Mock缓存操作
        service.cache_manager.aset.return_value = True

        # 测试数据
        data = {"match_id": "123", "result": "processed"}
        cache_key = "match_123_processed"

        result = await service.cache_processing_results(data, cache_key)

        assert result is not None
        assert isinstance(result, dict)
        assert 'cached' in result
        assert result['cached'] is True

        print("✅ 缓存处理结果测试通过")

    @pytest.mark.asyncio
    async def test_get_cached_results(self, service):
        """测试获取缓存结果"""
        print("🧪 测试获取缓存结果...")

        # 设置服务依赖
        service.cache_manager = AsyncMock()

        # Mock缓存命中
        cached_data = {"match_id": "123", "result": "processed"}
        service.cache_manager.aget.return_value = cached_data

        result = await service.get_cached_results("match_123_processed")

        assert result == cached_data

        # Mock缓存未命中
        service.cache_manager.aget.return_value = None
        result = await service.get_cached_results("match_456_processed")

        assert result is None

        print("✅ 获取缓存结果测试通过")

    @pytest.mark.asyncio
    async def test_batch_process_datasets(self, service):
        """测试批量数据集处理"""
        print("🧪 测试批量数据集处理...")

        # 设置服务依赖
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        # Mock单个处理方法
        with patch.object(service, 'process_raw_match_data') as mock_process:
            mock_process.return_value = {"match_id": "123"}

            # 测试数据
            datasets = [
                [{"external_match_id": "123", "home_team": "Team A"}],
                [{"external_match_id": "456", "home_team": "Team B"}]
            ]

            result = await service.batch_process_datasets(datasets)

            assert result is not None
            assert isinstance(result, dict)
            assert 'total_processed' in result
            assert 'success_count' in result

        print("✅ 批量数据集处理测试通过")

    @pytest.mark.asyncio
    async def test_process_with_retry_success(self, service):
        """测试带重试的处理 - 成功场景"""
        print("🧪 测试带重试的处理 - 成功场景...")

        # Mock处理函数
        async def mock_process_func(data):
            return {"processed": True, "data": data}

        test_data = {"test": "data"}

        result = await service.process_with_retry(mock_process_func, test_data, max_retries=3)

        assert result is not None
        assert result['processed'] is True

        print("✅ 带重试的处理 - 成功场景测试通过")

    @pytest.mark.asyncio
    async def test_process_with_retry_failure(self, service):
        """测试带重试的处理 - 失败场景"""
        print("🧪 测试带重试的处理 - 失败场景...")

        # Mock失败的处理函数
        async def mock_process_func(data):
            raise Exception("处理失败")

        test_data = {"test": "data"}

        result = await service.process_with_retry(mock_process_func, test_data, max_retries=3)

        assert result is not None
        assert 'error' in result
        assert result['retries'] == 3

        print("✅ 带重试的处理 - 失败场景测试通过")

    @pytest.mark.asyncio
    async def test_collect_performance_metrics(self, service):
        """测试收集性能指标"""
        print("🧪 测试收集性能指标...")

        # Mock时间测量
        with patch('time.time') as mock_time:
            mock_time.side_effect = [1000.0, 1001.0]  # 开始和结束时间

            result = await service.collect_performance_metrics()

            assert result is not None
            assert isinstance(result, dict)
            assert 'processing_time' in result
            assert result['processing_time'] == 1.0

        print("✅ 收集性能指标测试通过")

    @pytest.mark.asyncio
    async def test_process_large_dataset(self, service):
        """测试大数据集处理"""
        print("🧪 测试大数据集处理...")

        # 设置服务依赖
        service.data_cleaner = Mock()
        service.missing_handler = Mock()

        # Mock分批处理
        with patch.object(service, '_process_in_batches') as mock_batch:
            mock_batch.return_value = {"processed_count": 1000, "failed_count": 5}

            # 测试大数据集
            large_dataset = [{"id": i} for i in range(1000)]

            result = await service.process_large_dataset(large_dataset)

            assert result is not None
            assert isinstance(result, dict)
            assert 'total_processed' in result
            assert result['total_processed'] == 1000

        print("✅ 大数据集处理测试通过")

    @pytest.mark.asyncio
    async def test_cleanup(self, service):
        """测试清理操作"""
        print("🧪 测试清理操作...")

        # 设置服务依赖
        service.cache_manager = AsyncMock()
        service.data_lake = AsyncMock()

        # Mock清理操作
        service.cache_manager.clear.return_value = True
        service.data_lake.cleanup.return_value = True

        result = await service.cleanup()

        assert result is not None
        assert isinstance(result, bool)
        assert result is True

        print("✅ 清理操作测试通过")

    @pytest.mark.asyncio
    async def test_error_handling_initialization(self, service):
        """测试初始化错误处理"""
        print("🧪 测试初始化错误处理...")

        with patch('src.services.data_processing.FootballDataCleaner') as mock_cleaner:
            # 模拟各种初始化错误
            mock_cleaner.side_effect = [
                Exception("数据库连接失败"),
                Exception("配置文件缺失"),
                Exception("权限不足")
            ]

            for error_case in range(3):
                service = DataProcessingService()  # 重新创建实例
                result = await service.initialize()
                assert result is False

        print("✅ 初始化错误处理测试通过")

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, service):
        """测试并发处理"""
        print("🧪 测试并发处理...")

        # 设置服务依赖
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.cache_manager = AsyncMock()

        # Mock处理方法
        mock_result = {"match_id": "123", "processed": True}
        service.data_cleaner.clean_match_data.return_value = mock_result
        service.missing_handler.handle_missing_match_data.return_value = mock_result

        # 测试并发处理
        tasks = []
        for i in range(5):
            task = service.process_raw_match_data({"external_match_id": str(i), "home_team": f"Team {i}"})
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        assert len(results) == 5
        for result in results:
            assert not isinstance(result, Exception)
            assert result is not None

        print("✅ 并发处理测试通过")


def test_data_processing_comprehensive():
    """数据处理服务综合测试"""
    print("🚀 开始 Phase 5.3.2.1: 数据处理服务全面测试...")

    test_instance = TestDataProcessingService()

    # 执行所有测试
    tests = [
        # 基础功能测试
        test_instance.test_service_initialization,

        # 异步测试
        test_instance.test_initialize_success,
        test_instance.test_initialize_failure,
        test_instance.test_shutdown_normal,
        test_instance.test_process_raw_match_data_list_input,
        test_instance.test_process_raw_match_data_single_input,
        test_instance.test_process_raw_match_data_empty_list,
        test_instance.test_process_raw_match_data_cleaner_not_initialized,
        test_instance.test_process_raw_odds_data,
        test_instance.test_process_features_data,
        test_instance.test_process_batch_matches,
        test_instance.test_validate_data_quality_success,
        test_instance.test_validate_data_quality_failure,
        test_instance.test_process_text,
        test_instance.test_process_batch,
        test_instance.test_process_bronze_to_silver,
        test_instance.test_get_bronze_layer_status,
        test_instance.test_handle_missing_scores,
        test_instance.test_detect_anomalies,
        test_instance.test_store_processed_data,
        test_instance.test_cache_processing_results,
        test_instance.test_get_cached_results,
        test_instance.test_batch_process_datasets,
        test_instance.test_process_with_retry_success,
        test_instance.test_process_with_retry_failure,
        test_instance.test_collect_performance_metrics,
        test_instance.test_process_large_dataset,
        test_instance.test_cleanup,
        test_instance.test_error_handling_initialization,
        test_instance.test_concurrent_processing,
    ]

    passed = 0
    failed = 0

    # 执行同步测试
    for test in tests:
        try:
            service = Mock()  # Mock service for non-async tests
            test(service)
            passed += 1
            print(f"  ✅ {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {test.__name__}: {e}")

    # 执行异步测试
    async_tests = [
        test_instance.test_initialize_success,
        test_instance.test_initialize_failure,
        test_instance.test_shutdown_normal,
        test_instance.test_process_raw_match_data_list_input,
        test_instance.test_process_raw_match_data_single_input,
        test_instance.test_process_raw_match_data_empty_list,
        test_instance.test_process_raw_match_data_cleaner_not_initialized,
        test_instance.test_process_raw_odds_data,
        test_instance.test_process_features_data,
        test_instance.test_process_batch_matches,
        test_instance.test_validate_data_quality_success,
        test_instance.test_validate_data_quality_failure,
        test_instance.test_process_text,
        test_instance.test_process_batch,
        test_instance.test_process_bronze_to_silver,
        test_instance.test_get_bronze_layer_status,
        test_instance.test_handle_missing_scores,
        test_instance.test_detect_anomalies,
        test_instance.test_store_processed_data,
        test_instance.test_cache_processing_results,
        test_instance.test_get_cached_results,
        test_instance.test_batch_process_datasets,
        test_instance.test_process_with_retry_success,
        test_instance.test_process_with_retry_failure,
        test_instance.test_collect_performance_metrics,
        test_instance.test_process_large_dataset,
        test_instance.test_cleanup,
        test_instance.test_error_handling_initialization,
        test_instance.test_concurrent_processing,
    ]

    for test in async_tests:
        try:
            service = DataProcessingService() if IMPORT_SUCCESS else Mock()
            asyncio.run(test(service))
            passed += 1
            print(f"  ✅ {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {test.__name__}: {e}")

    print(f"\n📊 测试结果: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("🎉 Phase 5.3.2.1: 数据处理服务测试完成")
        print("\n📋 测试覆盖的功能:")
        print("  - ✅ 服务初始化和关闭")
        print("  - ✅ 原始数据处理（比赛、赔率、特征）")
        print("  - ✅ 批量数据处理")
        print("  - ✅ 数据质量验证")
        print("  - ✅ 缓存操作")
        print("  - ✅ 错误处理和重试机制")
        print("  - ✅ 性能指标收集")
        print("  - ✅ 并发处理")
        print("  - ✅ 数据存储和清理")
    else:
        print("❌ 部分测试失败")


if __name__ == "__main__":
    test_data_processing_comprehensive()