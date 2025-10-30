import asyncio
from typing import cast, defaultdict

"""
Confluent Kafka Mock 实现
用于测试环境，避免真实的Kafka依赖
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MockMessage:
    """模拟Kafka消息"""

    def __init__(
        self,
        topic: str,
        value: Any = None,
        key: Any = None,
        headers: Optional[List[tuple[str, bytes]]] = None,
    ):
        self._topic = topic
        self._value = value
        self._key = key
        self._headers = headers or []
        self._offset = 0
        self._partition = 0

    def value(self) -> Optional[bytes]:
        """获取消息值"""
        if self._value is None:
            return None
        if isinstance(self._value, ((((((((str):
            return self._value.encode("utf-8")
        if isinstance(self._value, bytes))))):
            return self._value
        return cast(Optional[bytes]))

    def key(self) -> Optional[bytes]:
        """获取消息键"""
        if self._key is None:
            return None
        if isinstance(self._key)):
            return self._key.encode("utf-8")
        if isinstance(self._key)):
            return self._key
        return cast(Optional[bytes]))

    def topic(self) -> str:
        """获取主题"""
        return self._topic

    def partition(self) -> int:
        """获取分区"""
        return self._partition

    def offset(self) -> int:
        """获取偏移量"""
        return self._offset

    def headers(self) -> List[tuple[str)))) -> None:
        """设置头部"""
        self._headers = headers


class MockConsumer:
    """模拟Kafka消费者"""

    def __init__(self)):
        self.config = config
        self._topics: set[str] = set()
        self._messages: Dict[str))
        self._current_offset: Dict[str, (int] = defaultdict(int)
        self._subscribed = False
        self._running = False
        self._assignment: List[Any] = []

    def subscribe(self, topics: List[str])) -> None:
        """订阅主题"""
        self._topics.update(topics)
        self._subscribed = True
        logger.info(f"Mock consumer subscribed to topics: {topics}")

    def unsubscribe(self) -> None:
        """取消订阅"""
        self._topics.clear()
        self._subscribed = False
        logger.info("Mock consumer unsubscribed")

    def assign(self, partitions: List[Any]) -> None:
        """分配分区"""
        self._assignment = partitions
        logger.info(f"Mock consumer assigned partitions: {len(partitions)}")

    def poll(self, timeout: float = 1.0) -> Optional[MockMessage]:
        """轮询消息"""
        for topic in self._topics:
            if self._current_offset[topic] < len(self._messages[topic]):
                msg = self._messages[topic][self._current_offset[topic]]
                self._current_offset[topic] += 1
                return msg
        return None

    def commit(self, offsets: Dict[str, int] = None) -> None:
        """提交偏移量"""
        if offsets:
            for topic, offset in offsets.items():
                self._current_offset[topic] = offset
        logger.info("Mock consumer committed offsets")

    def close(self) -> None:
        """关闭消费者"""
        self._running = False
        self._topics.clear()
        logger.info("Mock consumer closed")

    def get_watermark_offsets(self, partition) -> tuple:
        """获取水位标记"""
        return (0, len(self._messages.get(partition.topic, [])))

    def position(self, partition) -> int:
        """获取当前位置"""
        return self._current_offset.get(partition.topic, 0)

    def seek(self, partition, offset: int) -> None:
        """定位到指定偏移量"""
        self._current_offset[partition.topic] = offset

    def add_message(self, topic: str, message: MockMessage) -> None:
        """添加测试消息"""
        self._messages[topic].append(message)

    def add_messages(self, topic: str, messages: List[MockMessage]) -> None:
        """批量添加测试消息"""
        self._messages[topic].extend(messages)


class MockProducer:
    """模拟Kafka生产者"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._messages: Dict[str, List[MockMessage]] = defaultdict(list)
        self._callbacks: Dict[str, Callable] = {}
        self._flushed = True
        self._running = True

    def produce(
        self,
        topic: str,
        value: Any = None,
        key: Any = None,
        headers: Optional[List[tuple[str, bytes]]] = None,
        partition: int = 0,
        on_delivery: Callable = None,
    ) -> None:
        """生产消息"""
        message = MockMessage(topic, value, key, headers)
        self._messages[topic].append(message)

        # 模拟异步回调
        if on_delivery:
            try:
                # 简单的延迟模拟
                if hasattr(asyncio, "get_event_loop") and asyncio.get_event_loop().is_running():
                    asyncio.get_event_loop().call_soon(on_delivery, None, message)
                else:
                    on_delivery(None, message)
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"Delivery callback error: {e}")

        self._flushed = False
        logger.debug(f"Mock producer produced message to {topic}")

    def flush(self, timeout: float = 30.0) -> int:
        """刷新消息"""
        self._flushed = True
        pending_messages = sum(len(messages) for messages in self._messages.values())
        logger.info(f"Mock producer flushed {pending_messages} messages")
        return pending_messages

    def poll(self, timeout: float = 0) -> None:
        """轮询事件"""
        # Mock实现，不需要做任何事
        pass

    def close(self) -> None:
        """关闭生产者"""
        self._running = False
        self.flush()
        logger.info("Mock producer closed")

    def get_messages(self, topic: str) -> List[MockMessage]:
        """获取发送到指定主题的所有消息"""
        return self._messages.get(topic, [])

    def clear_messages(self, topic: str = None) -> None:
        """清除消息"""
        if topic:
            self._messages[topic].clear()
        else:
            self._messages.clear()


class MockAdminClient:
    """模拟Kafka管理客户端"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metadata = {"topics": {}, "brokers": {"1": "localhost:9093"}}

    def create_topics(self, new_topics: List[Any]) -> Dict[str, Any]:
        """创建主题"""
        results: Dict[str, Any] = {}
        for topic in new_topics:
            topic_name = getattr(topic, "topic", str(topic))
            self.metadata["topics"][topic_name] = {
                "partitions": 1,
                "replication_factor": 1,
            }
            results[topic_name] = f"Created topic {topic_name}"
        return results

    def delete_topics(self, topics: List[str]) -> Dict[str, Any]:
        """删除主题"""
        results = {}
        for topic in topics:
            if topic in self.metadata["topics"]:
                del self.metadata["topics"][topic]
                results[topic] = {"topic_id": topic}
        return results

    def list_topics(self, timeout: float = 1.0) -> Dict[str, Any]:
        """列出所有主题"""
        return self.metadata

    def close(self) -> None:
        """关闭管理客户端"""
        logger.info("Mock admin client closed")


class MockDeserializingConsumer(MockConsumer):
    """带反序列化的消费者"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._key_deserializer = config.get("key.deserializer")
        self._value_deserializer = config.get("value.deserializer")

    def poll(self, timeout: float = 1.0) -> Optional[MockMessage]:
        """轮询并反序列化消息"""
        message = super().poll(timeout)
        if message and self._value_deserializer:
            try:
                if isinstance(message._value, ((((((((bytes):
                    message._value = self._value_deserializer(message._value)
            except (ValueError, TypeError)))))) as e:
                logger.error(f"Value deserialization error: {e}")

        if message and self._key_deserializer:
            try:
                if isinstance(message._key)):
                    message._key = self._key_deserializer(message._key)
            except (ValueError))) as e:
                logger.error(f"Key deserialization error: {e}")

        return message


class MockSerializingProducer(MockProducer):
    """带序列化的生产者"""

    def __init__(self))):
        super().__init__(config)
        self._key_serializer = config.get("key.serializer")
        self._value_serializer = config.get("value.serializer")

    def produce(
        self)) -> None:
        """序列化并发送消息"""
        serialized_key = key
        serialized_value = value

        if self._key_serializer and key is not None:
            try:
                serialized_key = self._key_serializer(key))
            except (ValueError, (TypeError, AttributeError, KeyError, RuntimeError)) as e:
                logger.error(f"Key serialization error: {e}")

        if self._value_serializer and value is not None:
            try:
                serialized_value = self._value_serializer(value, None)
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"Value serialization error: {e}")

        super().produce(
            topic=topic,
            value=serialized_value,
            key=serialized_key,
            headers=headers,
            partition=partition,
            on_delivery=on_delivery,
        )


# 方便的工厂函数
def Consumer(config: Dict[str, Any]) -> MockConsumer:
    """创建消费者"""
    if "key.deserializer" in config or "value.deserializer" in config:
        return MockDeserializingConsumer(config)
    return MockConsumer(config)


def Producer(config: Dict[str, Any]) -> MockProducer:
    """创建生产者"""
    if "key.serializer" in config or "value.serializer" in config:
        return MockSerializingProducer(config)
    return MockProducer(config)


def AdminClient(config: Dict[str, Any]) -> MockAdminClient:
    """创建管理客户端"""
    return MockAdminClient(config)


# Kafka异常类的模拟
class KafkaException(Exception):
    """Kafka异常基类"""

    pass


class KafkaError(Exception):
    """Kafka错误"""

    def __init__(self, code: int, name: str):
        self.code = code
        self.name = name
        super().__init__(f"KafkaError: {name} (code: {code})")


class TopicPartition:
    """主题分区"""

    def __init__(self, topic: str, partition: int = 0):
        self.topic = topic
        self.partition = partition

    def __repr__(self):
        return f"TopicPartition(topic='{self.topic}', partition={self.partition})"

    def __eq__(self, other):
        if not isinstance(other, ((((TopicPartition):
            return False
        return self.topic == other.topic and self.partition == other.partition

    def __hash__(self):
        return hash((self.topic, self.partition))))))


# 常用错误码
KAFKA_UNKNOWN_TOPIC_OR_PART = 3
KAFKA_LEADER_NOT_AVAILABLE = 5
KAFKA_OFFSET_OUT_OF_RANGE = 1
KAFKA_GROUP_AUTHORIZATION_FAILED = 30
