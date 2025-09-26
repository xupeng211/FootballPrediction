"""
DataProcessingService Batch-Ω-009 测试套件

专门为 data_processing.py 设计的测试，目标是将其覆盖率从 7% 提升至 ≥70%
覆盖所有数据处理功能、清洗器集成、缓存操作、数据库交互等
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.services.data_processing import DataProcessingService


class TestDataProcessingServiceBatchOmega009:
    """DataProcessingService Batch-Ω-009 测试类"""

    @pytest.fixture
    def service(self):
        """创建 DataProcessingService 实例"""
        return DataProcessingService()

    @pytest.fixture
    def sample_raw_data(self):
        """示例原始数据"""
        return [
            {
                "match_id": 1001,
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2025-09-10",
                "league": "Premier League"
            },
            {
                "match_id": 1002,
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2025-09-11",
                "league": "Premier League"
            },
        ]

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return [
            {
                "match_id": 1001,
                "home_odds": 1.85,
                "draw_odds": 3.40,
                "away_odds": 4.20,
                "bookmaker": "Bet365"
            },
            {
                "match_id": 1002,
                "home_odds": 2.10,
                "draw_odds": 3.20,
                "away_odds": 3.60,
                "bookmaker": "William Hill"
            },
        ]

    @pytest.fixture
    def sample_dataframe(self):
        """示例DataFrame"""
        return pd.DataFrame([
            {
                "match_id": 1001,
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
            },
            {
                "match_id": 1002,
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 1,
                "away_score": 1,
            },
        ])

    def test_data_processing_service_initialization(self, service):
        """测试DataProcessingService初始化"""
        assert service.name == "DataProcessingService"
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.db_manager is None
        assert service.cache_manager is None

    def test_inheritance_from_base_service(self, service):
        """测试继承自BaseService"""
        from src.services.base import BaseService
        assert isinstance(service, BaseService)

    @pytest.mark.asyncio
    async def test_initialize_success(self, service):
        """测试初始化成功"""
        with patch('src.services.data_processing.FootballDataCleaner') as mock_cleaner, \
             patch('src.services.data_processing.MissingDataHandler') as mock_handler, \
             patch('src.services.data_processing.DataLakeStorage') as mock_lake, \
             patch('src.services.data_processing.DatabaseManager') as mock_db, \
             patch('src.services.data_processing.RedisManager') as mock_redis:

            mock_cleaner_instance = Mock()
            mock_handler_instance = Mock()
            mock_lake_instance = Mock()
            mock_db_instance = Mock()
            mock_redis_instance = Mock()

            mock_cleaner.return_value = mock_cleaner_instance
            mock_handler.return_value = mock_handler_instance
            mock_lake.return_value = mock_lake_instance
            mock_db.return_value = mock_db_instance
            mock_redis.return_value = mock_redis_instance

            result = await service.initialize()

            assert result is True
            assert service.data_cleaner == mock_cleaner_instance
            assert service.missing_handler == mock_handler_instance
            assert service.data_lake == mock_lake_instance
            assert service.db_manager == mock_db_instance
            assert service.cache_manager == mock_redis_instance

    @pytest.mark.asyncio
    async def test_initialize_failure(self, service):
        """测试初始化失败"""
        with patch('src.services.data_processing.FootballDataCleaner', side_effect=Exception("Init failed")):
            result = await service.initialize()

            assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_with_cache_manager(self, service):
        """测试关闭服务（有缓存管理器）"""
        # 先设置mock对象
        mock_cache = Mock()
        mock_cache.close = Mock()
        # 设置mock在async调用时抛出TypeError，然后会同步调用
        mock_cache.close.side_effect = [TypeError("Cannot await"), None]
        service.cache_manager = mock_cache
        service.db_manager = None

        await service.shutdown()

        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.cache_manager is None
        # 应该被调用了两次（一次async尝试，一次sync调用）
        assert mock_cache.close.call_count == 2

    @pytest.mark.asyncio
    async def test_shutdown_with_async_cache_manager(self, service):
        """测试关闭服务（异步缓存管理器）"""
        mock_cache = Mock()
        mock_cache.close = AsyncMock()
        mock_cache.close._mock_name = "async_mock"
        service.cache_manager = mock_cache
        service.db_manager = None

        await service.shutdown()

        mock_cache.close.assert_called_once()
        assert service.cache_manager is None

    @pytest.mark.asyncio
    async def test_shutdown_with_db_manager(self, service):
        """测试关闭服务（有数据库管理器）"""
        mock_db = Mock()
        mock_db.close = AsyncMock()
        service.db_manager = mock_db
        service.cache_manager = None

        await service.shutdown()

        assert service.db_manager is None
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_raw_match_data(self, service, sample_raw_data):
        """测试处理原始比赛数据"""
        # 初始化服务
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        # Mock the _process_single_match_data method
        with patch.object(service, '_process_single_match_data', new_callable=AsyncMock) as mock_process_single:
            mock_process_single.return_value = sample_raw_data[0]  # Return processed item

            result = await service.process_raw_match_data(sample_raw_data)

            # Should return a DataFrame for list input
            assert isinstance(result, pd.DataFrame)
            assert len(result) == len(sample_raw_data)
            assert mock_process_single.call_count == len(sample_raw_data)

    @pytest.mark.asyncio
    async def test_process_raw_odds_data(self, service, sample_odds_data):
        """测试处理原始赔率数据"""
        # 初始化服务
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        # 设置mock返回值
        service.data_cleaner.clean_odds_data.return_value = sample_odds_data
        service.missing_handler.handle_missing_odds.return_value = sample_odds_data
        service.data_lake.save_historical_data = AsyncMock(return_value="/path/to/file.parquet")
        service.db_manager.bulk_insert_raw_odds = AsyncMock(return_value=True)

        result = await service.process_raw_odds_data(sample_odds_data)

        assert result == sample_odds_data
        service.data_cleaner.clean_odds_data.assert_called_once_with(sample_odds_data)

    
    @pytest.mark.asyncio
    async def test_process_dataframe_matches(self, service, sample_dataframe):
        """测试处理DataFrame比赛数据"""
        # 初始化服务
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()

        # 设置mock返回值
        cleaned_df = sample_dataframe.copy()
        service.data_cleaner.clean_dataframe.return_value = cleaned_df
        service.missing_handler.handle_missing_dataframe.return_value = cleaned_df
        service.data_lake.save_historical_data = AsyncMock(return_value="/path/to/file.parquet")

        result = await service.process_dataframe_matches(sample_dataframe)

        assert result is True
        service.data_cleaner.clean_dataframe.assert_called_once()
        service.missing_handler.handle_missing_dataframe.assert_called_once()
        service.data_lake.save_historical_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_dataframe_with_cache(self, service, sample_dataframe):
        """测试处理DataFrame（使用缓存）"""
        # 初始化服务
        service.cache_manager = Mock()
        service.data_cleaner = Mock()
        service.missing_handler = Mock()

        # 设置缓存返回已缓存结果
        cache_key = f"matches_processing_{hash(str(sample_dataframe.to_dict()))}"
        cached_result = {"processed": True}
        service.cache_manager.get.return_value = cached_result

        result = await service.process_dataframe_matches(sample_dataframe)

        assert result is True
        service.cache_manager.get.assert_called_once()
        # 由于缓存命中，不应该调用处理器
        service.data_cleaner.clean_dataframe.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_raw_matches_data_empty(self, service):
        """测试处理空数据"""
        service.data_cleaner = Mock()
        service.data_cleaner.clean_match_data.return_value = []

        result = await service.process_raw_matches_data([])

        assert result is True
        service.data_cleaner.clean_match_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_raw_matches_data_error(self, service, sample_raw_data):
        """测试处理数据错误"""
        service.data_cleaner = Mock()
        service.data_cleaner.clean_match_data.side_effect = Exception("Processing failed")

        result = await service.process_raw_match_data(sample_raw_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_processed_data_statistics(self, service):
        """测试获取处理数据统计"""
        # 初始化服务
        service.data_lake = Mock()
        service.db_manager = Mock()

        # 设置mock返回值
        service.data_lake.get_table_stats.return_value = {
            "total_files": 5,
            "total_records": 1000,
            "total_size_mb": 10.5
        }
        service.db_manager.get_raw_data_stats.return_value = {
            "matches_count": 500,
            "odds_count": 300,
            "scores_count": 200
        }

        stats = await service.get_processed_data_statistics()

        assert isinstance(stats, dict)
        assert "data_lake" in stats
        assert "database" in stats
        assert "total_processed" in stats

    @pytest.mark.asyncio
    async def test_get_data_quality_report(self, service):
        """测试获取数据质量报告"""
        # 初始化服务
        service.data_cleaner = Mock()
        service.missing_handler = Mock()

        # 设置mock返回值
        service.data_cleaner.get_data_quality_metrics.return_value = {
            "completeness": 0.95,
            "accuracy": 0.98
        }
        service.missing_handler.get_missing_data_report.return_value = {
            "missing_rate": 0.05,
            "missing_fields": ["field1", "field2"]
        }

        report = await service.get_data_quality_report()

        assert isinstance(report, dict)
        assert "completeness" in report
        assert "missing_data" in report

    @pytest.mark.asyncio
    async def test_cleanup_old_data(self, service):
        """测试清理旧数据"""
        # 初始化服务
        service.data_lake = Mock()
        service.db_manager = Mock()

        # 设置mock返回值
        service.data_lake.cleanup_old_data.return_value = 5
        service.db_manager.cleanup_old_data.return_value = AsyncMock(return_value=3)

        result = await service.cleanup_old_data(days_to_keep=30)

        assert isinstance(result, dict)
        assert "data_lake_removed" in result
        assert "database_removed" in result
        assert result["data_lake_removed"] == 5
        assert result["database_removed"] == 3

    @pytest.mark.asyncio
    async def test_reprocess_failed_data(self, service):
        """测试重新处理失败数据"""
        # 初始化服务
        service.db_manager = Mock()
        service.data_cleaner = Mock()

        # 设置mock返回值
        failed_data = [{"match_id": 1001, "status": "failed"}]
        service.db_manager.get_failed_processing_data.return_value = failed_data
        service.data_cleaner.clean_match_data.return_value = [{"match_id": 1001, "status": "processed"}]

        result = await service.reprocess_failed_data()

        assert result is True
        service.db_manager.get_failed_processing_data.assert_called_once()
        service.data_cleaner.clean_match_data.assert_called_once()

    def test_service_name_property(self, service):
        """测试服务名称属性"""
        assert service.name == "DataProcessingService"

    def test_service_components_initial_state(self, service):
        """测试服务组件初始状态"""
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.db_manager is None
        assert service.cache_manager is None

    @pytest.mark.asyncio
    async def test_initialization_logging(self, service):
        """测试初始化日志记录"""
        with patch('src.services.data_processing.FootballDataCleaner') as mock_cleaner, \
             patch('src.services.data_processing.MissingDataHandler') as mock_handler, \
             patch('src.services.data_processing.DataLakeStorage') as mock_lake, \
             patch('src.services.data_processing.DatabaseManager') as mock_db, \
             patch('src.services.data_processing.RedisManager') as mock_redis:

            await service.initialize()

            # 验证日志消息被记录
            assert service.logger.info.called

    @pytest.mark.asyncio
    async def test_shutdown_logging(self, service):
        """测试关闭日志记录"""
        service.cache_manager = None
        service.db_manager = None

        await service.shutdown()

        # 验证日志消息被记录
        assert service.logger.info.called

    @pytest.mark.asyncio
    async def test_process_with_error_handling(self, service, sample_raw_data):
        """测试处理过程中的错误处理"""
        # 初始化服务
        service.data_cleaner = Mock()
        service.data_cleaner.clean_match_data.side_effect = Exception("Unexpected error")

        result = await service.process_raw_match_data(sample_raw_data)

        assert result is False
        # 验证错误被记录
        assert service.logger.error.called

    @pytest.mark.asyncio
    async def test_data_validation_before_processing(self, service):
        """测试处理前的数据验证"""
        # 测试无效数据类型
        invalid_data = "invalid data type"

        result = await service.process_raw_matches_data(invalid_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_concurrent_processing_support(self, service, sample_raw_data):
        """测试并发处理支持"""
        # 初始化服务
        service.data_cleaner = Mock()
        service.data_cleaner.clean_match_data.return_value = sample_raw_data
        service.missing_handler = Mock()
        service.missing_handler.handle_missing_matches.return_value = sample_raw_data
        service.data_lake = Mock()
        service.data_lake.save_historical_data = AsyncMock(return_value="/path/to/file.parquet")
        service.db_manager = Mock()
        service.db_manager.bulk_insert_raw_matches = AsyncMock(return_value=True)

        # 并发处理多个数据集
        tasks = []
        for i in range(3):
            task = service.process_raw_matches_data(sample_raw_data)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有任务都完成
        assert len(results) == 3
        for result in results:
            if not isinstance(result, Exception):
                assert result is True

    @pytest.mark.asyncio
    async def test_memory_efficiency_large_dataset(self, service):
        """测试大数据集内存效率"""
        # 创建大型数据集
        large_dataset = [{"match_id": i, "data": f"match_{i}"} for i in range(1000)]

        # 初始化服务
        service.data_cleaner = Mock()
        service.data_cleaner.clean_match_data.return_value = large_dataset
        service.missing_handler = Mock()
        service.missing_handler.handle_missing_matches.return_value = large_dataset
        service.data_lake = Mock()
        service.data_lake.save_historical_data = AsyncMock(return_value="/path/to/file.parquet")
        service.db_manager = Mock()
        service.db_manager.bulk_insert_raw_matches = AsyncMock(return_value=True)

        result = await service.process_raw_matches_data(large_dataset)

        assert result is True

    @pytest.mark.asyncio
    async def test_service_health_check(self, service):
        """测试服务健康检查"""
        # 初始化服务
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        health_status = await service.get_health_status()

        assert isinstance(health_status, dict)
        assert "status" in health_status
        assert "components" in health_status

    @pytest.mark.asyncio
    async def test_batch_processing_optimization(self, service, sample_raw_data):
        """测试批处理优化"""
        # 初始化服务
        service.data_cleaner = Mock()
        service.data_cleaner.clean_match_data.return_value = sample_raw_data
        service.missing_handler = Mock()
        service.missing_handler.handle_missing_matches.return_value = sample_raw_data
        service.data_lake = Mock()
        service.data_lake.save_historical_data = AsyncMock(return_value="/path/to/file.parquet")
        service.db_manager = Mock()
        service.db_manager.bulk_insert_raw_matches = AsyncMock(return_value=True)

        # 批量处理
        batch_size = 100
        batches = [sample_raw_data] * batch_size

        results = []
        for batch in batches:
            result = await service.process_raw_matches_data(batch)
            results.append(result)

        # 验证所有批次处理成功
        assert all(results)

    @pytest.mark.asyncio
    async def test_data_pipeline_integration(self, service, sample_raw_data):
        """测试数据管道集成"""
        # 初始化服务
        service.data_cleaner = Mock()
        service.data_cleaner.clean_match_data.return_value = sample_raw_data
        service.missing_handler = Mock()
        service.missing_handler.handle_missing_matches.return_value = sample_raw_data
        service.data_lake = Mock()
        service.data_lake.save_historical_data = AsyncMock(return_value="/path/to/file.parquet")
        service.db_manager = Mock()
        service.db_manager.bulk_insert_raw_matches = AsyncMock(return_value=True)

        # 测试完整的数据处理管道
        pipeline_result = await service.execute_data_pipeline(
            data=sample_raw_data,
            pipeline_steps=["clean", "validate", "store"]
        )

        assert pipeline_result is True
        service.data_cleaner.clean_match_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, service, sample_raw_data):
        """测试性能监控"""
        import time

        # 初始化服务
        service.data_cleaner = Mock()
        service.data_cleaner.clean_match_data.return_value = sample_raw_data
        service.missing_handler = Mock()
        service.missing_handler.handle_missing_matches.return_value = sample_raw_data
        service.data_lake = Mock()
        service.data_lake.save_historical_data = AsyncMock(return_value="/path/to/file.parquet")
        service.db_manager = Mock()
        service.db_manager.bulk_insert_raw_matches = AsyncMock(return_value=True)

        start_time = time.time()
        result = await service.process_raw_match_data(sample_raw_data)
        end_time = time.time()

        assert result is True
        processing_time = end_time - start_time
        assert processing_time < 10.0  # 处理时间应该在合理范围内

    def test_service_configuration_validation(self, service):
        """测试服务配置验证"""
        # 验证服务配置
        config = service.get_service_config()

        assert isinstance(config, dict)
        assert "service_name" in config
        assert "supported_data_types" in config
        assert "processing_stages" in config

    @pytest.mark.asyncio
    async def test_data_integrity_checks(self, service, sample_raw_data):
        """测试数据完整性检查"""
        # 初始化服务
        service.data_cleaner = Mock()
        service.data_cleaner.clean_match_data.return_value = sample_raw_data
        service.missing_handler = Mock()
        service.missing_handler.handle_missing_matches.return_value = sample_raw_data

        integrity_result = await service.validate_data_integrity(sample_raw_data)

        assert isinstance(integrity_result, dict)
        assert "is_valid" in integrity_result
        assert "issues" in integrity_result

    @pytest.mark.asyncio
    async def test_service_restart_capability(self, service):
        """测试服务重启能力"""
        # 初始化服务
        await service.initialize()

        # 验证服务已初始化
        assert service.data_cleaner is not None

        # 关闭服务
        await service.shutdown()

        # 验证服务已关闭
        assert service.data_cleaner is None

        # 重新初始化
        await service.initialize()

        # 验证服务重新初始化成功
        assert service.data_cleaner is not None