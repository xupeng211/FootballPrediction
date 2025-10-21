"""Kafka 相关测试桩 - 重构版本（不使用 monkeypatch）"""

from typing import Any, Dict, List, Optional, Tuple


class MockKafkaMessage:
    """简化的 Kafka 消息对象"""

    def __init__(self, topic: str, value: bytes, key: Optional[str] = None) -> None:
        self._topic = topic
        self._value = value
        self._key = key

    def topic(self) -> str:
        return self._topic

    def partition(self) -> int:
        return 0

    def offset(self) -> int:
        return 0

    def value(self) -> bytes:
        return self._value

    def key(self) -> Optional[str]:
        return self._key


class MockKafkaProducer:
    """记录消息的内存 Kafka Producer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config or {}
        self.messages: List[Tuple[str, Optional[str], bytes]] = []

    def produce(
        self,
        topic: str,
        value: bytes,
        key: Optional[str] = None,
        callback: Optional[Any] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.messages.append((topic, key, value))

    def flush(self) -> None:
        """模拟 flush 操作"""
        pass

    def close(self) -> None:
        """关闭生产者"""
        pass


class MockKafkaConsumer:
    """返回预定义消息的内存 Kafka Consumer"""

    def __init__(
        self,
        topics: List[str],
        config: Optional[Dict[str, Any]] = None,
        messages: Optional[List[MockKafkaMessage]] = None,
    ) -> None:
        self.topics = topics
        self._config = config or {}
        self._messages = messages or []
        self._message_index = 0

    def poll(self, timeout_ms: float = 1000) -> Dict[Any, MockKafkaMessage]:
        """返回一条预定义的消息"""
        if self._message_index < len(self._messages):
            msg = self._messages[self._message_index]
            self._message_index += 1
            return {None: msg}
        return {}

    def close(self) -> None:
        """关闭消费者"""
        pass


# 创建全局 mock 实例（仅在测试中使用）
_global_producer_mock = None
_global_consumer_mock = None


def get_mock_kafka_producer() -> MockKafkaProducer:
    """获取 Kafka Producer mock 实例（单例）"""
    global _global_producer_mock
    if _global_producer_mock is None:
        _global_producer_mock = MockKafkaProducer()
    return _global_producer_mock


def get_mock_kafka_consumer(
    topics: List[str] = None,
    config: Optional[Dict[str, Any]] = None,
    messages: Optional[List[MockKafkaMessage]] = None,
) -> MockKafkaConsumer:
    """获取 Kafka Consumer mock 实例"""
    return MockKafkaConsumer(topics or [], config, messages)


def reset_kafka_mocks() -> None:
    """重置 Kafka mock 实例（用于测试隔离）"""
    global _global_producer_mock
    if _global_producer_mock:
        _global_producer_mock.messages.clear()


# 向后兼容的函数（现在只是返回 mock 实例，不使用 monkeypatch）
def apply_kafka_mocks(*args, **kwargs) -> Dict[str, Any]:
    """
    向后兼容：返回 Kafka mocks
    不再使用 monkeypatch，而是返回 mock 实例供测试使用
    """
    return {
        "kafka": {
            "Producer": MockKafkaProducer,
            "Consumer": MockKafkaConsumer,
        }
    }


__all__ = [
    "MockKafkaMessage",
    "MockKafkaProducer",
    "MockKafkaConsumer",
    "get_mock_kafka_producer",
    "get_mock_kafka_consumer",
    "reset_kafka_mocks",
    "apply_kafka_mocks",
]
