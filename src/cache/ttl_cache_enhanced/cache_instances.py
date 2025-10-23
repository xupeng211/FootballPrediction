"""
预定义的缓存实例
Predefined Cache Instances

提供常用的缓存实例，开箱即用。
Provides commonly used cache instances, ready to use.
"""

from .ttl_cache import TTLCache

# 预定义的缓存实例
# Predefined cache instances

# 预测缓存 - 30分钟过期
prediction_cache = TTLCache(max_size=10000, default_ttl=1800)

# 特征缓存 - 1小时过期
feature_cache = TTLCache(max_size=5000, default_ttl=3600)

# 赔率缓存 - 5分钟过期
odds_cache = TTLCache(max_size=20000, default_ttl=300)

# 会话缓存 - 2小时过期
session_cache = TTLCache(max_size=1000, default_ttl=7200)

# 配置缓存 - 24小时过期
config_cache = TTLCache(max_size=500, default_ttl=86400)

# 临时缓存 - 5分钟过期
temp_cache = TTLCache(max_size=1000, default_ttl=300)

# 所有缓存的字典，方便统一管理
# Dictionary of all caches for easy management
CACHES = {
    "prediction": prediction_cache,
    "feature": feature_cache,
    "odds": odds_cache,
    "session": session_cache,
    "config": config_cache,
    "temp": temp_cache,
}


def start_auto_cleanup():  # type: ignore
    """启动所有缓存的自动清理"""
    for cache in CACHES.values():
        cache.start_auto_cleanup()


def stop_auto_cleanup():  # type: ignore
    """停止所有缓存的自动清理"""
    for cache in CACHES.values():
        cache.stop_auto_cleanup()


def get_cache(name: str):  # type: ignore
    """
    根据名称获取缓存

    Args:
        name: 缓存名称

    Returns:
        TTLCache: 缓存实例，如果不存在返回None
    """
    return CACHES.get(name)


def get_all_stats() -> dict:
    """
    获取所有缓存的统计信息

    Returns:
        dict: 统计信息字典
    """
    stats = {}
    for name, cache in CACHES.items():
        stats[name] = cache.get_stats()
    return stats


def clear_all_caches():  # type: ignore
    """清空所有缓存"""
    for cache in CACHES.values():
        cache.clear()


def cleanup_all_expired():  # type: ignore
    """清理所有缓存的过期项"""
    total_cleaned = 0
    for cache in CACHES.values():
        total_cleaned += cache.cleanup_expired()
    return total_cleaned


# 启动自动清理
# Start auto cleanup
start_auto_cleanup()
