from typing import Any, Dict, List, Optional, Union
"""
简化的适配器注册表
"""

from src.core.exceptions import AdapterError


class AdapterRegistry:
    """适配器注册表"""

    def __init__(self):
        self._registry: Dict[str, Dict[str, Any] = {}
        self._instances: Dict[str, Any] = {}

    def register(self, name: str, adapter_class: Type[Any], **kwargs):
        """注册适配器"""
        self._registry[name] = {"class": adapter_class, **kwargs}

    def unregister(self, name: str):
        """注销适配器"""
        if name not in self._registry:
            raise AdapterError(f"No adapter registered with name '{name}'")
        del self._registry[name]
        if name in self._instances:
            del self._instances[name]

    def create(self, name: str, config: Optional[Dict[str, Any]] = None):
        """创建适配器实例"""
        if name not in self._registry:
            raise AdapterError(f"No adapter registered with name '{name}'")

        adapter_info = self._registry[name]
        adapter_class = adapter_info["class"]

        try:
            if config:
                return adapter_class(config)
            else:
                return adapter_class()
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            raise AdapterError(f"Failed to create adapter '{name}': {str(e)}")

    def get_info(self, name: str) -> Dict[str, Any]:
        """获取适配器信息"""
        if name not in self._registry:
            raise AdapterError(f"No adapter registered with name '{name}'")
        return self._registry[name].copy()

    def list(self, **filters) -> List[tuple]:
        """列出适配器，支持过滤条件"""
        adapters = []
        for name, info in self._registry.items():
            match = True
            for key, value in filters.items():
                if key in info and info[key] != value:
                    match = False
                    break
            if match:
                adapters.append((name, info))
        return adapters

    def get_singleton(self, name: str):
        """获取单例实例"""
        if name not in self._registry:
            raise AdapterError(f"No adapter registered with name '{name}'")

        if name not in self._instances:
            adapter_info = self._registry[name]
            adapter_class = adapter_info["class"]
            self._instances[name] = adapter_class()

        return self._instances[name]

    def clear(self):
        """清空注册表"""
        self._registry.clear()
        self._instances.clear()

    def validate_config(self, name: str, config: Dict[str, Any]) -> bool:
        """验证配置"""
        # 简化实现，总是返回True
        return True

    def get_dependencies(self, name: str) -> List[str]:
        """获取依赖"""
        if name in self._registry:
            return self._registry[name].get("dependencies", [])  # type: ignore
        return []

    def resolve_dependencies(self, name: str) -> List[str]:
        """解析依赖关系"""
        # 简化实现
        return [name]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total": len(self._registry),
            "singletons": sum(
                1 for info in self._registry.values() if info.get("singleton", False)
            ),
        }

    def export(self) -> Dict[str, Any]:
        """导出注册表"""
        return self._registry.copy()

    def import_data(self, data: Dict[str, Any]):
        """导入数据"""
        self._registry.update(data)

    def adapter(self, name: str = None, **kwargs):
        """装饰器注册适配器"""

        def decorator(cls):
            adapter_name = name or cls.__name__
            self.register(adapter_name, cls, **kwargs)
            return cls

        return decorator


# 全局注册表实例
_global_registry = None


def get_global_registry() -> AdapterRegistry:
    """获取全局注册表实例"""
    global _global_registry
    if _global_registry is None:
        _global_registry = AdapterRegistry()
    return _global_registry


def register_adapter(name: str = None, **kwargs):
    """装饰器注册适配器"""
    registry = get_global_registry()
    return registry.adapter(name, **kwargs)
