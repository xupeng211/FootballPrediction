"""
简化的适配器工厂
"""

from typing import Any, Dict, Optional, Type


class AdapterFactory:
    """适配器工厂"""

    def __init__(self):
        """初始化适配器工厂"""
        self._adapters: Dict[str, Type] = {}
        self._instances: Dict[str, Any] = {}

    def register_adapter(self, name: str, adapter_class: Type) -> None:
        """注册适配器"""
        self._adapters[name] = adapter_class

    def create_adapter(
        self, name: str, config: Optional[Dict] = None, singleton: bool = False
    ) -> Any:
        """创建适配器实例"""
        if name not in self._adapters:
            raise ValueError(f"Unknown adapter: {name}")

        if singleton and name in self._instances:
            return self._instances[name]

        adapter_class = self._adapters[name]
        instance = adapter_class(config or {})

        if singleton:
            self._instances[name] = instance

        return instance


# 全局工厂实例
_global_factory = AdapterFactory()


def get_adapter(
    name: str, config: Optional[Dict] = None, singleton: bool = False
) -> Any:
    """获取适配器实例（便捷函数）"""
    return _global_factory.create_adapter(name, config, singleton)
