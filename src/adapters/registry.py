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

# 全局注册表实例
_global_registry = AdapterRegistry()


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
        """TODO: 添加函数文档"""
        self, name: str, adapter: Adapter, group: str | None = None
    ) -> None:
        """注册适配器"""
        self.adapters[name] = adapter
        if group:
            if group not in self.groups:
                self.groups[group] = []
            self.groups[group].append(adapter)

def get_adapter(name: str) -> Adapter:
    """获取适配器（便捷函数）"""
    return _global_registry.get_adapter(name)

    def get_group(self, group: str) -> list[Adapter]:
        """获取适配器组"""
        return self.groups.get(group, [])

    def list_adapters(self) -> list[str]:
        """列出所有适配器名称"""
        return list(self.adapters.keys())

    def list_groups(self) -> list[str]:
        """列出所有组名称"""
        return list(self.groups.keys())

    def unregister(self, name: str) -> bool:
        """注销适配器"""
        if name not in self.adapters:
            return False

        adapter = self.adapters[name]
        del self.adapters[name]

        # 从组中移除（保留空组以满足测试期望）
        for group_name, group_adapters in self.groups.items():
            if adapter in group_adapters:
                group_adapters.remove(adapter)

        return True

    def clear(self) -> None:
        """清空注册表"""
        self.adapters.clear()
        self.groups.clear()


# 全局注册表实例
def get_global_registry() -> AdapterRegistry:
    """获取全局注册表实例"""
    return _global_registry


def register_adapter(name: str, adapter: Adapter, group: str | None = None) -> None:
    """注册适配器（便捷函数）"""
    _global_registry.register(name, adapter, group)

