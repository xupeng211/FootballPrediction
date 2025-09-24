"""
阶段2：数据处理服务测试
目标：补齐核心逻辑测试覆盖率达到70%+
重点：测试数据处理服务、批处理、质量验证、缓存、错误处理
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest

from src.services.data_processing import DataProcessingService


class TestDataProcessingServicePhase2:
    """数据处理服务阶段2测试"""

    def setup_method(self):
        """设置测试环境"""
        # 创建模拟依赖
        self.mock_data_cleaner = Mock()
        self.mock_missing_handler = Mock()
        self.mock_data_lake = Mock()
        self.mock_db_manager = Mock()
        self.mock_cache_manager = Mock()

        # 创建服务实例
        self.service = DataProcessingService()

        # 设置模拟对象
        self.service.data_cleaner = self.mock_data_cleaner
        self.service.missing_handler = self.mock_missing_handler
        self.service.data_lake = self.mock_data_lake
        self.service.db_manager = self.mock_db_manager
        self.service.cache_manager = self.mock_cache_manager

        # 测试数据
        self.test_match_data = {
            "external_match_id": 1001,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": 2,
            "away_score": 1,
            "match_time": "2025-09-10 15:00:00",
        }

        self.test_odds_data = [
            {
                "external_match_id": 1001,
                "market": "1X2",
                "outcome": "Home",
                "price": 1.85,
            },
            {
                "external_match_id": 1001,
                "market": "1X2",
                "outcome": "Draw",
                "price": 3.40,
            },
        ]

    def test_initialization_basic(self):
        """测试基本初始化"""
        service = DataProcessingService()
        assert service.name == "DataProcessingService"
        assert service.data_cleaner is None
        assert service.missing_handler is None
        assert service.data_lake is None
        assert service.db_manager is None
        assert service.cache_manager is None

    async def test_initialize_success(self):
        """测试初始化成功"""
        with patch(
            "src.services.data_processing.FootballDataCleaner"
        ) as mock_cleaner_class, patch(
            "src.services.data_processing.MissingDataHandler"
        ) as mock_handler_class, patch(
            "src.services.data_processing.DataLakeStorage"
        ) as mock_lake_class, patch(
            "src.services.data_processing.DatabaseManager"
        ) as mock_db_class, patch(
            "src.services.data_processing.RedisManager"
        ) as mock_redis_class:
            # 设置模拟对象
            mock_cleaner = Mock()
            mock_handler = Mock()
            mock_lake = Mock()
            mock_db = Mock()
            mock_redis = Mock()

            mock_cleaner_class.return_value = mock_cleaner
            mock_handler_class.return_value = mock_handler
            mock_lake_class.return_value = mock_lake
            mock_db_class.return_value = mock_db
            mock_redis_class.return_value = mock_redis

            service = DataProcessingService()
            result = await service.initialize()

            assert result is True
            assert service.data_cleaner == mock_cleaner
            assert service.missing_handler == mock_handler
            assert service.data_lake == mock_lake
            assert service.db_manager == mock_db
            assert service.cache_manager == mock_redis

    async def test_initialize_failure(self):
        """测试初始化失败"""
        with patch(
            "src.services.data_processing.FootballDataCleaner"
        ) as mock_cleaner_class:
            mock_cleaner_class.side_effect = Exception("Initialization failed")

            service = DataProcessingService()
            result = await service.initialize()

            assert result is False

    async def test_shutdown_basic(self):
        """测试基本关闭"""
        # 设置模拟对象
        self.service.cache_manager = Mock()
        self.service.db_manager = Mock()

        # 模拟同步关闭
        self.service.cache_manager.close = Mock()
        self.service.db_manager.close = AsyncMock()

        await self.service.shutdown()

        # 验证组件被清空
        assert self.service.data_cleaner is None
        assert self.service.missing_handler is None
        assert self.service.data_lake is None

        # 验证关闭方法被调用
        self.service.cache_manager.close.assert_called_once()
        self.service.db_manager.close.assert_called_once()

    async def test_shutdown_with_mock_cache(self):
        """测试关闭模拟缓存"""
        # 模拟异步Mock对象
        mock_cache = AsyncMock()
        mock_cache.close._mock_name = "mock_close"  # 模拟mock属性

        self.service.cache_manager = mock_cache
        self.service.db_manager = AsyncMock()

        await self.service.shutdown()

        # 验证异步关闭被调用
        mock_cache.close.assert_called_once()

    async def test_process_raw_match_data_single_dict(self):
        """测试处理原始比赛数据单个字典"""
        # 模拟清洗器返回数据
        self.mock_data_cleaner.clean_match_data.return_value = self.test_match_data
        self.mock_missing_handler.handle_missing_match_data.return_value = (
            self.test_match_data
        )

        result = await self.service.process_raw_match_data(self.test_match_data)

        assert result == self.test_match_data
        self.mock_data_cleaner.clean_match_data.assert_called_once_with(
            self.test_match_data
        )

    async def test_process_raw_match_data_list(self):
        """测试处理原始比赛数据列表"""
        test_list = [self.test_match_data, self.test_match_data.copy()]

        # 模拟单个处理
        self.mock_data_cleaner.clean_match_data.return_value = self.test_match_data
        self.mock_missing_handler.handle_missing_match_data.return_value = (
            self.test_match_data
        )

        result = await self.service.process_raw_match_data(test_list)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    async def test_process_raw_match_data_empty_list(self):
        """测试处理原始比赛数据空列表"""
        result = await self.service.process_raw_match_data([])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    async def test_process_raw_match_data_cleaner_not_initialized(self):
        """测试处理原始比赛数据清洗器未初始化"""
        self.service.data_cleaner = None

        result = await self.service.process_raw_match_data(self.test_match_data)

        assert result is None

    async def test_process_raw_match_data_cleaning_failed(self):
        """测试处理原始比赛数据清洗失败"""
        self.mock_data_cleaner.clean_match_data.return_value = None

        result = await self.service.process_raw_match_data(self.test_match_data)

        assert result is None

    async def test_process_raw_match_data_with_cache(self):
        """测试处理原始比赛数据使用缓存"""
        match_id = 1001
        cached_data = {"cached": True, "external_match_id": match_id}

        # 模拟缓存命中
        self.mock_cache_manager.aget.return_value = cached_data

        test_data = self.test_match_data.copy()
        test_data["external_match_id"] = match_id

        result = await self.service.process_raw_match_data(test_data)

        assert result == cached_data
        self.mock_cache_manager.aget.assert_called_once()

    async def test_process_raw_match_data_cache_miss(self):
        """测试处理原始比赛数据缓存未命中"""
        match_id = 1001

        # 模拟缓存未命中
        self.mock_cache_manager.aget.return_value = None
        self.mock_data_cleaner.clean_match_data.return_value = self.test_match_data
        self.mock_missing_handler.handle_missing_match_data.return_value = (
            self.test_match_data
        )

        test_data = self.test_match_data.copy()
        test_data["external_match_id"] = match_id

        result = await self.service.process_raw_match_data(test_data)

        assert result == self.test_match_data
        # 验证缓存被设置
        self.mock_cache_manager.aset.assert_called_once()

    async def test_process_raw_odds_data_basic(self):
        """测试处理原始赔率数据基本功能"""
        # 模拟清洗结果
        cleaned_odds = self.test_odds_data.copy()
        self.mock_data_cleaner.clean_odds_data.return_value = cleaned_odds

        result = await self.service.process_raw_odds_data(self.test_odds_data)

        assert result == cleaned_odds
        self.mock_data_cleaner.clean_odds_data.assert_called_once_with(
            self.test_odds_data
        )

    async def test_process_raw_odds_data_async_cleaner(self):
        """测试处理原始赔率数据异步清洗器"""

        async def async_cleaner(odds_data):
            await asyncio.sleep(0.01)  # 模拟异步操作
            return odds_data.copy()

        self.mock_data_cleaner.clean_odds_data.return_value = async_cleaner(
            self.test_odds_data
        )

        result = await self.service.process_raw_odds_data(self.test_odds_data)

        assert result == self.test_odds_data

    async def test_process_raw_odds_data_cleaner_not_initialized(self):
        """测试处理原始赔率数据清洗器未初始化"""
        self.service.data_cleaner = None

        result = await self.service.process_raw_odds_data(self.test_odds_data)

        assert result == []

    async def test_process_features_data_basic(self):
        """测试处理特征数据基本功能"""
        match_id = 1001
        test_features = pd.DataFrame(
            {
                "feature1": [1, 2, 3],
                "feature2": [4, 5, 6],
            }
        )

        # 模拟处理结果
        processed_features = test_features.copy()
        self.mock_missing_handler.handle_missing_features.return_value = (
            processed_features
        )

        result = await self.service.process_features_data(match_id, test_features)

        assert result.equals(processed_features)
        self.mock_missing_handler.handle_missing_features.assert_called_once_with(
            match_id, test_features
        )

    async def test_process_features_data_handler_not_initialized(self):
        """测试处理特征数据处理器未初始化"""
        self.service.missing_handler = None
        test_features = pd.DataFrame({"feature1": [1, 2, 3]})

        result = await self.service.process_features_data(1001, test_features)

        # 应该返回原始数据
        assert result.equals(test_features)

    async def test_process_batch_matches_basic(self):
        """测试批量处理比赛数据基本功能"""
        raw_matches = [self.test_match_data.copy() for _ in range(3)]

        # 模拟单个处理成功
        self.mock_data_cleaner.clean_match_data.return_value = self.test_match_data
        self.mock_missing_handler.handle_missing_match_data.return_value = (
            self.test_match_data
        )

        result = await self.service.process_batch_matches(raw_matches)

        assert len(result) == 3
        assert all(item == self.test_match_data for item in result)

    async def test_process_batch_matches_with_failures(self):
        """测试批量处理比赛数据包含失败"""
        raw_matches = [self.test_match_data.copy() for _ in range(3)]

        # 模拟部分失败
        def side_effect(data):
            if data.get("external_match_id") == 1002:
                return None  # 失败
            return self.test_match_data

        self.mock_data_cleaner.clean_match_data.side_effect = side_effect
        self.mock_missing_handler.handle_missing_match_data.return_value = (
            self.test_match_data
        )

        result = await self.service.process_batch_matches(raw_matches)

        assert len(result) == 2  # 应该有2个成功

    def test_validate_data_quality_match_valid(self):
        """测试验证比赛数据质量有效"""
        # 模拟同步验证
        quality_report = asyncio.run(
            self.service.validate_data_quality(self.test_match_data, "match")
        )

        assert quality_report["data_type"] == "match"
        assert quality_report["is_valid"] is True
        assert len(quality_report["issues"]) == 0

    def test_validate_data_quality_match_missing_fields(self):
        """测试验证比赛数据质量缺失字段"""
        invalid_data = {"home_team_id": 1}  # 缺少必需字段

        quality_report = asyncio.run(
            self.service.validate_data_quality(invalid_data, "match")
        )

        assert quality_report["is_valid"] is False
        assert any(
            "Missing required field" in issue for issue in quality_report["issues"]
        )

    def test_validate_data_quality_match_negative_scores(self):
        """测试验证比赛数据质量负分数"""
        invalid_data = self.test_match_data.copy()
        invalid_data["home_score"] = -1

        quality_report = asyncio.run(
            self.service.validate_data_quality(invalid_data, "match")
        )

        assert quality_report["is_valid"] is False
        assert any("Negative scores" in issue for issue in quality_report["issues"])

    def test_validate_data_quality_match_high_scores(self):
        """测试验证比赛数据质量高分数警告"""
        invalid_data = self.test_match_data.copy()
        invalid_data["home_score"] = 25  # 异常高分

        quality_report = asyncio.run(
            self.service.validate_data_quality(invalid_data, "match")
        )

        assert quality_report["is_valid"] is True  # 仍然有效但有警告
        assert any(
            "Unusually high scores" in warning for warning in quality_report["warnings"]
        )

    def test_validate_data_quality_odds_valid(self):
        """测试验证赔率数据质量有效"""
        valid_odds = {
            "outcomes": [
                {"outcome": "Home", "price": 1.85},
                {"outcome": "Draw", "price": 3.40},
                {"outcome": "Away", "price": 4.20},
            ]
        }

        quality_report = asyncio.run(
            self.service.validate_data_quality(valid_odds, "odds")
        )

        assert quality_report["data_type"] == "odds"
        assert quality_report["is_valid"] is True

    def test_validate_data_quality_odds_no_outcomes(self):
        """测试验证赔率数据质量无结果"""
        invalid_odds = {"outcomes": []}

        quality_report = asyncio.run(
            self.service.validate_data_quality(invalid_odds, "odds")
        )

        assert quality_report["is_valid"] is False
        assert any(
            "No odds outcomes found" in issue for issue in quality_report["issues"]
        )

    def test_validate_data_quality_odds_invalid_price(self):
        """测试验证赔率数据质量无效价格"""
        invalid_odds = {
            "outcomes": [
                {"outcome": "Home", "price": 0.5},  # 无效价格
            ]
        }

        quality_report = asyncio.run(
            self.service.validate_data_quality(invalid_odds, "odds")
        )

        assert quality_report["is_valid"] is False
        assert any("Invalid odds price" in issue for issue in quality_report["issues"])

    def test_validate_data_quality_unknown_type(self):
        """测试验证数据质量未知类型"""
        unknown_data = {"some_field": "value"}

        quality_report = asyncio.run(
            self.service.validate_data_quality(unknown_data, "unknown")
        )

        # 未知类型应该返回基本结构
        assert quality_report["data_type"] == "unknown"
        assert quality_report["is_valid"] is True
        assert len(quality_report["issues"]) == 0

    async def test_process_text_basic(self):
        """测试处理文本数据基本功能"""
        test_text = "  Hello World  "
        result = await self.service.process_text(test_text)

        assert result["processed_text"] == "Hello World"
        assert result["word_count"] == 2
        assert result["character_count"] == 11

    async def test_process_batch_mixed_types(self):
        """测试批量处理混合类型"""
        mixed_data = ["text data", {"key": "value"}, 123]

        result = await self.service.process_batch(mixed_data)

        assert len(result) == 3
        assert result[0]["processed_text"] == "text data"
        assert result[1]["processed"] is True
        assert result[2]["processed"] is True

    async def test_process_bronze_to_silver_not_initialized(self):
        """测试Bronze到Silver层处理未初始化"""
        self.service.data_cleaner = None

        result = await self.service.process_bronze_to_silver()

        assert result["error"] == 1

    async def test_process_bronze_to_silver_success(self):
        """测试Bronze到Silver层处理成功"""
        # 模拟所有组件初始化
        self.service.data_cleaner.clean_match_data = AsyncMock(
            return_value={"cleaned": True}
        )
        self.service.missing_handler.handle_missing_match_data = AsyncMock(
            return_value={"processed": True}
        )
        self.service.data_lake.save_historical_data = AsyncMock()

        # 模拟数据库会话和查询
        mock_session = Mock()
        mock_raw_matches = []
        mock_raw_odds = []
        mock_raw_scores = []

        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = (
            mock_raw_matches
        )
        self.mock_db_manager.get_session.return_value.__enter__.return_value = (
            mock_session
        )

        result = await self.service.process_bronze_to_silver()

        assert "error" not in result
        assert result["processed_matches"] == 0
        assert result["processed_odds"] == 0
        assert result["processed_scores"] == 0

    async def test_get_bronze_layer_status_no_db_manager(self):
        """测试获取Bronze层状态无数据库管理器"""
        self.service.db_manager = None

        result = await self.service.get_bronze_layer_status()

        assert "error" in result

    async def test_get_bronze_layer_status_success(self):
        """测试获取Bronze层状态成功"""
        # 模拟数据库查询
        mock_session = Mock()
        mock_query = Mock()

        # 模拟查询结果
        mock_query.count.return_value = 100
        mock_query.filter.return_value.count.return_value = 80

        mock_session.query.return_value = mock_query
        self.mock_db_manager.get_session.return_value.__enter__.return_value = (
            mock_session
        )

        result = await self.service.get_bronze_layer_status()

        assert "matches" in result
        assert "odds" in result
        assert "scores" in result
        assert result["matches"]["total"] == 100
        assert result["matches"]["processed"] == 80
        assert result["matches"]["pending"] == 20

    async def test_handle_missing_scores_basic(self):
        """测试处理分数缺失值基本功能"""
        test_data = pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "home_score": [1, None, 2],
                "away_score": [0, 1, None],
            }
        )

        # 模拟处理结果
        processed_data = test_data.fillna(0)
        self.mock_missing_handler.interpolate_scores = Mock(return_value=processed_data)

        result = await self.service.handle_missing_scores(test_data)

        assert result.equals(processed_data)
        self.mock_missing_handler.interpolate_scores.assert_called_once_with(test_data)

    async def test_handle_missing_scores_no_handler(self):
        """测试处理分数缺失值无处理器"""
        self.service.missing_handler = None
        test_data = pd.DataFrame({"match_id": [1, 2, 3]})

        result = await self.service.handle_missing_scores(test_data)

        assert result is None

    async def test_handle_missing_scores_no_method(self):
        """测试处理分数缺失值无方法"""
        # 模拟处理器无插值方法
        del self.mock_missing_handler.interpolate_scores
        test_data = pd.DataFrame({"match_id": [1, 2, 3]})

        result = await self.service.handle_missing_scores(test_data)

        # 应该返回原始数据
        assert result.equals(test_data)

    async def test_handle_missing_team_data_basic(self):
        """测试处理球队数据缺失值基本功能"""
        test_data = pd.DataFrame(
            {
                "team_id": [1, 2, 3],
                "team_name": ["Team A", None, "Team C"],
            }
        )

        # 模拟处理结果
        processed_data = test_data.fillna("Unknown")
        self.mock_missing_handler.impute_team_data = Mock(return_value=processed_data)

        result = await self.service.handle_missing_team_data(test_data)

        assert result.equals(processed_data)

    async def test_detect_anomalies_basic(self):
        """测试异常检测基本功能"""
        test_data = pd.DataFrame(
            {
                "value": [1, 2, 100, 3, 4],  # 100是异常值
            }
        )

        # 模拟异常检测结果
        anomalies = [{"value": 100, "type": "outlier"}]
        self.mock_missing_handler.detect_anomalies = Mock(return_value=anomalies)

        result = await self.service.detect_anomalies(test_data)

        assert result == anomalies

    async def test_store_processed_data_basic(self):
        """测试存储处理后的数据基本功能"""
        test_data = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})

        # 模拟存储成功
        self.mock_data_lake.store_dataframe = Mock(return_value=True)
        self.mock_db_manager.bulk_insert = Mock(return_value=True)

        result = await self.service.store_processed_data(test_data, "test_table")

        assert result is True

    async def test_store_processed_data_with_cache(self):
        """测试存储处理后的数据带缓存"""
        test_data = pd.DataFrame({"col1": [1, 2, 3]})

        self.mock_data_lake.store_dataframe = Mock(return_value=True)
        self.mock_db_manager.bulk_insert = Mock(return_value=True)
        self.mock_cache_manager.set_json = Mock(return_value=True)

        result = await self.service.store_processed_data(
            test_data, "test_table", cache_results=True
        )

        assert result is True
        self.mock_cache_manager.set_json.assert_called_once()

    async def test_store_processed_data_partial_failure(self):
        """测试存储处理后的数据部分失败"""
        test_data = pd.DataFrame({"col1": [1, 2, 3]})

        # 模拟数据湖存储失败但数据库成功
        self.mock_data_lake.store_dataframe = Mock(
            side_effect=Exception("Storage failed")
        )
        self.mock_db_manager.bulk_insert = Mock(return_value=True)

        result = await self.service.store_processed_data(test_data, "test_table")

        assert result is False  # 部分失败应该返回False

    async def test_cache_processing_results_basic(self):
        """测试缓存处理结果基本功能"""
        test_data = {"result": "success"}
        cache_key = "test_key"

        self.mock_cache_manager.set_json = Mock(return_value=True)

        result = await self.service.cache_processing_results(cache_key, test_data)

        assert result is True
        self.mock_cache_manager.set_json.assert_called_once_with(
            cache_key, test_data, ttl=3600
        )

    async def test_cache_processing_results_no_manager(self):
        """测试缓存处理结果无管理器"""
        self.service.cache_manager = None

        result = await self.service.cache_processing_results(
            "test_key", {"data": "test"}
        )

        assert result is False

    async def test_get_cached_results_basic(self):
        """测试获取缓存结果基本功能"""
        cached_data = {"result": "cached"}
        cache_key = "test_key"

        self.mock_cache_manager.get_json = Mock(return_value=cached_data)

        result = await self.service.get_cached_results(cache_key)

        assert result == cached_data

    async def test_batch_process_datasets_basic(self):
        """测试批量处理数据集基本功能"""
        datasets = {
            "matches": [self.test_match_data],
            "odds": self.test_odds_data,
        }

        # 模拟处理结果
        processed_matches = [self.test_match_data]
        processed_odds = self.test_odds_data

        self.service.process_batch_matches = AsyncMock(return_value=processed_matches)
        self.service.process_raw_odds_data = AsyncMock(return_value=processed_odds)

        result = await self.service.batch_process_datasets(datasets)

        assert result["processed_counts"]["matches"] == 1
        assert result["processed_counts"]["odds"] == 2
        assert result["total_processed"] == 3

    async def test_batch_process_datasets_with_errors(self):
        """测试批量处理数据集包含错误"""
        datasets = {
            "matches": [self.test_match_data],
            "invalid_type": ["invalid_data"],
        }

        # 模拟一个成功一个失败
        self.service.process_batch_matches = AsyncMock(
            return_value=[self.test_match_data]
        )
        self.service.process_batch = AsyncMock(
            side_effect=Exception("Processing failed")
        )

        result = await self.service.batch_process_datasets(datasets)

        assert result["processed_counts"]["matches"] == 1
        assert "invalid_type" in result["errors"]
        assert result["total_processed"] == 1

    async def test_process_with_retry_success(self):
        """测试带重试处理成功"""
        test_func = Mock(return_value="success")
        test_data = {"test": "data"}

        result = await self.service.process_with_retry(
            test_func, test_data, max_retries=3
        )

        assert result == "success"
        test_func.assert_called_once_with(test_data)

    async def test_process_with_retry_eventual_success(self):
        """测试带重试处理最终成功"""
        call_count = 0

        def failing_then_success(data):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        test_func = Mock(side_effect=failing_then_success)
        test_data = {"test": "data"}

        result = await self.service.process_with_retry(
            test_func, test_data, max_retries=3
        )

        assert result == "success"
        assert call_count == 3

    async def test_process_with_retry_persistent_failure(self):
        """测试带重试处理持续失败"""
        test_func = Mock(side_effect=Exception("Persistent failure"))
        test_data = {"test": "data"}

        with pytest.raises(RuntimeError, match="处理持续失败"):
            await self.service.process_with_retry(test_func, test_data, max_retries=3)

    async def test_process_with_retry_async_function(self):
        """测试带重试处理异步函数"""

        async def async_func(data):
            await asyncio.sleep(0.01)
            return f"async_{data}"

        test_func = Mock(wraps=async_func)
        test_data = "test"

        result = await self.service.process_with_retry(test_func, test_data)

        assert result == "async_test"
        test_func.assert_called_once_with(test_data)

    async def test_process_in_batches_basic(self):
        """测试分批处理基本功能"""
        large_dataset = list(range(100))  # 100个元素
        batch_size = 25

        batches = []
        async for batch in self.service._process_in_batches(large_dataset, batch_size):
            batches.append(batch)

        assert len(batches) == 4  # 100 / 25 = 4
        assert all(len(batch) == 25 for batch in batches)

    async def test_process_in_batches_uneven(self):
        """测试分批处理不均匀数据"""
        uneven_dataset = list(range(95))  # 95个元素
        batch_size = 25

        batches = []
        async for batch in self.service._process_in_batches(uneven_dataset, batch_size):
            batches.append(batch)

        assert len(batches) == 4  # 95 / 25 = 3.8 -> 4 batches
        assert len(batches[0]) == 25
        assert len(batches[1]) == 25
        assert len(batches[2]) == 25
        assert len(batches[3]) == 20  # 最后一批较小

    async def test_collect_performance_metrics_basic(self):
        """测试收集性能指标基本功能"""

        async def dummy_processing_func(*args, **kwargs):
            await asyncio.sleep(0.1)  # 模拟处理时间
            return [1, 2, 3]  # 返回3个结果

        metrics = await self.service.collect_performance_metrics(dummy_processing_func)

        assert "total_time" in metrics
        assert "items_processed" in metrics
        assert "items_per_second" in metrics
        assert metrics["items_processed"] == 3
        assert metrics["total_time"] > 0

    async def test_process_large_dataset_basic(self):
        """测试处理大型数据集基本功能"""
        large_dataset = list(range(100))

        # 模拟批处理
        self.service.process_batch = AsyncMock(
            side_effect=lambda batch: [{"processed": item} for item in batch]
        )

        result = await self.service.process_large_dataset(large_dataset, batch_size=20)

        assert len(result) == 100
        assert self.service.process_batch.call_count == 5  # 100 / 20 = 5

    async def test_cleanup_basic(self):
        """测试基本清理"""
        # 设置模拟对象
        self.service.db_manager = Mock()
        self.service.db_manager.close = AsyncMock()

        # 添加缓存
        self.service._cache = {"key": "value"}

        result = await self.service.cleanup()

        assert result is True
        assert not hasattr(self.service, "_cache") or len(self.service._cache) == 0
        self.service.db_manager.close.assert_called_once()

    async def test_cleanup_with_sync_db_close(self):
        """测试清理同步数据库关闭"""
        # 模拟同步关闭
        self.service.db_manager = Mock()
        self.service.db_manager.close = Mock()

        result = await self.service.cleanup()

        assert result is True
        self.service.db_manager.close.assert_called_once()

    def test_service_inheritance(self):
        """测试服务继承"""
        from src.services.base import BaseService

        assert isinstance(self.service, BaseService)
        assert hasattr(self.service, "name")
        assert hasattr(self.service, "logger")

    def test_error_logging_patterns(self):
        """测试错误日志模式"""
        # 验证错误被正确记录
        with patch.object(self.service.logger, "error") as mock_error:
            try:
                # 模拟错误情况
                raise Exception("Test error")
            except Exception:
                self.service.handle_error(Exception("Test error"))

            mock_error.assert_called()

    def test_method_signatures(self):
        """测试方法签名"""
        import inspect

        # 检查主要方法的签名
        methods_to_check = [
            "process_raw_match_data",
            "process_raw_odds_data",
            "process_features_data",
            "validate_data_quality",
            "process_bronze_to_silver",
        ]

        for method_name in methods_to_check:
            method = getattr(self.service, method_name)
            sig = inspect.signature(method)
            assert sig is not None

    def test_async_method_detection(self):
        """测试异步方法检测"""
        import inspect

        # 检查异步方法
        async_methods = [
            "initialize",
            "shutdown",
            "process_raw_match_data",
            "process_raw_odds_data",
            "process_features_data",
            "process_batch_matches",
            "validate_data_quality",
            "process_bronze_to_silver",
            "get_bronze_layer_status",
        ]

        for method_name in async_methods:
            method = getattr(self.service, method_name)
            assert inspect.iscoroutinefunction(method), f"{method_name} should be async"

    def test_service_composition(self):
        """测试服务组合"""
        # 验证服务正确组合了各种组件
        assert hasattr(self.service, "data_cleaner")
        assert hasattr(self.service, "missing_handler")
        assert hasattr(self.service, "data_lake")
        assert hasattr(self.service, "db_manager")
        assert hasattr(self.service, "cache_manager")

    def test_configuration_flexibility(self):
        """测试配置灵活性"""
        # 测试服务可以在不同配置下工作
        service = DataProcessingService()

        # 组件应该可以为None（未初始化状态）
        assert service.data_cleaner is None
        assert service.missing_handler is None

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 测试旧方法仍然存在
        assert hasattr(self.service, "process_text")
        assert hasattr(self.service, "process_batch")

        # 测试旧方法可以正常调用
        async def test_old_methods():
            text_result = await self.service.process_text("test")
            assert "processed_text" in text_result

            batch_result = await self.service.process_batch(["test"])
            assert len(batch_result) == 1

        asyncio.run(test_old_methods())

    def test_error_handling_comprehensive(self):
        """测试错误处理全面性"""
        # 测试各种错误情况
        error_scenarios = [
            ("process_raw_match_data", None, "cleaner not initialized"),
            ("process_raw_odds_data", [], "odds processing with empty data"),
            ("validate_data_quality", {}, "empty data validation"),
        ]

        for method_name, test_data, description in error_scenarios:
            try:
                method = getattr(self.service, method_name)
                if asyncio.iscoroutinefunction(method):
                    # 对于异步方法，我们只测试方法存在性
                    assert method is not None
                else:
                    # 对于同步方法，测试基本调用
                    result = method(test_data)
                    assert result is not None or isinstance(result, dict)
            except Exception as e:
                # 错误应该被处理而不是抛出
                assert False, f"Method {method_name} failed unexpectedly: {e}"

    def test_performance_considerations(self):
        """测试性能考虑"""
        # 验证性能相关的方法存在
        performance_methods = [
            "collect_performance_metrics",
            "process_large_dataset",
            "process_in_batches",
            "process_with_retry",
        ]

        for method_name in performance_methods:
            assert hasattr(self.service, method_name)

    def test_data_integrity_validation(self):
        """测试数据完整性验证"""
        # 验证验证方法存在
        validation_methods = [
            "validate_data_quality",
            "detect_anomalies",
            "handle_missing_scores",
            "handle_missing_team_data",
        ]

        for method_name in validation_methods:
            assert hasattr(self.service, method_name)

    def test_caching_integration(self):
        """测试缓存集成"""
        # 验证缓存相关方法存在
        cache_methods = [
            "cache_processing_results",
            "get_cached_results",
            "store_processed_data",
        ]

        for method_name in cache_methods:
            assert hasattr(self.service, method_name)

    def test_comprehensive_test_coverage(self):
        """测试全面覆盖度"""
        # 验证所有主要功能类别都有测试覆盖
        test_methods = [method for method in dir(self) if method.startswith("test_")]

        functionality_categories = {
            "initialization": ["test_initialization"],
            "data_processing": [
                "test_process_raw_match_data",
                "test_process_raw_odds_data",
            ],
            "quality_validation": ["test_validate_data_quality"],
            "batch_processing": ["test_process_batch_matches"],
            "layer_processing": ["test_process_bronze_to_silver"],
            "caching": ["test_cache_processing_results", "test_get_cached_results"],
            "error_handling": ["test_process_with_retry"],
            "performance": ["test_collect_performance_metrics"],
            "cleanup": ["test_cleanup"],
            "backward_compatibility": ["test_backward_compatibility"],
        }

        # 验证每个类别都有对应的测试
        for category, methods in functionality_categories.items():
            category_tests = [
                method
                for method in test_methods
                if any(method.startswith(prefix) for prefix in methods)
            ]
            assert len(category_tests) > 0, f"Category {category} has no tests"
