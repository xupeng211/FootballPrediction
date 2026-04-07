from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import os
from typing import Any

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.common import (
    ALLOWED_DB_NAME,
    MIN_SECRET_KEY_LENGTH,
    Environment,
    env_flag,
    logger,
    validate_database_environment_impl,
    validate_no_local_postgres_conflict,
)
from src.config.db_settings import DatabaseConfig, DatabaseSettingsMixin, RedisConfig
from src.config.ml_settings import FotMobAPIConfig, MLSettingsMixin, StrategyConfig
from src.config.proxy_settings import ProxyConfig, ProxySettingsMixin
from src.core.exceptions import DatabaseConfigurationError


class UnifiedSettings(ProxySettingsMixin, MLSettingsMixin, DatabaseSettingsMixin, BaseSettings):
    """统一设置类。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **kwargs: Any) -> None:
        raw_env_db_name = os.environ.get("DB_NAME")
        if raw_env_db_name and raw_env_db_name != ALLOWED_DB_NAME:
            raise DatabaseConfigurationError(
                "🚨 V41.51 数据库大一统：非法数据库名称\n"
                f"   检测到: DB_NAME='{raw_env_db_name}'\n"
                f"   系统只允许: '{ALLOWED_DB_NAME}'\n"
                f"   请检查 .env 文件，确保 DB_NAME={ALLOWED_DB_NAME}"
            )

        auto_env = self.auto_inject_env_vars()
        auto_env.update(kwargs)

        raw_db_name = auto_env.get("db_name", kwargs.get("db_name", ALLOWED_DB_NAME))
        if raw_db_name != ALLOWED_DB_NAME:
            raise DatabaseConfigurationError(
                "🚨 V41.51 数据库大一统：非法数据库名称\n"
                f"   检测到: '{raw_db_name}'\n"
                f"   系统只允许: '{ALLOWED_DB_NAME}'\n"
                f"   请检查配置文件，确保 db_name={ALLOWED_DB_NAME}"
            )

        super().__init__(**auto_env)

    def get_log_config(self) -> dict[str, Any]:
        """生成日志配置。"""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "detailed": {
                    "format": (
                        "%(asctime)s - %(name)s - %(levelname)s - %(module)s "
                        "- %(funcName)s - %(message)s"
                    ),
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": self.log_level.value,
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": self.log_level.value,
                    "formatter": "detailed",
                    "filename": "logs/app.log",
                    "maxBytes": 10485760,
                    "backupCount": 5,
                },
            },
            "root": {
                "level": self.log_level.value,
                "handlers": ["console", "file"] if not self.is_development else ["console"],
            },
        }

    def validate_integrity(self) -> list[str]:
        """兼容旧接口。"""
        return self._validate_config_basic()

    def _validate_config_basic(self) -> list[str]:
        errors: list[str] = []

        if not self.secret_key.get_secret_value():
            errors.append("secret_key 不能为空")
        if not self.db_password.get_secret_value():
            errors.append("db_password 不能为空")
        if not self.get_model_path().exists():
            errors.append(f"模型文件不存在: {self.model_path}")

        if self.is_production:
            if self.debug:
                errors.append("生产环境不应启用 debug 模式")
            if not self.enable_metrics:
                errors.append("生产环境应启用指标收集")
            if "localhost" in self.allowed_hosts:
                errors.append("生产环境 allowed_hosts 不应包含 localhost")

        return errors

    def validate_environment(self) -> dict[str, Any]:
        """执行环境完整性检查。"""
        issues: list[str] = []
        warnings: list[str] = []

        if not self.db_password.get_secret_value():
            issues.append("DB_PASSWORD 未设置（开发环境可使用默认值）")
        if not self.secret_key.get_secret_value():
            issues.append("SECRET_KEY 未设置")

        if self.is_production:
            if len(self.secret_key.get_secret_value()) < MIN_SECRET_KEY_LENGTH:
                issues.append("生产环境 SECRET_KEY 必须至少 32 字符")
            if self.db_password.get_secret_value() in {"football_pass", "password", "123456"}:
                issues.append("生产环境使用了不安全的默认数据库密码")
            if self.debug:
                issues.append("生产环境不应启用 debug 模式")
            if "localhost" in self.allowed_hosts or "127.0.0.1" in self.allowed_hosts:
                warnings.append("生产环境 allowed_hosts 包含 localhost，请确认是否正确")

        if not self.redis_host or self.redis_host == "localhost":
            warnings.append("REDIS_HOST 未配置或为 localhost，缓存功能可能不可用")
        if not self.enable_metrics:
            warnings.append("ENABLE_METRICS 为 False，监控指标收集已禁用")
        if self.db_host == "localhost" and self.environment in ("production", "staging"):
            warnings.append(f"{self.environment.value} 环境使用 localhost 作为数据库主机，请确认")

        score = max(0.0, 100.0 - len(issues) * 25 - len(warnings) * 5)
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "environment": self.environment.value,
            "score": score,
        }


def _validate_database_environment(settings: UnifiedSettings) -> None:
    """执行数据库环境校验。"""
    if env_flag("SKIP_ENV_VALIDATION"):
        logger.warning("⚠️  环境检测已跳过 (SKIP_ENV_VALIDATION=1)")
        return

    if validate_database_environment_impl is None or validate_no_local_postgres_conflict is None:
        logger.warning("⚠️  环境检测模块不可用，跳过验证")
        return

    try:
        db_port = settings.database.port
        validate_no_local_postgres_conflict(db_port)
        validate_database_environment_impl(
            db_host=settings.database.host,
            db_port=db_port,
            allow_docker=True,
            allow_local=False,
        )
        logger.info("✅ V41.77: 数据库环境验证通过")
    except Exception as exc:
        raise DatabaseConfigurationError(
            f"🚨 V41.77: 数据库环境验证失败\n   错误: {exc}\n   请确保数据库环境正确配置"
        ) from exc


@lru_cache(maxsize=1)
def _build_settings() -> UnifiedSettings:
    """构建并缓存全局设置实例。"""
    try:
        settings = UnifiedSettings()
        errors = settings.validate_integrity()
        if errors:
            logger.warning("配置验证警告: %s", "; ".join(errors))
        _validate_database_environment(settings)
    except DatabaseConfigurationError:
        raise
    except Exception as exc:
        logger.warning("配置初始化警告: %s", exc)
        raw_db_name = os.getenv("DB_NAME", ALLOWED_DB_NAME)
        if raw_db_name != ALLOWED_DB_NAME:
            raise DatabaseConfigurationError(
                "🚨 非法数据库配置！\n"
                f"   系统只允许连接 '{ALLOWED_DB_NAME}'，检测到: '{raw_db_name}'\n"
                f"   请检查 .env 文件和环境变量，确保 DB_NAME={ALLOWED_DB_NAME}"
            ) from exc
        return UnifiedSettings(
            environment=Environment.DEVELOPMENT,
            debug=True,
            secret_key=SecretStr("dev-secret-key-please-change-in-production"),
        )
    return settings


def get_settings() -> UnifiedSettings:
    return _build_settings()


def reload_settings() -> UnifiedSettings:
    _build_settings.cache_clear()
    _build_config_accessor.cache_clear()
    return get_settings()


def get_database_url() -> str:
    return get_settings().database.get_connection_string()


def get_redis_url() -> str:
    return get_settings().redis.get_connection_string()


def is_production() -> bool:
    return get_settings().is_production


def is_development() -> bool:
    return get_settings().is_development


@dataclass
class ConfigAccessor:
    """类型安全的配置访问器。"""

    _settings: UnifiedSettings = field(default_factory=get_settings)

    @property
    def database(self) -> DatabaseConfig:
        return self._settings.database

    @property
    def redis(self) -> RedisConfig:
        return self._settings.redis

    @property
    def fotmob_api(self) -> FotMobAPIConfig:
        return self._settings.fotmob_api

    @property
    def proxy(self) -> ProxyConfig:
        return self._settings.build_proxy_config()

    def reload(self) -> None:
        self._settings = reload_settings()


@lru_cache(maxsize=1)
def _build_config_accessor() -> ConfigAccessor:
    return ConfigAccessor()


def get_config() -> ConfigAccessor:
    return _build_config_accessor()


__all__ = [
    "ConfigAccessor",
    "StrategyConfig",
    "UnifiedSettings",
    "get_config",
    "get_database_url",
    "get_redis_url",
    "get_settings",
    "is_development",
    "is_production",
    "reload_settings",
]
