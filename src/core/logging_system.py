"""
改进的日志系统
Improved Logging System

提供结构化日志记录功能：
- 多级别日志
- 结构化输出
- 日志聚合和分析
- 性能监控日志
- 审计日志

Provides structured logging with:
- Multiple log levels
- Structured output
- Log aggregation and analysis
- Performance monitoring logs
- Audit logs
"""

import logging
import os
import sys
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, cast

from pythonjsonlogger import jsonlogger


class LogLevel(Enum):
    """日志级别"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日志类别"""

    API = "api"
    PREDICTION = "prediction"
    DATA_COLLECTION = "data_collection"
    CACHE = "cache"
    DATABASE = "database"
    MODEL = "model"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    SECURITY = "security"


class StructuredLogger:
    """结构化日志器"""

    def __init__(
        self,
        name: str,
        category: LogCategory = LogCategory.API,
        level: LogLevel = LogLevel.INFO,
        enable_json: bool = True,
        enable_console: bool = True,
        enable_file: bool = True,
        log_file: Optional[str] = None,
    ):
        self.name = name
        self.category = category
        self.level = level
        self.enable_json = enable_json
        self.enable_console = enable_console
        self.enable_file = enable_file

        # 创建logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value))

        # 清除现有处理器
        self.logger.handlers.clear()

        # 配置格式化器
        self.formatter = self._create_formatter()

        # 添加处理器
        if enable_console:
            self._add_console_handler()
        if enable_file:
            self._add_file_handler(log_file)

    def _create_formatter(self) -> logging.Formatter:
        """创建日志格式化器"""
        if self.enable_json:
            return jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            return logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

    def _add_console_handler(self):
        """添加控制台处理器"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.formatter)
        self.logger.addHandler(handler)

    def _add_file_handler(self, log_file: Optional[str] = None):
        """添加文件处理器"""
        if not log_file:
            log_dir = os.getenv("LOG_DIR", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"{self.name}.log")

        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(self.formatter)
        self.logger.addHandler(handler)

    def _log(
        self,
        level: LogLevel,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[bool] = None,
    ):
        """记录日志"""
        # 添加标准字段
        log_extra = {
            "category": self.category.value,
            "service": "football-prediction",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "version": os.getenv("APP_VERSION", "1.0.0"),
        }

        # 添加额外字段
        if extra:
            log_extra.update(extra)

        # 记录日志
        getattr(self.logger, level.value.lower())(
            message, extra=log_extra, exc_info=exc_info
        )

    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log(LogLevel.DEBUG, message, kwargs)

    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log(LogLevel.INFO, message, kwargs)

    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log(LogLevel.WARNING, message, kwargs)

    def error(self, message: str, **kwargs):
        """错误日志"""
        self._log(LogLevel.ERROR, message, kwargs, exc_info=True)

    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._log(LogLevel.CRITICAL, message, kwargs, exc_info=True)

    # 特殊日志方法
    def audit(self, action: str, user_id: Optional[str] = None, **kwargs):
        """审计日志"""
        self.info(
            f"AUDIT: {action}",
            audit_action=action,
            user_id=user_id,
            audit_timestamp=datetime.now().isoformat(),
            **kwargs,
        )

    def performance(
        self, operation: str, duration: float, success: bool = True, **kwargs
    ):
        """性能日志"""
        self.info(
            f"PERFORMANCE: {operation}",
            operation=operation,
            duration_ms=duration * 1000,
            success=success,
            **kwargs,
        )

    def api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        user_id: Optional[str] = None,
        **kwargs,
    ):
        """API请求日志"""
        self.info(
            f"API: {method} {path} - {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration * 1000,
            user_id=user_id,
            **kwargs,
        )

    def prediction(
        self,
        match_id: int,
        model_version: str,
        prediction: str,
        confidence: float,
        success: bool = True,
        **kwargs,
    ):
        """预测日志"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"PREDICTION: Match {match_id} - {prediction} (confidence: {confidence:.3f})"

        self._log(
            level,
            message,
            {
                "match_id": match_id,
                "model_version": model_version,
                "prediction": prediction,
                "confidence": confidence,
                "success": success,
                **kwargs,
            },
        )

    def data_collection(
        self,
        source: str,
        data_type: str,
        records_count: int,
        success: bool = True,
        **kwargs,
    ):
        """数据收集日志"""
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"DATA COLLECTION: {source} - {data_type} ({records_count} records)"

        self._log(
            level,
            message,
            {
                "source": source,
                "data_type": data_type,
                "records_count": records_count,
                "success": success,
                **kwargs,
            },
        )

    def cache_operation(
        self,
        operation: str,
        key: str,
        hit: Optional[bool] = None,
        duration_ms: Optional[float] = None,
        **kwargs,
    ):
        """缓存操作日志"""
        message = f"CACHE {operation.upper()}: {key}"
        extra = {"operation": operation, "key": key}

        if hit is not None:
            extra["hit"] = str(hit)
            message += f" - {'HIT' if hit else 'MISS'}"

        if duration_ms is not None:
            extra["duration_ms"] = str(duration_ms)

        extra.update(kwargs)

        self.debug(message, **extra)

    def security_event(
        self,
        event_type: str,
        severity: str = "medium",
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs,
    ):
        """安全事件日志"""
        self.warning(
            f"SECURITY: {event_type}",
            security_event=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            **kwargs,
        )


class LoggerManager:
    """日志管理器"""

    _loggers: Dict[str, StructuredLogger] = {}
    _config: Dict[str, Any] = {}

    @classmethod
    def configure(
        cls,
        level: LogLevel = LogLevel.INFO,
        enable_json: bool = True,
        log_dir: str = "logs",
        **kwargs,
    ):
        """配置日志系统"""
        cls._config = {
            "level": level,
            "enable_json": enable_json,
            "log_dir": log_dir,
            **kwargs,
        }

        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)

    @classmethod
    def get_logger(
        cls, name: str, category: LogCategory = LogCategory.API, **kwargs
    ) -> StructuredLogger:
        """获取日志器"""
        key = f"{name}:{category.value}"

        if key not in cls._loggers:
            # 合并配置
            config = cls._config.copy()
            config.update(kwargs)

            # 创建日志器 - 过滤掉不支持的参数
            supported_params = {
                "level",
                "enable_json",
                "enable_console",
                "enable_file",
                "log_file",
            }
            filtered_config = {k: v for k, v in config.items() if k in supported_params}

            cls._loggers[key] = StructuredLogger(
                name=name, category=category, **filtered_config
            )

        return cls._loggers[key]

    @classmethod
    def get_all_loggers(cls) -> Dict[str, StructuredLogger]:
        """获取所有日志器"""
        return cls._loggers.copy()

    @classmethod
    def shutdown(cls):
        """关闭日志系统"""
        for logger in cls._loggers.values():
            for handler in logger.logger.handlers:
                handler.close()
        cls._loggers.clear()


# 便捷函数
def get_logger(name: str, category: LogCategory = LogCategory.API) -> StructuredLogger:
    """获取日志器的便捷函数"""
    return LoggerManager.get_logger(name, category)


# 性能监控装饰器
def log_performance(operation: str, logger: Optional[StructuredLogger] = None):
    """性能监控装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                log = logger or get_logger(func.__module__, LogCategory.PERFORMANCE)
                log.performance(
                    operation=operation,
                    duration=duration,
                    success=success,
                    function=func.__name__,
                    module=func.__module__,
                )

        return wrapper

    return decorator


# 异步性能监控装饰器
def log_async_performance(operation: str, logger: Optional[StructuredLogger] = None):
    """异步性能监控装饰器"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                log = logger or get_logger(func.__module__, LogCategory.PERFORMANCE)
                log.performance(
                    operation=operation,
                    duration=duration,
                    success=success,
                    function=func.__name__,
                    module=func.__module__,
                )

        return wrapper

    return decorator


# 审计日志装饰器
def log_audit(action: str, logger: Optional[StructuredLogger] = None):
    """审计日志装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            log = logger or get_logger(func.__module__, LogCategory.AUDIT)
            # 尝试从kwargs或args中提取用户ID
            user_id = kwargs.get("user_id") or (
                args[0]
                if args and isinstance(args[0], dict) and "user_id" in args[0]
                else None
            )

            log.audit(
                action=action,
                user_id=user_id,
                function=func.__name__,
                module=func.__module__,
            )

            return func(*args, **kwargs)

        return wrapper

    return decorator


# 初始化默认配置
LoggerManager.configure(
    level=LogLevel.INFO,
    enable_json=os.getenv("LOG_JSON", "true").lower() == "true",
    log_dir=os.getenv("LOG_DIR", "logs"),
)
