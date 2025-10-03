from src.data.collectors.base_collector import CollectionResult, DataCollector
from unittest.mock import patch
import pytest
import os

"""
单元测试：数据收集器模块

测试数据收集器的核心功能，包括：
- CollectionResult 数据结构
- DataCollector 基础功能
- 简化的功能测试

专注于测试核心逻辑，避免复杂的外部依赖。
"""

class TestCollectionResult:
    """测试采集结果数据结构"""
    def test_collection_result_creation(self):
        """测试采集结果创建"""
        result = CollectionResult(data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_20"),": collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_20"),": records_collected=10,": success_count=8,": error_count=2,"
            status = os.getenv("TEST_DATA_COLLECTORS_STATUS_20"),": error_message = os.getenv("TEST_DATA_COLLECTORS_ERROR_MESSAGE_20"),": collected_data = [{"]id[": 1}, {"]id[": 2)])": assert result.data_source =="]test_api[" assert result.collection_type =="]fixtures[" assert result.records_collected ==10[""""
    assert result.success_count ==8
    assert result.error_count ==2
    assert result.status =="]]partial[" assert result.error_message =="]Some records failed[" assert len(result.collected_data) ==2[""""
    def test_collection_result_success(self):
        "]]""测试成功的采集结果"""
        result = CollectionResult(
        data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_24"),": collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_25"),": records_collected=5,": success_count=5,": error_count=0,"
            status = os.getenv("TEST_DATA_COLLECTORS_STATUS_27"))": assert result.status =="]success[" assert result.error_count ==0[""""
    assert result.error_message is None
    def test_collection_result_failure(self):
        "]]""测试失败的采集结果"""
        result = CollectionResult(
        data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_24"),": collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_29"),": records_collected=0,": success_count=0,": error_count=1,"
            status = os.getenv("TEST_DATA_COLLECTORS_STATUS_30"),": error_message = os.getenv("TEST_DATA_COLLECTORS_ERROR_MESSAGE_31"))": assert result.status =="]failed[" assert result.records_collected ==0[""""
    assert result.error_message =="]]API connection timeout[" class MockDataCollector(DataCollector):""""
    "]""Mock数据收集器用于测试"""
    async def collect_fixtures(self, **kwargs):
    """Mock赛程采集"""
    return CollectionResult(data_source=self.data_source,
    collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_35"),": records_collected=3,": success_count=3,": error_count=0,"
            status = os.getenv("TEST_DATA_COLLECTORS_STATUS_27"),": collected_data=["""
            {"]id[": 1, "]home[": "]Arsenal[", "]away[": "]Chelsea["},""""
            {"]id[": 2, "]home[": "]Liverpool[", "]away[": "]City["},""""
            {"]id[": 3, "]home[": "]United[", "]away[": "]Spurs[")])": async def collect_odds(self, **kwargs):"""
        "]""Mock赔率采集"""
        return CollectionResult(data_source=self.data_source,
        collection_type="odds[",": records_collected=2,": success_count=2,": error_count=0,"
            status = os.getenv("TEST_DATA_COLLECTORS_STATUS_27"),": collected_data=["""
            {"]match_id[": 1, "]home_odds[": 2.1, "]draw_odds[": 3.4, "]away_odds[": 3.2},""""
            {"]match_id[": 2, "]home_odds[": 1.8, "]draw_odds[": 3.6, "]away_odds[": 4.5)])": async def collect_live_scores(self, **kwargs):"""
        "]""Mock实时比分采集"""
        return CollectionResult(data_source=self.data_source,
        collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_48"),": records_collected=1,": success_count=1,": error_count=0,"
            status = os.getenv("TEST_DATA_COLLECTORS_STATUS_27"),": collected_data=["""
            {"]match_id[": 1, "]home_score[": 2, "]away_score[": 1, "]status[": "]live[")""""
            ])
class TestDataCollector:
    "]""测试数据收集器基类"""
    @pytest.fixture
    def mock_collector(self):
        """创建Mock数据收集器"""
        with patch("src.data.collectors.base_collector.DatabaseManager["):": return MockDataCollector(": data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_53"), max_retries=2, retry_delay=1[""""
            )
    def test_data_collector_initialization(self, mock_collector):
        "]]""测试数据收集器初始化"""
    assert mock_collector.data_source =="test_api[" assert mock_collector.max_retries ==2[""""
    assert mock_collector.retry_delay ==1
    assert hasattr(mock_collector, "]]logger[")""""
    @pytest.mark.asyncio
    async def test_collect_fixtures(self, mock_collector):
        "]""测试赛程数据采集"""
        result = await mock_collector.collect_fixtures()
    assert isinstance(result, CollectionResult)
    assert result.collection_type =="fixtures[" assert result.status =="]success[" assert result.records_collected ==3[""""
    assert len(result.collected_data) ==3
    @pytest.mark.asyncio
    async def test_collect_odds(self, mock_collector):
        "]]""测试赔率数据采集"""
        result = await mock_collector.collect_odds()
    assert isinstance(result, CollectionResult)
    assert result.collection_type =="odds[" assert result.status =="]success[" assert result.records_collected ==2[""""
    assert len(result.collected_data) ==2
    @pytest.mark.asyncio
    async def test_collect_live_scores(self, mock_collector):
        "]]""测试实时比分采集"""
        result = await mock_collector.collect_live_scores()
    assert isinstance(result, CollectionResult)
    assert result.collection_type =="live_scores[" assert result.status =="]success[" assert result.records_collected ==1[""""
    assert len(result.collected_data) ==1
    @pytest.mark.asyncio
    async def test_collect_all_data(self, mock_collector):
        "]]""测试完整数据采集流程"""
        # Mock数据库相关方法
        with patch.object(mock_collector, "_create_collection_log[", return_value = 1)": with patch.object(:": mock_collector, "]_update_collection_log[", return_value=None[""""
            ):
                results = await mock_collector.collect_all_data()
    assert isinstance(results, dict)
    assert "]]fixtures[" in results[""""
    assert "]]odds[" in results[""""
    assert "]]live_scores[" in results[""""
        # 验证每个结果
        for data_type, result in results.items():
    assert isinstance(result, CollectionResult)
    assert result.collection_type ==data_type
    assert result.status =="]]success[" class TestDataCollectorErrorHandling:""""
    "]""测试数据收集器错误处理"""
    @pytest.fixture
    def error_collector(self):
        """创建会产生错误的Mock收集器"""
        class ErrorDataCollector(DataCollector):
            async def collect_fixtures(self, **kwargs):
            raise Exception("API connection failed[")": async def collect_odds(self, **kwargs):": return CollectionResult(": data_source=self.data_source,"
            collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_25"),": records_collected=0,": success_count=0,": error_count=1,"
                    status = os.getenv("TEST_DATA_COLLECTORS_STATUS_30"),": error_message = os.getenv("TEST_DATA_COLLECTORS_ERROR_MESSAGE_105"))": async def collect_live_scores(self, **kwargs):": return CollectionResult(": data_source=self.data_source,"
                collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_29"),": records_collected=1,": success_count=1,": error_count=0,"
                    status = os.getenv("TEST_DATA_COLLECTORS_STATUS_27"))": with patch("]src.data.collectors.base_collector.DatabaseManager["):": return ErrorDataCollector(data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_113"))""""
    @pytest.mark.asyncio
    async def test_collect_all_data_with_errors(self, error_collector):
        "]""测试带错误的完整采集流程"""
        with patch.object(error_collector, "_create_collection_log[", return_value = 1)": with patch.object(:": error_collector, "]_update_collection_log[", return_value=None[""""
            ):
                results = await error_collector.collect_all_data()
    assert isinstance(results, dict)
    assert len(results) ==3
        # fixtures应该失败
        fixtures_result = results["]]fixtures["]: assert fixtures_result.status =="]failed[" assert "]API connection failed[" in fixtures_result.error_message[""""
        # odds应该失败
        odds_result = results["]]odds["]: assert odds_result.status =="]failed[" assert odds_result.error_count ==1[""""
        # live_scores应该成功
        scores_result = results["]]live_scores["]: assert scores_result.status =="]success[" assert scores_result.success_count ==1[""""
class TestDataCollectorEdgeCases:
    "]]""测试数据收集器边界情况"""
    def test_collection_result_empty_data(self):
        """测试空数据的采集结果"""
        result = CollectionResult(
        data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_121"),": collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_20"),": records_collected=0,": success_count=0,": error_count=0,"
            status = os.getenv("TEST_DATA_COLLECTORS_STATUS_27"),": collected_data=[])": assert result.records_collected ==0[" assert result.collected_data ==[]"
    assert result.status =="]]success["  # 空结果也可能是成功的[" def test_collection_result_no_collected_data(self):"""
        "]]""测试没有collected_data字段的采集结果"""
        result = CollectionResult(
        data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_129"),": collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_25"),": records_collected=5,": success_count=5,": error_count=0,"
            status = os.getenv("TEST_DATA_COLLECTORS_STATUS_27"),""""
            # 没有 collected_data 字段
        )
    assert result.collected_data is None
    assert result.records_collected ==5
    assert result.status =="]success["""""
    @pytest.mark.asyncio
    async def test_collector_with_custom_params(self):
        "]""测试带自定义参数的收集器"""
        with patch("src.data.collectors.base_collector.DatabaseManager["):": collector = MockDataCollector(": data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_137"), max_retries=5, retry_delay=10[""""
            )
    assert collector.data_source =="]]custom_api[" assert collector.max_retries ==5[""""
    assert collector.retry_delay ==10
        # 测试方法仍然工作
        result = await collector.collect_fixtures()
    assert result.data_source =="]]custom_api"