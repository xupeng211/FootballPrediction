from __future__ import annotations

from collections.abc import Callable
from enum import Enum
import logging
import os
from typing import Any

LoadDotenvFunc = Callable[[], bool]
EnvironmentDetectorFunc = Callable[[], Any]
OptimalDbHostFunc = Callable[[str | None, str | None], str]
ValidatorFunc = Callable[..., None]

_load_dotenv: LoadDotenvFunc | None
EnvironmentType: Any
detect_environment: EnvironmentDetectorFunc | None
get_optimal_db_host: OptimalDbHostFunc | None
validate_database_environment_impl: ValidatorFunc | None
validate_no_local_postgres_conflict: ValidatorFunc | None

try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:
    _load_dotenv = None

try:
    from src.core.environment_detector import (
        EnvironmentType,
        detect_environment,
        get_optimal_db_host,
    )
except ImportError:
    EnvironmentType = None
    detect_environment = None
    get_optimal_db_host = None

try:
    from src.core.environment_validator import (
        validate_database_environment as validate_database_environment_impl,
    )
    from src.core.environment_validator import validate_no_local_postgres_conflict
except ImportError:
    validate_database_environment_impl = None
    validate_no_local_postgres_conflict = None

logger = logging.getLogger(__name__)

ALLOWED_DB_NAME = "football_db"
MIN_PORT = 1
MAX_PORT = 65535
MIN_SECRET_KEY_LENGTH = 32
MAX_BATCH_SIZE_LIMIT = 1000


class Environment(str, Enum):
    """环境枚举。"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """日志级别枚举。"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def load_dotenv_if_available() -> None:
    """按需加载 .env。"""
    if _load_dotenv is None:
        logger.debug("python-dotenv 未安装，跳过 .env 文件加载")
        return
    if os.getenv("PYTEST_CURRENT_TEST"):
        logger.debug("检测到 pytest 环境，跳过二次加载 .env")
        return
    _load_dotenv()


def env_flag(name: str) -> bool:
    """解析布尔型环境变量。"""
    return os.getenv(name, "").lower() in ("true", "1", "yes")


def env_int(name: str, default: int) -> int:
    """解析整型环境变量，失败时回退到默认值。"""
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default

    try:
        return int(raw_value)
    except ValueError:
        logger.warning("环境变量 %s=%r 不是有效整数，回退为 %s", name, raw_value, default)
        return default


__all__ = [
    "ALLOWED_DB_NAME",
    "MAX_BATCH_SIZE_LIMIT",
    "MAX_PORT",
    "MIN_PORT",
    "MIN_SECRET_KEY_LENGTH",
    "Environment",
    "EnvironmentType",
    "LogLevel",
    "detect_environment",
    "env_flag",
    "env_int",
    "get_optimal_db_host",
    "load_dotenv_if_available",
    "logger",
    "validate_database_environment_impl",
    "validate_no_local_postgres_conflict",
]
