"""
odds_collector.py
odds_collector

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

try:
    from .odds.basic import collector
    from .odds.basic import parser
    from .odds.basic import storage
    from .odds.basic import validator
except ImportError:
    # 如果odds子模块不存在，提供空实现
    collector = None
    parser = None
    storage = None
    validator = None

warnings.warn(
    "直接从 odds_collector 导入已弃用。请从 src/collectors/odds/basic 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容


# 创建兼容类
class OddsCollector:
    """兼容性占位符类"""

    def __init__(self, *args, **kwargs):
        if collector is None:
            raise NotImplementedError("OddsCollector implementation not available")


class OddsCollectorFactory:
    """兼容性占位符工厂类"""

    @staticmethod
    def create(*args, **kwargs):
        if collector is None:
            raise NotImplementedError("OddsCollector implementation not available")
        return OddsCollector(*args, **kwargs)


# 导出所有类
__all__ = ["OddsCollector", "OddsCollectorFactory"]
