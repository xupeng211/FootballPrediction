from typing import Optional

import os

"""CORS配置管理"""

# 常量定义
DEV_FRONTEND_PORT = 3000
DEV_ADMIN_PORT = 8080
DEV_API_PORT = 8000
CORS_MAX_AGE = 600


def get_cors_origins() -> list[str]:
    """获取CORS允许的源."""
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return os.getenv("CORS_ORIGINS", "https://yourdomain.com").split(",")
    elif env == "staging":
        return [
            "https://staging.yourdomain.com",
            f"http://localhost:{DEV_FRONTEND_PORT}",
        ]
    else:
        return [
            f"http://localhost:{DEV_FRONTEND_PORT}",
            f"http://localhost:{DEV_ADMIN_PORT}",
            f"http://localhost:{DEV_API_PORT}",
        ]


def get_cors_config() -> dict:
    """获取完整的CORS配置."""
    return {
        "allow_origins": get_cors_origins(),
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["*"],
        "max_age": CORS_MAX_AGE,
    }
