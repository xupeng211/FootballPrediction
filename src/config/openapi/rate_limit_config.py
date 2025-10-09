"""
限流配置模块
Rate Limit Configuration Module

管理 API 限流相关配置。
"""



class RateLimitConfig:
    """
    限流配置类 / Rate Limit Configuration Class

    管理 API 请求频率限制配置。
    """

    @staticmethod
    def get_default_limits() -> Dict[str, int]:
        """
        获取默认限流配置 / Get Default Rate Limit Configuration

        Returns:
            Dict[str, int]: 默认限流参数 / Default rate limit parameters
        """
        return {
            "requests_per_minute": 100,
            "requests_per_hour": 5000,
            "requests_per_day": 50000,
            "burst_size": 20,
            "retry_after": 60
        }

    @staticmethod
    def get_endpoint_specific_limits() -> Dict[str, Dict[str, int]]:
        """
        获取特定端点的限流配置 / Get Endpoint-specific Rate Limits

        Returns:
            Dict[str, Dict[str, int]]: 端点限流配置 / Endpoint rate limit configuration
        """
        return {
            # 预测相关端点 - 计算密集型
            "/predictions/": {
                "requests_per_minute": 30,
                "requests_per_hour": 1000,
                "requests_per_day": 10000,
                "burst_size": 5
            },
            "/predictions/match/{match_id}": {
                "requests_per_minute": 60,
                "requests_per_hour": 2000,
                "requests_per_day": 20000,
                "burst_size": 10
            },
            "/predictions/batch": {
                "requests_per_minute": 10,
                "requests_per_hour": 200,
                "requests_per_day": 2000,
                "burst_size": 2
            },

            # 数据查询端点 - 中等负载
            "/data/": {
                "requests_per_minute": 200,
                "requests_per_hour": 10000,
                "requests_per_day": 100000,
                "burst_size": 50
            },
            "/data/matches": {
                "requests_per_minute": 300,
                "requests_per_hour": 15000,
                "requests_per_day": 150000,
                "burst_size": 60
            },

            # 特征工程端点 - 较低负载
            "/features/": {
                "requests_per_minute": 100,
                "requests_per_hour": 5000,
                "requests_per_day": 50000,
                "burst_size": 20
            },

            # 健康检查 - 高频访问
            "/health": {
                "requests_per_minute": 1000,
                "requests_per_hour": 60000,
                "requests_per_day": 1000000,
                "burst_size": 100
            },

            # 文档端点 - 无限制
            "/docs": {
                "unlimited": True
            },
            "/redoc": {
                "unlimited": True
            },
            "/openapi.json": {
                "unlimited": True
            }
        }

    @staticmethod
    def get_rate_limit_headers() -> Dict[str, str]:
        """
        获取限流响应头配置 / Get Rate Limit Response Headers Configuration

        Returns:
            Dict[str, str]: 响应头配置 / Response headers configuration
        """
        return {
            "X-RateLimit-Limit": "Total request limit per time window",
            "X-RateLimit-Remaining": "Remaining requests in current window",
            "X-RateLimit-Reset": "Time when rate limit resets (Unix timestamp)",
            "X-RateLimit-Retry-After": "Seconds to wait before making another request",
            "X-RateLimit-Burst": "Burst size allowed"
        }

    @staticmethod
    def get_rate_limit_strategies() -> Dict[str, Any]:
        """
        获取限流策略配置 / Get Rate Limiting Strategies Configuration

        Returns:
            Dict[str, Any]: 限流策略配置 / Rate limiting strategies configuration
        """
        return {

            "strategy": "sliding_window",  # fixed_window, sliding_window, token_bucket
            "key_generator": "ip_address",  # ip_address, user_id, api_key, custom
            "storage": "redis",  # memory, redis, database
            "error_response": {
                "status_code": 429,
                "message": "Rate limit exceeded",
                "retry_after_header": True
            },
            "whitelist": [
                "127.0.0.1",  # 本地开发
                "10.0.0.0/8",  # 内网
                "192.168.0.0/16"  # 内网
            ],
            "blacklist": [
                # 可以添加恶意 IP
            ]
        }