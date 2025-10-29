"""
简化的适配器工厂
"""

from typing import Any, Dict, Optional, Type

from src.core.exceptions import AdapterError


class AdapterFactory:
    """适配器工厂"""

# 全局工厂实例
# 全局工厂实例
# 全局工厂实例
    def __init__(self):
        self._adapters: Dict[str, Type] = {}
        self._instances: Dict[str, Any] = {}

    def register_adapter(self, name: str, adapter_class: Type, **kwargs) -> None:
        """注册适配器类"""
        self._adapters[name] = adapter_class

# TODO: 方法 def create_adapter 过长(21行)，建议拆分
    def create_adapter(
        self, name: str, config: Optional[Dict] = None, singleton: bool = False
    ) -> Any:
        """创建适配器实例"""
        if name not in self._adapters:
            raise AdapterError(f"No adapter registered for '{name}'")

        adapter_class = self._adapters[name]

        if singleton and name in self._instances:
            return self._instances[name]

        adapter = adapter_class(config)

        if singleton:
            self._instances[name] = adapter

        return adapter

    def get_adapter_names(self) -> list[str]:
        """获取所有注册的适配器名称"""
        return list(self._adapters.keys())


# 全局工厂实例
def get_global_factory() -> AdapterFactory:
    """获取全局工厂实例"""
    global _global_factory
    if _global_factory is None:
        _global_factory = AdapterFactory()
    return _global_factory


def get_adapter(adapter_type: str, config: Optional[Dict] = None, singleton: bool = True) -> Any:
    """便捷函数：获取适配器"""
    factory = get_global_factory()
    return factory.create_adapter(adapter_type, config, singleton)