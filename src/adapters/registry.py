"""
适配器注册表
"""

try:
    from src.adapters.base import Adapter
    from src.core.exceptions import AdapterError
except ImportError:
    # Fallback classes
    class AdapterError(Exception):
        pass

    class Adapter:
        pass


class AdapterRegistry:
    """适配器注册表"""

    def __init__(self, factory=None):
        """初始化适配器注册表"""
        self.factory = factory or self._create_default_factory()
        self.adapters: dict[str, Adapter] = {}
        self.groups: dict[str, list[Adapter]] = {}

    def _create_default_factory(self):
        """创建默认工厂"""
        try:
            from src.adapters.factory_simple import get_global_factory
            return get_global_factory()
        except ImportError:
            return None

    def register(
        self, name: str, adapter: Adapter, group: str | None = None
    ) -> None:
        """注册适配器"""
        self.adapters[name] = adapter
        if group:
            if group not in self.groups:
                self.groups[group] = []
            self.groups[group].append(adapter)

    def get_adapter(self, name: str) -> Adapter:
        """获取适配器"""
        if name not in self.adapters:
            raise AdapterError(f"Adapter '{name}' not found")
        return self.adapters[name]

    def get_group(self, group: str) -> list[Adapter]:
        """获取适配器组"""
        return self.groups.get(group, [])

    def list_adapters(self) -> list[str]:
        """列出所有适配器名称"""
        return list(self.adapters.keys())

    def list_groups(self) -> list[str]:
        """列出所有组名称"""
        return list(self.groups.keys())


# 全局注册表实例
_global_registry = AdapterRegistry()


def get_global_registry() -> AdapterRegistry:
    """获取全局注册表实例"""
    return _global_registry


def register_adapter(name: str, adapter: Adapter, group: str | None = None) -> None:
    """注册适配器（便捷函数）"""
    _global_registry.register(name, adapter, group)


def get_adapter(name: str) -> Adapter:
    """获取适配器（便捷函数）"""
    return _global_registry.get_adapter(name)