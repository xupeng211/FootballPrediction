from typing import Optional

# adapters package init
# 自动生成以解决导入问题
from src.adapters import AdapterFactory, AdapterRegistry

from .router import router

# 创建全局适配器实例以支持测试mock
# 如果AdapterRegistry未实现，使用简单的字典作为替代
if AdapterRegistry is None:
    adapter_registry = {}  # 简单的字典替代
else:
    adapter_registry = AdapterRegistry()

if AdapterFactory is None:
    adapter_factory = {}  # 简单的字典替代
else:
    adapter_factory = AdapterFactory()

__all__ = ["router", "adapter_registry", "adapter_factory"]
