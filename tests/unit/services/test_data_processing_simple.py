"""
数据处理服务简化测试 / Data Processing Service Simple Tests

测试数据处理服务的核心功能，使用简化的测试方法
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

from src.services.data_processing import DataProcessingService


@pytest.mark.asyncio
class TestDataProcessingServiceSimple:
    """数据处理服务简化测试类"""

    @pytest.fixture
    def service(self):
        """创建数据处理服务实例"""
        service = DataProcessingService()
        service.logger = MagicMock()
        return service

    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return {
            "match_id": "match_123",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "home_score": 2,
            "away_score": 1,
            "match_date": "2024-01-15T15:00:00Z",
            "league": "Premier League",
        }

    @pytest.fixture
    def sample_dataframe(self):
        """示例DataFrame"""
        return pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "home_team": ["Team A", "Team B", "Team C"],
                "away_team": ["Team X", "Team Y", "Team Z"],
                "home_score": [2, 1, 0],
                "away_score": [1, 1, 2],
            }
        )

    # === 初始化测试 ===

    async def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.name == "DataProcessingService"
        assert service.logger is not None

    async def test_initialize_components(self, service):
        """测试初始化各个组件"""
        result = await service.initialize()

        assert result is True
        assert service.data_cleaner is not None
        assert service.missing_handler is not None
        assert service.data_lake is not None
        assert service.db_manager is not None
        assert service.cache_manager is not None

    async def test_initialize_failure(self, service):
        """测试初始化失败"""
        with patch(
            "src.services.data_processing.DataLakeStorage",
            side_effect=Exception("Storage initialization failed"),
        ):
            service.logger = MagicMock()
            result = await service.initialize()

            assert result is False
            service.logger.error.assert_called()

    # === 数据处理核心功能测试 ===

    async def test_process_raw_match_data(self, service, sample_match_data):
        """测试处理原始比赛数据"""
        await service.initialize()

        # Mock相关方法
        service.data_cleaner.clean_match_data = MagicMock(
            return_value=sample_match_data
        )
        service.missing_handler.handle_missing_values = MagicMock(
            return_value=sample_match_data
        )
        service.data_lake.store = MagicMock(return_value=True)

        result = await service.process_raw_match_data(sample_match_data)

        assert result is not None
        service.data_cleaner.clean_match_data.assert_called_once()

    async def test_process_raw_match_data_list(self, service, sample_match_data):
        """测试处理比赛数据列表"""
        await service.initialize()

        data_list = [sample_match_data, sample_match_data]

        # Mock相关方法
        service.data_cleaner.clean_match_data = MagicMock(side_effect=data_list)
        service.missing_handler.handle_missing_values = MagicMock(side_effect=data_list)

        result = await service.process_raw_match_data(data_list)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    async def test_process_raw_match_data_uninitialized(
        self, service, sample_match_data
    ):
        """测试未初始化时处理数据"""
        service.data_cleaner = None

        result = await service.process_raw_match_data(sample_match_data)

        assert result is None
        service.logger.error.assert_called_with("数据清洗器未初始化")

    async def test_process_raw_odds_data(self, service):
        """测试处理赔率数据"""
        await service.initialize()

        odds_data = {
            "match_id": "match_123",
            "home_win": 2.10,
            "draw": 3.40,
            "away_win": 3.20,
        }

        # Mock相关方法
        service.data_cleaner.clean_odds_data = MagicMock(return_value=odds_data)
        service.data_lake.store = MagicMock(return_value=True)

        result = await service.process_raw_odds_data(odds_data)

        assert result is not None
        service.data_cleaner.clean_odds_data.assert_called_once()

    async def test_process_features_data(self, service):
        """测试处理特征数据"""
        await service.initialize()

        # 创建特征DataFrame
        features_df = pd.DataFrame(
            {"match_id": [123], "home_form": [[1, 0, 1]], "away_form": [[0, 1, 0]]}
        )

        # Mock处理方法
        service.missing_handler.handle_missing_features = AsyncMock(
            return_value=features_df
        )

        result = await service.process_features_data(123, features_df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    async def test_process_batch_matches(self, service, sample_dataframe):
        """测试批量处理比赛数据"""
        await service.initialize()

        # 转换DataFrame为字典列表
        matches_list = sample_dataframe.to_dict("records")

        # Mock process_raw_match_data方法
        service.process_raw_match_data = AsyncMock(side_effect=matches_list)

        result = await service.process_batch_matches(matches_list)

        assert len(result) == 3
        assert result[0]["match_id"] == 1

    # === 数据质量验证测试 ===

    async def test_validate_data_quality(self, service, sample_match_data):
        """测试数据质量验证"""
        await service.initialize()

        # 创建包含必需字段的数据
        valid_match_data = {
            "external_match_id": "123",
            "home_team_id": 1,
            "away_team_id": 2,
            "match_time": "2024-01-15T15:00:00Z",
        }

        result = await service.validate_data_quality(valid_match_data, "match")

        assert result["is_valid"] is True
        assert result["data_type"] == "match"
        assert len(result["issues"]) == 0

    async def test_validate_data_quality_with_errors(self, service):
        """测试数据质量验证失败"""
        await service.initialize()

        invalid_data = {"home_team": "", "away_team": None}

        result = await service.validate_data_quality(invalid_data, "match")

        assert result["is_valid"] is False
        assert len(result["issues"]) > 0  # 应该有缺失字段的问题

    # === Bronze到Silver层处理测试 ===

    async def test_process_bronze_to_silver(self, service):
        """测试Bronze到Silver层数据处理"""
        await service.initialize()

        # Mock内部方法
        service._process_raw_matches_bronze_to_silver = AsyncMock(return_value=50)
        service._process_raw_odds_bronze_to_silver = AsyncMock(return_value=30)
        service._process_raw_scores_bronze_to_silver = AsyncMock(return_value=20)

        result = await service.process_bronze_to_silver(batch_size=100)

        assert result["processed_matches"] == 50
        assert result["processed_odds"] == 30
        assert result["processed_scores"] == 20
        assert result["errors"] == 0

    async def test_get_bronze_layer_status(self, service):
        """测试获取Bronze层状态"""
        await service.initialize()

        # Mock数据库查询
        mock_session = MagicMock()

        # Mock数据库查询
        # 需要mock session.query(RawMatchData).count() 和 session.query(RawMatchData).filter(...).count()
        mock_query_total = MagicMock()
        mock_query_total.count.return_value = 1000  # match_total

        mock_query_processed = MagicMock()
        mock_query_processed.count.return_value = 800  # match_processed

        mock_filter = MagicMock()
        mock_filter.count.return_value = 800

        mock_query = MagicMock()
        mock_query.count.side_effect = [
            1000,
            500,
            300,
        ]  # match_total, odds_total, scores_total
        mock_query.filter.return_value = mock_filter

        # 为RawMatchData, RawOddsData, RawScoresData分别设置mock
        def mock_query_func(model):
            if "RawMatchData" in str(model):
                return mock_query
            elif "RawOddsData" in str(model):
                mock_odds = MagicMock()
                mock_odds.count.return_value = 500
                mock_odds.filter.return_value.count.return_value = 400
                return mock_odds
            else:  # RawScoresData
                mock_scores = MagicMock()
                mock_scores.count.return_value = 300
                mock_scores.filter.return_value.count.return_value = 200
                return mock_scores

        mock_session.query = mock_query_func
        service.db_manager.get_session = MagicMock()
        service.db_manager.get_session.return_value.__enter__.return_value = (
            mock_session
        )
        service.db_manager.get_session.return_value.__exit__.return_value = None

        status = await service.get_bronze_layer_status()

        assert status["matches"]["total"] == 1000
        assert status["matches"]["processed"] == 800
        assert status["matches"]["pending"] == 200
        assert status["odds"]["total"] == 500
        assert status["odds"]["processed"] == 400
        assert status["odds"]["pending"] == 100
        assert status["scores"]["total"] == 300
        assert status["scores"]["processed"] == 200
        assert status["scores"]["pending"] == 100

    # === 缺失值处理测试 ===

    async def test_handle_missing_scores(self, service):
        """测试处理缺失比分"""
        await service.initialize()

        # 创建带缺失值的DataFrame
        data_with_missing = pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "home_score": [2, None, 1],
                "away_score": [1, None, 2],
            }
        )

        # Mock处理方法
        filled_data = pd.DataFrame(
            {"match_id": [1, 2, 3], "home_score": [2, 1, 1], "away_score": [1, 1, 2]}
        )
        service.missing_handler.interpolate_scores = MagicMock(return_value=filled_data)

        result = await service.handle_missing_scores(data_with_missing)

        assert result is not None
        assert len(result) == 3
        assert result["home_score"].isna().sum() == 0

    async def test_handle_missing_team_data(self, service):
        """测试处理缺失球队数据"""
        await service.initialize()

        # 创建DataFrame
        team_data = pd.DataFrame(
            {
                "team_id": [1, 2],
                "team_name": ["Team A", None],
                "league": ["Premier League", None],
            }
        )

        # Mock处理方法
        service.missing_handler.handle_missing_teams = AsyncMock(return_value=team_data)

        result = await service.handle_missing_team_data(team_data)

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    # === 异常检测测试 ===

    async def test_detect_anomalies(self, service, sample_dataframe):
        """测试异常检测"""
        await service.initialize()

        # Mock异常检测方法
        anomalies = [
            {"index": 1, "field": "home_score", "value": 10, "reason": "Too high"},
            {"index": 2, "field": "away_score", "value": -1, "reason": "Negative"},
        ]
        service.missing_handler.detect_anomalies = MagicMock(return_value=anomalies)

        result = await service.detect_anomalies(sample_dataframe)

        assert len(result) == 2
        assert result[0]["field"] == "home_score"
        assert result[1]["reason"] == "Negative"

    # === 缓存管理测试 ===

    async def test_cache_processing_results(self, service):
        """测试缓存处理结果"""
        await service.initialize()

        result_data = {"match_id": "123", "processed": True}
        cache_key = "test_key"

        # Mock缓存方法
        service.cache_manager.set_json = MagicMock(return_value=True)

        result = await service.cache_processing_results(cache_key, result_data)

        assert result is True
        service.cache_manager.set_json.assert_called_once_with(
            cache_key, result_data, ttl=3600
        )

    async def test_get_cached_results(self, service):
        """测试获取缓存结果"""
        await service.initialize()

        cache_key = "test_key"
        cached_data = {"match_id": "123", "processed": True}

        # Mock缓存方法
        service.cache_manager.get_json = MagicMock(return_value=cached_data)

        result = await service.get_cached_results(cache_key)

        assert result == cached_data
        service.cache_manager.get_json.assert_called_once_with(cache_key)

    # === 批量处理测试 ===

    async def test_process_batch(self, service):
        """测试批量处理"""
        await service.initialize()

        data_list = [{"id": 1}, {"id": 2}, {"id": 3}, "text_data", 123]

        # Mock处理文本方法
        service.process_text = AsyncMock(
            return_value={"text": "text_data", "processed": True}
        )

        results = await service.process_batch(data_list)

        assert len(results) == 5
        assert results[0]["processed"] is True
        assert results[1]["processed"] is True
        assert results[2]["processed"] is True
        assert results[3]["text"] == "text_data"
        assert "original_data" in results[4]

    async def test_batch_process_datasets(self, service):
        """测试批量处理多个数据集"""
        await service.initialize()

        datasets = {"matches": [{"id": 1}, {"id": 2}], "odds": [{"id": 1}]}

        # Mock批量处理方法
        service.process_batch_matches = AsyncMock(
            return_value=[{"id": 1, "processed": True}, {"id": 2, "processed": True}]
        )
        service.process_raw_odds_data = AsyncMock(
            side_effect=[
                {"id": 1, "home_team": "Team A"},
                {"id": 2, "away_team": "Team B"},
            ]
        )

        results = await service.batch_process_datasets(datasets)

        assert "processed_counts" in results
        assert "matches" in results["processed_counts"]
        assert "odds" in results["processed_counts"]
        assert results["processed_counts"]["matches"] == 2
        assert results["processed_counts"]["odds"] == 2
        assert results["total_processed"] == 4
        assert results["errors"] == {}

    # === 重试机制测试 ===

    async def test_process_with_retry_success(self, service):
        """测试重试机制成功"""

        async def process_func(data):
            return {"processed": True, "data": data}

        result = await service.process_with_retry(
            process_func, {"test": "data"}, max_retries=3
        )

        assert result["processed"] is True

    async def test_process_with_retry_failure(self, service):
        """测试重试机制失败"""

        async def failing_process_func(data):
            raise ValueError("Processing failed")

        with pytest.raises(RuntimeError):
            await service.process_with_retry(
                failing_process_func, {"test": "data"}, max_retries=2
            )

    # === 文本处理测试 ===

    async def test_process_text(self, service):
        """测试文本处理"""
        await service.initialize()

        text = "Manchester United 2-1 Liverpool"

        result = await service.process_text(text)

        assert result["processed_text"] == "Manchester United 2-1 Liverpool"
        assert result["word_count"] == 4
        assert result["character_count"] == 31

    # === 清理功能测试 ===

    async def test_cleanup(self, service):
        """测试清理功能"""
        await service.initialize()

        # Mock清理方法
        service.cache_manager.flush_all = MagicMock()
        service.data_lake.cleanup_temp_files = MagicMock()

        result = await service.cleanup()

        assert result is True

    # === 健康检查测试 ===

    async def test_health_check(self, service):
        """测试健康检查"""
        # 简化测试 - 只验证初始化后的状态
        await service.initialize()

        # 验证组件已初始化
        assert service.data_cleaner is not None
        assert service.missing_handler is not None
        assert service.data_lake is not None
        assert service.db_manager is not None
        assert service.cache_manager is not None

    # === 错误处理测试 ===

    async def test_store_processed_data_success(self, service):
        """测试存储处理后的数据成功"""
        await service.initialize()

        processed_data = pd.DataFrame({"match_id": ["123"], "features": [{}]})
        table_name = "processed_matches"

        # Mock存储成功
        service.data_lake.store = MagicMock(return_value=True)

        result = await service.store_processed_data(processed_data, table_name)

        assert result is True

    async def test_store_processed_data_failure(self, service):
        """测试存储处理后的数据失败"""
        await service.initialize()

        processed_data = pd.DataFrame({"match_id": ["123"], "features": [{}]})
        table_name = "processed_matches"

        # Mock存储失败，但mock其他存储方式成功
        service.data_lake.store_dataframe = MagicMock(
            side_effect=Exception("Storage failed")
        )
        # Mock bulk_insert也失败，但data_lake.store_dataframe会尝试
        service.db_manager.bulk_insert = MagicMock(side_effect=Exception("DB failed"))

        result = await service.store_processed_data(processed_data, table_name)

        # 当所有存储方式都失败时，返回False
        assert result is False

    async def test_collect_performance_metrics(self, service):
        """测试收集性能指标"""
        await service.initialize()

        # 定义一个测试函数
        async def test_function(data):
            await asyncio.sleep(0.01)  # 模拟处理时间
            return {"processed": True, "data": data}

        # 测试数据
        test_data = {"test": "data"}

        metrics = await service.collect_performance_metrics(test_function, test_data)

        assert "total_time" in metrics
        assert "items_processed" in metrics
        assert "items_per_second" in metrics
        assert metrics["total_time"] > 0
        assert metrics["items_processed"] == 1
