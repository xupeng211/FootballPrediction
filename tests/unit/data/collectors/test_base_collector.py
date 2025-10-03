"""
数据采集器基类测试
测试src/data/collectors/base_collector.py模块
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

from src.data.collectors.base_collector import (
    DataCollector,
    CollectionResult,
    EXTERNAL_API_RETRY_CONFIG
)


class MockDataCollector(DataCollector):
    """用于测试的模拟数据采集器"""

    def __init__(self, data_source: str = os.getenv("TEST_BASE_COLLECTOR_STR_26"), **kwargs):
        super().__init__(data_source, **kwargs)

    async def collect_fixtures(self, **kwargs) -> CollectionResult:
        """模拟采集赛程数据"""
        return CollectionResult(
            data_source=self.data_source,
            collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_32"),
            records_collected=10,
            success_count=8,
            error_count=2,
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_34"),
            error_message = os.getenv("TEST_BASE_COLLECTOR_ERROR_MESSAGE_36"),
            collected_data=[{"id": i} for i in range(10)]
        )

    async def collect_odds(self, **kwargs) -> CollectionResult:
        """模拟采集赔率数据"""
        return CollectionResult(
            data_source=self.data_source,
            collection_type="odds",
            records_collected=5,
            success_count=5,
            error_count=0,
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_46"),
            collected_data=[{"match_id": i, "odds": 1.5} for i in range(5)]
        )

    async def collect_live_scores(self, **kwargs) -> CollectionResult:
        """模拟采集实时比分数据"""
        return CollectionResult(
            data_source=self.data_source,
            collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_54"),
            records_collected=3,
            success_count=2,
            error_count=1,
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_34"),
            error_message = os.getenv("TEST_BASE_COLLECTOR_ERROR_MESSAGE_58"),
            collected_data=[{"match_id": i, "score": f"{i}-0"} for i in range(3)]
        )


class TestCollectionResult:
    """测试采集结果数据结构"""

    def test_collection_result_creation(self):
        """测试创建采集结果"""
        result = CollectionResult(
            data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_63"),
            collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_32"),
            records_collected=100,
            success_count=95,
            error_count=5,
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_46")
        )

        assert result.data_source == "test_api"
        assert result.collection_type == "fixtures"
        assert result.records_collected == 100
        assert result.success_count == 95
        assert result.error_count == 5
        assert result.status == "success"
        assert result.error_message is None
        assert result.collected_data is None

    def test_collection_result_with_optional_fields(self):
        """测试带可选字段的采集结果"""
        result = CollectionResult(
            data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_63"),
            collection_type="odds",
            records_collected=50,
            success_count=45,
            error_count=5,
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_34"),
            error_message = os.getenv("TEST_BASE_COLLECTOR_ERROR_MESSAGE_88"),
            collected_data=[{"match_id": 1, "odds": 2.0}]
        )

        assert result.error_message == "Some API calls failed"
        assert len(result.collected_data) == 1
        assert result.collected_data[0]["match_id"] == 1

    def test_collection_result_status_values(self):
        """测试不同状态值"""
        statuses = ["success", "failed", "partial"]

        for status in statuses:
            result = CollectionResult(
                data_source="test",
                collection_type="test",
                records_collected=0,
                success_count=0,
                error_count=0,
                status=status
            )
            assert result.status == status


class TestDataCollectorInit:
    """测试数据采集器初始化"""

    def test_collector_initialization(self):
        """测试采集器初始化参数"""
        collector = MockDataCollector(
            data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_112"),
            max_retries=5,
            retry_delay=10,
            timeout=60
        )

        assert collector.data_source == "football_api"
        assert collector.max_retries == 5
        assert collector.retry_delay == 10
        assert collector.timeout == 60
        assert collector.db_manager is not None
        assert collector.logger is not None

    def test_collector_initialization_defaults(self):
        """测试采集器默认参数"""
        collector = MockDataCollector()

        assert collector.data_source == "test_source"
        assert collector.max_retries == 3
        assert collector.retry_delay == 5
        assert collector.timeout == 30

    def test_collector_logger_name(self):
        """测试日志器名称"""
        collector = MockDataCollector("custom_source")
        assert "MockDataCollector" in collector.logger.name
        assert "collector" in collector.logger.name


class TestExternalApiRetryConfig:
    """测试外部API重试配置"""

    def test_retry_config_values(self):
        """测试重试配置值"""
        assert EXTERNAL_API_RETRY_CONFIG.max_attempts == 3
        assert EXTERNAL_API_RETRY_CONFIG.base_delay == 2.0
        assert EXTERNAL_API_RETRY_CONFIG.max_delay == 30.0
        assert EXTERNAL_API_RETRY_CONFIG.exponential_base == 2.0
        assert EXTERNAL_API_RETRY_CONFIG.jitter == True

    def test_retry_config_exceptions(self):
        """测试重试异常类型"""
        import aiohttp
        import asyncio

        expected_exceptions = (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError)
        assert EXTERNAL_API_RETRY_CONFIG.retryable_exceptions == expected_exceptions


class TestMakeRequestWithRetry:
    """测试带重试机制的HTTP请求"""

    @pytest.mark.asyncio
    async def test_make_request_success(self):
        """测试成功的HTTP请求"""
        collector = MockDataCollector()

        mock_response = {
            "status": "success",
            "data": {"key": "value"}
        }

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.request.return_value.__aenter__.return_value = mock_response_obj
            mock_session_class.return_value.__aenter__.return_value = mock_session

            result = await collector._make_request_with_retry(
                "https://api.example.com/data"
            )

            assert result == mock_response
            mock_session.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_http_error(self):
        """测试HTTP错误响应"""
        collector = MockDataCollector()

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 404
            mock_response_obj.request_info = Mock()
            mock_response_obj.history = []

            mock_session.request.return_value.__aenter__.return_value = mock_response_obj
            mock_session_class.return_value.__aenter__.return_value = mock_session

            with pytest.raises(Exception):
                await collector._make_request_with_retry(
                    "https://api.example.com/notfound"
                )

    @pytest.mark.asyncio
    async def test_make_request_with_headers_and_params(self):
        """测试带请求头和参数的HTTP请求"""
        collector = MockDataCollector()

        headers = {"Authorization": "Bearer token"}
        params = {"page": 1, "limit": 10}
        json_data = {"key": "value"}

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value={})

            mock_session.request.return_value.__aenter__.return_value = mock_response_obj
            mock_session_class.return_value.__aenter__.return_value = mock_session

            await collector._make_request_with_retry(
                "https://api.example.com/data",
                method="POST",
                headers=headers,
                params=params,
                json_data=json_data
            )

            # 验证请求参数
            call_args = mock_session.request.call_args
            assert call_args[1]["method"] == "POST"
            assert call_args[1]["headers"] == headers
            assert call_args[1]["params"] == params
            assert call_args[1]["json"] == json_data


class TestMakeRequest:
    """测试HTTP请求方法（包含重试逻辑）"""

    @pytest.mark.asyncio
    async def test_make_request_success_on_first_try(self):
        """测试第一次尝试就成功"""
        collector = MockDataCollector()

        with patch.object(collector, '_make_request_with_retry') as mock_retry:
            mock_retry.return_value = {"success": True}

            result = await collector._make_request("https://api.example.com")

            assert result == {"success": True}
            mock_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_success_after_retry(self):
        """测试重试后成功"""
        collector = MockDataCollector(max_retries=3, retry_delay=0.1)

        with patch.object(collector, '_make_request_with_retry') as mock_retry:
            with patch('asyncio.sleep') as mock_sleep:
                # 前两次失败，第三次成功
                mock_retry.side_effect = [
                    Exception("First failure"),
                    Exception("Second failure"),
                    {"success": True}
                ]

                result = await collector._make_request("https://api.example.com")

                assert result == {"success": True}
                assert mock_retry.call_count == 3
                assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_make_request_all_attempts_fail(self):
        """测试所有尝试都失败"""
        collector = MockDataCollector(max_retries=2, retry_delay=0.1)

        with patch.object(collector, '_make_request_with_retry') as mock_retry:
            with patch('asyncio.sleep') as mock_sleep:
                mock_retry.side_effect = Exception("Persistent failure")

                with pytest.raises(Exception, match = os.getenv("TEST_BASE_COLLECTOR_MATCH_295")):
                    await collector._make_request("https://api.example.com")

                assert mock_retry.call_count == 2
                assert mock_sleep.call_count == 1


class TestSaveToBronzeLayer:
    """测试保存到Bronze层"""

    @pytest.mark.asyncio
    async def test_save_raw_match_data(self):
        """测试保存原始比赛数据"""
        collector = MockDataCollector()

        raw_data = [
            {
                "external_match_id": "123",
                "external_league_id": "456",
                "match_time": "2024-01-01T15:00:00Z",
                "raw_data": {"home": "Team A", "away": "Team B"}
            },
            {
                "external_match_id": "124",
                "external_league_id": "456",
                "match_time": "2024-01-02T18:00:00Z",
                "raw_data": {"home": "Team C", "away": "Team D"}
            }
        ]

        with patch('src.data.collectors.base_collector.DatabaseManager') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            # 模拟模型类
            with patch('src.data.collectors.base_collector.RawMatchData') as mock_model:
                mock_instance = Mock()
                mock_model.return_value = mock_instance

                await collector._save_to_bronze_layer("raw_match_data", raw_data)

                # 验证数据库操作
                assert mock_session.add.call_count == 2
                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_empty_data(self):
        """测试保存空数据"""
        collector = MockDataCollector()

        with patch.object(collector.logger, 'info') as mock_logger:
            await collector._save_to_bronze_layer("raw_match_data", [])

            mock_logger.assert_called_with("No data to save to raw_match_data")

    @pytest.mark.asyncio
    async def test_save_unsupported_table(self):
        """测试保存到不支持的表"""
        collector = MockDataCollector()

        with pytest.raises(ValueError, match = os.getenv("TEST_BASE_COLLECTOR_MATCH_350")):
            await collector._save_to_bronze_layer("invalid_table", [{"test": "data"}])

    @pytest.mark.asyncio
    async def test_save_with_invalid_match_time(self):
        """测试包含无效比赛时间的数据"""
        collector = MockDataCollector()

        raw_data = [
            {
                "external_match_id": "123",
                "match_time": "invalid-date",
                "raw_data": {"home": "Team A"}
            }
        ]

        with patch('src.data.collectors.base_collector.DatabaseManager') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            with patch('src.data.collectors.base_collector.RawMatchData') as mock_model:
                mock_instance = Mock()
                mock_model.return_value = mock_instance

                with patch.object(collector.logger, 'warning') as mock_logger:
                    await collector._save_to_bronze_layer("raw_match_data", raw_data)

                    # 验证警告日志
                    mock_logger.assert_called_once()
                    assert "Invalid match_time format" in mock_logger.call_args[0][0]


class TestIsDuplicateRecord:
    """测试重复记录检查"""

    def test_is_duplicate_true(self):
        """测试重复记录（返回True）"""
        collector = MockDataCollector()

        new_record = {"match_id": 123, "league_id": 456, "home": "Team A"}
        existing_records = [
            {"match_id": 123, "league_id": 456, "home": "Team A", "away": "Team B"},
            {"match_id": 789, "league_id": 456, "home": "Team C", "away": "Team D"}
        ]

        result = collector._is_duplicate_record(
            new_record, existing_records, ["match_id", "league_id"]
        )

        assert result is True

    def test_is_duplicate_false(self):
        """测试非重复记录（返回False）"""
        collector = MockDataCollector()

        new_record = {"match_id": 999, "league_id": 456, "home": "Team X"}
        existing_records = [
            {"match_id": 123, "league_id": 456, "home": "Team A", "away": "Team B"},
            {"match_id": 789, "league_id": 456, "home": "Team C", "away": "Team D"}
        ]

        result = collector._is_duplicate_record(
            new_record, existing_records, ["match_id", "league_id"]
        )

        assert result is False

    def test_is_duplicate_missing_fields(self):
        """测试缺失关键字段的情况"""
        collector = MockDataCollector()

        new_record = {"match_id": 123}  # 缺少league_id
        existing_records = [
            {"match_id": 123, "league_id": 456, "home": "Team A"}
        ]

        result = collector._is_duplicate_record(
            new_record, existing_records, ["match_id", "league_id"]
        )

        # 应该返回False，因为缺少关键字段
        assert result is False


class TestCollectionLog:
    """测试采集日志功能"""

    @pytest.mark.asyncio
    async def test_create_collection_log(self):
        """测试创建采集日志"""
        collector = MockDataCollector()

        with patch('src.data.collectors.base_collector.DatabaseManager') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            with patch('src.data.collectors.base_collector.DataCollectionLog') as mock_log_class:
                mock_log = Mock()
                mock_log.id = 123
                mock_log_class.return_value = mock_log

                log_id = await collector._create_collection_log("fixtures")

                assert log_id == 123
                mock_log.mark_started.assert_called_once()
                mock_session.add.assert_called_once_with(mock_log)
                mock_session.commit.assert_called_once()
                mock_session.refresh.assert_called_once_with(mock_log)

    @pytest.mark.asyncio
    async def test_create_collection_log_error(self):
        """测试创建采集日志失败"""
        collector = MockDataCollector()

        with patch.object(collector.logger, 'error') as mock_logger:
            log_id = await collector._create_collection_log("fixtures")

            assert log_id == 0
            mock_logger.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_collection_log_success(self):
        """测试更新采集日志（成功状态）"""
        collector = MockDataCollector()

        result = CollectionResult(
            data_source="test",
            collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_32"),
            records_collected=10,
            success_count=10,
            error_count=0,
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_46")
        )

        with patch('src.data.collectors.base_collector.DatabaseManager') as mock_db:
            mock_session = AsyncMock()
            mock_log = Mock()
            mock_session.get.return_value = mock_log
            mock_db.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            with patch('src.data.collectors.base_collector.DataCollectionLog') as mock_log_class:
                with patch('src.data.collectors.base_collector.CollectionStatus') as mock_status:
                    mock_status.SUCCESS = os.getenv("TEST_BASE_COLLECTOR_SUCCESS_496")

                    await collector._update_collection_log(123, result)

                    mock_log.mark_completed.assert_called_once()
                    mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_collection_log_invalid_id(self):
        """测试更新采集日志（无效ID）"""
        collector = MockDataCollector()

        result = CollectionResult(
            data_source="test",
            collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_32"),
            records_collected=0,
            success_count=0,
            error_count=0,
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_508")
        )

        with patch.object(collector.logger, 'warning') as mock_logger:
            await collector._update_collection_log(0, result)

            mock_logger.assert_called_with("Invalid log_id (0), cannot update collection log.")


class TestCollectAllData:
    """测试完整数据采集流程"""

    @pytest.mark.asyncio
    async def test_collect_all_data_success(self):
        """测试成功采集所有数据类型"""
        collector = MockDataCollector()

        with patch.object(collector, '_create_collection_log') as mock_create_log:
            with patch.object(collector, '_update_collection_log') as mock_update_log:
                mock_create_log.return_value = 100

                results = await collector.collect_all_data()

                # 验证结果
                assert len(results) == 3
                assert "fixtures" in results
                assert "odds" in results
                assert "live_scores" in results

                # 验证每种数据类型的采集结果
                assert results["fixtures"].status == "partial"
                assert results["fixtures"].records_collected == 10

                assert results["odds"].status == "success"
                assert results["odds"].records_collected == 5

                assert results["live_scores"].status == "partial"
                assert results["live_scores"].records_collected == 3

                # 验证日志调用
                assert mock_create_log.call_count == 3
                assert mock_update_log.call_count == 3

    @pytest.mark.asyncio
    async def test_collect_all_data_with_exception(self):
        """测试采集过程中的异常处理"""
        collector = MockDataCollector()

        # 让fixtures采集抛出异常
        async def failing_collect_fixtures(**kwargs):
            raise Exception("API connection failed")

        collector.collect_fixtures = failing_collect_fixtures

        with patch.object(collector, '_create_collection_log') as mock_create_log:
            with patch.object(collector, '_update_collection_log') as mock_update_log:
                with patch.object(collector.logger, 'error') as mock_logger:
                    mock_create_log.return_value = 100

                    results = await collector.collect_all_data()

                    # 验证错误处理
                    assert results["fixtures"].status == "failed"
                    assert "API connection failed" in results["fixtures"].error_message

                    # 验证其他数据类型仍然正常采集
                    assert results["odds"].status == "success"
                    assert results["live_scores"].status == "partial"

                    # 验证错误日志
                    mock_logger.assert_called()


class TestDataCollectorEdgeCases:
    """测试数据采集器边界情况"""

    def test_collector_with_different_data_sources(self):
        """测试不同数据源的采集器"""
        sources = ["api_football", "sportradar", "opta", "custom_api"]

        for source in sources:
            collector = MockDataCollector(data_source=source)
            assert collector.data_source == source

    @pytest.mark.asyncio
    async def test_make_request_different_methods(self):
        """测试不同的HTTP方法"""
        collector = MockDataCollector()

        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

        for method in methods:
            with patch.object(collector, '_make_request_with_retry') as mock_retry:
                mock_retry.return_value = {"method": method}

                result = await collector._make_request(
                    "https://api.example.com",
                    method=method
                )

                assert result["method"] == method

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """测试并发请求"""
        collector = MockDataCollector()

        async def make_multiple_requests():
            tasks = []
            for i in range(5):
                task = collector._make_request(f"https://api.example.com/data/{i}")
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        with patch.object(collector, '_make_request_with_retry') as mock_retry:
            mock_retry.return_value = {"success": True}

            results = await make_multiple_requests()

            # 验证所有请求都成功
            assert len(results) == 5
            for result in results:
                assert result["success"] == True


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "-s"])