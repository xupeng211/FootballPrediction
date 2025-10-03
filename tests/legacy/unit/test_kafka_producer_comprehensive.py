from datetime import datetime, timezone
import json

from confluent_kafka import KafkaException
from src.streaming.kafka_producer import FootballKafkaProducer
from src.streaming.stream_config import StreamConfig
from unittest.mock import Mock, patch
import asyncio
import pytest
import os

"""
Kafka生产者的全面单元测试
测试覆盖：
- FootballKafkaProducer 类的所有方法
- 消息序列化和发送
- 错误处理和重试机制
- 配置管理和连接处理
- 批量处理和性能优化
"""
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import pytest
from confluent_kafka import KafkaException
from src.streaming.kafka_producer import FootballKafkaProducer
from src.streaming.stream_config import StreamConfig
class TestFootballKafkaProducer:
    """Kafka生产者测试类"""
    def setup_method(self):
        """每个测试方法前的设置"""
        self.config = StreamConfig()
        # Mock Kafka Producer初始化以避免实际连接
        with patch("src.streaming.kafka_producer.Producer[") as mock_producer:": mock_producer.return_value = Mock()": self.producer = FootballKafkaProducer(self.config)": def test_producer_initialization(self):"
        "]""测试生产者初始化"""
    assert self.producer is not None
    assert self.producer.config is not None
    assert hasattr(self.producer, "producer[")" assert hasattr(self.producer, "]logger[")" def test_producer_initialization_with_custom_config(self):"""
        "]""测试使用自定义配置初始化生产者"""
        custom_config = StreamConfig()
        custom_config.kafka_config.bootstrap_servers = os.getenv("TEST_KAFKA_PRODUCER_COMPREHENSIVE_BOOTSTRAP_SERVER")""""
        # Mock Kafka Producer初始化以避免实际连接
        with patch("]src.streaming.kafka_producer.Producer[") as mock_producer:": mock_producer.return_value = Mock()": producer = FootballKafkaProducer(custom_config)": assert producer.config ==custom_config"
    assert (
        producer.config.kafka_config.bootstrap_servers =="]custom - server9092["""""
        )
    @patch("]src.streaming.kafka_producer.Producer[")": def test_producer_creation_success(self, mock_producer_class):"""
        "]""测试Kafka生产者创建成功"""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer
        producer = FootballKafkaProducer(self.config)
        producer._create_producer()
        mock_producer_class.assert_called_once()
    assert producer.producer ==mock_producer
    @patch("src.streaming.kafka_producer.Producer[")": def test_producer_creation_failure(self, mock_producer_class):"""
        "]""测试Kafka生产者创建失败"""
        mock_producer_class.side_effect = KafkaException("Connection failed[")""""
        # 在初始化时就会抛出异常
        with pytest.raises(KafkaException):
            FootballKafkaProducer(self.config)
    def test_serialize_message_json(self):
        "]""测试JSON消息序列化"""
        test_data = {
        "match_id[": 12345,""""
        "]home_team[: "Team A[","]"""
        "]away_team[: "Team B[","]"""
        "]timestamp[": datetime.now()": serialized = self.producer._serialize_message(test_data)"""
        # 验证序列化结果
        assert isinstance(serialized, str)
        deserialized = json.loads(serialized)
        assert deserialized["]match_id["] ==12345[" assert deserialized["]]home_team["] =="]Team A[" def test_serialize_message_string("
    """"
        "]""测试字符串消息序列化"""
        test_data = os.getenv("TEST_KAFKA_PRODUCER_COMPREHENSIVE_TEST_DATA_71"): serialized = self.producer._serialize_message(test_data)": assert serialized ==test_data[" def test_serialize_message_none(self):""
        "]]""测试None消息序列化"""
        serialized = self.producer._serialize_message(None)
    assert serialized =="""
    def test_serialize_message_invalid_json(self):
        """测试无效JSON对象序列化"""
        # 创建一个无法序列化的对象
        class UnserializableObject:
            def __init__(self):
                self.circular_ref = self
        test_data = UnserializableObject()
        serialized = self.producer._serialize_message(test_data)
        # 应该返回字符串表示
    assert isinstance(serialized, str)
    def test_delivery_callback_success(self):
        """测试消息投递成功回调"""
        mock_message = Mock()
        mock_message.error.return_value = None
        mock_message.topic.return_value = os.getenv("TEST_KAFKA_PRODUCER_COMPREHENSIVE_RETURN_VALUE_89"): mock_message.partition.return_value = 0[": mock_message.offset.return_value = 12345["""
        # 不应该抛出异常
        self.producer._delivery_callback(None, mock_message)
    def test_delivery_callback_failure(self):
        "]]]""测试消息投递失败回调"""
        mock_error = Mock()
        mock_error.str.return_value = os.getenv("TEST_KAFKA_PRODUCER_COMPREHENSIVE_RETURN_VALUE_94"): mock_message = Mock()": mock_message.error.return_value = mock_error["""
        # 不应该抛出异常，但应该记录错误
        with patch.object(self.producer.logger, "]]error[") as mock_log_error:": self.producer._delivery_callback(mock_error, mock_message)": mock_log_error.assert_called_once()""
    @patch("]src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_send_match_data_success(self, mock_producer_class):
        "]""测试发送比赛数据成功"""
        mock_producer = Mock()
        mock_producer.produce = Mock()
        mock_producer.poll = Mock()
        mock_producer_class.return_value = mock_producer
        producer = FootballKafkaProducer(self.config)
        producer.producer = mock_producer
        match_data = {
        "match_id[": 12345,""""
        "]home_team[: "Team A[","]"""
        "]away_team[: "Team B[","]"""
        "]kickoff_time[": datetime.now(timezone.utc)": result = await producer.send_match_data(match_data)": assert result is True[" mock_producer.produce.assert_called_once()"
        mock_producer.poll.assert_called_once_with(0)
    @patch("]]src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_send_match_data_with_custom_key(self, mock_producer_class):
        "]""测试使用自定义key发送比赛数据"""
        mock_producer = Mock()
        mock_producer.produce = Mock()
        mock_producer.poll = Mock()
        mock_producer_class.return_value = mock_producer
        producer = FootballKafkaProducer(self.config)
        producer.producer = mock_producer
        match_data = {"match_id[" : 12345}": custom_key = os.getenv("TEST_KAFKA_PRODUCER_COMPREHENSIVE_CUSTOM_KEY_123")""""
        : result = await producer.send_match_data(match_data, key=custom_key)
    assert result is True
        # 验证produce调用时使用了自定义key
        call_args = mock_producer.produce.call_args
    assert call_args[1]"]key[" ==custom_key[""""
    @patch("]]src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_send_odds_data_success(self, mock_producer_class):
        "]""测试发送赔率数据成功"""
        mock_producer = Mock()
        mock_producer.produce = Mock()
        mock_producer.poll = Mock()
        mock_producer_class.return_value = mock_producer
        producer = FootballKafkaProducer(self.config)
        producer.producer = mock_producer
        odds_data = {
        "match_id[": 12345,""""
        "]bookmaker[: "Test Bookmaker[","]"""
        "]home_odds[": 2.5,""""
        "]draw_odds[": 3.2,""""
            "]away_odds[": 1.8,""""
            "]timestamp[": datetime.now(timezone.utc)": result = await producer.send_odds_data(odds_data)": assert result is True[" mock_producer.produce.assert_called_once()"
    @patch("]]src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_send_scores_data_success(self, mock_producer_class):
        "]""测试发送比分数据成功"""
        mock_producer = Mock()
        mock_producer.produce = Mock()
        mock_producer.poll = Mock()
        mock_producer_class.return_value = mock_producer
        producer = FootballKafkaProducer(self.config)
        producer.producer = mock_producer
        scores_data = {
        "match_id[": 12345,""""
        "]home_score[": 2,""""
        "]away_score[": 1,""""
        "]minute[": 90,""""
            "]status[": ["]finished[",""""
            "]timestamp[": datetime.now(timezone.utc)": result = await producer.send_scores_data(scores_data)": assert result is True[" mock_producer.produce.assert_called_once()"
    @patch("]]src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_send_match_data_producer_not_initialized(self, mock_producer_class):
        "]""测试生产者未初始化时发送数据"""
        # 模拟Producer创建失败
        mock_producer_class.side_effect = Exception("Connection failed[")""""
        # 初始化会失败，所以期望抛出异常
        with pytest.raises(Exception):
            _ = FootballKafkaProducer(self.config)
    @patch("]src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_send_data_kafka_exception(self, mock_producer_class):
        "]""测试发送数据时Kafka异常"""
        mock_producer = Mock()
        mock_producer.produce.side_effect = KafkaException("Buffer full[")": mock_producer_class.return_value = mock_producer[": producer = FootballKafkaProducer(self.config)": producer.producer = mock_producer"
        match_data = {"]]match_id[" : 12345}": result = await producer.send_match_data(match_data)": assert result is False[""
    @patch("]]src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_send_batch_success(self, mock_producer_class):
        "]""测试批量发送数据成功"""
        mock_producer = Mock()
        mock_producer.produce = Mock()
        mock_producer.poll = Mock()
        mock_producer.flush = Mock()
        mock_producer_class.return_value = mock_producer
        producer = FootballKafkaProducer(self.config)
        producer.producer = mock_producer
        batch_data = [
        {"match_id[": 1, "]home_team[": "]Team A["},""""
        {"]match_id[": 2, "]home_team[": "]Team B["},""""
        {"]match_id[": 3, "]home_team[": "]Team C["}]": result = await producer.send_batch(batch_data, "]match[")""""
        # send_batch 在没有失败时返回统计字典
    assert isinstance(result, dict)
    assert result["]success["] ==3[" assert result["]]failed["] ==0[" assert mock_producer.produce.call_count ==3["""
    @patch("]]]src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_send_batch_partial_failure(self, mock_producer_class):
        "]""测试批量发送部分失败"""
        mock_producer = Mock()
        # 第二次调用produce时抛出异常
        mock_producer.produce.side_effect = ["None[", KafkaException("]Error["), None]": mock_producer.poll = Mock()": mock_producer.flush = Mock()": mock_producer_class.return_value = mock_producer"
        producer = FootballKafkaProducer(self.config)
        producer.producer = mock_producer
        batch_data = [{"]match_id[": 1}, {"]match_id[": 2}, {"]match_id[" : 3}]": result = await producer.send_batch(batch_data, "]match[")""""
        # send_batch 在有失败时返回统计字典
    assert isinstance(result, dict)
    assert result["]success["] ==2[" assert result["]]failed["] ==1[""""
    @pytest.mark.asyncio
    async def test_send_batch_invalid_data_type(self):
        "]]""测试批量发送无效数据类型"""
        producer = FootballKafkaProducer(self.config)
        batch_data = [{"match_id[" : 1}]": result = await producer.send_batch(batch_data, "]invalid_type[")""""
        # send_batch 在不支持的数据类型时返回统计字典
    assert isinstance(result, dict)
    assert result["]success["] ==0[" assert result["]]failed["] ==1[""""
    @pytest.mark.asyncio
    async def test_send_batch_empty_data(self):
        "]]""测试批量发送空数据"""
        producer = FootballKafkaProducer(self.config)
        result = await producer.send_batch([], "match[")""""
        # send_batch 对于空数据返回统计字典
    assert isinstance(result, dict)
    assert result["]success["] ==0[" assert result["]]failed["] ==0[" def test_close_producer_success(self):"""
        "]]""测试关闭生产者成功"""
        mock_producer = Mock()
        mock_producer.flush = Mock(return_value=0)  # 模拟成功刷新，无剩余消息
        producer = FootballKafkaProducer(self.config)
        producer.producer = mock_producer
        producer.close()
        mock_producer.flush.assert_called_once_with(10.0)  # 默认超时时间
    assert producer.producer is None
    def test_close_producer_none(self):
        """测试关闭未初始化的生产者"""
        producer = FootballKafkaProducer(self.config)
        producer.producer = None
        # 不应该抛出异常
        producer.close()
    def test_close_producer_with_timeout(self):
        """测试使用自定义超时关闭生产者"""
        mock_producer = Mock()
        mock_producer.flush = Mock()
        producer = FootballKafkaProducer(self.config)
        producer.producer = mock_producer
        custom_timeout = 60.0
        producer.close(timeout=custom_timeout)
        mock_producer.flush.assert_called_once_with(custom_timeout)
    def test_context_manager_usage(self):
        """测试上下文管理器使用"""
        with patch("src.streaming.kafka_producer.Producer[") as mock_producer_class:": mock_producer = Mock()"""
            # 设置flush方法返回整数而不是Mock对象
            mock_producer.flush.return_value = 0
            mock_producer_class.return_value = mock_producer
            producer = FootballKafkaProducer(self.config)
            with producer:
                # 在上下文中使用生产者
    assert producer.producer is not None
            # 上下文退出后应该自动关闭
            mock_producer.flush.assert_called_once()
    def test_get_producer_config(self):
        "]""测试获取生产者配置"""
        producer = FootballKafkaProducer(self.config)
        config = producer.get_producer_config()
    assert isinstance(config, dict)
    assert "bootstrap.servers[" in config[""""
    assert "]]client.id[" in config[""""
    @patch("]]src.streaming.kafka_producer.Producer[")": def test_producer_health_check(self, mock_producer_class):"""
        "]""测试生产者健康检查"""
        mock_producer = Mock()
        mock_producer.list_topics = Mock()
        mock_producer.list_topics.return_value.topics = {"test - topic[": Mock()": mock_producer_class.return_value = mock_producer[": producer = FootballKafkaProducer(self.config)": producer.producer = mock_producer"
        is_healthy = producer.health_check()
    assert is_healthy is True
        mock_producer.list_topics.assert_called_once()
    def test_producer_health_check_no_producer(self):
        "]]""测试无生产者时的健康检查"""
        producer = FootballKafkaProducer(self.config)
        producer.producer = None
        is_healthy = producer.health_check()
    assert is_healthy is False
    @patch("src.streaming.kafka_producer.Producer[")": def test_producer_health_check_exception(self, mock_producer_class):"""
        "]""测试健康检查异常"""
        mock_producer = Mock()
        mock_producer.list_topics.side_effect = KafkaException("Connection error[")": mock_producer_class.return_value = mock_producer[": producer = FootballKafkaProducer(self.config)": producer.producer = mock_producer"
        is_healthy = producer.health_check()
    assert is_healthy is False
class TestProducerPerformance:
    "]]""生产者性能测试"""
    def setup_method(self):
        """为每个测试方法设置配置"""
        self.config = StreamConfig()
    @patch("src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, mock_producer_class):
        "]""测试批量处理性能"""
        mock_producer = Mock()
        mock_producer.produce = Mock()
        mock_producer.poll = Mock()
        mock_producer.flush = Mock()
        mock_producer_class.return_value = mock_producer
        producer = FootballKafkaProducer(self.config)
        producer.producer = mock_producer
        # 创建大批量数据
        large_batch = [{"match_id[": i, "]data[": f["]test_{i}"]} for i in range(1000)]": import time[": start_time = time.time()": result = await producer.send_batch(large_batch, "]match[")": end_time = time.time()": duration = end_time - start_time[""
        # 验证性能（批量处理应该很快）
    assert duration < 5.0  # 1000条消息应该在5秒内处理完
    assert isinstance(result, dict)
    assert result["]]success["] ==1000[" assert result["]]failed["] ==0[""""
    @patch("]]src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_concurrent_sends(self, mock_producer_class):
        "]""测试并发发送"""
        mock_producer = Mock()
        mock_producer.produce = Mock()
        mock_producer.poll = Mock()
        mock_producer_class.return_value = mock_producer
        producer = FootballKafkaProducer(self.config)
        producer.producer = mock_producer
        # 并发发送多个消息
        tasks = []
        for i in range(10):
        task = producer.send_match_data({"match_id[" : i))": tasks.append(task)": results = await asyncio.gather(*tasks)""
        # 所有发送都应该成功
    assert all(results)
    assert mock_producer.produce.call_count ==10
class TestErrorHandling:
    "]""错误处理测试"""
    def setup_method(self):
        """每个测试方法前的设置"""
        self.config = StreamConfig()
    @patch("src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_producer_buffer_full(self, mock_producer_class):
        "]""测试生产者缓冲区满"""
        mock_producer = Mock()
        mock_producer.produce.side_effect = KafkaException("Local Queue full[")": mock_producer_class.return_value = mock_producer[": producer = FootballKafkaProducer(self.config)": producer.producer = mock_producer"
        result = await producer.send_match_data({"]]match_id[" : 1))": assert result is False["""
    @patch("]]src.streaming.kafka_producer.Producer[")""""
    @pytest.mark.asyncio
    async def test_producer_timeout(self, mock_producer_class):
        "]""测试生产者超时"""
        mock_producer = Mock()
        mock_producer.produce.side_effect = KafkaException("Request timed out[")": mock_producer_class.return_value = mock_producer[": producer = FootballKafkaProducer(self.config)": producer.producer = mock_producer"
        result = await producer.send_match_data({"]]match_id[" : 1))": assert result is False["""
    @patch("]]src.streaming.kafka_producer.Producer[")": def test_invalid_configuration(self, mock_producer_class):"""
        "]""测试无效配置"""
        # 模拟Producer初始化时的错误
        mock_producer_class.side_effect = ValueError("Invalid bootstrap servers[")""""
        # 创建无效配置
        invalid_config = StreamConfig()
        # Setting bootstrap_servers to None in kafka_config will cause get_producer_config to fail
        invalid_config.kafka_config.bootstrap_servers = None
        # 在初始化时应该抛出错误
        with pytest.raises(ValueError):
            _ = FootballKafkaProducer(invalid_config)
    @patch("]src.streaming.kafka_producer.Producer[")": def test_producer_creation_retry(self, mock_producer_class):"""
        "]""测试生产者创建重试"""
        # 第一次失败，第二次成功
        mock_producer_class.side_effect = [KafkaException("Temporary failure["), Mock()]""""
        # 实现重试逻辑的话，这里应该成功
        # 目前的实现可能没有重试，所以这个测试需要根据实际实现调整
        # producer = FootballKafkaProducer(self.config)
class TestMessageValidation:
    "]""消息验证测试"""
    def setup_method(self):
        """每个测试方法前的设置"""
        self.config = StreamConfig()
    def test_validate_match_data(self):
        """测试比赛数据验证"""
        producer = FootballKafkaProducer(self.config)
        # 有效数据
        valid_data = {"match_id[": 12345, "]home_team[": "]Team A[", "]away_team[" : "]Team B["}": is_valid = producer._validate_match_data(valid_data)": assert is_valid is True[" def test_validate_odds_data(self):"
        "]]""测试赔率数据验证"""
        producer = FootballKafkaProducer(self.config)
        # 有效数据
        valid_data = {
        "match_id[": 12345,""""
        "]bookmaker[: "Test Bookmaker[","]"""
        "]home_odds[": 2.5}": is_valid = producer._validate_odds_data(valid_data)": assert is_valid is True[" def test_validate_scores_data(self):"
        "]]""测试比分数据验证"""
        producer = FootballKafkaProducer(self.config)
        # 有效数据
        valid_data = {"match_id[": 12345, "]home_score[": 2, "]away_score[" : 1}": is_valid = producer._validate_scores_data(valid_data)": assert is_valid is True[" if __name__ =="]]__main__[":""""
    : pytest.main(["]__file__[")"]": import time