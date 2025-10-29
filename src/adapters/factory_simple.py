"""
简化的适配器工厂
"""

from typing import Any, Dict, Optional, Type

from src.core.exceptions import AdapterError


class AdapterFactory:
    """适配器工厂"""

    def __init__(self):
        self._adapters: Dict[str, Type] = {}
        self._instances: Dict[str, Any] = {}

    def register_adapter(self, name: str, adapter_class: Type, **kwargs) -> None:
        """注册适配器类"""
        self._adapters[name] = adapter_class

    def create_adapter(
        self, name: str, config: Optional[Dict] = None, singleton: bool = False
    ) -> Any:
        """创建适配器实例"""
        if name not in self._adapters:
            raise AdapterError(f"No adapter registered for '{name}'")

        adapter_class = self._adapters[name]

        if singleton and name in self._instances:
            return self._instances[name]

        try:
            instance = adapter_class(**(config or {}))
        except Exception as e:
            raise AdapterError(f"Failed to create adapter '{name}': {e}")

        if singleton:
            self._instances[name] = instance

        return instance

    def get_adapter_names(self) -> list[str]:
        """获取已注册的适配器名称"""
        return list(self._adapters.keys())

    def clear_instances(self) -> None:
        """清除所有实例"""
        self._instances.clear()


# 全局工厂实例
_global_factory = AdapterFactory()


def get_adapter(
    name: str, config: Optional[Dict] = None, singleton: bool = False
) -> Any:
    """获取适配器实例（全局工厂）"""
    return _global_factory.create_adapter(name, config, singleton)


def register_adapter(name: str, adapter_class: Type, **kwargs) -> None:
    """注册适配器类（全局工厂）"""
    _global_factory.register_adapter(name, adapter_class, **kwargs)


def get_adapter_names() -> list[str]:
    """获取已注册的适配器名称（全局工厂）"""
    return _global_factory.get_adapter_names()


def clear_adapter_instances() -> None:
    """清除所有实例（全局工厂）"""
    _global_factory.clear_instances()


def get_global_factory() -> AdapterFactory:
    """获取全局工厂实例"""
    return _global_factory


def get_adapter(
    name: str, config: Optional[Dict] = None, singleton: bool = False
) -> Any:
    """获取适配器实例（便捷函数）"""
    return _global_factory.create_adapter(name, config, singleton)


def register_adapter(name: str, adapter_class: Type, **kwargs) -> None:
    """注册适配器类（便捷函数）"""
    _global_factory.register_adapter(name, adapter_class, **kwargs)
