"""
流处理配置测试
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import json
import yaml
from typing import Any, Dict, List, Optional
from pathlib import Path

from src.streaming.stream_config_simple import (
    StreamConfig,
    KafkaConfig,
    ConsumerConfig,
    ProducerConfig,
)


class TestStreamConfig:
    """流配置基础测试"""

    def test_stream_config_creation(self):
        """测试创建流配置"""
        config = StreamConfig(
            name="test_stream",
            bootstrap_servers=["localhost:9092"],
            topics=["topic1", "topic2"],
        )

        assert config.name == "test_stream"
        assert config.bootstrap_servers == ["localhost:9092"]
        assert config.topics == ["topic1", "topic2"]

    def test_stream_config_validation(self):
        """测试配置验证"""
        # 有效配置
        config = StreamConfig(
            name="test", bootstrap_servers=["localhost:9092"], topics=["topic"]
        )
        assert config.is_valid() is True

        # 无效配置（缺少名称）
        with pytest.raises(ValueError, match="Name is required"):
            StreamConfig(
                name="", bootstrap_servers=["localhost:9092"], topics=["topic"]
            )

    def test_stream_config_to_dict(self):
        """测试配置转字典"""
        config = StreamConfig(
            name="test",
            bootstrap_servers=["localhost:9092"],
            topics=["topic1", "topic2"],
        )

        config_dict = config.to_dict()
        assert config_dict["name"] == "test"
        assert config_dict["bootstrap_servers"] == ["localhost:9092"]
        assert config_dict["topics"] == ["topic1", "topic2"]

    def test_stream_config_from_dict(self):
        """测试从字典创建配置"""
        config_dict = {
            "name": "test",
            "bootstrap_servers": ["localhost:9092"],
            "topics": ["topic1", "topic2"],
            "group_id": "test_group",
        }

        config = StreamConfig.from_dict(config_dict)
        assert config.name == "test"
        assert config.group_id == "test_group"

    def test_stream_config_merge(self):
        """测试配置合并"""
        base_config = StreamConfig(
            name="base", bootstrap_servers=["localhost:9092"], topics=["topic1"]
        )

        override = {"topics": ["topic2", "topic3"], "group_id": "new_group"}

        merged = base_config.merge(override)
        assert merged.name == "base"
        assert merged.topics == ["topic2", "topic3"]
        assert merged.group_id == "new_group"


class TestKafkaConfig:
    """Kafka配置测试"""

    def test_kafka_config_defaults(self):
        """测试Kafka默认配置"""
        config = KafkaConfig(bootstrap_servers=["localhost:9092"])

        assert config.port == 9092
        assert config.protocol == "PLAINTEXT"
        assert config.security_protocol == "PLAINTEXT"

    def test_kafka_config_with_ssl(self):
        """测试SSL配置"""
        config = KafkaConfig(
            bootstrap_servers=["kafka.example.com:9093"],
            protocol="SSL",
            ssl_cafile="/path/to/ca.crt",
            ssl_certfile="/path/to/client.crt",
            ssl_keyfile="/path/to/client.key",
        )

        assert config.protocol == "SSL"
        assert config.ssl_cafile == "/path/to/ca.crt"
        assert config.ssl_certfile == "/path/to/client.crt"
        assert config.ssl_keyfile == "/path/to/client.key"

    def test_kafka_config_with_sasl(self):
        """测试SASL配置"""
        config = KafkaConfig(
            bootstrap_servers=["kafka.example.com:9092"],
            security_protocol="SASL_SSL",
            sasl_mechanism="PLAIN",
            sasl_username="user",
            sasl_password="pass",
        )

        assert config.security_protocol == "SASL_SSL"
        assert config.sasl_mechanism == "PLAIN"
        assert config.sasl_username == "user"
        assert config.sasl_password == "pass"

    def test_kafka_config_to_aiokafka(self):
        """测试转换为aiokafka配置"""
        config = KafkaConfig(
            bootstrap_servers=["kafka1:9092", "kafka2:9092"],
            client_id="test_client",
            request_timeout_ms=30000,
            retry_backoff_ms=100,
        )

        kafka_config = config.to_aiokafka_config()
        assert kafka_config["bootstrap_servers"] == ["kafka1:9092", "kafka2:9092"]
        assert kafka_config["client_id"] == "test_client"
        assert kafka_config["request_timeout_ms"] == 30000
        assert kafka_config["retry_backoff_ms"] == 100

    def test_kafka_config_validation(self):
        """测试Kafka配置验证"""
        # 有效配置
        config = KafkaConfig(bootstrap_servers=["localhost:9092"])
        assert config.validate() is True

        # 无效配置（没有服务器）
        with pytest.raises(ValueError, match="bootstrap_servers is required"):
            KafkaConfig(bootstrap_servers=[])

        # 无效端口
        with pytest.raises(ValueError, match="Invalid port"):
            KafkaConfig(bootstrap_servers=["localhost:99999"])


class TestConsumerConfig:
    """消费者配置测试"""

    def test_consumer_config_defaults(self):
        """测试消费者默认配置"""
        config = ConsumerConfig(
            bootstrap_servers=["localhost:9092"],
            group_id="test_group",
            topics=["test_topic"],
        )

        assert config.auto_offset_reset == "latest"
        assert config.enable_auto_commit is True
        assert config.auto_commit_interval_ms == 5000

    def test_consumer_config_earliest_offset(self):
        """测试从最早偏移量开始"""
        config = ConsumerConfig(
            bootstrap_servers=["localhost:9092"],
            group_id="test_group",
            topics=["test_topic"],
            auto_offset_reset="earliest",
        )

        assert config.auto_offset_reset == "earliest"

    def test_consumer_config_manual_commit(self):
        """测试手动提交配置"""
        config = ConsumerConfig(
            bootstrap_servers=["localhost:9092"],
            group_id="test_group",
            topics=["test_topic"],
            enable_auto_commit=False,
        )

        assert config.enable_auto_commit is False

    def test_consumer_config_with_session_timeout(self):
        """测试会话超时配置"""
        config = ConsumerConfig(
            bootstrap_servers=["localhost:9092"],
            group_id="test_group",
            topics=["test_topic"],
            session_timeout_ms=30000,
        )

        assert config.session_timeout_ms == 30000

    def test_consumer_config_to_aiokafka(self):
        """测试转换为aiokafka消费者配置"""
        config = ConsumerConfig(
            bootstrap_servers=["kafka1:9092"],
            group_id="test_group",
            topics=["topic1", "topic2"],
            max_poll_records=100,
            fetch_min_bytes=1024,
        )

        kafka_config = config.to_aiokafka_config()
        assert kafka_config["group_id"] == "test_group"
        assert kafka_config["auto_offset_reset"] == "latest"
        assert kafka_config["max_poll_records"] == 100
        assert kafka_config["fetch_min_bytes"] == 1024

    def test_consumer_config_validation(self):
        """测试消费者配置验证"""
        # 缺少group_id
        with pytest.raises(ValueError, match="group_id is required"):
            ConsumerConfig(bootstrap_servers=["localhost:9092"], topics=["test_topic"])

        # 缺少topics
        with pytest.raises(ValueError, match="topics is required"):
            ConsumerConfig(bootstrap_servers=["localhost:9092"], group_id="test_group")


class TestProducerConfig:
    """生产者配置测试"""

    def test_producer_config_defaults(self):
        """测试生产者默认配置"""
        config = ProducerConfig(bootstrap_servers=["localhost:9092"])

        assert config.acks == 1
        assert config.retries == 3
        assert config.batch_size == 16384
        assert config.linger_ms == 0

    def test_producer_config_all_acks(self):
        """测试所有确认配置"""
        config = ProducerConfig(bootstrap_servers=["localhost:9092"], acks="all")

        assert config.acks == "all"

    def test_producer_config_no_retries(self):
        """测试不重试配置"""
        config = ProducerConfig(bootstrap_servers=["localhost:9092"], retries=0)

        assert config.retries == 0

    def test_producer_config_with_compression(self):
        """测试压缩配置"""
        config = ProducerConfig(
            bootstrap_servers=["localhost:9092"], compression_type="gzip"
        )

        assert config.compression_type == "gzip"

    def test_producer_config_with_idempotence(self):
        """测试幂等性配置"""
        config = ProducerConfig(
            bootstrap_servers=["localhost:9092"], enable_idempotence=True
        )

        assert config.enable_idempotence is True

    def test_producer_config_to_aiokafka(self):
        """测试转换为aiokafka生产者配置"""
        config = ProducerConfig(
            bootstrap_servers=["kafka1:9092"],
            acks="all",
            retries=5,
            batch_size=32768,
            linger_ms=10,
            compression_type="snappy",
        )

        kafka_config = config.to_aiokafka_config()
        assert kafka_config["acks"] == "all"
        assert kafka_config["retries"] == 5
        assert kafka_config["batch_size"] == 32768
        assert kafka_config["linger_ms"] == 10
        assert kafka_config["compression_type"] == "snappy"

    def test_producer_config_validation(self):
        """测试生产者配置验证"""
        # 无效的acks值
        with pytest.raises(ValueError, match="acks must be 0, 1, all"):
            ProducerConfig(bootstrap_servers=["localhost:9092"], acks="invalid")

        # 无效的压缩类型
        with pytest.raises(ValueError, match="Invalid compression type"):
            ProducerConfig(
                bootstrap_servers=["localhost:9092"], compression_type="invalid"
            )


class TestConfigLoading:
    """配置加载测试"""

    def test_load_config_from_json(self):
        """测试从JSON加载配置"""
        json_content = {
            "name": "test_stream",
            "bootstrap_servers": ["localhost:9092"],
            "topics": ["topic1", "topic2"],
            "group_id": "test_group",
            "auto_offset_reset": "earliest",
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(json_content))):
            config = StreamConfig.from_file("config.json")

        assert config.name == "test_stream"
        assert config.group_id == "test_group"
        assert config.auto_offset_reset == "earliest"

    def test_load_config_from_yaml(self):
        """测试从YAML加载配置"""
        yaml_content = """
        name: test_stream
        bootstrap_servers:
          - kafka1:9092
          - kafka2:9092
        topics:
          - topic1
          - topic2
        group_id: test_group
        auto_offset_reset: earliest
        """

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch(
                "yaml.safe_load",
                return_value={
                    "name": "test_stream",
                    "bootstrap_servers": ["kafka1:9092", "kafka2:9092"],
                    "topics": ["topic1", "topic2"],
                    "group_id": "test_group",
                    "auto_offset_reset": "earliest",
                },
            ):
                config = StreamConfig.from_file("config.yaml")

        assert config.name == "test_stream"
        assert len(config.bootstrap_servers) == 2
        assert config.group_id == "test_group"

    def test_load_config_with_env_substitution(self):
        """测试环境变量替换"""
        import os

        os.environ["KAFKA_SERVER"] = "kafka.example.com:9092"
        os.environ["KAFKA_GROUP"] = "prod_group"

        config_dict = {
            "name": "test",
            "bootstrap_servers": ["${KAFKA_SERVER}"],
            "group_id": "${KAFKA_GROUP}",
            "topics": ["test_topic"],
        }

        with patch.dict(
            os.environ,
            {"KAFKA_SERVER": "kafka.example.com:9092", "KAFKA_GROUP": "prod_group"},
        ):
            config = ConsumerConfig.from_dict(config_dict)

        assert config.bootstrap_servers == ["kafka.example.com:9092"]
        assert config.group_id == "prod_group"

    def test_save_config_to_file(self):
        """测试保存配置到文件"""
        config = ConsumerConfig(
            bootstrap_servers=["localhost:9092"],
            group_id="test_group",
            topics=["topic1"],
        )

        config.to_dict()

        with patch("builtins.open", mock_open()) as mock_file:
            with patch("json.dump") as mock_dump:
                config.save_to_file("config.json")

                mock_file.assert_called_once_with("config.json", "w")
                mock_dump.assert_called_once()

    def test_config_inheritance(self):
        """测试配置继承"""
        base_config = StreamConfig(
            name="base", bootstrap_servers=["kafka1:9092"], topics=["base_topic"]
        )

        child_config = ConsumerConfig(
            group_id="child_group", topics=["child_topic"], parent=base_config
        )

        assert child_config.bootstrap_servers == ["kafka1:9092"]
        assert child_config.group_id == "child_group"
        assert child_config.topics == ["child_topic"]

    def test_config_profile(self):
        """测试配置档案"""
        profiles = {
            "development": {
                "bootstrap_servers": ["localhost:9092"],
                "topics": ["dev_topic"],
            },
            "production": {
                "bootstrap_servers": ["kafka1:9092", "kafka2:9092", "kafka3:9092"],
                "topics": ["prod_topic"],
                "acks": "all",
                "retries": 10,
            },
        }

        # 开发环境配置
        dev_config = ProducerConfig.from_dict(profiles["development"])
        assert dev_config.bootstrap_servers == ["localhost:9092"]

        # 生产环境配置
        prod_config = ProducerConfig.from_dict(profiles["production"])
        assert len(prod_config.bootstrap_servers) == 3
        assert prod_config.acks == "all"
        assert prod_config.retries == 10

    def test_config_template(self):
        """测试配置模板"""
        template = {
            "bootstrap_servers": ["{{KAFKA_SERVERS}}"],
            "group_id": "{{GROUP_ID}}",
            "topics": ["{{TOPIC_PREFIX}}_events"],
        }

        values = {
            "KAFKA_SERVERS": "kafka.example.com:9092",
            "GROUP_ID": "event_consumer",
            "TOPIC_PREFIX": "prod",
        }

        # 应用模板变量
        config_str = json.dumps(template)
        for key, value in values.items():
            config_str = config_str.replace(f"{{{{{key}}}}}", value)

        config_dict = json.loads(config_str)
        config = ConsumerConfig.from_dict(config_dict)

        assert config.bootstrap_servers == ["kafka.example.com:9092"]
        assert config.group_id == "event_consumer"
        assert config.topics == ["prod_events"]

    def test_config_validation_rules(self):
        """测试配置验证规则"""
        # 定义验证规则
        rules = {
            "bootstrap_servers": {"required": True, "type": list, "min_items": 1},
            "group_id": {"required": True, "type": str, "pattern": r"^[a-zA-Z0-9_-]+$"},
            "session_timeout_ms": {"type": int, "min_value": 1000, "max_value": 300000},
        }

        # 有效配置
        valid_config = {
            "bootstrap_servers": ["localhost:9092"],
            "group_id": "test_group",
            "session_timeout_ms": 10000,
        }

        # 无效配置（group_id包含特殊字符）
        invalid_config = {
            "bootstrap_servers": ["localhost:9092"],
            "group_id": "test@group",
            "session_timeout_ms": 10000,
        }

        # 验证有效配置
        assert ConsumerConfig.validate_with_rules(valid_config, rules) is True

        # 验证无效配置
        assert ConsumerConfig.validate_with_rules(invalid_config, rules) is False
