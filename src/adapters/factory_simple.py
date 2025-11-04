"""
简单的适配器工厂实现
Simple Adapter Factory Implementation
"""

from typing import Any

from .base import Adapter

try:
    from .registry import AdapterError
except ImportError:
    class AdapterError(Exception):
        pass


class AdapterFactory:
    """适配器工厂类"""

    def __init__(self):
        """初始化适配器工厂"""
        self.adapters = {}
        self.singletons = {}

    def register_adapter(self, name: str, adapter_class: type[Adapter]) -> None:
        """
        注册适配器

        Args:
            name: 适配器名称
            adapter_class: 适配器类
        """
        self.adapters[name] = adapter_class

    def create_adapter(
        self,
        name: str,
        config: dict[str, Any] | None = None,
        singleton: bool = True
    ) -> Adapter:
        """
        创建适配器实例

        Args:
            name: 适配器名称
            config: 配置参数
            singleton: 是否单例

        Returns:
            适配器实例

        Raises:
            AdapterError: 适配器创建失败
        """
        if name not in self.adapters:
            raise AdapterError(f"Unknown adapter: {name}")

        adapter_class = self.adapters[name]

        if singleton:
            if name not in self.singletons:
                self.singletons[name] = adapter_class(config or {})
            return self.singletons[name]

        return adapter_class(config or {})


# 全局工厂实例
_global_factory = AdapterFactory()


def get_adapter(
    name: str,
    config: Any = None,
    singleton: bool = True
) -> Adapter:
    """
    获取适配器实例（便捷函数）

    Args:
        name: 适配器名称
        config: 配置参数
        singleton: 是否单例

    Returns:
        适配器实例
    """
    return _global_factory.create_adapter(name, config, singleton)


def register_adapter(name: str, adapter_class: type[Adapter]) -> None:
    """
    注册适配器（便捷函数）

    Args:
        name: 适配器名称
        adapter_class: 适配器类
    """
    _global_factory.register_adapter(name, adapter_class)


def get_global_factory() -> AdapterFactory:
    """
    获取全局工厂实例

    Returns:
        全局工厂实例
    """
    return _global_factory


# 预定义的适配器名称
class AdapterNames:
    """预定义的适配器名称常量"""

    HTTP = "http"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    FILE_STORAGE = "file_storage"