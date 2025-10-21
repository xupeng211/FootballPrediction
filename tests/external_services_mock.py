# 外部服务Mock配置
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

class MockHTTPClient:
    """模拟HTTP客户端"""

    def __init__(self):
        self.responses = {}
        self.requests = []

    def get(self, url: str, **kwargs):
        self.requests.append({"method": "GET", "url": url, **kwargs})
        response = Mock()
        response.status_code = 200
        response.json.return_value = self.responses.get(url, {"status": "ok"})
        return response

    async def aget(self, url: str, **kwargs):
        self.requests.append({"method": "GET", "url": url, **kwargs})
        response = AsyncMock()
        response.status_code = 200
        response.json.return_value = self.responses.get(url, {"status": "ok"})
        return response

# Mock外部服务
mock_http_client = MockHTTPClient()

def get_http_client():
    """获取HTTP客户端（测试用Mock）"""
    return mock_http_client

# Kafka Mock
class MockKafkaProducer:
    """模拟Kafka生产者"""

    def __init__(self):
        self.messages = []

    def send(self, topic: str, value: bytes, **kwargs):
        self.messages.append({"topic": topic, "value": value, **kwargs})
        return Mock()

class MockKafkaConsumer:
    """模拟Kafka消费者"""

    def __init__(self):
        self.messages = []

    def __iter__(self):
        return iter(self.messages)

def get_kafka_producer():
    """获取Kafka生产者（测试用Mock）"""
    return MockKafkaProducer()

def get_kafka_consumer():
    """获取Kafka消费者（测试用Mock）"""
    return MockKafkaConsumer()
