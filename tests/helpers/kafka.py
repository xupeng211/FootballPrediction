"""Kafka 相关测试桩"""

import sys
from types import ModuleType
from typing import Any, Dict, List, Optional, Tuple

from pytest import MonkeyPatch


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
        self.config = config or {}
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


class MockKafkaConsumer:
    """返回预定义消息的内存 Kafka Consumer"""

    def __init__(
        self,
        topics: List[str],
        config: Optional[Dict[str, Any]] = None,
        messages: Optional[List[MockKafkaMessage]] = None,
    ) -> None:
        self.topics = topics
        self.config = config or {}
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


def apply_kafka_mocks(monkeypatch: MonkeyPatch) -> None:
    """
    应用 Kafka mock

    Args:
        monkeypatch: pytest monkeypatch fixture
    """
    # 创建 mock 模块
    mock_kafka = ModuleType("kafka")
    mock_kafka.Producer = MockKafkaProducer
    mock_kafka.Consumer = MockKafkaConsumer

    # 应用 mock
    monkeypatch.setitem(sys.modules, "kafka", mock_kafka)
    monkeypatch.setitem(sys.modules, "kafka.producer", mock_kafka)
    monkeypatch.setitem(sys.modules, "kafka.consumer", mock_kafka)


__all__ = [
    "MockKafkaMessage",
    "MockKafkaProducer",
    "MockKafkaConsumer",
    "apply_kafka_mocks",
]
