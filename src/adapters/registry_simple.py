"""
简化的适配器注册表
"""

from typing import Any, Dict, Optional, Type

from src.core.exceptions import AdapterError


class AdapterRegistry:
    """适配器注册表"""

    def __init__(self):
        """初始化适配器注册表"""
        self._registry: Dict[str, Dict] = {}
        self._instances: Dict[str, Any] = {}

    def register(self, name: str, adapter_class: Type, **kwargs) -> None:
        """注册适配器"""
        self._registry[name] = {"class": adapter_class, **kwargs}

    def unregister(self, name: str) -> None:
        """注销适配器"""
        if name not in self._registry:
            raise AdapterError(f"No adapter registered with name '{name}'")
        del self._registry[name]
        if name in self._instances:
            del self._instances[name]

    def create(self, name: str, config: Optional[Dict] = None) -> Any:
        """创建适配器实例"""
        if name not in self._registry:
            raise AdapterError(f"No adapter registered with name '{name}'")

        adapter_info = self._registry[name]
        adapter_class = adapter_info["class"]

        try:
            return adapter_class(config)
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            raise AdapterError(f"Failed to create adapter '{name}': {str(e)}")

    def get_registered_names(self) -> list[str]:
        """获取所有已注册的适配器名称"""
        return list(self._registry.keys())

    def get_adapter_info(self, name: str) -> Optional[Dict]:
        """获取适配器信息"""
        return self._registry.get(name)

    def clear(self) -> None:
        """清空注册表"""
        self._registry.clear()
        self._instances.clear()


# 全局注册表实例
_global_registry: Optional[AdapterRegistry] = None


def get_global_registry() -> AdapterRegistry:
    """获取全局注册表实例"""
    global _global_registry
    if _global_registry is None:
        _global_registry = AdapterRegistry()
    return _global_registry


def register_adapter(name: str = None, **kwargs):
    """装饰器注册适配器"""
    def decorator(cls):
        """装饰器函数"""
        adapter_name = name or cls.__name__
        registry = get_global_registry()
        registry.register(adapter_name, cls, **kwargs)
        return cls

    return decorator
