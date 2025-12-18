#!/usr/bin/env python3
"""
智能日志系统 - Sprint 4 核心组件

针对50GB大数据处理的日志优化系统。
提供分级过滤、压缩存储和智能日志管理。

设计原则:
- Log Level Filtering (日志分级过滤)
- Intelligent Rotation (智能轮转)
- Compression Support (压缩支持)
- Performance Impact Minimal (最小性能影响)
"""

import logging
import logging.handlers
import gzip
import json
import os
import sys
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time
import psutil
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class LoggingConfig:
    """日志配置"""
    # 日志级别配置
    level: str = "INFO"
    console_level: str = "WARNING"
    file_level: str = "INFO"
    debug_level: str = "DEBUG"

    # 文件配置
    log_dir: str = "logs"
    max_file_size_mb: int = 100  # 100MB
    backup_count: int = 5
    enable_compression: bool = True
    compression_level: int = 6

    # 性能配置
    buffer_size: int = 8192
    enable_async_logging: bool = True
    batch_flush_interval: int = 5  # 秒

    # 智能过滤配置
    enable_intelligent_filtering: bool = True
    max_debug_logs_per_hour: int = 1000
    max_info_logs_per_hour: int = 5000
    max_warning_logs_per_hour: int = 1000
    rate_limit_window_seconds: int = 3600  # 1小时

    # 环境配置
    environment: str = "production"  # development, testing, production
    enable_performance_logs: bool = False
    enable_sql_logs: bool = False


@dataclass
class LogStats:
    """日志统计"""
    total_logs: int = 0
    logs_by_level: Dict[str, int] = field(default_factory=lambda: {
        'DEBUG': 0, 'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0
    })
    logs_by_hour: Dict[str, int] = field(default_factory=dict)
    total_size_bytes: int = 0
    suppressed_logs: int = 0
    last_hour_stats: Dict[str, int] = field(default_factory=dict)


class IntelligentLogFilter(logging.Filter):
    """智能日志过滤器"""

    def __init__(self, config: LoggingConfig):
        self.config = config
        self.stats = LogStats()
        self._hourly_counters = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5分钟清理一次计数器

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤日志记录"""
        try:
            # 更新统计
            self._update_stats(record)

            # 智能过滤逻辑
            if self.config.enable_intelligent_filtering:
                return self._intelligent_filter(record)

            return True

        except Exception as e:
            # 过滤器异常时不影响日志输出
            logger.error(f"日志过滤器异常: {e}")
            return True

    def _update_stats(self, record: logging.LogRecord) -> None:
        """更新日志统计"""
        self.stats.total_logs += 1
        level_name = record.levelname
        self.stats.logs_by_level[level_name] = self.stats.logs_by_level.get(level_name, 0) + 1

        # 小时统计
        current_hour = datetime.now().strftime("%Y-%m-%d %H")
        self.stats.logs_by_hour[current_hour] = self.stats.logs_by_hour.get(current_hour, 0) + 1

        # 清理旧统计
        self._cleanup_old_stats()

    def _intelligent_filter(self, record: logging.LogRecord) -> bool:
        """智能过滤逻辑"""
        level = record.levelname
        current_time = time.time()
        current_hour = datetime.now().strftime("%Y-%m-%d %H")

        # 初始化小时计数器
        if current_hour not in self._hourly_counters:
            self._hourly_counters[current_hour] = {
                'DEBUG': 0, 'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0
            }

        # 检查小时限制
        hourly_counts = self._hourly_counters[current_hour]
        hourly_limits = {
            'DEBUG': self.config.max_debug_logs_per_hour,
            'INFO': self.config.max_info_logs_per_hour,
            'WARNING': self.config.max_warning_logs_per_hour,
            'ERROR': 1000,  # 错误日志不限制
            'CRITICAL': 1000  # 严重错误日志不限制
        }

        if hourly_counts[level] >= hourly_limits.get(level, 1000):
            self.stats.suppressed_logs += 1
            return False

        # 增加计数
        self._hourly_counters[current_hour][level] += 1

        # 环境特定过滤
        if self.config.environment == "production":
            return self._production_filter(record)

        return True

    def _production_filter(self, record: logging.LogRecord) -> bool:
        """生产环境过滤"""
        # 生产环境下过滤调试日志
        if record.levelname == "DEBUG":
            return False

        # 过滤性能敏感的日志
        if not self.config.enable_performance_logs and "PERF" in record.getMessage():
            return False

        # 过滤SQL日志
        if not self.config.enable_sql_logs and "sql" in record.getMessage().lower():
            return False

        return True

    def _cleanup_old_stats(self) -> None:
        """清理旧统计数据"""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        # 清理超过24小时的统计
        cutoff_time = datetime.now() - timedelta(hours=24)

        # 清理小时统计
        hours_to_remove = [
            hour for hour in self.stats.logs_by_hour.keys()
            if datetime.strptime(hour, "%Y-%m-%d %H") < cutoff_time
        ]
        for hour in hours_to_remove:
            del self.stats.logs_by_hour[hour]

        # 清理小时计数器
        hours_to_remove = [
            hour for hour in self._hourly_counters.keys()
            if datetime.strptime(hour, "%Y-%m-%d %H") < cutoff_time
        ]
        for hour in hours_to_remove:
            del self._hourly_counters[hour]

        self._last_cleanup = current_time


class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """压缩轮转文件处理器"""

    def __init__(self, filename, config: LoggingConfig, **kwargs):
        super().__init__(
            filename,
            maxBytes=config.max_file_size_mb * 1024 * 1024,
            backupCount=config.backup_count,
            encoding='utf-8',
            **kwargs
        )
        self.config = config

    def doRollover(self) -> None:
        """执行日志轮转"""
        super().doRollover()

        if self.config.enable_compression:
            self._compress_old_logs()

    def _compress_old_logs(self) -> None:
        """压缩旧日志文件"""
        try:
            # 压缩备份文件
            for i in range(1, self.backupCount + 1):
                old_file = f"{self.baseFilename}.{i}"
                if os.path.exists(old_file) and not old_file.endswith('.gz'):
                    compressed_file = f"{old_file}.gz"

                    # 读取原文件
                    with open(old_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb', compresslevel=self.config.compression_level) as f_out:
                            f_out.writelines(f_in)

                    # 删除原文件
                    os.remove(old_file)

                    logger.info(f"压缩日志文件: {old_file} -> {compressed_file}")

        except Exception as e:
            logger.error(f"压缩日志文件失败: {e}")


class AsyncMemoryEfficientHandler(logging.Handler):
    """异步内存高效日志处理器"""

    def __init__(self, config: LoggingConfig):
        super().__init__()
        self.config = config
        self.buffer = []
        self.buffer_size = config.buffer_size
        self.last_flush = time.time()
        self._lock = threading.Lock()
        self._handler = self._create_underlying_handler()

    def _create_underlying_handler(self) -> logging.Handler:
        """创建底层处理器"""
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / "football_prediction.log"

        if self.config.enable_compression:
            return CompressedRotatingFileHandler(
                str(log_file), self.config
            )
        else:
            return logging.handlers.RotatingFileHandler(
                str(log_file),
                maxBytes=self.config.max_file_size_mb * 1024 * 1024,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )

    def emit(self, record: logging.LogRecord) -> None:
        """发射日志记录"""
        try:
            # 格式化记录
            formatted_record = self.format(record)

            with self._lock:
                self.buffer.append(formatted_record)

                # 检查是否需要刷新
                if (len(self.buffer) >= self.buffer_size or
                    time.time() - self.last_flush >= self.config.batch_flush_interval):
                    self._flush_buffer()

        except Exception as e:
            # 日志处理异常时不影响程序运行
            sys.stderr.write(f"日志处理异常: {e}\n")

    def _flush_buffer(self) -> None:
        """刷新缓冲区"""
        if not self.buffer:
            return

        try:
            for record in self.buffer:
                self._handler.emit(logging.LogRecord(
                    name=self._handler.logger.name,
                    level=self._handler.level,
                    pathname="",
                    lineno=0,
                    msg=record,
                    args=(),
                    exc_info=None
                ))

            self.buffer.clear()
            self.last_flush = time.time()

        except Exception as e:
            sys.stderr.write(f"日志缓冲区刷新失败: {e}\n")
            self.buffer.clear()

    def close(self) -> None:
        """关闭处理器"""
        with self._lock:
            if self.buffer:
                self._flush_buffer()
        self._handler.close()
        super().close()


class StructuredJSONFormatter(logging.Formatter):
    """结构化JSON格式化器"""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 添加额外信息
        if self.include_extra and hasattr(record, '__dict__'):
            extra_fields = {
                key: value for key, value in record.__dict__.items()
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info'
                }
            }
            log_entry.update(extra_fields)

        # 异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_intelligent_logging(config: Optional[LoggingConfig] = None) -> logging.Logger:
    """
    设置智能日志系统

    Args:
        config: 日志配置

    Returns:
        logging.Logger: 配置好的logger
    """
    config = config or LoggingConfig()

    # 获取根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper()))

    # 清除现有处理器
    root_logger.handlers.clear()

    # 智能过滤器
    intelligent_filter = IntelligentLogFilter(config)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.console_level.upper()))
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(intelligent_filter)

    # 文件处理器
    if config.enable_async_logging:
        file_handler = AsyncMemoryEfficientHandler(config)
    else:
        log_dir = Path(config.log_dir)
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "football_prediction.log"

        if config.enable_compression:
            file_handler = CompressedRotatingFileHandler(
                str(log_file), config
            )
        else:
            file_handler = logging.handlers.RotatingFileHandler(
                str(log_file),
                maxBytes=config.max_file_size_mb * 1024 * 1024,
                backupCount=config.backup_count,
                encoding='utf-8'
            )

    file_handler.setLevel(getattr(logging, config.file_level.upper()))
    file_handler.addFilter(intelligent_filter)

    if config.environment == "development":
        # 开发环境使用结构化格式
        json_formatter = StructuredJSONFormatter()
        file_handler.setFormatter(json_formatter)
    else:
        # 生产环境使用简洁格式
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        file_handler.setFormatter(file_formatter)

    # 添加处理器
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # 配置特定logger
    configure_specific_loggers(config)

    root_logger.info("🔧 智能日志系统已初始化")
    return root_logger


def configure_specific_loggers(config: LoggingConfig) -> None:
    """配置特定logger"""
    # 数据库日志
    db_logger = logging.getLogger('sqlalchemy')
    if config.enable_sql_logs:
        db_logger.setLevel(logging.INFO)
    else:
        db_logger.setLevel(logging.WARNING)

    # 性能日志
    perf_logger = logging.getLogger('performance')
    if config.enable_performance_logs:
        perf_logger.setLevel(logging.INFO)
    else:
        perf_logger.setLevel(logging.WARNING)

    # 外部库日志
    external_loggers = [
        'urllib3',
        'requests',
        'botocore',
        'boto3',
        'asyncio'
    ]

    for logger_name in external_loggers:
        external_logger = logging.getLogger(logger_name)
        external_logger.setLevel(logging.WARNING)


@lru_cache(maxsize=32)
def get_logger_stats() -> LogStats:
    """获取日志统计（带缓存）"""
    for handler in logging.getLogger().handlers:
        if isinstance(handler, (IntelligentLogFilter, AsyncMemoryEfficientHandler)):
            if isinstance(handler, IntelligentLogFilter):
                return handler.stats
            elif hasattr(handler, '_handler'):
                for sub_handler in handler._handler.handlers:
                    if isinstance(sub_handler, IntelligentLogFilter):
                        return sub_handler.stats
    return LogStats()


def log_usage_statistics(interval_hours: int = 24) -> None:
    """记录使用统计"""
    stats = get_logger_stats()

    logger.info("📊 日志使用统计:")
    logger.info(f"  总日志数: {stats.total_logs:,}")
    logger.info("  按级别统计:")
    for level, count in stats.logs_by_level.items():
        if count > 0:
            logger.info(f"    {level}: {count:,}")
    logger.info(f"  被抑制日志: {stats.suppressed_logs:,}")


# 便捷函数
def setup_production_logging() -> logging.Logger:
    """设置生产环境日志"""
    config = LoggingConfig(
        environment="production",
        level="INFO",
        console_level="ERROR",
        file_level="INFO",
        enable_compression=True,
        max_file_size_mb=200,
        backup_count=10,
        enable_intelligent_filtering=True,
        max_debug_logs_per_hour=0,  # 生产环境不输出DEBUG日志
        max_info_logs_per_hour=2000,
        enable_performance_logs=False,
        enable_sql_logs=False
    )
    return setup_intelligent_logging(config)


def setup_development_logging() -> logging.Logger:
    """设置开发环境日志"""
    config = LoggingConfig(
        environment="development",
        level="DEBUG",
        console_level="DEBUG",
        file_level="DEBUG",
        enable_compression=False,
        max_file_size_mb=50,
        backup_count=3,
        enable_intelligent_filtering=False,  # 开发环境不过滤
        enable_performance_logs=True,
        enable_sql_logs=True
    )
    return setup_intelligent_logging(config)