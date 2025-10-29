from src.core.config import 
from src.core.config import 
from src.core.config import 
from src.core.config import 
"""
缓存策略优化配置
生成时间：2025-10-26 20:57:22
"""

# 缓存策略配置
CACHE_STRATEGIES = {
    "cache_invalidation": {
        "time_based": {
            "enabled": True,
            "ttl_short": 60,  # 1分钟
            "ttl_medium": 300,  # 5分钟
            "ttl_long": 3600,  # 1小时
        },
        "event_based": {
            "enabled": True,
            "events": ["data_updated", "user_action", "config_changed"],
        },
    },
    "cache_warming": {
        "enabled": True,
        "strategies": ["most_used", "recently_accessed", "precomputed"],
        "warming_schedule": "0 6 * * *",  # 每天早上6点
    },
    "cache_hit_optimization": {
        "lru_promotion": True,
        "frequency_analysis": True,
        "access_pattern_learning": True,
    },
}


# 缓存键命名策略
class CacheKeyManager:
    @staticmethod
    def generate_key(prefix: str, identifier: str, **kwargs) -> str:
        """生成缓存键"""
        parts = [prefix, identifier]

        # 添加参数
        for key, value in sorted(kwargs.items()):
            parts.append(f"{key}:{value}")

        return ":".join(parts)

    @staticmethod
    def parse_key(key: str) -> Dict[str, str]:
        """解析缓存键"""
        parts = key.split(":")
        return {part.split(":") for part in parts if ":" in part}


# 缓存装饰器
def cache_result(prefix: str, ttl: int = 300, level: str = "L1_MEMORY"):
    """缓存结果装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = CacheKeyManager.generate_key(prefix, func.__name__, *args, **kwargs)

            # 尝试从缓存获取
            cached_result = multi_cache.get(key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_level = CacheLevel[level.upper()]
            multi_cache.set(key, result, cache_level, ttl)

            return result

        return wrapper

    return decorator
