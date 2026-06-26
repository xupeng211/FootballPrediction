from __future__ import annotations

from collections.abc import Callable
from enum import Enum
import logging
import os
import re
from typing import Any

from src.core.exceptions import DatabaseConfigurationError

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
DEFAULT_DB_NAME = ALLOWED_DB_NAME
NON_PRODUCTION_DB_NAMES = frozenset(
    {
        ALLOWED_DB_NAME,
        "football_prediction_staging",
        "football_prediction_test",
        "football_db_dev",
        "football_db_test",
        "football_test",
        "test_db",
    }
)
VALID_DB_SSL_MODES = frozenset(
    {
        "disable",
        "allow",
        "prefer",
        "require",
        "verify-ca",
        "verify-full",
    }
)
PRODUCTION_DB_SSL_MODES = frozenset({"require", "verify-ca", "verify-full"})
DEFAULT_DB_SSL_MODE = "require"
MIN_PORT = 1
MAX_PORT = 65535
MIN_SECRET_KEY_LENGTH = 32
MAX_BATCH_SIZE_LIMIT = 1000
_DB_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


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


def normalize_environment_name(environment: Any | None = None) -> str:
    """Normalize runtime environment labels for DB safety policy."""
    raw_environment = environment
    if raw_environment is None:
        raw_environment = (
            os.getenv("ENVIRONMENT")
            or os.getenv("APP_ENV")
            or os.getenv("NODE_ENV")
            or Environment.DEVELOPMENT.value
        )

    value = getattr(raw_environment, "value", raw_environment)
    normalized = str(value or Environment.DEVELOPMENT.value).strip().lower().replace("-", "_")

    aliases = {
        "dev": Environment.DEVELOPMENT.value,
        "local": Environment.DEVELOPMENT.value,
        "test": Environment.TESTING.value,
        "tests": Environment.TESTING.value,
        "stage": Environment.STAGING.value,
        "local_staging": Environment.STAGING.value,
        "prod": Environment.PRODUCTION.value,
    }
    return aliases.get(normalized, normalized)


def is_production_like_environment(environment: Any | None = None) -> bool:
    """Return True for environments where DB identity and SSL must be strict."""
    return normalize_environment_name(environment) in {
        Environment.PRODUCTION.value,
        "monitoring",
    }


def allowed_db_names_for_environment(environment: Any | None = None) -> frozenset[str]:
    """Return the DB names allowed for the supplied runtime environment."""
    if is_production_like_environment(environment):
        return frozenset({ALLOWED_DB_NAME})
    return NON_PRODUCTION_DB_NAMES


def validate_db_name_for_environment(db_name: str | None, environment: Any | None = None) -> str:
    """Validate DB identity without weakening production protection."""
    value = (db_name or "").strip()
    normalized_environment = normalize_environment_name(environment)
    allowed_names = allowed_db_names_for_environment(normalized_environment)

    if not value:
        raise DatabaseConfigurationError(
            "🚨 数据库配置非法：DB_NAME 不能为空\n"
            f"   当前环境: {normalized_environment}\n"
            f"   允许的数据库名称: {', '.join(sorted(allowed_names))}"
        )

    if _DB_NAME_PATTERN.fullmatch(value) is None:
        raise DatabaseConfigurationError(
            f"🚨 数据库配置非法：DB_NAME 只能包含字母、数字和下划线\n   检测到: {value!r}"
        )

    if value not in allowed_names:
        raise DatabaseConfigurationError(
            "🚨 数据库配置非法：当前环境不允许该 DB_NAME\n"
            f"   当前环境: {normalized_environment}\n"
            f"   检测到: {value!r}\n"
            f"   允许的数据库名称: {', '.join(sorted(allowed_names))}"
        )
    return value


def normalize_db_ssl_mode(
    ssl_mode: object | None = None,
    environment: Any | None = None,
    *,
    default: str = DEFAULT_DB_SSL_MODE,
) -> str:
    """Normalize DB_SSL_MODE to a libpq-style string enum."""
    if ssl_mode is None or ssl_mode == "":
        value = default
    elif isinstance(ssl_mode, bool):
        value = "require" if ssl_mode else "disable"
    else:
        raw_value = str(ssl_mode).strip().lower().replace("_", "-")
        legacy_bool_values = {
            "true": "require",
            "1": "require",
            "yes": "require",
            "on": "require",
            "false": "disable",
            "0": "disable",
            "no": "disable",
            "off": "disable",
        }
        value = legacy_bool_values.get(raw_value, raw_value)

    if value not in VALID_DB_SSL_MODES:
        raise DatabaseConfigurationError(
            "🚨 数据库 SSL 配置非法：DB_SSL_MODE 不受支持\n"
            f"   检测到: {ssl_mode!r}\n"
            f"   允许值: {', '.join(sorted(VALID_DB_SSL_MODES))}"
        )

    normalized_environment = normalize_environment_name(environment)
    if (
        is_production_like_environment(normalized_environment)
        and value not in PRODUCTION_DB_SSL_MODES
    ):
        raise DatabaseConfigurationError(
            "🚨 数据库 SSL 配置非法：生产环境必须启用强制 SSL\n"
            f"   当前环境: {normalized_environment}\n"
            f"   检测到: DB_SSL_MODE={value!r}\n"
            f"   生产允许值: {', '.join(sorted(PRODUCTION_DB_SSL_MODES))}"
        )

    return value


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
    "DEFAULT_DB_NAME",
    "DEFAULT_DB_SSL_MODE",
    "MAX_BATCH_SIZE_LIMIT",
    "MAX_PORT",
    "MIN_PORT",
    "MIN_SECRET_KEY_LENGTH",
    "NON_PRODUCTION_DB_NAMES",
    "PRODUCTION_DB_SSL_MODES",
    "VALID_DB_SSL_MODES",
    "Environment",
    "EnvironmentType",
    "LogLevel",
    "allowed_db_names_for_environment",
    "detect_environment",
    "env_flag",
    "env_int",
    "get_optimal_db_host",
    "is_production_like_environment",
    "load_dotenv_if_available",
    "logger",
    "normalize_db_ssl_mode",
    "normalize_environment_name",
    "validate_database_environment_impl",
    "validate_db_name_for_environment",
    "validate_no_local_postgres_conflict",
]
