"""
流配置管理器测试 - 覆盖率提升版本

针对 KafkaConfig、TopicConfig 和 StreamConfig 的详细测试，专注于提升覆盖率至 70%+
"""

import pytest
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import patch, Mock

from src.streaming.stream_config import KafkaConfig, TopicConfig, StreamConfig


class TestKafkaConfig:
    """Kafka配置测试类"""

    def test_init_default_values(self):
        """测试默认值初始化"""
        config = KafkaConfig()

        # 验证连接配置
        assert config.bootstrap_servers == "localhost:9092"
        assert config.security_protocol == "PLAINTEXT"

        # 验证生产者配置
        assert config.producer_client_id == "football-prediction-producer"
        assert config.producer_acks == "all"
        assert config.producer_retries == 3
        assert config.producer_retry_backoff_ms == 1000
        assert config.producer_linger_ms == 5
        assert config.producer_batch_size == 16384

        # 验证消费者配置
        assert config.consumer_group_id == "football-prediction-consumers"
        assert config.consumer_client_id == "football-prediction-consumer"
        assert config.consumer_auto_offset_reset == "latest"
        assert config.consumer_enable_auto_commit is True
        assert config.consumer_auto_commit_interval_ms == 5000
        assert config.consumer_max_poll_records == 500

        # 验证序列化配置
        assert config.key_serializer == "string"
        assert config.value_serializer == "json"

    def test_init_custom_values(self):
        """测试自定义值初始化"""
        config = KafkaConfig(
            bootstrap_servers="kafka:9092",
            security_protocol="SASL_SSL",
            producer_client_id="custom-producer",
            producer_retries=5,
            consumer_group_id="custom-consumers"
        )

        assert config.bootstrap_servers == "kafka:9092"
        assert config.security_protocol == "SASL_SSL"
        assert config.producer_client_id == "custom-producer"
        assert config.producer_retries == 5
        assert config.consumer_group_id == "custom-consumers"

    def test_dataclass_properties(self):
        """测试dataclass属性"""
        config = KafkaConfig()

        # 验证是dataclass实例
        assert hasattr(config, '__dataclass_fields__')

        # 验证字段存在
        fields = config.__dataclass_fields__
        assert 'bootstrap_servers' in fields
        assert 'security_protocol' in fields
        assert 'producer_client_id' in fields
        assert 'consumer_group_id' in fields

    def test_immutability_of_defaults(self):
        """测试默认值的不可变性"""
        config1 = KafkaConfig()
        config2 = KafkaConfig()

        # 两个实例应该有相同的默认值
        assert config1.bootstrap_servers == config2.bootstrap_servers
        assert config1.producer_retries == config2.producer_retries


class TestTopicConfig:
    """Topic配置测试类"""

    def test_init_default_values(self):
        """测试默认值初始化"""
        config = TopicConfig(name="test-topic")

        assert config.name == "test-topic"
        assert config.partitions == 3
        assert config.replication_factor == 1
        assert config.cleanup_policy == "delete"
        assert config.retention_ms == 604800000  # 7天
        assert config.segment_ms == 86400000  # 1天

    def test_init_custom_values(self):
        """测试自定义值初始化"""
        config = TopicConfig(
            name="custom-topic",
            partitions=6,
            replication_factor=3,
            cleanup_policy="compact",
            retention_ms=3600000,  # 1小时
            segment_ms=1800000  # 30分钟
        )

        assert config.name == "custom-topic"
        assert config.partitions == 6
        assert config.replication_factor == 3
        assert config.cleanup_policy == "compact"
        assert config.retention_ms == 3600000
        assert config.segment_ms == 1800000

    def test_topic_config_retention_values(self):
        """测试Topic配置的保留时间值"""
        config = TopicConfig(name="test-topic")

        # 验证保留时间是否合理
        assert config.retention_ms > 0
        assert config.segment_ms > 0
        assert config.retention_ms >= config.segment_ms

    def test_topic_config_partition_values(self):
        """测试Topic配置的分区值"""
        config = TopicConfig(name="test-topic")

        # 验证分区数是否合理
        assert config.partitions > 0
        assert config.replication_factor > 0

    def test_dataclass_properties(self):
        """测试dataclass属性"""
        config = TopicConfig(name="test-topic")

        # 验证是dataclass实例
        assert hasattr(config, '__dataclass_fields__')

        # 验证字段存在
        fields = config.__dataclass_fields__
        assert 'name' in fields
        assert 'partitions' in fields
        assert 'replication_factor' in fields
        assert 'cleanup_policy' in fields


class TestStreamConfig:
    """流配置管理器测试类"""

    def test_init(self):
        """测试初始化"""
        config = StreamConfig()

        assert config.kafka_config is not None
        assert config.topics is not None
        assert isinstance(config.kafka_config, KafkaConfig)
        assert isinstance(config.topics, dict)

    def test_load_kafka_config_default(self):
        """测试加载默认Kafka配置"""
        with patch.dict(os.environ, {}, clear=True):
            config = StreamConfig()

            assert config.kafka_config.bootstrap_servers == "localhost:9092"
            assert config.kafka_config.security_protocol == "PLAINTEXT"
            assert config.kafka_config.producer_client_id == "football-prediction-producer"
            assert config.kafka_config.consumer_group_id == "football-prediction-consumers"

    def test_load_kafka_config_from_env(self):
        """测试从环境变量加载Kafka配置"""
        env_vars = {
            "KAFKA_BOOTSTRAP_SERVERS": "kafka:9092",
            "KAFKA_SECURITY_PROTOCOL": "SASL_SSL",
            "KAFKA_PRODUCER_CLIENT_ID": "env-producer",
            "KAFKA_PRODUCER_ACKS": "1",
            "KAFKA_PRODUCER_RETRIES": "5",
            "KAFKA_CONSUMER_GROUP_ID": "env-consumers",
            "KAFKA_CONSUMER_CLIENT_ID": "env-consumer",
            "KAFKA_CONSUMER_AUTO_OFFSET_RESET": "earliest"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = StreamConfig()

            assert config.kafka_config.bootstrap_servers == "kafka:9092"
            assert config.kafka_config.security_protocol == "SASL_SSL"
            assert config.kafka_config.producer_client_id == "env-producer"
            assert config.kafka_config.producer_acks == "1"
            assert config.kafka_config.producer_retries == 5
            assert config.kafka_config.consumer_group_id == "env-consumers"
            assert config.kafka_config.consumer_client_id == "env-consumer"
            assert config.kafka_config.consumer_auto_offset_reset == "earliest"

    def test_load_kafka_config_partial_env(self):
        """测试部分环境变量配置"""
        env_vars = {
            "KAFKA_BOOTSTRAP_SERVERS": "custom-kafka:9092",
            "KAFKA_PRODUCER_RETRIES": "10"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = StreamConfig()

            # 验证环境变量覆盖的值
            assert config.kafka_config.bootstrap_servers == "custom-kafka:9092"
            assert config.kafka_config.producer_retries == 10

            # 验证默认值保持不变
            assert config.kafka_config.security_protocol == "PLAINTEXT"
            assert config.kafka_config.producer_client_id == "football-prediction-producer"

    def test_init_topics(self):
        """测试初始化Topic配置"""
        config = StreamConfig()

        # 验证Topic数量
        assert len(config.topics) == 4

        # 验证各个Topic存在
        assert "matches-stream" in config.topics
        assert "odds-stream" in config.topics
        assert "scores-stream" in config.topics
        assert "processed-data-stream" in config.topics

        # 验证Topic配置
        matches_config = config.topics["matches-stream"]
        assert matches_config.name == "matches-stream"
        assert matches_config.partitions == 3
        assert matches_config.retention_ms == 86400000  # 1天

        # 验证赔率流配置（数据量大，更多分区）
        odds_config = config.topics["odds-stream"]
        assert odds_config.name == "odds-stream"
        assert odds_config.partitions == 6
        assert odds_config.retention_ms == 43200000  # 12小时

        # 验证比分流配置（较短保留时间）
        scores_config = config.topics["scores-stream"]
        assert scores_config.name == "scores-stream"
        assert scores_config.partitions == 3
        assert scores_config.retention_ms == 21600000  # 6小时

    def test_get_producer_config(self):
        """测试获取生产者配置"""
        config = StreamConfig()

        producer_config = config.get_producer_config()

        # 验证基本配置
        assert producer_config["bootstrap.servers"] == "localhost:9092"
        assert producer_config["security.protocol"] == "PLAINTEXT"
        assert producer_config["client.id"] == "football-prediction-producer"
        assert producer_config["acks"] == "all"
        assert producer_config["retries"] == 3

        # 验证高级配置
        assert producer_config["compression.type"] == "gzip"
        assert producer_config["max.in.flight.requests.per.connection"] == 1
        assert producer_config["linger.ms"] == 5
        assert producer_config["batch.size"] == 16384

    def test_get_consumer_config_default(self):
        """测试获取默认消费者配置"""
        config = StreamConfig()

        consumer_config = config.get_consumer_config()

        # 验证基本配置
        assert consumer_config["bootstrap.servers"] == "localhost:9092"
        assert consumer_config["security.protocol"] == "PLAINTEXT"
        assert consumer_config["client.id"] == "football-prediction-consumer"
        assert consumer_config["group.id"] == "football-prediction-consumers"
        assert consumer_config["auto.offset.reset"] == "latest"
        assert consumer_config["enable.auto.commit"] is True

        # 验证超时配置
        assert consumer_config["max.poll.interval.ms"] == 300000
        assert consumer_config["session.timeout.ms"] == 30000
        assert consumer_config["heartbeat.interval.ms"] == 3000

    def test_get_consumer_config_custom_group(self):
        """测试获取自定义消费者组配置"""
        config = StreamConfig()

        consumer_config = config.get_consumer_config("custom-group")

        assert consumer_config["group.id"] == "custom-group"
        # 其他配置应该保持不变
        assert consumer_config["bootstrap.servers"] == "localhost:9092"
        assert consumer_config["client.id"] == "football-prediction-consumer"

    def test_get_topic_config_existing(self):
        """测试获取现有Topic配置"""
        config = StreamConfig()

        topic_config = config.get_topic_config("matches-stream")

        assert topic_config is not None
        assert topic_config.name == "matches-stream"
        assert topic_config.partitions == 3

    def test_get_topic_config_nonexistent(self):
        """测试获取不存在的Topic配置"""
        config = StreamConfig()

        topic_config = config.get_topic_config("nonexistent-topic")

        assert topic_config is None

    def test_get_all_topics(self):
        """测试获取所有Topic"""
        config = StreamConfig()

        topics = config.get_all_topics()

        assert isinstance(topics, list)
        assert len(topics) == 4
        assert "matches-stream" in topics
        assert "odds-stream" in topics
        assert "scores-stream" in topics
        assert "processed-data-stream" in topics

    def test_is_valid_topic_true(self):
        """测试验证有效Topic"""
        config = StreamConfig()

        assert config.is_valid_topic("matches-stream") is True
        assert config.is_valid_topic("odds-stream") is True
        assert config.is_valid_topic("scores-stream") is True
        assert config.is_valid_topic("processed-data-stream") is True

    def test_is_valid_topic_false(self):
        """测试验证无效Topic"""
        config = StreamConfig()

        assert config.is_valid_topic("invalid-topic") is False
        assert config.is_valid_topic("") is False
        assert config.is_valid_topic(None) is False
        assert config.is_valid_topic("matches-stream-extra") is False

    def test_topic_config_properties(self):
        """测试Topic配置属性"""
        config = StreamConfig()

        # 验证各个Topic的特定属性
        matches_config = config.topics["matches-stream"]
        odds_config = config.topics["odds-stream"]
        scores_config = config.topics["scores-stream"]

        # 赔率流应该有更多分区
        assert odds_config.partitions > matches_config.partitions
        assert odds_config.partitions > scores_config.partitions

        # 保留时间应该合理
        assert scores_config.retention_ms < matches_config.retention_ms
        assert odds_config.retention_ms < matches_config.retention_ms

    def test_configuration_consistency(self):
        """测试配置一致性"""
        config = StreamConfig()

        # 验证生产者和消费者配置使用相同的基础设置
        producer_config = config.get_producer_config()
        consumer_config = config.get_consumer_config()

        assert producer_config["bootstrap.servers"] == consumer_config["bootstrap.servers"]
        assert producer_config["security.protocol"] == consumer_config["security.protocol"]

    def test_environment_variable_persistence(self):
        """测试环境变量持久性"""
        env_vars = {
            "KAFKA_BOOTSTRAP_SERVERS": "persistent-kafka:9092",
            "KAFKA_PRODUCER_RETRIES": "7"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config1 = StreamConfig()
            config2 = StreamConfig()

            # 两个实例应该使用相同的环境变量
            assert config1.kafka_config.bootstrap_servers == "persistent-kafka:9092"
            assert config2.kafka_config.bootstrap_servers == "persistent-kafka:9092"
            assert config1.kafka_config.producer_retries == 7
            assert config2.kafka_config.producer_retries == 7

    def test_integer_conversion_from_env(self):
        """测试从环境变量的整数转换"""
        env_vars = {
            "KAFKA_PRODUCER_RETRIES": "10"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = StreamConfig()

            # 验证字符串正确转换为整数
            assert isinstance(config.kafka_config.producer_retries, int)
            assert config.kafka_config.producer_retries == 10

    def test_missing_environment_variables(self):
        """测试缺失环境变量的处理"""
        # 清除所有相关环境变量
        with patch.dict(os.environ, {}, clear=True):
            config = StreamConfig()

            # 应该使用默认值
            assert config.kafka_config.bootstrap_servers == "localhost:9092"
            assert config.kafka_config.producer_retries == 3
            assert config.kafka_config.consumer_group_id == "football-prediction-consumers"

    def test_topic_configuration_structure(self):
        """测试Topic配置结构"""
        config = StreamConfig()

        # 验证Topic配置字典结构
        for topic_name, topic_config in config.topics.items():
            assert isinstance(topic_name, str)
            assert isinstance(topic_config, TopicConfig)
            assert topic_config.name == topic_name
            assert topic_config.partitions > 0
            assert topic_config.replication_factor > 0
            assert topic_config.retention_ms > 0

    def test_configuration_immutability(self):
        """测试配置不可变性"""
        config1 = StreamConfig()
        config2 = StreamConfig()

        # 两个实例应该有相同的Topic配置
        assert len(config1.topics) == len(config2.topics)
        for topic_name in config1.topics:
            assert topic_name in config2.topics
            assert config1.topics[topic_name].partitions == config2.topics[topic_name].partitions


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])