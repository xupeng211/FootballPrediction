"""
足球预测系统服务管理器模块

统一管理所有业务服务的生命周期和依赖关系。
"""

from typing import Dict, Optional

from src.core import logger

from .base import BaseService
from .content_analysis import ContentAnalysisService
from .data_processing import DataProcessingService
from .user_profile import UserProfileService


class ServiceManager:
    """服务管理器 - 负责统一管理所有业务服务的生命周期和依赖关系"""

    def __init__(self) -> None:
        self.services: Dict[str, BaseService] = {}
        self.logger = logger

    def register_service(self, service: BaseService) -> None:
        """注册服务 - 将服务加入管理器，支持后续统一初始化和管理"""
        self.services[service.name] = service
        self.logger.info(f"已注册服务: {service.name}")

    async def initialize_all(self) -> bool:
        """初始化所有服务 - 按注册顺序依次初始化，任一失败则整体失败"""
        self.logger.info("正在初始化所有服务...")
        success = True

        for service in self.services.values():
            try:
                # 每个服务独立初始化，失败不影响其他服务的尝试
                result = await service.initialize()
                if not result:
                    success = False
                    self.logger.error(f"服务初始化失败: {service.name}")
            except Exception as e:
                # 捕获异常避免整个初始化流程中断
                success = False
                self.logger.error(f"服务初始化异常: {service.name}, {e}")

        return success

    async def shutdown_all(self) -> None:
        """关闭所有服务 - 确保资源清理，即使某个服务关闭失败也继续处理其他服务"""
        self.logger.info("正在关闭所有服务...")

        for service in self.services.values():
            try:
                await service.shutdown()
            except Exception as e:
                # 关闭失败不应阻止其他服务的正常关闭
                self.logger.error(f"服务关闭异常: {service.name}, {e}")

    def get_service(self, name: str) -> Optional[BaseService]:
        """获取服务实例 - 提供类型安全的服务访问接口"""
        return self.services.get(name)


# 全局服务管理器实例
service_manager = ServiceManager()

# 注册默认服务
service_manager.register_service(ContentAnalysisService())
service_manager.register_service(UserProfileService())
service_manager.register_service(DataProcessingService())
