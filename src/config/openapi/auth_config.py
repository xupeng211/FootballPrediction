"""
认证配置模块
Authentication Configuration Module

管理 API 认证相关的配置。
"""



class AuthConfig:
    """
    认证配置类 / Authentication Configuration Class

    管理 API 密钥和 JWT 认证配置。
    """

    @staticmethod
    def get_security_schemes() -> Dict[str, Any]:
        """
        获取安全配置 / Get Security Configuration

        Returns:
            Dict[str, Any]: 安全方案配置 / Security schemes configuration
        """
        return {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API密钥认证，请在请求头中携带 X-API-Key",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Token 认证，格式：Bearer <token>",
            },
        }

    @staticmethod
    def get_authentication_flows() -> Dict[str, Any]:
        """
        获取认证流程说明 / Get Authentication Flow Descriptions

        Returns:
            Dict[str, Any]: 认证流程配置 / Authentication flow configuration
        """
        return {
            "ApiKeyAuth": {
                "type": "apiKey",
                "description": "API Key 认证流程：\n1. 联系管理员获取 API Key\n2. 在请求头中添加 X-API-Key: your-api-key\n3. 正常调用 API",
                "example": "curl -H 'X-API-Key: your-api-key' https://api.football-prediction.com/predictions/match_123",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Bearer Token 认证流程：\n1. 使用用户名密码登录获取 JWT\n2. 在请求头中添加 Authorization: Bearer <jwt-token>\n3. Token 有效期为 24 小时",
                "example": "curl -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' https://api.football-prediction.com/predictions/match_123",
            },
        }

    @staticmethod
    def get_auth_requirements() -> Dict[str, list]:
        """
        获取认证要求 / Get Authentication Requirements

        Returns:
            Dict[str, list]: 各端点的认证要求 / Authentication requirements for endpoints
        """
        return {
            # 生产环境需要认证的端点
            "protected_endpoints": [
                "/predictions/",
                "/features/",
                "/models/",
                "/admin/"
            ],
            # 开发环境可选认证的端点
            "optional_auth": [
                "/data/",
                "/statistics/"
            ],
            # 公开端点
            "public_endpoints": [
                "/health",
                "/docs",
                "/openapi.json",
                "/redoc"
            ]
        }

    @staticmethod
    def get_rate_limit_rules() -> Dict[str, Any]:
        """
        获取基于认证的限流规则 / Get Authentication-based Rate Limiting Rules

        Returns:
            Dict[str, Any]: 限流规则配置 / Rate limiting rules configuration
        """
        return {

            "anonymous": {
                "requests_per_minute": 60,
                "requests_per_hour": 1000,
                "burst_size": 10
            },
            "api_key": {
                "requests_per_minute": 300,
                "requests_per_hour": 10000,
                "burst_size": 50
            },
            "jwt_token": {
                "requests_per_minute": 600,
                "requests_per_hour": 20000,
                "burst_size": 100
            },
            "admin": {
                "requests_per_minute": 1200,
                "requests_per_hour": 50000,
                "burst_size": 200
            }
        }