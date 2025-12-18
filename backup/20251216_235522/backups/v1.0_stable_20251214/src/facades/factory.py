"""外观模式工厂模块
Facade Factory Module.

提供外观和子系统的工厂创建功能.
"""

from typing import Any

from .base import Facade, Subsystem, SystemFacade


class FacadeConfig:
    """外观配置类."""

    def __init__(
        self,
        name: str,
        subsystem_configs: dict[str, dict[str, Any]] | None = None,
        global_config: dict[str, Any] | None = None,
    ):
        """初始化外观配置.

        Args:
            name: 外观名称
            subsystem_configs: 子系统配置字典
            global_config: 全局配置
        """
        self.name = name
        self.subsystem_configs = subsystem_configs or {}
        self.global_config = global_config or {}
        self.auto_start = True
        self.health_check_interval = 30

    def add_subsystem_config(self, name: str, config: dict[str, Any]) -> None:
        """添加子系统配置."""
        self.subsystem_configs[name] = config

    def get_subsystem_config(self, name: str) -> dict[str, Any] | None:
        """获取子系统配置."""
        return self.subsystem_configs.get(name)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "name": self.name,
            "subsystem_configs": self.subsystem_configs,
            "global_config": self.global_config,
            "auto_start": self.auto_start,
            "health_check_interval": self.health_check_interval,
        }


class FacadeFactory:
    """外观工厂类."""

    def __init__(self):
        """初始化工厂."""
        self._subsystem_registry: dict[str[Subsystem]] = {}
        self._facade_registry: dict[str[Facade]] = {}
        self._created_instances: dict[str, Facade] = {}

    def register_subsystem(self, name: str, subsystem_class: type[Subsystem]) -> None:
        """注册子系统类型.

        Args:
            name: 子系统名称
            subsystem_class: 子系统类
        """
        self._subsystem_registry[name] = subsystem_class

    def register_facade(self, name: str, facade_class: type[Facade]) -> None:
        """注册外观类型.

        Args:
            name: 外观名称
            facade_class: 外观类
        """
        self._facade_registry[name] = facade_class

    def create_subsystem(
        self, name: str, config: dict[str, Any] | None = None
    ) -> Subsystem | None:
        """创建子系统实例.

        Args:
            name: 子系统名称
            config: 配置参数

        Returns:
            Optional[Subsystem]: 子系统实例或None
        """
        if name not in self._subsystem_registry:
            return None

        subsystem_class = self._subsystem_registry[name]
        return subsystem_class(name, config)

    def create_facade(self, config: FacadeConfig) -> Facade | None:
        """创建外观实例.

        Args:
            config: 外观配置

        Returns:
            Optional[Facade]: 外观实例或None
        """
        # 优先使用注册的特定外观类
        if config.name in self._facade_registry:
            facade_class = self._facade_registry[config.name]
            facade = facade_class(config.name, config.global_config)
        else:
            # 默认使用SystemFacade
            facade = SystemFacade(config.name, config.global_config)

        # 创建并注册子系统
        for subsystem_name, subsystem_config in config.subsystem_configs.items():
            subsystem = self.create_subsystem(subsystem_name, subsystem_config)
            if subsystem:
                facade.register_subsystem(subsystem)

        # 缓存创建的实例
        self._created_instances[config.name] = facade

        return facade

    def get_facade(self, name: str) -> Facade | None:
        """获取已创建的外观实例.

        Args:
            name: 外观名称

        Returns:
            Optional[Facade]: 外观实例或None
        """
        return self._created_instances.get(name)

    def create_system_facade(
        self, name: str = "System", config: dict[str, Any] | None = None
    ) -> SystemFacade:
        """创建系统外观的便捷方法.

        Args:
            name: 系统名称
            config: 配置参数

        Returns:
            SystemFacade: 系统外观实例
        """
        facade_config = FacadeConfig(name, global_config=config)
        return self.create_facade(facade_config)

    def list_registered_subsystems(self) -> list[str]:
        """列出已注册的子系统类型."""
        return list(self._subsystem_registry.keys())

    def list_registered_facades(self) -> list[str]:
        """列出已注册的外观类型."""
        return list(self._facade_registry.keys())

    def list_created_instances(self) -> list[str]:
        """列出已创建的实例."""
        return list(self._created_instances.keys())

    def clear_cache(self) -> None:
        """清除实例缓存."""
        self._created_instances.clear()


# 全局工厂实例
facade_factory = FacadeFactory()


# 便捷函数
def create_facade(
    name: str,
    subsystem_configs: dict[str, dict[str, Any]] | None = None,
    global_config: dict[str, Any] | None = None,
) -> Facade | None:
    """创建外观的便捷函数.

    Args:
        name: 外观名称
        subsystem_configs: 子系统配置
        global_config: 全局配置

    Returns:
        Optional[Facade]: 外观实例
    """
    config = FacadeConfig(name, subsystem_configs, global_config)
    return facade_factory.create_facade(config)


def create_system_facade(
    name: str = "System", config: dict[str, Any] | None = None
) -> SystemFacade:
    """创建系统外观的便捷函数.

    Args:
        name: 系统名称
        config: 配置参数

    Returns:
        SystemFacade: 系统外观实例
    """
    return facade_factory.create_system_facade(name, config)


# 导出的公共接口
__all__ = [
    "FacadeConfig",
    "FacadeFactory",
    "facade_factory",
    "create_facade",
    "create_system_facade",
]
