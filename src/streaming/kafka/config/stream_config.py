"""
Kafka流处理配置
"""



_settings = get_settings()


class StreamConfig:
    """流处理配置"""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        group_id: Optional[str] = None,
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = True,
        session_timeout_ms: int = 30000,
        heartbeat_interval_ms: int = 3000,
    ):
        """
        初始化流配置

        Args:
            bootstrap_servers: Kafka服务器地址
            group_id: 消费者组ID
            auto_offset_reset: 偏移量重置策略
            enable_auto_commit: 是否自动提交偏移量
            session_timeout_ms: 会话超时时间
            heartbeat_interval_ms: 心跳间隔
        """
        self.bootstrap_servers = bootstrap_servers or getattr(
            _settings, "kafka_bootstrap_servers", "localhost:9092"
        )
        self.group_id = group_id or getattr(
            _settings, "kafka_group_id", "football-prediction"
        )
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self.session_timeout_ms = session_timeout_ms
        self.heartbeat_interval_ms = heartbeat_interval_ms

    def to_producer_config(self) -> Dict[str, Any]:
        """转换为生产者配置"""
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": f"football-prediction-producer-{int(time.time())}",
            "acks": "all",
            "retries": 3,
            "retry.backoff.ms": 100,
            "linger.ms": 10,
            "batch.size": 16384,
            "compression.type": "snappy",
        }

    def to_consumer_config(self) -> Dict[str, Any]:
        """转换为消费者配置"""
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": self.group_id, Dict, Optional


            "auto.offset.reset": self.auto_offset_reset,
            "enable.auto.commit": self.enable_auto_commit,
            "session.timeout.ms": self.session_timeout_ms,
            "heartbeat.interval.ms": self.heartbeat_interval_ms,
        }