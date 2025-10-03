import os

from dataclasses import is_dataclass
from src.streaming.stream_config import KafkaConfig, TopicConfig, StreamConfig
from unittest.mock import patch
import pytest

"""
流式处理配置管理测试套件

覆盖src/streaming/stream_config.py的所有功能：
- KafkaConfig 数据类
- TopicConfig 数据类
- StreamConfig 配置管理器

目标：实现100%覆盖率
"""

class TestKafkaConfig:
    """KafkaConfig测试类"""
    def test_kafka_config_creation_default(self):
        """测试使用默认值创建KafkaConfig"""
        config = KafkaConfig()
        # 验证连接配置
        assert config.bootstrap_servers =="localhost9092[" assert config.security_protocol =="]PLAINTEXT["""""
        # 验证生产者配置
        assert config.producer_client_id =="]football-prediction-producer[" assert config.producer_acks =="]all[" assert config.producer_retries ==3[""""
        assert config.producer_retry_backoff_ms ==1000
        assert config.producer_linger_ms ==5
        assert config.producer_batch_size ==16384
        # 验证消费者配置
        assert config.consumer_group_id =="]]football-prediction-consumers[" assert config.consumer_client_id =="]football-prediction-consumer[" assert config.consumer_auto_offset_reset =="]latest[" assert config.consumer_enable_auto_commit is True[""""
        assert config.consumer_auto_commit_interval_ms ==5000
        assert config.consumer_max_poll_records ==500
        # 验证序列化配置
        assert config.key_serializer =="]]string[" assert config.value_serializer =="]json[" def test_kafka_config_creation_custom("
    """"
        "]""测试使用自定义值创建KafkaConfig"""
        config = KafkaConfig(
            bootstrap_servers = "kafka-server9092[",": security_protocol="]SASL_SSL[",": producer_client_id="]custom-producer[",": producer_acks="]1[",": producer_retries=5,": consumer_group_id="]custom-group[",": consumer_client_id="]custom-consumer[",": consumer_auto_offset_reset="]earliest[",": consumer_enable_auto_commit=False,": key_serializer="]avro[",": value_serializer="]avro[")": assert config.bootstrap_servers =="]kafka-server9092[" assert config.security_protocol =="]SASL_SSL[" assert config.producer_client_id =="]custom-producer[" assert config.producer_acks =="]1[" assert config.producer_retries ==5[""""
        assert config.consumer_group_id =="]]custom-group[" assert config.consumer_client_id =="]custom-consumer[" assert config.consumer_auto_offset_reset =="]earliest[" assert config.consumer_enable_auto_commit is False[""""
        assert config.key_serializer =="]]avro[" assert config.value_serializer =="]avro[" def test_kafka_config_dataclass_properties("
    """"
        "]""测试KafkaConfig的dataclass属性"""
        # 验证是dataclass
        assert is_dataclass(KafkaConfig)
        # 验证字段
        config = KafkaConfig()
        assert hasattr(config, "bootstrap_servers[")" assert hasattr(config, "]security_protocol[")" assert hasattr(config, "]producer_client_id[")" assert hasattr(config, "]consumer_group_id[")" assert hasattr(config, "]key_serializer[")" assert hasattr(config, "]value_serializer[")" def test_kafka_config_boundary_values(self):"""
        "]""测试KafkaConfig边界值"""
        # 测试边界数值
        config = KafkaConfig(
            producer_retries=0,  # 最小重试次数
            producer_retry_backoff_ms=0,  # 最小退避时间
            producer_linger_ms=0,  # 最小延迟
            producer_batch_size=1,  # 最小批量大小
            consumer_max_poll_records=1,  # 最小轮询记录数
            consumer_auto_commit_interval_ms=1,  # 最小提交间隔
        )
        assert config.producer_retries ==0
        assert config.producer_retry_backoff_ms ==0
        assert config.producer_linger_ms ==0
        assert config.producer_batch_size ==1
        assert config.consumer_max_poll_records ==1
        assert config.consumer_auto_commit_interval_ms ==1
    def test_kafka_config_large_values(self):
        """测试KafkaConfig大数值"""
        config = KafkaConfig(
            producer_retries=999999,
            producer_retry_backoff_ms=999999999,
            producer_linger_ms=999999999,
            producer_batch_size=999999999,
            consumer_max_poll_records=999999999,
            consumer_auto_commit_interval_ms=999999999)
        assert config.producer_retries ==999999
        assert config.producer_retry_backoff_ms ==999999999
        assert config.producer_linger_ms ==999999999
        assert config.producer_batch_size ==999999999
class TestTopicConfig:
    """TopicConfig测试类"""
    def test_topic_config_creation_default(self):
        """测试使用默认值创建TopicConfig"""
        config = TopicConfig(name="test-topic[")": assert config.name =="]test-topic[" assert config.partitions ==3[""""
        assert config.replication_factor ==1
        assert config.cleanup_policy =="]]delete[" assert config.retention_ms ==604800000  # 7天[""""
        assert config.segment_ms ==86400000  # 1天
    def test_topic_config_creation_custom(self):
        "]]""测试使用自定义值创建TopicConfig"""
        config = TopicConfig(
            name="custom-topic[",": partitions=10,": replication_factor=3,": cleanup_policy="]compact[",": retention_ms=3600000,  # 1小时[": segment_ms=1800000,  # 30分钟[""
        )
        assert config.name =="]]]custom-topic[" assert config.partitions ==10[""""
        assert config.replication_factor ==3
        assert config.cleanup_policy =="]]compact[" assert config.retention_ms ==3600000[""""
        assert config.segment_ms ==1800000
    def test_topic_config_dataclass_properties(self):
        "]]""测试TopicConfig的dataclass属性"""
        # 验证是dataclass
        assert is_dataclass(TopicConfig)
        # 验证字段
        config = TopicConfig(name="test[")": assert hasattr(config, "]name[")" assert hasattr(config, "]partitions[")" assert hasattr(config, "]replication_factor[")" assert hasattr(config, "]cleanup_policy[")" assert hasattr(config, "]retention_ms[")" assert hasattr(config, "]segment_ms[")" def test_topic_config_boundary_values(self):"""
        "]""测试TopicConfig边界值"""
        # 测试最小有效值
        config = TopicConfig(
            name="test[",": partitions=1,  # 最小分区数[": replication_factor=1,  # 最小副本因子[": retention_ms=1,  # 最小保留时间"
            segment_ms=1,  # 最小段大小
        )
        assert config.partitions ==1
        assert config.replication_factor ==1
        assert config.retention_ms ==1
        assert config.segment_ms ==1
    def test_topic_config_retention_time_values(self):
        "]]]""测试不同保留时间配置"""
        test_cases = [
            ("1 hour[", 3600000),""""
            ("]6 hours[", 21600000),""""
            ("]12 hours[", 43200000),""""
            ("]1 day[", 86400000),""""
            ("]7 days[", 604800000),""""
            ("]30 days[", 2592000000)]": for name, retention_ms in test_cases = config TopicConfig(name=f["]test-{name)"], retention_ms=retention_ms)": assert config.retention_ms ==retention_ms[" def test_topic_config_cleanup_policies(self):""
        "]""测试不同的清理策略"""
        policies = ["delete[", "]compact[", "]compact,delete["]": for policy in policies = config TopicConfig(name=f["]test-{policy)"], cleanup_policy=policy)": assert config.cleanup_policy ==policy[" class TestStreamConfig:""
    "]""StreamConfig测试类"""
    @pytest.fixture
    def mock_env_vars(self):
        """模拟环境变量"""
        env_vars = {
            "KAFKA_BOOTSTRAP_SERVERS[: "kafka-prod:9092[","]"""
            "]KAFKA_SECURITY_PROTOCOL[": ["]SASL_SSL[",""""
            "]KAFKA_PRODUCER_CLIENT_ID[: "prod-producer[","]"""
            "]KAFKA_PRODUCER_ACKS[: "1[","]"""
            "]KAFKA_PRODUCER_RETRIES[: "5[","]"""
            "]KAFKA_CONSUMER_GROUP_ID[: "prod-consumers[","]"""
            "]KAFKA_CONSUMER_CLIENT_ID[: "prod-consumer[","]"""
            "]KAFKA_CONSUMER_AUTO_OFFSET_RESET[": ["]earliest["}": return env_vars[": def test_stream_config_init_default(self):""
        "]]""测试StreamConfig默认初始化"""
        with patch.dict(os.environ, {), clear = True)
            config = StreamConfig()
            # 验证Kafka配置加载
            assert config.kafka_config.bootstrap_servers =="localhost9092[" assert config.kafka_config.security_protocol =="]PLAINTEXT[" assert (""""
                config.kafka_config.producer_client_id =="]football-prediction-producer["""""
            )
            assert (
                config.kafka_config.consumer_group_id =="]football-prediction-consumers["""""
            )
            # 验证Topics初始化
            assert len(config.topics) ==4
            assert "]matches-stream[" in config.topics[""""
            assert "]]odds-stream[" in config.topics[""""
            assert "]]scores-stream[" in config.topics[""""
            assert "]]processed-data-stream[" in config.topics[""""
    def test_stream_config_init_with_env_vars(self, mock_env_vars):
        "]]""测试使用环境变量初始化StreamConfig"""
        with patch.dict(os.environ, mock_env_vars):
            config = StreamConfig()
            # 验证环境变量生效
            assert config.kafka_config.bootstrap_servers =="kafka-prod9092[" assert config.kafka_config.security_protocol =="]SASL_SSL[" assert config.kafka_config.producer_client_id =="]prod-producer[" assert config.kafka_config.producer_acks =="]1[" assert config.kafka_config.producer_retries ==5[""""
            assert config.kafka_config.consumer_group_id =="]]prod-consumers[" assert config.kafka_config.consumer_client_id =="]prod-consumer[" assert config.kafka_config.consumer_auto_offset_reset =="]earliest[" def test_load_kafka_config_with_env_vars("
    """"
        "]""测试_load_kafka_config方法"""
        with patch.dict(os.environ, mock_env_vars):
            config = StreamConfig()
            kafka_config = config._load_kafka_config()
            assert isinstance(kafka_config, KafkaConfig)
            assert kafka_config.bootstrap_servers =="kafka-prod9092[" assert kafka_config.security_protocol =="]SASL_SSL[" assert kafka_config.producer_retries ==5[""""
    def test_init_topics_default(self):
        "]]""测试_init_topics方法默认配置"""
        with patch.dict(os.environ, {), clear = True)
            config = StreamConfig()
            topics = config._init_topics()
            assert len(topics) ==4
            # 验证matches-stream配置
            matches_topic = topics["matches-stream["]"]": assert matches_topic.name =="matches-stream[" assert matches_topic.partitions ==3[""""
            assert matches_topic.retention_ms ==86400000  # 1天
            # 验证odds-stream配置
            odds_topic = topics["]]odds-stream["]: assert odds_topic.name =="]odds-stream[" assert odds_topic.partitions ==6  # 赔率数据量大，更多分区[""""
            assert odds_topic.retention_ms ==43200000  # 12小时
            # 验证scores-stream配置
            scores_topic = topics["]]scores-stream["]: assert scores_topic.name =="]scores-stream[" assert scores_topic.partitions ==3[""""
            assert scores_topic.retention_ms ==21600000  # 6小时
            # 验证processed-data-stream配置
            processed_topic = topics["]]processed-data-stream["]: assert processed_topic.name =="]processed-data-stream[" assert processed_topic.partitions ==3[""""
            assert processed_topic.retention_ms ==604800000  # 7天
    def test_get_producer_config(self):
        "]]""测试get_producer_config方法"""
        config = StreamConfig()
        producer_config = config.get_producer_config()
        expected_keys = [
            "bootstrap.servers[",""""
            "]security.protocol[",""""
            "]client.id[",""""
            "]acks[",""""
            "]retries[",""""
            "]retry.backoff.ms[",""""
            "]linger.ms[",""""
            "]batch.size[",""""
            "]compression.type[",""""
            "]max.in.flight.requests.per.connection["]": for key in expected_keys:": assert key in producer_config[""
        # 验证配置值转换
        assert (
            producer_config["]]bootstrap.servers["]""""
            ==config.kafka_config.bootstrap_servers
        )
        assert (
            producer_config["]security.protocol["]""""
            ==config.kafka_config.security_protocol
        )
        assert producer_config["]client.id["] ==config.kafka_config.producer_client_id[" assert producer_config["]]acks["] ==config.kafka_config.producer_acks[" assert producer_config["]]compression.type["] =="]gzip[" assert producer_config["]max.in.flight.requests.per.connection["] ==1[" def test_get_consumer_config_default(self):"""
        "]]""测试get_consumer_config方法默认值"""
        config = StreamConfig()
        consumer_config = config.get_consumer_config()
        expected_keys = [
            "bootstrap.servers[",""""
            "]security.protocol[",""""
            "]client.id[",""""
            "]group.id[",""""
            "]auto.offset.reset[",""""
            "]enable.auto.commit[",""""
            "]auto.commit.interval.ms[",""""
            "]max.poll.interval.ms[",""""
            "]session.timeout.ms[",""""
            "]heartbeat.interval.ms["]": for key in expected_keys:": assert key in consumer_config[""
        # 验证配置值
        assert consumer_config["]]group.id["] ==config.kafka_config.consumer_group_id[" assert ("""
            consumer_config["]]auto.offset.reset["]""""
            ==config.kafka_config.consumer_auto_offset_reset
        )
        assert (
            consumer_config["]enable.auto.commit["]""""
            ==config.kafka_config.consumer_enable_auto_commit
        )
        assert consumer_config["]max.poll.interval.ms["] ==300000[" def test_get_consumer_config_custom_group(self):"""
        "]]""测试get_consumer_config方法自定义group"""
        config = StreamConfig()
        custom_group = "custom-test-group[": consumer_config = config.get_consumer_config(consumer_group_id=custom_group)": assert consumer_config["]group.id["] ==custom_group[" def test_get_topic_config_existing(self):"""
        "]]""测试get_topic_config方法 - 存在的topic"""
        config = StreamConfig()
        topic_config = config.get_topic_config("matches-stream[")": assert topic_config is not None[" assert topic_config.name =="]]matches-stream[" assert topic_config.partitions ==3[""""
    def test_get_topic_config_non_existing(self):
        "]]""测试get_topic_config方法 - 不存在的topic"""
        config = StreamConfig()
        topic_config = config.get_topic_config("non-existing-topic[")": assert topic_config is None[" def test_get_all_topics(self):""
        "]]""测试get_all_topics方法"""
        config = StreamConfig()
        all_topics = config.get_all_topics()
        assert isinstance(all_topics, list)
        assert len(all_topics) ==4
        assert "matches-stream[" in all_topics[""""
        assert "]]odds-stream[" in all_topics[""""
        assert "]]scores-stream[" in all_topics[""""
        assert "]]processed-data-stream[" in all_topics[""""
    def test_is_valid_topic_true(self):
        "]]""测试is_valid_topic方法 - 有效topic"""
        config = StreamConfig()
        assert config.is_valid_topic("matches-stream[") is True[" assert config.is_valid_topic("]]odds-stream[") is True[" assert config.is_valid_topic("]]scores-stream[") is True[" assert config.is_valid_topic("]]processed-data-stream[") is True[" def test_is_valid_topic_false(self):"""
        "]]""测试is_valid_topic方法 - 无效topic"""
        config = StreamConfig()
        assert config.is_valid_topic("invalid-topic[") is False[" assert config.is_valid_topic( ) is False["""
        assert config.is_valid_topic(None) is False
        assert config.is_valid_topic("]]]matches-stream-extra[") is False[" def test_topics_direct_modification(self):"""
        "]]""验证topics字典可以直接修改（实际行为测试）"""
        config = StreamConfig()
        config.get_all_topics()
        # 直接修改topics字典（这是允许的）
        config.topics["new-topic["] = TopicConfig(name="]new-topic[")""""
        # 验证配置确实被修改了
        assert len(config.get_all_topics()) ==5
        assert "]new-topic[" in config.get_all_topics()""""
        assert config.get_topic_config("]new-topic[") is not None[" class TestStreamConfigIntegration:"""
    "]]""StreamConfig集成测试"""
    def test_config_consistency(self):
        """测试配置一致性"""
        config = StreamConfig()
        # 验证生产者和消费者配置使用相同的服务器
        producer_config = config.get_producer_config()
        consumer_config = config.get_consumer_config()
        assert (
            producer_config["bootstrap.servers["] ==consumer_config["]bootstrap.servers["]"]"""
        )
        assert (
            producer_config["security.protocol["] ==consumer_config["]security.protocol["]"]"""
        )
    def test_environment_variable_priority(self):
        """测试环境变量优先级"""
        # 设置环境变量
        env_vars = {"KAFKA_BOOTSTRAP_SERVERS[: "env-kafka9092["}"]": with patch.dict(os.environ, env_vars):": config = StreamConfig()"
            # 验证环境变量覆盖默认值
            assert config.kafka_config.bootstrap_servers =="]env-kafka9092[" def test_topic_config_completeness("
    """"
        "]""测试Topic配置完整性"""
        config = StreamConfig()
        for topic_name in config.get_all_topics():
            topic_config = config.get_topic_config(topic_name)
            # 验证必要字段
            assert topic_config.name is not None
            assert topic_config.partitions > 0
            assert topic_config.replication_factor > 0
            assert topic_config.cleanup_policy in [
                "delete[",""""
                "]compact[",""""
                "]compact,delete["]": assert topic_config.retention_ms > 0[" assert topic_config.segment_ms > 0[""
    def test_config_serialization_compatibility(self):
        "]]]""测试配置序列化兼容性"""
        config = StreamConfig()
        # 测试KafkaConfig序列化
        kafka_dict = {
            "bootstrap_servers[": config.kafka_config.bootstrap_servers,""""
            "]security_protocol[": config.kafka_config.security_protocol,""""
            "]producer_client_id[": config.kafka_config.producer_client_id}": assert isinstance(kafka_dict, dict)"""
        # 测试TopicConfig序列化
        for topic_name in config.get_all_topics():
            topic_config = config.get_topic_config(topic_name)
            topic_dict = {
                "]name[": topic_config.name,""""
                "]partitions[": topic_config.partitions,""""
                "]replication_factor[": topic_config.replication_factor}": assert isinstance(topic_dict, dict)" class TestStreamConfigEdgeCases:""
    "]""StreamConfig边界情况测试"""
    def test_empty_environment_variables(self):
        """测试空环境变量"""
        with patch.dict(os.environ, {), clear = True)
            config = StreamConfig()
            # 应该使用默认值
            assert config.kafka_config.bootstrap_servers =="localhost9092[" assert (""""
                config.kafka_config.consumer_group_id =="]football-prediction-consumers["""""
            )
    def test_invalid_environment_variable_types(self):
        "]""测试无效环境变量类型"""
        # 设置无效的数值类型环境变量
        env_vars = {
            "KAFKA_PRODUCER_RETRIES[": ["]invalid_number[",  # 应该是数字[""""
        }
        with patch.dict(os.environ, env_vars):
            # 应该抛出ValueError
            with pytest.raises(ValueError):
                StreamConfig()
    def test_special_characters_in_config(self):
        "]]""测试配置中的特殊字符"""
        StreamConfig()
        # 测试特殊字符在字符串字段中
        special_chars_config = KafkaConfig(
            bootstrap_servers = "kafka:9092,another-kafka9093[",": security_protocol="]SASL_SSL[",": producer_client_id="]producer@test#123[")": assert "]," in special_chars_config.bootstrap_servers[""""
        assert "]#" in special_chars_config.producer_client_id[""""
    def test_unicode_config_values(self):
        "]""测试Unicode配置值"""
        StreamConfig()
        # 测试Unicode支持
        unicode_config = TopicConfig(
            name="测试主题-中文-🚀",": partitions=5)": assert "测试主题[" in unicode_config.name[""""
        assert "]]🚀" in unicode_config.name[""""
    def test_large_configuration_values(self):
        "]""测试大配置值"""
        StreamConfig()
        # 测试大数值配置
        large_config = TopicConfig(
            name="large-topic[",": partitions=1000,  # 大分区数[": retention_ms=999999999999,  # 大保留时间[""
        )
        assert large_config.partitions ==1000
        assert large_config.retention_ms ==999999999999
if __name__ =="]]]__main__[": pytest.main(""""
        ["]__file__[",""""
            "]-v[",""""
            "]--cov=src.streaming.stream_config[",""""
            "]--cov-report=term-missing["]"]"""
    )