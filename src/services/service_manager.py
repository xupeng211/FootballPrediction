"""
服务管理器 - 负责统一管理足球预测系统服务的生命周期
"""

from src.core import logger

from .base_service import BaseService


class ServiceManager:
    """服务管理器 - 负责统一管理足球预测系统服务的生命周期"""

    def __init__(self) -> None:
        self.services: dict[str, BaseService] = {}
        self.logger = logger

    def register_service(self, service: BaseService) -> None:
        """注册服务"""
        self.services[service.name] = service
        self.logger.info(f"已注册服务: {service.name}")

    async def initialize_all(self) -> bool:
        """初始化所有服务"""
        self.logger.info("正在初始化所有足球预测服务...")
        success = True

        for service in self.services.values():
            try:
                result = await service.initialize()
                if not result:
                    success = False
                    self.logger.error(f"服务初始化失败: {service.name}")
            except Exception as e:
                success = False
                self.logger.error(f"服务初始化异常: {service.name}, {e}")

        return success

    async def shutdown_all(self) -> None:
        """关闭所有服务"""
        self.logger.info("正在关闭所有服务...")

        for service in self.services.values():
            try:
                await service.shutdown()
            except Exception as e:
                self.logger.error(f"服务关闭异常: {service.name}, {e}")

    def get_service(self, name: str) -> BaseService:
        """获取服务实例"""
        return self.services.get(name)


# 全局服务管理器实例
service_manager = ServiceManager()
