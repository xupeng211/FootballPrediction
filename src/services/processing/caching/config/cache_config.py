from typing import Optional

"""缓存配置
Cache Configuration.
"""

from dataclasses import dataclass


@dataclass
class CacheConfig:
    """类文档字符串."""

    pass  # 添加pass语句
    """缓存配置类"""

    # 默认TTL（秒）
    default_ttl: int = 3600

    # 各类型数据的TTL配置
    ttl_config: dict[str, int] | None = None

    # 缓存大小限制
    max_size: int = 10000

    # 是否启用压缩
    enable_compression: bool = True

    # 序列化方式
    serializer: str = "json"

    def __post_init__(self):
        """函数文档字符串."""
        # 添加pass语句
        """初始化后处理"""
        if self.ttl_config is None:
            self.ttl_config = {
                "match_processing": 3600,  # 1小时
                "odds_processing": 1800,  # 30分钟
                "features_processing": 7200,  # 2小时
                "validation": 900,  # 15分钟
                "statistics": 1800,  # 30分钟
            }


# 全局缓存配置实例
CACHE_CONFIG = CacheConfig()


def get_cache_ttl(cache_type: str) -> int:
    """获取指定类型的缓存TTL".

    Args:
        cache_type: 缓存类型

    Returns:
        TTL秒数
    """
    if CACHE_CONFIG.ttl_config is None:
        return CACHE_CONFIG.default_ttl
    return CACHE_CONFIG.ttl_config.get(cache_type, CACHE_CONFIG.default_ttl)
