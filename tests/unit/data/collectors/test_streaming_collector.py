"""
测试流式数据采集器

测试覆盖：
1. StreamingDataCollector 初始化和配置
2. Kafka生产者集成
3. 流式数据发送功能
4. 批量采集和流处理
5. 异常处理和错误恢复
6. 上下文管理器功能
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.data.collectors.base_collector import CollectionResult
from src.data.collectors.streaming_collector import StreamingDataCollector


class TestStreamingDataCollector:
    """测试流式数据采集器"""

    def setup_method(self):
        """设置测试"""
        # 模拟StreamConfig和FootballKafkaProducer
        with patch(
            "src.data.collectors.streaming_collector.StreamConfig"
        ) as mock_config:
            with patch(
                "src.data.collectors.streaming_collector.FootballKafkaProducer"
            ) as mock_producer:
                mock_config.return_value = Mock()
                mock_producer.return_value = Mock()
                self.collector = StreamingDataCollector(
                    data_source="test_source", enable_streaming=True
                )

    def test_init_with_streaming_enabled(self):
        """测试启用流式处理的初始化"""
        with patch(
            "src.data.collectors.streaming_collector.StreamConfig"
        ) as mock_config:
            with patch(
                "src.data.collectors.streaming_collector.FootballKafkaProducer"
            ) as mock_producer:
                mock_config.return_value = Mock()
                mock_producer.return_value = Mock()

                collector = StreamingDataCollector(
                    data_source="test_source",
                    max_retries=5,
                    retry_delay=10,
                    timeout=60,
                    enable_streaming=True,
                )

    assert collector.data_source == "test_source"
    assert collector.max_retries == 5
    assert collector.retry_delay == 10
    assert collector.timeout == 60
    assert collector.enable_streaming is True
    assert collector.kafka_producer is not None

    def test_init_with_streaming_disabled(self):
        """测试禁用流式处理的初始化"""
        collector = StreamingDataCollector(enable_streaming=False)

    assert collector.enable_streaming is False
    assert collector.kafka_producer is None

    def test_init_with_custom_stream_config(self):
        """测试自定义流配置初始化"""
        with patch(
            "src.data.collectors.streaming_collector.FootballKafkaProducer"
        ) as mock_producer:
            mock_config = Mock()
            mock_producer.return_value = Mock()

            collector = StreamingDataCollector(
                enable_streaming=True, stream_config=mock_config
            )

    assert collector.stream_config == mock_config

    @patch("src.data.collectors.streaming_collector.FootballKafkaProducer")
    def test_initialize_kafka_producer_success(self, mock_producer):
        """测试Kafka生产者初始化成功"""
        mock_instance = Mock()
        mock_producer.return_value = mock_instance

        collector = StreamingDataCollector(enable_streaming=False)
        collector._initialize_kafka_producer()

    assert collector.kafka_producer == mock_instance

    @patch("src.data.collectors.streaming_collector.FootballKafkaProducer")
    def test_initialize_kafka_producer_failure(self, mock_producer):
        """测试Kafka生产者初始化失败"""
        mock_producer.side_effect = Exception("连接失败")

        collector = StreamingDataCollector(enable_streaming=False)
        collector._initialize_kafka_producer()

    assert collector.kafka_producer is None
    assert collector.enable_streaming is False

    @pytest.mark.asyncio
    async def test_send_to_stream_success(self):
        """测试发送数据到流成功"""
        mock_producer = AsyncMock()
        mock_producer.send_batch.return_value = {"success": 5, "failed": 0}

        self.collector.kafka_producer = mock_producer

        data_list = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]
        result = await self.collector._send_to_stream(data_list, "test_stream")

    assert result["success"] == 5
    assert result["failed"] == 0
        mock_producer.send_batch.assert_called_once_with(data_list, "test_stream")

    @pytest.mark.asyncio
    async def test_send_to_stream_failure(self):
        """测试发送数据到流失败"""
        mock_producer = AsyncMock()
        mock_producer.send_batch.side_effect = Exception("发送失败")

        self.collector.kafka_producer = mock_producer

        data_list = [{"id": 1}, {"id": 2}]
        result = await self.collector._send_to_stream(data_list, "test_stream")

    assert result["success"] == 0
    assert result["failed"] == 2

    @pytest.mark.asyncio
    async def test_send_to_stream_disabled(self):
        """测试流式处理禁用时发送数据"""
        self.collector.enable_streaming = False

        data_list = [{"id": 1}]
        result = await self.collector._send_to_stream(data_list, "test_stream")

    assert result["success"] == 0
    assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_send_to_stream_public_interface_empty_data(self):
        """测试公共接口发送空数据"""
        result = await self.collector.send_to_stream([])
    assert result is True

    @pytest.mark.asyncio
    async def test_send_to_stream_public_interface_match_data(self):
        """测试公共接口发送比赛数据"""
        mock_producer = AsyncMock()
        mock_producer.send_batch.return_value = {"success": 1, "failed": 0}
        self.collector.kafka_producer = mock_producer

        data = [{"match_id": 123, "home_team": "Team A", "away_team": "Team B"}]
        result = await self.collector.send_to_stream(data)

    assert result is True
        mock_producer.send_batch.assert_called_once_with(data, "match")

    @pytest.mark.asyncio
    async def test_send_to_stream_public_interface_odds_data(self):
        """测试公共接口发送赔率数据"""
        mock_producer = AsyncMock()
        mock_producer.send_batch.return_value = {"success": 1, "failed": 0}
        self.collector.kafka_producer = mock_producer

        data = [{"odds": 1.5, "bookmaker": "Bet365"}]
        result = await self.collector.send_to_stream(data)

    assert result is True
        mock_producer.send_batch.assert_called_once_with(data, "odds")

    @pytest.mark.asyncio
    async def test_send_to_stream_public_interface_scores_data(self):
        """测试公共接口发送比分数据"""
        mock_producer = AsyncMock()
        mock_producer.send_batch.return_value = {"success": 1, "failed": 0}
        self.collector.kafka_producer = mock_producer

        data = [{"score": "2-1", "minute": 45, "live": True}]
        result = await self.collector.send_to_stream(data)

    assert result is True
        mock_producer.send_batch.assert_called_once_with(data, "scores")

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_streaming_success(self):
        """测试带流处理的赛程采集成功"""
        # 模拟父类方法
        mock_result = CollectionResult(
            data_source="test_source",
            collection_type="fixtures",
            status="success",
            success_count=5,
            error_count=0,
            records_collected=5,
            collected_data=[{"fixture": 1}, {"fixture": 2}],
            error_message=None,
        )

        with patch.object(
            self.collector.__class__.__bases__[0],
            "collect_fixtures",
            return_value=mock_result,
        ):
            mock_producer = AsyncMock()
            mock_producer.send_batch.return_value = {"success": 2, "failed": 0}
            self.collector.kafka_producer = mock_producer

            result = await self.collector.collect_fixtures_with_streaming()

    assert result.status == "success"
    assert "流处理" in result.error_message

    @pytest.mark.asyncio
    async def test_collect_odds_with_streaming_success(self):
        """测试带流处理的赔率采集成功"""
        mock_result = CollectionResult(
            data_source="test_source",
            collection_type="odds",
            status="success",
            success_count=3,
            error_count=0,
            records_collected=3,
            collected_data=[{"odds": 1}, {"odds": 2}],
            error_message=None,
        )

        with patch.object(self.collector, "collect_odds", return_value=mock_result):
            mock_producer = AsyncMock()
            mock_producer.send_batch.return_value = {"success": 2, "failed": 0}
            self.collector.kafka_producer = mock_producer

            result = await self.collector.collect_odds_with_streaming()

    assert result.status == "success"
    assert "流处理" in result.error_message

    @pytest.mark.asyncio
    async def test_collect_live_scores_with_streaming_success(self):
        """测试带流处理的实时比分采集成功"""
        mock_result = CollectionResult(
            data_source="test_source",
            collection_type="scores",
            status="success",
            success_count=4,
            error_count=0,
            records_collected=4,
            collected_data=[{"score": 1}, {"score": 2}],
            error_message=None,
        )

        with patch.object(
            self.collector, "collect_live_scores", return_value=mock_result
        ):
            mock_producer = AsyncMock()
            mock_producer.send_batch.return_value = {"success": 2, "failed": 0}
            self.collector.kafka_producer = mock_producer

            result = await self.collector.collect_live_scores_with_streaming()

    assert result.status == "success"
    assert "流处理" in result.error_message

    @pytest.mark.asyncio
    async def test_batch_collect_and_stream_success(self):
        """测试批量采集和流处理成功"""
        mock_result = CollectionResult(
            data_source="test_source",
            collection_type="batch",
            status="success",
            success_count=2,
            error_count=0,
            records_collected=2,
            collected_data=[{"data": 1}],
            error_message="流处理 - 成功: 1, 失败: 0",
        )

        with patch.object(
            self.collector, "collect_fixtures_with_streaming", return_value=mock_result
        ):
            with patch.object(
                self.collector, "collect_odds_with_streaming", return_value=mock_result
            ):
                configs = [
                    {"type": "fixtures", "kwargs": {}},
                    {"type": "odds", "kwargs": {}},
                ]

                result = await self.collector.batch_collect_and_stream(configs)

    assert result["total_collections"] == 2
    assert result["successful_collections"] == 2
    assert result["failed_collections"] == 0
    assert result["total_stream_success"] == 2
    assert result["total_stream_failed"] == 0

    @pytest.mark.asyncio
    async def test_batch_collect_with_exceptions(self):
        """测试批量采集中的异常处理"""
        mock_success_result = CollectionResult(
            data_source="test_source",
            collection_type="batch",
            status="success",
            success_count=1,
            error_count=0,
            records_collected=1,
            collected_data=[{"data": 1}],
            error_message="流处理 - 成功: 1, 失败: 0",
        )

        with patch.object(
            self.collector,
            "collect_fixtures_with_streaming",
            return_value=mock_success_result,
        ):
            with patch.object(
                self.collector,
                "collect_odds_with_streaming",
                side_effect=Exception("采集失败"),
            ):
                configs = [
                    {"type": "fixtures", "kwargs": {}},
                    {"type": "odds", "kwargs": {}},
                ]

                result = await self.collector.batch_collect_and_stream(configs)

    assert result["total_collections"] == 2
    assert result["successful_collections"] == 1
    assert result["failed_collections"] == 1

    @pytest.mark.asyncio
    async def test_batch_collect_unknown_type(self):
        """测试批量采集未知类型"""
        configs = [{"type": "unknown", "kwargs": {}}]

        result = await self.collector.batch_collect_and_stream(configs)

    assert result["total_collections"] == 1
    assert result["successful_collections"] == 0
    assert result["failed_collections"] == 0

    def test_toggle_streaming_enable(self):
        """测试启用流式处理"""
        self.collector.enable_streaming = False
        self.collector.kafka_producer = None

        with patch.object(self.collector, "_initialize_kafka_producer") as mock_init:
            # Mock the initialization to set kafka_producer
            def mock_initialize():
                self.collector.kafka_producer = Mock()

            mock_init.side_effect = mock_initialize

            self.collector.toggle_streaming(True)

            mock_init.assert_called_once()
    assert self.collector.enable_streaming is True

    def test_toggle_streaming_disable(self):
        """测试禁用流式处理"""
        self.collector.enable_streaming = True

        self.collector.toggle_streaming(False)

    assert self.collector.enable_streaming is False

    def test_get_streaming_status_enabled(self):
        """测试获取流式处理状态（启用）"""
        mock_config = Mock()
        mock_config.kafka_config.bootstrap_servers = ["localhost:9092"]
        mock_config.topics = {"match": "match_topic", "odds": "odds_topic"}

        self.collector.stream_config = mock_config

        status = self.collector.get_streaming_status()

    assert status["streaming_enabled"] is True
    assert status["kafka_producer_initialized"] is True
    assert status["stream_config"]["bootstrap_servers"] == ["localhost:9092"]
    assert "match" in status["stream_config"]["topics"]

    def test_get_streaming_status_disabled(self):
        """测试获取流式处理状态（禁用）"""
        collector = StreamingDataCollector(enable_streaming=False)

        status = collector.get_streaming_status()

    assert status["streaming_enabled"] is False
    assert status["kafka_producer_initialized"] is False

    def test_close(self):
        """测试关闭采集器"""
        mock_producer = Mock()
        self.collector.kafka_producer = mock_producer

        self.collector.close()

        mock_producer.close.assert_called_once()
    assert self.collector.kafka_producer is None

    def test_del(self):
        """测试析构函数"""
        mock_producer = Mock()
        self.collector.kafka_producer = mock_producer

        with patch.object(self.collector, "close") as mock_close:
            self.collector.__del__()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试异步上下文管理器"""
        async with self.collector as collector:
    assert collector == self.collector

    @pytest.mark.asyncio
    async def test_abstract_methods_not_implemented(self):
        """测试抽象方法未实现"""
        with pytest.raises(NotImplementedError):
            await self.collector.collect_fixtures()

        with pytest.raises(NotImplementedError):
            await self.collector.collect_odds()

        with pytest.raises(NotImplementedError):
            await self.collector.collect_live_scores()


class TestStreamingDataCollectorEdgeCases:
    """测试流式数据采集器边界情况"""

    def setup_method(self):
        """设置测试"""
        with patch("src.data.collectors.streaming_collector.StreamConfig"):
            with patch("src.data.collectors.streaming_collector.FootballKafkaProducer"):
                self.collector = StreamingDataCollector(enable_streaming=True)

    @pytest.mark.asyncio
    async def test_send_to_stream_no_producer(self):
        """测试没有生产者时发送数据"""
        self.collector.kafka_producer = None

        result = await self.collector.send_to_stream([{"data": 1}])

    assert result is True

    @pytest.mark.asyncio
    async def test_collect_with_streaming_disabled(self):
        """测试流式处理禁用时的采集"""
        self.collector.enable_streaming = False

        mock_result = CollectionResult(
            data_source="test_source",
            collection_type="odds",
            status="success",
            success_count=1,
            error_count=0,
            records_collected=1,
            collected_data=[{"data": 1}],
            error_message=None,
        )

        with patch.object(self.collector, "collect_odds", return_value=mock_result):
            result = await self.collector.collect_odds_with_streaming()

    assert result.status == "success"
            # 不应该有流处理信息
    assert result.error_message is None or "流处理" not in result.error_message

    @pytest.mark.asyncio
    async def test_collect_with_failed_collection(self):
        """测试采集失败时的处理"""
        mock_result = CollectionResult(
            data_source="test_source",
            collection_type="fixtures",
            status="failed",
            success_count=0,
            error_count=1,
            records_collected=0,
            collected_data=None,
            error_message="采集失败",
        )

        with patch.object(
            self.collector.__class__.__bases__[0],
            "collect_fixtures",
            return_value=mock_result,
        ):
            result = await self.collector.collect_fixtures_with_streaming()

    assert result.status == "failed"
            # 失败时不应该进行流处理
    assert "流处理" not in (result.error_message or "")
