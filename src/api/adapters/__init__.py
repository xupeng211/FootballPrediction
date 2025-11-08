from src.adapters import AdapterFactory, AdapterRegistry

from .router import router

adapter_registry = AdapterRegistry()
adapter_factory = AdapterFactory()
__all__ = ["router", "adapter_registry", "adapter_factory"]
