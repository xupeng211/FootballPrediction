"""
数据处理服务测试 / Data Processing Service Tests

测试数据处理服务的核心功能：
- 数据清洗和标准化
- 缺失值处理
- 数据质量验证
- 特征数据准备
- 批量数据处理
- 缓存管理
- 异常检测
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.services.data_processing import DataProcessingService


@pytest.mark.asyncio
class TestDataProcessingService:
    """数据处理服务测试类"""

    @pytest.fixture
    def mock_service(self):
        """创建模拟的数据处理服务"""
        service = DataProcessingService()
        service.logger = MagicMock()
        service.data_cleaner = MagicMock()
        service.missing_handler = MagicMock()
        service.data_lake = MagicMock()
        service.db_manager = MagicMock()
        service.cache_manager = MagicMock()
        return service

    @pytest.fixture
    def sample_raw_match_data(self):
        """示例原始比赛数据"""
        return {
            "match_id": "match_123",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "home_score": 2,
            "away_score": 1,
            "match_date": "2024-01-15T15:00:00Z",
            "league": "Premier League",
            "season": "2023-2024",
            "venue": "Old Trafford",
            "attendance": 73000,
            "referee": "Michael Oliver",
        }

    @pytest.fixture
    def sample_raw_odds_data(self):
        """示例原始赔率数据"""
        return {
            "match_id": "match_123",
            "home_win_odds": 2.10,
            "draw_odds": 3.40,
            "away_win_odds": 3.20,
            "over_under_2_5": 1.85,
            "both_teams_score": 1.65,
            "bookmaker": "Bet365",
            "timestamp": "2024-01-14T10:00:00Z",
        }

    @pytest.fixture
    def sample_dataframe(self):
        """示例DataFrame数据"""
        return pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "home_team": ["Team A", "Team B", "Team C"],
                "away_team": ["Team X", "Team Y", "Team Z"],
                "home_score": [2, 1, 0],
                "away_score": [1, 1, 2],
                "date": pd.date_range("2024-01-01", periods=3),
            }
        )

    # === 初始化相关测试 ===

    async def test_service_initialization(self, mock_service):
        """测试服务初始化"""
        assert mock_service.name == "DataProcessingService"
        assert mock_service.data_cleaner is not None
        assert mock_service.missing_handler is not None
        assert mock_service.data_lake is not None
        assert mock_service.db_manager is not None
        assert mock_service.cache_manager is not None

    async def test_initialize_success(self, mock_service):
        """测试成功初始化"""
        # 重新创建实例，这样initialize会实际运行
        service = DataProcessingService()
        service.logger = MagicMock()

        result = await service.initialize()

        assert result is True
        assert service.data_cleaner is not None
        assert service.missing_handler is not None
        assert service.data_lake is not None
        assert service.db_manager is not None
        assert service.cache_manager is not None
        service.logger.info.assert_called()
        # 检查日志是否包含预期的信息
        service.logger.info.assert_any_call(
            "数据处理服务初始化完成：清洗器、缺失值处理器、数据湖存储、数据库连接、缓存管理器"
        )

    async def test_initialize_failure(self, mock_service):
        """测试初始化失败"""
        # 使用patch来模拟失败
        with patch(
            "src.services.data_processing.DataLakeStorage",
            side_effect=Exception("Data lake initialization failed"),
        ):
            service = DataProcessingService()
            service.logger = MagicMock()

            result = await service.initialize()

            assert result is False
            service.logger.error.assert_called_with(
                "初始化数据处理服务失败: Data lake initialization failed"
            )

    async def test_shutdown(self, mock_service):
        """测试关闭服务"""
        # 使用AsyncMock处理异步方法
        mock_service.cache_manager.close = MagicMock()
        mock_service.db_manager.close = AsyncMock()

        await mock_service.shutdown()

        # 验证组件被清理
        assert mock_service.data_cleaner is None
        assert mock_service.missing_handler is None
        assert mock_service.data_lake is None
        assert mock_service.cache_manager is None
        assert mock_service.db_manager is None

    # === 数据处理核心功能测试 ===

    async def test_process_raw_match_data_success(self, mock_service, sample_raw_match_data):
        """测试成功处理原始比赛数据"""
        # 重新创建实例并初始化
        service = DataProcessingService()
        service.logger = MagicMock()
        await service.initialize()

        # Mock相关方法
        service.data_cleaner.clean_match_data = MagicMock(return_value=sample_raw_match_data)
        service.missing_handler.handle_missing_values = MagicMock(
            return_value=sample_raw_match_data
        )
        service.data_lake.store = MagicMock(return_value=True)
        service.cache_manager.set = MagicMock(return_value=True)

        result = await service.process_raw_match_data(sample_raw_match_data)

        assert result is not None  # 返回处理后的数据，不是True
        service.data_cleaner.clean_match_data.assert_called_once()

    async def test_process_raw_match_data_validation_failure(
        self, mock_service, sample_raw_match_data
    ):
        """测试处理数据验证失败"""
        # 重新创建实例并初始化
        service = DataProcessingService()
        service.logger = MagicMock()
        await service.initialize()

        # 模拟验证失败
        service.data_cleaner.clean_match_data = MagicMock(
            side_effect=ValueError("Invalid match data")
        )

        result = await service.process_raw_match_data(sample_raw_match_data)

        assert result is None  # 失败时返回None
        service.logger.error.assert_called()

    async def test_process_single_match_data(self, mock_service, sample_raw_match_data):
        """测试处理单个比赛数据"""
        # 重新创建实例并初始化
        service = DataProcessingService()
        service.logger = MagicMock()
        await service.initialize()

        # 设置mock返回值
        service.data_cleaner.validate_data = MagicMock(
            return_value={"is_valid": True, "errors": [], "warnings": []}
        )
        service.data_cleaner.extract_features = MagicMock(
            return_value={
                "home_recent_form": [1, 0, 1, 1, 0],
                "away_recent_form": [0, 1, 0, 0, 1],
                "head_to_head": {"wins": 3, "draws": 2, "losses": 1},
            }
        )
        service.data_lake.store = MagicMock(return_value=True)

        result = await service._process_single_match_data(sample_raw_match_data)

        assert result is not None
        assert "features" in result
        service.data_cleaner.validate_data.assert_called_once()
        service.data_cleaner.extract_features.assert_called_once()

    async def test_process_raw_odds_data(self, mock_service, sample_raw_odds_data):
        """测试处理原始赔率数据"""
        # 重新创建实例并初始化
        service = DataProcessingService()
        service.logger = MagicMock()
        await service.initialize()

        # 设置mock返回值
        service.data_cleaner.clean_odds_data = MagicMock(return_value=sample_raw_odds_data)
        service.data_lake.store = MagicMock(return_value=True)

        result = await service.process_raw_odds_data(sample_raw_odds_data)

        assert result is not None  # 返回处理后的数据
        service.data_cleaner.clean_odds_data.assert_called_once()

    async def test_process_features_data(self, mock_service):
        """测试处理特征数据"""
        # 重新创建实例并初始化
        service = DataProcessingService()
        service.logger = MagicMock()
        await service.initialize()

        # 创建示例特征DataFrame
        features_df = pd.DataFrame(
            {
                "match_id": [123],
                "home_team_form": [1, 0, 1, 1, 0],
                "away_team_form": [0, 1, 0, 0, 1],
                "home_goals_avg": [1.5],
                "away_goals_avg": [1.2],
            }
        )

        # Mock处理方法
        service.missing_handler.handle_missing_features = AsyncMock(return_value=features_df)

        result = await service.process_features_data(123, features_df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    # === 批量处理测试 ===

    async def test_process_batch_matches(self, mock_service, sample_dataframe):
        """测试批量处理比赛数据"""
        # 设置mock返回值
        mock_service.data_cleaner.clean_dataframe.return_value = sample_dataframe
        mock_service.missing_handler.fill_missing_dataframe.return_value = sample_dataframe
        mock_service.data_lake.store_batch.return_value = True

        result = await mock_service.process_batch_matches(sample_dataframe)

        assert result is True
        mock_service.data_cleaner.clean_dataframe.assert_called_once()
        mock_service.missing_handler.fill_missing_dataframe.assert_called_once()

    async def test_process_batch(self, mock_service):
        """测试批量处理通用方法"""
        data_list = [
            {"id": 1, "value": "data1"},
            {"id": 2, "value": "data2"},
            {"id": 3, "value": "data3"},
            "text_data",  # 字符串数据
            123,  # 其他类型数据
        ]

        # Mock处理文本的方法
        mock_service.process_text = AsyncMock(
            side_effect=[{"text": "text_data", "processed": True}]
        )

        results = await mock_service.process_batch(data_list)

        assert len(results) == 5
        assert results[0]["processed"] is True
        assert results[1]["processed"] is True
        assert results[2]["processed"] is True
        assert results[3]["text"] == "text_data"
        assert "original_data" in results[4]

    # === 数据质量验证测试 ===

    async def test_validate_data_quality(self, mock_service, sample_raw_match_data):
        """测试数据质量验证"""
        # 设置mock返回值
        mock_service.data_cleaner.validate_data.return_value = {
            "is_valid": True,
            "errors": [],
            "warnings": ["Match date is close to current date"],
        }

        result = await mock_service.validate_data_quality(sample_raw_match_data)

        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 1

    async def test_validate_data_quality_with_errors(self, mock_service):
        """测试数据质量验证失败"""
        invalid_data = {"home_team": "", "away_team": None}

        # 设置mock返回值
        mock_service.data_cleaner.validate_data.return_value = {
            "is_valid": False,
            "errors": ["Home team cannot be empty", "Away team cannot be null"],
            "warnings": [],
        }

        result = await mock_service.validate_data_quality(invalid_data)

        assert result["is_valid"] is False
        assert len(result["errors"]) == 2
        assert "Home team cannot be empty" in result["errors"]

    # === Bronze到Silver层处理测试 ===

    async def test_process_bronze_to_silver(self, mock_service):
        """测试Bronze到Silver层数据处理"""
        # 设置mock返回值
        mock_service._process_raw_matches_bronze_to_silver = AsyncMock(return_value=50)
        mock_service._process_raw_odds_bronze_to_silver = AsyncMock(return_value=30)
        mock_service._process_raw_scores_bronze_to_silver = AsyncMock(return_value=20)

        result = await mock_service.process_bronze_to_silver(batch_size=100)

        assert result["matches_processed"] == 50
        assert result["odds_processed"] == 30
        assert result["scores_processed"] == 20
        assert result["total_processed"] == 100

    async def test_get_bronze_layer_status(self, mock_service):
        """测试获取Bronze层状态"""
        # Mock数据库查询
        mock_session = MagicMock()
        mock_result1 = MagicMock()
        mock_result1.scalar.return_value = 1000  # RawMatchData count
        mock_result2 = MagicMock()
        mock_result2.scalar.return_value = 500  # RawOddsData count
        mock_result3 = MagicMock()
        mock_result3.scalar.return_value = 300  # RawScoresData count

        mock_session.execute.side_effect = [mock_result1, mock_result2, mock_result3]

        mock_service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        mock_service.db_manager.get_async_session.return_value.__aexit__.return_value = None

        status = await mock_service.get_bronze_layer_status()

        assert status["raw_matches"] == 1000
        assert status["raw_odds"] == 500
        assert status["raw_scores"] == 300
        assert status["total_records"] == 1800

    # === 缺失值处理测试 ===

    async def test_handle_missing_scores(self, mock_service):
        """测试处理缺失的比分数据"""
        # 创建有缺失值的DataFrame
        data_with_missing = pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "home_score": [2, None, 1],
                "away_score": [1, None, 2],
                "date": pd.date_range("2024-01-01", periods=3),
            }
        )

        # 设置mock返回值
        mock_service.missing_handler.fill_missing_dataframe.return_value = pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "home_score": [2, 1, 1],
                "away_score": [1, 1, 2],
                "date": pd.date_range("2024-01-01", periods=3),
            }
        )

        result = await mock_service.handle_missing_scores(data_with_missing)

        assert result is not None
        assert len(result) == 3
        assert result["home_score"].isna().sum() == 0

    async def test_handle_missing_team_data(self, mock_service):
        """测试处理缺失的球队数据"""
        # 创建有缺失值的DataFrame
        team_data = pd.DataFrame(
            {
                "team_id": [1, 2],
                "team_name": ["Team A", None],
                "league": ["Premier League", "Premier League"],
            }
        )

        # 设置mock返回值
        mock_service.missing_handler.handle_missing_teams = AsyncMock(return_value=team_data)

        result = await mock_service.handle_missing_team_data(team_data)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        mock_service.missing_handler.handle_missing_teams.assert_called_once_with(team_data)

    # === 异常检测测试 ===

    async def test_detect_anomalies(self, mock_service, sample_dataframe):
        """测试异常检测"""
        # 设置mock返回值
        mock_service.data_cleaner.detect_outliers.return_value = [
            {
                "index": 1,
                "field": "home_score",
                "value": 10,
                "reason": "Unusually high score",
            },
            {
                "index": 2,
                "field": "away_score",
                "value": -1,
                "reason": "Negative score",
            },
        ]

        anomalies = await mock_service.detect_anomalies(sample_dataframe)

        assert len(anomalies) == 2
        assert anomalies[0]["field"] == "home_score"
        assert anomalies[1]["reason"] == "Negative score"

    # === 缓存管理测试 ===

    async def test_cache_processing_results(self, mock_service):
        """测试缓存处理结果"""
        result_data = {"match_id": "123", "processed": True}
        cache_key = "processed_match_123"

        mock_service.cache_manager.set.return_value = True

        cached = await mock_service.cache_processing_results(cache_key, result_data)

        assert cached is True
        mock_service.cache_manager.set.assert_called_once()

    async def test_get_cached_results(self, mock_service):
        """测试获取缓存结果"""
        cache_key = "processed_match_123"
        cached_data = {"match_id": "123", "processed": True}

        mock_service.cache_manager.get.return_value = cached_data

        result = await mock_service.get_cached_results(cache_key)

        assert result == cached_data
        mock_service.cache_manager.get.assert_called_once_with(cache_key)

    # === 性能和重试机制测试 ===

    async def test_process_with_retry_success(self, mock_service):
        """测试重试机制成功"""

        # Mock处理函数
        async def process_func(data):
            return {"processed": True, "data": data}

        result = await mock_service.process_with_retry(
            process_func, {"test": "data"}, max_retries=3
        )

        assert result["processed"] is True

    async def test_process_with_retry_failure(self, mock_service):
        """测试重试机制失败"""

        # Mock失败的处理函数
        async def failing_process_func(data):
            raise ValueError("Processing failed")

        with pytest.raises(ValueError):
            await mock_service.process_with_retry(
                failing_process_func, {"test": "data"}, max_retries=2
            )

    async def test_batch_process_datasets(self, mock_service):
        """测试批量处理多个数据集"""
        datasets = {
            "matches": [{"id": 1}, {"id": 2}],
            "odds": [{"id": 1}, {"id": 2}],
            "scores": [{"id": 1}],
        }

        # Mock批量处理方法
        mock_service.process_batch = AsyncMock(
            side_effect=[
                [{"id": 1, "processed": True}, {"id": 2, "processed": True}],
                [{"id": 1, "processed": True}, {"id": 2, "processed": True}],
                [{"id": 1, "processed": True}],
            ]
        )

        results = await mock_service.batch_process_datasets(datasets)

        assert "matches" in results
        assert "odds" in results
        assert "scores" in results
        assert len(results["matches"]) == 2

    async def test_collect_performance_metrics(self, mock_service):
        """测试收集性能指标"""
        # Mock服务方法
        mock_service.process_batch_matches = AsyncMock()
        mock_service.process_raw_match_data = AsyncMock()

        # 模拟执行一些操作
        await mock_service.process_batch_matches(pd.DataFrame())
        await mock_service.process_raw_match_data({})

        metrics = await mock_service.collect_performance_metrics()

        assert "timestamp" in metrics
        assert "memory_usage" in metrics
        assert "cache_hit_rate" in metrics

    # === 错误处理测试 ===

    async def test_process_raw_match_data_database_error(self, mock_service, sample_raw_match_data):
        """测试处理数据时数据库错误"""
        # 设置mock返回值
        mock_service.data_cleaner.clean_match_data.return_value = sample_raw_match_data
        mock_service.missing_handler.handle_missing_values.return_value = sample_raw_match_data

        # Mock数据库错误
        mock_service.db_manager.get_async_session.side_effect = Exception(
            "Database connection failed"
        )

        result = await mock_service.process_raw_match_data(sample_raw_match_data)

        assert result is False
        mock_service.logger.error.assert_called()

    async def test_store_processed_data_error(self, mock_service):
        """测试存储处理后的数据时出错"""
        processed_data = pd.DataFrame({"match_id": ["123"], "features": [{}]})
        table_name = "processed_matches"

        # Mock存储失败
        mock_service.data_lake.store = MagicMock(return_value=False)

        result = await mock_service.store_processed_data(processed_data, table_name)

        assert result is False

    # === 清理功能测试 ===

    async def test_cleanup(self, mock_service):
        """测试清理临时数据和缓存"""
        mock_service.cache_manager.flush_all = MagicMock()
        mock_service.data_lake.cleanup_temp_files = MagicMock()

        result = await mock_service.cleanup()

        assert result is True
        mock_service.logger.info.assert_called_with("数据清理完成")

    # === 文本处理测试 ===

    async def test_process_text(self, mock_service):
        """测试文本处理"""
        text = "Manchester United vs Liverpool, 2-1"

        # Mock清洗方法
        mock_service.data_cleaner.clean_text.return_value = {
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "home_score": 2,
            "away_score": 1,
        }

        result = await mock_service.process_text(text)

        assert result["home_team"] == "Manchester United"
        assert result["away_team"] == "Liverpool"
        assert result["home_score"] == 2
        assert result["away_score"] == 1

    # === 健康检查测试 ===

    def test_health_check(self, mock_service):
        """测试健康检查"""
        # Mock组件状态
        mock_service.data_cleaner = MagicMock()
        mock_service.missing_handler = MagicMock()
        mock_service.data_lake = MagicMock()
        mock_service.db_manager = MagicMock()
        mock_service.cache_manager = MagicMock()

        health = mock_service.health_check()

        assert health["status"] == "healthy"
        assert "components" in health
        assert all(
            component["status"] == "connected" for component in health["components"].values()
        )
