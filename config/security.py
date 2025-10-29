"""
安全配置文件
Security Configuration

集中管理所有安全相关的配置和设置。
"""

import os
from typing import Dict, List, Optional


class SecuritySettings:
    """安全设置"""

    def __init__(self):
        # 基础设置
        self.enabled = True
        self.debug = os.getenv("DEBUG", "false").lower() == "true"

        # JWT设置
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-here-please-change-this")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.jwt_refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

        # 速率限制
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        self.rate_limit_burst = int(os.getenv("RATE_LIMIT_BURST", "10"))
        self.rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

        # CORS设置
        self.cors_origins = (
            os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
        )
        self.cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
        self.cors_allow_methods = os.getenv(
            "CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS"
        ).split(",")
        self.cors_allow_headers = os.getenv("CORS_ALLOW_HEADERS", "*").split(",")

        # HTTPS/TLS设置
        self.force_https = os.getenv("FORCE_HTTPS", "false").lower() == "true"
        self.ssl_cert_path = os.getenv("SSL_CERT_PATH")
        self.ssl_key_path = os.getenv("SSL_KEY_PATH")

        # 安全头
        self.secure_headers_enabled = os.getenv("SECURE_HEADERS_ENABLED", "true").lower() == "true"
        self.x_frame_options = os.getenv("X_FRAME_OPTIONS", "DENY")
        self.x_content_type_options = os.getenv("X_CONTENT_TYPE_OPTIONS", "nosniff")
        self.x_xss_protection = os.getenv("X_XSS_PROTECTION", "1; mode=block")
        self.strict_transport_security = os.getenv(
            "STRICT_TRANSPORT_SECURITY", "max-age=31536000; includeSubDomains"
        )

        # 内容安全策略
        self.csp_enabled = os.getenv("CSP_ENABLED", "true").lower() == "true"
        self.csp_default_src = os.getenv("CSP_DEFAULT_SRC", "'self'")
        self.csp_script_src = os.getenv("CSP_SCRIPT_SRC", "'self' 'unsafe-inline'")
        self.csp_style_src = os.getenv("CSP_STYLE_SRC", "'self' 'unsafe-inline'")

        # API安全
        self.api_key_header = os.getenv("API_KEY_HEADER", "X-API-Key")
        self.api_key_length = int(os.getenv("API_KEY_LENGTH", "32"))
        self.api_token_expire_hours = int(os.getenv("API_TOKEN_EXPIRE_HOURS", "24"))

        # 密码策略
        self.password_min_length = int(os.getenv("PASSWORD_MIN_LENGTH", "12"))
        self.password_require_uppercase = (
            os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
        )
        self.password_require_lowercase = (
            os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower() == "true"
        )
        self.password_require_numbers = (
            os.getenv("PASSWORD_REQUIRE_NUMBERS", "true").lower() == "true"
        )
        self.password_require_symbols = (
            os.getenv("PASSWORD_REQUIRE_SYMBOLS", "true").lower() == "true"
        )

        # 会话安全
        self.session_timeout_minutes = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
        self.session_secure_cookie = os.getenv("SESSION_SECURE_COOKIE", "true").lower() == "true"
        self.session_http_only_cookie = (
            os.getenv("SESSION_HTTP_ONLY_COOKIE", "true").lower() == "true"
        )
        self.session_samesite_cookie = os.getenv("SESSION_SAMESITE_COOKIE", "Strict")

        # 审计日志
        self.audit_log_enabled = os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"
        self.audit_log_level = os.getenv("AUDIT_LOG_LEVEL", "INFO").upper()
        self.audit_log_file = os.getenv("AUDIT_LOG_FILE", "/var/log/app/audit.log")

        # 数据保护
        self.encrypt_data_at_rest = os.getenv("ENCRYPT_DATA_AT_REST", "true").lower() == "true"
        self.encrypt_data_in_transit = (
            os.getenv("ENCRYPT_DATA_IN_TRANSIT", "true").lower() == "true"
        )

        # 监控和检测
        self.enable_intrusion_detection = (
            os.getenv("ENABLE_INTRUSION_DETECTION", "false").lower() == "true"
        )
        self.enable_anomaly_detection = (
            os.getenv("ENABLE_ANOMALY_DETECTION", "false").lower() == "true"
        )


# 安全配置实例
security_settings = SecuritySettings()


def get_security_config() -> SecuritySettings:
    """获取安全配置"""
    return security_settings


def is_production() -> bool:
    """判断是否为生产环境"""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def is_development() -> bool:
    """判断是否为开发环境"""
    return os.getenv("ENVIRONMENT", "development").lower() == "development"


def get_cors_origins() -> List[str]:
    """获取CORS允许的源"""
    if is_production():
        return security_settings.cors_origins
    return ["*"]  # 开发环境允许所有源


def get_rate_limit_config() -> Dict[str, int]:
    """获取速率限制配置"""
    return {
        "requests_per_minute": security_settings.rate_limit_per_minute,
        "burst_size": security_settings.rate_limit_burst,
    }


def get_password_policy() -> Dict[str, any]:
    """获取密码策略"""
    return {
        "min_length": security_settings.password_min_length,
        "require_uppercase": security_settings.password_require_uppercase,
        "require_lowercase": security_settings.password_require_lowercase,
        "require_numbers": security_settings.password_require_numbers,
        "require_symbols": security_settings.password_require_symbols,
    }


def get_session_config() -> Dict[str, any]:
    """获取会话配置"""
    return {
        "max_age": security_settings.session_timeout_minutes * 60,
        "secure": security_settings.session_secure_cookie,
        "httponly": security_settings.session_http_only_cookie,
        "samesite": security_settings.session_samesite_cookie,
    }


def get_security_headers() -> Dict[str, str]:
    """获取安全头"""
    headers = {}

    if security_settings.secure_headers_enabled:
        headers["X-Frame-Options"] = security_settings.x_frame_options
        headers["X-Content-Type-Options"] = security_settings.x_content_type_options
        headers["X-XSS-Protection"] = security_settings.x_xss_protection

    if security_settings.force_https:
        headers["Strict-Transport-Security"] = security_settings.strict_transport_security

    return headers


def get_csp_policy() -> str:
    """获取内容安全策略"""
    if not security_settings.csp_enabled:
        return ""

    directives = [
        f"default-src {security_settings.csp_default_src}",
        f"script-src {security_settings.csp_script_src}",
        f"style-src {security_settings.csp_style_src}",
        "img-src 'self' data: https:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]

    return "; ".join(directives)


# 环境特定的安全配置
class EnvironmentSecurityConfig:
    """环境特定的安全配置"""

    @staticmethod
    def get_development_config() -> Dict[str, any]:
        """开发环境安全配置"""
        return {
            "debug": True,
            "rate_limit_enabled": False,  # 开发环境关闭速率限制
            "audit_log_enabled": True,
            "secure_headers_enabled": False,  # 开发环境关闭安全头便于调试
            "csp_enabled": False,  # 开发环境关闭CSP便于调试
            "cors_origins": ["*"],
            "cors_allow_credentials": True,
        }

    @staticmethod
    def get_staging_config() -> Dict[str, any]:
        """测试环境安全配置"""
        return {
            "debug": True,
            "rate_limit_enabled": True,
            "audit_log_enabled": True,
            "secure_headers_enabled": True,
            "csp_enabled": True,
            "cors_origins": ["http://localhost:3000", "http://localhost:8080"],
            "cors_allow_credentials": True,
        }

    @staticmethod
    def get_production_config() -> Dict[str, any]:
        """生产环境安全配置"""
        return {
            "debug": False,
            "rate_limit_enabled": True,
            "audit_log_enabled": True,
            "secure_headers_enabled": True,
            "csp_enabled": True,
            "force_https": True,
            "cors_origins": [],  # 生产环境需要明确配置
            "cors_allow_credentials": False,
        }


def get_environment_security_config() -> Dict[str, any]:
    """获取当前环境的安全配置"""
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        return EnvironmentSecurityConfig.get_production_config()
    elif environment == "staging":
        return EnvironmentSecurityConfig.get_staging_config()
    else:
        return EnvironmentSecurityConfig.get_development_config()


# 安全检查函数
def validate_security_config() -> List[str]:
    """验证安全配置"""
    issues = []

    # 检查必需的配置
    if (
        not security_settings.jwt_secret_key
        or security_settings.jwt_secret_key == "your-secret-key-here"
    ):
        issues.append("JWT_SECRET_KEY must be set to a secure value")

    # 检查密码策略
    if security_settings.password_min_length < 8:
        issues.append("Password minimum length should be at least 8 characters")

    # 检查生产环境特定配置
    if is_production():
        if not security_settings.force_https:
            issues.append("HTTPS should be enforced in production")

        if security_settings.cors_origins == ["*"]:
            issues.append("CORS should not allow all origins in production")

        if not security_settings.session_secure_cookie:
            issues.append("Session cookies should be secure in production")

    return issues


def run_security_audit() -> Dict[str, any]:
    """运行安全审计"""
    audit_result = {
        "timestamp": "2025-10-22T18:50:00Z",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "issues": validate_security_config(),
        "config": {
            "rate_limit_enabled": security_settings.rate_limit_enabled,
            "secure_headers_enabled": security_settings.secure_headers_enabled,
            "csp_enabled": security_settings.csp_enabled,
            "audit_log_enabled": security_settings.audit_log_enabled,
            "force_https": security_settings.force_https,
        },
        "password_policy": get_password_policy(),
        "session_config": get_session_config(),
    }

    return audit_result
