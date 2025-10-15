from typing import Any, Dict, List, Optional, Union

"""
简化的流配置实现
"""

import json
import os
from pathlib import Path


class StreamConfig:
    """流配置基类"""

    def __init__(
        self, name: str, bootstrap_servers: List[str], topics: List[str], **kwargs
    ):
        if not name:
            raise ValueError("Name is required")
        if not bootstrap_servers:
            raise ValueError("bootstrap_servers is required")

        self.name = name
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics

        # 设置其他属性
        for key, value in kwargs.items():
            setattr(self, key, value)

    def is_valid(self) -> bool:
        """验证配置是否有效"""
        return bool(self.name and self.bootstrap_servers)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        _config = {
            "name": self.name,
            "bootstrap_servers": self.bootstrap_servers,
            "topics": self.topics,
        }
        # 添加其他属性
        for key, value in self.__dict__.items():
            if key not in config:
                config[key] = value
        return config

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "StreamConfig":
        """从字典创建配置"""
        return cls(**config_dict)

    def merge(self, override: Dict[str, Any]) -> "StreamConfig":
        """合并配置"""
        current = self.to_dict()
        current.update(override)
        return self.from_dict(current)

    @classmethod
    def from_file(cls, file_path: str) -> "StreamConfig":
        """从文件加载配置"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(path, "r") as f:
            if file_path.endswith(".json"):
                config_dict = json.load(f)
            else:
                # 简单的键值解析
                content = f.read()
                config_dict = {}
                for line in content.split("\n"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        config_dict[key.strip()] = value.strip()

        # 环境变量替换
        config_dict = cls._substitute_env_vars(config_dict)
        return cls.from_dict(config_dict)

    @staticmethod
    def _substitute_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
        """替换环境变量"""
        result = {}
        for key, value in config.items():
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                env_var = value[2:-1]
                result[key] = os.getenv(env_var, value)
            else:
                result[key] = value
        return result

    def save_to_file(self, file_path: str):
        """保存配置到文件"""
        config_dict = self.to_dict()
        with open(file_path, "w") as f:
            json.dump(config_dict, f, indent=2)


class KafkaConfig(StreamConfig):
    """Kafka配置"""

    def __init__(
        self,
        bootstrap_servers: List[str],
        port: int = 9092,
        protocol: str = "PLAINTEXT",
        **kwargs,
    ):
        super().__init__(
            name="kafka", bootstrap_servers=bootstrap_servers, topics=[], **kwargs
        )
        self.port = port
        self.protocol = protocol

    def to_aiokafka_config(self) -> Dict[str, Any]:
        """转换为aiokafka配置"""
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "client_id": getattr(self, "client_id", None),
            "request_timeout_ms": getattr(self, "request_timeout_ms", 30000),
            "retry_backoff_ms": getattr(self, "retry_backoff_ms", 100),
            **getattr(self, "extra_config", {}),
        }

    def validate(self) -> bool:
        """验证配置"""
        if not self.bootstrap_servers:
            raise ValueError("bootstrap_servers is required")

        for server in self.bootstrap_servers:
            if ":" in server:
                host, port = server.split(":")
                try:
                    port_int = int(port)
                    if not (1 <= port_int <= 65535):
                        raise ValueError(f"Invalid port: {port_int}")
                except ValueError:
                    raise ValueError("Invalid port format")

        return True


class ConsumerConfig(StreamConfig):
    """消费者配置"""

    def __init__(
        self,
        bootstrap_servers: List[str],
        group_id: str,
        topics: List[str],
        auto_offset_reset: str = "latest",
        enable_auto_commit: bool = True,
        auto_commit_interval_ms: int = 5000,
        **kwargs,
    ):
        super().__init__(
            name="consumer",
            bootstrap_servers=bootstrap_servers,
            topics=topics,
            **kwargs,
        )

        if not group_id:
            raise ValueError("group_id is required")
        if not topics:
            raise ValueError("topics is required")

        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self.auto_commit_interval_ms = auto_commit_interval_ms

    def to_aiokafka_config(self) -> Dict[str, Any]:
        """转换为aiokafka消费者配置"""
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "group_id": self.group_id,
            "auto_offset_reset": self.auto_offset_reset,
            "enable_auto_commit": self.enable_auto_commit,
            "auto_commit_interval_ms": self.auto_commit_interval_ms,
            "max_poll_records": getattr(self, "max_poll_records", 500),
            "fetch_min_bytes": getattr(self, "fetch_min_bytes", 1),
            "session_timeout_ms": getattr(self, "session_timeout_ms", 10000),
            "heartbeat_interval_ms": getattr(self, "heartbeat_interval_ms", 3000),
        }

    @staticmethod
    def validate_with_rules(config: Dict[str, Any], rules: Dict[str, Any]) -> bool:
        """使用规则验证配置"""
        for field, rule in rules.items():
            if rule.get("required") and field not in config:
                raise ValueError(f"{field} is required")

            if field in config:
                value = config[field]
                expected_type = rule.get("type")
                if expected_type and not isinstance(value, expected_type):
                    raise ValueError(
                        f"{field} must be of type {expected_type.__name__}"
                    )

                min_value = rule.get("min_value")
                if min_value is not None and value < min_value:
                    raise ValueError(f"{field} must be >= {min_value}")

                max_value = rule.get("max_value")
                if max_value is not None and value > max_value:
                    raise ValueError(f"{field} must be <= {max_value}")

                pattern = rule.get("pattern")
                if (
                    pattern
                    and hasattr(pattern, "match")
                    and not pattern.match(str(value))
                ):
                    raise ValueError(f"{field} does not match required pattern")

                min_items = rule.get("min_items")
                if min_items and len(value) < min_items:
                    raise ValueError(f"{field} must have at least {min_items} items")

        return True


class ProducerConfig(StreamConfig):
    """生产者配置"""

    def __init__(
        self,
        bootstrap_servers: List[str],
        acks: int = 1,
        retries: int = 3,
        batch_size: int = 16384,
        linger_ms: int = 0,
        compression_type: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            name="producer", bootstrap_servers=bootstrap_servers, topics=[], **kwargs
        )

        # 验证acks值
        if acks not in [0, 1, "all"]:
            raise ValueError("acks must be 0, 1, all")

        # 验证压缩类型
        valid_compression = [None, "none", "gzip", "snappy", "lz4", "zstd"]
        if compression_type not in valid_compression:
            raise ValueError("Invalid compression type")

        self.acks = acks
        self.retries = retries
        self.batch_size = batch_size
        self.linger_ms = linger_ms
        self.compression_type = compression_type

    def to_aiokafka_config(self) -> Dict[str, Any]:
        """转换为aiokafka生产者配置"""
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "acks": self.acks,
            "retries": self.retries,
            "batch_size": self.batch_size,
            "linger_ms": self.linger_ms,
            "compression_type": self.compression_type,
            "max_request_size": getattr(self, "max_request_size", 1048576),
            "buffer_memory": getattr(self, "buffer_memory", 33554432),
            "enable_idempotence": getattr(self, "enable_idempotence", False),
        }
