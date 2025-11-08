"""
日志系统集成
Log System Integration

与现有日志系统集成，自动收集和分析应用日志。
"""

import asyncio
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from .log_aggregator import LogCollector, LogLevel, LogSource, log_collector

logger = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """自定义日志处理器，将日志发送到聚合系统"""

    def __init__(
        self, collector: LogCollector, source: LogSource = LogSource.APPLICATION
    ):
        super().__init__()
        self.collector = collector
        self.source = source

    def emit(self, record: logging.LogRecord):
        """发送日志记录"""
        try:
            # 创建日志消息
            message = self.format(record)

            # 异步发送
            asyncio.create_task(self.collector.parse_and_store(message, self.source))
        except Exception as e:
            logger.error(f"发送日志到聚合系统失败: {e}")


class PythonLoggingIntegration:
    """Python日志系统集成"""

    def __init__(self, collector: LogCollector):
        self.collector = collector
        self.handlers: dict[str, logging.Handler] = {}

    def setup_handler(
        self,
        logger_name: str = "",
        source: LogSource = LogSource.APPLICATION,
        level: int = logging.INFO,
        format_string: str | None = None,
    ) -> bool:
        """设置日志处理器"""
        try:
            # 创建处理器
            handler = LogHandler(self.collector, source)
            handler.setLevel(level)

            # 设置格式
            if format_string:
                formatter = logging.Formatter(format_string)
                handler.setFormatter(formatter)
            else:
                formatter = logging.Formatter(
                    "%(asctime)s,%(msecs)d %(levelname)s %(module)s %(message)s"
                )
                handler.setFormatter(formatter)

            # 获取logger
            target_logger = (
                logging.getLogger(logger_name) if logger_name else logging.getLogger()
            )
            target_logger.addHandler(handler)
            target_logger.setLevel(level)

            # 保存处理器引用
            handler_id = f"{logger_name or 'root'}_{source.value}"
            self.handlers[handler_id] = handler

            logger.info(f"日志处理器已设置: {handler_id}")
            return True

        except Exception as e:
            logger.error(f"设置日志处理器失败: {e}")
            return False

    def remove_handler(
        self, logger_name: str = "", source: LogSource = LogSource.APPLICATION
    ):
        """移除日志处理器"""
        try:
            handler_id = f"{logger_name or 'root'}_{source.value}"

            if handler_id in self.handlers:
                handler = self.handlers[handler_id]
                target_logger = (
                    logging.getLogger(logger_name)
                    if logger_name
                    else logging.getLogger()
                )
                target_logger.removeHandler(handler)
                del self.handlers[handler_id]

                logger.info(f"日志处理器已移除: {handler_id}")
                return True
            else:
                logger.warning(f"日志处理器不存在: {handler_id}")
                return False

        except Exception as e:
            logger.error(f"移除日志处理器失败: {e}")
            return False


class FileLogWatcher:
    """文件日志监视器"""

    def __init__(self, collector: LogCollector):
        self.collector = collector
        self.watch_tasks: dict[str, asyncio.Task] = {}

    async def watch_log_file(
        self,
        file_path: str,
        source: LogSource = LogSource.APPLICATION,
        auto_detect_parser: bool = True,
    ):
        """监视日志文件"""
        try:
            # 检测日志文件格式
            if auto_detect_parser:
                detected_source = await self._detect_log_source(file_path)
                if detected_source:
                    source = detected_source

            # 启动文件监视
            await self.collector.watch_file(file_path, source)

            logger.info(f"文件日志监视已启动: {file_path} (源: {source.value})")

        except Exception as e:
            logger.error(f"启动文件日志监视失败 {file_path}: {e}")

    async def _detect_log_source(self, file_path: str) -> LogSource | None:
        """自动检测日志文件来源"""
        try:
            if not Path(file_path).exists():
                return None

            # 读取文件开头的几行
            with open(file_path, encoding="utf-8", errors="ignore") as file:
                lines = []
                for _ in range(10):
                    line = file.readline()
                    if not line:
                        break
                    lines.append(line.strip())

                # 分析日志格式
                return self._analyze_log_format(lines)

        except Exception as e:
            logger.warning(f"检测日志文件格式失败 {file_path}: {e}")
            return None

    def _analyze_log_format(self, lines: list[str]) -> LogSource | None:
        """分析日志格式"""
        if not lines:
            return None

        # 检测访问日志格式
        access_patterns = [
            r'\d+\.\d+\.\d+\.\d+.*?\[.*?\].*?"GET.*?"\s+\d+',
            r'\S+\s+\S+\s+\S+\s+\[.*?\].*?"\w+\s+.*?"\s+\d+',
        ]

        for pattern in access_patterns:
            if any(re.search(pattern, line) for line in lines):
                return LogSource.ACCESS

        # 检测错误日志格式
        error_patterns = [
            r"\[.*?ERROR.*?\]",
            r"\[.*?CRITICAL.*?\]",
            r"\[.*?FATAL.*?\]",
            r"Traceback \(most recent call last\):",
        ]

        for pattern in error_patterns:
            if any(re.search(pattern, line) for line in lines):
                return LogSource.ERROR

        # 检测系统日志格式
        system_patterns = [
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.*?systemd.*?",
            r"\w+\s+\d+\s+\d{2}:\d{2}:\d{2}.*?\w+:\s+",
        ]

        for pattern in system_patterns:
            if any(re.search(pattern, line) for line in lines):
                return LogSource.SYSTEM

        return LogSource.APPLICATION


class LogBufferManager:
    """日志缓冲区管理器"""

    def __init__(self, collector: LogCollector):
        self.collector = collector
        self.buffer_limit = 10000
        self.flush_interval = 60  # 秒
        self._running = False
        self._flush_task: asyncio.Task | None = None

    async def start_buffering(self):
        """开始缓冲管理"""
        if self._running:
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._buffer_loop())
        logger.info("日志缓冲管理器已启动")

    async def stop_buffering(self):
        """停止缓冲管理"""
        if not self._running:
            return

        self._running = False
        if self._flush_task:
            self._flush_task.cancel()

        logger.info("日志缓冲管理器已停止")

    async def _buffer_loop(self):
        """缓冲管理循环"""
        while self._running:
            try:
                # 检查缓冲区大小
                if len(self.collector.log_buffer) > self.buffer_limit:
                    logger.warning(
                        f"日志缓冲区过大 ({len(self.collector.log_buffer)}), 清理旧日志"
                    )
                    # 保留最新的一半日志
                    new_size = len(self.collector.log_buffer) // 2
                    while len(self.collector.log_buffer) > new_size:
                        self.collector.log_buffer.popleft()

                # 等待下次检查
                await asyncio.sleep(self.flush_interval)

            except Exception as e:
                logger.error(f"缓冲管理循环错误: {e}")
                await asyncio.sleep(self.flush_interval)


class LogAnalytics:
    """日志分析器"""

    def __init__(self, collector: LogCollector):
        self.collector = collector
        self.analysis_tasks: list[asyncio.Task] = []

    async def start_realtime_analysis(self):
        """开始实时分析"""
        try:
            # 添加监听器
            self.collector.add_listener(self._analyze_log_entry)
            logger.info("实时日志分析已启动")

        except Exception as e:
            logger.error(f"启动实时日志分析失败: {e}")

    async def _analyze_log_entry(self, log_entry):
        """分析单个日志条目"""
        try:
            # 检测异常模式
            await self._detect_anomalies(log_entry)

            # 检测性能问题
            await self._detect_performance_issues(log_entry)

            # 检测安全事件
            await self._detect_security_events(log_entry)

        except Exception as e:
            logger.error(f"分析日志条目失败: {e}")

    async def _detect_anomalies(self, log_entry):
        """检测异常模式"""
        # 检测错误激增
        if log_entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            # 计算最近1分钟的错误数量
            recent_errors = sum(
                1
                for log in self.collector.log_buffer
                if (
                    log.level in [LogLevel.ERROR, LogLevel.CRITICAL]
                    and (datetime.now(UTC) - log.timestamp).total_seconds() < 60
                )
            )

            if recent_errors > 10:  # 1分钟内超过10个错误
                logger.warning(f"检测到错误激增: {recent_errors} 个错误/分钟")

    async def _detect_performance_issues(self, log_entry):
        """检测性能问题"""
        # 检查响应时间
        if log_entry.response_time and log_entry.response_time > 5.0:
            logger.warning(
                f"检测到慢响应: {log_entry.response_time}s - {log_entry.message}"
            )

        # 检查HTTP错误
        if log_entry.status_code and log_entry.status_code >= 500:
            logger.warning(
                f"检测到服务器错误: {log_entry.status_code} - {log_entry.message}"
            )

    async def _detect_security_events(self, log_entry):
        """检测安全事件"""
        # 检查可疑IP
        suspicious_patterns = [
            r"192\.168\.",
            r"10\.",
            r"172\.",
        ]

        if log_entry.ip_address:
            import re

            for pattern in suspicious_patterns:
                if re.search(pattern, log_entry.ip_address):
                    logger.info(f"检测到内网访问: {log_entry.ip_address}")

        # 检查可疑用户代理
        suspicious_agents = [
            "curl",
            "wget",
            "python-requests",
            "sqlmap",
            "nmap",
        ]

        if log_entry.user_agent:
            for agent in suspicious_agents:
                if agent.lower() in log_entry.user_agent.lower():
                    logger.info(f"检测到可疑用户代理: {agent}")


# ============================================================================
# 初始化函数
# ============================================================================


async def initialize_log_system():
    """初始化日志系统"""
    try:
        # 启动日志收集器
        await log_collector.start_collection()

        # 设置Python日志集成
        py_integration = PythonLoggingIntegration(log_collector)

        # 为根logger设置处理器
        py_integration.setup_handler(
            logger_name="",
            source=LogSource.APPLICATION,
            level=logging.INFO,
            format_string="%(asctime)s,%(msecs)d %(levelname)s %(name)s %(message)s",
        )

        # 创建文件监视器
        FileLogWatcher(log_collector)

        # 创建缓冲区管理器
        buffer_manager = LogBufferManager(log_collector)
        await buffer_manager.start_buffering()

        # 创建实时分析器
        analytics = LogAnalytics(log_collector)
        await analytics.start_realtime_analysis()

        logger.info("日志系统集成初始化完成")
        return True

    except Exception as e:
        logger.error(f"初始化日志系统失败: {e}")
        return False


def setup_python_logging():
    """设置Python日志系统"""
    try:
        # 创建自定义处理器
        handler = LogHandler(log_collector, LogSource.APPLICATION)
        handler.setLevel(logging.INFO)

        # 设置格式
        formatter = logging.Formatter(
            "%(asctime)s,%(msecs)d %(levelname)s %(name)s %(module)s %(message)s"
        )
        handler.setFormatter(formatter)

        # 添加到根logger
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

        logger.info("Python日志系统已设置")

    except Exception as e:
        logger.error(f"设置Python日志系统失败: {e}")
