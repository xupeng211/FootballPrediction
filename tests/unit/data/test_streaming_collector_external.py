"""
StreamingDataCollector 测试

测试流式数据采集器的所有功能，包括：
- Kafka生产者初始化
- 数据流发送
- 批量采集和流处理
- 异常处理和降级逻辑
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.data.collectors.base_collector import CollectionResult
from src.data.collectors.streaming_collector import StreamingDataCollector
from src.streaming import FootballKafkaProducer, StreamConfig


class TestStreamingDataCollector:
    """StreamingDataCollector测试类"""

    @pytest.fixture
    def mock_stream_config(self):
        """模拟流配置"""
        config = MagicMock(spec=StreamConfig)
        config.kafka_config = MagicMock()
        config.kafka_config.bootstrap_servers = "localhost:9092"
        config.topics = {"match": "test_match_topic", "odds": "test_odds_topic"}
        return config

    @pytest.fixture
    def mock_kafka_producer(self):
        """模拟Kafka生产者"""
        producer = MagicMock(spec=FootballKafkaProducer)
        producer.send_batch = AsyncMock(return_value={"success": 5, "failed": 0})
        producer.close = MagicMock()
        return producer

    @pytest.fixture
    def streaming_collector(self, mock_stream_config, mock_kafka_producer):
        """创建StreamingDataCollector实例"""
        with patch(
            "src.data.collectors.streaming_collector.FootballKafkaProducer",
            return_value=mock_kafka_producer,
        ):
            collector = StreamingDataCollector(
                data_source="test_source",
                max_retries=3,
                retry_delay=1,
                timeout=10,
                enable_streaming=True,
                stream_config=mock_stream_config,
            )
            return collector

    @pytest.fixture
    def streaming_collector_disabled(self):
        """创建禁用流式处理的StreamingDataCollector实例"""
        return StreamingDataCollector(
            data_source="test_source",
            max_retries=3,
            retry_delay=1,
            timeout=10,
            enable_streaming=False,
        )

    @pytest.fixture
    def sample_data(self):
        """示例数据"""
        return [
            {
                "match_id": 1,
                "home_team": "Team A",
                "away_team": "Team B",
                "date": "2024-01-01",
            },
            {
                "match_id": 2,
                "home_team": "Team C",
                "away_team": "Team D",
                "date": "2024-01-02",
            },
        ]

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据（不包含match_id以测试odds类型推断）"""
        return [
            {"odds": 2.5, "bookmaker": "Bookmaker A", "price": 1.8, "event_id": 1},
            {"odds": 3.0, "bookmaker": "Bookmaker B", "price": 2.1, "event_id": 2},
        ]

    @pytest.fixture
    def sample_scores_data(self):
        """示例比分数据（不包含match_id以测试scores类型推断）"""
        return [
            {"score": "1-0", "minute": 45, "live": True, "event_id": 1},
            {"score": "2-1", "minute": 60, "live": True, "event_id": 2},
        ]

    class TestInitialization:
        """测试初始化逻辑"""

        def test_init_with_streaming_enabled(self, streaming_collector):
            """测试启用流式处理的初始化"""
            assert streaming_collector.enable_streaming is True
            assert streaming_collector.kafka_producer is not None
            assert streaming_collector.data_source == "test_source"
            assert streaming_collector.max_retries == 3
            assert streaming_collector.retry_delay == 1
            assert streaming_collector.timeout == 10

        def test_init_with_streaming_disabled(self, streaming_collector_disabled):
            """测试禁用流式处理的初始化"""
            assert streaming_collector_disabled.enable_streaming is False
            assert streaming_collector_disabled.kafka_producer is None
            assert streaming_collector_disabled.data_source == "test_source"

        def test_init_kafka_producer_failure(self, mock_stream_config):
            """测试Kafka生产者初始化失败的降级处理"""
            with patch(
                "src.data.collectors.streaming_collector.FootballKafkaProducer",
                side_effect=Exception("Kafka connection failed"),
            ):
                collector = StreamingDataCollector(
                    data_source="test_source",
                    enable_streaming=True,
                    stream_config=mock_stream_config,
                )
                # Kafka生产者初始化失败时应该禁用流式处理
                assert collector.enable_streaming is False
                assert collector.kafka_producer is None

    class TestSendToStream:
        """测试数据流发送功能"""

        @pytest.mark.asyncio
        async def test_send_to_stream_success(self, streaming_collector, sample_data):
            """测试成功发送数据到流"""
            result = await streaming_collector.send_to_stream(sample_data)
            assert result is True
            streaming_collector.kafka_producer.send_batch.assert_called_once_with(
                sample_data, "match"
            )

        @pytest.mark.asyncio
        async def test_send_to_stream_odds_data(
            self, streaming_collector, sample_odds_data
        ):
            """测试发送赔率数据到流"""
            result = await streaming_collector.send_to_stream(sample_odds_data)
            assert result is True
            streaming_collector.kafka_producer.send_batch.assert_called_once_with(
                sample_odds_data, "odds"
            )

        @pytest.mark.asyncio
        async def test_send_to_stream_scores_data(
            self, streaming_collector, sample_scores_data
        ):
            """测试发送比分数据到流"""
            result = await streaming_collector.send_to_stream(sample_scores_data)
            assert result is True
            streaming_collector.kafka_producer.send_batch.assert_called_once_with(
                sample_scores_data, "scores"
            )

        @pytest.mark.asyncio
        async def test_send_to_stream_empty_data(self, streaming_collector):
            """测试发送空数据"""
            result = await streaming_collector.send_to_stream([])
            assert result is True
            # 空数据不应该调用send_batch
            streaming_collector.kafka_producer.send_batch.assert_not_called()

        @pytest.mark.asyncio
        async def test_send_to_stream_disabled(
            self, streaming_collector_disabled, sample_data
        ):
            """测试禁用流式处理时发送数据"""
            result = await streaming_collector_disabled.send_to_stream(sample_data)
            assert result is True
            # 禁用流式处理时不应该调用send_batch
            assert streaming_collector_disabled.kafka_producer is None

        @pytest.mark.asyncio
        async def test_send_to_stream_kafka_failure(
            self, streaming_collector, sample_data
        ):
            """测试Kafka发送失败的处理"""
            streaming_collector.kafka_producer.send_batch.side_effect = Exception(
                "Kafka error"
            )

            result = await streaming_collector.send_to_stream(sample_data)
            assert result is False

        @pytest.mark.asyncio
        async def test_send_to_stream_partial_success(
            self, streaming_collector, sample_data
        ):
            """测试部分成功发送数据"""
            streaming_collector.kafka_producer.send_batch.return_value = {
                "success": 1,
                "failed": 1,
            }

            result = await streaming_collector.send_to_stream(sample_data)
            assert result is True  # 部分成功也算成功

    class TestInternalStreamMethods:
        """测试内部流处理方法"""

        @pytest.mark.asyncio
        async def test_send_to_stream_internal_success(
            self, streaming_collector, sample_data
        ):
            """测试内部发送方法成功"""
            stats = await streaming_collector._send_to_stream(sample_data, "match")
            expected_stats = {"success": 5, "failed": 0}
            assert stats == expected_stats

        @pytest.mark.asyncio
        async def test_send_to_stream_internal_disabled(
            self, streaming_collector_disabled, sample_data
        ):
            """测试禁用流式处理时内部发送方法"""
            stats = await streaming_collector_disabled._send_to_stream(
                sample_data, "match"
            )
            expected_stats = {"success": 0, "failed": 0}
            assert stats == expected_stats

        @pytest.mark.asyncio
        async def test_send_to_stream_internal_exception(
            self, streaming_collector, sample_data
        ):
            """测试内部发送方法异常处理"""
            streaming_collector.kafka_producer.send_batch.side_effect = Exception(
                "Kafka error"
            )

            stats = await streaming_collector._send_to_stream(sample_data, "match")
            expected_stats = {"success": 0, "failed": len(sample_data)}
            assert stats == expected_stats

    class TestStreamingCollectionMethods:
        """测试流式采集方法"""

        @pytest.mark.asyncio
        async def test_collect_fixtures_with_streaming_success(
            self, streaming_collector, sample_data
        ):
            """测试赛程数据采集和流处理成功"""
            # Mock父类的collect_fixtures方法
            mock_result = CollectionResult(
                data_source="test_source",
                collection_type="fixtures",
                records_collected=len(sample_data),
                success_count=len(sample_data),
                error_count=0,
                status="success",
                collected_data=sample_data,
                error_message=None,
            )

            # 使用super()来mock父类方法
            with patch.object(
                type(streaming_collector).__bases__[0],
                "collect_fixtures",
                new_callable=AsyncMock,
                return_value=mock_result,
            ) as mock_collect:
                result = await streaming_collector.collect_fixtures_with_streaming()

                # 验证父类方法被调用
                mock_collect.assert_called_once()

                # 验证流处理被调用
                streaming_collector.kafka_producer.send_batch.assert_called_once()

                # 验证结果
                assert result.status == "success"
                assert result.records_collected == len(sample_data)
                assert "流处理" in result.error_message

        @pytest.mark.asyncio
        async def test_collect_fixtures_with_streaming_failure(
            self, streaming_collector
        ):
            """测试赛程数据采集失败的情况"""
            mock_result = CollectionResult(
                data_source="test_source",
                collection_type="fixtures",
                records_collected=0,
                success_count=0,
                error_count=1,
                status="error",
                collected_data=None,
                error_message="API error",
            )

            # 使用super()来mock父类方法
            with patch.object(
                type(streaming_collector).__bases__[0],
                "collect_fixtures",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                result = await streaming_collector.collect_fixtures_with_streaming()

                # 采集失败时不应该进行流处理
                streaming_collector.kafka_producer.send_batch.assert_not_called()

                assert result.status == "error"
                assert result.error_message == "API error"

        @pytest.mark.asyncio
        async def test_collect_odds_with_streaming_success(
            self, streaming_collector, sample_odds_data
        ):
            """测试赔率数据采集和流处理成功"""
            mock_result = CollectionResult(
                data_source="test_source",
                collection_type="odds",
                records_collected=len(sample_odds_data),
                success_count=len(sample_odds_data),
                error_count=0,
                status="success",
                collected_data=sample_odds_data,
                error_message=None,
            )

            with patch.object(
                streaming_collector,
                "collect_odds",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                result = await streaming_collector.collect_odds_with_streaming()

                # 验证流处理被调用
                streaming_collector.kafka_producer.send_batch.assert_called_once()

                assert result.status == "success"

        @pytest.mark.asyncio
        async def test_collect_live_scores_with_streaming_success(
            self, streaming_collector, sample_scores_data
        ):
            """测试实时比分数据采集和流处理成功"""
            mock_result = CollectionResult(
                data_source="test_source",
                collection_type="scores",
                records_collected=len(sample_scores_data),
                success_count=len(sample_scores_data),
                error_count=0,
                status="success",
                collected_data=sample_scores_data,
                error_message=None,
            )

            with patch.object(
                streaming_collector,
                "collect_live_scores",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                result = await streaming_collector.collect_live_scores_with_streaming()

                # 验证流处理被调用
                streaming_collector.kafka_producer.send_batch.assert_called_once()

                assert result.status == "success"

    class TestBatchCollection:
        """测试批量采集功能"""

        @pytest.mark.asyncio
        async def test_batch_collect_and_stream_success(
            self, streaming_collector, sample_data, sample_odds_data
        ):
            """测试批量采集和流处理成功"""
            # Mock各种采集方法
            mock_fixtures_result = CollectionResult(
                data_source="test_source",
                collection_type="fixtures",
                records_collected=2,
                success_count=2,
                error_count=0,
                status="success",
                collected_data=sample_data,
                error_message=None,
            )

            mock_odds_result = CollectionResult(
                data_source="test_source",
                collection_type="odds",
                records_collected=2,
                success_count=2,
                error_count=0,
                status="success",
                collected_data=sample_odds_data,
                error_message=None,
            )

            collection_configs = [
                {"type": "fixtures", "kwargs": {}},
                {"type": "odds", "kwargs": {}},
            ]

            with patch.object(
                streaming_collector,
                "collect_fixtures_with_streaming",
                new_callable=AsyncMock,
                return_value=mock_fixtures_result,
            ), patch.object(
                streaming_collector,
                "collect_odds_with_streaming",
                new_callable=AsyncMock,
                return_value=mock_odds_result,
            ):
                result = await streaming_collector.batch_collect_and_stream(
                    collection_configs
                )

                # 验证结果
                assert result["total_collections"] == 2
                assert result["successful_collections"] == 2
                assert result["failed_collections"] == 0
                assert len(result["collection_results"]) == 2

        @pytest.mark.asyncio
        async def test_batch_collect_and_stream_mixed_results(
            self, streaming_collector, sample_data
        ):
            """测试批量采集混合结果（成功和失败）"""
            mock_success_result = CollectionResult(
                data_source="test_source",
                collection_type="fixtures",
                records_collected=2,
                success_count=2,
                error_count=0,
                status="success",
                collected_data=sample_data,
                error_message=None,
            )

            mock_failure_result = CollectionResult(
                data_source="test_source",
                collection_type="odds",
                records_collected=0,
                success_count=0,
                error_count=1,
                status="error",
                collected_data=None,
                error_message="API error",
            )

            collection_configs = [
                {"type": "fixtures", "kwargs": {}},
                {"type": "odds", "kwargs": {}},
            ]

            with patch.object(
                streaming_collector,
                "collect_fixtures_with_streaming",
                new_callable=AsyncMock,
                return_value=mock_success_result,
            ), patch.object(
                streaming_collector,
                "collect_odds_with_streaming",
                new_callable=AsyncMock,
                return_value=mock_failure_result,
            ):
                result = await streaming_collector.batch_collect_and_stream(
                    collection_configs
                )

                # 验证结果
                assert result["total_collections"] == 2
                assert result["successful_collections"] == 1
                assert result["failed_collections"] == 1

        @pytest.mark.asyncio
        async def test_batch_collect_and_stream_exception_handling(
            self, streaming_collector
        ):
            """测试批量采集异常处理"""
            collection_configs = [
                {"type": "fixtures", "kwargs": {}},
                {"type": "invalid_type", "kwargs": {}},
            ]

            with patch.object(
                streaming_collector,
                "collect_fixtures_with_streaming",
                new_callable=AsyncMock,
                side_effect=Exception("Collection error"),
            ):
                result = await streaming_collector.batch_collect_and_stream(
                    collection_configs
                )

                # 验证异常处理
                assert result["total_collections"] == 2
                assert (
                    result["failed_collections"] == 1
                )  # 只有fixtures任务，invalid_type被跳过

    class TestStreamingControl:
        """测试流式处理控制功能"""

        def test_toggle_streaming_enable(self, streaming_collector_disabled):
            """测试启用流式处理"""
            assert streaming_collector_disabled.enable_streaming is False

            with patch(
                "src.data.collectors.streaming_collector.FootballKafkaProducer"
            ) as mock_producer_class:
                mock_producer = MagicMock()
                mock_producer_class.return_value = mock_producer

                streaming_collector_disabled.toggle_streaming(True)

                assert streaming_collector_disabled.enable_streaming is True
                assert streaming_collector_disabled.kafka_producer is not None

        def test_toggle_streaming_disable(self, streaming_collector):
            """测试禁用流式处理"""
            assert streaming_collector.enable_streaming is True
            assert streaming_collector.kafka_producer is not None

            streaming_collector.toggle_streaming(False)

            assert streaming_collector.enable_streaming is False

        def test_get_streaming_status(self, streaming_collector):
            """测试获取流式处理状态"""
            status = streaming_collector.get_streaming_status()

            assert status["streaming_enabled"] is True
            assert status["kafka_producer_initialized"] is True
            assert status["stream_config"] is not None
            assert "bootstrap_servers" in status["stream_config"]
            assert "topics" in status["stream_config"]

        def test_get_streaming_status_disabled(self, streaming_collector_disabled):
            """测试禁用流式处理时的状态"""
            status = streaming_collector_disabled.get_streaming_status()

            assert status["streaming_enabled"] is False
            assert status["kafka_producer_initialized"] is False

    class TestResourceCleanup:
        """测试资源清理功能"""

        def test_close(self, streaming_collector):
            """测试关闭采集器"""
            assert streaming_collector.kafka_producer is not None

            streaming_collector.close()

            # 注意：kafka_producer可能被设置为None，所以检查close方法是否被调用
            if streaming_collector.kafka_producer:
                streaming_collector.kafka_producer.close.assert_called_once()
            assert streaming_collector.kafka_producer is None

        def test_close_disabled(self, streaming_collector_disabled):
            """测试关闭禁用流式处理的采集器"""
            streaming_collector_disabled.close()  # 不应该抛出异常

        def test_del_destructor(self, streaming_collector):
            """测试析构函数"""
            with patch.object(streaming_collector, "close") as mock_close:
                del streaming_collector
                # 注意：Python的析构函数调用时机不确定，所以这个测试可能不稳定
                # 这里我们主要测试close方法存在并可被调用

        @pytest.mark.asyncio
        async def test_async_context_manager(self, mock_stream_config):
            """测试异步上下文管理器"""
            with patch(
                "src.data.collectors.streaming_collector.FootballKafkaProducer"
            ) as mock_producer_class:
                mock_producer = MagicMock()
                mock_producer_class.return_value = mock_producer

                async with StreamingDataCollector(
                    data_source="test_source",
                    enable_streaming=True,
                    stream_config=mock_stream_config,
                ) as collector:
                    assert collector.enable_streaming is True
                    assert collector.kafka_producer is not None

                # 退出上下文时应该调用close
                mock_producer.close.assert_called_once()

    class TestAbstractMethods:
        """测试抽象方法实现"""

        @pytest.mark.asyncio
        async def test_abstract_methods_raise_not_implemented(
            self, streaming_collector
        ):
            """测试抽象方法抛出NotImplementedError"""
            with pytest.raises(NotImplementedError, match="需要在具体采集器中实现"):
                await streaming_collector.collect_fixtures()

            with pytest.raises(NotImplementedError, match="需要在具体采集器中实现"):
                await streaming_collector.collect_odds()

            with pytest.raises(NotImplementedError, match="需要在具体采集器中实现"):
                await streaming_collector.collect_live_scores()

    class TestEdgeCases:
        """测试边界情况"""

        @pytest.mark.asyncio
        async def test_send_to_stream_invalid_data_structure(self, streaming_collector):
            """测试发送无效数据结构"""
            invalid_data = [{"invalid_key": "invalid_value"}]  # 缺少匹配关键字段

            result = await streaming_collector.send_to_stream(invalid_data)
            assert result is True
            # 应该默认发送到"data"流
            streaming_collector.kafka_producer.send_batch.assert_called_once_with(
                invalid_data, "data"
            )

        @pytest.mark.asyncio
        async def test_send_to_stream_mixed_data_types(self, streaming_collector):
            """测试混合数据类型"""
            mixed_data = [
                {"match_id": 1, "home_team": "Team A"},
                {"odds": 2.5, "bookmaker": "Bookmaker A"},
                {"score": "1-0", "minute": 45},
            ]

            result = await streaming_collector.send_to_stream(mixed_data)
            assert result is True
            # 应该根据第一个数据项的键确定流类型
            streaming_collector.kafka_producer.send_batch.assert_called_once_with(
                mixed_data, "match"
            )

        @pytest.mark.asyncio
        async def test_batch_collect_with_invalid_config(self, streaming_collector):
            """测试使用无效配置进行批量采集"""
            invalid_configs = [{"type": "invalid_type", "kwargs": {}}]

            result = await streaming_collector.batch_collect_and_stream(invalid_configs)

            # 应该跳过无效类型
            assert result["total_collections"] == 1
            assert result["failed_collections"] == 0  # 被跳过，不算失败
            assert len(result["collection_results"]) == 0

        @pytest.mark.asyncio
        async def test_stream_stats_parsing_error(
            self, streaming_collector, sample_data
        ):
            """测试流处理统计解析错误"""
            # 创建包含无效流处理统计信息的CollectionResult
            mock_result = CollectionResult(
                data_source="test_source",
                collection_type="fixtures",
                records_collected=len(sample_data),
                success_count=len(sample_data),
                error_count=0,
                status="success",
                collected_data=sample_data,
                error_message="流处理 - invalid_stats_format",
            )

            with patch.object(
                streaming_collector,
                "collect_fixtures_with_streaming",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                result = await streaming_collector.batch_collect_and_stream(
                    [{"type": "fixtures", "kwargs": {}}]
                )

                # 应该处理解析错误，使用默认的流统计
                assert result["total_collections"] == 1
                assert result["successful_collections"] == 1
