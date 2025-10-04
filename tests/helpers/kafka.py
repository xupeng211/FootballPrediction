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
        if callback:
            callback(None, MockKafkaMessage(topic, value, key))

    def poll(self, _timeout: float = 0.0) -> int:
        return 0

    def flush(self, _timeout: Optional[float] = None) -> int:
        return 0


class MockKafkaConsumer:
    """基于内存队列的 Kafka Consumer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self._queue: List[MockKafkaMessage] = []
        self.subscriptions: List[str] = []

    def subscribe(self, topics: List[str]) -> None:
        self.subscriptions = topics

    def poll(self, _timeout: float = 0.1) -> Optional[MockKafkaMessage]:
        if self._queue:
            return self._queue.pop(0)
        return None

    def close(self) -> None:
        return None

    def push(self, topic: str, value: bytes, key: Optional[str] = None) -> None:
        self._queue.append(MockKafkaMessage(topic, value, key))


def apply_kafka_mocks(monkeypatch: MonkeyPatch) -> None:
    """替换 confluent_kafka 为测试桩"""

    try:
        import confluent_kafka as kafka  # type: ignore
    except ImportError:
        kafka = ModuleType("confluent_kafka")  # type: ignore
        sys.modules["confluent_kafka"] = kafka

    monkeypatch.setattr(kafka, "Producer", MockKafkaProducer, raising=False)
    monkeypatch.setattr(kafka, "Consumer", MockKafkaConsumer, raising=False)
    monkeypatch.setattr(kafka, "KafkaException", RuntimeError, raising=False)
    monkeypatch.setattr(kafka, "KafkaError", RuntimeError, raising=False)


__all__ = [
    "MockKafkaMessage",
    "MockKafkaProducer",
    "MockKafkaConsumer",
    "apply_kafka_mocks",
]
