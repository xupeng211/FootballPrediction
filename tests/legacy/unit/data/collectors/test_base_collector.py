from datetime import datetime

from src.data.collectors.base_collector import CollectionResult, DataCollector
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import pytest
import os

"""
测试数据采集器基类

测试覆盖：
1. DataCollector 初始化和配置
2. CollectionResult 数据结构
3. HTTP请求方法（带重试机制）
4. 数据保存到Bronze层
5. 重复记录检测
6. 采集日志记录和管理
7. 完整数据采集流程
8. 错误处理和异常情况
"""

class TestCollectionResult:
    """测试采集结果数据结构"""
    def test_collection_result_creation_minimal(self):
        """测试最小采集结果创建"""
        result = CollectionResult(
            data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"),": collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_27"),": records_collected=10,": success_count=8,": error_count=2,"
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_27"))": assert result.data_source =="]test_source[" assert result.collection_type =="]fixtures[" assert result.records_collected ==10[""""
        assert result.success_count ==8
        assert result.error_count ==2
        assert result.status =="]]success[" assert result.error_message is None[""""
        assert result.collected_data is None
    def test_collection_result_creation_full(self):
        "]]""测试完整采集结果创建"""
        result = CollectionResult(
            data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"),": collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_33"),": records_collected=15,": success_count=12,": error_count=3,"
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_36"),": error_message = os.getenv("TEST_BASE_COLLECTOR_ERROR_MESSAGE_36"),": collected_data = [{"]id[": 1}, {"]id[": 2}])": assert result.data_source =="]test_source[" assert result.collection_type =="]odds[" assert result.records_collected ==15[""""
        assert result.success_count ==12
        assert result.error_count ==3
        assert result.status =="]]partial[" assert result.error_message =="]Some data failed to collect[" assert result.collected_data ==[{"]id[" 1}, {"]id[" 2}]" class MockDataCollector(DataCollector):"""
    "]""模拟数据采集器用于测试"""
    def __init__(self, data_source: str, **kwargs):
        super().__init__(data_source, **kwargs)
        self.test_data = [{"id[": 1, "]name[" "]test["}]": async def collect_fixtures(self, **kwargs) -> CollectionResult:": return CollectionResult(": data_source=self.data_source,"
            collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_27"),": records_collected=1,": success_count=1,": error_count=0,"
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_27"),": collected_data=self.test_data)": async def collect_odds(self, **kwargs) -> CollectionResult:": return CollectionResult("
            data_source=self.data_source,
            collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_33"),": records_collected=1,": success_count=1,": error_count=0,"
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_27"),": collected_data=self.test_data)": async def collect_live_scores(self, **kwargs) -> CollectionResult:": return CollectionResult("
            data_source=self.data_source,
            collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_47"),": records_collected=1,": success_count=1,": error_count=0,"
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_27"),": collected_data=self.test_data)": class TestDataCollector:""
    "]""测试数据采集器基类"""
    def test_data_collector_initialization(self):
        """测试数据采集器初始化"""
        collector = MockDataCollector(
            data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"), max_retries=5, retry_delay=10, timeout=60[""""
        )
        assert collector.data_source =="]]test_source[" assert collector.max_retries ==5[""""
        assert collector.retry_delay ==10
        assert collector.timeout ==60
        assert collector.db_manager is not None
        assert collector.logger is not None
    def test_data_collector_initialization_defaults(self):
        "]]""测试数据采集器默认参数初始化"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))": assert collector.data_source =="]test_source[" assert collector.max_retries ==3[""""
        assert collector.retry_delay ==5
        assert collector.timeout ==30
    @pytest.mark.asyncio
    async def test_make_request_with_retry_success(self):
        "]]""测试HTTP请求成功（带重试装饰器）"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock aiohttp response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"]data[": ["]test["})""""
        # Mock aiohttp session
        mock_session = MagicMock()
        mock_session.request.return_value.__aenter__.return_value = mock_response
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        with patch("]aiohttp.ClientSession[", return_value = mock_session)": result = await collector._make_request_with_retry("""
                "]https://api.test.com/data["""""
            )
        assert result =={"]data[" ["]test["}" mock_session.request.assert_called_once_with("""
            method="]GET[",": url = os.getenv("TEST_BASE_COLLECTOR_URL_77"),": headers=None,": params=None,": json=None)"
    @pytest.mark.asyncio
    async def test_make_request_with_retry_http_error(self):
        "]""测试HTTP请求失败"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock aiohttp response with error = mock_response MagicMock()
        mock_response.status = 404
        mock_response.request_info = MagicMock()
        mock_response.history = []
        # Mock aiohttp session
        mock_session = MagicMock()
        mock_session.request.return_value.__aenter__.return_value = mock_response
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        with patch("]aiohttp.ClientSession[", return_value = mock_session)": with pytest.raises(aiohttp.ClientResponseError):": await collector._make_request_with_retry("]https://api.test.com/data[")""""
    @pytest.mark.asyncio
    async def test_make_request_success(self):
        "]""测试HTTP请求成功（带手动重试）"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock the retry method to return successful result
        with patch.object(:
            collector, "]_make_request_with_retry[", return_value = {"]data[" "]test["}""""
        ) as mock_retry = result await collector._make_request("]https//api.test.com/data[")": assert result =={"]data[" ["]test["}" mock_retry.assert_called_once_with("""
            url = os.getenv("TEST_BASE_COLLECTOR_URL_77"),": method="]GET[",": headers=None,": params=None,": json_data=None)"
    @pytest.mark.asyncio
    async def test_make_request_with_retries(self):
        "]""测试HTTP请求带重试机制"""
        collector = MockDataCollector(
            data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"), max_retries=2, retry_delay=0.1[""""
        )
        # Mock the retry method to fail first time, succeed second time
        call_count = 0
        async def mock_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count ==1
                raise Exception("]]First attempt failed[")": return {"]data[" "]success["}": with patch.object(:": collector, "]_make_request_with_retry[", side_effect=mock_retry[""""
        ) as mock_retry_method = result await collector._make_request("]]https//api.test.com/data[")": assert result =={"]data[" ["]success["}" assert call_count ==2["""
        assert mock_retry_method.call_count ==2
    @pytest.mark.asyncio
    async def test_make_request_max_retries_exceeded(self):
        "]]""测试HTTP请求超过最大重试次数"""
        collector = MockDataCollector(
            data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"), max_retries=2, retry_delay=0.1[""""
        )
        # Mock the retry method to always fail
        with patch.object(:
            collector, "]]_make_request_with_retry[", side_effect=Exception("]Always fails[")""""
        ) as mock_retry:
            with pytest.raises(Exception, match = os.getenv("TEST_BASE_COLLECTOR_MATCH_123"))": await collector._make_request("]https://api.test.com/data[")""""
            # Should have been called max_retries times
            assert mock_retry.call_count ==2
    @pytest.mark.asyncio
    async def test_save_to_bronze_layer_success(self):
        "]""测试成功保存数据到Bronze层"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock database session and models
        mock_session = MagicMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.commit = AsyncMock()
        collector.db_manager.get_async_session = MagicMock(return_value=mock_session)
        # Mock the raw data models
        with patch("]src.database.models.raw_data.RawMatchData[") as mock_model:": mock_instance = MagicMock()": mock_model.return_value = mock_instance[": test_data = ["
                {"]]raw_data[": {"]match_id[": 123}, "]external_match_id[": "]ext_123["}""""
            ]
            await collector._save_to_bronze_layer("]raw_match_data[", test_data)""""
        # Verify the model was created with correct data:
        mock_model.assert_called_once()
        args, kwargs = mock_model.call_args
        assert kwargs["]data_source["] =="]test_source[" assert kwargs["]raw_data["] =={"]match_id[" 123}" assert kwargs["]processed["] is False[""""
        # Verify external_match_id was set separately
        assert mock_instance.external_match_id =="]]ext_123["""""
        # Verify session operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    @pytest.mark.asyncio
    async def test_save_to_bronze_layer_empty_data(self):
        "]""测试保存空数据到Bronze层"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))": with patch.object(collector.logger, "]info[") as mock_logger:": await collector._save_to_bronze_layer("]raw_match_data[", [])": mock_logger.assert_called_once_with("]No data to save to raw_match_data[")""""
    @pytest.mark.asyncio
    async def test_save_to_bronze_layer_invalid_table(self):
        "]""测试保存到无效表名"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))": with pytest.raises(ValueError, match = os.getenv("TEST_BASE_COLLECTOR_MATCH_158"): ["]invalid_table[")": await collector._save_to_bronze_layer("]invalid_table[", [{"]data[": "]test["}])""""
    @pytest.mark.asyncio
    async def test_save_to_bronze_layer_with_match_time(self):
        "]""测试保存包含match_time的数据"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock database session
        mock_session = MagicMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.commit = AsyncMock()
        collector.db_manager.get_async_session = MagicMock(return_value=mock_session)
        # Mock the raw data models
        with patch("]src.database.models.raw_data.RawMatchData[") as mock_model:": mock_instance = MagicMock()": mock_model.return_value = mock_instance[": test_data = ["
                {
                    "]]raw_data[": {"]match_id[": 123},""""
                    "]external_match_id[": ["]ext_123[",""""
                    "]match_time[: "2024-01-01T12:00:00Z["}"]"""
            ]
            await collector._save_to_bronze_layer("]raw_match_data[", test_data)""""
        # Verify match_time was parsed correctly
        mock_model.assert_called_once()
        assert isinstance(mock_instance.match_time, datetime)
    @pytest.mark.asyncio
    async def test_save_to_bronze_layer_invalid_match_time(self):
        "]""测试保存包含无效match_time的数据"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock database session
        mock_session = MagicMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.commit = AsyncMock()
        collector.db_manager.get_async_session = MagicMock(return_value=mock_session)
        # Mock the raw data models
        with patch("]src.database.models.raw_data.RawMatchData[") as mock_model:": mock_instance = MagicMock()": mock_model.return_value = mock_instance[": with patch.object(collector.logger, "]]warning[") as mock_logger:": test_data = ["""
                    {
                        "]raw_data[": {"]match_id[": 123},""""
                        "]external_match_id[": ["]ext_123[",""""
                        "]match_time[": ["]invalid_date["}""""
                ]
                await collector._save_to_bronze_layer("]raw_match_data[", test_data)""""
            # Verify warning was logged for invalid date format:
            mock_logger.assert_called_once()
    def test_is_duplicate_record_true(self):
        "]""测试重复记录检测（重复）"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))": new_record = {"]id[": 1, "]name[": "]test[", "]value[" "]A["}": existing_records = ["""
            {"]id[": 1, "]name[": "]test[", "]value[": "]B["},  # Same id and name[""""
            {"]]id[": 2, "]name[": "]other[", "]value[": "]C["}]": result = collector._is_duplicate_record(": new_record, existing_records, ["]id[", "]name["]""""
        )
        assert result is True
    def test_is_duplicate_record_false(self):
        "]""测试重复记录检测（不重复）"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))": new_record = {"]id[": 3, "]name[": "]test[", "]value[" "]A["}": existing_records = ["""
            {"]id[": 1, "]name[": "]test[", "]value[": "]B["},""""
            {"]id[": 2, "]name[": "]other[", "]value[": "]C["}]": result = collector._is_duplicate_record(": new_record, existing_records, ["]id[", "]name["]""""
        )
        assert result is False
    def test_is_duplicate_record_missing_fields(self):
        "]""测试重复记录检测（字段缺失）"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))": new_record = {"]id[": 1, "]name[" "]test["}": existing_records = [{"]id[": 1, "]value[": "]A["}]  # Missing 'name' field[": result = collector._is_duplicate_record(": new_record, existing_records, ["]]id[", "]name["]""""
        )
        # Should be duplicate because all fields present in both records match (only 'id' field)
        assert result is True
    @pytest.mark.asyncio
    async def test_create_collection_log_success(self):
        "]""测试创建采集日志成功"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock database session and model
        mock_session = MagicMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        collector.db_manager.get_async_session = MagicMock(return_value=mock_session)
        # Mock the log entry
        mock_log_entry = MagicMock()
        mock_log_entry.id = 123
        with patch(:
            "]src.database.models.data_collection_log.DataCollectionLog[",": return_value=mock_log_entry):": log_id = await collector._create_collection_log("]fixtures[")": assert log_id ==123[" mock_session.add.assert_called_once_with(mock_log_entry)""
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_log_entry)
        mock_log_entry.mark_started.assert_called_once()
    @pytest.mark.asyncio
    async def test_create_collection_log_failure(self):
        "]]""测试创建采集日志失败"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock database session to raise exception
        mock_session = MagicMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.commit = AsyncMock()
        collector.db_manager.get_async_session = MagicMock(return_value=mock_session)
        with patch(:
            "]src.database.models.data_collection_log.DataCollectionLog[",": side_effect=Exception("]DB error[")):": with patch.object(collector.logger, "]error[") as mock_logger:": log_id = await collector._create_collection_log("]fixtures[")": assert log_id ==0[" mock_logger.assert_called_once_with("]]Failed to create collection log[": [DB error])""""
    @pytest.mark.asyncio
    async def test_update_collection_log_success(self):
        "]""测试更新采集日志成功"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock database session and model
        mock_session = MagicMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.commit = AsyncMock()
        collector.db_manager.get_async_session = MagicMock(return_value=mock_session)
        # Mock the log entry and status enum
        mock_log_entry = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_log_entry)
        with patch(:
            "]src.database.models.data_collection_log.CollectionStatus["""""
        ):
            result = CollectionResult(
                data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_261"),": collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_27"),": records_collected=10,": success_count=8,": error_count=2,"
                status = os.getenv("TEST_BASE_COLLECTOR_STATUS_27"))": await collector._update_collection_log(123, result)"""
        # Should be called with DataCollectionLog class and log_id:
        mock_session.get.assert_called_once()
        mock_log_entry.mark_completed.assert_called_once()
        mock_session.commit.assert_called_once()
    @pytest.mark.asyncio
    async def test_update_collection_log_invalid_log_id(self):
        "]""测试更新采集日志（无效log_id）"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))": result = CollectionResult(": data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_261"),": collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_27"),": records_collected=10,": success_count=8,": error_count=2,"
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_27"))": with patch.object(collector.logger, "]warning[") as mock_logger:": await collector._update_collection_log(0, result)": mock_logger.assert_called_once_with(""
            "]Invalid log_id (0), cannot update collection log."""""
        )
    @pytest.mark.asyncio
    async def test_update_collection_log_log_not_found(self):
        """测试更新采集日志（日志不存在）"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock database session
        mock_session = MagicMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.get.return_value = None  # Log entry not found
        mock_session.commit = AsyncMock()
        collector.db_manager.get_async_session = MagicMock(return_value=mock_session)
        result = CollectionResult(
            data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_261"),": collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_27"),": records_collected=10,": success_count=8,": error_count=2,"
            status = os.getenv("TEST_BASE_COLLECTOR_STATUS_27"))""""
        # Should not raise exception
        await collector._update_collection_log(999, result)
    @pytest.mark.asyncio
    async def test_collect_all_data_success(self):
        "]""测试完整数据采集流程成功"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock the log creation and update methods
        with patch.object(:
            collector, "]_create_collection_log[", return_value=1[""""
        ) as mock_create, patch.object(
            collector, "]]_update_collection_log["""""
        ) as mock_update = results await collector.collect_all_data()
        assert len(results) ==3
        assert "]fixtures[" in results[""""
        assert "]]odds[" in results[""""
        assert "]]live_scores[" in results[""""
        # Verify all results are successful
        for result in results.values():
            assert result.status =="]]success[" assert result.success_count ==1[""""
            assert result.error_count ==0
        # Verify logs were created and updated
        assert mock_create.call_count ==3
        assert mock_update.call_count ==3
    @pytest.mark.asyncio
    async def test_collect_all_data_with_failure(self):
        "]]""测试完整数据采集流程（包含失败）"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock collect_odds to fail
        async def failing_collect_odds(**kwargs):
            raise Exception("]Odds collection failed[")": collector.collect_odds = failing_collect_odds["""
        # Mock the log creation and update methods
        with patch.object(:
            collector, "]]_create_collection_log[", return_value=1[""""
        ) as mock_create_log, patch.object(
            collector, "]]_update_collection_log["""""
        ) as mock_update = results await collector.collect_all_data()
        assert len(results) ==3
        assert results["]fixtures["].status =="]success[" assert results["]odds["].status =="]failed[" assert results["]live_scores["].status =="]success["""""
        # Verify the failed result has correct error message
        assert results["]odds["].error_message =="]Odds collection failed[" assert results["]odds["].success_count ==0[" assert results["]]odds["].error_count ==1[""""
        # Verify logs were still created and updated for all collections:
        assert mock_create_log.call_count ==3
        assert mock_update.call_count ==3
    @pytest.mark.asyncio
    async def test_collect_all_data_log_creation_failure(self):
        "]]""测试完整数据采集流程（日志创建失败）"""
        collector = MockDataCollector(data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27"))""""
        # Mock log creation to fail
        with patch.object(:
            collector, "]_create_collection_log[", return_value=0[""""
        ), patch.object(collector, "]]_update_collection_log[") as mock_update:": results = await collector.collect_all_data()": assert len(results) ==3[" assert all(result.status =="]]success[" for result in results.values())"]"""
        # Verify update was still called with log_id = 0
        assert mock_update.call_count ==3
        for call in mock_update.call_args_list:
            assert call[0][0] ==0  # First argument is log_id