# adapters package init
# 自动生成以解决导入问题

from .router import router
from src.adapters import AdapterRegistry, AdapterFactory

# 创建全局适配器实例以支持测试mock
adapter_registry = AdapterRegistry()
adapter_factory = AdapterFactory()

__all__ = ["router", "adapter_registry", "adapter_factory"]
