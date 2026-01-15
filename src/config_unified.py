#!/usr/bin/env python3
"""
V26.0 统一配置系统 - 工业级纯净架构
=====================================

Version: V26.0 (Stable)

合并config.py和config_secure.py的功能，提供类型安全的统一配置接口。

设计原则:
- Single Configuration Source (单一配置源)
- Type Safety First (类型安全优先)
- Environment Isolation (环境隔离)
- Validation & Defaults (验证与默认值)

配置层级:
1. Core Settings (核心设置)
2. Environment Settings (环境设置)
3. Database Settings (数据库设置)
4. Redis Settings (缓存设置)
5. External API Settings (外部API设置)
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
import os
from pathlib import Path
from typing import Any

# V36.6: 添加用于硬红线检测的异常
class DatabaseConfigurationError(EnvironmentError):
    """V36.6: 数据库配置错误 - 单数据库准则违规"""
    pass

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """环境枚举"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """日志级别枚举"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseConfig:
    """V41.49: 数据库配置 - 优化连接池支持 10 并发"""

    host: str
    port: int
    name: str
    user: str
    password: SecretStr
    ssl_mode: bool = False
    # V41.49: 连接池优化 - 提升 pool_size 支持高并发
    pool_size: int = 15           # 原 10 → 15 (基础连接数)
    max_overflow: int = 20        # 保持 20 (最大溢出数，理论最大 35)
    pool_timeout: int = 10        # 原 30 → 10 (降低超时，防止无限阻塞)
    pool_recycle: int = 600       # 原 3600 → 600 (10分钟回收，避免长连接问题)

    # 新增：异步连接属性（用于 SQLAlchemy async）
    async_url: str | None = None
    async_pool_size: int = 15     # V41.49: 同步提升至 15
    async_max_overflow: int = 20  # 保持 20
    echo: bool = False
    echo_pool: bool = False

    def get_connection_string(self) -> str:
        """获取同步连接字符串"""
        password = self.password.get_secret_value()
        if self.ssl_mode:
            return f"postgresql://{self.user}:{password}@{self.host}:{self.port}/{self.name}?sslmode=require"
        return f"postgresql://{self.user}:{password}@{self.host}:{self.port}/{self.name}"

    def get_async_url(self) -> str:
        """获取异步连接字符串（用于 SQLAlchemy async）"""
        if self.async_url:
            return self.async_url
        password = self.password.get_secret_value()
        prefix = "postgresql+asyncpg://"
        if self.ssl_mode:
            prefix += f"{self.user}:{password}@{self.host}:{self.port}/{self.name}?ssl=require"
        else:
            prefix += f"{self.user}:{password}@{self.host}:{self.port}/{self.name}"
        return prefix


@dataclass
class RedisConfig:
    """Redis配置"""

    host: str
    port: int
    db: int = 0
    password: SecretStr | None = None
    max_connections: int = 20
    socket_timeout: int = 5
    socket_connect_timeout: int = 5

    def get_connection_string(self) -> str:
        """获取Redis连接字符串"""
        if self.password:
            password = self.password.get_secret_value()
            return f"redis://:{password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class FotMobAPIConfig:
    """FotMob API配置"""

    base_url: str = "https://www.fotmob.com/api"
    headers: dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        """初始化后验证"""
        if not self.headers:
            # 默认 headers
            self.headers = {
                "User-Agent": "FootballPrediction/1.0",
                "Accept": "application/json",
            }


class UnifiedSettings(BaseSettings):
    """统一设置类 - 工业级类型安全"""

    # === 环境自动检测和注入 ===
    @classmethod
    def auto_inject_env_vars(cls) -> dict[str, Any]:
        """V41.59: 自动注入环境变量（增强环境检测）"""
        env_config = {}

        # V41.59: 首先加载 .env 文件（确保环境变量可用）
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            logger.debug("python-dotenv 未安装，跳过 .env 文件加载")

        # V41.59: 使用智能环境检测器
        try:
            from src.core.environment_detector import (
                EnvironmentType,
                get_optimal_db_host,
                detect_environment
            )

            current_env = detect_environment()
            monitoring_mode = os.getenv("MONITORING_MODE", "").lower() in ("true", "1", "yes")

            # 根据环境自动配置
            if current_env == EnvironmentType.DOCKER:
                logger.info("🐳 V41.59: Docker 环境自动配置")
                env_config.update(
                    {
                        "db_host": "db",
                        "db_port": int(os.getenv("DB_PORT", 5432)),
                        "db_name": os.getenv("DB_NAME", "football_db"),
                        "db_user": os.getenv("DB_USER", "football_user"),
                        "db_password": os.getenv("DB_PASSWORD", "change-me-in-production"),
                        "redis_host": os.getenv("REDIS_HOST", "redis"),
                        "redis_port": int(os.getenv("REDIS_PORT", 6379)),
                        "environment": "monitoring" if monitoring_mode else "production",
                    }
                )

            elif current_env == EnvironmentType.WSL2:
                logger.info("🟡 V41.59: WSL2 环境自动配置")
                # 获取最优主机（检测端口冲突）
                optimal_host = get_optimal_db_host(
                    preferred_host=os.getenv("DB_HOST"),
                    env_var_host=os.getenv("PGHOST")  # 支持 PGHOST 环境变量
                )
                env_config.update(
                    {
                        "db_host": optimal_host,
                        "db_port": int(os.getenv("DB_PORT", 5432)),
                        "db_name": os.getenv("DB_NAME", "football_db"),
                        "db_user": os.getenv("DB_USER", "football_user"),
                        "db_password": os.getenv("DB_PASSWORD") or os.getenv("PGPASSWORD", "change-me-in-production"),
                        "redis_host": os.getenv("REDIS_HOST", "localhost"),
                        "redis_port": int(os.getenv("REDIS_PORT", 6379)),
                        "environment": "development",
                    }
                )

            else:
                logger.info("🏠 V41.59: 本地环境自动配置")
                env_config.update(
                    {
                        "db_host": os.getenv("DB_HOST", "localhost"),
                        "db_port": int(os.getenv("DB_PORT", 5432)),
                        "db_name": os.getenv("DB_NAME", "football_db"),
                        "db_user": os.getenv("DB_USER", "football_user"),
                        "db_password": os.getenv("DB_PASSWORD") or os.getenv("PGPASSWORD", "change-me-in-production"),
                        "redis_host": os.getenv("REDIS_HOST", "localhost"),
                        "redis_port": int(os.getenv("REDIS_PORT", 6379)),
                        "environment": "development",
                    }
                )

        except ImportError:
            # 回退到旧逻辑（兼容性）
            logger.warning("⚠️  环境检测器未找到，使用旧版配置逻辑")
            docker_env = os.getenv("DOCKER_ENV", "").lower() in ("true", "1", "yes")
            monitoring_mode = os.getenv("MONITORING_MODE", "").lower() in ("true", "1", "yes")

            if docker_env:
                db_password = os.getenv("DB_PASSWORD")
                if not db_password:
                    logger.warning("🚨 Docker环境检测到DB_PASSWORD未设置，请通过环境变量配置")

                env_config.update(
                    {
                        "db_host": "db",
                        "db_port": int(os.getenv("DB_PORT", 5432)),
                        "db_name": os.getenv("DB_NAME", "football_db"),
                        "db_user": os.getenv("DB_USER", "football_user"),
                        "db_password": db_password or "change-me-in-production",
                        "redis_host": os.getenv("REDIS_HOST", "redis"),
                        "redis_port": int(os.getenv("REDIS_PORT", 6379)),
                        "environment": "monitoring" if monitoring_mode else "production",
                    }
                )

        # 自动注入所有FOOTBALL_前缀的环境变量
        for key, value in os.environ.items():
            if key.startswith("FOOTBALL_"):
                config_key = key[9:].lower()  # 去掉FOOTBALL_前缀并转小写
                # 特殊处理某些变量
                if config_key in ["db_host", "redis_host"] and docker_env:
                    continue  # Docker环境下保持容器名
                env_config[config_key] = value

        return env_config

    def __init__(self, **kwargs):
        # V41.51: 数据库大一统 - 强制只允许 football_db
        # 物理消除环境偏差，确保所有连接指向同一个真实数据库
        raw_env_db_name = os.environ.get('DB_NAME')

        # V41.51: 单数据库准则 - 强制只允许 football_db
        ALLOWED_DB_NAME = 'football_db'

        # 如果设置了 DB_NAME，必须是 football_db
        if raw_env_db_name and raw_env_db_name != ALLOWED_DB_NAME:
            raise DatabaseConfigurationError(
                f"🚨 V41.51 数据库大一统：非法数据库名称\n"
                f"   检测到: DB_NAME='{raw_env_db_name}'\n"
                f"   系统只允许: '{ALLOWED_DB_NAME}'\n"
                f"   请检查 .env 文件，确保 DB_NAME={ALLOWED_DB_NAME}"
            )

        # V36.6: 单数据库准则 - 先注入环境变量以便进行硬红线检测
        auto_env = self.auto_inject_env_vars()

        # 用户传入的参数优先级更高
        auto_env.update(kwargs)

        # V41.51: 单数据库准则 - 强制只允许 football_db
        raw_db_name = auto_env.get('db_name', kwargs.get('db_name', 'football_db'))
        if raw_db_name != ALLOWED_DB_NAME:
            raise DatabaseConfigurationError(
                f"🚨 V41.51 数据库大一统：非法数据库名称\n"
                f"   检测到: '{raw_db_name}'\n"
                f"   系统只允许: '{ALLOWED_DB_NAME}'\n"
                f"   请检查配置文件，确保 db_name={ALLOWED_DB_NAME}"
            )

        super().__init__(**auto_env)

    # === 环境配置 ===
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="运行环境")

    debug: bool = Field(default=False, description="调试模式")

    log_level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")

    # === 应用配置 ===
    app_name: str = Field(default="Football Prediction System", description="应用名称")

    app_version: str = Field(default="1.0.0", description="应用版本")

    host: str = Field(default="0.0.0.0", description="服务监听地址")

    port: int = Field(default=8000, description="服务端口")

    workers: int = Field(default=1, description="工作进程数")

    # === 安全配置 ===
    # 生产环境必须通过环境变量设置，开发环境默认值不安全
    secret_key: SecretStr = Field(
        default=SecretStr("dev-secret-key-change-in-production-minimum-32-chars"),
        description="应用密钥（生产环境必须通过环境变量设置）",
    )

    allowed_hosts: list[str] = Field(default=["localhost", "127.0.0.1"], description="允许的主机列表")

    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], description="CORS允许的源"
    )

    # === 数据库配置 ===
    # V41.59: 智能环境检测 - 自动选择最优数据库主机
    db_host: str = Field(
        default="localhost",
        description="数据库主机 (V41.59: 支持环境智能检测)"
    )

    db_port: int = Field(default=5432, description="数据库端口")

    # V36.6: 单数据库准则 - 强制使用 football_db
    db_name: str = Field(default="football_db", description="数据库名称")

    db_user: str = Field(default="football_user", description="数据库用户名")

    db_password: SecretStr = Field(description="数据库密码")

    db_ssl_mode: bool = Field(default=False, description="数据库SSL模式（生产环境建议启用，设置DB_SSL_MODE=true）")

    db_pool_size: int = Field(default=10, description="数据库连接池大小")

    # === Redis配置 ===
    redis_host: str = Field(default="localhost", description="Redis主机")

    redis_port: int = Field(default=6379, description="Redis端口")

    redis_db: int = Field(default=0, description="Redis数据库")

    redis_password: SecretStr | None = Field(default=None, description="Redis密码")

    # === 外部API配置 ===
    fotmob_base_url: str = Field(default="https://www.fotmob.com/api", description="FotMob API基础URL")

    fotmob_web_url: str = Field(default="https://www.fotmob.com", description="FotMob 网站基础URL")

    fotmob_x_mas_header: str | None = Field(default=None, description="FotMob X-MAS Header")

    fotmob_x_foo_header: str | None = Field(default=None, description="FotMob X-FOO Header")

    oddsportal_base_url: str = Field(default="https://www.oddsportal.com", description="OddsPortal基础URL")

    oddsportal_timeout_ms: int = Field(default=30000, description="OddsPortal请求超时时间（毫秒）")

    oddsportal_retry_attempts: int = Field(default=3, description="OddsPortal重试次数")

    # === 模型配置 ===
    # 使用 model_zoo 目录中的 V19.4 生产模型
    model_path: str = Field(
        default="model_zoo/v19.4_draw_sensitivity_model.pkl", description="模型文件路径（指向 model_zoo 目录）"
    )

    model_version: str = Field(default="xgboost_v2", description="模型版本")

    # === 监控配置 ===
    enable_metrics: bool = Field(default=True, description="启用指标收集")

    metrics_port: int = Field(default=9090, description="指标端口")

    enable_tracing: bool = Field(default=False, description="启用链路追踪")

    # === 缓存配置 ===
    cache_ttl_seconds: int = Field(default=300, description="缓存TTL（秒）")

    cache_max_size: int = Field(default=1000, description="缓存最大条目数")

    # === 业务配置 ===
    default_confidence_threshold: float = Field(default=0.6, description="默认置信度阈值")

    max_batch_size: int = Field(default=100, description="最大批量处理大小")

    prediction_timeout_seconds: int = Field(default=30, description="预测超时时间（秒）")

    # === V3.2 三联赛原生支持配置 ===
    supported_leagues: dict[str, Any] = Field(
        default_factory=lambda: {
            "serie_a": {"id": 135, "name": "Serie A", "country": "Italy", "active": True, "priority": 1},
            "la_liga": {"id": 87, "name": "La Liga", "country": "Spain", "active": True, "priority": 2},
            "bundesliga": {"id": 54, "name": "Bundesliga", "country": "Germany", "active": True, "priority": 3},
        },
        description="V3.2 三联赛原生支持配置",
    )

    # === ROI 配置 (V2.3.1) ===
    min_edge: float = Field(default=7.0, description="最小边际值 (%)")
    min_confidence: float = Field(default=45.0, description="最小置信度 (%)")
    target_roi: float = Field(default=13.35, description="目标ROI (%)")

    # === 数据收集配置 ===
    data_retention_days: int = Field(default=365, description="数据保留天数")
    harvest_batch_size: int = Field(default=50, description="数据收集批量大小")
    harvest_delay_seconds: float = Field(default=1.0, description="数据收集间隔（秒）")

    # V26.5: IP 冷却期安全配置
    collection_pause_until: str | None = Field(
        default=None,
        description="IP 冷却期截止时间 (ISO 8601 格式)，在此时间之前禁止数据采集，防止 IP 封禁",
    )

    # === V26.0 流水线配置 (标准化参数) ===
    # 比赛状态常量 (统一大小写处理)
    match_status_finished: str = Field(default="FINISHED", description="比赛完成状态")
    match_status_scheduled: str = Field(default="SCHEDULED", description="比赛计划状态")
    match_status_live: str = Field(default="LIVE", description="比赛进行中状态")
    match_status_postponed: str = Field(default="POSTPONED", description="比赛推迟状态")

    # 特征提取状态常量
    feature_status_pending: str = Field(default="PENDING", description="特征待提取状态")
    feature_status_processing: str = Field(default="PROCESSING", description="特征提取中状态")
    feature_status_completed: str = Field(default="COMPLETED", description="特征提取完成状态")
    feature_status_failed: str = Field(default="FAILED", description="特征提取失败状态")

    # 流水线处理参数
    pipeline_batch_size: int = Field(default=50, description="流水线批次处理大小")
    pipeline_gc_interval: int = Field(default=50, description="GC调用间隔（记录数）")
    max_l2_concurrency: int = Field(default=2, description="L2解析最大并发数")
    pipeline_target_version: str = Field(default="V26.0", description="目标特征版本")

    # Pydantic V2 配置
    model_config = SettingsConfigDict(
        # 启用.env文件自动加载，支持环境变量配置
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # 允许额外字段（用于向后兼容）- Pydantic V2 语法
        extra="ignore",
    )

    # === 验证器 ===
    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """验证端口范围"""
        if not 1 <= v <= 65535:
            raise ValueError("端口必须在1-65535范围内")
        return v

    @field_validator("workers")
    @classmethod
    def validate_workers(cls, v: int) -> int:
        """验证工作进程数"""
        if v < 1:
            raise ValueError("工作进程数必须大于0")
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: SecretStr) -> SecretStr:
        """验证密钥强度"""
        secret = v.get_secret_value()
        if len(secret) < 32:
            raise ValueError("密钥长度必须至少32个字符")
        return v

    @field_validator("default_confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, v: float) -> float:
        """验证置信度阈值"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("置信度阈值必须在0.0-1.0之间")
        return v

    @field_validator("max_batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """验证批量大小"""
        if not 1 <= v <= 1000:
            raise ValueError("批量大小必须在1-1000之间")
        return v

    @field_validator("db_host")
    @classmethod
    def validate_db_host(cls, v: str, info: ValidationInfo) -> str:
        """自动适配Docker环境的数据库主机"""
        # 检查是否在Docker环境中
        docker_env = os.getenv("DOCKER_ENV", "").lower() in ("true", "1", "yes")
        environment = info.data.get("environment", "development")

        # 如果明确设置了DOCKER_ENV=true，自动使用db作为主机名
        if docker_env:
            logger.info("🐳 检测到Docker环境，自动使用db作为数据库主机")
            return "db"

        # 如果在生产环境中且没有显式设置主机，使用db
        if environment in ("production", "staging") and v == "localhost":
            logger.info("🏭 生产环境，自动使用db作为数据库主机")
            return "db"

        # 否则使用原设置
        return v

    @field_validator("redis_host")
    @classmethod
    def validate_redis_host(cls, v: str, info: ValidationInfo) -> str:
        """自动适配Docker环境的Redis主机"""
        # 检查是否在Docker环境中
        docker_env = os.getenv("DOCKER_ENV", "").lower() in ("true", "1", "yes")
        environment = info.data.get("environment", "development")

        # 如果明确设置了DOCKER_ENV=true，自动使用redis作为主机名
        if docker_env:
            logger.info("🐳 检测到Docker环境，自动使用redis作为Redis主机")
            return "redis"

        # 如果在生产环境中且没有显式设置主机，使用redis
        if environment in ("production", "staging") and v == "localhost":
            logger.info("🏭 生产环境，自动使用redis作为Redis主机")
            return "redis"

        # 否则使用原设置
        return v

    @field_validator("db_name")
    @classmethod
    def validate_db_name(cls, v: str) -> str:
        """V41.51: 数据库大一统 - 强制只允许 football_db

        物理消除环境偏差，确保所有连接指向同一个真实数据库
        """
        # V41.51: 单数据库准则 - 强制只允许 football_db
        ALLOWED_DB_NAME = 'football_db'

        if v != ALLOWED_DB_NAME:
            raise DatabaseConfigurationError(
                f"🚨 V41.51 数据库大一统：非法数据库名称\n"
                f"   检测到: '{v}'\n"
                f"   系统只允许: '{ALLOWED_DB_NAME}'\n"
                f"   请检查配置文件，确保 db_name={ALLOWED_DB_NAME}"
            )

        return v

    # === 属性方法 ===
    @property
    def database(self) -> DatabaseConfig:
        """获取数据库配置"""
        # 构建异步 URL
        password = self.db_password.get_secret_value()
        if self.db_ssl_mode:
            async_url = f"postgresql+asyncpg://{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}?ssl=require"
        else:
            async_url = f"postgresql+asyncpg://{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"

        return DatabaseConfig(
            host=self.db_host,
            port=self.db_port,
            name=self.db_name,
            user=self.db_user,
            password=self.db_password,
            ssl_mode=self.db_ssl_mode,
            pool_size=self.db_pool_size,
            max_overflow=self.db_pool_size,  # 使用 pool_size 作为 max_overflow 默认值
            pool_timeout=30,
            pool_recycle=3600,
            # 异步连接属性 - 现在动态构建
            async_url=async_url,
            async_pool_size=self.db_pool_size,
            async_max_overflow=self.db_pool_size,
            echo=False,
            echo_pool=False,
        )

    @property
    def redis(self) -> RedisConfig:
        """获取Redis配置"""
        return RedisConfig(
            host=self.redis_host,
            port=self.redis_port,
            db=self.redis_db,
            password=self.redis_password,
        )

    @property
    def fotmob_api(self) -> FotMobAPIConfig:
        """获取FotMob API配置"""
        headers = {}
        if self.fotmob_x_mas_header:
            headers["X-MAS"] = self.fotmob_x_mas_header
        if self.fotmob_x_foo_header:
            headers["X-FOO"] = self.fotmob_x_foo_header

        return FotMobAPIConfig(
            base_url=self.fotmob_base_url,
            headers=headers,
        )

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == Environment.DEVELOPMENT

    # === 便捷方法 ===
    def get_model_path(self) -> Path:
        """获取模型文件路径"""
        return Path(self.model_path)

    def get_log_config(self) -> dict[str, Any]:
        """获取日志配置"""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
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
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                },
            },
            "root": {
                "level": self.log_level.value,
                "handlers": ["console", "file"] if not self.is_development else ["console"],
            },
        }

    def validate_integrity(self) -> list[str]:
        """验证配置完整性（已弃用，请使用 validate_environment）"""
        return self._validate_config_basic()

    def _validate_config_basic(self) -> list[str]:
        """基础配置验证"""
        errors = []

        # 检查必需的配置
        if not self.secret_key.get_secret_value():
            errors.append("secret_key 不能为空")

        if not self.db_password.get_secret_value():
            errors.append("db_password 不能为空")

        # 检查路径
        if not self.get_model_path().exists():
            errors.append(f"模型文件不存在: {self.model_path}")

        # 检查环境特定的配置
        if self.is_production:
            if self.debug:
                errors.append("生产环境不应启用debug模式")
            if not self.enable_metrics:
                errors.append("生产环境应启用指标收集")
            if "localhost" in self.allowed_hosts:
                errors.append("生产环境allowed_hosts不应包含localhost")

        return errors

    def validate_environment(self) -> dict[str, Any]:
        """验证环境配置完整性（新增方法）

        Returns:
            包含验证结果的字典：
            - valid: bool - 是否所有检查都通过
            - issues: List[str] - 严重问题列表
            - warnings: List[str] - 警告列表
            - environment: str - 当前环境
            - score: float - 健康分数 (0-100)
        """
        issues = []
        warnings = []

        # === 必需配置检查 ===
        if not self.db_password.get_secret_value():
            issues.append("DB_PASSWORD 未设置（开发环境可使用默认值）")

        if not self.secret_key.get_secret_value():
            issues.append("SECRET_KEY 未设置")

        # === 生产环境特殊检查 ===
        if self.is_production:
            if len(self.secret_key.get_secret_value()) < 32:
                issues.append("生产环境 SECRET_KEY 必须至少 32 字符")

            if self.db_password.get_secret_value() in ["football_pass", "password", "123456"]:
                issues.append("生产环境使用了不安全的默认数据库密码")

            if self.debug:
                issues.append("生产环境不应启用 debug 模式")

            if "localhost" in self.allowed_hosts or "127.0.0.1" in self.allowed_hosts:
                warnings.append("生产环境 allowed_hosts 包含 localhost，请确认是否正确")

        # === 可选配置警告 ===
        if not self.redis_host or self.redis_host == "localhost":
            warnings.append("REDIS_HOST 未配置或为 localhost，缓存功能可能不可用")

        if not self.enable_metrics:
            warnings.append("ENABLE_METRICS 为 False，监控指标收集已禁用")

        # === 数据库连接检查 ===
        if self.db_host == "localhost" and self.environment in ["production", "staging"]:
            warnings.append(f"{self.environment.value} 环境使用 localhost 作为数据库主机，请确认")

        # === 计算健康分数 ===
        score = 100.0
        score -= len(issues) * 25  # 每个严重问题扣 25 分
        score -= len(warnings) * 5  # 每个警告扣 5 分
        score = max(0, score)

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "environment": self.environment.value,
            "score": score,
        }


# === 全局设置实例 ===
_settings_instance: UnifiedSettings | None = None


def get_settings() -> UnifiedSettings:
    """获取全局设置实例（单例模式）"""
    global _settings_instance
    if _settings_instance is None:
        # V36.6: 单数据库准则 - 强制执行硬红线检测
        # 即使创建最小配置时也必须检查数据库配置
        try:
            _settings_instance = UnifiedSettings()

            # 验证配置完整性
            errors = _settings_instance.validate_integrity()
            if errors:
                logger.warning(f"配置验证警告: {'; '.join(errors)}")

            # V41.77: 数据库隔离检测
            _validate_database_environment(_settings_instance)

        except DatabaseConfigurationError:
            # V36.6: 硬红线违规 - 必须失败，不允许绕过
            raise
        except Exception as e:
            logger.warning(f"配置初始化警告: {e}")
            # V36.6: 即使创建最小配置时也必须检查数据库配置
            # 先检查环境变量中的数据库名称
            raw_db_name = os.getenv("DB_NAME", "football_db")
            if raw_db_name != "football_db":
                raise DatabaseConfigurationError(
                    f"🚨 非法数据库配置！\n"
                    f"   系统只允许连接 'football_db'，检测到: '{raw_db_name}'\n"
                    f"   请检查 .env 文件和环境变量，确保 DB_NAME=football_db"
                )
            # 创建最小可用配置（只有在数据库配置正确时）
            _settings_instance = UnifiedSettings(
                environment=Environment.DEVELOPMENT,
                debug=True,
                secret_key=SecretStr("dev-secret-key-please-change-in-production"),
            )

    return _settings_instance


def _validate_database_environment(settings: UnifiedSettings) -> None:
    """
    V41.77: 验证数据库环境

    Args:
        settings: 配置实例

    Raises:
        DatabaseConfigurationError: 环境验证失败时
    """
    # 检查环境变量是否禁用了环境检测
    skip_validation = os.getenv("SKIP_ENV_VALIDATION", "").lower() in ("1", "true", "yes")

    if skip_validation:
        logger.warning("⚠️  环境检测已跳过 (SKIP_ENV_VALIDATION=1)")
        return

    try:
        from src.core.environment_validator import (
            validate_no_local_postgres_conflict,
            validate_database_environment
        )

        db_port = settings.database.port

        # 检查本地 PostgreSQL 冲突
        validate_no_local_postgres_conflict(db_port)

        # 验证数据库环境
        db_host = settings.database.host
        validate_database_environment(
            db_host=db_host,
            db_port=db_port,
            allow_docker=True,
            allow_local=False
        )

        logger.info("✅ V41.77: 数据库环境验证通过")

    except ImportError:
        logger.warning("⚠️  环境检测模块不可用，跳过验证")
    except Exception as e:
        raise DatabaseConfigurationError(
            f"🚨 V41.77: 数据库环境验证失败\n"
            f"   错误: {e}\n"
            f"   请确保数据库环境正确配置"
        )


def reload_settings() -> UnifiedSettings:
    """重新加载设置"""
    global _settings_instance
    _settings_instance = None
    return get_settings()


# === 便捷函数 ===
def get_database_url() -> str:
    """获取数据库连接字符串"""
    return get_settings().database.get_connection_string()


def get_redis_url() -> str:
    """获取Redis连接字符串"""
    return get_settings().redis.get_connection_string()


def is_production() -> bool:
    """检查是否为生产环境"""
    return get_settings().is_production


def is_development() -> bool:
    """检查是否为开发环境"""
    return get_settings().is_development


# === 类型安全的配置访问器 ===
@dataclass
class ConfigAccessor:
    """类型安全的配置访问器"""

    _settings: UnifiedSettings = field(default_factory=get_settings)

    @property
    def database(self) -> DatabaseConfig:
        """获取数据库配置"""
        return self._settings.database

    @property
    def redis(self) -> RedisConfig:
        """获取Redis配置"""
        return self._settings.redis

    @property
    def fotmob_api(self) -> FotMobAPIConfig:
        """获取FotMob API配置"""
        return self._settings.fotmob_api

    def reload(self) -> None:
        """重新加载配置"""
        self._settings = reload_settings()


# 全局配置访问器（延迟初始化）
config = None


def get_config() -> ConfigAccessor:
    """获取配置访问器（延迟初始化）"""
    global config
    if config is None:
        config = ConfigAccessor()
    return config
