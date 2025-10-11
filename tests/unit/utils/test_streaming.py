"""流处理测试"""

import pytest


class TestStreaming:
    """测试流处理模块"""

    def test_kafka_components_import(self):
        """测试Kafka组件导入"""
        try:
            from src.streaming.kafka_components import (
                KafkaProducerManager,
                KafkaConsumerManager,
            )

            assert KafkaProducerManager is not None
            assert KafkaConsumerManager is not None
        except ImportError:
            pytest.skip("Kafka components not available")

    def test_kafka_producer_import(self):
        """测试Kafka生产者导入"""
        try:
            from src.streaming.kafka_producer import FootballKafkaProducer

            assert FootballKafkaProducer is not None
        except ImportError:
            pytest.skip("FootballKafkaProducer not available")

    def test_kafka_consumer_import(self):
        """测试Kafka消费者导入"""
        try:
            from src.streaming.kafka_consumer import FootballKafkaConsumer

            assert FootballKafkaConsumer is not None
        except ImportError:
            pytest.skip("FootballKafkaConsumer not available")

    def test_stream_processor_import(self):
        """测试流处理器导入"""
        try:
            from src.streaming.stream_processor import StreamProcessor

            assert StreamProcessor is not None
        except ImportError:
            pytest.skip("StreamProcessor not available")
