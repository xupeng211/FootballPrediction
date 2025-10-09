"""
OpenAPI 配置模块
OpenAPI Configuration Module

提供 FastAPI 应用的 OpenAPI 配置和文档增强功能。
"""

from .auth_config import AuthConfig
from .rate_limit_config import RateLimitConfig
from .cors_config import CORSConfig
from .docs_config import DocsConfig
from .config_manager import OpenAPIConfig

__all__ = [
    'AuthConfig',
    'RateLimitConfig',
    'CORSConfig',
    'DocsConfig',
    'OpenAPIConfig'
]