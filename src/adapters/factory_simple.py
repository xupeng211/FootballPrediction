"""
简化的适配器工厂
"""

from typing import Any, Dict, Optional, Type, cast
from src.core.exceptions import AdapterError


class AdapterFactory:
    """适配器工厂"""

    def __init__(self):  # type: ignore
        self._adapters: Dict[str, Type] = {}
        self._instances: Dict[str, Any] = {}

    def register_adapter(self, name: str, adapter_class: Type, **kwargs):  # type: ignore
        """注册适配器"""
        if name in self._adapters:
            raise AdapterError(f"Adapter '{name}' already registered")
        self._adapters[name] = cast(
            Type[object],
            {
                "class": adapter_class,
                "singleton": kwargs.get("singleton", False),
                **kwargs,
            }
        )

    def create_adapter(
        self, name: str, config: Optional[Dict] = None, singleton: bool = False
    ):
        """创建适配器实例"""
        if name not in self._adapters:
            raise AdapterError(f"No adapter registered for '{name}'")

        adapter_info = self._adapters[name]
        adapter_class = adapter_info["class"]

        try:
            if singleton or adapter_info["singleton"]:
                if name not in self._instances:
                    self._instances[name] = adapter_class(config)
                return self._instances[name]
            else:
                return adapter_class(config)
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            raise AdapterError(f"Failed to create adapter '{name}': {str(e)}")

    def get_instance(self):  # type: ignore
        """获取全局工厂实例"""
        return self

    def list_adapters(self):  # type: ignore
        """列出所有已注册的适配器"""
        return [(name, info["class"]) for name, info in self._adapters.items()]

    def list(self, **filters):  # type: ignore
        """列出适配器，支持过滤条件"""
        adapters = []
        for name, info in self._adapters.items():
            match = True
            for key, value in filters.items():
                if key in info and info[key] != value:
                    match = False
                    break
            if match:
                adapters.append((name, info))
        return adapters

    def unregister_adapter(self, name: str):  # type: ignore
        """注销适配器"""
        self._adapters.pop(name, None)
        self._instances.pop(name, None)

    def get_adapter_type(self, name: str):  # type: ignore
        """获取适配器类型"""
        if name in self._adapters:
            return self._adapters[name]["class"]
        return None


# 全局工厂实例
_global_factory = None


def get_global_factory() -> AdapterFactory:
    """获取全局工厂实例"""
    global _global_factory
    if _global_factory is None:
        _global_factory = AdapterFactory()
    return _global_factory


def get_adapter(
    adapter_type: str, config: Optional[Dict] = None, singleton: bool = False
):
    """便捷函数：获取适配器"""
    factory = get_global_factory()
    return factory.create_adapter(adapter_type, config, singleton)
