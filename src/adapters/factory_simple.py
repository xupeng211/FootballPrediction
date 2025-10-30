""""
简化的适配器工厂
""""

from typing import Any, Dict, Optional, Type

from src.core.exceptions import AdapterError


class AdapterFactory:
    """适配器工厂"""

# 全局工厂实例
_global_factory = AdapterFactory()


# TODO: 方法 def create_adapter 过长(23行)，建议拆分
# 全局工厂实例
# TODO: 方法 def create_adapter 过长(23行)，建议拆分
# TODO: 方法 def create_adapter 过长(23行)，建议拆分
# 全局工厂实例
# TODO: 方法 def create_adapter 过长(23行)，建议拆分
# TODO: 方法 def create_adapter 过长(23行)，建议拆分
# 全局工厂实例
# TODO: 方法 def create_adapter 过长(23行)，建议拆分
# TODO: 方法 def create_adapter 过长(23行)，建议拆分
# 全局工厂实例
    def __init__(self):
        self._adapters: Dict[str, Type] = {}
        self._instances: Dict[str, Any] = {}

# TODO: 方法 def create_adapter 过长(23行),建议拆分
# TODO: 方法 def create_adapter 过长(23行),建议拆分
    def create_adapter(
        """TODO: 添加函数文档"""
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

def register_adapter(name: str, adapter_class: Type, **kwargs) -> None:
    """注册适配器类（便捷函数）"""
    _global_factory.register_adapter(name, adapter_class, **kwargs)


def get_adapter_names() -> list[str]:
    """获取已注册的适配器名称（全局工厂）"""
    return _global_factory.get_adapter_names()


    def clear_instances(self) -> None:
        """清除所有实例"""
        self._instances.clear()


# 全局工厂实例
def get_adapter(name: str, config: Optional[Dict] = None, singleton: bool = False) -> Any:
    """获取适配器实例（便捷函数）"""
    return _global_factory.create_adapter(name, config, singleton)


def clear_adapter_instances() -> None:
    """清除所有实例（全局工厂）"""
    _global_factory.clear_instances()


def get_global_factory() -> AdapterFactory:
    """获取全局工厂实例"""
    return _global_factory