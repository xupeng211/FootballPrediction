"""

"""





    """获取全局服务管理器"""


    """获取全局服务注册表"""


    """获取全局服务工厂"""


    """获取全局健康检查器"""


    """初始化默认服务"""





    """注册默认服务工厂"""



    """注册默认工厂"""




    """获取服务管理器的便捷函数 - 向后兼容"""


    """获取服务的便捷函数"""


    """注册服务的便捷函数"""


    """注销服务的便捷函数"""


    """初始化所有服务的便捷函数"""


    """关闭所有服务的便捷函数"""


    """获取全局服务管理器信息"""


全局服务管理器
提供全局默认的服务管理器实例。
# 全局服务管理器实例
_global_service_manager: Optional[ServiceManager] = None
_global_registry: Optional[ServiceRegistry] = None
_global_factory: Optional[ServiceFactory] = None
_global_health_checker: Optional[ServiceHealthChecker] = None
def get_global_manager() -> ServiceManager:
    global _global_service_manager
    if _global_service_manager is None:
        _global_service_manager = ServiceManager("global")
        _initialize_default_services(_global_service_manager)
    return _global_service_manager
def get_global_registry() -> ServiceRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = ServiceRegistry()
        _register_default_factories(_global_registry)
    return _global_registry
def get_global_factory() -> ServiceFactory:
    global _global_factory
    if _global_factory is None:
        _global_factory = ServiceFactory()
        _register_default_factories_factory(_global_factory)
    return _global_factory
def get_global_health_checker() -> ServiceHealthChecker:
    global _global_health_checker
    if _global_health_checker is None:
        _global_health_checker = ServiceHealthChecker()
    return _global_health_checker
def _initialize_default_services(manager: ServiceManager) -> None:
    settings = get_settings()
    enabled_services = getattr(settings, "enabled_services", []) or []
    # 默认服务工厂映射
    service_factories = {
        "DataProcessingService": DataProcessingService,
        "UserProfileService": UserProfileService,
    }
    for service_name in enabled_services:
        factory = service_factories.get(service_name)
        if not factory:
            logger.warning("未识别的服务名称，跳过注册: %s", service_name)
            continue
        if service_name not in manager.services:
            service = factory()
            manager.register_service(service_name, service)
            logger.info(f"已注册默认服务: {service_name}")
def _register_default_factories(registry: ServiceRegistry) -> None:
    registry.register_factory("DataProcessingService", DataProcessingService)
    registry.register_factory("UserProfileService", UserProfileService)
    # 设置依赖关系
    registry.set_dependencies("DataProcessingService", [])
    registry.set_dependencies("UserProfileService", ["DataProcessingService"])
def _register_default_factories_factory(factory: ServiceFactory) -> None:
    factory.register_class("DataProcessingService", DataProcessingService)
    factory.register_class("UserProfileService", UserProfileService)
# 向后兼容的全局实例
service_manager = get_global_manager()
global_service_manager = service_manager
def get_service_manager() -> ServiceManager:
    return get_global_manager()
def get_service(service_name: str) -> Optional[BaseService]:
    manager = get_global_manager()
    return manager.get_service(service_name)
def register_service(name: str, service: BaseService) -> None:
    manager = get_global_manager()
    manager.register_service(name, service)
def unregister_service(name: str) -> bool:
    manager = get_global_manager()
    return manager.unregister_service(name)
async def initialize_all_services() -> bool:
    manager = get_global_manager()
    return await manager.initialize_all()
async def shutdown_all_services() -> None:
    manager = get_global_manager()
    await manager.shutdown_all()
def get_global_service_info() -> Dict:
    manager = get_global_manager()
    registry = get_global_registry()
    factory = get_global_factory()
    health_checker = get_global_health_checker()
    return {
        "manager": manager.get_manager_info(),
        "registry": {
            "registered_services": registry.get_all_services(),
            "dependencies": registry._dependencies, Optional
            "registered_services": registry.get_all_services(),)
        },
        "factory": {
            "registered_builders": factory.get_registered_services(),
        },
        "health_checker": health_checker.get_summary(),
    }