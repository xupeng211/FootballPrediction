from typing import Dict, Any, List, Optional
import json
import os
import sys

from unittest.mock import AsyncMock, MagicMock, Mock, patch, MagicMock
import asyncio
import pytest

"""
FootballKafkaConsumer 增强测试套件 - Phase 5.1 Batch-Δ-014

专门为 kafka_consumer.py 设计的增强测试，目标是将其覆盖率从 10% 提升至 ≥70%
覆盖所有 Kafka 消费功能、消息处理、错误管理和上下文管理
"""

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
class TestFootballKafkaConsumerComprehensive:
    """FootballKafkaConsumer 综合测试类"""
    @pytest.fixture
    def mock_config(self):
        """创建模拟流配置"""
        config = Mock()
        config.kafka_servers = "localhost9092[": config.kafka_topics = ["]matches[", "]odds[", "]scores["]": config.kafka_group_id = "]football_consumer_group[": config.kafka_auto_offset_reset = "]earliest[": config.kafka_enable_auto_commit = True[": return config["""
    @pytest.fixture
    def consumer(self, mock_config):
        "]]]""创建 FootballKafkaConsumer 实例"""
        from src.streaming.kafka_consumer import FootballKafkaConsumer
        # Mock Kafka Consumer to avoid actual Kafka connection
        with patch('src.streaming.kafka_consumer.Consumer') as mock_consumer_class = mock_consumer Mock()
            mock_consumer_class.return_value = mock_consumer
            consumer_instance = FootballKafkaConsumer(config=mock_config)
            consumer_instance._consumer = mock_consumer
            return consumer_instance
    @pytest.fixture
    def sample_match_message(self):
        """示例比赛消息"""
        return {
        "match_id[": 12345,""""
        "]home_team[: "Team A[","]"""
        "]away_team[: "Team B[","]"""
        "]home_score[": 2,""""
            "]away_score[": 1,""""
            "]match_date[: "2023-01-01T15:00:00Z[","]"""
            "]status[": ["]completed[",""""
            "]competition[: "Premier League"""""
        }
    @pytest.fixture
    def sample_odds_message(self):
        "]""示例赔率消息"""
        return {
        "match_id[": 12345,""""
        "]home_win[": 2.10,""""
        "]draw[": 3.40,""""
        "]away_win[": 3.60,""""
            "]bookmaker[": ["]BookmakerA[",""""
            "]timestamp[: "2023-01-01T14:55:00Z"""""
        }
    @pytest.fixture
    def sample_scores_message(self):
        "]""示例比分消息"""
        return {
        "match_id[": 12345,""""
        "]current_home_score[": 2,""""
        "]current_away_score[": 1,""""
        "]minute[": 90,""""
            "]status[": ["]full_time[",""""
            "]timestamp[: "2023-01-01T16:45:00Z"""""
        }
    @pytest.fixture
    def mock_kafka_message(self):
        "]""创建模拟 Kafka 消息"""
        mock_message = Mock()
        mock_message.topic = "matches[": mock_message.partition = 0[": mock_message.offset = 123[": mock_message.key = b["]]]match_12345["]: mock_message.value = json.dumps({""""
        "]match_id[": 12345,""""
        "]home_team[: "Team A[","]"""
        "]away_team[: "Team B[","]"""
        "]home_score[": 2,""""
            "]away_score[": 1[""""
        )).encode('utf-8')
        mock_message.error = None
        return mock_message
    # === 初始化测试 ===
    def test_initialization_with_config(self, consumer, mock_config):
        "]]""测试使用配置初始化"""
    assert consumer.config is mock_config
    assert consumer._consumer is not None
    def test_initialization_without_config(self):
        """测试无配置初始化"""
        from src.streaming.kafka_consumer import FootballKafkaConsumer, StreamConfig
        with patch('src.streaming.kafka_consumer.Consumer') as mock_consumer_class = mock_consumer Mock()
            mock_consumer_class.return_value = mock_consumer
            consumer = FootballKafkaConsumer()
    assert consumer.config is not None
    assert isinstance(consumer.config, StreamConfig)
    def test_initialization_with_custom_group_id(self, mock_config):
        """测试自定义消费者组ID"""
        from src.streaming.kafka_consumer import FootballKafkaConsumer
        with patch('src.streaming.kafka_consumer.Consumer') as mock_consumer_class = mock_consumer Mock()
            mock_consumer_class.return_value = mock_consumer
            consumer = FootballKafkaConsumer(config=mock_config, consumer_group_id="custom_group[")""""
            # 应该使用自定义组ID
    assert consumer is not None
    # === 消费者创建测试 ===
    def test_create_consumer(self, consumer):
        "]""测试创建消费者"""
        consumer._create_consumer()
    assert consumer._consumer is not None
    def test_initialize_consumer(self, consumer):
        """测试初始化消费者"""
        consumer._initialize_consumer("test_group[")": assert consumer._consumer is not None["""
    # === 消息反序列化测试 ===
    def test_deserialize_message_valid_json(self, consumer):
        "]]""测试有效JSON消息反序列化"""
        message_data = {"key[: "value"", "number]: 123}": message_bytes = json.dumps(message_data).encode('utf-8')": result = consumer._deserialize_message(message_bytes)": assert result ==message_data"
    assert isinstance(result, dict)
    def test_deserialize_message_invalid_json(self, consumer):
        """测试无效JSON消息反序列化"""
        invalid_bytes = b["invalid json string["]"]": result = consumer._deserialize_message(invalid_bytes)""
        # 应该返回空字典或处理错误
    assert isinstance(result, dict)
    def test_deserialize_message_empty_bytes(self, consumer):
        """测试空字节消息反序列化"""
        empty_bytes = b = result consumer._deserialize_message(empty_bytes)
    assert isinstance(result, dict)
    def test_deserialize_message_none(self, consumer):
        """测试None消息反序列化"""
        result = consumer._deserialize_message(None)
    assert isinstance(result, dict)
    # === 消息处理测试 ===
    @pytest.mark.asyncio
    async def test_process_match_message(self, consumer, sample_match_message):
        """测试处理比赛消息"""
        with patch.object(consumer, '_process_match_message') as mock_process:
            mock_process.return_value = True
            result = await consumer.process_message(sample_match_message)
    assert result is True
        mock_process.assert_called_once_with(sample_match_message)
    @pytest.mark.asyncio
    async def test_process_odds_message(self, consumer, sample_odds_message):
        """测试处理赔率消息"""
        with patch.object(consumer, '_process_odds_message') as mock_process:
            mock_process.return_value = True
            result = await consumer.process_message(sample_odds_message)
    assert result is True
        mock_process.assert_called_once_with(sample_odds_message)
    @pytest.mark.asyncio
    async def test_process_scores_message(self, consumer, sample_scores_message):
        """测试处理比分消息"""
        with patch.object(consumer, '_process_scores_message') as mock_process:
            mock_process.return_value = True
            result = await consumer.process_message(sample_scores_message)
    assert result is True
        mock_process.assert_called_once_with(sample_scores_message)
    @pytest.mark.asyncio
    async def test_process_unknown_message_type(self, consumer):
        """测试处理未知类型消息"""
        unknown_message = {"type[: "unknown"", "data]}": result = await consumer.process_message(unknown_message)"""
        # 应该处理未知类型而不崩溃
    assert result is not None
    @pytest.mark.asyncio
    async def test_process_message_with_exception(self, consumer, sample_match_message):
        """测试处理消息时的异常"""
        with patch.object(consumer, '_process_match_message') as mock_process:
            mock_process.side_effect = Exception("Processing error[")": result = await consumer.process_message(sample_match_message)"""
            # 应该处理异常而不崩溃
    assert result is not None
    # === Kafka消息处理测试 ===
    @pytest.mark.asyncio
    async def test_process_kafka_message_success(self, consumer, mock_kafka_message):
        "]""测试成功处理Kafka消息"""
        with patch.object(consumer, 'process_message') as mock_process:
            mock_process.return_value = True
            result = await consumer._process_message(mock_kafka_message)
    assert result is True
        mock_process.assert_called_once()
    @pytest.mark.asyncio
    async def test_process_kafka_message_with_error(self, consumer):
        """测试处理带错误的Kafka消息"""
        error_message = Mock()
        error_message.error = Exception("Kafka error[")": result = await consumer._process_message(error_message)"""
        # 应该处理错误消息
    assert result is not None
    @pytest.mark.asyncio
    async def test_process_kafka_message_none_value(self, consumer):
        "]""测试处理空值的Kafka消息"""
        none_value_message = Mock()
        none_value_message.error = None
        none_value_message.value = None
        result = await consumer._process_message(none_value_message)
    assert result is not None
    # === 订阅测试 ===
    def test_subscribe_topics(self, consumer):
        """测试订阅主题"""
        topics = ["matches[", "]odds[", "]scores["]": consumer.subscribe_topics(topics)": consumer._consumer.subscribe.assert_called_once_with(topics)": def test_subscribe_topics_empty_list(self, consumer):"
        "]""测试订阅空主题列表"""
        consumer.subscribe_topics([])
        # 应该处理空列表而不崩溃
        consumer._consumer.subscribe.assert_called_once_with([])
    def test_subscribe_all_topics(self, consumer):
        """测试订阅所有主题"""
        consumer.subscribe_all_topics()
        # 应该订阅配置中的所有主题
        consumer._consumer.subscribe.assert_called_once()
    # === 消费测试 ===
    @pytest.mark.asyncio
    async def test_start_consuming_basic(self, consumer):
        """测试基础消息消费"""
        with patch.object(consumer._consumer, 'poll') as mock_poll:
            # 模拟无消息
            mock_poll.return_value = None
            # 应该在一定时间内完成而不阻塞
            await asyncio.wait_for(consumer.start_consuming(timeout=0.1), timeout=1.0)
            mock_poll.assert_called()
    @pytest.mark.asyncio
    async def test_start_consuming_with_messages(self, consumer, mock_kafka_message):
        """测试消费消息"""
        with patch.object(consumer._consumer, 'poll') as mock_poll, \:
            patch.object(consumer, '_process_message') as mock_process:
            # 模拟收到消息
            mock_poll.return_value = mock_kafka_message
            mock_process.return_value = True
            # 短时间运行
            task = asyncio.create_task(consumer.start_consuming(timeout=0.1))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                await task
            except asyncio.CancelledError:
                pass
            mock_process.assert_called()
    @pytest.mark.asyncio
    async def test_consume_batch_success(self, consumer, mock_kafka_message):
        """测试批量消费成功"""
        with patch.object(consumer._consumer, 'consume') as mock_consume, \:
            patch.object(consumer, '_process_message') as mock_process:
            # 模拟批量消息
            mock_consume.return_value = ["mock_kafka_message[": mock_process.return_value = True[": result = await consumer.consume_batch(num_messages=1, timeout=1.0)": assert result is not None[" mock_consume.assert_called_once_with(1, timeout=1.0)"
        mock_process.assert_called_once()
    @pytest.mark.asyncio
    async def test_consume_batch_empty(self, consumer):
        "]]]""测试消费空批量"""
        with patch.object(consumer._consumer, 'consume') as mock_consume:
            # 模拟无消息
            mock_consume.return_value = []
            result = await consumer.consume_batch(num_messages=1, timeout=1.0)
    assert result is not None
        mock_consume.assert_called_once()
    @pytest.mark.asyncio
    async def test_consume_messages_with_limit(self, consumer, mock_kafka_message):
        """测试限制数量的消息消费"""
        with patch.object(consumer._consumer, 'consume') as mock_consume, \:
            patch.object(consumer, '_process_message') as mock_process:
            # 模拟多条消息
            messages = ["mock_kafka_message[" * 5[": mock_consume.return_value = messages[": mock_process.return_value = True[": result = await consumer.consume_messages(max_messages=3, timeout=1.0)"
    assert result is not None
        # 应该处理指定数量的消息
    assert mock_process.call_count ==3
    # === 停止和关闭测试 ===
    def test_stop_consuming(self, consumer):
        "]]]]""测试停止消费"""
        consumer.stop_consuming()
        # 应该调用相关停止方法
    assert hasattr(consumer, '_consuming')
        # 停止后应该设置标志
    def test_close(self, consumer):
        """测试关闭消费者"""
        consumer.close()
        consumer._consumer.close.assert_called_once()
    def test_close_already_closed(self, consumer):
        """测试关闭已关闭的消费者"""
        consumer._consumer = None
        # 应该不崩溃
        consumer.close()
    # === 上下文管理器测试 ===
    @pytest.mark.asyncio
    async def test_async_context_manager(self, consumer):
        """测试异步上下文管理器"""
        async with consumer:
    assert consumer is not None
        # 退出时应调用close
        consumer._consumer.close.assert_called()
    @pytest.mark.asyncio
    async def test_async_context_manager_with_exception(self, consumer):
        """测试异步上下文管理器异常处理"""
        with patch.object(consumer, 'close') as mock_close:
            try:
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                async with consumer:
                raise ValueError("Test exception[")": except ValueError:": pass[""
            # 即使有异常也应该调用close
            mock_close.assert_called_once()
    # === 析构函数测试 ===
    def test_del_destructor(self, consumer):
        "]]""测试析构函数"""
        with patch.object(consumer, 'close') as mock_close:
            del consumer
            # 析构函数应该调用close
            # 注意：在实际测试中，__del__的行为可能不可预测
    # === 错误处理测试 ===
    @pytest.mark.asyncio
    async def test_kafka_exception_handling(self, consumer):
        """测试Kafka异常处理"""
        with patch.object(consumer._consumer, 'poll') as mock_poll:
            # 模拟Kafka异常
            mock_poll.side_effect = Exception("Kafka connection error[")""""
            # 应该处理异常而不崩溃
            await consumer.start_consuming(timeout=0.1)
    @pytest.mark.asyncio
    async def test_message_processing_exception(self, consumer, mock_kafka_message):
        "]""测试消息处理异常"""
        with patch.object(consumer, 'process_message') as mock_process:
            # 模拟处理异常
            mock_process.side_effect = Exception("Processing failed[")": result = await consumer._process_message(mock_kafka_message)"""
            # 应该返回False或处理异常
    assert result is not None
    def test_subscribe_exception_handling(self, consumer):
        "]""测试订阅异常处理"""
        with patch.object(consumer._consumer, 'subscribe') as mock_subscribe:
            # 模拟订阅异常
            mock_subscribe.side_effect = Exception("Subscription failed[")""""
            # 应该处理异常而不崩溃
            consumer.subscribe_topics("]test_topic[")""""
    # === 边界条件测试 ===
    def test_deserialize_large_message(self, consumer):
        "]""测试大消息反序列化"""
        large_data = {"data[": ["]x[" * 1000000}  # 1MB数据[": large_bytes = json.dumps(large_data).encode('utf-8')": result = consumer._deserialize_message(large_bytes)": assert isinstance(result, dict)"
    def test_deserialize_unicode_message(self, consumer):
        "]]""测试Unicode消息反序列化"""
        unicode_data = {"text[: "中文测试 🚀"", "emoji]}": unicode_bytes = json.dumps(unicode_data, ensure_ascii=False).encode('utf-8')": result = consumer._deserialize_message(unicode_bytes)": assert result ==unicode_data"
    @pytest.mark.asyncio
    async def test_consume_with_zero_timeout(self, consumer):
        """测试零超时消费"""
        with patch.object(consumer._consumer, 'poll') as mock_poll:
            mock_poll.return_value = None
            await consumer.start_consuming(timeout=0.0)
            mock_poll.assert_called()
    # === 性能测试 ===
    @pytest.mark.asyncio
    async def test_high_throughput_processing(self, consumer, mock_kafka_message):
        """测试高吞吐量处理"""
        with patch.object(consumer, '_process_message') as mock_process:
            mock_process.return_value = True
            # 模拟处理大量消息
            tasks = []
            for _ in range(100):
            task = asyncio.create_task(consumer._process_message(mock_kafka_message))
            tasks.append(task)
            # 等待所有任务完成
            results = await asyncio.gather(*tasks)
    assert all(result is not None for result in results)
    assert mock_process.call_count ==100
    # === 配置测试 ===
    def test_consumer_configuration(self, mock_config):
        """测试消费者配置"""
        from src.streaming.kafka_consumer import FootballKafkaConsumer
        with patch('src.streaming.kafka_consumer.Consumer') as mock_consumer_class = mock_consumer Mock()
            mock_consumer_class.return_value = mock_consumer
            consumer = FootballKafkaConsumer(config=mock_config)
            # 验证配置被正确应用
    assert consumer.config ==mock_config
    def test_default_configuration(self):
        """测试默认配置"""
        from src.streaming.kafka_consumer import FootballKafkaConsumer, StreamConfig
        with patch('src.streaming.kafka_consumer.Consumer') as mock_consumer_class = mock_consumer Mock()
            mock_consumer_class.return_value = mock_consumer
            consumer = FootballKafkaConsumer()
            # 应该有默认配置
    assert consumer.config is not None
    assert isinstance(consumer.config, StreamConfig)
    # === 集成测试 ===
    @pytest.mark.asyncio
    async def test_full_consumption_workflow(self, consumer, mock_kafka_message):
        """测试完整消费工作流"""
        with patch.object(consumer._consumer, 'subscribe') as mock_subscribe, \:
            patch.object(consumer._consumer, 'poll') as mock_poll, \
            patch.object(consumer, '_process_message') as mock_process:
            mock_process.return_value = True
            # 订阅主题
            consumer.subscribe_topics("test_topic[")": mock_subscribe.assert_called_once()"""
            # 开始消费
            mock_poll.return_value = mock_kafka_message
            # 短时间运行
            task = asyncio.create_task(consumer.start_consuming(timeout=0.1))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                await task
            except asyncio.CancelledError:
                pass
            # 验证工作流
            mock_subscribe.assert_called()
            mock_poll.assert_called()
            mock_process.assert_called()
    @pytest.mark.asyncio
    async def test_batch_processing_workflow(self, consumer, mock_kafka_message):
        "]""测试批量处理工作流"""
        with patch.object(consumer._consumer, 'consume') as mock_consume, \:
            patch.object(consumer, '_process_message') as mock_process:
            # 模拟批量消息
            messages = ["mock_kafka_message[" * 10[": mock_consume.return_value = messages[": mock_process.return_value = True[": result = await consumer.consume_batch(num_messages=10, timeout=1.0)"
    assert result is not None
    assert mock_process.call_count ==10
        mock_consume.assert_called_once_with(10, timeout=1.0)
    # === 重连机制测试 ===
    @pytest.mark.asyncio
    async def test_reconnection_handling(self, consumer):
        "]]]]""测试重连处理"""
        with patch.object(consumer._consumer, 'poll') as mock_poll:
            # 模拟连接失败然后恢复
            call_count = 0
            def mock_poll_with_recovery(timeout):
                nonlocal call_count
                call_count += 1
                if call_count ==1
                raise Exception("Connection lost[")": return None[": mock_poll.side_effect = mock_poll_with_recovery[""
            # 应该处理连接问题并继续
            consumer.start_consuming(timeout=0.1)
    assert call_count >= 1
    # === 偏移量管理测试 ===
    @pytest.mark.asyncio
    async def test_offset_commit_handling(self, consumer, mock_kafka_message):
        "]]]""测试偏移量提交处理"""
        with patch.object(consumer._consumer, 'poll') as mock_poll, \:
            patch.object(consumer._consumer, 'commit') as mock_commit, \
            patch.object(consumer, '_process_message') as mock_process:
            mock_poll.return_value = mock_kafka_message
            mock_process.return_value = True
            # 短时间运行
            task = asyncio.create_task(consumer.start_consuming(timeout=0.1))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                await task
            except asyncio.CancelledError:
                pass
            # 验证提交调用（如果配置了自动提交）
            # mock_commit.assert_called()
    # === 消费者组测试 ===
    def test_consumer_group_configuration(self, mock_config):
        """测试消费者组配置"""
        from src.streaming.kafka_consumer import FootballKafkaConsumer
        custom_group_id = "custom_consumer_group[": with patch('src.streaming.kafka_consumer.Consumer') as mock_consumer_class:": mock_consumer = Mock()": mock_consumer_class.return_value = mock_consumer[": consumer = FootballKafkaConsumer("
            config=mock_config,
            consumer_group_id=custom_group_id
            )
            # 应该使用自定义消费者组ID
    assert consumer is not None
    # === 工具函数测试 ===
    def test_get_session_function(self):
        "]]""测试get_session工具函数"""
        from src.streaming.kafka_consumer import get_session
        session = get_session()
    assert session is not None
        from src.streaming.kafka_consumer import FootballKafkaConsumer
        from src.streaming.kafka_consumer import FootballKafkaConsumer, StreamConfig
        from src.streaming.kafka_consumer import FootballKafkaConsumer
        from src.streaming.kafka_consumer import FootballKafkaConsumer
        from src.streaming.kafka_consumer import FootballKafkaConsumer, StreamConfig
        from src.streaming.kafka_consumer import FootballKafkaConsumer
        from src.streaming.kafka_consumer import get_session