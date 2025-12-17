#!/usr/bin/env python3
"""
应用配置管理模块

使用Pydantic Settings进行配置管理，从环境变量加载所有配置参数。
解决硬编码问题，提供类型安全的配置访问。

主要特性:
- 环境变量自动加载
- 类型验证和转换
- 默认值支持
- 配置分组管理
- 敏感信息保护

环境变量命名规范:
- 数据库配置: DB_*
- 连接池配置: DB_POOL_*
- FotMob API配置: FOTMOB_*
- 应用配置: APP_*
- 日志配置: LOG_*
"""

import os
import logging
from typing import Optional, List, Dict, Any, Callable, TYPE_CHECKING
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from database.db_pool import DatabasePoolConfig

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """数据库连接配置"""

    # 基本连接配置
    host: str = Field(default="localhost", description="数据库主机地址")
    port: int = Field(default=5432, description="数据库端口")
    user: str = Field(default="postgres", description="数据库用户名")
    password: str = Field(default="postgres", description="数据库密码")
    database: str = Field(default="football_prediction", description="数据库名称")

    # 数据库URL (可选，如果提供则覆盖上述配置)
    url: Optional[str] = Field(default=None, description="完整数据库URL")

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_connection_string(self) -> str:
        """获取数据库连接字符串"""
        if self.url:
            return self.url

        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class DatabasePoolSettings(BaseSettings):
    """数据库连接池配置"""

    # 连接池大小配置
    min_size: int = Field(
        default=5, env="DB_POOL_MIN_SIZE", ge=1, le=100, description="最小连接数"
    )
    max_size: int = Field(
        default=20, env="DB_POOL_MAX_SIZE", ge=1, le=1000, description="最大连接数"
    )
    max_queries: int = Field(
        default=50000, env="DB_POOL_MAX_QUERIES", ge=100, description="每连接最大查询数"
    )
    max_inactive_connection_lifetime: float = Field(
        default=300.0,
        env="DB_POOL_MAX_INACTIVE_LIFETIME",
        ge=10.0,
        le=3600.0,
        description="连接最大非活跃时间(秒)",
    )

    # 超时配置
    timeout: float = Field(
        default=60.0, env="DB_TIMEOUT", ge=1.0, le=600.0, description="连接超时(秒)"
    )
    command_timeout: float = Field(
        default=30.0,
        env="DB_COMMAND_TIMEOUT",
        ge=1.0,
        le=300.0,
        description="命令执行超时(秒)",
    )

    # 健康检查配置
    health_check_interval: float = Field(
        default=30.0,
        env="DB_HEALTH_CHECK_INTERVAL",
        ge=5.0,
        le=300.0,
        description="健康检查间隔(秒)",
    )
    health_check_timeout: float = Field(
        default=5.0,
        env="DB_HEALTH_CHECK_TIMEOUT",
        ge=1.0,
        le=60.0,
        description="健康检查超时(秒)",
    )

    # 重连配置
    max_retries: int = Field(
        default=3, env="DB_MAX_RETRIES", ge=0, le=10, description="最大重试次数"
    )
    retry_delay: float = Field(
        default=1.0, env="DB_RETRY_DELAY", ge=0.1, le=10.0, description="重试延迟(秒)"
    )

    class Config:
        env_prefix = "DB_POOL_"
        case_sensitive = False
        extra = "ignore"


class FotMobSettings(BaseSettings):
    """FotMob API配置"""

    # API基础配置
    base_url: str = Field(
        default="https://www.fotmob.com/api",
        env="FOTMOB_BASE_URL",
        description="FotMob API基础URL",
    )

    # 鉴权头配置 - 从环境变量加载，无硬编码
    x_mas_header: str = Field(
        default="", env="FOTMOB_X_MAS_HEADER", description="FotMob x-mas鉴权头"
    )
    x_foo_header: str = Field(
        default="", env="FOTMOB_X_FOO_HEADER", description="FotMob x-foo鉴权头"
    )

    # 请求配置
    max_retries: int = Field(
        default=3, env="FOTMOB_MAX_RETRIES", ge=0, le=10, description="API最大重试次数"
    )
    timeout: int = Field(
        default=30, env="FOTMOB_TIMEOUT", ge=5, le=120, description="API请求超时(秒)"
    )
    delay_between_requests: float = Field(
        default=2.0,
        env="FOTMOB_DELAY_BETWEEN_REQUESTS",
        ge=0.1,
        le=10.0,
        description="请求间隔(秒)",
    )

    # 数据采集配置
    batch_size: int = Field(
        default=50, env="FOTMOB_BATCH_SIZE", ge=1, le=1000, description="批处理大小"
    )
    max_concurrent_requests: int = Field(
        default=10,
        env="FOTMOB_MAX_CONCURRENT_REQUESTS",
        ge=1,
        le=100,
        description="最大并发请求数",
    )

    # Circuit Breaker配置
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        env="FOTMOB_CIRCUIT_BREAKER_FAILURE_THRESHOLD",
        ge=1,
        le=20,
        description="熔断器失败阈值",
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=300,  # 5分钟
        env="FOTMOB_CIRCUIT_BREAKER_RECOVERY_TIMEOUT",
        ge=60,
        le=1800,
        description="熔断器恢复超时(秒)",
    )
    circuit_breaker_half_open_max_calls: int = Field(
        default=3,
        env="FOTMOB_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS",
        ge=1,
        le=10,
        description="熔断器半开状态最大调用数",
    )

    @field_validator("x_mas_header", "x_foo_header")
    @classmethod
    def validate_auth_headers(cls, v, info):
        """验证鉴权头在生产环境下不能为空"""
        if not v or v.strip() == "":
            # 在开发环境下允许为空，但给出警告
            if os.getenv("APP_ENV", "development") != "production":
                return v  # 开发环境允许为空
            field_name = (
                info.field_name if hasattr(info, "field_name") else "auth_header"
            )
            raise ValueError(
                f"FotMob {field_name} 在生产环境下不能为空，请设置对应的环境变量"
            )
        return v.strip()

    def get_headers(self) -> Dict[str, str]:
        """获取完整的请求头"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "x-mas": self.x_mas_header,
            "x-foo": self.x_foo_header,
        }

    model_config = SettingsConfigDict(
        env_prefix="FOTMOB_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ApplicationSettings(BaseSettings):
    """应用程序基础配置"""

    # 应用基础信息
    name: str = Field(
        default="FootballPrediction", env="APP_NAME", description="应用名称"
    )
    version: str = Field(default="1.0.0", env="APP_VERSION", description="应用版本")
    environment: str = Field(
        default="development",
        env="APP_ENV",
        pattern="^(development|testing|staging|production)$",
        description="运行环境",
    )
    debug: bool = Field(default=False, env="APP_DEBUG", description="调试模式")

    # 服务配置
    host: str = Field(default="0.0.0.0", env="APP_HOST", description="服务监听地址")
    port: int = Field(
        default=8000, env="APP_PORT", ge=1, le=65535, description="服务端口"
    )
    workers: int = Field(
        default=1, env="APP_WORKERS", ge=1, le=100, description="工作进程数"
    )

    # 性能配置
    request_timeout: int = Field(
        default=300,
        env="APP_REQUEST_TIMEOUT",
        ge=30,
        le=3600,
        description="请求超时(秒)",
    )
    max_request_size: int = Field(
        default=10 * 1024 * 1024,
        env="APP_MAX_REQUEST_SIZE",
        description="最大请求大小(bytes)",
    )

    # 安全配置
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="APP_SECRET_KEY",
        description="应用密钥",
    )
    allowed_hosts: List[str] = Field(
        default=["*"], env="APP_ALLOWED_HOSTS", description="允许的主机列表"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        """验证密钥强度"""
        if len(v) < 32:
            if os.getenv("APP_ENV", "development") != "production":
                # 开发环境给出警告但允许
                import warnings

                warnings.warn(
                    f"应用密钥长度 {len(v)} 少于推荐的32个字符，建议在生产环境使用更长的密钥",
                    UserWarning,
                )
                return v
            raise ValueError("应用密钥长度必须至少32个字符")
        return v

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class LoggingSettings(BaseSettings):
    """日志配置"""

    level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="日志级别",
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT",
        description="日志格式",
    )
    file_path: Optional[str] = Field(
        default=None, env="LOG_FILE_PATH", description="日志文件路径"
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,
        env="LOG_MAX_FILE_SIZE",
        description="日志文件最大大小(bytes)",
    )
    backup_count: int = Field(
        default=5, env="LOG_BACKUP_COUNT", ge=0, le=20, description="日志备份数量"
    )

    # 结构化日志配置
    enable_json_logs: bool = Field(
        default=False, env="LOG_ENABLE_JSON", description="启用JSON格式日志"
    )
    enable_correlation_id: bool = Field(
        default=True, env="LOG_ENABLE_CORRELATION_ID", description="启用关联ID"
    )

    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置字典"""
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": self.format,
                },
                # JSON formatter - 临时禁用以修复启动问题
                # "json": {
                #     "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                #     "fmt": self.format,
                # },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",  # 强制使用default formatter
                    "level": self.level,
                },
            },
            "root": {
                "level": self.level,
                "handlers": ["console"],
            },
            "loggers": {
                "src": {
                    "level": self.level,
                    "handlers": ["console"],
                    "propagate": False,
                },
                "database": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
        }

        return config

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Settings(BaseSettings):
    """主配置类 - 整合所有配置模块"""

    # 配置分组
    database: DatabaseSettings = DatabaseSettings()
    db_pool: DatabasePoolSettings = DatabasePoolSettings()
    fotmob: FotMobSettings = FotMobSettings()
    app: ApplicationSettings = ApplicationSettings()
    logging: LoggingSettings = LoggingSettings()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 允许额外的环境变量，避免CI/运维变量导致启动失败

        # 自定义环境变量加载器
        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ) -> List[Callable[[], Dict[str, Any]]]:
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_config()

    def _validate_config(self):
        """验证配置的完整性和一致性"""
        # 生产环境特殊检查
        if self.app.environment == "production":
            if self.app.debug:
                raise ValueError("生产环境不能启用调试模式")

            if self.app.secret_key == "your-secret-key-change-in-production":
                raise ValueError("生产环境必须设置安全的密钥")

            if not self.fotmob.x_mas_header or not self.fotmob.x_foo_header:
                raise ValueError("生产环境必须设置FotMob API鉴权头")

        # 数据库连接池配置检查
        if self.db_pool.max_size < self.db_pool.min_size:
            raise ValueError("连接池最大大小不能小于最小大小")

        # FotMob API配置检查
        if self.fotmob.max_concurrent_requests > self.db_pool.max_size:
            logger.warning(
                f"并发请求数({self.fotmob.max_concurrent_requests})大于连接池大小({self.db_pool.max_size})，"
                "可能导致请求等待"
            )

    def get_database_pool_config(self) -> "DatabasePoolConfig":
        """获取数据库连接池配置对象"""
        from database.db_pool import DatabasePoolConfig

        return DatabasePoolConfig(
            host=self.database.host,
            port=self.database.port,
            user=self.database.user,
            password=self.database.password,
            database=self.database.database,
            min_size=self.db_pool.min_size,
            max_size=self.db_pool.max_size,
            max_queries=self.db_pool.max_queries,
            max_inactive_connection_lifetime=self.db_pool.max_inactive_connection_lifetime,
            timeout=self.db_pool.timeout,
            command_timeout=self.db_pool.command_timeout,
            health_check_interval=self.db_pool.health_check_interval,
            health_check_timeout=self.db_pool.health_check_timeout,
            max_retries=self.db_pool.max_retries,
            retry_delay=self.db_pool.retry_delay,
        )

    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.app.environment == "development"

    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.app.environment == "production"

    def get_service_url(self) -> str:
        """获取服务URL"""
        return f"http://{self.app.host}:{self.app.port}"

    def summary(self) -> Dict[str, Any]:
        """获取配置摘要（隐藏敏感信息）"""
        return {
            "app": {
                "name": self.app.name,
                "version": self.app.version,
                "environment": self.app.environment,
                "service_url": self.get_service_url(),
            },
            "database": {
                "host": self.database.host,
                "port": self.database.port,
                "database": self.database.database,
                "url": "***" if self.database.url else None,
            },
            "db_pool": {
                "min_size": self.db_pool.min_size,
                "max_size": self.db_pool.max_size,
                "timeout": self.db_pool.timeout,
            },
            "fotmob": {
                "base_url": self.fotmob.base_url,
                "x_mas_configured": bool(self.fotmob.x_mas_header),
                "x_foo_configured": bool(self.fotmob.x_foo_header),
                "max_retries": self.fotmob.max_retries,
            },
            "logging": {
                "level": self.logging.level,
                "json_enabled": self.logging.enable_json_logs,
            },
        }


# 全局配置实例
settings: Settings = Settings()


def get_settings() -> Settings:
    """获取全局配置实例"""
    return settings


def reload_settings() -> Settings:
    """重新加载配置（主要用于测试）"""
    global settings
    settings = Settings()
    return settings


# 配置快捷访问函数
def get_database_url() -> str:
    """获取数据库连接字符串"""
    return settings.database.get_connection_string()


def get_fotmob_headers() -> Dict[str, str]:
    """获取FotMob API请求头"""
    return settings.fotmob.get_headers()


def is_debug_mode() -> bool:
    """是否为调试模式"""
    return settings.app.debug


def get_log_level() -> str:
    """获取日志级别"""
    return settings.logging.level


# 初始化日志
def setup_logging():
    """根据配置初始化日志系统"""
    import logging.config

    config = settings.logging.get_logging_config()
    logging.config.dictConfig(config)

    logger.info(
        f"日志系统初始化完成 - 级别: {settings.logging.level}, "
        f"JSON格式: {settings.logging.enable_json_logs}"
    )


if __name__ == "__main__":
    # 配置测试和验证
    try:
        print("🔧 配置验证开始...")
        print(settings.summary())
        print("✅ 配置验证通过")
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        raise
