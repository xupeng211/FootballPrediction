import json

from src.streaming.kafka_producer import FootballKafkaProducer
from unittest.mock import Mock, patch
import pytest

"""
Kafka生产者简单测试套件

覆盖src/streaming/kafka_producer.py的核心功能：
- FootballKafkaProducer类初始化
- 生产者创建和配置
- 消息序列化和发送
- 错误处理

目标：快速提升覆盖率
"""

class TestFootballKafkaProducer:
    """FootballKafkaProducer测试类"""
    @pytest.fixture
    def mock_stream_config(self):
        """模拟StreamConfig"""
        config = Mock()
        config.get_producer_config.return_value = {
            "bootstrap.servers[: "localhost:9092[","]"""
            "]client.id[: "test-producer[","]"""
            "]acks[": ["]all[",""""
            "]retries[": 3}": return config["""
    @pytest.fixture
    def producer(self, mock_stream_config):
        "]]""创建FootballKafkaProducer实例"""
        with patch("confluent_kafka.Producer[") as mock_producer_class:": mock_producer = Mock()": mock_producer_class.return_value = mock_producer[": football_producer = FootballKafkaProducer(mock_stream_config)"
            football_producer.producer = mock_producer
            return football_producer
    def test_producer_init_success(self, mock_stream_config):
        "]]""测试成功创建FootballKafkaProducer"""
        with patch("confluent_kafka.Producer[") as mock_producer_class:": mock_producer = Mock()": mock_producer_class.return_value = mock_producer[": producer = FootballKafkaProducer(mock_stream_config)"
            assert producer.config ==mock_stream_config
            assert producer.producer ==mock_producer
            expected_config = mock_stream_config.get_producer_config()
            mock_producer_class.assert_called_once_with(expected_config)
    def test_producer_init_with_default_config(self):
        "]]""测试使用默认配置创建FootballKafkaProducer"""
        with patch("confluent_kafka.Producer[") as mock_producer_class:": mock_producer = Mock()": mock_producer_class.return_value = mock_producer[": producer = FootballKafkaProducer()"
            assert producer.config is not None
            assert producer.producer ==mock_producer
            mock_producer_class.assert_called_once()
    def test_producer_init_failure(self, mock_stream_config):
        "]]""测试FootballKafkaProducer初始化失败"""
        with patch("confluent_kafka.Producer[") as mock_producer_class:": mock_producer_class.side_effect = Exception("]连接失败[")": with pytest.raises(Exception, match = "]连接失败[")": FootballKafkaProducer(mock_stream_config)": def test_serialize_message_success(self, producer):""
        "]""测试成功序列化消息"""
        test_data = {"match_id[": 123, "]home_team[": "]Test FC[", "]away_team[": "]Away FC["}": result = producer._serialize_message(test_data)": expected = json.dumps(test_data).encode("]utf-8[")": assert result ==expected[" def test_serialize_message_with_complex_data(self, producer):""
        "]]""测试序列化复杂数据"""
        test_data = {
            "match_id[": 123,""""
            "]teams[": {"]home[": "]Team A[", "]away[": "]Team B["},""""
            "]scores[: "1, 2, 3[","]"""
            "]timestamp[: "2025-09-29T15:00:00["}"]": result = producer._serialize_message(test_data)": expected = json.dumps(test_data).encode("]utf-8[")": assert result ==expected[" def test_serialize_message_with_none(self, producer):""
        "]]""测试序列化None数据"""
        with pytest.raises(Exception):
            producer._serialize_message(None)
    def test_produce_message_success(self, producer):
        """测试成功发送消息"""
        topic = "test-topic[": message = {"]test[": ["]data["}": key = "]test-key[": producer.producer.produce.return_value = None[": producer.producer.flush.return_value = 1[": result = producer.produce_message(topic, message, key)": assert result is True"
        producer.producer.produce.assert_called_once()
        producer.producer.flush.assert_called_once()
    def test_produce_message_without_key(self, producer):
        "]]]""测试发送无key消息"""
        topic = "test-topic[": message = {"]test[": ["]data["}": producer.producer.produce.return_value = None[": producer.producer.flush.return_value = 1[": result = producer.produce_message(topic, message)"
        assert result is True
        producer.producer.produce.assert_called_once()
    def test_produce_message_failure(self, producer):
        "]]]""测试发送消息失败"""
        topic = "test-topic[": message = {"]test[": ["]data["}": producer.producer.produce.side_effect = Exception("]发送失败[")": result = producer.produce_message(topic, message)": assert result is False[" def test_flush_success(self, producer):"
        "]]""测试成功刷新缓冲区"""
        producer.producer.flush.return_value = 1
        result = producer.flush()
        assert result is True
        producer.producer.flush.assert_called_once()
    def test_flush_failure(self, producer):
        """测试刷新缓冲区失败"""
        producer.producer.flush.return_value = 0
        result = producer.flush()
        assert result is False
    def test_flush_with_timeout(self, producer):
        """测试带超时的刷新"""
        producer.producer.flush.return_value = 1
        result = producer.flush(timeout=5.0)
        assert result is True
        producer.producer.flush.assert_called_once_with(5.0)
class TestFootballKafkaProducerEdgeCases:
    """FootballKafkaProducer边界情况测试"""
    def test_empty_topic_handling(self, producer):
        """测试空主题处理"""
        with pytest.raises(Exception):
            producer.produce_message("", {"test[": "]data["))": def test_none_topic_handling(self, producer):"""
        "]""测试None主题处理"""
        with pytest.raises(Exception):
            producer.produce_message(None, {"test[": ["]data["))": def test_empty_message_handling(self, producer):"""
        "]""测试空消息处理"""
        with pytest.raises(Exception):
            producer.produce_message("test-topic[", {))": def test_unicode_in_message(self, producer):"""
        "]""测试消息中的Unicode字符"""
        message = {"test[: "测试数据"", "emoji]}": producer.producer.produce.return_value = None[": producer.producer.flush.return_value = 1[": result = producer.produce_message("]]test-topic[", message)": assert result is True[" def test_large_message_handling(self, producer):""
        "]]""测试大消息处理"""
        message = {"data[": ["]x[" * 10000}  # 10KB消息[": producer.producer.produce.return_value = None[": producer.producer.flush.return_value = 1[": result = producer.produce_message("]]]]test-topic[", message)": assert result is True[" def test_producer_already_initialized(self, producer):""
        "]]""测试生产者已初始化状态"""
        # 验证producer对象已经正确设置
        assert producer.producer is not None
        assert producer.config is not None
    def test_config_methods_called(self, mock_stream_config):
        """测试配置方法被正确调用"""
        with patch("confluent_kafka.Producer[") as mock_producer_class:": mock_producer = Mock()": mock_producer_class.return_value = mock_producer[": FootballKafkaProducer(mock_stream_config)"
            # 验证get_producer_config被调用
            mock_stream_config.get_producer_config.assert_called_once()
if __name__ =="]]__main__[": pytest.main(""""
        ["]__file__[",""""
            "]-v[",""""
            "]--cov=src.streaming.kafka_producer[",""""
            "]--cov-report=term-missing["]"]"""
    )