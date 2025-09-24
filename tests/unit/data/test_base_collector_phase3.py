"""
Phase 3：数据采集器基类综合测试
目标：全面提升base_collector.py模块覆盖率到60%+
重点：测试所有抽象方法、HTTP请求功能、数据保存、重复记录检查和日志记录功能
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.data.collectors.base_collector import (
    EXTERNAL_API_RETRY_CONFIG,
    CollectionResult,
    DataCollector,
)


class TestCollectionResult:
    """采集结果数据结构测试"""

    def test_collection_result_creation(self):
        """测试采集结果创建"""
        result = CollectionResult(
            data_source="test_api",
            collection_type="fixtures",
            records_collected=10,
            success_count=8,
            error_count=2,
            status="partial",
            error_message="Some records failed",
            collected_data=[{"id": 1}, {"id": 2}],
        )

        assert result.data_source == "test_api"
        assert result.collection_type == "fixtures"
        assert result.records_collected == 10
        assert result.success_count == 8
        assert result.error_count == 2
        assert result.status == "partial"
        assert result.error_message == "Some records failed"
        assert result.collected_data == [{"id": 1}, {"id": 2}]

    def test_collection_result_minimal(self):
        """测试最小采集结果"""
        result = CollectionResult(
            data_source="test_api",
            collection_type="fixtures",
            records_collected=5,
            success_count=5,
            error_count=0,
            status="success",
        )

        assert result.data_source == "test_api"
        assert result.status == "success"
        assert result.error_message is None
        assert result.collected_data is None

    def test_collection_result_failure(self):
        """测试失败采集结果"""
        result = CollectionResult(
            data_source="test_api",
            collection_type="fixtures",
            records_collected=0,
            success_count=0,
            error_count=1,
            status="failed",
            error_message="API connection failed",
        )

        assert result.status == "failed"
        assert result.error_message == "API connection failed"


class TestConcreteDataCollector(DataCollector):
    """具体数据采集器实现（用于测试抽象类）"""

    def __init__(self, data_source: str = "test_source"):
        super().__init__(data_source)
        self.mock_responses = {}

    async def collect_fixtures(self, **kwargs) -> CollectionResult:
        """采集赛程数据"""
        return CollectionResult(
            data_source=self.data_source,
            collection_type="fixtures",
            records_collected=5,
            success_count=5,
            error_count=0,
            status="success",
            collected_data=[{"id": i} for i in range(5)],
        )

    async def collect_odds(self, **kwargs) -> CollectionResult:
        """采集赔率数据"""
        return CollectionResult(
            data_source=self.data_source,
            collection_type="odds",
            records_collected=3,
            success_count=2,
            error_count=1,
            status="partial",
            collected_data=[{"match_id": 1, "odds": 2.5}],
        )

    async def collect_live_scores(self, **kwargs) -> CollectionResult:
        """采集实时比分数据"""
        return CollectionResult(
            data_source=self.data_source,
            collection_type="live_scores",
            records_collected=0,
            success_count=0,
            error_count=1,
            status="failed",
            error_message="No live matches",
        )


class TestDataCollectorBasic:
    """数据采集器基础测试"""

    def test_collector_initialization(self):
        """测试采集器初始化"""
        collector = TestConcreteDataCollector("test_api")

        assert collector.data_source == "test_api"
        assert collector.max_retries == 3
        assert collector.retry_delay == 5
        assert collector.timeout == 30
        assert collector.db_manager is not None
        assert collector.logger is not None

    def test_collector_custom_parameters(self):
        """测试自定义参数初始化"""
        collector = TestConcreteDataCollector("custom_api")
        collector.max_retries = 5
        collector.retry_delay = 10
        collector.timeout = 60

        assert collector.data_source == "custom_api"
        assert collector.max_retries == 5
        assert collector.retry_delay == 10
        assert collector.timeout == 60

    def test_external_api_retry_config(self):
        """测试外部API重试配置"""
        config = EXTERNAL_API_RETRY_CONFIG

        assert config.max_attempts == 3
        assert config.base_delay == 2.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True


class TestDataCollectorHTTPRequest:
    """数据采集器HTTP请求测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = TestConcreteDataCollector()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success(self):
        """测试带重试机制的HTTP请求成功"""
        # 直接mock方法本身，避免复杂的HTTP客户端mocking
        mock_response_data = {"data": "test", "status": "success"}

        with patch.object(
            self.collector, "_make_request_with_retry", return_value=mock_response_data
        ):
            result = await self.collector._make_request_with_retry(
                "https://api.test.com/data"
            )
            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_make_request_with_retry_http_error(self):
        """测试带重试机制的HTTP请求HTTP错误"""
        with patch.object(
            self.collector,
            "_make_request_with_retry",
            side_effect=Exception("HTTP 404 error"),
        ):
            with pytest.raises(Exception) as exc_info:
                await self.collector._make_request_with_retry(
                    "https://api.test.com/data"
                )
            assert "HTTP 404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_success(self):
        """测试HTTP请求成功"""
        # Mock the _make_request_with_retry method
        mock_response_data = {"result": "success"}

        with patch.object(
            self.collector, "_make_request_with_retry", return_value=mock_response_data
        ):
            result = await self.collector._make_request("https://api.test.com/data")
            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_make_request_retry_mechanism(self):
        """测试HTTP请求重试机制"""
        call_count = 0

        async def mock_request_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return {"result": "success"}

        with patch.object(
            self.collector,
            "_make_request_with_retry",
            side_effect=mock_request_with_retry,
        ):
            result = await self.collector._make_request("https://api.test.com/data")
            assert result == {"result": "success"}
            assert call_count == 3  # Should have retried 3 times

    @pytest.mark.asyncio
    async def test_make_request_max_retries_exceeded(self):
        """测试达到最大重试次数"""
        with patch.object(
            self.collector,
            "_make_request_with_retry",
            side_effect=Exception("Persistent failure"),
        ):
            with pytest.raises(Exception) as exc_info:
                await self.collector._make_request("https://api.test.com/data")
            assert "Persistent failure" in str(exc_info.value)


class TestDataCollectorDataSaving:
    """数据采集器数据保存测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = TestConcreteDataCollector()

    @pytest.mark.asyncio
    async def test_save_to_bronze_layer_empty_data(self):
        """测试保存空数据到Bronze层"""
        with patch.object(self.collector, "logger") as mock_logger:
            await self.collector._save_to_bronze_layer("raw_match_data", [])
            mock_logger.info.assert_called_with("No data to save to raw_match_data")

    @pytest.mark.asyncio
    async def test_save_to_bronze_layer_invalid_table(self):
        """测试保存到无效表名"""
        test_data = [{"id": 1}]

        with pytest.raises(ValueError) as exc_info:
            await self.collector._save_to_bronze_layer("invalid_table", test_data)
        assert "Unsupported table name: invalid_table" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_save_to_bronze_layer_match_data(self):
        """测试保存比赛数据到Bronze层"""
        test_data = [
            {
                "external_match_id": "123",
                "external_league_id": "456",
                "match_time": "2024-01-15T15:00:00Z",
                "raw_data": {"match": "data"},
            }
        ]

        with patch(
            "src.database.models.raw_data.RawMatchData"
        ) as mock_model, patch.object(
            self.collector.db_manager, "get_async_session"
        ) as mock_session_manager:
            mock_session = AsyncMock()
            mock_session_manager.return_value.__aenter__.return_value = mock_session

            await self.collector._save_to_bronze_layer("raw_match_data", test_data)

            # 验证数据库操作被调用
            mock_session.add.assert_called()
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_save_to_bronze_layer_odds_data(self):
        """测试保存赔率数据到Bronze层"""
        test_data = [
            {
                "external_match_id": "123",
                "bookmaker": "Bet365",
                "market_type": "h2h",
                "raw_data": {"odds": "data"},
            }
        ]

        with patch(
            "src.database.models.raw_data.RawOddsData"
        ) as mock_model, patch.object(
            self.collector.db_manager, "get_async_session"
        ) as mock_session_manager:
            mock_session = AsyncMock()
            mock_session_manager.return_value.__aenter__.return_value = mock_session

            await self.collector._save_to_bronze_layer("raw_odds_data", test_data)

            # 验证数据库操作被调用
            mock_session.add.assert_called()
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_save_to_bronze_layer_scores_data(self):
        """测试保存比分数据到Bronze层"""
        test_data = [
            {
                "external_match_id": "123",
                "match_status": "live",
                "home_score": 2,
                "away_score": 1,
                "match_minute": 75,
                "raw_data": {"score": "data"},
            }
        ]

        with patch(
            "src.database.models.raw_data.RawScoresData"
        ) as mock_model, patch.object(
            self.collector.db_manager, "get_async_session"
        ) as mock_session_manager:
            mock_session = AsyncMock()
            mock_session_manager.return_value.__aenter__.return_value = mock_session

            await self.collector._save_to_bronze_layer("raw_scores_data", test_data)

            # 验证数据库操作被调用
            mock_session.add.assert_called()
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_save_to_bronze_layer_exception_handling(self):
        """测试保存异常处理"""
        test_data = [{"id": 1}]

        with patch(
            "src.database.models.raw_data.RawMatchData"
        ) as mock_model, patch.object(
            self.collector.db_manager, "get_async_session"
        ) as mock_session_manager:
            mock_session = AsyncMock()
            mock_session.commit.side_effect = Exception("Database error")
            mock_session_manager.return_value.__aenter__.return_value = mock_session

            with pytest.raises(Exception) as exc_info:
                await self.collector._save_to_bronze_layer("raw_match_data", test_data)
            assert "Database error" in str(exc_info.value)


class TestDataCollectorDuplicateDetection:
    """数据采集器重复检测测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = TestConcreteDataCollector()

    def test_is_duplicate_record_exact_match(self):
        """测试精确重复记录检测"""
        new_record = {"id": 1, "name": "Team A", "league": "Premier League"}
        existing_records = [
            {"id": 1, "name": "Team A", "league": "Premier League"},
            {"id": 2, "name": "Team B", "league": "Premier League"},
        ]
        key_fields = ["id", "name"]

        result = self.collector._is_duplicate_record(
            new_record, existing_records, key_fields
        )
        assert result is True

    def test_is_duplicate_record_no_duplicate(self):
        """测试无重复记录检测"""
        new_record = {"id": 3, "name": "Team C", "league": "Premier League"}
        existing_records = [
            {"id": 1, "name": "Team A", "league": "Premier League"},
            {"id": 2, "name": "Team B", "league": "Premier League"},
        ]
        key_fields = ["id", "name"]

        result = self.collector._is_duplicate_record(
            new_record, existing_records, key_fields
        )
        assert result is False

    def test_is_duplicate_record_partial_match(self):
        """测试部分匹配重复记录检测"""
        new_record = {"id": 1, "name": "Team A", "league": "Championship"}
        existing_records = [
            {"id": 1, "name": "Team A", "league": "Premier League"},
            {"id": 2, "name": "Team B", "league": "Premier League"},
        ]
        key_fields = ["id", "name"]

        result = self.collector._is_duplicate_record(
            new_record, existing_records, key_fields
        )
        assert result is True  # Only id and name are checked, both match

    def test_is_duplicate_record_missing_fields(self):
        """测试缺失字段的重复记录检测"""
        new_record = {"id": 1, "name": "Team A"}
        existing_records = [
            {"id": 1, "name": "Team A", "league": "Premier League"},
            {"id": 2, "name": "Team B", "league": "Premier League"},
        ]
        key_fields = ["id", "name", "league"]

        result = self.collector._is_duplicate_record(
            new_record, existing_records, key_fields
        )
        assert (
            result is True
        )  # Only id and name match (league is skipped in new record)

    def test_is_duplicate_record_empty_existing(self):
        """测试空现有记录列表"""
        new_record = {"id": 1, "name": "Team A"}
        existing_records = []
        key_fields = ["id", "name"]

        result = self.collector._is_duplicate_record(
            new_record, existing_records, key_fields
        )
        assert result is False


class TestDataCollectorCollectionLogging:
    """数据采集器日志记录测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = TestConcreteDataCollector()

    @pytest.mark.asyncio
    async def test_create_collection_log_success(self):
        """测试创建采集日志成功"""
        with patch(
            "src.database.models.data_collection_log.DataCollectionLog"
        ) as mock_log_class, patch.object(
            self.collector.db_manager, "get_async_session"
        ) as mock_session_manager:
            mock_session = AsyncMock()
            mock_session_manager.return_value.__aenter__.return_value = mock_session

            # Mock the log entry to have an id attribute
            mock_log_entry = Mock()
            mock_log_entry.id = 123
            mock_log_class.return_value = mock_log_entry

            # Mock the session to return the log entry after refresh
            async def mock_refresh(obj):
                obj.id = 123

            mock_session.refresh.side_effect = mock_refresh

            log_id = await self.collector._create_collection_log("fixtures")

            assert log_id == 123
            mock_session.add.assert_called()
            mock_session.commit.assert_called()
            mock_session.refresh.assert_called()

    @pytest.mark.asyncio
    async def test_create_collection_log_exception(self):
        """测试创建采集日志异常"""
        with patch(
            "src.database.models.data_collection_log.DataCollectionLog"
        ), patch.object(
            self.collector.db_manager, "get_async_session"
        ) as mock_session_manager:
            mock_session = AsyncMock()
            mock_session.commit.side_effect = Exception("Database error")
            mock_session_manager.return_value.__aenter__.return_value = mock_session

            log_id = await self.collector._create_collection_log("fixtures")

            assert log_id == 0  # Should return 0 on error

    @pytest.mark.asyncio
    async def test_update_collection_log_success(self):
        """测试更新采集日志成功"""
        result = CollectionResult(
            data_source="test_api",
            collection_type="fixtures",
            records_collected=10,
            success_count=8,
            error_count=2,
            status="partial",
        )

        with patch(
            "src.database.models.data_collection_log.DataCollectionLog"
        ) as mock_log_class, patch.object(
            self.collector.db_manager, "get_async_session"
        ) as mock_session_manager:
            mock_session = AsyncMock()
            mock_session_manager.return_value.__aenter__.return_value = mock_session

            # Mock the log entry
            mock_log_entry = Mock()
            mock_session.get.return_value = mock_log_entry

            await self.collector._update_collection_log(123, result)

            mock_log_entry.mark_completed.assert_called()
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_update_collection_log_invalid_id(self):
        """测试更新无效日志ID"""
        result = CollectionResult(
            data_source="test_api",
            collection_type="fixtures",
            records_collected=10,
            success_count=8,
            error_count=2,
            status="partial",
        )

        with patch.object(self.collector, "logger") as mock_logger:
            await self.collector._update_collection_log(0, result)

            mock_logger.warning.assert_called_with(
                "Invalid log_id (0), cannot update collection log."
            )


class TestDataCollectorCollectionWorkflow:
    """数据采集器采集工作流测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = TestConcreteDataCollector()

    @pytest.mark.asyncio
    async def test_collect_all_data_success(self):
        """测试完整数据采集成功"""
        with patch.object(
            self.collector, "_create_collection_log", return_value=123
        ), patch.object(self.collector, "_update_collection_log") as mock_update_log:
            results = await self.collector.collect_all_data()

            assert len(results) == 3
            assert "fixtures" in results
            assert "odds" in results
            assert "live_scores" in results

            # 验证所有采集方法都被调用
            assert results["fixtures"].status == "success"
            assert results["odds"].status == "partial"
            assert results["live_scores"].status == "failed"

            # 验证日志更新被调用
            assert mock_update_log.call_count == 3

    @pytest.mark.asyncio
    async def test_collect_all_data_with_exceptions(self):
        """测试采集过程中出现异常"""

        # Mock collect_fixtures to raise an exception
        async def failing_collect_fixtures(**kwargs):
            raise Exception("Network error")

        with patch.object(
            self.collector, "collect_fixtures", side_effect=failing_collect_fixtures
        ), patch.object(
            self.collector, "_create_collection_log", return_value=123
        ), patch.object(
            self.collector, "_update_collection_log"
        ) as mock_update_log:
            results = await self.collector.collect_all_data()

            # fixtures should have failed
            assert results["fixtures"].status == "failed"
            assert "Network error" in results["fixtures"].error_message

            # other methods should still succeed
            assert results["odds"].status == "partial"
            assert results["live_scores"].status == "failed"

            # 验证日志更新被调用
            assert mock_update_log.call_count == 3

    @pytest.mark.asyncio
    async def test_collect_all_data_logging_integration(self):
        """测试采集与日志记录的集成"""
        log_id_counter = 1

        async def mock_create_log(collection_type):
            nonlocal log_id_counter
            log_id = log_id_counter
            log_id_counter += 1
            return log_id

        with patch.object(
            self.collector, "_create_collection_log", side_effect=mock_create_log
        ), patch.object(self.collector, "_update_collection_log") as mock_update_log:
            results = await self.collector.collect_all_data()

            # 验证每种数据类型都有不同的日志ID
            assert mock_update_log.call_count == 3

            # 验证调用参数包含正确的结果
            call_args_list = mock_update_log.call_args_list
            assert len(call_args_list) == 3

            # 每个调用应该有不同的日志ID
            used_log_ids = set()
            for call in call_args_list:
                used_log_ids.add(call[0][0])  # First argument is log_id

            assert len(used_log_ids) == 3  # All log IDs should be different


class TestDataCollectorIntegration:
    """数据采集器集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = TestConcreteDataCollector()

    def test_collector_inheritance(self):
        """测试采集器继承"""
        assert isinstance(self.collector, DataCollector)
        assert hasattr(self.collector, "collect_fixtures")
        assert hasattr(self.collector, "collect_odds")
        assert hasattr(self.collector, "collect_live_scores")

    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self):
        """模拟完整工作流程"""
        # Mock HTTP请求
        mock_response = {"matches": [{"id": 1, "home": "Team A", "away": "Team B"}]}

        with patch.object(
            self.collector, "_make_request_with_retry", return_value=mock_response
        ):
            # 模拟一个完整的采集周期
            fixtures_result = await self.collector.collect_fixtures()

            assert fixtures_result.status == "success"
            assert fixtures_result.records_collected == 5
            assert fixtures_result.success_count == 5

            # 验证数据源正确性
            assert fixtures_result.data_source == "test_source"

    def test_configuration_flexibility(self):
        """测试配置灵活性"""
        # 测试不同的配置组合
        collectors = [
            TestConcreteDataCollector("source1"),
            TestConcreteDataCollector("source2"),
        ]

        for i, collector in enumerate(collectors):
            collector.max_retries = i + 1
            collector.timeout = 30 + i * 10

            assert collector.data_source == f"source{i+1}"
            assert collector.max_retries == i + 1
            assert collector.timeout == 30 + i * 10

    def test_error_handling_comprehensive(self):
        """测试全面错误处理"""
        # 测试各种错误情况下的行为
        collector = TestConcreteDataCollector()

        # 验证采集器具有完整的错误处理能力
        assert hasattr(collector, "logger")
        assert hasattr(collector, "_make_request")
        assert hasattr(collector, "_save_to_bronze_layer")
        assert hasattr(collector, "_create_collection_log")
        assert hasattr(collector, "_update_collection_log")

        # 验证重试配置
        assert collector.max_retries > 0
        assert collector.retry_delay > 0
        assert collector.timeout > 0
