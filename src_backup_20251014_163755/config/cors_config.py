"""CORS配置管理"""

import os
from typing import List


def get_cors_origins() -> List[str]:
    """获取CORS允许的源"""
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        return os.getenv("CORS_ORIGINS", "https://yourdomain.com").split(",")
    elif env == "staging":
        return ["https://staging.yourdomain.com", "http://localhost:3000"]
    else:
        return [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:8000",
        ]


def get_cors_config() -> Dict[str, Any]:
    """获取完整的CORS配置"""
    return {
        "allow_origins": get_cors_origins(),
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["*"],
        "max_age": 600,
    }
