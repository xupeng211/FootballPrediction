"""
简单的适配器工厂实现
Simple Adapter Factory Implementation
"""

from typing import Any

from .base import Adapter, AdapterError


class AdapterFactory:
    """适配器工厂类"""

# 全局工厂实例
_global_factory = AdapterFactory()


) -> Adapter:
    """
    获取适配器实例（便捷函数）

    Args:
        name: 适配器名称
        config: 配置参数
        singleton: 是否单例

    Returns:
        适配器实例
    """
    return _global_factory.create_adapter(name, config, singleton)


# 预定义的适配器名称
class AdapterNames:
    """适配器名称常量"""

    # 数据源适配器
    FOOTBALL_DATA = "football_data"
    BETTING_ODDS = "betting_odds"
    MATCH_RESULTS = "match_results"

    # 存储适配器
    DATABASE = "database"
    CACHE = "cache"
    FILE_STORAGE = "file_storage"

    # 分析适配器
    PREDICTION = "prediction"
    STATISTICS = "statistics"
    PERFORMANCE = "performance"

# 预定义的适配器名称
# TODO: 方法 def create_adapter 过长(46行)，建议拆分
# 全局工厂实例
) -> Adapter:
) -> Adapter:
# 预定义的适配器名称
# TODO: 方法 def create_adapter 过长(46行)，建议拆分
# 全局工厂实例
) -> Adapter:
# 预定义的适配器名称
# TODO: 方法 def create_adapter 过长(46行)，建议拆分
# 全局工厂实例
def get_adapter(
    """TODO: 添加函数文档"""
    name: str,
    config: dict[str, Any] | None = None,
    singleton: bool = True
) -> Adapter:
    def __init__(self):
        """初始化适配器工厂"""
        self._adapters: dict[str, type] = {}
        self._instances: dict[str, Any] = {}

def register_adapter(name: str, adapter_class: type) -> None:
    """
    注册适配器（便捷函数）

    Args:
        name: 适配器名称
        adapter_class: 适配器类
    """
    _global_factory.register_adapter(name, adapter_class)


# 预定义的适配器名称
# TODO: 方法 def create_adapter 过长(46行)，建议拆分
    def create_adapter(
        """TODO: 添加函数文档"""
        self,
        name: str,
        config: dict[str, Any] | None = None,
        singleton: bool = True
    ) -> Adapter:
        """
        创建适配器实例

        Args:
            name: 适配器名称
            config: 配置参数
            singleton: 是否单例

        Returns:
            适配器实例

        Raises:
            AdapterError: 适配器创建失败
        """
        if name not in self._adapters:
            raise AdapterError(f"Adapter '{name}' not registered")

        # 单例模式
        if singleton and name in self._instances:
            return self._instances[name]

        try:
            adapter_class = self._adapters[name]

            # 创建适配器实例
            if config:
                adapter = adapter_class(**config)
            else:
                adapter = adapter_class()

            # 保存单例实例
            if singleton:
                self._instances[name] = adapter

            return adapter

        except Exception as e:
            raise AdapterError(f"Failed to create adapter '{name}': {e}")

    def list_adapters(self) -> list[str]:
        """列出所有注册的适配器名称"""
        return list(self._adapters.keys())

    def is_registered(self, name: str) -> bool:
        """检查适配器是否已注册"""
        return name in self._adapters

    def unregister_adapter(self, name: str) -> None:
        """注销适配器"""
        if name in self._adapters:
            del self._adapters[name]
        if name in self._instances:
            del self._instances[name]

    def clear_instances(self) -> None:
        """清空所有实例"""
        self._instances.clear()


# 全局工厂实例
def get_global_factory() -> AdapterFactory:
    """获取全局工厂实例"""
    return _global_factory

