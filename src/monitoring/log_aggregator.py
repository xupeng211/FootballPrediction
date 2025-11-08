"""
企业级日志聚合分析系统
Enterprise Log Aggregation and Analysis System

提供日志收集、解析、存储、查询和分析功能。
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================================
# 日志数据结构
# ============================================================================


class LogLevel(Enum):
    """日志级别"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogSource(Enum):
    """日志来源"""

    APPLICATION = "application"
    ACCESS = "access"
    ERROR = "error"
    SYSTEM = "system"
    AUDIT = "audit"


@dataclass
class LogEntry:
    """日志条目"""

    id: str
    timestamp: datetime
    level: LogLevel
    source: LogSource
    message: str
    module: str | None = None
    function: str | None = None
    line_number: int | None = None
    thread_id: str | None = None
    process_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    status_code: int | None = None
    response_time: float | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_message: str | None = None


@dataclass
class LogQuery:
    """日志查询"""

    keyword: str | None = None
    level: LogLevel | None = None
    source: LogSource | None = None
    module: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    tags: list[str] = field(default_factory=list)
    metadata_filter: dict[str, Any] = field(default_factory=dict)
    limit: int = 100
    offset: int = 0


@dataclass
class LogStatistics:
    """日志统计"""

    total_count: int
    level_counts: dict[LogLevel, int]
    source_counts: dict[LogSource, int]
    hourly_counts: dict[str, int]
    error_rate: float
    avg_response_time: float
    top_errors: list[dict[str, Any]]
    top_modules: list[dict[str, Any]]


# ============================================================================
# 日志解析器
# ============================================================================


class LogParser(ABC):
    """日志解析器基类"""

    @abstractmethod
    def parse(self, message: str) -> LogEntry | None:
        """解析日志消息"""
        pass


class PythonLogParser(LogParser):
    """Python日志解析器"""

    # Python日志正则表达式
    LOG_PATTERN = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s+"
        r"(?P<level>[A-Z]+)\s+"
        r"(?P<module>\w+)\s+"
        r"(?P<message>.*)"
    )

    # 详细日志格式（包含文件名和行号）
    DETAILED_PATTERN = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s+"
        r"(?P<level>[A-Z]+)\s+"
        r"(?P<module>\w+)\s+"
        r"(?P<function>\w+)\s+"
        r"(?P<filename>[^:]+):(?P<line_number>\d+)\s+"
        r"(?P<message>.*)"
    )

    def parse(self, message: str) -> LogEntry | None:
        """解析Python日志"""
        try:
            # 尝试详细格式
            match = self.DETAILED_PATTERN.match(message)
            if match:
                return self._create_log_entry_from_match(
                    match, message, LogSource.APPLICATION
                )

            # 尝试标准格式
            match = self.LOG_PATTERN.match(message)
            if match:
                return self._create_log_entry_from_match(
                    match, message, LogSource.APPLICATION
                )

            return None

        except Exception as e:
            logger.warning(f"解析Python日志失败: {e}, 消息: {message[:100]}")
            return None

    def _create_log_entry_from_match(
        self, match: re.Match, raw_message: str, source: LogSource
    ) -> LogEntry:
        """从匹配结果创建日志条目"""
        import uuid
        from datetime import datetime

        # 解析时间戳
        timestamp_str = match.group("timestamp")
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f").replace(
            tzinfo=UTC
        )

        # 解析级别
        level_str = match.group("level")
        try:
            level = LogLevel(level_str)
        except ValueError:
            level = LogLevel.INFO

        # 创建日志条目
        log_entry = LogEntry(
            id=str(uuid.uuid4()),
            timestamp=timestamp,
            level=level,
            source=source,
            message=match.group("message"),
            module=match.group("module"),
            raw_message=raw_message,
        )

        # 添加详细信息（如果存在）
        if "function" in match.groupdict():
            log_entry.function = match.group("function")
            log_entry.line_number = int(match.group("line_number"))

        return log_entry


class AccessLogParser(LogParser):
    """访问日志解析器"""

    # Nginx/Apache访问日志格式
    ACCESS_LOG_PATTERN = re.compile(
        r"(?P<ip>\S+)\s+\S+\s+\S+\s+"
        r"\[(?P<timestamp>[^\]]+)\]\s+"
        r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>\S+)"\s+'
        r"(?P<status>\d+)\s+(?P<size>\S+)\s+"
        r'"(?P<referer>[^"]*)"\s+'
        r'"(?P<user_agent>[^"]*)"'
    )

    def parse(self, message: str) -> LogEntry | None:
        """解析访问日志"""
        try:
            match = self.ACCESS_LOG_PATTERN.match(message)
            if not match:
                return None

            import uuid
            from datetime import datetime

            # 解析时间戳
            timestamp_str = match.group("timestamp")
            # 尝试不同的时间格式
            timestamp_formats = [
                "%d/%b/%Y:%H:%M:%S %z",  # Apache格式
                "%d/%b/%Y:%H:%M:%S %z",  # Nginx格式
            ]

            timestamp = None
            for fmt in timestamp_formats:
                try:
                    timestamp = datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue

            if not timestamp:
                timestamp = datetime.now(UTC)

            # 解析状态码
            status_code = int(match.group("status"))

            # 确定日志级别
            if status_code >= 500:
                level = LogLevel.ERROR
            elif status_code >= 400:
                level = LogLevel.WARNING
            else:
                level = LogLevel.INFO

            return LogEntry(
                id=str(uuid.uuid4()),
                timestamp=timestamp,
                level=level,
                source=LogSource.ACCESS,
                message=f"{match.group('method')} {match.group('path')} {match.group('status')}",
                ip_address=match.group("ip"),
                status_code=status_code,
                metadata={
                    "method": match.group("method"),
                    "path": match.group("path"),
                    "protocol": match.group("protocol"),
                    "size": match.group("size"),
                    "referer": match.group("referer"),
                    "user_agent": match.group("user_agent"),
                },
                raw_message=message,
            )

        except Exception as e:
            logger.warning(f"解析访问日志失败: {e}, 消息: {message[:100]}")
            return None


class ErrorLogParser(LogParser):
    """错误日志解析器"""

    # 错误日志正则表达式
    ERROR_PATTERN = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+"
        r"\[(?P<level>[^\]]+)\]\s+"
        r"(?P<module>\w+):(?P<message>.*)"
    )

    def parse(self, message: str) -> LogEntry | None:
        """解析错误日志"""
        try:
            match = self.ERROR_PATTERN.match(message)
            if not match:
                return None

            import uuid
            from datetime import datetime

            # 解析时间戳
            timestamp_str = match.group("timestamp")
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=UTC
            )

            # 解析级别
            level_str = match.group("level").upper()
            try:
                level = LogLevel(level_str)
            except ValueError:
                level = LogLevel.ERROR

            return LogEntry(
                id=str(uuid.uuid4()),
                timestamp=timestamp,
                level=level,
                source=LogSource.ERROR,
                message=match.group("message"),
                module=match.group("module"),
                raw_message=message,
            )

        except Exception as e:
            logger.warning(f"解析错误日志失败: {e}, 消息: {message[:100]}")
            return None


# ============================================================================
# 日志收集器
# ============================================================================


class LogCollector:
    """日志收集器"""

    def __init__(self):
        self.parsers: list[LogParser] = []
        self.log_buffer: deque[LogEntry] = deque(maxlen=10000)
        self.listeners: list[callable] = []
        self._running = False
        self._file_watchers: dict[str, asyncio.Task] = {}

    def add_parser(self, parser: LogParser):
        """添加解析器"""
        self.parsers.append(parser)

    def add_listener(self, callback: callable):
        """添加监听器"""
        self.listeners.append(callback)

    async def start_collection(self):
        """开始日志收集"""
        if self._running:
            return

        self._running = True

        # 添加默认解析器
        if not self.parsers:
            self.add_parser(PythonLogParser())
            self.add_parser(AccessLogParser())
            self.add_parser(ErrorLogParser())

        logger.info("日志收集器已启动")

    async def stop_collection(self):
        """停止日志收集"""
        self._running = False

        # 停止文件监视器
        for watcher in self._file_watchers.values():
            watcher.cancel()

        self._file_watchers.clear()
        logger.info("日志收集器已停止")

    async def parse_and_store(
        self, message: str, source: LogSource = LogSource.APPLICATION
    ):
        """解析并存储日志消息"""
        if not self._running:
            return

        log_entry = None

        # 尝试使用所有解析器
        for parser in self.parsers:
            log_entry = parser.parse(message)
            if log_entry:
                log_entry.source = source
                break

        # 如果没有解析器能处理，创建基本日志条目
        if not log_entry:
            import uuid

            log_entry = LogEntry(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(UTC),
                level=LogLevel.INFO,
                source=source,
                message=message,
                raw_message=message,
            )

        # 添加到缓冲区
        self.log_buffer.append(log_entry)

        # 通知监听器
        for listener in self.listeners:
            try:
                await listener(log_entry)
            except Exception as e:
                logger.error(f"日志监听器处理失败: {e}")

    async def watch_file(
        self, file_path: str, source: LogSource = LogSource.APPLICATION
    ):
        """监视日志文件"""
        if not Path(file_path).exists():
            logger.warning(f"日志文件不存在: {file_path}")
            return

        # 创建文件监视任务
        task = asyncio.create_task(self._watch_file_loop(file_path, source))
        self._file_watchers[file_path] = task
        logger.info(f"开始监视日志文件: {file_path}")

    async def _watch_file_loop(self, file_path: str, source: LogSource):
        """文件监视循环"""
        try:
            with open(file_path, encoding="utf-8") as file:
                # 跳到文件末尾
                file.seek(0, 2)

                while self._running:
                    line = file.readline()
                    if line:
                        line = line.strip()
                        if line:
                            await self.parse_and_store(line, source)
                    else:
                        await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"监视文件失败 {file_path}: {e}")

    def get_logs(self, query: LogQuery) -> list[LogEntry]:
        """查询日志"""
        filtered_logs = []

        for log_entry in self.log_buffer:
            if self._matches_query(log_entry, query):
                filtered_logs.append(log_entry)

        # 排序和分页
        filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
        start_idx = query.offset
        end_idx = start_idx + query.limit

        return filtered_logs[start_idx:end_idx]

    def _matches_query(self, log_entry: LogEntry, query: LogQuery) -> bool:
        """检查日志条目是否匹配查询条件"""
        # 时间范围过滤
        if query.start_time and log_entry.timestamp < query.start_time:
            return False
        if query.end_time and log_entry.timestamp > query.end_time:
            return False

        # 级别过滤
        if query.level and log_entry.level != query.level:
            return False

        # 来源过滤
        if query.source and log_entry.source != query.source:
            return False

        # 模块过滤
        if query.module and log_entry.module != query.module:
            return False

        # 关键词过滤
        if query.keyword:
            if (
                query.keyword.lower() not in log_entry.message.lower()
                and query.keyword.lower() not in (log_entry.module or "").lower()
            ):
                return False

        # 标签过滤
        if query.tags:
            if not any(tag in log_entry.tags for tag in query.tags):
                return False

        # 元数据过滤
        for key, value in query.metadata_filter.items():
            if log_entry.metadata.get(key) != value:
                return False

        return True


# ============================================================================
# 日志分析器
# ============================================================================


class LogAnalyzer:
    """日志分析器"""

    def __init__(self, log_collector: LogCollector):
        self.log_collector = log_collector

    def analyze_logs(self, query: LogQuery, hours: int = 24) -> LogStatistics:
        """分析日志"""
        # 设置时间范围
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=hours)
        query.start_time = start_time
        query.end_time = end_time
        query.limit = 10000  # 分析时获取更多数据

        logs = self.log_collector.get_logs(query)

        if not logs:
            return self._empty_statistics()

        # 计算统计信息
        stats = LogStatistics(
            total_count=len(logs),
            level_counts=self._count_by_level(logs),
            source_counts=self._count_by_source(logs),
            hourly_counts=self._count_by_hour(logs),
            error_rate=self._calculate_error_rate(logs),
            avg_response_time=self._calculate_avg_response_time(logs),
            top_errors=self._get_top_errors(logs),
            top_modules=self._get_top_modules(logs),
        )

        return stats

    def _empty_statistics(self) -> LogStatistics:
        """空统计信息"""
        return LogStatistics(
            total_count=0,
            level_counts={},
            source_counts={},
            hourly_counts={},
            error_rate=0.0,
            avg_response_time=0.0,
            top_errors=[],
            top_modules=[],
        )

    def _count_by_level(self, logs: list[LogEntry]) -> dict[LogLevel, int]:
        """按级别统计"""
        counts = defaultdict(int)
        for log in logs:
            counts[log.level] += 1
        return dict(counts)

    def _count_by_source(self, logs: list[LogEntry]) -> dict[LogSource, int]:
        """按来源统计"""
        counts = defaultdict(int)
        for log in logs:
            counts[log.source] += 1
        return dict(counts)

    def _count_by_hour(self, logs: list[LogEntry]) -> dict[str, int]:
        """按小时统计"""
        counts = defaultdict(int)
        for log in logs:
            hour_key = log.timestamp.strftime("%Y-%m-%d %H:00")
            counts[hour_key] += 1
        return dict(counts)

    def _calculate_error_rate(self, logs: list[LogEntry]) -> float:
        """计算错误率"""
        total = len(logs)
        if total == 0:
            return 0.0

        error_count = sum(
            1 for log in logs if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        )
        return (error_count / total) * 100

    def _calculate_avg_response_time(self, logs: list[LogEntry]) -> float:
        """计算平均响应时间"""
        response_times = [
            log.response_time for log in logs if log.response_time is not None
        ]
        if not response_times:
            return 0.0
        return sum(response_times) / len(response_times)

    def _get_top_errors(
        self, logs: list[LogEntry], limit: int = 10
    ) -> list[dict[str, Any]]:
        """获取最常见的错误"""
        error_logs = [
            log for log in logs if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        ]
        error_counts = defaultdict(int)

        for log in error_logs:
            # 使用模块名和消息的前50个字符作为错误标识
            error_key = f"{log.module or 'unknown'}: {log.message[:50]}"
            error_counts[error_key] += 1

        # 排序并返回前N个
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                "error": error,
                "count": count,
                "percentage": (count / len(error_logs)) * 100 if error_logs else 0,
            }
            for error, count in sorted_errors[:limit]
        ]

    def _get_top_modules(
        self, logs: list[LogEntry], limit: int = 10
    ) -> list[dict[str, Any]]:
        """获取最活跃的模块"""
        module_counts = defaultdict(int)
        for log in logs:
            if log.module:
                module_counts[log.module] += 1

        sorted_modules = sorted(module_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                "module": module,
                "count": count,
                "percentage": (count / len(logs)) * 100 if logs else 0,
            }
            for module, count in sorted_modules[:limit]
        ]


# ============================================================================
# 全局实例
# ============================================================================

# 创建全局日志收集器
log_collector = LogCollector()

# 创建全局日志分析器
log_analyzer = LogAnalyzer(log_collector)
