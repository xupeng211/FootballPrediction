"""
        import os

            from fastapi.openapi.utils import get_openapi
        from fastapi.middleware.cors import CORSMiddleware

配置管理器模块
Configuration Manager Module

统一管理 OpenAPI 配置的主类。
"""




class OpenAPIConfig:
    """
    OpenAPI 配置管理类 / OpenAPI Configuration Management Class

    统一管理所有 OpenAPI 相关配置。
    """

    @staticmethod
    def configure_openapi(app: FastAPI) -> None:
        """
        配置 FastAPI 应用的 OpenAPI / Configure OpenAPI for FastAPI Application

        Args:
            app (FastAPI): FastAPI 应用实例 / FastAPI application instance
        """
        # 获取配置
        info = DocsConfig.get_app_info()
        servers = DocsConfig.get_servers()
        tags = DocsConfig.get_tags()
        security_schemes = AuthConfig.get_security_schemes()
        examples = DocsConfig.get_examples()
        schemas = DocsConfig.get_schemas()

        # 自定义 OpenAPI
        def custom_openapi():
            if app.openapi_schema:
                return app.openapi_schema

            # 先获取基础 schema

            openapi_schema = get_openapi(
                title=info["title"],
                version=info["version"],
                description=info["description"],
                routes=app.routes,
                servers=servers,
                tags=tags,
            )

            # 添加 logo
            openapi_schema["info"]["x-logo"] = {
                "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
            }

            # 更新联系人和许可证信息
            openapi_schema["info"]["contact"] = info["contact"]
            openapi_schema["info"]["license"] = info["license_info"]
            openapi_schema["info"]["termsOfService"] = info["terms_of_service"]

            # 添加示例
            if "components" not in openapi_schema:
                openapi_schema["components"] = {}
            openapi_schema["components"]["examples"] = examples

            # 添加请求/响应模型
            if "schemas" not in openapi_schema["components"]:
                openapi_schema["components"]["schemas"] = {}
            openapi_schema["components"]["schemas"].update(schemas)

            # 添加安全配置
            openapi_schema["components"]["securitySchemes"] = security_schemes

            # 添加认证流程说明
            openapi_schema["components"]["authenticationFlows"] = AuthConfig.get_authentication_flows()

            # 添加扩展信息
            openapi_schema["x-tag-groups"] = [
                {"name": "核心业务", "tags": ["预测", "数据", "特征"]},
                {"name": "系统管理", "tags": ["健康检查", "监控", "模型"]},
            ]

            app.openapi_schema = openapi_schema
            return openapi_schema

        app.openapi = custom_openapi

    @staticmethod
    def get_complete_config() -> Dict[str, Any]:
        """
        获取完整的 OpenAPI 配置 / Get Complete OpenAPI Configuration

        Returns:
            Dict[str, Any]: 完整配置信息 / Complete configuration information
        """
        return {
            "app_info": DocsConfig.get_app_info(),
            "servers": DocsConfig.get_servers(),
            "tags": DocsConfig.get_tags(),
            "security_schemes": AuthConfig.get_security_schemes(),
            "authentication_flows": AuthConfig.get_authentication_flows(),
            "examples": DocsConfig.get_examples(),
            "schemas": DocsConfig.get_schemas(),
            "rate_limits": {
                "default": RateLimitConfig.get_default_limits(),
                "endpoint_specific": RateLimitConfig.get_endpoint_specific_limits(),
                "strategies": RateLimitConfig.get_rate_limit_strategies()
            },
            "cors": CORSConfig.get_cors_config(),
        }

    @staticmethod
    def get_environment_config() -> Dict[str, Any]:
        """
        根据环境获取配置 / Get Configuration by Environment

        Returns:
            Dict[str, Any]: 环境特定配置 / Environment-specific configuration
        """

        env = os.getenv("ENVIRONMENT", "development").lower()

        base_config = OpenAPIConfig.get_complete_config()

        if env == "production":
            # 生产环境配置调整
            base_config["cors"] = CORSConfig.get_cors_config()
            base_config["rate_limits"]["default"] = {
                **base_config["rate_limits"]["default"],
                "requests_per_minute": 50  # 生产环境更严格的限制
            }
        elif env == "staging":
            # 测试环境配置调整
            base_config["cors"] = CORSConfig.get_cors_config()
            base_config["rate_limits"]["default"] = {
                **base_config["rate_limits"]["default"],
                "requests_per_minute": 200  # 测试环境较宽松的限制
            }
        else:
            # 开发环境保持默认配置
            pass

        return base_config

    @staticmethod
    def setup_middleware(app: FastAPI) -> None:
        """
        设置中间件 / Setup Middleware

        Args:
            app (FastAPI): FastAPI 应用实例 / FastAPI application instance
        """
        # 设置 CORS 中间件

        cors_config = CORSConfig.get_cors_middleware_config()
        app.add_middleware(
            CORSMiddleware,
            **cors_config
        )

    @staticmethod
    def validate_config() -> bool:
        """
        验证配置有效性 / Validate Configuration

        Returns:
            bool: 配置是否有效 / Whether configuration is valid
        """
        try:
            # 验证必需的配置项
            info = DocsConfig.get_app_info()
            required_fields = ["title", "version", "description"]

            for field in required_fields:



                if field not in info or not info[field]:
                    return False

            # 验证服务器配置
            servers = DocsConfig.get_servers()
            if not servers or not isinstance(servers, list):
                return False

            # 验证标签配置
            tags = DocsConfig.get_tags()
            if not tags or not isinstance(tags, list):
                return False

            # 验证安全配置
            security_schemes = AuthConfig.get_security_schemes()
            if not security_schemes or not isinstance(security_schemes, dict):
                return False

            return True

        except Exception:
            return False