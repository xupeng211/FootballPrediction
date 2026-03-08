"""
FootballPrediction 核心功能模块 (V4.20 重构版)

提供系统核心功能，包括：
- 配置管理
- 日志系统
- 异常处理
- 基础工具类

"""

import logging
from pathlib import Path
from typing import Any, Dict


class Config:
    """配置管理类 - 提供统一的配置读写和持久化机制"""

    def __init__(self) -> None:
        # 配置文件存储在用户主目录下， avoid权限问题
        self.config_dir = Path.home() / ".footballprediction"
        self.config_file = self.config_dir / "config.json"
        self._config: dict[str, Any] = {}

    def _load_config(self) -> None:
        """加载配置文件 - 自动处理文件不存在或格式错误的情况"""
        if self.config_file.exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception as e:
                # 配置文件损坏时记录警告，但不中断程序执行
                logging.warning(f"配置文件加载失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项 - 支持默认值，确保程序健壮性"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置项 - 仅更新内存中的配置，需调用save()持久化"""
        self._config[key] = value

    def save(self) -> None:
        """保存配置到文件 - 自动创建目录，确保配置持久化"""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            # ensure_ascii=False保证中文字符正确显示
            json.dump(self._config, f, ensure_ascii=False, indent=2)


class Logger:
    """日志管理类"""

    @staticmethod
    def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger


    @staticmethod
    def get_logger(name: str, level: str = "INFO") -> logging.Logger:
        """获取日志器 - 兼容 get_logger 的简单封装"""
        logger = Logger.setup_logger(name, level)
        return logger


class FootballPredictionError(Exception):
    """FootballPrediction基础异常类"""


class ConfigError(FootballPredictionError):
    """配置相关异常"""


class DataError(FootballPredictionError):
    """数据处理异常"""


# 全局配置实例
config = Config()

# 默认日志器
logger = Logger.setup_logger("footballprediction")


__all__ = [
    "Config",
    "ConfigError",
    "DataError",
    "FootballPredictionError",
    "Logger",
    "config",
    "logger",
]

# ============================================================================
# V105.0 新增模块
# ============================================================================

from src.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerOpenError,
    CircuitState,
    api_breaker,
    database_breaker,
    network_breaker,
)
from src.core.graceful_shutdown import GracefulShutdownManager, graceful_shutdown
from src.core.structured_logging import (
    ComponentLogger,
    EventCode,
    HarvestStats,
    LogContext,
    LogLevel,
    get_logger,
    log_context,
    performance_timer,
    setup_structured_logging,
)

__all__ += [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitBreakerOpenError",
    "CircuitState",
    # Structured Logging
    "ComponentLogger",
    "EventCode",
    # Graceful Shutdown
    "GracefulShutdownManager",
    "HarvestStats",
    "LogContext",
    "LogLevel",
    "api_breaker",
    "database_breaker",
    "network_breaker",
    "get_logger",
    "graceful_shutdown",
    "log_context",
    "performance_timer",
    "setup_structured_logging",
]
