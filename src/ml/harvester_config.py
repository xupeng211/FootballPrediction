#!/usr/bin/env python3
"""
V20.8 Harvester 专用配置 - Pydantic BaseSettings
===============================================

设计原则:
- 使用 Pydantic BaseSettings 自动加载环境变量
- 移除 os.environ 手动注入
- 提供默认值和验证

作者: SRE Lead
日期: 2025-12-25
版本: V20.8
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class HarvesterSettings(BaseSettings):
    """
    V20.8 Harvester 配置类

    优先级 (Pydantic 自动处理):
    1. 环境变量
    2. .env 文件
    3. 默认值
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    # ==================== 数据库配置 ====================
    # V20.8 显式环境变量（容器内优先）
    postgres_password: str = Field(default="football_pass", alias="POSTGRES_PASSWORD")
    db_name: str = Field(default="football_db", alias="DB_NAME")
    postgres_user: str = Field(default="football_user", alias="POSTGRES_USER")
    db_host: str = Field(default="db", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")

    # 兼容旧环境变量
    football_db_host: str | None = Field(default=None, alias="FOOTBALL_DB_HOST")
    football_db_name: str | None = Field(default=None, alias="FOOTBALL_DB_NAME")
    db_password: str | None = Field(default=None, alias="DB_PASSWORD")
    db_user: str | None = Field(default=None, alias="DB_USER")

    # ==================== 连接配置 ====================
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_connect_timeout: int = Field(default=10, alias="DB_CONNECT_TIMEOUT")
    db_retry_attempts: int = Field(default=3, alias="DB_RETRY_ATTEMPTS")
    db_retry_delay: float = Field(default=1.0, alias="DB_RETRY_DELAY")

    # ==================== 日志配置 ====================
    harvest_log_file: str = Field(default="/var/log/harvester/harvest.log", alias="HARVEST_LOG_FILE")
    harvest_log_level: str = Field(default="INFO", alias="HARVEST_LOG_LEVEL")
    harvest_log_max_bytes: int = Field(default=50 * 1024 * 1024, alias="HARVEST_LOG_MAX_BYTES")
    harvest_log_backup_count: int = Field(default=5, alias="HARVEST_LOG_BACKUP_COUNT")

    # ==================== API 配置 ====================
    fotmob_api_timeout: int = Field(default=30, alias="FOTMOB_API_TIMEOUT")
    fotmob_api_retry: int = Field(default=3, alias="FOTMOB_API_RETRY")

    # ==================== 维度死结配置 ====================
    min_features: int = Field(default=881, alias="MIN_FEATURES")
    target_features: int = Field(default=881, alias="TARGET_FEATURES")
    dimension_fuse_count: int = Field(default=5, alias="DIMENSION_FUSE_COUNT")

    @field_validator("db_host")
    @classmethod
    def validate_db_host(cls, v):
        """
        自动探测数据库主机

        - 'db' -> Docker 容器内
        - 'localhost' -> 宿主机
        """
        if v == "db":
            try:
                import socket

                socket.gethostbyname("db")
                return "db"
            except socket.gaierror:
                # 非 Docker 环境，自动切换
                return "localhost"
        return v

    def get_db_params(self) -> dict:
        """
        获取数据库连接参数（用于 psycopg2.connect）

        Returns:
            数据库连接参数字典
        """
        # 优先级：显式环境变量 > 兼容环境变量 > 默认值
        host = self.db_host
        if self.football_db_host:
            host = self.football_db_host

        port = self.db_port
        database = self.db_name
        if self.football_db_name:
            database = self.football_db_name

        user = self.postgres_user
        if self.db_user:
            user = self.db_user

        password = self.postgres_password
        if self.db_password:
            password = self.db_password

        return {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
            "connect_timeout": self.db_connect_timeout,
        }

    def get_log_params(self) -> dict:
        """获取日志配置参数"""
        return {
            "log_file": self.harvest_log_file,
            "log_level": self.harvest_log_level,
            "max_bytes": self.harvest_log_max_bytes,
            "backup_count": self.harvest_log_backup_count,
        }


# ==================== 单例模式 ====================
_harvester_settings: HarvesterSettings | None = None


def get_harvester_settings() -> HarvesterSettings:
    """
    获取 Harvester 配置单例

    Returns:
        HarvesterSettings 实例
    """
    global _harvester_settings
    if _harvester_settings is None:
        _harvester_settings = HarvesterSettings()
    return _harvester_settings


def reload_harvester_settings() -> HarvesterSettings:
    """
    重新加载配置（用于测试或动态更新）

    Returns:
        新的 HarvesterSettings 实例
    """
    global _harvester_settings
    _harvester_settings = HarvesterSettings()
    return _harvester_settings
