"""

"""




    """服务管理器 - 负责统一管理所有业务服务的生命周期和依赖关系"""


        """注册服务 - 将服务加入管理器，支持后续统一初始化和管理"""



        """注销服务"""

        """获取服务实例 - 提供类型安全的服务访问接口"""

        """获取所有服务列表"""

        """获取已初始化的服务列表"""

        """服务字典属性 - 兼容测试代码"""

        """获取服务数量"""

        """设置服务启动顺序"""

        """初始化所有服务 - 按注册顺序依次初始化，任一失败则整体失败"""




        """初始化单个服务"""



        """关闭所有服务 - 确保资源清理，即使某个服务关闭失败也继续处理其他服务"""



        """重启单个服务"""


        """检查所有服务的健康状态"""

        """获取服务信息"""


        """获取管理器信息"""


服务管理器核心实现
负责管理所有业务服务的生命周期和依赖关系。
class ServiceManager:
    def __init__(self, name: str = "default") -> None:
        self._services: Dict[str, BaseService] = {}
        self._initialized_services: set = set()
        self._startup_order: List[str] = []
        self.logger = logger
        self.name = name
        self._created_at = datetime.now()
    def register_service(self, name: str, service: BaseService) -> None:
        if name in self._services:
            existing = self._services[name]
            if existing is service or existing.__class__ is service.__class__:
                self.logger.debug(f"服务已存在，跳过重复注册: {name}")
                return
            self.logger.warning(
                "替换已注册服务 %s (旧: %s, 新: %s)",
                name,
                existing.__class__.__name__,
                service.__class__.__name__,
            )
        self._services[name] = service
        self.logger.info(f"已注册服务: {name}")
    def unregister_service(self, name: str) -> bool:
        if name in self._services:
            service = self._services[name]
            if name in self._initialized_services:
                self._initialized_services.remove(name)
            del self._services[name]
            self.logger.info(f"已注销服务: {name}")
            return True
        return False
    def get_service(self, name: str) -> Optional[BaseService]:
        return self._services.get(name)
    def list_services(self) -> Dict[str, BaseService]:
        return self._services.copy()
    def get_initialized_services(self) -> List[str]:
        return list(self._initialized_services)
    @property
    def services(self) -> Dict[str, BaseService]:
        return self._services
    @property
    def service_count(self) -> int:
        return len(self._services)
    def set_startup_order(self, order: List[str]) -> None:
        # 验证所有服务都已注册
        for name in order:
            if name not in self._services:
                raise ValueError(f"服务未注册: {name}")
        self._startup_order = order
    async def initialize_all(self) -> bool:
        self.logger.info("正在初始化所有服务...")
        # 使用启动顺序，如果没有设置则按注册顺序
        services_to_init = []
        if self._startup_order:
            for name in self._startup_order:
                if name in self._services:
                    services_to_init.append(self._services[name])
        else:
            services_to_init = list(self._services.values())
        success = True
        for service in services_to_init:
            try:
                # 每个服务独立初始化，失败不影响其他服务的尝试
                result = await service.initialize()
                if result:
                    self._initialized_services.add(service.name)
                    self.logger.info(f"服务初始化成功: {service.name}")
                else:
                    success = False
                    self.logger.error(f"服务初始化失败: {service.name}")
            except Exception as e:
                # 捕获异常避免整个初始化流程中断
                success = False
                self.logger.error(f"服务初始化异常: {service.name}, {e}")
        return success
    async def initialize_service(self, name: str) -> bool:
        if name not in self._services:
            self.logger.error(f"服务未注册: {name}")
            return False
        if name in self._initialized_services:
            self.logger.debug(f"服务已初始化: {name}")
            return True
        service = self._services[name]
        try:
            result = await service.initialize()
            if result:
                self._initialized_services.add(name)
                self.logger.info(f"服务初始化成功: {name}")
            else:
                self.logger.error(f"服务初始化失败: {name}")
            return result
        except Exception as e:
            self.logger.error(f"服务初始化异常: {name}, {e}")
            return False
    async def shutdown_all(self) -> None:
        self.logger.info("正在关闭所有服务...")
        # 按初始化的逆序关闭服务
        services_to_shutdown = []
        for name in reversed(list(self._initialized_services)):
            if name in self._services:
                services_to_shutdown.append(self._services[name])
        for service in services_to_shutdown:
            try:
                await service.shutdown()
                self._initialized_services.remove(service.name)
                self.logger.info(f"服务已关闭: {service.name}")
            except Exception as e:
                # 关闭失败不应阻止其他服务的正常关闭
                self.logger.error(f"服务关闭异常: {service.name}, {e}")
    async def restart_service(self, name: str) -> bool:
        if name not in self._services:
            self.logger.error(f"服务未注册: {name}")
            return False
        service = self._services[name]
        try:
            await service.shutdown()
            result = await service.initialize()
            if result:
                self.logger.info(f"服务重启成功: {name}")
            else:
                self.logger.error(f"服务重启失败: {name}")
            return result
        except Exception as e:
            self.logger.error(f"服务重启异常: {name}, {e}")
            return False
    async def health_check(self) -> Dict[str, bool]:
        health_status = {}
        for name, service in self._services.items():
            try:
                # 如果服务有health_check方法，调用它
                if hasattr(service, 'health_check') and asyncio.iscoroutinefunction(service.health_check):
                    health_status[name] = await service.health_check()
                elif hasattr(service, 'health_check'):
                    health_status[name] = service.health_check()
                else:
                    # 服务没有health_check方法，假设健康
                    health_status[name] = True
            except Exception as e:
                self.logger.error(f"健康检查异常: {name}, {e}")
                health_status[name] = False
        return health_status
    def get_service_info(self, name: str) -> Optional[Dict]:
        if name not in self._services:
            return None
        service = self._services[name]
        return {
            "name": service.name,
            "class": service.__class__.__name__,
            "initialized": name in self._initialized_services,
            "dependencies": getattr(service, 'dependencies', []),
        }
    def get_manager_info(self) -> Dict:
        return {
            "name": self.name,
            "service_count": len(self._services),
            "initialized_count": len(self._initialized_services),
            "created_at": self._created_at.isoformat(),
            "created_at": self._created_at.isoformat(),)
        }