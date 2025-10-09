"""
服务管理器模块

提供模块化的服务管理功能：
- 服务注册和发现
- 服务生命周期管理
- 依赖注入支持
- 健康检查
"""

from .service_manager import ServiceManager
from .service_registry import ServiceRegistry
from .service_factory import ServiceFactory
from .health_checker import ServiceHealthChecker
from .global_manager import global_service_manager, get_service_manager, get_service, register_service

__all__ = [
    "ServiceManager",
    "ServiceRegistry",
    "ServiceFactory",
    "ServiceHealthChecker",
    "global_service_manager",
    "get_service_manager",
    "get_service",
    "register_service",
]