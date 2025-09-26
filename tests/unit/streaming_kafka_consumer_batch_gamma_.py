"""
KafkaConsumer Batch-Γ-008 测试套件

专门为 kafka_consumer.py 设计的测试，目标是将其覆盖率从 10% 提升至 ≥45%
覆盖所有 Kafka 消费功能、消息处理、错误处理和连接管理
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.streaming.kafka_consumer import FootballKafkaConsumer
from src.streaming.stream_config import StreamConfig


class TestKafkaConsumerBatchGamma008:
    """KafkaConsumer Batch-Γ-008 测试类"""

    @pytest.fixture
    def consumer_config(self):
        """创建 Kafka 消费者配置"""
        return {
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'football_prediction_group',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
            'client.id': 'football_prediction_consumer'
        }

    @pytest.fixture
    def stream_config(self):
        """创建 StreamConfig 实例"""
        return StreamConfig()

    @pytest.fixture
    def kafka_consumer(self, consumer_config):
        """创建 Kafka 消费者实例"""
        # 创建StreamConfig对象而不是传递字典
        stream_config = StreamConfig()
        # 更新配置
        stream_config.kafka_config.bootstrap_servers = consumer_config['bootstrap.servers']
        stream_config.kafka_config.consumer_group_id = consumer_config['group.id']
        stream_config.kafka_config.consumer_client_id = consumer_config['client.id']
        stream_config.kafka_config.consumer_auto_offset_reset = consumer_config['auto.offset.reset']
        stream_config.kafka_config.consumer_enable_auto_commit = consumer_config['enable.auto.commit']

        with patch('src.streaming.kafka_consumer.Consumer'):
            consumer = FootballKafkaConsumer(stream_config)
            return consumer

    @pytest.fixture
    def mock_message(self):
        """创建模拟 Kafka 消息"""
        mock_msg = Mock()
        mock_msg.topic = 'football_matches'
        mock_msg.partition = 0
        mock_msg.offset = 123
        mock_msg.key = b'match_123'
        mock_msg.value = b'{"match_id": 123, "home_team": "Team A", "away_team": "Team B"}'
        mock_msg.headers = []
        mock_msg.timestamp = datetime.now().timestamp()
        mock_msg.timestamp_type = 0
        return mock_msg

    def test_kafka_consumer_initialization(self, kafka_consumer):
        """测试 Kafka 消费者初始化"""
        # 验证配置设置
        assert kafka_consumer.config is not None
        assert kafka_consumer.running == False
        assert kafka_consumer.consumer is not None

    def test_kafka_consumer_initialization_with_topics(self, stream_config):
        """测试带主题订阅的 Kafka 消费者初始化"""
        topics = ['matches', 'odds', 'predictions']

        with patch('src.streaming.kafka_consumer.Consumer'):
            consumer = FootballKafkaConsumer(stream_config)
            consumer.subscribe_topics(topics)

        assert topics in consumer.consumer.subscribe.call_args[0]

    def test_create_consumer_success(self, kafka_consumer):
        """测试成功创建消费者"""
        # 重置消费者
        kafka_consumer.consumer = None

        with patch('confluent_kafka.Consumer') as mock_consumer_class:
            mock_consumer = Mock()
            mock_consumer_class.return_value = mock_consumer

            kafka_consumer._create_consumer()

            assert kafka_consumer.consumer == mock_consumer
            mock_consumer_class.assert_called_once_with(kafka_consumer.config)

    def test_create_consumer_with_error(self, kafka_consumer):
        """测试创建消费者时出错"""
        # 重置消费者
        kafka_consumer.consumer = None

        with patch('confluent_kafka.Consumer') as mock_consumer_class:
            mock_consumer_class.side_effect = Exception("Connection failed")

            with pytest.raises(Exception):
                kafka_consumer._create_consumer()

    def test_subscribe_to_topics(self, kafka_consumer):
        """测试订阅主题"""
        topics = ['matches', 'odds']

        kafka_consumer.subscribe(topics)

        assert set(kafka_consumer.topic_subscriptions) == set(topics)
        kafka_consumer.consumer.subscribe.assert_called_once_with(topics)

    def test_subscribe_to_single_topic(self, kafka_consumer):
        """测试订阅单个主题"""
        topic = 'matches'

        kafka_consumer.subscribe(topic)

        assert kafka_consumer.topic_subscriptions == [topic]
        kafka_consumer.consumer.subscribe.assert_called_once_with([topic])

    def test_subscribe_empty_topics(self, kafka_consumer):
        """测试订阅空主题列表"""
        with pytest.raises(Exception):
            kafka_consumer.subscribe([])

    def test_unsubscribe_from_topics(self, kafka_consumer):
        """测试取消订阅主题"""
        kafka_consumer.topic_subscriptions = ['matches', 'odds']

        kafka_consumer.unsubscribe(['matches'])

        assert kafka_consumer.topic_subscriptions == ['odds']
        kafka_consumer.consumer.unsubscribe.assert_called_once()

    def test_unsubscribe_all_topics(self, kafka_consumer):
        """测试取消订阅所有主题"""
        kafka_consumer.topic_subscriptions = ['matches', 'odds']

        kafka_consumer.unsubscribe()

        assert kafka_consumer.topic_subscriptions == []
        kafka_consumer.consumer.unsubscribe.assert_called_once()

    def test_get_consumer_config(self, kafka_consumer, consumer_config):
        """测试获取消费者配置"""
        config = kafka_consumer.get_consumer_config()

        assert config == consumer_config

    def test_get_topic_subscriptions(self, kafka_consumer):
        """测试获取主题订阅"""
        kafka_consumer.topic_subscriptions = ['matches', 'odds']

        subscriptions = kafka_consumer.get_topic_subscriptions()

        assert subscriptions == ['matches', 'odds']

    def test_get_consumer_info(self, kafka_consumer):
        """测试获取消费者信息"""
        kafka_consumer.topic_subscriptions = ['matches', 'odds']
        kafka_consumer.running = True

        info = kafka_consumer.get_consumer_info()

        assert info['running'] == True
        assert set(info['subscriptions']) == {'matches', 'odds'}
        assert 'config' in info

    def test_is_connected_connected(self, kafka_consumer):
        """测试连接状态 - 已连接"""
        kafka_consumer.consumer = Mock()

        assert kafka_consumer.is_connected() == True

    def test_is_connected_disconnected(self, kafka_consumer):
        """测试连接状态 - 未连接"""
        kafka_consumer.consumer = None

        assert kafka_consumer.is_connected() == False

    def test_decode_message_success(self, kafka_consumer, mock_message):
        """测试成功解码消息"""
        result = kafka_consumer._decode_message(mock_message)

        assert result['topic'] == mock_message.topic
        assert result['partition'] == mock_message.partition
        assert result['offset'] == mock_message.offset
        assert result['key'] == 'match_123'
        assert result['value'] == {"match_id": 123, "home_team": "Team A", "away_team": "Team B"}

    def test_decode_message_no_key(self, kafka_consumer, mock_message):
        """测试解码无键消息"""
        mock_message.key = None

        result = kafka_consumer._decode_message(mock_message)

        assert result['key'] is None

    def test_decode_message_no_value(self, kafka_consumer, mock_message):
        """测试解码无值消息"""
        mock_message.value = None

        result = kafka_consumer._decode_message(mock_message)

        assert result['value'] is None

    def test_decode_message_invalid_json(self, kafka_consumer, mock_message):
        """测试解码无效 JSON 消息"""
        mock_message.value = b'invalid json'

        result = kafka_consumer._decode_message(mock_message)

        assert result['value'] == b'invalid json'

    def test_decode_message_headers(self, kafka_consumer, mock_message):
        """测试解码带头的消息"""
        mock_message.headers = [('content-type', b'application/json')]

        result = kafka_consumer._decode_message(mock_message)

        assert result['headers'] == {'content-type': 'application/json'}

    def test_decode_message_empty_headers(self, kafka_consumer, mock_message):
        """测试解码空头消息"""
        mock_message.headers = []

        result = kafka_consumer._decode_message(mock_message)

        assert result['headers'] == {}

    def test_process_message_callback_success(self, kafka_consumer, mock_message):
        """测试成功处理消息回调"""
        callback_called = []

        def message_callback(message):
            callback_called.append(message)

        kafka_consumer._process_message(mock_message, message_callback)

        assert len(callback_called) == 1
        assert callback_called[0]['topic'] == mock_message.topic

    def test_process_message_no_callback(self, kafka_consumer, mock_message):
        """测试无回调处理消息"""
        # 应该不抛出异常
        kafka_consumer._process_message(mock_message, None)

    def test_process_message_callback_error(self, kafka_consumer, mock_message):
        """测试消息回调错误"""
        def error_callback(message):
            raise Exception("Callback error")

        # 应该不抛出异常，而是记录错误
        kafka_consumer._process_message(mock_message, error_callback)

    def test_start_consuming_success(self, kafka_consumer, mock_message):
        """测试成功开始消费"""
        # Mock 消费者轮询
        kafka_consumer.consumer.poll.side_effect = [mock_message, None]  # 第二次返回 None 结束循环

        consumed_messages = []

        def callback(message):
            consumed_messages.append(message)

        # 设置运行状态
        kafka_consumer.running = True

        # 启动消费（使用短超时）
        with patch('time.sleep'):  # 避免实际睡眠
            kafka_consumer.start_consuming(callback, timeout=0.1, batch_size=1)

        assert len(consumed_messages) == 1
        assert consumed_messages[0]['topic'] == mock_message.topic

    def test_start_consuming_no_callback(self, kafka_consumer):
        """测试无回调开始消费"""
        with pytest.raises(Exception):
            kafka_consumer.start_consuming(None)

    def test_start_consuming_not_connected(self, kafka_consumer):
        """测试未连接开始消费"""
        kafka_consumer.consumer = None

        def callback(message):
            pass

        with pytest.raises(Exception):
            kafka_consumer.start_consuming(callback)

    def test_start_consuming_batch_processing(self, kafka_consumer):
        """测试批处理消费"""
        # 创建多个消息
        messages = [Mock() for _ in range(3)]
        for i, msg in enumerate(messages):
            msg.topic = f'topic_{i}'
            msg.value = f'value_{i}'

        kafka_consumer.consumer.poll.side_effect = messages + [None]

        consumed_messages = []

        def callback(message):
            consumed_messages.append(message)

        kafka_consumer.running = True

        with patch('time.sleep'):
            kafka_consumer.start_consuming(callback, timeout=0.1, batch_size=3)

        assert len(consumed_messages) == 3

    def test_start_consuming_with_commit(self, kafka_consumer, mock_message):
        """测试带提交的消费"""
        kafka_consumer.consumer.poll.side_effect = [mock_message, None]

        consumed_messages = []

        def callback(message):
            consumed_messages.append(message)

        kafka_consumer.running = True

        with patch('time.sleep'):
            kafka_consumer.start_consuming(callback, timeout=0.1, batch_size=1, auto_commit=True)

        assert len(consumed_messages) == 1
        kafka_consumer.consumer.commit.assert_called()

    def test_start_consuming_timeout(self, kafka_consumer):
        """测试消费超时"""
        # 消费者始终返回 None
        kafka_consumer.consumer.poll.return_value = None

        consumed_messages = []

        def callback(message):
            consumed_messages.append(message)

        kafka_consumer.running = True

        with patch('time.sleep'):
            kafka_consumer.start_consuming(callback, timeout=0.1, batch_size=1)

        assert len(consumed_messages) == 0

    def test_stop_consuming(self, kafka_consumer):
        """测试停止消费"""
        kafka_consumer.running = True

        kafka_consumer.stop_consuming()

        assert kafka_consumer.running == False

    def test_pause_consuming(self, kafka_consumer):
        """测试暂停消费"""
        kafka_consumer.consumer = Mock()

        kafka_consumer.pause_consuming(['matches'])

        kafka_consumer.consumer.pause.assert_called_once_with(['matches'])

    def test_resume_consuming(self, kafka_consumer):
        """测试恢复消费"""
        kafka_consumer.consumer = Mock()

        kafka_consumer.resume_consuming(['matches'])

        kafka_consumer.consumer.resume.assert_called_once_with(['matches'])

    def test_seek_to_beginning(self, kafka_consumer):
        """测试寻址到开始"""
        kafka_consumer.consumer = Mock()

        kafka_consumer.seek_to_beginning('matches', 0)

        kafka_consumer.consumer.seek.assert_called_once()

    def test_seek_to_end(self, kafka_consumer):
        """测试寻址到末尾"""
        kafka_consumer.consumer = Mock()

        kafka_consumer.seek_to_end('matches', 0)

        kafka_consumer.consumer.seek.assert_called_once()

    def test_commit_offset(self, kafka_consumer):
        """测试提交偏移量"""
        kafka_consumer.consumer = Mock()

        kafka_consumer.commit_offset()

        kafka_consumer.consumer.commit.assert_called_once()

    def test_commit_offset_async(self, kafka_consumer):
        """测试异步提交偏移量"""
        kafka_consumer.consumer = Mock()

        kafka_consumer.commit_offset(async_commit=True)

        kafka_consumer.consumer.commit.asynchronous.assert_called_once()

    def test_get_committed_offsets(self, kafka_consumer):
        """测试获取已提交偏移量"""
        kafka_consumer.consumer = Mock()
        kafka_consumer.consumer.committed.return_value = {'matches': {'partition': 0, 'offset': 100}}

        offsets = kafka_consumer.get_committed_offsets(['matches'])

        assert offsets == {'matches': {'partition': 0, 'offset': 100}}
        kafka_consumer.consumer.committed.assert_called_once_with(['matches'])

    def test_get_watermark_offsets(self, kafka_consumer):
        """测试获取水位偏移量"""
        kafka_consumer.consumer = Mock()
        kafka_consumer.consumer.get_watermark_offsets.return_value = (0, 1000)

        low, high = kafka_consumer.get_watermark_offsets('matches', 0)

        assert low == 0
        assert high == 1000
        kafka_consumer.consumer.get_watermark_offsets.assert_called_once()

    def test_consumer_error_handling(self, kafka_consumer):
        """测试消费者错误处理"""
        # Mock 消费者抛出异常
        kafka_consumer.consumer.poll.side_effect = Exception("Consumer error")

        consumed_messages = []

        def callback(message):
            consumed_messages.append(message)

        kafka_consumer.running = True

        with patch('time.sleep'):
            # 应该优雅处理错误而不抛出异常
            kafka_consumer.start_consuming(callback, timeout=0.1, batch_size=1)

        assert len(consumed_messages) == 0

    def test_consumer_reconnection(self, kafka_consumer):
        """测试消费者重连"""
        # 第一次调用失败，第二次成功
        kafka_consumer.consumer.poll.side_effect = [Exception("Connection lost"), None]

        consumed_messages = []

        def callback(message):
            consumed_messages.append(message)

        kafka_consumer.running = True

        with patch('time.sleep'):
            kafka_consumer.start_consuming(callback, timeout=0.2, batch_size=1)

        assert len(consumed_messages) == 0

    def test_configuration_validation(self, consumer_config):
        """测试配置验证"""
        # 测试缺少必需配置
        invalid_config = consumer_config.copy()
        invalid_config.pop('bootstrap.servers')

        with pytest.raises(Exception):
            FootballKafkaConsumer(invalid_config)

    def test_consumer_lifecycle(self, kafka_consumer):
        """测试消费者生命周期"""
        # 测试完整的生命周期：创建 -> 订阅 -> 开始 -> 停止
        assert kafka_consumer.is_connected() == True

        kafka_consumer.subscribe(['test_topic'])
        assert 'test_topic' in kafka_consumer.get_topic_subscriptions()

        kafka_consumer.running = True
        assert kafka_consumer.get_consumer_info()['running'] == True

        kafka_consumer.stop_consuming()
        assert kafka_consumer.running == False

        kafka_consumer.unsubscribe()
        assert len(kafka_consumer.get_topic_subscriptions()) == 0

    def test_batch_message_processing(self, kafka_consumer):
        """测试批量消息处理"""
        # 创建多个消息
        messages = []
        for i in range(5):
            msg = Mock()
            msg.topic = 'matches'
            msg.value = f'{{"match_id": {i}}}'
            messages.append(msg)

        kafka_consumer.consumer.poll.side_effect = messages + [None]

        processed_messages = []

        def callback(message):
            processed_messages.append(message)

        kafka_consumer.running = True

        with patch('time.sleep'):
            kafka_consumer.start_consuming(callback, timeout=0.1, batch_size=5)

        assert len(processed_messages) == 5
        for i, msg in enumerate(processed_messages):
            assert msg['value']['match_id'] == i

    def test_error_handling_in_consume_loop(self, kafka_consumer):
        """测试消费循环中的错误处理"""
        # 模拟轮询时偶尔出错
        kafka_consumer.consumer.poll.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            None  # 正常退出
        ]

        processed_messages = []

        def callback(message):
            processed_messages.append(message)

        kafka_consumer.running = True

        with patch('time.sleep'):
            # 应该优雅处理网络错误
            kafka_consumer.start_consuming(callback, timeout=0.1, batch_size=1)

        assert len(processed_messages) == 0

    def test_consumer_stats(self, kafka_consumer):
        """测试消费者统计"""
        # 设置一些状态
        kafka_consumer.topic_subscriptions = ['matches', 'odds']
        kafka_consumer.running = True

        stats = kafka_consumer.get_consumer_info()

        assert 'running' in stats
        assert 'subscriptions' in stats
        assert 'config' in stats
        assert isinstance(stats['subscriptions'], list)
        assert isinstance(stats['config'], dict)