"""简化的适配器注册表
Simple Adapter Registry.

提供轻量级的适配器注册和管理功能。
Provides lightweight adapter registration and management functionality.
"""

from typing import Any, Optional

# 尝试导入AdapterError，如果失败则创建
try:
    from src.core.exceptions import AdapterError
except ImportError:

    class AdapterError(Exception):
        """适配器错误."""

        pass


class AdapterRegistry:
    """适配器注册表."""

    def __init__(self):
        """初始化适配器注册表."""
        self._registry: dict[str, dict] = {}
        self._instances: dict[str, Any] = {}

    def register(self, name: str, adapter_class: type, **kwargs) -> None:
        """注册适配器."""
        self._registry[name] = {"class": adapter_class, **kwargs}

    def unregister(self, name: str) -> None:
        """注销适配器."""
        if name not in self._registry:
            raise AdapterError(f"No adapter registered with name '{name}'")
        del self._registry[name]

    def get_adapter_class(self, name: str) -> Optional[type]:
        """获取适配器类."""
        if name in self._registry:
            return self._registry[name]["class"]
        return None

    def create_adapter(self, name: str, **kwargs) -> Any:
        """创建适配器实例."""
        adapter_info = self._registry.get(name)
        if not adapter_info:
            raise AdapterError(f"No adapter registered with name '{name}'")

        adapter_class = adapter_info["class"]
        instance_kwargs = {**adapter_info, **kwargs}
        del instance_kwargs["class"]

        instance = adapter_class(**instance_kwargs)
        self._instances[name] = instance
        return instance

    def get_adapter(self, name: str) -> Optional[Any]:
        """获取适配器实例."""
        return self._instances.get(name)

    def get_adapter_names(self) -> list[str]:
        """获取所有适配器名称."""
        return list(self._registry.keys())

    def clear(self) -> None:
        """清除所有适配器."""
        self._registry.clear()
        self._instances.clear()


# 全局注册表实例
_global_registry: AdapterRegistry | None = None


def get_global_registry() -> AdapterRegistry:
    """获取全局注册表实例."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AdapterRegistry()
    return _global_registry


__all__ = [
    "AdapterRegistry",
    "AdapterError",
    "get_global_registry",
]
