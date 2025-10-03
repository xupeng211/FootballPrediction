from src.streaming.kafka_consumer import FootballKafkaConsumer
from unittest.mock import Mock, patch
import pytest

"""
Kafka消费者测试套件

覆盖src/streaming/kafka_consumer.py的所有功能：
- KafkaConsumer类初始化
- 消费者创建和配置
- 主题订阅
- 消息轮询和处理
- 连接管理
- 错误处理

目标：实现高覆盖率
"""

class TestFootballKafkaConsumer:
    """FootballKafkaConsumer测试类"""
    @pytest.fixture
    def mock_stream_config(self):
        """模拟StreamConfig"""
        config = Mock()
        config.get_consumer_config.return_value = {
            "bootstrap.servers[: "localhost:9092[","]"""
            "]group.id[: "test-group[","]"""
            "]auto.offset.reset[": ["]latest[",""""
            "]enable.auto.commit[": False}": return config["""
    @pytest.fixture
    def consumer(self, mock_stream_config):
        "]]""创建FootballKafkaConsumer实例"""
        with patch("confluent_kafka.Consumer[") as mock_consumer_class:": mock_consumer = Mock()": mock_consumer_class.return_value = mock_consumer[": kafka_consumer = FootballKafkaConsumer(mock_stream_config)"
            kafka_consumer.consumer = mock_consumer
            return kafka_consumer
    def test_football_kafka_consumer_init_success(self, mock_stream_config):
        "]]""测试成功创建FootballKafkaConsumer"""
        with patch("confluent_kafka.Consumer[") as mock_consumer_class:": mock_consumer = Mock()": mock_consumer_class.return_value = mock_consumer[": consumer = FootballKafkaConsumer(mock_stream_config)"
            assert consumer.config ==mock_stream_config
            assert consumer.consumer ==mock_consumer
            expected_config = mock_stream_config.get_consumer_config()
            mock_consumer_class.assert_called_once_with(expected_config)
    def test_kafka_consumer_init_with_default_config(self):
        "]]""测试使用默认配置创建KafkaConsumer"""
        default_config = {
            "bootstrap.servers[: "localhost:9092[","]"""
            "]group.id[: "football-prediction-consumers[","]"""
            "]auto.offset.reset[": ["]latest[",""""
            "]enable.auto.commit[": True}": with patch("]confluent_kafka.Consumer[") as mock_consumer_class:": mock_consumer = Mock()": mock_consumer_class.return_value = mock_consumer[": consumer = KafkaConsumer()"
            assert consumer.config ==default_config
            assert consumer.consumer ==mock_consumer
    def test_kafka_consumer_init_failure(self, mock_config):
        "]]""测试KafkaConsumer初始化失败"""
        with patch("confluent_kafka.Consumer[") as mock_consumer_class:": mock_consumer_class.side_effect = Exception("]连接失败[")": with pytest.raises(Exception, match = "]连接失败[")": KafkaConsumer(mock_config)": def test_subscribe_topics_success(self, consumer):""
        "]""测试成功订阅主题"""
        topics = ["test-topic1[", "]test-topic2["]": consumer.consumer.subscribe.return_value = None[": result = consumer.subscribe_topics(topics)": assert result is True"
        consumer.consumer.subscribe.assert_called_once_with(topics)
    def test_subscribe_topics_empty_list(self, consumer):
        "]]""测试订阅空主题列表"""
        result = consumer.subscribe_topics([])
        assert result is False
        consumer.consumer.subscribe.assert_not_called()
    def test_subscribe_topics_failure(self, consumer):
        """测试订阅主题失败"""
        topics = "test-topic[": consumer.consumer.subscribe.side_effect = Exception("]订阅失败[")": result = consumer.subscribe_topics(topics)": assert result is False[" def test_poll_message_success(self, consumer):"
        "]]""测试成功轮询消息"""
        mock_message = Mock()
        mock_message.value = b'{"test[": ["]data["}'": mock_message.topic = "]test-topic[": mock_message.partition = 0[": mock_message.offset = 123[": consumer.consumer.poll.return_value = mock_message[": result = consumer.poll_message(timeout=1.0)"
        assert result ==mock_message
        consumer.consumer.poll.assert_called_once_with(1.0)
    def test_poll_message_no_message(self, consumer):
        "]]]]""测试轮询无消息"""
        consumer.consumer.poll.return_value = None
        result = consumer.poll_message(timeout=1.0)
        assert result is None
        consumer.consumer.poll.assert_called_once_with(1.0)
    def test_poll_message_failure(self, consumer):
        """测试轮询消息失败"""
        consumer.consumer.poll.side_effect = Exception("轮询失败[")": result = consumer.poll_message(timeout=1.0)": assert result is None[" def test_close_consumer_success(self, consumer):"
        "]]""测试成功关闭消费者"""
        consumer.consumer.close.return_value = None
        result = consumer.close()
        assert result is True
        consumer.consumer.close.assert_called_once()
    def test_close_consumer_failure(self, consumer):
        """测试关闭消费者失败"""
        consumer.consumer.close.side_effect = Exception("关闭失败[")": result = consumer.close()": assert result is False[" def test_consumer_assignment(self, consumer):"
        "]]""测试获取消费者分区分配"""
        mock_assignment = [Mock(), Mock()]
        consumer.consumer.assignment.return_value = mock_assignment
        result = consumer.get_assignment()
        assert result ==mock_assignment
        consumer.consumer.assignment.assert_called_once()
    def test_consumer_position(self, consumer):
        """测试获取消费者位置"""
        mock_topic_partition = Mock()
        mock_position = 123
        consumer.consumer.position.return_value = mock_position
        result = consumer.get_position(mock_topic_partition)
        assert result ==mock_position
        consumer.consumer.position.assert_called_once_with(mock_topic_partition)
    def test_consumer_commit(self, consumer):
        """测试提交偏移量"""
        mock_offsets = {"test-topic[": {"]partition[": 0, "]offset[": 123}}": consumer.consumer.commit.return_value = None[": result = consumer.commit(offsets=mock_offsets)": assert result is True"
        consumer.consumer.commit.assert_called_once_with(offsets=mock_offsets)
    def test_consumer_commit_failure(self, consumer):
        "]]""测试提交偏移量失败"""
        consumer.consumer.commit.side_effect = Exception("提交失败[")": result = consumer.commit(offsets={))": assert result is False[" def test_consumer_store_offsets(self, consumer):"
        "]]""测试存储偏移量"""
        message = Mock()
        message.topic = "test-topic[": message.partition = 0[": message.offset = 123[": consumer.consumer.store_offsets.return_value = None[": result = consumer.store_offsets(message=message)"
        assert result is True
        consumer.consumer.store_offsets.assert_called_once_with(message=message)
    def test_consumer_store_offsets_failure(self, consumer):
        "]]]]""测试存储偏移量失败"""
        message = Mock()
        consumer.consumer.store_offsets.side_effect = Exception("存储失败[")": result = consumer.store_offsets(message=message)": assert result is False[" def test_consumer_unsubscribe(self, consumer):"
        "]]""测试取消订阅"""
        consumer.consumer.unsubscribe.return_value = None
        result = consumer.unsubscribe()
        assert result is True
        consumer.consumer.unsubscribe.assert_called_once()
    def test_consumer_unsubscribe_failure(self, consumer):
        """测试取消订阅失败"""
        consumer.consumer.unsubscribe.side_effect = Exception("取消订阅失败[")": result = consumer.unsubscribe()": assert result is False[" def test_consumer_get_watermark_offsets(self, consumer):"
        "]]""测试获取水位偏移量"""
        mock_topic_partition = Mock()
        low, high = 0, 1000
        consumer.consumer.get_watermark_offsets.return_value = (low, high)
        result = consumer.get_watermark_offsets(mock_topic_partition)
        assert result ==(low, high)
        consumer.consumer.get_watermark_offsets.assert_called_once_with(
            mock_topic_partition
        )
    def test_consumer_get_watermark_offsets_failure(self, consumer):
        """测试获取水位偏移量失败"""
        mock_topic_partition = Mock()
        consumer.consumer.get_watermark_offsets.side_effect = Exception("获取失败[")": result = consumer.get_watermark_offsets(mock_topic_partition)": assert result is None[" class TestKafkaConsumerEdgeCases:"
    "]]""KafkaConsumer边界情况测试"""
    def test_none_config_handling(self):
        """测试处理None配置"""
        with pytest.raises(Exception):
            KafkaConsumer(None)
    def test_empty_config_handling(self):
        """测试处理空配置"""
        with patch("confluent_kafka.Consumer[") as mock_consumer_class:": mock_consumer = Mock()": mock_consumer_class.return_value = mock_consumer[": consumer = KafkaConsumer({))"
            assert consumer.config =={}
    def test_config_with_special_characters(self, consumer):
        "]]""测试配置中的特殊字符"""
        special_config = {
            "bootstrap.servers[: "localhost:9092,another-server:9093[","]"""
            "]group.id[: "test.group.with.dots[","]"""
            "]auto.offset.reset[": ["]earliest["}": with patch("]confluent_kafka.Consumer[") as mock_consumer_class:": mock_consumer = Mock()": mock_consumer_class.return_value = mock_consumer[": new_consumer = KafkaConsumer(special_config)"
            assert new_consumer.config ==special_config
    def test_subscribe_topics_with_unicode(self, consumer):
        "]]""测试订阅Unicode主题名称"""
        unicode_topics = ["测试主题[", "]test-topic-unicode["]": consumer.consumer.subscribe.return_value = None[": result = consumer.subscribe_topics(unicode_topics)": assert result is True"
        consumer.consumer.subscribe.assert_called_once_with(unicode_topics)
    def test_poll_with_negative_timeout(self, consumer):
        "]]""测试负超时轮询"""
        consumer.consumer.poll.return_value = None
        result = consumer.poll_message(timeout=-1.0)
        assert result is None
        consumer.consumer.poll.assert_called_once_with(-1.0)
    def test_poll_with_zero_timeout(self, consumer):
        """测试零超时轮询"""
        consumer.consumer.poll.return_value = None
        result = consumer.poll_message(timeout=0.0)
        assert result is None
        consumer.consumer.poll.assert_called_once_with(0.0)
    def test_consumer_already_closed(self, consumer):
        """测试消费者已关闭"""
        consumer.consumer.close.side_effect = Exception("消费者已关闭[")": result = consumer.close()": assert result is False[" def test_consumer_methods_with_none_consumer(self):"
        "]]""测试consumer为None时的方法调用"""
        with patch("confluent_kafka.Consumer[") as mock_consumer_class:": mock_consumer_class.return_value = None[": consumer = KafkaConsumer({))": consumer.consumer = None"
            # 这些方法应该能安全处理None consumer
            assert consumer.subscribe_topics("]]test[") is False[" assert consumer.poll_message() is None["""
            assert consumer.close() is False
if __name__ =="]]]__main__[": pytest.main(""""
        ["]__file__[",""""
            "]-v[",""""
            "]--cov=src.streaming.kafka_consumer[",""""
            "]--cov-report=term-missing["]"]"""
    )