"""
Auto-generated tests for src.data.collectors.streaming_collector module
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any, Optional

from src.data.collectors.streaming_collector import StreamingDataCollector
from src.data.collectors.base_collector import CollectionResult
from src.streaming import FootballKafkaProducer, StreamConfig


class TestStreamingDataCollector:
    """测试流式数据采集器"""

    def test_streaming_data_collector_initialization_with_streaming(self):
        """测试启用流式处理的流式采集器初始化"""
        stream_config = StreamConfig()
        collector = StreamingDataCollector(
            data_source="test_source",
            max_retries=3,
            retry_delay=5,
            timeout=30,
            enable_streaming=True,
            stream_config=stream_config
        )

        assert collector.data_source == "test_source"
        assert collector.max_retries == 3
        assert collector.retry_delay == 5
        assert collector.timeout == 30
        assert collector.enable_streaming is True
        assert collector.stream_config == stream_config
        assert collector.kafka_producer is not None

    def test_streaming_data_collector_initialization_without_streaming(self):
        """测试禁用流式处理的流式采集器初始化"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=False
        )

        assert collector.enable_streaming is False
        assert collector.kafka_producer is None

    def test_streaming_data_collector_initialization_with_default_config(self):
        """测试使用默认配置的流式采集器初始化"""
        collector = StreamingDataCollector(
            data_source="test_source"
        )

        assert collector.data_source == "test_source"
        assert collector.max_retries == 3  # 默认值
        assert collector.retry_delay == 5  # 默认值
        assert collector.timeout == 30  # 默认值
        assert collector.enable_streaming is True  # 默认值
        assert collector.stream_config is not None
        assert collector.kafka_producer is not None

    def test_initialize_kafka_producer_success(self):
        """测试Kafka生产者初始化成功"""
        stream_config = StreamConfig()
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=False,
            stream_config=stream_config
        )

        with patch('src.data.collectors.streaming_collector.FootballKafkaProducer') as mock_producer_class:
            mock_producer = MagicMock()
            mock_producer_class.return_value = mock_producer

            collector._initialize_kafka_producer()

            assert collector.kafka_producer == mock_producer
            mock_producer_class.assert_called_once_with(stream_config)

    def test_initialize_kafka_producer_failure(self):
        """测试Kafka生产者初始化失败"""
        stream_config = StreamConfig()
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=False,
            stream_config=stream_config
        )

        with patch('src.data.collectors.streaming_collector.FootballKafkaProducer') as mock_producer_class:
            mock_producer_class.side_effect = Exception("Kafka connection failed")

            collector._initialize_kafka_producer()

            assert collector.kafka_producer is None

    @pytest.mark.asyncio
    async def test_send_to_stream_disabled(self):
        """测试禁用流式处理时发送到流"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=False
        )

        data = [{"test": "data"}]
        result = await collector._send_to_stream(data, "test_stream")

        assert result == {"success": 0, "failed": 0}

    @pytest.mark.asyncio
    async def test_send_to_stream_no_producer(self):
        """测试无Kafka生产者时发送到流"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )
        collector.kafka_producer = None  # 模拟生产者初始化失败

        data = [{"test": "data"}]
        result = await collector._send_to_stream(data, "test_stream")

        assert result == {"success": 0, "failed": 0}

    @pytest.mark.asyncio
    async def test_send_to_stream_success(self):
        """测试成功发送到流"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )
        mock_producer = AsyncMock()
        mock_producer.send_batch.return_value = {"success": 2, "failed": 0}
        collector.kafka_producer = mock_producer

        data = [{"test": "data1"}, {"test": "data2"}]
        result = await collector._send_to_stream(data, "test_stream")

        assert result["success"] == 2
        assert result["failed"] == 0
        mock_producer.send_batch.assert_called_once_with(data, "test_stream")

    @pytest.mark.asyncio
    async def test_send_to_stream_with_exception(self):
        """测试发送到流异常处理"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )
        mock_producer = AsyncMock()
        mock_producer.send_batch.side_effect = Exception("Kafka error")
        collector.kafka_producer = mock_producer

        data = [{"test": "data1"}, {"test": "data2"}]
        result = await collector._send_to_stream(data, "test_stream")

        assert result["success"] == 0
        assert result["failed"] == 2

    @pytest.mark.asyncio
    async def test_send_to_stream_public_interface_empty_data(self):
        """测试公共接口发送空数据"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )

        result = await collector.send_to_stream([])
        assert result is True

    @pytest.mark.asyncio
    async def test_send_to_stream_public_interface_disabled_streaming(self):
        """测试公共接口禁用流式处理"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=False
        )

        data = [{"test": "data"}]
        result = await collector.send_to_stream(data)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_to_stream_public_interface_match_data(self):
        """测试发送比赛数据流类型推断"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )
        mock_producer = AsyncMock()
        mock_producer.send_batch.return_value = {"success": 1, "failed": 0}
        collector.kafka_producer = mock_producer

        # 比赛数据
        data = [{"match_id": 1001, "home_team": "Team A", "away_team": "Team B"}]
        result = await collector.send_to_stream(data)

        assert result is True
        mock_producer.send_batch.assert_called_once_with(data, "match")

    @pytest.mark.asyncio
    async def test_send_to_stream_public_interface_odds_data(self):
        """测试发送赔率数据流类型推断"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )
        mock_producer = AsyncMock()
        mock_producer.send_batch.return_value = {"success": 1, "failed": 0}
        collector.kafka_producer = mock_producer

        # 赔率数据
        data = [{"match_id": 1001, "odds": 1.85, "bookmaker": "Bet365"}]
        result = await collector.send_to_stream(data)

        assert result is True
        mock_producer.send_batch.assert_called_once_with(data, "odds")

    @pytest.mark.asyncio
    async def test_send_to_stream_public_interface_scores_data(self):
        """测试发送比分数据流类型推断"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )
        mock_producer = AsyncMock()
        mock_producer.send_batch.return_value = {"success": 1, "failed": 0}
        collector.kafka_producer = mock_producer

        # 比分数据
        data = [{"match_id": 1001, "score": "2-1", "minute": 75, "live": True}]
        result = await collector.send_to_stream(data)

        assert result is True
        mock_producer.send_batch.assert_called_once_with(data, "scores")

    @pytest.mark.asyncio
    async def test_send_to_stream_public_interface_default_data(self):
        """测试发送默认数据流类型"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )
        mock_producer = AsyncMock()
        mock_producer.send_batch.return_value = {"success": 1, "failed": 0}
        collector.kafka_producer = mock_producer

        # 默认数据
        data = [{"unknown_field": "value"}]
        result = await collector.send_to_stream(data)

        assert result is True
        mock_producer.send_batch.assert_called_once_with(data, "data")

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_streaming_success(self):
        """测试成功采集赛程并发送到流"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )

        # 模拟基础采集结果
        base_result = CollectionResult(
            status="success",
            records_collected=2,
            collected_data=[{"match_id": 1001}, {"match_id": 1002}],
            error_message=None
        )

        with patch.object(collector, 'collect_fixtures', return_value=base_result) as mock_collect:
            with patch.object(collector, '_send_to_stream') as mock_send:
                mock_send.return_value = {"success": 2, "failed": 0}

                result = await collector.collect_fixtures_with_streaming()

                assert result.status == "success"
                assert result.records_collected == 2
                assert result.collected_data == [{"match_id": 1001}, {"match_id": 1002}]
                assert "流处理 - 成功: 2, 失败: 0" in result.error_message

                mock_collect.assert_called_once()
                mock_send.assert_called_once_with([{"match_id": 1001}, {"match_id": 1002}], "match")

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_streaming_failure(self):
        """测试采集赛程失败"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )

        base_result = CollectionResult(
            status="failed",
            records_collected=0,
            collected_data=None,
            error_message="API request failed"
        )

        with patch.object(collector, 'collect_fixtures', return_value=base_result) as mock_collect:
            result = await collector.collect_fixtures_with_streaming()

            assert result.status == "failed"
            assert result.error_message == "API request failed"
            mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_odds_with_streaming_success(self):
        """测试成功采集赔率并发送到流"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )

        base_result = CollectionResult(
            status="success",
            records_collected=3,
            collected_data=[{"match_id": 1001, "odds": 1.85}],
            error_message=None
        )

        with patch.object(collector, 'collect_odds', return_value=base_result) as mock_collect:
            with patch.object(collector, '_send_to_stream') as mock_send:
                mock_send.return_value = {"success": 1, "failed": 0}

                result = await collector.collect_odds_with_streaming()

                assert result.status == "success"
                assert result.records_collected == 3
                assert "流处理 - 成功: 1, 失败: 0" in result.error_message

                mock_collect.assert_called_once()
                mock_send.assert_called_once_with([{"match_id": 1001, "odds": 1.85}], "odds")

    @pytest.mark.asyncio
    async def test_collect_live_scores_with_streaming_success(self):
        """测试成功采集实时比分并发送到流"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )

        base_result = CollectionResult(
            status="success",
            records_collected=1,
            collected_data=[{"match_id": 1001, "score": "1-0"}],
            error_message=None
        )

        with patch.object(collector, 'collect_live_scores', return_value=base_result) as mock_collect:
            with patch.object(collector, '_send_to_stream') as mock_send:
                mock_send.return_value = {"success": 1, "failed": 0}

                result = await collector.collect_live_scores_with_streaming()

                assert result.status == "success"
                assert result.records_collected == 1
                assert "流处理 - 成功: 1, 失败: 0" in result.error_message

                mock_collect.assert_called_once()
                mock_send.assert_called_once_with([{"match_id": 1001, "score": "1-0"}], "scores")

    @pytest.mark.asyncio
    async def test_batch_collect_and_stream_basic(self):
        """测试批量采集和流处理"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )

        # 模拟采集配置
        collection_configs = [
            {"type": "fixtures", "kwargs": {"league": "Premier League"}},
            {"type": "odds", "kwargs": {"matches": [1001, 1002]}},
            {"type": "scores", "kwargs": {"live": True}}
        ]

        # 模拟采集结果
        fixtures_result = CollectionResult(
            status="success",
            records_collected=2,
            collected_data=[{"match_id": 1001}],
            error_message="流处理 - 成功: 1, 失败: 0"
        )

        odds_result = CollectionResult(
            status="success",
            records_collected=3,
            collected_data=[{"match_id": 1001, "odds": 1.85}],
            error_message="流处理 - 成功: 1, 失败: 0"
        )

        scores_result = CollectionResult(
            status="success",
            records_collected=1,
            collected_data=[{"match_id": 1001, "score": "1-0"}],
            error_message="流处理 - 成功: 1, 失败: 0"
        )

        with patch.object(collector, 'collect_fixtures_with_streaming') as mock_fixtures:
            with patch.object(collector, 'collect_odds_with_streaming') as mock_odds:
                with patch.object(collector, 'collect_live_scores_with_streaming') as mock_scores:
                    mock_fixtures.return_value = fixtures_result
                    mock_odds.return_value = odds_result
                    mock_scores.return_value = scores_result

                    result = await collector.batch_collect_and_stream(collection_configs)

                    assert result["total_collections"] == 3
                    assert result["successful_collections"] == 3
                    assert result["failed_collections"] == 0
                    assert result["total_stream_success"] == 3
                    assert result["total_stream_failed"] == 0
                    assert len(result["collection_results"]) == 3

    @pytest.mark.asyncio
    async def test_batch_collect_and_stream_with_failures(self):
        """测试批量采集和流处理包含失败"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )

        collection_configs = [
            {"type": "fixtures", "kwargs": {}},
            {"type": "odds", "kwargs": {}},
            {"type": "unknown", "kwargs": {}},  # 未知类型
            {"type": "scores", "kwargs": {}}
        ]

        success_result = CollectionResult(
            status="success",
            records_collected=1,
            collected_data=[{"test": "data"}],
            error_message="流处理 - 成功: 1, 失败: 0"
        )

        failed_result = CollectionResult(
            status="failed",
            records_collected=0,
            collected_data=None,
            error_message="Collection failed"
        )

        with patch.object(collector, 'collect_fixtures_with_streaming') as mock_fixtures:
            with patch.object(collector, 'collect_odds_with_streaming') as mock_odds:
                with patch.object(collector, 'collect_live_scores_with_streaming') as mock_scores:
                    mock_fixtures.return_value = success_result
                    mock_odds.return_value = failed_result
                    mock_scores.return_value = success_result

                    result = await collector.batch_collect_and_stream(collection_configs)

                    assert result["total_collections"] == 3  # 未知类型被跳过
                    assert result["successful_collections"] == 2
                    assert result["failed_collections"] == 1
                    assert result["total_stream_success"] == 2
                    assert result["total_stream_failed"] == 0

    @pytest.mark.asyncio
    async def test_batch_collect_and_stream_with_exceptions(self):
        """测试批量采集和流处理异常处理"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )

        collection_configs = [
            {"type": "fixtures", "kwargs": {}},
            {"type": "odds", "kwargs": {}}
        ]

        with patch.object(collector, 'collect_fixtures_with_streaming') as mock_fixtures:
            with patch.object(collector, 'collect_odds_with_streaming') as mock_odds:
                mock_fixtures.side_effect = Exception("Fixtures failed")
                mock_odds.return_value = CollectionResult(
                    status="success",
                    records_collected=1,
                    collected_data=[{"test": "data"}],
                    error_message="流处理 - 成功: 1, 失败: 0"
                )

                result = await collector.batch_collect_and_stream(collection_configs)

                assert result["total_collections"] == 2
                assert result["successful_collections"] == 1
                assert result["failed_collections"] == 1
                assert len(result["collection_results"]) == 2

    def test_toggle_streaming_enable(self):
        """测试启用流式处理"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=False
        )

        with patch.object(collector, '_initialize_kafka_producer') as mock_init:
            mock_init.return_value = None
            collector.kafka_producer = MagicMock()  # 模拟Kafka生产者已存在

            collector.toggle_streaming(True)

            assert collector.enable_streaming is True
            mock_init.assert_called_once()

    def test_toggle_streaming_disable(self):
        """测试禁用流式处理"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )
        collector.kafka_producer = MagicMock()

        collector.toggle_streaming(False)

        assert collector.enable_streaming is False

    def test_get_streaming_status_enabled(self):
        """测试获取启用状态的流式处理状态"""
        stream_config = StreamConfig()
        stream_config.kafka_config.bootstrap_servers = "localhost:9092"
        stream_config.topics = {"match": "test_topic"}

        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True,
            stream_config=stream_config
        )
        collector.kafka_producer = MagicMock()

        status = collector.get_streaming_status()

        assert status["streaming_enabled"] is True
        assert status["kafka_producer_initialized"] is True
        assert status["stream_config"]["bootstrap_servers"] == "localhost:9092"
        assert "match" in status["stream_config"]["topics"]

    def test_get_streaming_status_disabled(self):
        """测试获取禁用状态的流式处理状态"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=False
        )

        status = collector.get_streaming_status()

        assert status["streaming_enabled"] is False
        assert status["kafka_producer_initialized"] is False

    def test_close_with_producer(self):
        """测试关闭采集器（有Kafka生产者）"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )
        mock_producer = MagicMock()
        collector.kafka_producer = mock_producer

        collector.close()

        mock_producer.close.assert_called_once()
        assert collector.kafka_producer is None

    def test_close_without_producer(self):
        """测试关闭采集器（无Kafka生产者）"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=False
        )

        # 应该不抛出异常
        collector.close()

    def test_del_destructor(self):
        """测试析构函数"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )
        mock_producer = MagicMock()
        collector.kafka_producer = mock_producer

        # 调用析构函数
        collector.__del__()

        mock_producer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """测试异步上下文管理器"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=True
        )
        mock_producer = MagicMock()
        collector.kafka_producer = mock_producer

        async with collector as c:
            assert c == collector

        # 验证资源清理
        mock_producer.close.assert_called_once()

    def test_abstract_methods_raise_not_implemented(self):
        """测试抽象方法抛出NotImplementedError"""
        collector = StreamingDataCollector(
            data_source="test_source",
            enable_streaming=False
        )

        with pytest.raises(NotImplementedError):
            collector.collect_fixtures()

        with pytest.raises(NotImplementedError):
            collector.collect_odds()

        with pytest.raises(NotImplementedError):
            collector.collect_live_scores()


@pytest.fixture
def sample_stream_config():
    """示例流配置fixture"""
    config = StreamConfig()
    return config


@pytest.fixture
def sample_collection_result():
    """示例采集结果fixture"""
    return CollectionResult(
        status="success",
        records_collected=2,
        collected_data=[{"match_id": 1001}, {"match_id": 1002}],
        error_message=None
    )


@pytest.fixture
def sample_streaming_collector():
    """示例流式采集器fixture"""
    collector = StreamingDataCollector(
        data_source="test_source",
        enable_streaming=True
    )
    # 模拟Kafka生产者
    collector.kafka_producer = AsyncMock()
    collector.kafka_producer.send_batch.return_value = {"success": 1, "failed": 0}
    return collector


@pytest.fixture
def sample_collection_configs():
    """示例采集配置fixture"""
    return [
        {"type": "fixtures", "kwargs": {"league": "Premier League"}},
        {"type": "odds", "kwargs": {"matches": [1001, 1002]}},
        {"type": "scores", "kwargs": {"live": True}}
    ]


@pytest.mark.parametrize("stream_type,expected_type,data_sample", [
    ("match", "match", [{"match_id": 1001, "home_team": "Team A"}]),
    ("odds", "odds", [{"match_id": 1001, "odds": 1.85}]),
    ("scores", "scores", [{"match_id": 1001, "score": "1-0", "minute": 75}]),
    ("data", "data", [{"unknown_field": "value"}]),
])
@pytest.mark.asyncio
async def test_send_to_stream_type_detection(stream_type, expected_type, data_sample):
    """参数化测试流类型检测"""
    collector = StreamingDataCollector(
        data_source="test_source",
        enable_streaming=True
    )
    mock_producer = AsyncMock()
    mock_producer.send_batch.return_value = {"success": 1, "failed": 0}
    collector.kafka_producer = mock_producer

    result = await collector.send_to_stream(data_sample)

    assert result is True
    mock_producer.send_batch.assert_called_once_with(data_sample, expected_type)