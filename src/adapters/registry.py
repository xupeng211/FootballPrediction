from .base import Adapter
from src.adapters.factory_simple import get_global_factory

"""


"""

    """适配器错误"""

    """适配器注册表"""

        """初始化适配器注册表"""

        """创建默认工厂"""

        """注册适配器"""

        """获取适配器"""

        """获取适配器组"""

# 全局注册表实例

    """获取全局注册表"""

适配器注册表模块
Adapter Registry Module
class AdapterError(Exception):
class AdapterRegistry:
def __init__(self, factory=None):
        self.factory = factory or self._create_default_factory()
        self.adapters: dict[str, Adapter] = {}
        self.groups: dict[str, list[Adapter]] = {}
def _create_default_factory(self):
        try:
            return get_global_factory()
        except ImportError:
            return None
def register(self, name: str, adapter: Adapter, group: str | None = None) -> None:
        self.adapters[name] = adapter
        if group:
            if group not in self.groups:
                self.groups[group] = []
            self.groups[group].append(adapter)
def get_adapter(self, name: str) -> Adapter:
        if name not in self.adapters:
            raise AdapterError(f"Adapter '{name}' not found")
        return self.adapters[name]
def get_group(self, group: str) -> list[Adapter]:
        return self.groups.get(group, [])
_GLOBAL_REGISTRY = AdapterRegistry()
def get_global_registry() -> AdapterRegistry:
    return _global_registry
