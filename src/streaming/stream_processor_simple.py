"""
简化的流处理器实现
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable, AsyncIterator
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.core.exceptions import StreamingError


class StreamProcessor:
    """流处理器基类"""

    def __init__(
        self, consumer, producer, input_topics: List[str], output_topics: List[str]
    ):
        self.consumer = consumer
        self.producer = producer
        self.input_topics = input_topics
        self.output_topics = output_topics
        self.metrics = {
            "messages_processed": 0,
            "messages_failed": 0,
            "processing_time": 0,
        }

    async def start(self):
        """启动处理器"""
        await self.consumer.start()
        await self.producer.start()

    async def stop(self):
        """停止处理器"""
        await self.consumer.stop()
        await self.producer.stop()

    async def process(
        self,
        process_func: Callable,
        max_messages: int = None,
        error_handler: Callable = None,
        dead_letter_topic: str = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """处理消息流"""
        processed = 0
        async for message in self.consumer.consume():
            try:
                start_time = datetime.utcnow()

                # 处理消息
                result = await process_func(message)

                # 发送结果
                if result:
                    if "topic" not in result and self.output_topics:
                        result["topic"] = self.output_topics[0]
                    await self.producer.send_message(result)

                # 更新指标
                self.metrics["messages_processed"] += 1
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                self.metrics["processing_time"] += processing_time  # type: ignore

                processed += 1
                if max_messages and processed >= max_messages:
                    break

                yield result

            except Exception as e:
                self.metrics["messages_failed"] += 1
                if error_handler:
                    await error_handler(e, message)

                # 发送到死信队列
                if dead_letter_topic:
                    await self.producer.send_message(
                        {
                            "topic": dead_letter_topic,
                            "key": message.get("key"),
                            "value": {
                                "original_message": message,
                                "error": str(e),
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                            "headers": {"dlq": "true"},
                        }
                    )

    async def process_batch(
        self, batch_func: Callable, batch_size: int = 10
    ) -> AsyncIterator[Dict[str, Any]]:
        """批量处理消息"""
        batch = []
        async for message in self.consumer.consume():
            batch.append(message)

            if len(batch) >= batch_size:
                try:
                    result = await batch_func(batch)
                    self.metrics["messages_processed"] += len(batch)
                    yield result
                    batch = []
                except Exception:
                    self.metrics["messages_failed"] += len(batch)
                    batch = []

        # 处理剩余的消息
        if batch:
            try:
                result = await batch_func(batch)
                self.metrics["messages_processed"] += len(batch)
                yield result
            except Exception:
                self.metrics["messages_failed"] += len(batch)

    async def transform_message(
        self, message: Dict[str, Any], transformation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """转换消息"""
        result = {"key": message["key"], "value": {}, "topic": message.get("topic")}

        # 应用映射
        if "mapping" in transformation:
            for old_key, new_key in transformation["mapping"].items():
                if old_key in message["value"]:
                    result["value"][new_key] = message["value"][old_key]

        # 保留指定字段
        if "filters" in transformation:
            for field in transformation["filters"]:
                if field in message["value"]:
                    result["value"][field] = message["value"][field]

        return result

    async def aggregate(
        self, aggregate_func: Callable, window_size: timedelta, key_extractor: Callable
    ) -> AsyncIterator[Dict[str, Any]]:
        """聚合消息"""
        windows = {}

        async for message in self.consumer.consume():
            key = key_extractor(message)
            timestamp = datetime.utcnow()
            window_key = f"{key}_{timestamp // window_size}"  # type: ignore

            if window_key not in windows:
                windows[window_key] = {
                    "key": key,
                    "messages": [],
                    "window_start": timestamp,
                }

            windows[window_key]["messages"].append(message)

            # 检查窗口是否过期
            if timestamp - windows[window_key]["window_start"] > window_size:
                batch = windows.pop(window_key)
                try:
                    result = await aggregate_func(batch["key"], batch["messages"])
                    yield result
                except Exception:
                    self.metrics["messages_failed"] += len(batch["messages"])

    async def filter(self, filter_func: Callable) -> AsyncIterator[Dict[str, Any]]:
        """过滤消息"""
        async for message in self.consumer.consume():
            if filter_func(message):
                yield message

    async def join(
        self, stream1: str, stream2: str, join_func: Callable, window: timedelta
    ) -> AsyncIterator[Dict[str, Any]]:
        """连接两个流"""
        # 简化实现
        stream1_buffer = {}
        stream2_buffer = {}

        async for message in self.consumer.consume():
            if message["topic"] == stream1:
                stream1_buffer[message["key"]] = message
            elif message["topic"] == stream2:
                stream2_buffer[message["key"]] = message

            # 检查是否有匹配的键
            key = message["key"]
            if key in stream1_buffer and key in stream2_buffer:
                result = await join_func(stream1_buffer[key], stream2_buffer[key])
                if result:
                    yield result
                # 清理已处理的键
                stream1_buffer.pop(key, None)
                stream2_buffer.pop(key, None)

    def get_metrics(self) -> Dict[str, Any]:
        """获取处理指标"""
        return self.metrics.copy()

    async def process_windowed(
        self,
        window_func: Callable,
        window_size: timedelta,
        timestamp_extractor: Callable,
    ) -> AsyncIterator[Dict[str, Any]]:
        """窗口处理"""
        windows = {}

        async for message in self.consumer.consume():
            timestamp = timestamp_extractor(message)
            window_id = timestamp // window_size

            if window_id not in windows:
                windows[window_id] = {"messages": [], "start_time": timestamp}

            windows[window_id]["messages"].append(message)

            # 处理已关闭的窗口
            current_time = datetime.utcnow()
            closed_windows = [
                wid
                for wid, w in windows.items()
                if current_time - w["start_time"] > window_size * 2
            ]

            for wid in closed_windows:
                window = windows.pop(wid)
                if window["messages"]:
                    result = await window_func(window["messages"])
                    yield result


class MessageProcessor:
    """消息处理器"""

    def __init__(self, name: str, input_topic: str = None, output_topic: str = None):
        self.name = name
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.handlers = {}  # type: ignore

    def add_handler(self, event_type: str, handler: Callable):
        """添加事件处理器"""
        self.handlers[event_type] = handler

    def remove_handler(self, event_type: str):
        """移除事件处理器"""
        self.handlers.pop(event_type, None)

    def get_handler(self, event_type: str) -> Optional[Callable]:
        """获取事件处理器"""
        return self.handlers.get(event_type)


class BatchProcessor:
    """批量处理器"""

    def __init__(self, name: str, batch_size: int = 10, batch_timeout: float = 5.0):
        self.name = name
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.current_batch = []  # type: ignore
        self.metrics = {"batches_processed": 0, "total_messages_processed": 0}

    def add_to_batch(self, message: Dict[str, Any]):
        """添加消息到批次"""
        self.current_batch.append(message)

    def is_batch_ready(self) -> bool:
        """检查批次是否准备好处理"""
        return len(self.current_batch) >= self.batch_size

    def clear_batch(self):
        """清空批次"""
        self.current_batch = []

    def get_batch(self) -> List[Dict[str, Any]]:
        """获取当前批次"""
        return self.current_batch.copy()

    def get_metrics(self) -> Dict[str, Any]:
        """获取批次指标"""
        return {**self.metrics, "current_batch_size": len(self.current_batch)}
