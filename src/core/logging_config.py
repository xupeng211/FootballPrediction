"""P4-2: 统一日志配置
基于 loguru 的结构化日志系统，支持开发和生产环境的不同格式.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, 

# 尝试导入 loguru，如果不可用则回退到标准库
try:
    from loguru import logger

    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    import logging as _logging

    logger = _logging.getLogger(__name__)

# 导入 Request ID 功能
try:
    from src.api.middleware.request_id import get_request_id
except ImportError:
    # 如果在非 FastAPI 环境中使用，提供空实现
    def get_request_id() -> str:
        return ""


class StructuredFormatter:
    """结构化日志格式化器

    根据环境变量决定使用 JSON 格式（生产）还是彩色文本格式（开发）
    """

    def __init__(self, service_name: str = "football-prediction"):
        self.service_name = service_name
        self.env = self._get_env()

    @staticmethod
    def _get_env() -> str:
        """获取当前环境"""
        import os

        env = os.getenv("ENV", "development").lower()
        return env

    def _serialize_record(self, record: dict) -> dict[str, Any]:
        """将 loguru 记录序列化为结构化字典"""
        extra = record.get("extra", {})

        # 构建基础结构
        structured_record = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "service": self.service_name,
            "module": record["name"],
            "message": record["message"],
            "function": record["function"],
            "line": record["line"],
        }

        # 添加 Request ID（如果存在）
        request_id = get_request_id()
        if request_id:
            structured_record["request_id"] = request_id

        # 添加异常信息（如果存在）
        if record.get("exception"):
            structured_record["exception"] = {
                "type": record["exception"].typing.Type.__name__,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback,
            }

        # 添加额外字段
        if extra:
            # 过滤掉 loguru 内部字段
            filtered_extra = {k: v for k, v in extra.items() if not k.startswith("_")}
            structured_record.update(filtered_extra)

        return structured_record

    def json_formatter(self, record: dict) -> str:
        """JSON 格式化器（生产环境使用）"""
        try:
            structured_record = self._serialize_record(record)
            return json.dumps(structured_record, ensure_ascii=False, default=str)
        except Exception as e:
            # 如果 JSON 序列化失败，回退到简单格式
            return json.dumps(
                {
                    "timestamp": record["time"].isoformat(),
                    "level": record["level"].name,
                    "service": self.service_name,
                    "message": f"[LOG_SERIALIZATION_ERROR] {record['message']}",
                    "error": str(e),
                    "original": str(record),
                },
                ensure_ascii=False,
            )

    def color_formatter(self, record: dict) -> str:
        """彩色文本格式化器（开发环境使用）"""
        # 获取颜色代码
        level_color = {
            "TRACE": "<cyan>",
            "DEBUG": "<blue>",
            "INFO": "<green>",
            "WARNING": "<yellow>",
            "ERROR": "<red>",
            "CRITICAL": "<bold><red>",
        }.get(record["level"].name, "")

        request_id = get_request_id()
        request_id_str = f"[{request_id}] " if request_id else ""

        # 格式化：[时间] [级别] [Request-ID] [模块] 消息
        return (
            f"<green>{record['time'].strftime('%Y-%m-%d %H:%M:%S')}</green> "
            f"{level_color}<{record['level'].name}></level_color> "
            f"<blue>{request_id_str}</blue>"
            f"<cyan>[{record['name']}]</cyan> "
            f"{record['message']}"
        )


class LoggingConfig:
    """日志配置管理器"""

    def __init__(self, service_name: str = "football-prediction"):
        self.service_name = service_name
        self.formatter = StructuredFormatter(service_name)
        self.env = self.formatter._get_env()
        self._logs_dir = Path("logs")
        self._logs_dir.mkdir(exist_ok=True)

    def setup_logging(self, log_level: str = "INFO") -> None:
        """设置统一日志配置

        Args:
            log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if not LOGURU_AVAILABLE:
            # 回退到标准库日志配置
            self._setup_standard_logging(log_level)
            return

        # 移除默认的控制台处理器
        logger.remove()

        # 根据环境选择格式化器
        if self.env in ["production", "prod"]:
            format_string = self.formatter.json_formatter
            rotation = "50 MB"  # 文件大小达到 50MB 时轮转
            retention = "30 days"  # 保留 30 天的日志文件
            compression = "gz"  # 压缩旧日志文件
        else:
            format_string = self.formatter.color_formatter
            rotation = "10 MB"
            retention = "7 days"
            compression = None

        # 1. 添加控制台输出（供 Docker 日志收集）
        logger.add(
            sys.stdout,
            format=format_string,
            level=log_level,
            enqueue=True,  # 异步写入
            catch=True,  # 捕获异常防止日志记录失败导致程序崩溃
        )

        # 2. 添加文件输出（带轮转）
        logger.add(
            self._logs_dir / "app.log",
            format=format_string,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            enqueue=True,
            catch=True,
        )

        # 3. 添加错误日志单独文件
        logger.add(
            self._logs_dir / "error.log",
            format=format_string,
            level="ERROR",
            rotation=rotation,
            retention=retention,
            compression=compression,
            enqueue=True,
            catch=True,
        )

        # 4. 拦截标准库 logging
        self._intercept_standard_logging()

        logger.info(f"日志系统已初始化 - 环境: {self.env}, 级别: {log_level}")

    def _intercept_standard_logging(self) -> None:
        """拦截标准库 logging 并重定向到 loguru"""

        class InterceptHandler(logging.Handler):
            """标准库 logging 拦截器"""

            def emit(self, record: logging.LogRecord) -> None:
                """拦截并转发日志记录到 loguru"""
                # 获取日志级别映射
                level: str
                try:
                    level = logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno

                # 查找调用帧
                frame, depth = logging.currentframe(), 2
                while frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1

                logger.opt(
                    depth=depth,
                    exception=record.exc_info,
                ).log(
                    level,
                    record.getMessage(),
                )

        # 安装拦截器
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

        # 设置常见库的日志级别
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("asyncpg").setLevel(logging.WARNING)

    def _setup_standard_logging(self, log_level: str) -> None:
        """设置标准库日志配置（loguru 不可用时的回退方案）"""
        import logging
        import logging.handlers

        # 创建日志目录
        self._logs_dir.mkdir(exist_ok=True)

        # 根据环境选择格式
        if self.env in ["production", "prod"]:
            # 生产环境：JSON 格式
            import json
            from datetime import datetime

            class JSONFormatter(logging.Formatter):
                def __init__(self, service_name):
                    super().__init__()
                    self.service_name = service_name

                def format(self, record):
                    log_entry = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": record.levelname,
                        "service": self.service_name,
                        "module": record.name,
                        "message": record.getMessage(),
                        "function": record.funcName,
                        "line": record.lineno,
                    }

                    # 添加 Request ID
                    request_id = get_request_id()
                    if request_id:
                        log_entry["request_id"] = request_id

                    if record.exc_info:
                        log_entry["exception"] = self.formatException(record.exc_info)

                    return json.dumps(log_entry, ensure_ascii=False)

            formatter = JSONFormatter(self.service_name)
        else:
            # 开发环境：彩色文本格式
            try:
                import colorlog

                class RequestIDFormatter(colorlog.ColoredFormatter):
                    def format(self, record):
                        # 添加 request_id 到记录中
                        request_id = get_request_id()
                        record.request_id = request_id if request_id else ""
                        return super().format(record)

                formatter = RequestIDFormatter(
                    "%(log_color)s%(asctime)s - %(levelname)s - %(blue)s[%(request_id)s]%(reset)s %(cyan)s[%(name)s]%(reset)s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "red,bg_white",
                    },
                )
            except ImportError:
                # 回退到标准格式化器
                class RequestIDFormatter(logging.Formatter):
                    def format(self, record):
                        # 添加 request_id 到记录中
                        request_id = get_request_id()
                        request_id_str = f"[{request_id}] " if request_id else ""
                        record.request_id = request_id_str
                        return super().format(record)

                formatter = RequestIDFormatter(
                    "%(asctime)s - %(levelname)s - %(request_id)s[%(name)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )

        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))

        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # 文件处理器（带轮转）
        file_handler = logging.handlers.RotatingFileHandler(
            self._logs_dir / "app.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # 错误日志处理器
        error_handler = logging.handlers.RotatingFileHandler(
            self._logs_dir / "error.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

        # 设置第三方库日志级别
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("asyncpg").setLevel(logging.WARNING)


# 全局日志配置实例
_logging_config: LoggingConfig | None = None


def setup_logging(
    service_name: str = "football-prediction", log_level: str = "INFO"
) -> None:
    """设置应用日志配置

    Args:
        service_name: 服务名称
        log_level: 日志级别
    """
    global _logging_config
    _logging_config = LoggingConfig(service_name)
    _logging_config.setup_logging(log_level)


def get_logger(name: str = None) -> "logger":
    """获取配置好的日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        loguru logger 或标准库 logger 实例
    """
    if LOGURU_AVAILABLE:
        if name:
            return logger.bind(name=name)
        return logger
    else:
        # 回退到标准库
        import logging

        if name:
            return logging.getLogger(name)
        return logging.getLogger()


# 导出接口
__all__ = [
    "LoggingConfig",
    "StructuredFormatter",
    "setup_logging",
    "get_logger",
]
