"""
Titan007 采集器配置管理
Titan007 Collector Configuration Management

基于 Pydantic Settings 的配置管理，支持环境变量和 .env 文件配置。
解决硬编码问题，支持生产环境动态调优。

使用示例:
    from src.config.titan_settings import get_titan_settings

    settings = get_titan_settings()

    # 使用配置
    collector = BaseTitanCollector(
        base_url=settings.titan.base_url,
        max_retries=settings.titan.max_retries,
        timeout=settings.titan.timeout
    )
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class TitanCollectorSettings(BaseSettings):
    """Titan007 采集器配置"""

    # API 配置
    base_url: str = Field(
        default="https://live.titan007.com/api/odds", description="Titan API 基础URL"
    )

    # 重试配置
    max_retries: int = Field(default=3, ge=0, le=10, description="最大重试次数")

    timeout: float = Field(
        default=30.0, ge=1.0, le=300.0, description="请求超时时间（秒）"
    )

    # 连接池配置
    max_connections: int = Field(
        default=10, ge=1, le=100, description="HTTP连接池最大连接数"
    )

    max_keepalive_connections: int = Field(
        default=5, ge=1, le=50, description="HTTP连接池最大保持连接数"
    )

    # 重试策略配置
    retry_multiplier: float = Field(
        default=0.5, ge=0.1, le=2.0, description="重试退避倍数"
    )

    retry_min_wait: float = Field(
        default=1.0, ge=0.1, description="最小重试等待时间（秒）"
    )

    retry_max_wait: float = Field(
        default=10.0, ge=1.0, description="最大重试等待时间（秒）"
    )

    # 限流配置
    rate_limit_qps: float = Field(default=2.0, ge=0.1, description="每秒请求数限制")

    rate_limit_burst: int = Field(default=1, ge=1, description="突发请求数限制")

    rate_limit_max_wait: float = Field(
        default=30.0, ge=1.0, description="限流最大等待时间（秒）"
    )

    class Config:
        env_prefix = "TITAN_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量


class DatabasePoolSettings(BaseSettings):
    """数据库连接池配置"""

    pool_size: int = Field(default=20, ge=5, le=100, description="数据库连接池大小")

    max_overflow: int = Field(
        default=30, ge=10, le=100, description="数据库连接池最大溢出"
    )

    pool_timeout: int = Field(
        default=60, ge=10, le=300, description="获取连接超时时间（秒）"
    )

    pool_recycle: int = Field(default=3600, ge=1800, description="连接回收时间（秒）")

    class Config:
        env_prefix = "DB_POOL_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class TitanSettings(BaseSettings):
    """Titan007 完整配置"""

    titan: TitanCollectorSettings = Field(default_factory=TitanCollectorSettings)
    db_pool: DatabasePoolSettings = Field(default_factory=DatabasePoolSettings)

    # 环境标识
    environment: str = Field(default="development", description="运行环境")

    # 调试模式
    debug: bool = Field(default=False, description="是否启用调试模式")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# 全局配置实例（单例）
_settings: Optional[TitanSettings] = None


def get_titan_settings() -> TitanSettings:
    """获取 Titan007 配置（单例模式）"""
    global _settings
    if _settings is None:
        _settings = TitanSettings()
    return _settings


def reload_titan_settings() -> TitanSettings:
    """重新加载配置（主要用于测试）"""
    global _settings
    _settings = None
    return get_titan_settings()


# 便捷属性访问
titan_settings = get_titan_settings()
