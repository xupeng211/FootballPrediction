"""
服务管理器模块（重构版）

为了向后兼容，保留原始的导入路径。
建议使用：from src.services.manager import ServiceManager
"""

# 从新的模块化实现重新导出
from .manager import (
    ServiceManager,
    ServiceRegistry,
    ServiceFactory,
    ServiceHealthChecker,
    global_service_manager,
    get_service_manager,
)

# 为了向后兼容，重新导出原始的名称
service_manager = global_service_manager

__all__ = [
    "ServiceManager",
    "ServiceRegistry",
    "ServiceFactory",
    "ServiceHealthChecker",
    "global_service_manager",
    "get_service_manager",
    "service_manager",
]