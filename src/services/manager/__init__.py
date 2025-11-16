"""Services Manager Module
服务管理器模块.

提供服务管理和生命周期管理功能。
"""

from .manager import ServiceManager, _ensure_default_services, service_manager

__all__ = [
    "ServiceManager",
    "service_manager",
    "_ensure_default_services",
]
