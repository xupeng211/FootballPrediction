"""
服务注册表

管理服务的工厂模式和依赖配置。
"""

from typing import Dict, Type, Optional, List
from src.core import logger
from ..base import BaseService


class ServiceRegistry:
    """服务注册表 - 管理服务工厂和依赖配置"""

    def __init__(self) -> None:
        self._factories: Dict[str, Type[BaseService]] = {}
        self._dependencies: Dict[str, List[str]] = {}
        self._singleton_services: Dict[str, BaseService] = {}
        self.logger = logger

    def register_factory(self, name: str, factory: Type[BaseService]) -> None:
        """注册服务工厂"""
        if name in self._factories:
            self.logger.warning(f"替换服务工厂: {name}")
        self._factories[name] = factory
        self.logger.debug(f"已注册服务工厂: {name}")

    def register_singleton(self, name: str, service: BaseService) -> None:
        """注册单例服务"""
        if name in self._singleton_services:
            self.logger.warning(f"替换单例服务: {name}")
        self._singleton_services[name] = service
        self.logger.debug(f"已注册单例服务: {name}")

    def get_factory(self, name: str) -> Optional[Type[BaseService]]:
        """获取服务工厂"""
        return self._factories.get(name)

    def get_singleton(self, name: str) -> Optional[BaseService]:
        """获取单例服务"""
        return self._singleton_services.get(name)

    def create_service(self, name: str) -> Optional[BaseService]:
        """创建服务实例"""
        # 先检查是否为单例
        if name in self._singleton_services:
            return self._singleton_services[name]

        # 使用工厂创建
        factory = self._factories.get(name)
        if not factory:
            self.logger.error(f"未找到服务工厂: {name}")
            return None

        try:
            return factory()
        except Exception as e:
            self.logger.error(f"创建服务失败: {name}, {e}")
            return None

    def set_dependencies(self, name: str, dependencies: List[str]) -> None:
        """设置服务依赖"""
        self._dependencies[name] = dependencies
        self.logger.debug(f"已设置服务依赖: {name} -> {dependencies}")

    def get_dependencies(self, name: str) -> List[str]:
        """获取服务依赖"""
        return self._dependencies.get(name, [])

    def get_all_services(self) -> List[str]:
        """获取所有注册的服务名称"""
        return list(set(self._factories.keys()) | set(self._singleton_services.keys()))

    def validate_dependencies(self) -> bool:
        """验证依赖关系是否有效"""
        for name, deps in self._dependencies.items():
            for dep in deps:
                if dep not in self._factories and dep not in self._singleton_services:
                    self.logger.error(f"依赖不存在: {name} -> {dep}")
                    return False
        return True

    def get_startup_order(self) -> List[str]:
        """根据依赖关系计算启动顺序"""
        # 拓扑排序
        result = []
        visited = set()
        temp_visited = set()

        def visit(name: str):
            if name in temp_visited:
                raise ValueError(f"循环依赖检测: {name}")
            if name not in visited:
                temp_visited.add(name)
                for dep in self._dependencies.get(name, []):
                    visit(dep)
                temp_visited.remove(name)
                visited.add(name)
                result.append(name)

        for name in self._factories.keys():
            if name not in visited:
                visit(name)

        return result