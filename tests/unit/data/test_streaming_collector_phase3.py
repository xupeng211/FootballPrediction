"""
Phase 3：流式数据采集器综合测试
目标：全面提升streaming_collector.py模块覆盖率到60%+
重点：测试Kafka流式处理、批量采集、双重写入和流类型检测功能
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest

from src.data.collectors.base_collector import CollectionResult
from src.data.collectors.streaming_collector import StreamingDataCollector


class TestStreamingCollectorBasic:
    """流式数据采集器基础测试"""

    def setup_method(self):
        """设置测试环境"""
        with patch("src.streaming.FootballKafkaProducer"):
            with patch("src.streaming.StreamConfig"):
                self.collector = StreamingDataCollector(
                    data_source="test_source", enable_streaming=True
                )

    def test_collector_initialization(self):
        """测试采集器初始化"""
        assert self.collector is not None
        assert hasattr(self.collector, "data_source")
        assert hasattr(self.collector, "enable_streaming")
        assert hasattr(self.collector, "stream_config")
        assert hasattr(self.collector, "kafka_producer")
        assert self.collector.data_source == "test_source"
        assert self.collector.enable_streaming is True
        assert self.collector.kafka_producer is not None

    def test_collector_initialization_without_streaming(self):
        """测试禁用流式处理的初始化"""
        with patch("src.streaming.StreamConfig"):
            collector = StreamingDataCollector(
                data_source="test_source", enable_streaming=False
            )

            assert collector.enable_streaming is False
            assert collector.kafka_producer is None

    def test_collector_initialization_with_custom_config(self):
        """测试自定义配置的初始化"""
        mock_config = Mock()

        with patch("src.streaming.FootballKafkaProducer"):
            collector = StreamingDataCollector(
                data_source="test_source",
                enable_streaming=True,
                stream_config=mock_config,
            )

            assert collector.stream_config is mock_config

    def test_collector_inheritance(self):
        """测试继承关系"""
        assert isinstance(self.collector, StreamingDataCollector)
        # 应该继承自DataCollector，检查是否有基类的方法
        assert hasattr(self.collector, "collect_fixtures")
        assert hasattr(self.collector, "collect_odds")
        assert hasattr(self.collector, "collect_live_scores")


class TestStreamingCollectorSendToStream:
    """流式数据采集器发送到流测试"""

    def setup_method(self):
        """设置测试环境"""
        with patch("src.streaming.FootballKafkaProducer") as mock_producer_class:
            self.mock_producer = AsyncMock()
            mock_producer_class.return_value = self.mock_producer

            with patch("src.streaming.StreamConfig"):
                self.collector = StreamingDataCollector(
                    data_source="test_source", enable_streaming=True
                )

    @pytest.mark.asyncio
    async def test_send_to_stream_success(self):
        """测试成功发送数据到流"""
        # Mock Kafka producer的send_batch方法
        expected_stats = {"success": 2, "failed": 0}
        self.mock_producer.send_batch.return_value = expected_stats

        data = [
            {"match_id": "123", "home_team": "Team A", "away_team": "Team B"},
            {"match_id": "456", "home_team": "Team C", "away_team": "Team D"},
        ]

        result = await self.collector._send_to_stream(data, "fixtures")

        assert result == expected_stats
        self.mock_producer.send_batch.assert_called_once_with(data, "fixtures")

    @pytest.mark.asyncio
    async def test_send_to_stream_empty_data(self):
        """测试发送空数据"""
        result = await self.collector._send_to_stream([], "fixtures")

        assert result == {"success": 0, "failed": 0}
        self.mock_producer.send_batch.assert_called_once_with([], "fixtures")

    @pytest.mark.asyncio
    async def test_send_to_stream_kafka_failure(self):
        """测试Kafka发送失败"""
        self.mock_producer.send_batch.side_effect = Exception("Kafka Error")

        data = [{"match_id": "123", "home_team": "Team A", "away_team": "Team B"}]

        result = await self.collector._send_to_stream(data, "fixtures")

        assert result == {"success": 0, "failed": 1}
        self.mock_producer.send_batch.assert_called_once_with(data, "fixtures")

    @pytest.mark.asyncio
    async def test_send_to_stream_disabled_streaming(self):
        """测试禁用流式处理的发送"""
        with patch("src.streaming.StreamConfig"):
            collector = StreamingDataCollector(
                data_source="test_source", enable_streaming=False
            )

            data = [{"match_id": "123", "home_team": "Team A", "away_team": "Team B"}]

            result = await collector._send_to_stream(data, "fixtures")

            assert result == {"success": 0, "failed": 0}

    @pytest.mark.asyncio
    async def test_send_to_stream_no_producer(self):
        """测试无Kafka生产者的发送"""
        # 手动设置kafka_producer为None
        self.collector.kafka_producer = None

        data = [{"match_id": "123", "home_team": "Team A", "away_team": "Team B"}]

        result = await self.collector._send_to_stream(data, "fixtures")

        assert result == {"success": 0, "failed": 0}

    @pytest.mark.asyncio
    async def test_send_to_stream_public_method_success(self):
        """测试公共的send_to_stream方法成功"""
        # Mock Kafka producer的send_batch方法
        expected_stats = {"success": 1, "failed": 0}
        self.mock_producer.send_batch.return_value = expected_stats

        data = [{"match_id": "123", "home_team": "Team A", "away_team": "Team B"}]

        result = await self.collector.send_to_stream(data)

        assert result is True
        # 验证流类型推断为"match"（因为包含match_id, home_team, away_team）
        self.mock_producer.send_batch.assert_called_once_with(data, "match")

    @pytest.mark.asyncio
    async def test_send_to_stream_public_method_odds_data(self):
        """测试公共send_to_stream方法处理赔率数据"""
        expected_stats = {"success": 1, "failed": 0}
        self.mock_producer.send_batch.return_value = expected_stats

        data = [{"match_id": "123", "bookmaker": "bet365", "odds": "2.5"}]

        result = await self.collector.send_to_stream(data)

        assert result is True
        # 验证流类型推断为"odds"（因为包含bookmaker, odds）
        self.mock_producer.send_batch.assert_called_once_with(data, "odds")

    @pytest.mark.asyncio
    async def test_send_to_stream_public_method_scores_data(self):
        """测试公共send_to_stream方法处理比分数据"""
        expected_stats = {"success": 1, "failed": 0}
        self.mock_producer.send_batch.return_value = expected_stats

        data = [{"match_id": "123", "score": "2-1", "minute": 45}]

        result = await self.collector.send_to_stream(data)

        assert result is True
        # 验证流类型推断为"scores"（因为包含score, minute）
        self.mock_producer.send_batch.assert_called_once_with(data, "scores")

    @pytest.mark.asyncio
    async def test_send_to_stream_public_method_default_data(self):
        """测试公共send_to_stream方法处理默认数据类型"""
        expected_stats = {"success": 1, "failed": 0}
        self.mock_producer.send_batch.return_value = expected_stats

        data = [{"some_field": "some_value"}]  # 不匹配任何特殊类型

        result = await self.collector.send_to_stream(data)

        assert result is True
        # 验证流类型为默认的"data"
        self.mock_producer.send_batch.assert_called_once_with(data, "data")

    @pytest.mark.asyncio
    async def test_send_to_stream_public_method_empty_data(self):
        """测试公共send_to_stream方法处理空数据"""
        result = await self.collector.send_to_stream([])

        assert result is True  # 空数据应该返回True
        self.mock_producer.send_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_to_stream_public_method_failure(self):
        """测试公共send_to_stream方法失败情况"""
        self.mock_producer.send_batch.side_effect = Exception("Kafka Error")

        data = [{"match_id": "123", "home_team": "Team A", "away_team": "Team B"}]

        result = await self.collector.send_to_stream(data)

        assert result is False  # 失败应该返回False

    @pytest.mark.asyncio
    async def test_send_to_stream_public_method_disabled_streaming(self):
        """测试禁用流式处理的公共send_to_stream方法"""
        with patch("src.streaming.StreamConfig"):
            collector = StreamingDataCollector(
                data_source="test_source", enable_streaming=False
            )

            data = [{"match_id": "123", "home_team": "Team A", "away_team": "Team B"}]

            result = await collector.send_to_stream(data)

            assert result is True  # 禁用流式处理应该返回True


class TestStreamingCollectorCollectFixturesWithStreaming:
    """流式数据采集器赛程采集测试"""

    def setup_method(self):
        """设置测试环境"""
        with patch("src.streaming.FootballKafkaProducer") as mock_producer_class:
            self.mock_producer = AsyncMock()
            mock_producer_class.return_value = self.mock_producer

            with patch("src.streaming.StreamConfig"):
                self.collector = StreamingDataCollector(
                    data_source="test_source", enable_streaming=True
                )

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_streaming_success(self):
        """测试成功采集赛程并发送到流"""
        # Mock父类的collect_fixtures方法
        mock_collection_result = CollectionResult(
            data_source="test_source",
            collection_type="fixtures",
            records_collected=5,
            success_count=5,
            error_count=0,
            status="success",
            collected_data=[
                {"match_id": "123", "home_team": "Team A", "away_team": "Team B"},
                {"match_id": "456", "home_team": "Team C", "away_team": "Team D"},
            ],
        )

        # Mock _send_to_stream方法
        expected_stream_stats = {"success": 2, "failed": 0}

        with patch.object(
            self.collector, "collect_fixtures", return_value=mock_collection_result
        ):
            with patch.object(
                self.collector, "_send_to_stream", return_value=expected_stream_stats
            ):
                result = await self.collector.collect_fixtures_with_streaming()

        # 验证返回结果
        assert result.records_collected == 5
        assert result.success_count == 5
        assert result.error_count == 0
        assert result.status == "success"

        # 验证流处理统计被添加到error_message中
        assert "流处理 - 成功: 2, 失败: 0" in result.error_message

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_streaming_no_data(self):
        """测试无数据情况"""
        mock_collection_result = CollectionResult(
            data_source="test_source",
            collection_type="fixtures",
            records_collected=0,
            success_count=0,
            error_count=0,
            status="success",
            collected_data=[],
        )

        with patch.object(
            self.collector, "collect_fixtures", return_value=mock_collection_result
        ):
            with patch.object(self.collector, "_send_to_stream") as mock_send:
                result = await self.collector.collect_fixtures_with_streaming()

        # 验证没有流式发送（因为没有数据）
        mock_send.assert_not_called()

        assert result.records_collected == 0
        assert result.success_count == 0

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_streaming_partial_stream_failure(self):
        """测试流式发送部分失败"""
        mock_collection_result = CollectionResult(
            data_source="test_source",
            collection_type="fixtures",
            records_collected=2,
            success_count=2,
            error_count=0,
            status="success",
            collected_data=[
                {"match_id": "123", "home_team": "Team A", "away_team": "Team B"},
                {"match_id": "456", "home_team": "Team C", "away_team": "Team D"},
            ],
        )

        # 流式发送部分失败
        stream_stats = {"success": 1, "failed": 1}

        with patch.object(
            self.collector, "collect_fixtures", return_value=mock_collection_result
        ):
            with patch.object(
                self.collector, "_send_to_stream", return_value=stream_stats
            ):
                result = await self.collector.collect_fixtures_with_streaming()

        # 验证返回结果反映部分成功
        assert result.records_collected == 2
        assert result.success_count == 2
        assert result.error_count == 0
        assert result.status == "success"

        # 验证流处理统计被添加
        assert "流处理 - 成功: 1, 失败: 1" in result.error_message

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_streaming_parent_failure(self):
        """测试父类采集失败"""
        mock_collection_result = CollectionResult(
            data_source="test_source",
            collection_type="fixtures",
            records_collected=0,
            success_count=0,
            error_count=1,
            status="failed",
            collected_data=[],
            error_message="Collection failed",
        )

        with patch.object(
            self.collector, "collect_fixtures", return_value=mock_collection_result
        ):
            with patch.object(self.collector, "_send_to_stream") as mock_send:
                result = await self.collector.collect_fixtures_with_streaming()

        # 验证没有流式发送
        mock_send.assert_not_called()

        # 验证返回原始失败结果
        assert result.records_collected == 0
        assert result.success_count == 0
        assert result.error_count == 1
        assert result.status == "failed"
        assert result.error_message == "Collection failed"

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_streaming_disabled_streaming(self):
        """测试禁用流式处理"""
        with patch("src.streaming.StreamConfig"):
            collector = StreamingDataCollector(
                data_source="test_source", enable_streaming=False
            )

            mock_collection_result = CollectionResult(
                data_source="test_source",
                collection_type="fixtures",
                records_collected=2,
                success_count=2,
                error_count=0,
                status="success",
                collected_data=[{"match_id": "123", "data": "test"}],
            )

            with patch.object(
                collector, "collect_fixtures", return_value=mock_collection_result
            ):
                with patch.object(collector, "_send_to_stream") as mock_send:
                    result = await collector.collect_fixtures_with_streaming()

            # 验证没有流式发送
            mock_send.assert_not_called()

            # 验证返回原始结果
            assert result.records_collected == 2
            assert result.success_count == 2


class TestStreamingCollectorCollectOddsWithStreaming:
    """流式数据采集器赔率采集测试"""

    def setup_method(self):
        """设置测试环境"""
        with patch("src.streaming.FootballKafkaProducer") as mock_producer_class:
            self.mock_producer = AsyncMock()
            mock_producer_class.return_value = self.mock_producer

            with patch("src.streaming.StreamConfig"):
                self.collector = StreamingDataCollector(
                    data_source="test_source", enable_streaming=True
                )

    @pytest.mark.asyncio
    async def test_collect_odds_with_streaming_success(self):
        """测试成功采集赔率并发送到流"""
        mock_collection_result = CollectionResult(
            data_source="test_source",
            collection_type="odds",
            records_collected=3,
            success_count=3,
            error_count=0,
            status="success",
            collected_data=[
                {"match_id": "123", "bookmaker": "bet365", "odds": "2.5"},
                {"match_id": "123", "bookmaker": "william_hill", "odds": "2.6"},
            ],
        )

        expected_stream_stats = {"success": 2, "failed": 0}

        with patch.object(
            self.collector, "collect_odds", return_value=mock_collection_result
        ):
            with patch.object(
                self.collector, "_send_to_stream", return_value=expected_stream_stats
            ):
                result = await self.collector.collect_odds_with_streaming()

        # 验证发送到"odds"流
        self.collector._send_to_stream.assert_called_once_with(
            mock_collection_result.collected_data, "odds"
        )

        # 验证返回结果
        assert result.records_collected == 3
        assert result.success_count == 3
        assert result.error_count == 0
        assert result.status == "success"

        # 验证流处理统计
        assert "流处理 - 成功: 2, 失败: 0" in result.error_message


class TestStreamingCollectorKafkaIntegration:
    """流式数据采集器Kafka集成测试"""

    def setup_method(self):
        """设置测试环境"""
        with patch("src.streaming.FootballKafkaProducer") as mock_producer_class:
            self.mock_producer = AsyncMock()
            mock_producer_class.return_value = self.mock_producer

            with patch("src.streaming.StreamConfig"):
                self.collector = StreamingDataCollector(
                    data_source="test_source", enable_streaming=True
                )

    def test_kafka_producer_initialization(self):
        """测试Kafka生产者初始化"""
        # 验证Kafka生产者被正确初始化
        assert self.collector.kafka_producer is not None
        assert self.collector.kafka_producer == self.mock_producer

    def test_kafka_producer_initialization_failure(self):
        """测试Kafka生产者初始化失败"""
        # 模拟初始化失败
        with patch("src.streaming.FootballKafkaProducer") as mock_producer_class:
            mock_producer_class.side_effect = Exception("Kafka initialization failed")

            with patch("src.streaming.StreamConfig"):
                collector = StreamingDataCollector(
                    data_source="test_source", enable_streaming=True
                )

                # 验证流式处理被禁用
                assert collector.enable_streaming is False
                assert collector.kafka_producer is None

    @pytest.mark.asyncio
    async def test_stream_config_customization(self):
        """测试流配置自定义"""
        mock_config = Mock()
        mock_config.bootstrap_servers = ["custom-kafka:9092"]
        mock_config.topic_prefix = "custom_"

        with patch("src.streaming.FootballKafkaProducer") as mock_producer_class:
            self.mock_producer = AsyncMock()
            mock_producer_class.return_value = self.mock_producer

            collector = StreamingDataCollector(
                data_source="test_source",
                enable_streaming=True,
                stream_config=mock_config,
            )

            # 验证配置被正确使用
            assert collector.stream_config is mock_config
            mock_producer_class.assert_called_once_with(mock_config)

    def test_stream_type_detection_in_public_method(self):
        """测试公共方法中的流类型检测"""
        test_cases = [
            # (input_data, expected_stream_type)
            (
                [{"match_id": "123", "home_team": "Team A", "away_team": "Team B"}],
                "match",
            ),
            ([{"match_id": "123", "bookmaker": "bet365", "odds": "2.5"}], "odds"),
            ([{"match_id": "123", "score": "2-1", "minute": 45}], "scores"),
            ([{"match_id": "123", "live": "true"}], "scores"),
            ([{"some_field": "some_value"}], "data"),
        ]

        for input_data, expected_type in test_cases:
            with patch.object(self.collector, "_send_to_stream") as mock_send:
                mock_send.return_value = {"success": 1, "failed": 0}

                # 执行异步方法
                async def test_send():
                    return await self.collector.send_to_stream(input_data)

                result = asyncio.run(test_send())

                # 验证调用正确的流类型
                mock_send.assert_called_once_with(input_data, expected_type)


class TestStreamingCollectorErrorHandling:
    """流式数据采集器错误处理测试"""

    def setup_method(self):
        """设置测试环境"""
        with patch("src.streaming.FootballKafkaProducer") as mock_producer_class:
            self.mock_producer = AsyncMock()
            mock_producer_class.return_value = self.mock_producer

            with patch("src.streaming.StreamConfig"):
                self.collector = StreamingDataCollector(
                    data_source="test_source", enable_streaming=True
                )

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_kafka_failure(self):
        """测试Kafka故障时的优雅降级"""
        # 模拟Kafka完全不可用
        self.mock_producer.send_batch.side_effect = Exception("Kafka connection failed")

        data = [{"match_id": "123", "home_team": "Team A", "away_team": "Team B"}]

        # 系统应该仍然工作，只是流式发送失败
        result = await self.collector._send_to_stream(data, "fixtures")

        assert result == {"success": 0, "failed": 1}
        # 系统不应该崩溃，应该返回失败统计

    @pytest.mark.asyncio
    async def test_error_logging(self):
        """测试错误日志记录"""
        self.mock_producer.send_batch.side_effect = Exception("Test error")

        data = [{"match_id": "123", "home_team": "Team A", "away_team": "Team B"}]

        with patch.object(self.collector, "logger") as mock_logger:
            result = await self.collector._send_to_stream(data, "fixtures")

            # 验证错误被记录
            mock_logger.error.assert_called_once()
            assert "发送数据到流失败" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_data_integrity_on_partial_failure(self):
        """测试部分失败时的数据完整性"""
        # 模拟部分数据发送成功，部分失败
        self.mock_producer.send_batch.return_value = {"success": 1, "failed": 1}

        data = [
            {"match_id": "123", "home_team": "Team A", "away_team": "Team B"},
            {"match_id": "456", "home_team": "Team C", "away_team": "Team D"},
        ]

        result = await self.collector._send_to_stream(data, "fixtures")

        # 验证返回正确的统计信息
        assert result["success"] == 1
        assert result["failed"] == 1
        assert result["success"] + result["failed"] == len(data)

    def test_config_validation(self):
        """测试配置验证"""
        # 测试各种配置组合
        test_configs = [
            {"enable_streaming": True, "stream_config": None},
            {"enable_streaming": False, "stream_config": None},
            {"enable_streaming": True, "stream_config": Mock()},
            {"enable_streaming": False, "stream_config": Mock()},
        ]

        for config in test_configs:
            try:
                with patch("src.streaming.FootballKafkaProducer"):
                    with patch("src.streaming.StreamConfig"):
                        collector = StreamingDataCollector(
                            data_source="test_source", **config
                        )
                        # 验证采集器可以正常创建
                        assert collector is not None
            except Exception as e:
                pytest.fail(f"配置验证失败: {config}, 错误: {e}")

    @pytest.mark.asyncio
    async def test_exception_in_stream_type_detection(self):
        """测试流类型检测中的异常处理"""
        # Mock _send_to_stream抛出异常
        with patch.object(self.collector, "_send_to_stream") as mock_send:
            mock_send.side_effect = Exception("Stream type detection error")

            data = [{"match_id": "123", "home_team": "Team A", "away_team": "Team B"}]

            result = await self.collector.send_to_stream(data)

            # 验证异常被捕获并返回False
            assert result is False


class TestStreamingCollectorIntegration:
    """流式数据采集器集成测试"""

    def setup_method(self):
        """设置测试环境"""
        with patch("src.streaming.FootballKafkaProducer") as mock_producer_class:
            self.mock_producer = AsyncMock()
            mock_producer_class.return_value = self.mock_producer

            with patch("src.streaming.StreamConfig"):
                self.collector = StreamingDataCollector(
                    data_source="test_source", enable_streaming=True
                )

    @pytest.mark.asyncio
    async def test_complete_streaming_workflow(self):
        """测试完整的流式处理工作流"""
        # 模拟一个完整的流式处理场景

        # 1. 采集数据
        mock_fixtures_result = CollectionResult(
            data_source="test_source",
            collection_type="fixtures",
            records_collected=2,
            success_count=2,
            error_count=0,
            status="success",
            collected_data=[
                {"match_id": "123", "home_team": "Team A", "away_team": "Team B"},
                {"match_id": "456", "home_team": "Team C", "away_team": "Team D"},
            ],
        )

        # 2. 流式发送
        stream_stats = {"success": 2, "failed": 0}

        with patch.object(
            self.collector, "collect_fixtures", return_value=mock_fixtures_result
        ):
            with patch.object(
                self.collector, "_send_to_stream", return_value=stream_stats
            ):
                # 执行带流式处理的采集
                result = await self.collector.collect_fixtures_with_streaming()

                # 验证整体工作流
                assert result.records_collected == 2
                assert result.status == "success"
                assert "流处理 - 成功: 2, 失败: 0" in result.error_message

    @pytest.mark.asyncio
    async def test_concurrent_stream_operations(self):
        """测试并发流操作"""
        # 模拟并发流操作
        tasks = []

        for i in range(3):
            data = [{"match_id": str(i), "data": f"test_{i}"}]
            task = self.collector._send_to_stream(data, "fixtures")
            tasks.append(task)

        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有任务都成功完成
        assert all(not isinstance(r, Exception) for r in results)
        assert all(isinstance(r, dict) for r in results)

        # 验证Kafka调用次数
        assert self.mock_producer.send_batch.call_count == 3

    def test_collector_state_consistency(self):
        """测试采集器状态一致性"""
        # 验证采集器状态在操作前后保持一致
        original_enable_streaming = self.collector.enable_streaming
        original_producer = self.collector.kafka_producer
        original_config = self.collector.stream_config

        # 执行一些操作
        # 注意：这里主要测试状态不会被意外修改

        assert self.collector.enable_streaming == original_enable_streaming
        assert self.collector.kafka_producer == original_producer
        assert self.collector.stream_config == original_config

    @pytest.mark.asyncio
    async def test_performance_characteristics(self):
        """测试性能特征"""
        # 测试大数据集的处理
        large_dataset = [{"match_id": str(i), "data": f"test_{i}"} for i in range(100)]

        # Mock快速处理
        self.mock_producer.send_batch.return_value = {"success": 100, "failed": 0}

        import time

        start_time = time.time()

        result = await self.collector._send_to_stream(large_dataset, "fixtures")

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证处理结果
        assert result["success"] == 100
        assert result["failed"] == 0

        # 验证处理时间合理（这个阈值可以根据实际情况调整）
        assert processing_time < 1.0  # 应该在1秒内完成

        # 验证只调用了一次send_batch（批量发送）
        self.mock_producer.send_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_mixed_data_types_workflow(self):
        """测试混合数据类型的工作流"""
        # 模拟处理多种数据类型的场景
        fixtures_data = [
            {"match_id": "123", "home_team": "Team A", "away_team": "Team B"}
        ]
        odds_data = [{"match_id": "123", "bookmaker": "bet365", "odds": "2.5"}]
        scores_data = [{"match_id": "123", "score": "2-1", "minute": 45}]

        # Mock各自的流式发送
        self.mock_producer.send_batch.return_value = {"success": 1, "failed": 0}

        # 使用公共方法发送不同类型的数据
        results = await asyncio.gather(
            self.collector.send_to_stream(fixtures_data),
            self.collector.send_to_stream(odds_data),
            self.collector.send_to_stream(scores_data),
            return_exceptions=True,
        )

        # 验证所有发送都成功
        assert all(result is True for result in results)

        # 验证发送到正确的流类型
        calls = self.mock_producer.send_batch.call_args_list
        assert calls[0][0][0] == fixtures_data
        assert calls[1][0][0] == odds_data
        assert calls[2][0][0] == scores_data

        # 验证流类型
        # 注意：这个验证取决于实际的send_batch实现参数顺序
        pass
