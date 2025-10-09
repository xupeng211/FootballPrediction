"""


"""





from .manager import (
from .manager import (

足球预测系统服务管理器模块
已重构为模块化架构,原始功能现在通过以下模块提供:
- service_manager: 核心服务管理器
- service_registry: 服务注册表
- service_factory: 服务工厂
- health_checker: 健康检查器
- global_manager: 全局管理器
为了向后兼容,保留原始的导入接口.
建议使用:from src.services.manager import ServiceManager
# 为了向后兼容,从新的模块化实现重新导出
    ServiceManager,
    service_manager as _service_manager,
    get_service_manager,
)
# 保持原有的全局实例以保持向后兼容
service_manager = _service_manager
# 重新导出其他兼容性接口
    get_service,
    register_service,
    unregister_service,
    initialize_all_services,
    shutdown_all_services,
    get_global_service_info,
)
__all__ = [
    "ServiceManager",
    "service_manager",
    "get_service_manager",
    "get_service",
    "register_service",
    "unregister_service",
    "initialize_all_services",
    "shutdown_all_services",
    "get_global_service_info",
]