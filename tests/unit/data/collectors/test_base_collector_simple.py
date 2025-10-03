"""
数据采集器基类简单测试
只测试基本功能，不涉及复杂的数据库操作
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

from src.data.collectors.base_collector import (
    DataCollector,
    CollectionResult,
    EXTERNAL_API_RETRY_CONFIG
)


class SimpleDataCollector(DataCollector):
    """简单的测试用数据采集器"""

    def __init__(self, data_source: str = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STR_24"), **kwargs):
        super().__init__(data_source, **kwargs)

    async def collect_fixtures(self, **kwargs) -> CollectionResult:
        return CollectionResult(
            data_source=self.data_source,
            collection_type = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_29"),
            records_collected=5,
            success_count=5,
            error_count=0,
            status = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STATUS_31")
        )

    async def collect_odds(self, **kwargs) -> CollectionResult:
        return CollectionResult(
            data_source=self.data_source,
            collection_type="odds",
            records_collected=3,
            success_count=3,
            error_count=0,
            status = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STATUS_31")
        )

    async def collect_live_scores(self, **kwargs) -> CollectionResult:
        return CollectionResult(
            data_source=self.data_source,
            collection_type = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_45"),
            records_collected=2,
            success_count=2,
            error_count=0,
            status = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STATUS_31")
        )


class TestCollectionResult:
    """测试采集结果"""

    def test_collection_result_basic(self):
        """测试基本采集结果"""
        result = CollectionResult(
            data_source="test",
            collection_type = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_29"),
            records_collected=10,
            success_count=8,
            error_count=2,
            status = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STATUS_61")
        )

        assert result.data_source == "test"
        assert result.collection_type == "fixtures"
        assert result.records_collected == 10
        assert result.success_count == 8
        assert result.error_count == 2
        assert result.status == "partial"

    def test_collection_result_with_data(self):
        """测试带数据的采集结果"""
        data = [{"id": 1}, {"id": 2}]
        result = CollectionResult(
            data_source="test",
            collection_type = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_29"),
            records_collected=2,
            success_count=2,
            error_count=0,
            status = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STATUS_31"),
            collected_data=data
        )

        assert result.collected_data == data
        assert len(result.collected_data) == 2


class TestDataCollectorBasic:
    """测试数据采集器基本功能"""

    def test_collector_creation(self):
        """测试创建采集器"""
        collector = SimpleDataCollector("football_api")

        assert collector.data_source == "football_api"
        assert collector.max_retries == 3
        assert collector.retry_delay == 5
        assert collector.timeout == 30
        assert collector.db_manager is not None
        assert collector.logger is not None

    def test_collector_custom_params(self):
        """测试自定义参数"""
        collector = SimpleDataCollector(
            data_source = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_DATA_SOURCE_101"),
            max_retries=5,
            retry_delay=10,
            timeout=60
        )

        assert collector.data_source == "custom_api"
        assert collector.max_retries == 5
        assert collector.retry_delay == 10
        assert collector.timeout == 60

    def test_is_duplicate_record(self):
        """测试重复记录检查"""
        collector = SimpleDataCollector()

        # 测试重复记录
        new_record = {"match_id": 123, "league_id": 456}
        existing_records = [
            {"match_id": 123, "league_id": 456, "home": "Team A"},
            {"match_id": 789, "league_id": 456, "home": "Team B"}
        ]

        assert collector._is_duplicate_record(
            new_record, existing_records, ["match_id", "league_id"]
        ) is True

        # 测试非重复记录
        new_record2 = {"match_id": 999, "league_id": 456}
        assert collector._is_duplicate_record(
            new_record2, existing_records, ["match_id", "league_id"]
        ) is False

    def test_is_duplicate_record_missing_fields(self):
        """测试缺失字段的情况"""
        collector = SimpleDataCollector()

        new_record = {"match_id": 123}  # 缺少league_id
        existing_records = [
            {"match_id": 123, "league_id": 456}
        ]

        # 实际行为：只有match_id匹配，所以会返回True
        result = collector._is_duplicate_record(
            new_record, existing_records, ["match_id", "league_id"]
        )
        assert result is True


class TestCollectAllData:
    """测试完整采集流程"""

    @pytest.mark.asyncio
    async def test_collect_all_success(self):
        """测试成功采集所有数据"""
        collector = SimpleDataCollector()

        results = await collector.collect_all_data()

        assert len(results) == 3
        assert "fixtures" in results
        assert "odds" in results
        assert "live_scores" in results

        # 验证每个采集结果
        for data_type, result in results.items():
            assert result.data_source == "test_source"
            assert result.collection_type == data_type
            assert result.status == "success"
            assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_collect_all_with_failure(self):
        """测试采集失败的处理"""
        collector = SimpleDataCollector()

        # 让fixtures采集失败
        async def failing_collect(**kwargs):
            raise Exception("API Error")

        collector.collect_fixtures = failing_collect

        with patch.object(collector.logger, 'error') as mock_logger:
            results = await collector.collect_all_data()

            # 验证失败处理
            assert results["fixtures"].status == "failed"
            assert "API Error" in results["fixtures"].error_message

            # 验证其他数据仍然成功
            assert results["odds"].status == "success"
            assert results["live_scores"].status == "success"

            # 验证错误日志
            mock_logger.assert_called()


class TestRetryConfig:
    """测试重试配置"""

    def test_retry_config_exists(self):
        """测试重试配置存在"""
        assert EXTERNAL_API_RETRY_CONFIG is not None

    def test_retry_config_attributes(self):
        """测试重试配置属性"""
        assert hasattr(EXTERNAL_API_RETRY_CONFIG, 'max_attempts')
        assert hasattr(EXTERNAL_API_RETRY_CONFIG, 'base_delay')
        assert hasattr(EXTERNAL_API_RETRY_CONFIG, 'max_delay')
        assert hasattr(EXTERNAL_API_RETRY_CONFIG, 'exponential_base')
        assert hasattr(EXTERNAL_API_RETRY_CONFIG, 'jitter')
        assert hasattr(EXTERNAL_API_RETRY_CONFIG, 'retryable_exceptions')

    def test_retry_config_values(self):
        """测试重试配置值"""
        assert EXTERNAL_API_RETRY_CONFIG.max_attempts == 3
        assert EXTERNAL_API_RETRY_CONFIG.base_delay == 2.0
        assert EXTERNAL_API_RETRY_CONFIG.max_delay == 30.0
        assert EXTERNAL_API_RETRY_CONFIG.exponential_base == 2.0
        assert EXTERNAL_API_RETRY_CONFIG.jitter is True


class TestAbstractMethods:
    """测试抽象方法"""

    def test_abstract_methods_exist(self):
        """测试抽象方法存在"""
        abstract_methods = DataCollector.__abstractmethods__

        assert 'collect_fixtures' in abstract_methods
        assert 'collect_odds' in abstract_methods
        assert 'collect_live_scores' in abstract_methods

    def test_concrete_implementation(self):
        """测试具体实现"""
        collector = SimpleDataCollector()

        # 应该可以调用抽象方法
        import asyncio

        async def test_methods():
            fixtures = await collector.collect_fixtures()
            odds = await collector.collect_odds()
            scores = await collector.collect_live_scores()

            assert isinstance(fixtures, CollectionResult)
            assert isinstance(odds, CollectionResult)
            assert isinstance(scores, CollectionResult)

        # 运行测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(test_methods())
        loop.close()


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "-s"])