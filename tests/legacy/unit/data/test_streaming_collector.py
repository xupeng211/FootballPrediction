from datetime import datetime

from src.data.collectors.base_collector import CollectionResult
from src.data.collectors.streaming_collector import StreamingDataCollector
from src.streaming import StreamConfig
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import pytest

"""
流式数据采集器的单元测试

测试覆盖：
- 流式数据采集功能
- Kafka集成
- 错误处理和重试机制
- 批量流处理
- 配置管理
"""

class TestStreamingDataCollector:
    """测试流式数据采集器的所有功能"""
    @pytest.fixture
    def default_config(self):
        """默认配置"""
        return {
        "data_source[": ["]test_source[",""""
        "]max_retries[": 3,""""
        "]retry_delay[": 1,""""
        "]timeout[": 10,""""
            "]enable_streaming[": True}""""
    @pytest.fixture
    def mock_stream_config(self):
        "]""模拟流配置"""
        config = MagicMock(spec=StreamConfig)
        config.kafka_bootstrap_servers = "localhost9092[": config.topic_prefix = "]football[": config.batch_size = 100[": config.flush_timeout = 5[": return config[""
    @pytest.fixture
    def mock_kafka_producer(self):
        "]]]]""模拟Kafka生产者"""
        producer = AsyncMock()
        producer.send.return_value = AsyncMock()
        producer.flush.return_value = None
        producer.close.return_value = None
        return producer
    @pytest.fixture
    def sample_data(self):
        """示例采集数据"""
        return [
        {
        "id[": 1,""""
        "]type[": ["]match[",""""
        "]home_team[: "Team A[","]"""
            "]away_team[: "Team B[","]"""
                "]timestamp[": datetime.now().isoformat()},""""
            {
                "]id[": 2,""""
                "]type[": ["]odds[",""""
                "]match_id[": 1,""""
                "]home_odds[": 2.1,""""
                "]away_odds[": 3.2,""""
                "]timestamp[": datetime.now().isoformat()}]": def test_streaming_collector_initialization_default(self, default_config):"""
        "]""测试默认配置初始化"""
        collector = StreamingDataCollector(**default_config)
    assert collector.data_source ==default_config["data_source["]" assert collector.max_retries ==default_config["]max_retries["]" assert collector.retry_delay ==default_config["]retry_delay["]" assert collector.timeout ==default_config["]timeout["]" assert collector.enable_streaming ==default_config["]enable_streaming["]" assert collector.stream_config is not None  # 应该使用默认配置["""
    def test_streaming_collector_initialization_custom_config(self, mock_stream_config):
        "]]""测试自定义流配置初始化"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            # Mock producer初始化成功
            mock_producer_class.return_value = MagicMock()
            collector = StreamingDataCollector(
            data_source="]custom_source[",": enable_streaming=True,": stream_config=mock_stream_config)": assert collector.data_source =="]custom_source[" assert collector.enable_streaming is True[""""
    assert collector.stream_config ==mock_stream_config
    def test_streaming_collector_initialization_disabled(self):
        "]]""测试禁用流式处理的初始化"""
        collector = StreamingDataCollector(
        data_source="test_source[", enable_streaming=False[""""
        )
    assert collector.enable_streaming is False
    assert collector.kafka_producer is None
    @pytest.mark.asyncio
    async def test_collect_with_streaming_enabled_success(
        self, mock_kafka_producer, sample_data
    ):
        "]]""测试启用流式处理的数据采集成功"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            mock_producer_class.return_value = mock_kafka_producer
            collector = StreamingDataCollector(
            data_source="]test_source[", enable_streaming=True[""""
            )
            # 确保Kafka生产者初始化成功
    assert collector.enable_streaming is True
    assert collector.kafka_producer is not None
        # Mock _send_to_stream 方法以避免实际Kafka调用
        with patch.object(collector, "]]_send_to_stream[") as mock_send_stream:": mock_send_stream.return_value = {"""
            "]success[": len(sample_data),""""
            "]failed[": 0}""""
                # Mock父类的collect_fixtures方法
                with patch.object(:
                    collector.__class__.__bases__[0], "]collect_fixtures["""""
                ) as mock_collect:
                    mock_collect.return_value = CollectionResult(
                    data_source="]test_source[",": collection_type="]fixtures[",": records_collected=len(sample_data),": success_count=len(sample_data),": error_count=0,"
                        status="]success[",": collected_data=sample_data)"""
                    # 执行测试 - 调用带流处理的方法
                    result = await collector.collect_fixtures_with_streaming()
                    # 验证结果
    assert isinstance(result, CollectionResult)
    assert result.status =="]success[" assert result.records_collected ==len(sample_data)""""
    assert result.error_count ==0
        # 验证流处理被调用
        mock_send_stream.assert_called_once_with(sample_data, "]match[")""""
    @pytest.mark.asyncio
    async def test_collect_with_streaming_disabled(self, sample_data):
        "]""测试禁用流式处理的数据采集"""
        collector = StreamingDataCollector(
        data_source="test_source[", enable_streaming=False[""""
        )
        # Mock基础采集方法
        with patch.object(collector, "]]collect_fixtures[") as mock_collect:": mock_collect.return_value = CollectionResult(": data_source="]test_source[",": collection_type="]fixtures[",": records_collected=len(sample_data),": success_count=len(sample_data),": error_count=0,"
                status="]success[",": collected_data=sample_data)"""
            # 执行测试
            result = await collector.collect_fixtures()
            # 验证结果 - 应该正常采集但不发送流
    assert isinstance(result, CollectionResult)
    assert result.status =="]success[" assert result.records_collected ==len(sample_data)""""
        # 验证没有Kafka操作
    assert collector.kafka_producer is None
    @pytest.mark.asyncio
    async def test_kafka_producer_send_error_handling(
        self, mock_kafka_producer, sample_data
    ):
        "]""测试Kafka发送异常处理"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            # Mock Kafka发送失败
            mock_kafka_producer.send.side_effect = Exception("]Kafka send failed[")": mock_producer_class.return_value = mock_kafka_producer[": collector = StreamingDataCollector(": data_source="]]test_source[", enable_streaming=True[""""
            )
            # Mock基础采集方法
            with patch.object(collector, "]]collect_fixtures[") as mock_collect:": mock_collect.return_value = CollectionResult(": data_source="]test_source[",": collection_type="]fixtures[",": records_collected=len(sample_data),": success_count=len(sample_data),": error_count=0,"
                    status="]success[",": collected_data=sample_data)"""
                # 执行测试
                result = await collector.collect_fixtures()
                # 验证结果 - 应该处理错误但不影响数据采集
    assert isinstance(result, CollectionResult)
    assert result.status =="]success["  # 数据采集成功[" assert result.records_collected ==len(sample_data)"""
        # 可能会有Kafka相关的警告，但不应该是严重错误
    @pytest.mark.asyncio
    async def test_batch_stream_processing_success(self, mock_kafka_producer):
        "]]""测试批量流处理成功"""
        # 大量数据测试批量处理
        large_data = [
        {
        "id[": i,""""
        "]type[": ["]test_data[",""""
        "]value[": f["]value_{i}"],""""
            "timestamp[": datetime.now().isoformat()}": for i in range(250)  # 超过默认批量大小:"""
        ]
        with patch(:
            "]src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            mock_producer_class.return_value = mock_kafka_producer
            collector = StreamingDataCollector(
            data_source="]test_source[", enable_streaming=True[""""
            )
            # 确保Kafka生产者初始化成功
    assert collector.enable_streaming is True
    assert collector.kafka_producer is not None
        # Mock _send_to_stream 方法以避免实际Kafka调用
        with patch.object(collector, "]]_send_to_stream[") as mock_send_stream:": mock_send_stream.return_value = {"""
            "]success[": len(large_data),""""
            "]failed[": 0}""""
                # Mock父类的collect_fixtures方法
                with patch.object(:
                    collector.__class__.__bases__[0], "]collect_fixtures["""""
                ) as mock_collect:
                    mock_collect.return_value = CollectionResult(
                    data_source="]test_source[",": collection_type="]fixtures[",": records_collected=len(large_data),": success_count=len(large_data),": error_count=0,"
                        status="]success[",": collected_data=large_data)"""
                    # 执行测试 - 调用带流处理的方法
                    result = await collector.collect_fixtures_with_streaming()
                    # 验证结果
    assert result.status =="]success[" assert result.records_collected ==len(large_data)""""
                # 验证流处理被调用
                mock_send_stream.assert_called_once_with(large_data, "]match[")""""
    @pytest.mark.asyncio
    async def test_send_to_stream_method_success(
        self, mock_kafka_producer, sample_data
    ):
        "]""测试发送到流的方法"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            mock_producer_class.return_value = mock_kafka_producer
            collector = StreamingDataCollector(
            data_source="]test_source[", enable_streaming=True[""""
            )
            # 确保Kafka生产者初始化成功
    assert collector.enable_streaming is True
    assert collector.kafka_producer is not None
        # Mock send_batch 方法返回成功统计
        mock_kafka_producer.send_batch.return_value = {
        "]]success[": len(sample_data),""""
        "]failed[": 0}""""
            # 执行测试
            success = await collector.send_to_stream(sample_data)
            # 验证结果
    assert success is True
        # 验证send_batch被调用而不是send
        mock_kafka_producer.send_batch.assert_called_once()
    @pytest.mark.asyncio
    async def test_send_to_stream_method_disabled(self, sample_data):
        "]""测试流式处理禁用时的发送方法"""
        collector = StreamingDataCollector(
        data_source="test_source[", enable_streaming=False[""""
        )
        # 执行测试
        success = await collector.send_to_stream(sample_data)
        # 验证结果 - 应该直接返回True（跳过流式处理）
    assert success is True
    @pytest.mark.asyncio
    async def test_send_to_stream_empty_data(self, mock_kafka_producer):
        "]]""测试发送空数据"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            mock_producer_class.return_value = mock_kafka_producer
            collector = StreamingDataCollector(
            data_source="]test_source[", enable_streaming=True[""""
            )
            # 执行测试
            success = await collector.send_to_stream([])
            # 验证结果
    assert success is True
        mock_kafka_producer.send.assert_not_called()
        mock_kafka_producer.flush.assert_not_called()
    @pytest.mark.asyncio
    async def test_kafka_producer_initialization_error(self):
        "]]""测试Kafka生产者初始化失败"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            # Mock初始化失败
            mock_producer_class.side_effect = Exception("]Kafka initialization failed[")""""
            # 执行测试 - 初始化应该处理异常
            collector = StreamingDataCollector(
            data_source="]test_source[", enable_streaming=True[""""
            )
            # 验证错误处理 - Kafka失败时应该禁用流式处理
    assert collector.enable_streaming is False  # 修正：初始化失败时应为False
        # Kafka生产者应该为None
    assert collector.kafka_producer is None
    @pytest.mark.asyncio
    async def test_topic_name_generation(self, mock_kafka_producer):
        "]]""测试主题名称生成"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            mock_producer_class.return_value = mock_kafka_producer
            collector = StreamingDataCollector(
            data_source="]custom_source[", enable_streaming=True[""""
            )
            test_data = [{"]]id[": 1, "]type[": "]match["}]""""
            # 执行测试
            await collector.send_to_stream(test_data)
            # 验证主题名称格式
            if mock_kafka_producer.send.called = call_args mock_kafka_producer.send.call_args_list[0]
            topic = call_args[1].get("]topic[") or call_args[0][0]""""
            # 验证主题名称包含数据源信息
    assert isinstance(topic, str)
    assert len(topic) > 0
    @pytest.mark.asyncio
    async def test_data_serialization_for_kafka(self, mock_kafka_producer):
        "]""测试数据序列化用于Kafka"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            mock_producer_class.return_value = mock_kafka_producer
            collector = StreamingDataCollector(
            data_source="]test_source[", enable_streaming=True[""""
            )
            # 确保Kafka生产者初始化成功
    assert collector.enable_streaming is True
    assert collector.kafka_producer is not None
        # 包含特殊数据类型的测试数据
        test_data = [
        {
        "]]id[": 1,""""
            "]timestamp[": datetime.now().isoformat(),  # 修复：使用ISO格式字符串[""""
            "]]float_value[": 3.14,""""
                "]bool_value[": True,""""
                    "]none_value[": None}""""
            ]
            # Mock send_batch 方法返回成功统计
            mock_kafka_producer.send_batch.return_value = {
                "]success[": len(test_data),""""
                "]failed[": 0}""""
            # 执行测试
            success = await collector.send_to_stream(test_data)
            # 验证序列化成功
    assert success is True
            mock_kafka_producer.send_batch.assert_called_once()
    @pytest.mark.asyncio
    async def test_concurrent_streaming_operations(
        self, mock_kafka_producer, sample_data
    ):
        "]""测试并发流式操作"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            mock_producer_class.return_value = mock_kafka_producer
            collector = StreamingDataCollector(
            data_source="]test_source[", enable_streaming=True[""""
            )
            # 确保Kafka生产者初始化成功
    assert collector.enable_streaming is True
    assert collector.kafka_producer is not None
        # Mock send_batch 方法返回成功统计
        mock_kafka_producer.send_batch.return_value = {"]]success[": 1, "]failed[": 0}""""
        # 创建多个并发任务
        tasks = []
            for i in range(5):
            task = collector.send_to_stream(
            [{"]id[": i, "]batch[": i, "]data[": f["]concurrent_data_{i}"]}]""""
            )
            tasks.append(task)
            # 并发执行
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # 验证所有操作都成功
            for result in results:
    assert not isinstance(result, Exception)
    assert result is True
    @pytest.mark.asyncio
    async def test_collect_with_retry_on_stream_failure(
        self, mock_kafka_producer, sample_data
    ):
        """测试流式发送失败时的重试机制"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            # 第一次失败，第二次成功
            mock_kafka_producer.send.side_effect = [
            Exception("]Temporary failure["),": AsyncMock(),  # 成功["""
            ]
            mock_producer_class.return_value = mock_kafka_producer
            collector = StreamingDataCollector(
            data_source="]]test_source[", enable_streaming=True, max_retries=2[""""
            )
            # Mock基础采集方法 - 需要mock父类的collect_fixtures方法
            with patch(:
                "]]src.data.collectors.base_collector.DataCollector.collect_fixtures[",": new_callable=AsyncMock) as mock_collect:": mock_collect.return_value = CollectionResult(": data_source="]test_source[",": collection_type="]fixtures[",": records_collected=len(sample_data),": success_count=len(sample_data),": error_count=0,"
                    status="]success[",": collected_data=sample_data)"""
                # 执行测试
                result = await collector.collect_fixtures_with_streaming()
                # 验证数据采集成功（即使流式发送有问题）
    assert result.status =="]success[" assert result.records_collected ==len(sample_data)""""
    def test_stream_config_validation(self):
        "]""测试流配置验证"""
        # 测试有效配置
        valid_config = StreamConfig()
        collector = StreamingDataCollector(
        data_source="test_source[", enable_streaming=True, stream_config=valid_config[""""
        )
    assert collector.stream_config ==valid_config
    @pytest.mark.asyncio
    async def test_cleanup_resources(self, mock_kafka_producer):
        "]]""测试资源清理"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            mock_producer_class.return_value = mock_kafka_producer
            collector = StreamingDataCollector(
            data_source="]test_source[", enable_streaming=True[""""
            )
            # 执行一些操作
            await collector.send_to_stream([{"]]id[": 1}])""""
            # 测试清理方法（如果存在）
            if hasattr(collector, "]close[") or hasattr(collector, "]cleanup["):": cleanup_method = getattr(collector, "]close[", None) or getattr(": collector, "]cleanup[", None[""""
            )
                if asyncio.iscoroutinefunction(cleanup_method):
                await cleanup_method()
                else:
                cleanup_method()
            # 验证Kafka生产者关闭
            mock_kafka_producer.close.assert_called()
    @pytest.mark.asyncio
    async def test_error_recovery_and_logging(self, mock_kafka_producer, sample_data):
        "]]""测试错误恢复和日志记录"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class, patch(
            "]src.data.collectors.streaming_collector.logging["""""
        ):
            # Mock连续失败
            mock_kafka_producer.send.side_effect = Exception("]Persistent failure[")": mock_producer_class.return_value = mock_kafka_producer[": collector = StreamingDataCollector(": data_source="]]test_source[", enable_streaming=True, max_retries=1[""""
            )
            # Mock父类的collect_fixtures方法
            with patch.object(:
                collector.__class__.__bases__[0], "]]collect_fixtures["""""
            ) as mock_collect:
                mock_collect.return_value = CollectionResult(
                data_source="]test_source[",": collection_type="]fixtures[",": records_collected=len(sample_data),": success_count=len(sample_data),": error_count=0,"
                    status="]success[",": collected_data=sample_data)"""
                # 执行测试
                result = await collector.collect_fixtures_with_streaming()
                # 验证错误恢复 - 数据采集应该继续
    assert result.status =="]success[" assert result.records_collected ==len(sample_data)""""
            # 可以验证错误日志（如果实现了日志记录）
    def test_inheritance_and_interface(self):
        "]""测试继承关系和接口"""
        from src.data.collectors.base_collector import DataCollector
        collector = StreamingDataCollector()
        # 验证继承关系
    assert isinstance(collector, DataCollector)
        # 验证必要方法存在
    assert hasattr(
        collector, "collect_fixtures_with_streaming["""""
        )  # 修正：检查具体的方法
    assert hasattr(collector, "]send_to_stream[")" assert callable(collector.collect_fixtures_with_streaming)"""
    assert callable(collector.send_to_stream)
    @pytest.mark.asyncio
    async def test_metadata_enrichment(self, mock_kafka_producer):
        "]""测试元数据丰富化"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class:
            mock_producer_class.return_value = mock_kafka_producer
            collector = StreamingDataCollector(
            data_source="]enriched_source[", enable_streaming=True[""""
            )
            basic_data = [{"]]id[": 1, "]value[": "]test["}]""""
            # 执行测试
            await collector.send_to_stream(basic_data)
            # 验证发送的数据可能包含元数据
            if mock_kafka_producer.send.called = call_args mock_kafka_producer.send.call_args_list[0]
            # 检查是否添加了元数据字段
            sent_data = call_args[1].get("]value[") or call_args[0][1]"]"""
                # 元数据可能包括时间戳、数据源等信息
    assert sent_data is not None
        from src.data.collectors.base_collector import DataCollector