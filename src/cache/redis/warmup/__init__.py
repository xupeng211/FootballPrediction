"""
缓存预热模块

包含缓存预热管理器，用于系统启动时预热高频数据
"""


from .warmup_manager import CacheWarmupManager, warmup_cache_on_startup

__all__ = [
    "CacheWarmupManager",
    "warmup_cache_on_startup",
]
