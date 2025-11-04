"""
适配器工厂模块
Adapter Factory Module
"""

from dataclasses import dataclass, field
from typing import Any

from .base import Adapter

try:
    from .football import ApiFootballAdapter, CompositeFootballAdapter, OptaDataAdapter
except ImportError:
    # Mock implementations for testing
    class ApiFootballAdapter(Adapter):
        pass

    class CompositeFootballAdapter(Adapter):
        pass

    class OptaDataAdapter(Adapter):
        pass


@dataclass
class AdapterConfig:
    """适配器配置"""

    name: str
    adapter_type: str
    enabled: bool = True
    priority: int = 100
    config: dict[str, Any] = field(default_factory=dict)
    timeout: int | None = None
    retry_count: int = 3
    rate_limit: int | None = None


@dataclass
class AdapterGroupConfig:
    """适配器组配置"""

    name: str
    description: str = ""
    adapters: list[AdapterConfig] = field(default_factory=list)
    fallback_enabled: bool = True
    load_balancing: str = "round_robin"


class AdapterFactory:
    """适配器工厂类"""

    def __init__(self):
        """初始化适配器工厂"""
        self._adapters = {}
        self._configs = {}
        self._groups = {}
        self._register_default_adapters()

    def _register_default_adapters(self):
        """注册默认适配器"""
        self.register_adapter("api_football", ApiFootballAdapter)
        self.register_adapter("composite_football", CompositeFootballAdapter)
        self.register_adapter("opta_data", OptaDataAdapter)

    def register_adapter(self, name: str, adapter_class: type[Adapter]) -> None:
        """注册适配器"""
        self._adapters[name] = adapter_class

    def create_adapter(self, name: str, config: dict[str, Any] | None = None, **kwargs) -> Adapter:
        """创建适配器"""
        if name not in self._adapters:
            raise ValueError(f"Unknown adapter: {name}")

        adapter_class = self._adapters[name]
        return adapter_class(config or {}, **kwargs)

    def create_group(self, group_config: AdapterGroupConfig) -> list[Adapter]:
        """创建适配器组"""
        adapters = []
        for adapter_config in group_config.adapters:
            if adapter_config.enabled:
                adapter = self.create_adapter(
                    adapter_config.name,
                    adapter_config.config
                )
                adapters.append(adapter)

        return adapters


# 全局适配器工厂实例
_global_factory = AdapterFactory()


def get_adapter(name: str, config: dict[str, Any] | None = None, **kwargs) -> Adapter:
    """创建适配器的便捷函数"""
    return _global_factory.create_adapter(name, config, **kwargs)


def register_adapter(name: str, adapter_class: type[Adapter]) -> None:
    """注册适配器的便捷函数"""
    _global_factory.register_adapter(name, adapter_class)


def get_global_factory() -> AdapterFactory:
    """获取全局工厂实例"""
    return _global_factory