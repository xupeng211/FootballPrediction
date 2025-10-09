"""




"""



    """设置 OpenAPI 配置的便捷函数"""

from src.config.openapi import OpenAPIConfig
from src.config.openapi_config import OpenAPIConfig  # 仍然有效

OpenAPI 配置 - 向后兼容性导入
OpenAPI Configuration - Backward Compatibility Import
此文件已拆分为模块化结构,为了保持向后兼容性,这里重新导出主要类.
This file has been split into a modular structure, main classes are re-exported here for backward compatibility.
新的模块化结构 / New modular structure:
- openapi/auth_config.py: 认证配置
- openapi/rate_limit_config.py: 限流配置
- openapi/cors_config.py: CORS配置
- openapi/docs_config.py: 文档配置
- openapi/config_manager.py: 配置管理器
使用新的模块化结构 / Use the new modular structure:
或者使用原有的导入方式 / Or use the original import style:
# 导入拆分后的模块以保持向后兼容性
    OpenAPIConfig,
    AuthConfig,
    RateLimitConfig,
    CORSConfig,
    DocsConfig
)
# 重新导出主要类
__all__ = [
    'OpenAPIConfig',
    'AuthConfig',
    'RateLimitConfig',
    'CORSConfig',
    'DocsConfig'
]
# 导出配置函数
def setup_openapi(app):
    OpenAPIConfig.configure_openapi(app)