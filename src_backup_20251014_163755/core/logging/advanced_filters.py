"""
高级日志过滤器
用于生产环境的日志处理
"""

import re
import json
import time
import hashlib
import logging
import asyncio
from typing import Any, Dict, List, Optional, Set, Union
from collections import defaultdict, deque
import threading
from datetime import datetime, timedelta


class SensitiveDataFilter(logging.Filter):
    """敏感数据过滤器"""

    def __init__(self, patterns: Optional[List[str]] = None):
        super().__init__()
        self.patterns = patterns or [
            "password",
            "token",
            "secret",
            "key",
            "authorization",
            "cookie",
            "session",
            "credential",
            "private",
        ]
        self.regex_patterns = [
            re.compile(rf'{pattern}["\']?\s*[:=]\s*["\']?([^"\']\s,]+)', re.IGNORECASE)
            for pattern in self.patterns
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤敏感数据"""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = self._sanitize_data(record.msg)

        if hasattr(record, "args") and record.args:
            record.args = tuple(
                self._sanitize_data(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )

        return True

    def _sanitize_data(self, data: str) -> str:
        """清理敏感数据"""
        for pattern in self.regex_patterns:
            data = pattern.sub(lambda m: f"{m.group(0).split(m.group(1))[0]}***", data)

        # 额外的模式匹配
        patterns = [
            (r"Bearer\s+([a-zA-Z0-9\._-]+)", r"Bearer ***"),
            (r"Basic\s+([a-zA-Z0-9+/=]+)", r"Basic ***"),
            (r'{"password":\s*"[^"]*"}', '{"password":"***"}'),
            (r'"secret":\s*"[^"]*"', '"secret":"***"'),
        ]

        for pattern, replacement in patterns:
            data = re.sub(pattern, replacement, data, flags=re.IGNORECASE)

        return data


class RateLimitFilter(logging.Filter):
    """速率限制过滤器"""

    def __init__(self, rate: int = 100, window: int = 60):
        super().__init__()
        self.rate = rate
        self.window = window
        self.messages: Dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def filter(self, record: logging.LogRecord) -> bool:
        """检查是否应该记录日志"""
        message_hash = self._get_message_hash(record.getMessage())
        timestamp = time.time()

        with self.lock:
            message_queue = self.messages[message_hash]

            # 清理过期的消息
            while message_queue and timestamp - message_queue[0] > self.window:
                message_queue.popleft()

            # 检查速率
            if len(message_queue) >= self.rate:
                return False

            message_queue.append(timestamp)

        return True

    def _get_message_hash(self, message: str) -> str:
        """获取消息哈希"""
        return hashlib.md5(message.encode()).hexdigest()


class ContextFilter(logging.Filter):
    """上下文过滤器 - 添加请求/追踪信息"""

    def __init__(self):
        super().__init__()
        self.context = threading.local()

    def filter(self, record: logging.LogRecord) -> bool:
        """添加上下文信息"""
        # 添加线程ID
        record.thread_id = threading.get_ident()

        # 添加进程ID
        record.process_id = record.process

        # 添加时间戳（ISO格式）
        record.timestamp = datetime.utcnow().isoformat() + "Z"

        # 添加主机信息
        import socket

        record.hostname = socket.gethostname()

        # 添加环境信息
        import os

        record.environment = os.getenv("ENVIRONMENT", "unknown")
        record.service = os.getenv("SERVICE_NAME", "football-prediction")
        record.version = os.getenv("APP_VERSION", "1.0.0")

        # 添加请求ID（如果存在）
        if hasattr(self.context, "request_id"):
            record.request_id = self.context.request_id

        # 添加用户ID（如果存在）
        if hasattr(self.context, "user_id"):
            record.user_id = self.context.user_id

        # 添加追踪ID（如果存在）
        if hasattr(self.context, "trace_id"):
            record.trace_id = self.context.trace_id

        if hasattr(self.context, "span_id"):
            record.span_id = self.context.span_id

        return True

    def set_request_id(self, request_id: str):
        """设置请求ID"""
        self.context.request_id = request_id

    def set_user_id(self, user_id: str):
        """设置用户ID"""
        self.context.user_id = user_id

    def set_trace_id(self, trace_id: str):
        """设置追踪ID"""
        self.context.trace_id = trace_id

    def set_span_id(self, span_id: str):
        """设置Span ID"""
        self.context.span_id = span_id


class RequestIDFilter(logging.Filter):
    """请求ID过滤器 - 从请求头提取并添加到日志"""

    def __init__(self, header_name: str = "X-Request-ID"):
        super().__init__()
        self.header_name = header_name
        self.generator = self._id_generator()

    def filter(self, record: logging.LogRecord) -> bool:
        """添加请求ID"""
        if not hasattr(record, "request_id") or not record.request_id:
            record.request_id = next(self.generator)

        return True

    def _id_generator(self):
        """生成唯一ID"""
        while True:
            yield f"{int(time.time() * 1000)}-{id(self)}"


class AsyncLogFilter(logging.Filter):
    """异步日志过滤器 - 防止日志阻塞主线程"""

    def __init__(self, queue_size: int = 1000):
        super().__init__()
        self.queue_size = queue_size
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.task = None

    async def start(self):
        """启动异步处理任务"""
        self.task = asyncio.create_task(self._process_logs())

    async def stop(self):
        """停止异步处理"""
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def _process_logs(self):
        """异步处理日志"""
        while True:
            try:
                record = await self.queue.get()
                await self._handle_record(record)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"日志处理错误: {e}")

    async def _handle_record(self, record):
        """处理日志记录"""
        # 这里可以添加异步的处理逻辑
        # 例如发送到外部服务、写入数据库等
        pass

    def filter(self, record: logging.LogRecord) -> bool:
        """异步处理日志"""
        try:
            self.queue.put_nowait(record)
        except asyncio.QueueFull:
            # 队列满时的处理策略
            return False

        return True


class SamplingFilter(logging.Filter):
    """采样过滤器 - 减少日志量"""

    def __init__(self, rate: float = 0.1, seed: Optional[int] = None):
        super().__init__()
        self.rate = rate
        self.seed = seed or int(time.time())
        self.counter = 0

    def filter(self, record: logging.LogRecord) -> bool:
        """根据采样率决定是否记录"""
        # 错误级别始终记录
        if record.levelno >= logging.ERROR:
            return True

        # 使用计数器采样
        self.counter += 1
        if self.counter % int(1 / self.rate) == 0:
            return True

        # 使用哈希采样（基于消息内容）
        import hashlib

        message_hash = int(hashlib.md5(record.getMessage().encode()).hexdigest(), 16)
        return (message_hash % 100) < (self.rate * 100)


class StructuredFilter(logging.Filter):
    """结构化日志过滤器 - 确保日志是有效的JSON"""

    def filter(self, record: logging.LogRecord) -> bool:
        """确保日志可以序列化为JSON"""
        try:
            # 尝试序列化记录
            self._serialize_record(record)
            return True
        except (TypeError, ValueError):
            # 如果无法序列化，转换为字符串
            if hasattr(record, "msg"):
                record.msg = str(record.msg)
            return True

    def _serialize_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """序列化日志记录"""
        data = {
            "timestamp": record.timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 添加可选字段
        optional_fields = [
            "module",
            "function",
            "line",
            "process",
            "thread",
            "service",
            "environment",
            "version",
            "hostname",
            "request_id",
            "user_id",
            "trace_id",
            "span_id",
        ]

        for field in optional_fields:
            if hasattr(record, field):
                data[field] = getattr(record, field)

        # 添加异常信息
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)

        return data


class EnrichmentFilter(logging.Filter):
    """增强过滤器 - 添加额外的元数据"""

    def __init__(self, metadata: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.metadata = metadata or {}

    def filter(self, record: logging.LogRecord) -> bool:
        """添加元数据"""
        # 添加自定义元数据
        for key, value in self.metadata.items():
            setattr(record, key, value)

        # 添加运行时信息
        import sys

        record.python_version = sys.version

        # 添加依赖版本
        try:
            import fastapi

            record.fastapi_version = fastapi.__version__
        except ImportError:
            pass

        try:
            import sqlalchemy

            record.sqlalchemy_version = sqlalchemy.__version__
        except ImportError:
            pass

        return True


class PerformanceFilter(logging.Filter):
    """性能过滤器 - 监控日志性能"""

    def __init__(self, max_size: int = 10000):
        super().__init__()
        self.max_size = max_size
        self.slow_logs = deque(maxlen=100)
        self.lock = threading.Lock()

    def filter(self, record: logging.LogRecord) -> bool:
        """记录慢日志"""
        message_size = len(str(record.getMessage()))

        if message_size > self.max_size:
            # 截断过长的消息
            if hasattr(record, "msg"):
                record.msg = record.msg[: self.max_size] + "... [TRUNCATED]"

        # 记录慢日志（用于分析）
        start_time = getattr(record, "start_time", None)
        if start_time:
            duration = time.time() - start_time
            if duration > 1.0:  # 超过1秒的日志
                with self.lock:
                    self.slow_logs.append(
                        {
                            "message": record.getMessage(),
                            "duration": duration,
                            "timestamp": time.time(),
                        }
                    )

        return True

    def get_slow_logs(self) -> List[Dict[str, Any]:
        """获取慢日志列表"""
        with self.lock:
            return list(self.slow_logs)


class AggregateFilter(logging.Filter):
    """聚合过滤器 - 聚合相似的日志"""

    def __init__(self, window: int = 60, threshold: int = 10):
        super().__init__()
        self.window = window
        self.threshold = threshold
        self.aggregated: Dict[str, Dict[str, Any] = {}
        self.lock = threading.Lock()

    def filter(self, record: logging.LogRecord) -> bool:
        """聚合日志"""
        message = record.getMessage()
        level = record.levelname
        logger = record.name

        # 创建聚合键
        key = f"{logger}:{level}:{message[:100]}"

        with self.lock:
            now = time.time()

            # 清理过期的聚合
            self._cleanup_expired(now)

            # 更新或创建聚合
            if key in self.aggregated:
                agg = self.aggregated[key]
                agg["count"] += 1
                agg["last_seen"] = now
            else:
                self.aggregated[key] = {
                    "message": message,
                    "level": level,
                    "logger": logger,
                    "count": 1,
                    "first_seen": now,
                    "last_seen": now,
                }

            # 达到阈值时输出聚合日志
            if self.aggregated[key]["count"] == self.threshold:
                self._output_aggregated(key)
                return False  # 阻止原始日志输出

        return True

    def _cleanup_expired(self, now: float):
        """清理过期的聚合"""
        expired_keys = []
        for key, agg in self.aggregated.items():
            if now - agg["last_seen"] > self.window:
                expired_keys.append(key)

        for key in expired_keys:
            if self.aggregated[key]["count"] < self.threshold:
                # 输出未达到阈值的聚合
                self._output_aggregated(key)
            del self.aggregated[key]

    def _output_aggregated(self, key: str):
        """输出聚合日志"""
        agg = self.aggregated[key]
        logger = logging.getLogger(agg["logger"])

        message = (
            f"[AGGREGATED] {agg['message']} "
            f"(occurred {agg['count']} times "
            f"between {datetime.fromtimestamp(agg['first_seen'])} "
            f"and {datetime.fromtimestamp(agg['last_seen'])})"
        )

        logger.log(getattr(logging, agg["level"]), message)
