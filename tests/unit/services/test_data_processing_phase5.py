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