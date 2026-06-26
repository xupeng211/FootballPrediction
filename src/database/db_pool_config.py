#!/usr/bin/env python3
"""数据库连接池共享配置。"""

from dataclasses import dataclass, field
import logging
import os
import urllib.parse

from src.config.common import (
    DEFAULT_DB_NAME,
    DEFAULT_DB_SSL_MODE,
    normalize_db_ssl_mode,
    validate_db_name_for_environment,
)

logger = logging.getLogger(__name__)


def _env_str(name: str, default: str) -> str:
    """读取字符串环境变量，确保返回值始终为字符串。"""
    return os.getenv(name) or default


class ConfigError(Exception):
    """配置缺失或无效错误。"""


@dataclass
class DatabasePoolConfig:
    """数据库连接池配置类。"""

    host: str = field(default_factory=lambda: DatabasePoolConfig._get_db_host())
    port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "football_user"))
    password: str = field(default_factory=lambda: DatabasePoolConfig._get_required_password())
    database: str = field(
        default_factory=lambda: validate_db_name_for_environment(
            os.getenv("DB_NAME", DEFAULT_DB_NAME)
        )
    )

    ssl_mode: str = field(
        default_factory=lambda: normalize_db_ssl_mode(os.getenv("DB_SSL_MODE", DEFAULT_DB_SSL_MODE))
    )
    ssl_cert: str | None = field(default_factory=lambda: os.getenv("DB_SSL_CERT", None))
    ssl_key: str | None = field(default_factory=lambda: os.getenv("DB_SSL_KEY", None))
    ssl_root_cert: str | None = field(default_factory=lambda: os.getenv("DB_SSL_ROOT_CERT", None))

    min_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_MIN_SIZE", "5")))
    max_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_MAX_SIZE", "10")))
    max_queries: int = field(default_factory=lambda: int(os.getenv("DB_POOL_MAX_QUERIES", "50000")))
    max_inactive_connection_lifetime: float = field(
        default_factory=lambda: float(os.getenv("DB_POOL_MAX_INACTIVE_LIFETIME", "300.0"))
    )

    timeout: float = field(default_factory=lambda: float(os.getenv("DB_TIMEOUT", "30.0")))
    command_timeout: float = field(
        default_factory=lambda: float(os.getenv("DB_COMMAND_TIMEOUT", "30.0"))
    )
    health_check_interval: float = field(
        default_factory=lambda: float(os.getenv("DB_HEALTH_CHECK_INTERVAL", "30.0"))
    )
    health_check_timeout: float = field(
        default_factory=lambda: float(os.getenv("DB_HEALTH_CHECK_TIMEOUT", "5.0"))
    )
    max_retries: int = field(default_factory=lambda: int(os.getenv("DB_MAX_RETRIES", "3")))
    retry_delay: float = field(default_factory=lambda: float(os.getenv("DB_RETRY_DELAY", "1.0")))

    def __post_init__(self) -> None:
        self.database = validate_db_name_for_environment(self.database)
        self.ssl_mode = normalize_db_ssl_mode(self.ssl_mode)

    @staticmethod
    def _get_db_host() -> str:
        """智能获取数据库主机名。"""
        docker_env = os.getenv("DOCKER_ENV", "").lower() in ("true", "1", "yes")
        db_host = os.getenv("DB_HOST", "localhost")

        if docker_env and db_host == "host.docker.internal":
            logger.info("🐳 Docker 环境：自动使用 'db' 作为数据库主机")
            return "db"

        return db_host

    @staticmethod
    def _get_required_password() -> str:
        """强制从环境变量获取密码。"""
        password = os.getenv("DB_PASSWORD")
        if not password:
            logger.warning("⚠️ DB_PASSWORD 未设置，请在 .env 文件中配置")
            if os.getenv("NODE_ENV") == "production":
                raise ConfigError("生产环境必须设置 DB_PASSWORD 环境变量")
            return ""
        return password

    @classmethod
    def from_url(cls, db_url: str | None = None) -> "DatabasePoolConfig":
        """从数据库 URL 创建配置对象。"""
        if db_url is None:
            db_host = _env_str("DB_HOST", "localhost")
            db_port = _env_str("DB_PORT", "5432")
            db_user = _env_str("DB_USER", "football_user")
            db_password = os.getenv("DB_PASSWORD") or ""
            db_name = validate_db_name_for_environment(_env_str("DB_NAME", DEFAULT_DB_NAME))
            db_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        parsed = urllib.parse.urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))
        query = urllib.parse.parse_qs(parsed.query)
        raw_ssl_mode = (
            query.get("sslmode", [None])[0]
            or query.get("ssl", [None])[0]
            or os.getenv("DB_SSL_MODE", DEFAULT_DB_SSL_MODE)
        )

        return cls(
            host=parsed.hostname or _env_str("DB_HOST", "localhost"),
            port=parsed.port or int(_env_str("DB_PORT", "5432")),
            user=parsed.username or _env_str("DB_USER", "football_user"),
            password=parsed.password or os.getenv("DB_PASSWORD") or "",
            database=validate_db_name_for_environment(
                parsed.path.lstrip("/") or _env_str("DB_NAME", DEFAULT_DB_NAME)
            ),
            ssl_mode=normalize_db_ssl_mode(raw_ssl_mode),
        )
