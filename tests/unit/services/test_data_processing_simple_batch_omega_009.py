"""
DataProcessingService Batch-Ω-009 测试套件 - 精简版

专门为 data_processing.py 设计的测试，目标是将其覆盖率从 7% 提升至 ≥70%
只测试实际存在的方法，确保测试稳定运行
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
            },
            {
                "match_id": 1002,
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2025-09-11",
            },
        ]

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return [
            {
                "match_id": 1001,
                "bookmaker": "Bet365",
                "home_odds": 1.85,
                "draw_odds": 3.4,
                "away_odds": 4.2,
                "home_implied_prob": 0.54,
                "draw_implied_prob": 0.29,
                "away_implied_prob": 0.24,
            },
            {
                "match_id": 1002,
                "bookmaker": "William Hill",
                "home_odds": 2.1,
                "draw_odds": 3.2,
                "away_odds": 3.6,
                "home_implied_prob": 0.48,
                "draw_implied_prob": 0.31,
                "away_implied_prob": 0.27,
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

    def test_service_initialization(self, service):
        """测试服务初始化"""
    assert service.name == "DataProcessingService"
    assert service.data_cleaner is None
    assert service.missing_handler is None
    assert service.data_lake is None
    assert service.cache_manager is None
    assert service.db_manager is None
    assert service.logger is not None

    @pytest.mark.asyncio
    async def test_initialize_success(self, service):
        """测试初始化成功"""
        with patch('src.services.data_processing.FootballDataCleaner') as mock_cleaner, \
             patch('src.services.data_processing.MissingDataHandler') as mock_handler:

            mock_cleaner_instance = Mock()
            mock_handler_instance = Mock()
            mock_cleaner.return_value = mock_cleaner_instance
            mock_handler.return_value = mock_handler_instance

            result = await service.initialize()

    assert result is True
    assert service.data_cleaner == mock_cleaner_instance
    assert service.missing_handler == mock_handler_instance

    @pytest.mark.asyncio
    async def test_initialize_failure(self, service):
        """测试初始化失败"""
        with patch('src.services.data_processing.FootballDataCleaner') as mock_cleaner:
            mock_cleaner.side_effect = Exception("Initialization failed")

            result = await service.initialize()

    assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_with_cache_manager(self, service):
        """测试关闭服务（有缓存管理器）"""
        mock_cache = Mock()
        mock_cache.close = Mock()
        mock_cache.close.side_effect = [TypeError("Cannot await"), None]
        service.cache_manager = mock_cache
        service.db_manager = None

        await service.shutdown()

    assert service.data_cleaner is None
    assert service.missing_handler is None
    assert service.data_lake is None
    assert service.cache_manager is None
    assert service.db_manager is None

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
    async def test_shutdown_with_async_cache_manager(self, service):
        """测试关闭服务（异步缓存管理器）"""
        mock_cache = Mock()
        mock_cache.close = AsyncMock()
        service.cache_manager = mock_cache
        service.db_manager = None

        await service.shutdown()

    assert service.cache_manager is None
        mock_cache.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_raw_match_data_list_input(self, service, sample_raw_data):
        """测试处理原始比赛数据（列表输入）"""
        service.data_cleaner = Mock()

        with patch.object(service, '_process_single_match_data', new_callable=AsyncMock) as mock_process_single:
            mock_process_single.return_value = sample_raw_data[0]

            result = await service.process_raw_match_data(sample_raw_data)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == len(sample_raw_data)
    assert mock_process_single.call_count == len(sample_raw_data)

    @pytest.mark.asyncio
    async def test_process_raw_match_data_dict_input(self, service, sample_raw_data):
        """测试处理原始比赛数据（字典输入）"""
        service.data_cleaner = Mock()
        single_data = sample_raw_data[0]

        with patch.object(service, '_process_single_match_data', new_callable=AsyncMock) as mock_process_single:
            mock_process_single.return_value = single_data

            result = await service.process_raw_match_data(single_data)

    assert result == single_data
            mock_process_single.assert_called_once_with(single_data)

    @pytest.mark.asyncio
    async def test_process_raw_match_data_empty_list(self, service):
        """测试处理空列表数据"""
        service.data_cleaner = Mock()

        result = await service.process_raw_match_data([])

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0

    @pytest.mark.asyncio
    async def test_process_raw_match_data_no_cleaner(self, service, sample_raw_data):
        """测试无数据清洗器的情况"""
        service.data_cleaner = None

        result = await service.process_raw_match_data(sample_raw_data)

    assert result is None

    @pytest.mark.asyncio
    async def test_process_raw_match_data_exception(self, service, sample_raw_data):
        """测试处理异常情况"""
        service.data_cleaner = Mock()

        with patch.object(service, '_process_single_match_data', new_callable=AsyncMock) as mock_process_single:
            mock_process_single.side_effect = Exception("Processing failed")

            result = await service.process_raw_match_data(sample_raw_data)

    assert result is None

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_success(self, service, sample_odds_data):
        """测试处理赔率数据成功"""
        service.data_cleaner = Mock()
        service.data_cleaner.clean_odds_data.return_value = sample_odds_data

        result = await service.process_raw_odds_data(sample_odds_data)

    assert result == sample_odds_data
        service.data_cleaner.clean_odds_data.assert_called_once_with(sample_odds_data)

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_async_cleaner(self, service, sample_odds_data):
        """测试异步数据清洗器"""
        service.data_cleaner = Mock()
        async def async_clean(*args):
            return sample_odds_data
        service.data_cleaner.clean_odds_data.return_value = async_clean()

        result = await service.process_raw_odds_data(sample_odds_data)

    assert result == sample_odds_data

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_no_cleaner(self, service, sample_odds_data):
        """测试无数据清洗器的情况"""
        service.data_cleaner = None

        result = await service.process_raw_odds_data(sample_odds_data)

    assert result == []

    @pytest.mark.asyncio
    async def test_process_raw_odds_data_exception(self, service, sample_odds_data):
        """测试处理异常情况"""
        service.data_cleaner = Mock()
        service.data_cleaner.clean_odds_data.side_effect = Exception("Cleaning failed")

        result = await service.process_raw_odds_data(sample_odds_data)

    assert result == []

    @pytest.mark.asyncio
    async def test_process_features_data_basic(self, service, sample_dataframe):
        """测试处理特征数据基本功能"""
        service.missing_handler = Mock()

        result = await service.process_features_data(1001, sample_dataframe)

    assert result is sample_dataframe  # Should return the same DataFrame if no missing handler

    @pytest.mark.asyncio
    async def test_process_features_data_with_missing_handler(self, service, sample_dataframe):
        """测试处理特征数据（有缺失值处理器）"""
        service.missing_handler = Mock()
        service.missing_handler.handle_missing_features = AsyncMock(return_value=sample_dataframe)

        result = await service.process_features_data(1001, sample_dataframe)

    assert result == sample_dataframe
        service.missing_handler.handle_missing_features.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_features_data_no_missing_handler(self, service, sample_dataframe):
        """测试无缺失值处理器的情况"""
        service.missing_handler = None

        result = await service.process_features_data(1001, sample_dataframe)

    assert result is sample_dataframe

    @pytest.mark.asyncio
    async def test__process_single_match_data_basic(self, service, sample_raw_data):
        """测试处理单个比赛数据基本功能"""
        single_data = sample_raw_data[0]
        service.data_cleaner = Mock()
        service.missing_handler = Mock()
        service.data_lake = Mock()
        service.db_manager = Mock()

        service.data_cleaner.clean_match_data.return_value = single_data
        service.missing_handler.handle_missing_match_data.return_value = single_data
        service.data_lake.save_historical_data = AsyncMock()
        service.db_manager.bulk_insert_raw_matches = AsyncMock(return_value=True)

        result = await service._process_single_match_data(single_data)

    assert result == single_data

    
    @pytest.mark.asyncio
    async def test_handle_missing_scores_with_dataframe(self, service):
        """测试处理缺失比分数据"""
        service.missing_handler = Mock()
        test_df = pd.DataFrame({"match_id": [1, 2], "home_score": [1, None]})
        service.missing_handler.interpolate_scores.return_value = test_df

        result = await service.handle_missing_scores(test_df)

    assert result is not None
        service.missing_handler.interpolate_scores.assert_called_once_with(test_df)

    @pytest.mark.asyncio
    async def test_handle_missing_scores_no_handler(self, service):
        """测试无缺失值处理器的情况"""
        service.missing_handler = None
        test_df = pd.DataFrame({"match_id": [1, 2], "home_score": [1, None]})

        result = await service.handle_missing_scores(test_df)

    assert result is None

    @pytest.mark.asyncio
    async def test_detect_anomalies_basic(self, service, sample_dataframe):
        """测试异常检测基本功能"""
        result = await service.detect_anomalies(sample_dataframe)

    assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_collect_performance_metrics(self, service):
        """测试收集性能指标"""
        async def mock_processing_function(*args, **kwargs):
            return [1, 2, 3]  # 模拟处理结果

        result = await service.collect_performance_metrics(mock_processing_function)

    assert isinstance(result, dict)
    assert "total_time" in result
    assert "items_processed" in result
    assert "items_per_second" in result

    @pytest.mark.asyncio
    async def test_cleanup_basic(self, service):
        """测试清理基本功能"""
        result = await service.cleanup()

    assert isinstance(result, bool)

    def test_service_repr(self, service):
        """测试服务字符串表示"""
        repr_str = repr(service)
    assert "DataProcessingService" in repr_str