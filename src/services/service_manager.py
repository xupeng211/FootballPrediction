"""
ServiceManager - 服务管理器
==========================

V4.46.2: 占位实现，解决 API 启动导入错误

@module services.service_manager
@version V4.46.2
"""

from typing import Any, Dict, List, Optional, Type
import logging

from .base_service import BaseService


class ServiceManager:
    """
    服务管理器

    管理所有服务的生命周期
    """

    _instance: Optional["ServiceManager"] = None

    def __new__(cls) -> "ServiceManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services: Dict[str, BaseService] = {}
            cls._instance.logger = logging.getLogger("services.ServiceManager")
        return cls._instance

    def register(self, name: str, service: BaseService) -> None:
        """注册服务"""
        self._services[name] = service
        self.logger.info(f"服务已注册: {name}")

    def get(self, name: str) -> Optional[BaseService]:
        """获取服务"""
        return self._services.get(name)

    def get_all(self) -> Dict[str, BaseService]:
        """获取所有服务"""
        return self._services.copy()

    async def initialize_all(self) -> None:
        """初始化所有服务"""
        for name, service in self._services.items():
            try:
                await service.initialize()
                self.logger.info(f"服务已初始化: {name}")
            except Exception as e:
                self.logger.error(f"服务初始化失败: {name} - {e}")

    async def shutdown_all(self) -> None:
        """关闭所有服务"""
        for name, service in self._services.items():
            try:
                await service.shutdown()
                self.logger.info(f"服务已关闭: {name}")
            except Exception as e:
                self.logger.error(f"服务关闭失败: {name} - {e}")

    async def health_check_all(self) -> Dict[str, Any]:
        """检查所有服务健康状态"""
        results = {}
        for name, service in self._services.items():
            results[name] = await service.health_check()
        return results


# 全局服务管理器实例
service_manager = ServiceManager()


__all__ = ["ServiceManager", "service_manager"]
