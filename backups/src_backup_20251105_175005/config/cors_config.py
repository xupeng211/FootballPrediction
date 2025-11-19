"""CORS配置管理."""

import os


def get_cors_origins() -> list[str]:
    """获取CORS允许的源."""
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        return os.getenv("CORS_ORIGINS", "https://yourdomain.com").split(",")
    elif env == "staging":
        return [
            "https://staging.yourdomain.com",
            "http://localhost:3000",  # TODO: 将魔法数字 3000 提取为常量
        ]  # TODO: 将魔法数字 3000 提取为常量
    else:
        return [
            "http://localhost:3000",  # TODO: 将魔法数字 3000 提取为常量
            "http://localhost:8080",  # TODO: 将魔法数字 8080 提取为常量
            "http://localhost:8000",  # TODO: 将魔法数字 8000 提取为常量
        ]


def get_cors_config() -> dict:
    """获取完整的CORS配置."""
    return {
        "allow_origins": get_cors_origins(),
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["*"],
        "max_age": 600,  # TODO: 将魔法数字 600 提取为常量
    }
