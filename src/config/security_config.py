"""安全配置管理
Security Configuration Management.

提供安全相关的配置管理功能:
- 环境变量管理
- 敏感信息处理
- 配置验证
- 安全默认值
"""

import logging
import os
import secrets
from typing import Any

logger = logging.getLogger(__name__)


class SecurityConfig:
    """安全配置管理类."""

    def __init__(self):
        """初始化安全配置."""
        self._load_config()

    def _load_config(self):
        """加载安全配置."""
        # 数据库配置
        self.database_url = os.getenv("DATABASE_URL")
        self.database_host = os.getenv("DATABASE_HOST", "localhost")
        self.database_port = os.getenv("DATABASE_PORT", "5432")
        self.database_name = os.getenv("DATABASE_NAME", "football_prediction")
        self.database_user = os.getenv("DATABASE_USER")
        self.database_password = os.getenv("DATABASE_PASSWORD")

        # Redis配置
        self.redis_url = os.getenv("REDIS_URL")
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = os.getenv("REDIS_PORT", "6379")
        self.redis_password = os.getenv("REDIS_PASSWORD")

        # 安全密钥
        self.secret_key = os.getenv("SECRET_KEY")
        if not self.secret_key:
            logger.warning(
                "SECRET_KEY not found in environment, generating temporary key"
            )
            self.secret_key = secrets.token_urlsafe(32)

        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.jwt_secret_key:
            logger.warning(
                "JWT_SECRET_KEY not found in environment, generating temporary key"
            )
            self.jwt_secret_key = secrets.token_urlsafe(32)

        # API配置
        self.api_token = os.getenv("API_TOKEN")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

        # 测试配置
        self.test_user_email = os.getenv("TEST_USER_EMAIL", "test@example.com")
        self.test_user_password_hash = os.getenv("TEST_USER_PASSWORD_HASH")

    def get_database_url(self) -> str:
        """获取数据库连接URL."""
        if self.database_url:
            return self.database_url

        if not all([self.database_user, self.database_password]):
            raise ValueError("Database credentials not properly configured")

        return f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"

    def get_redis_url(self) -> str:
        """获取Redis连接URL."""
        if self.redis_url:
            return self.redis_url

        if self.redis_password:
            return (
                f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
            )
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/0"

    def validate(self) -> dict[str, Any]:
        """验证配置完整性."""
        issues = []
        warnings = []

        # 检查必需的配置
        required_configs = [
            ("secret_key", self.secret_key),
            ("jwt_secret_key", self.jwt_secret_key),
        ]

        for name, value in required_configs:
            if not value or len(value) < 16:
                issues.append(f"{name} is missing or too short")

        # 检查数据库配置
        if not self.database_url and not all(
            [self.database_user, self.database_password]
        ):
            issues.append("Database configuration incomplete")

        # 检查安全性
        if self.secret_key == self.jwt_secret_key:
            warnings.append("SECRET_KEY and JWT_SECRET_KEY should be different")

        if self.jwt_expiration_hours > 168:  # 7 days
            warnings.append("JWT expiration time is very long")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "status": "OK" if len(issues) == 0 else "NEEDS_ATTENTION",
        }

    def get_safe_config(self) -> dict[str, Any]:
        """获取安全的配置信息（隐藏敏感信息）."""
        return {
            "database_host": self.database_host,
            "database_port": self.database_port,
            "database_name": self.database_name,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "jwt_algorithm": self.jwt_algorithm,
            "jwt_expiration_hours": self.jwt_expiration_hours,
            "test_user_email": self.test_user_email,
            "secret_configured": bool(self.secret_key),
            "jwt_secret_configured": bool(self.jwt_secret_key),
        }


# 全局安全配置实例
security_config = SecurityConfig()


def get_security_config() -> SecurityConfig:
    """获取全局安全配置实例."""
    return security_config


# 便捷函数
def validate_security_config() -> dict[str, Any]:
    """验证安全配置的便捷函数."""
    return security_config.validate()


def get_database_url() -> str:
    """获取数据库URL的便捷函数."""
    return security_config.get_database_url()


def get_redis_url() -> str:
    """获取Redis URL的便捷函数."""
    return security_config.get_redis_url()


# 导出的公共接口
__all__ = [
    "SecurityConfig",
    "get_security_config",
    "security_config",
    "validate_security_config",
    "get_database_url",
    "get_redis_url",
]
