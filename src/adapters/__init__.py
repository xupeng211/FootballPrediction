from .base import Adaptee, BaseAdapter, Target

# 暂时注释掉有问题的模块导入，等后续修复
# from .factory_simple import AdapterFactory, get_adapter
# from .football import (
#     ApiFootballAdapter,
#     FootballApiAdapter,
#     FootballDataAdapter,
#     OptaDataAdapter,
# )
# from .registry import AdapterError, AdapterRegistry

# 适配器模式实现
# Adapter Pattern Implementation
# 用于集成外部系统和API.
# Used to integrate external systems and APIs.

__all__ = [
    # 基础类 - Base classes
    "BaseAdapter",
    "Adaptee",
    "Target",
]

# 为了向后兼容，提供BaseAdapter的别名
Adapter = BaseAdapter
