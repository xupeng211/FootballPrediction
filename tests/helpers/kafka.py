"""
Kafka测试辅助工具
提供Kafka生产者和消费者的Mock实现
"""

from typing import Any, Dict, List, Optional, AsyncGenerator
from unittest.mock import Mock, AsyncMock
import asyncio
import json


class MockKafkaMessage:
    """模拟Kafka消息"""

    def __init__(
        self,
        topic: str,
        key: Optional[bytes] = None,
        value: Optional[bytes] = None,
        partition: int = 0,
        offset: int = 0
    ):
        self.topic = topic
        self.key = key
        self.value = value
        self.partition = partition
        self.offset = offset

    def decode(self) -> str:
        """解码消息值"""
        if self.value:
            return self.value.decode('utf-8')
        return ""

    def decode_json(self) -> Dict[str, Any]:
        """解码JSON消息"""
        try:
            return json.loads(self.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}


class MockKafkaProducer:
    """模拟Kafka生产者"""

    def __init__(self):
        self.messages: List[MockKafkaMessage] = []
        self.closed = False

    async def send(
        self,
        topic: str,
        value: Any,
        key: Optional[Any] = None,
        partition: Optional[int] = None
    ) -> MockKafkaMessage:
        """发送消息"""
        if isinstance(value, dict):
            value_bytes = json.dumps(value).encode('utf-8')
        elif isinstance(value, str):
            value_bytes = value.encode('utf-8')
        else:
            value_bytes = str(value).encode('utf-8')

        if isinstance(key, str):
            key_bytes = key.encode('utf-8')
        else:
            key_bytes = key

        message = MockKafkaMessage(
            topic=topic,
            key=key_bytes,
            value=value_bytes,
            partition=partition or 0
        )

        self.messages.append(message)
        return message

    async def flush(self) -> None:
        """刷新缓冲区"""
        pass

    async def close(self) -> None:
        """关闭生产者"""
        self.closed = True

    def get_messages(self, topic: Optional[str] = None) -> List[MockKafkaMessage]:
        """获取发送的消息"""
        if topic:
            return [msg for msg in self.messages if msg.topic == topic]
        return self.messages.copy()

    def clear_messages(self) -> None:
        """清空消息记录"""
        self.messages.clear()


class MockKafkaConsumer:
    """模拟Kafka消费者"""

    def __init__(self, topics: List[str], **kwargs):
        self.topics = topics
        self.messages: List[MockKafkaMessage] = []
        self.current_index = 0
        self.closed = False
        self.position = {topic: 0 for topic in topics}

    def add_message(self, message: MockKafkaMessage) -> None:
        """添加消息到队列"""
        if message.topic in self.topics:
            self.messages.append(message)

    def add_messages(self, messages: List[MockKafkaMessage]) -> None:
        """批量添加消息"""
        for msg in messages:
            self.add_message(msg)

    async def __anext__(self) -> MockKafkaMessage:
        """异步迭代器"""
        if self.current_index >= len(self.messages):
            raise StopAsyncIteration

        message = self.messages[self.current_index]
        self.current_index += 1
        self.position[message.topic] = message.offset
        return message

    def __aiter__(self) -> AsyncGenerator[MockKafkaMessage, None]:
        """返回异步迭代器"""
        return self

    async def getmany(self, timeout_ms: int = 0, max_records: int = None) -> Dict[str, List[MockKafkaMessage]]:
        """批量获取消息"""
        if max_records is None:
            max_records = len(self.messages) - self.current_index

        result = {}
        count = 0

        while self.current_index < len(self.messages) and count < max_records:
            message = self.messages[self.current_index]
            topic = message.topic

            if topic not in result:
                result[topic] = []

            result[topic].append(message)
            self.current_index += 1
            count += 1

        return result

    async def commit(self) -> None:
        """提交偏移量"""
        pass

    async def close(self) -> None:
        """关闭消费者"""
        self.closed = True

    def position(self, topic: str) -> int:
        """获取主题偏移量"""
        return self.position.get(topic, 0)

    def seek(self, topic: str, partition: int, offset: int) -> None:
        """设置偏移量"""
        # 在mock中简化实现
        self.current_index = offset


def apply_kafka_mocks():
    """应用Kafka mock装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 创建mock生产者和消费者
            producer = MockKafkaProducer()
            consumer = MockKafkaConsumer(['test_topic'])

            # 添加测试消息
            test_message = MockKafkaMessage(
                topic='test_topic',
                key=b'test_key',
                value=b'{"test": "data"}'
            )
            consumer.add_message(test_message)

            return await func(producer, consumer, *args, **kwargs)
        return wrapper
    return decorator


# 全局mock实例
mock_kafka_producer = MockKafkaProducer()
mock_kafka_consumer = MockKafkaConsumer(['test_topic'])