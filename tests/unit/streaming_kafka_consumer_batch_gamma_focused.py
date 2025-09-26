"""
KafkaConsumer Batch-Γ-008 聚焦测试套件

专门为 kafka_consumer.py 设计的测试，目标是将其覆盖率从当前值提升至 ≥45%
覆盖关键功能：消息处理、错误处理、配置验证等
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncio
import sys
import os
import json

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.streaming.kafka_consumer import FootballKafkaConsumer
from src.streaming.stream_config import StreamConfig


class TestKafkaConsumerBatchGamma008Focused:
    """KafkaConsumer Batch-Γ-008 聚焦测试类"""

    @pytest.fixture
    def stream_config(self):
        """创建 StreamConfig 实例"""
        return StreamConfig()

    @pytest.fixture
    def kafka_consumer(self, stream_config):
        """创建 Kafka 消费者实例"""
        with patch('src.streaming.kafka_consumer.Consumer'):
            consumer = FootballKafkaConsumer(stream_config)
            return consumer

    def test_consumer_basic_properties(self, kafka_consumer):
        """测试消费者基本属性"""
        # 验证消费者基本属性设置正确
        assert kafka_consumer.config is not None
        assert kafka_consumer.consumer is not None
        assert kafka_consumer.running == False
        assert kafka_consumer.consumer_group_id is None
        assert hasattr(kafka_consumer, 'db_manager')
        assert hasattr(kafka_consumer, 'logger')

    def test_deserialize_message_success(self, kafka_consumer):
        """测试成功反序列化消息"""
        # 测试正常JSON消息
        test_data = {"match_id": 123, "home_team": "Team A", "away_team": "Team B"}
        message_value = json.dumps(test_data).encode('utf-8')

        result = kafka_consumer._deserialize_message(message_value)

        assert result == test_data

    def test_deserialize_message_invalid_json(self, kafka_consumer):
        """测试反序列化无效JSON消息"""
        # 测试无效JSON消息
        invalid_json = b'{"invalid": json}'

        # 应该抛出异常
        with pytest.raises(Exception):
            kafka_consumer._deserialize_message(invalid_json)

    def test_deserialize_message_unicode_error(self, kafka_consumer):
        """测试反序列化Unicode编码错误"""
        # 测试Unicode编码错误
        invalid_unicode = b'\xff\xfe'

        # 应该抛出异常
        with pytest.raises(Exception):
            kafka_consumer._deserialize_message(invalid_unicode)

    def test_subscribe_topics_success(self, kafka_consumer):
        """测试成功订阅主题"""
        topics = ['matches', 'odds']

        # Mock consumer已经存在
        kafka_consumer.consumer = Mock()

        # Mock config.is_valid_topic to return True for valid topics
        kafka_consumer.config.is_valid_topic = Mock(return_value=True)

        # 调用订阅方法
        kafka_consumer.subscribe_topics(topics)

        # 验证consumer.subscribe被调用
        kafka_consumer.consumer.subscribe.assert_called_once_with(topics)

    
    def test_subscribe_topics_empty_list(self, kafka_consumer):
        """测试订阅空主题列表"""
        topics = []

        # Mock consumer已经存在
        kafka_consumer.consumer = Mock()

        # 调用订阅方法 - 应该只记录错误而不抛出异常
        kafka_consumer.subscribe_topics(topics)

        # 验证consumer.subscribe没有被调用
        kafka_consumer.consumer.subscribe.assert_not_called()

    
    def test_close_consumer(self, kafka_consumer):
        """测试关闭消费者"""
        # 设置运行状态为True
        kafka_consumer.running = True

        # 调用关闭方法
        kafka_consumer.close()

        # 验证运行状态被设置为False
        assert kafka_consumer.running == False

    def test_context_manager_exit(self, kafka_consumer):
        """测试上下文管理器退出"""
        # 设置运行状态为True
        kafka_consumer.running = True

        # 模拟上下文管理器退出
        kafka_consumer.__del__()

        # 验证运行状态被设置为False
        assert kafka_consumer.running == False

    def test_create_consumer_when_already_exists(self, kafka_consumer):
        """测试当消费者已存在时创建消费者"""
        # 确保consumer已经存在
        assert kafka_consumer.consumer is not None

        # 获取原始consumer
        original_consumer = kafka_consumer.consumer

        # 调用创建方法
        kafka_consumer._create_consumer()

        # 验证consumer没有改变
        assert kafka_consumer.consumer == original_consumer

    @pytest.mark.asyncio
    async def test_process_match_message_success(self, kafka_consumer):
        """测试成功处理比赛消息"""
        # Mock数据库会话
        mock_session = AsyncMock()
        kafka_consumer.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        kafka_consumer.db_manager.get_async_session.return_value.__aexit__.return_value = None

        # 测试消息数据
        message_data = {
            "data": {
                "match_id": "123",
                "league_id": "456",
                "home_team": "Team A",
                "away_team": "Team B",
                "match_time": "2025-01-01T15:00:00"
            },
            "source": "kafka_stream"
        }

        result = await kafka_consumer._process_match_message(message_data)

        # 验证处理成功
        assert result is True

        # 验证数据库操作
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_odds_message_success(self, kafka_consumer):
        """测试成功处理赔率消息"""
        # Mock数据库会话
        mock_session = AsyncMock()
        kafka_consumer.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        kafka_consumer.db_manager.get_async_session.return_value.__aexit__.return_value = None

        # 测试消息数据
        message_data = {
            "data": {
                "match_id": "123",
                "home_odds": 2.5,
                "away_odds": 3.0,
                "draw_odds": 2.8
            },
            "source": "kafka_stream"
        }

        result = await kafka_consumer._process_odds_message(message_data)

        # 验证处理成功
        assert result is True

        # 验证数据库操作
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_scores_message_success(self, kafka_consumer):
        """测试成功处理比分消息"""
        # Mock数据库会话
        mock_session = AsyncMock()
        kafka_consumer.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        kafka_consumer.db_manager.get_async_session.return_value.__aexit__.return_value = None

        # 测试消息数据
        message_data = {
            "data": {
                "match_id": "123",
                "home_score": 2,
                "away_score": 1
            },
            "source": "kafka_stream"
        }

        result = await kafka_consumer._process_scores_message(message_data)

        # 验证处理成功
        assert result is True

        # 验证数据库操作
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_unknown_type(self, kafka_consumer):
        """测试处理未知类型消息"""
        # 测试未知类型消息
        message_data = {
            "data": {"some": "data"},
            "type": "unknown_type",
            "source": "kafka_stream"
        }

        result = await kafka_consumer._process_message_by_type(message_data, "unknown_type")

        # 验证处理失败
        assert result is False

    @pytest.mark.asyncio
    async def test_process_message_database_error(self, kafka_consumer):
        """测试处理消息时数据库错误"""
        # Mock数据库会话抛出异常
        mock_session = AsyncMock()
        mock_session.commit.side_effect = Exception("Database error")
        kafka_consumer.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        kafka_consumer.db_manager.get_async_session.return_value.__aexit__.return_value = None

        # 测试消息数据
        message_data = {
            "data": {"match_id": "123"},
            "source": "kafka_stream"
        }

        result = await kafka_consumer._process_match_message(message_data)

        # 验证处理失败
        assert result is False

    def test_consumer_configuration(self, kafka_consumer):
        """测试消费者配置"""
        # 验证配置正确设置
        assert kafka_consumer.config.kafka_config.bootstrap_servers is not None
        assert kafka_consumer.config.kafka_config.consumer_group_id is not None
        assert kafka_consumer.config.kafka_config.security_protocol is not None
        assert kafka_consumer.config.kafka_config.consumer_client_id is not None

    def test_consumer_error_handling(self, kafka_consumer):
        """测试消费者错误处理"""
        # 验证错误处理属性存在
        assert hasattr(kafka_consumer, 'logger')
        assert hasattr(kafka_consumer, 'db_manager')

        # 验证db_manager是DatabaseManager实例
        from src.database.connection import DatabaseManager
        assert isinstance(kafka_consumer.db_manager, DatabaseManager)

    def test_consumer_methods_exist(self, kafka_consumer):
        """测试消费者方法存在"""
        # 验证关键方法存在
        assert hasattr(kafka_consumer, 'subscribe_topics')
        assert hasattr(kafka_consumer, 'subscribe_all_topics')
        assert hasattr(kafka_consumer, 'close')
        assert hasattr(kafka_consumer, '_deserialize_message')
        assert hasattr(kafka_consumer, '_process_match_message')
        assert hasattr(kafka_consumer, '_process_odds_message')
        assert hasattr(kafka_consumer, '_process_scores_message')
        assert hasattr(kafka_consumer, '_process_message_by_type')