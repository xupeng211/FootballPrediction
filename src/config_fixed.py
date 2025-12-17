#!/usr/bin/env python3
"""
应用配置管理模块 - 修复版本

使用Pydantic Settings v2进行配置管理，从环境变量加载所有配置参数。
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
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    )

    def get_connection_string(self) -> str:
        """获取数据库连接字符串"""
        if self.url:
            return self.url
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("端口号必须在1-65535之间")
        return v


class DatabasePoolSettings(BaseSettings):
    """数据库连接池配置"""

    # 连接池大小配置
    min_size: int = Field(default=5, ge=1, le=100, description="最小连接数")
    max_size: int = Field(default=20, ge=1, le=1000, description="最大连接数")
    max_queries: int = Field(default=50000, ge=100, description="每连接最大查询数")
    max_inactive_connection_lifetime: float = Field(
        default=300.0, ge=10.0, le=3600.0, description="连接最大非活跃时间(秒)"
    )

    # 超时配置
    timeout: float = Field(default=60.0, ge=1.0, le=600.0, description="连接超时(秒)")
    command_timeout: float = Field(
        default=30.0, ge=1.0, le=300.0, description="命令超时(秒)"
    )

    model_config = SettingsConfigDict(
        env_prefix="DB_POOL_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("max_size")
    @classmethod
    def validate_max_size(cls, v, info):
        if info.data and "min_size" in info.data and v < info.data["min_size"]:
            raise ValueError("最大连接数不能小于最小连接数")
        return v


class FotMobSettings(BaseSettings):
    """FotMob API配置"""

    # API基本配置
    base_url: str = Field(
        default="https://www.fotmob.com/api", description="FotMob API基础URL"
    )
    timeout: int = Field(default=30, ge=1, le=300, description="API请求超时(秒)")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="重试次数")

    # 请求头配置
    x_mas_header: str = Field(default="", description="X-MAS请求头")
    x_foo_header: str = Field(default="", description="X-FOO请求头")
    user_agent: str = Field(
        default="FootballPrediction/1.0.0", description="User-Agent"
    )

    model_config = SettingsConfigDict(
        env_prefix="FOTMOB_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    def get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if self.x_mas_header:
            headers["X-MAS"] = self.x_mas_header
        if self.x_foo_header:
            headers["X-FOO"] = self.x_foo_header

        return headers


class ApplicationSettings(BaseSettings):
    """应用基本配置"""

    # 应用信息
    name: str = Field(default="Football Prediction API", description="应用名称")
    version: str = Field(default="1.0.0", description="应用版本")
    description: str = Field(
        default="Football match prediction API using machine learning",
        description="应用描述",
    )

    # 服务器配置
    host: str = Field(default="0.0.0.0", description="服务器主机")
    port: int = Field(default=8000, ge=1, le=65535, description="服务器端口")
    debug: bool = Field(default=False, description="调试模式")

    # 安全配置
    secret_key: str = Field(
        default="your-secret-key-change-in-production", description="JWT密钥"
    )
    access_token_expire_minutes: int = Field(
        default=30, ge=1, le=1440, description="访问令牌过期时间(分钟)"
    )

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )


class LoggingSettings(BaseSettings):
    """日志配置"""

    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式",
    )
    file_path: Optional[str] = Field(default=None, description="日志文件路径")
    max_file_size: int = Field(
        default=10485760, ge=1024, description="日志文件最大大小(字节)"  # 10MB
    )
    backup_count: int = Field(default=5, ge=1, le=100, description="日志文件备份数量")

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"日志级别必须是以下之一: {valid_levels}")
        return v.upper()


class Settings(BaseSettings):
    """主配置类 - 整合所有配置模块"""

    # 配置模块
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    database_pool: DatabasePoolSettings = Field(default_factory=DatabasePoolSettings)
    fotmob: FotMobSettings = Field(default_factory=FotMobSettings)
    app: ApplicationSettings = Field(default_factory=ApplicationSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    # 其他配置
    environment: str = Field(
        default="development", description="运行环境 (development, testing, production)"
    )
    timezone: str = Field(default="UTC", description="时区")
    max_workers: int = Field(default=4, ge=1, le=50, description="最大工作线程数")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 忽略额外的环境变量
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        valid_envs = ["development", "testing", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"环境必须是以下之一: {valid_envs}")
        return v.lower()

    def is_production(self) -> bool:
        """检查是否为生产环境"""
        return self.environment == "production"

    def is_development(self) -> bool:
        """检查是否为开发环境"""
        return self.environment == "development"

    def get_database_connection_string(self) -> str:
        """获取数据库连接字符串"""
        return self.database.get_connection_string()

    def get_fotmob_headers(self) -> Dict[str, str]:
        """获取FotMob API请求头"""
        return self.fotmob.get_headers()

    def is_debug_mode(self) -> bool:
        """检查是否为调试模式"""
        return self.app.debug or self.is_development()


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取全局配置实例"""
    return settings


def get_database_connection_string() -> str:
    """获取数据库连接字符串"""
    return settings.database.get_connection_string()


def get_fotmob_headers() -> Dict[str, str]:
    """获取FotMob API请求头"""
    return settings.fotmob.get_headers()


def is_debug_mode() -> bool:
    """检查是否为调试模式"""
    return settings.is_debug_mode()


def is_production_mode() -> bool:
    """检查是否为生产模式"""
    return settings.is_production()


def reload_settings() -> Settings:
    """重新加载配置"""
    global settings
    settings = Settings()
    return settings


def validate_configuration() -> Dict[str, Any]:
    """验证配置有效性"""
    issues = []
    warnings = []

    # 检查数据库配置
    if not settings.database.user:
        issues.append("数据库用户名不能为空")
    if not settings.database.password:
        warnings.append("数据库密码为空，可能存在安全风险")

    # 检查FotMob配置
    if not settings.fotmob.x_mas_header and not settings.fotmob.x_foo_header:
        warnings.append("FotMob API请求头未配置，可能影响数据获取")

    # 检查应用配置
    if settings.app.secret_key == "your-secret-key-change-in-production":
        if settings.is_production():
            issues.append("生产环境必须更改默认密钥")
        else:
            warnings.append("使用了默认密钥，生产环境前必须更改")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "environment": settings.environment,
    }


if __name__ == "__main__":
    # 配置测试
    print("🧪 配置模块测试")

    try:
        # 创建配置实例
        config = Settings()
        print(f"✅ 配置创建成功")
        print(f"   环境: {config.environment}")
        print(f"   应用: {config.app.name} v{config.app.version}")
        print(
            f"   数据库: {config.database.host}:{config.database.port}/{config.database.database}"
        )

        # 验证配置
        validation = validate_configuration()
        if validation["valid"]:
            print("✅ 配置验证通过")
        else:
            print("⚠️ 配置验证发现问题:")
            for issue in validation["issues"]:
                print(f"   ❌ {issue}")

        # 显示警告
        if validation["warnings"]:
            print("⚠️ 配置警告:")
            for warning in validation["warnings"]:
                print(f"   ⚠️ {warning}")

        # 测试连接字符串生成
        conn_str = get_database_connection_string()
        print(f"📡 数据库连接字符串: {conn_str}")

        # 测试API头生成
        headers = get_fotmob_headers()
        print(f"🔗 FotMob API头: {headers}")

        print("\n🎉 配置模块测试完成!")

    except Exception as e:
        print(f"❌ 配置模块测试失败: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
