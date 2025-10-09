"""
CORS 配置模块
CORS Configuration Module

管理跨域资源共享相关配置。
"""

from typing import Dict, Any, List


class CORSConfig:
    """
    CORS 配置类 / CORS Configuration Class

    管理跨域资源共享策略配置。
    """

    @staticmethod
    def get_default_origins() -> List[str]:
        """
        获取默认允许的源 / Get Default Allowed Origins

        Returns:
            List[str]: 允许的源列表 / List of allowed origins
        """
        return [
            "http://localhost:3000",  # React 开发服务器
            "http://localhost:8080",  # Vue 开发服务器
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
        ]

    @staticmethod
    def get_production_origins() -> List[str]:
        """
        获取生产环境允许的源 / Get Production Allowed Origins

        Returns:
            List[str]: 生产环境允许的源列表 / Production allowed origins list
        """
        return [
            "https://football-prediction.com",
            "https://www.football-prediction.com",
            "https://app.football-prediction.com",
            "https://admin.football-prediction.com",
        ]

    @staticmethod
    def get_cors_config() -> Dict[str, Any]:
        """
        获取 CORS 配置 / Get CORS Configuration

        Returns:
            Dict[str, Any]: CORS 配置参数 / CORS configuration parameters
        """
        return {
            "allow_origins": CORSConfig._get_environment_origins(),
            "allow_credentials": True,
            "allow_methods": [
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "OPTIONS",
                "PATCH"
            ],
            "allow_headers": [
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-API-Key",
                "X-Requested-With",
                "Origin",
                "Cache-Control",
                "Pragma"
            ],
            "expose_headers": [
                "X-Total-Count",
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "X-RateLimit-Retry-After"
            ],
            "max_age": 86400,  # 24 小时预检缓存
        }

    @staticmethod
    def _get_environment_origins() -> List[str]:
        """
        根据环境获取允许的源 / Get Allowed Origins by Environment

        Returns:
            List[str]: 环境对应的源列表 / Environment-specific origins list
        """
        import os

        env = os.getenv("ENVIRONMENT", "development").lower()

        if env == "production":
            return CORSConfig.get_production_origins()
        elif env == "staging":
            return [
                "https://staging.football-prediction.com",
                "https://staging-app.football-prediction.com",
                *CORSConfig.get_default_origins()
            ]
        else:
            # 开发环境允许所有本地源
            return [
                *CORSConfig.get_default_origins(),
                "http://localhost:*",
                "http://127.0.0.1:*"
            ]

    @staticmethod
    def get_cors_middleware_config() -> Dict[str, Any]:
        """
        获取 CORS 中间件配置 / Get CORS Middleware Configuration

        Returns:
            Dict[str, Any]: 中间件配置参数 / Middleware configuration parameters
        """
        return {
            "allow_origins": CORSConfig._get_environment_origins(),
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
            "expose_headers": [
                "X-Total-Count",
                "X-RateLimit-*"
            ],
            "max_age": 86400,
        }

    @staticmethod
    def get_vary_headers() -> List[str]:
        """
        获取 Vary 响应头配置 / Get Vary Headers Configuration

        Returns:
            List[str]: Vary 头列表 / Vary headers list
        """
        return [
            "Origin",
            "Access-Control-Request-Method",
            "Access-Control-Request-Headers"
        ]

    @staticmethod
    def get_preflight_config() -> Dict[str, Any]:
        """
        获取预检请求配置 / Get Preflight Request Configuration

        Returns:
            Dict[str, Any]: 预检请求配置 / Preflight request configuration
        """
        return {
            "max_age": 86400,  # 24 小时
            "cache_headers": True,
            "handle_options_requests": True,
        }