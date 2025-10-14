"""
Manager - 服务模块

提供 manager 相关的服务功能。

主要功能：
- [待补充 - Manager的主要功能]

使用示例：
    from services import Manager
    # 使用示例代码

注意事项：
- [待补充 - 使用注意事项]
"""

from typing import Any,  Dict[str, Any],  Any, Optional

from src.core import logger
from src.core.config import get_settings

from .base_unified import BaseService
from .content_analysis import ContentAnalysisService
from .data_processing import DataProcessingService
from .user_profile import UserProfileService

"""
足球预测系统服务管理器模块

统一管理所有业务服务的生命周期和依赖关系。
"""


class ServiceManager:
    """服务管理器 - 负责统一管理所有业务服务的生命周期和依赖关系"""

    def __init__(self) -> None:
        self._services: Dict[str, BaseService] = {}}
        self.logger = logger

    def register_service(self, name: str, service: BaseService) -> None:
        """注册服务 - 将服务加入管理器，支持后续统一初始化和管理"""
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

    def get_service(self, name: str) -> Optional[BaseService]:
        """获取服务实例 - 提供类型安全的服务访问接口"""
        return self._services.get(name)

    def list_services(self) -> Dict[str, BaseService]:
        """获取所有服务列表"""
        return self._services.copy()

    @property
    def services(self) -> Dict[str, BaseService]:
        """服务字典属性 - 兼容测试代码"""
        return self._services

    async def initialize_all(self) -> bool:
        """初始化所有服务 - 按注册顺序依次初始化，任一失败则整体失败"""
        self.logger.info("正在初始化所有服务...")
        success = True
        for service in self._services.values():
            try:
                # 每个服务独立初始化，失败不影响其他服务的尝试
                result = await service.initialize()
                if not result:
                    success = False
                    self.logger.error(f"服务初始化失败: {service.name}")
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                # 捕获异常避免整个初始化流程中断
                success = False
                self.logger.error(f"服务初始化异常: {service.name}, {e}")
        return success

    async def shutdown_all(self) -> None:
        """关闭所有服务 - 确保资源清理，即使某个服务关闭失败也继续处理其他服务"""
        self.logger.info("正在关闭所有服务...")
        for service in self._services.values():
            try:
                await service.shutdown()
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                # 关闭失败不应阻止其他服务的正常关闭
                self.logger.error(f"服务关闭异常: {service.name}, {e}")


# 全局服务管理器实例
service_manager = ServiceManager()


_SERVICE_FACTORIES = {
    "ContentAnalysisService": ContentAnalysisService,
    "UserProfileService": UserProfileService,
    "DataProcessingService": DataProcessingService,
}


def _ensure_default_services() -> None:
    settings = get_settings()
    enabled_services = getattr(settings, "enabled_services", []) or []

    for service_name in enabled_services:
        factory = _SERVICE_FACTORIES.get(service_name)
        if not factory:
            service_manager.logger.warning(
                "未识别的服务名称，跳过注册: %s", service_name
            )
            continue

        if service_name not in service_manager.services:
            service_manager.register_service(service_name, factory())


_ensure_default_services()
