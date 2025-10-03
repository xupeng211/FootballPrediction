"""
缓存配置模块
Cache Configuration Module

提供缓存相关的配置管理
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass
from src.cache.optimization import CacheConfig, CacheLevel, EvictionPolicy


@dataclass
class CacheSettings:
    """缓存设置"""

    # 基础配置
    enabled: bool = True
    default_ttl: int = 300  # 5分钟

    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = None
    redis_max_connections: int = 10

    # 内存缓存配置
    memory_cache_size: int = 1000
    memory_cache_ttl: int = 300

    # 多级缓存配置
    l2_cache_ttl: int = 1800  # 30分钟
    l2_max_memory: str = "100mb"

    # 预热配置
    preload_enabled: bool = True
    preload_batch_size: int = 100

    # 监控配置
    metrics_enabled: bool = True
    stats_interval: int = 60

    # 特定路径缓存配置
    path_configs: Dict[str, Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.path_configs is None:
            self.path_configs = {
                # 健康检查 - 短缓存
                "/health": {
                    "ttl": 30,
                    "enabled": True
                },
                # 预测API - 中等缓存
                "/api/v1/predictions": {
                    "ttl": 600,
                    "enabled": True
                },
                # 数据API - 长缓存
                "/api/v1/data": {
                    "ttl": 1800,
                    "enabled": True
                },
                # 特征数据 - 长缓存
                "/api/v1/features": {
                    "ttl": 3600,
                    "enabled": True
                },
                # 监控API - 短缓存
                "/api/v1/monitoring": {
                    "ttl": 60,
                    "enabled": True
                }
            }


class CacheConfigManager:
    """缓存配置管理器"""

    def __init__(self):
        self.settings = self._load_settings()

    def _load_settings(self) -> CacheSettings:
        """从环境变量加载设置"""
        return CacheSettings(
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "300")),

            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            redis_max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),

            memory_cache_size=int(os.getenv("MEMORY_CACHE_SIZE", "1000")),
            memory_cache_ttl=int(os.getenv("MEMORY_CACHE_TTL", "300")),

            l2_cache_ttl=int(os.getenv("L2_CACHE_TTL", "1800")),
            l2_max_memory=os.getenv("L2_MAX_MEMORY", "100mb"),

            preload_enabled=os.getenv("CACHE_PRELOAD_ENABLED", "true").lower() == "true",
            preload_batch_size=int(os.getenv("CACHE_PRELOAD_BATCH_SIZE", "100")),

            metrics_enabled=os.getenv("CACHE_METRICS_ENABLED", "true").lower() == "true",
            stats_interval=int(os.getenv("CACHE_STATS_INTERVAL", "60"))
        )

    def get_cache_config(self) -> CacheConfig:
        """获取缓存配置对象"""
        return CacheConfig(
            l1_max_size=self.settings.memory_cache_size,
            l1_ttl=self.settings.memory_cache_ttl,
            l2_ttl=self.settings.l2_cache_ttl,
            l2_max_memory=self.settings.l2_max_memory,
            preload_batch_size=self.settings.preload_batch_size,
            metrics_enabled=self.settings.metrics_enabled,
            stats_interval=self.settings.stats_interval
        )

    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置"""
        config = {
            "host": self.settings.redis_host,
            "port": self.settings.redis_port,
            "db": self.settings.redis_db,
            "max_connections": self.settings.redis_max_connections,
            "decode_responses": True,
            "retry_on_timeout": True,
            "socket_keepalive": True,
            "socket_keepalive_options": {},
            "health_check_interval": 30
        }

        if self.settings.redis_password:
            config["password"] = self.settings.redis_password

        return config

    def get_path_ttl(self, path: str) -> int:
        """获取特定路径的TTL"""
        # 精确匹配
        if path in self.settings.path_configs:
            config = self.settings.path_configs[path]
            if config.get("enabled", True):
                return config.get("ttl", self.settings.default_ttl)

        # 前缀匹配
        for path_pattern, config in self.settings.path_configs.items():
            if path.startswith(path_pattern):
                if config.get("enabled", True):
                    return config.get("ttl", self.settings.default_ttl)

        return self.settings.default_ttl

    def is_path_cacheable(self, path: str) -> bool:
        """检查路径是否可缓存"""
        # 精确匹配
        if path in self.settings.path_configs:
            return self.settings.path_configs[path].get("enabled", True)

        # 前缀匹配
        for path_pattern, config in self.settings.path_configs.items():
            if path.startswith(path_pattern):
                return config.get("enabled", True)

        return self.settings.enabled

    def get_preload_keys(self) -> List[str]:
        """获取预热的键列表"""
        # 这里应该从数据库或配置文件加载
        # 示例实现
        keys = []

        if self.settings.preload_enabled:
            # 预热热门比赛
            keys.extend([
                "predictions:upcoming:limit_10",
                "predictions:high_confidence:today",
                "teams:popular",
                "matches:today",
                "features:latest"
            ])

        return keys


# 全局配置管理器实例
_cache_config_manager: CacheConfigManager = None


def get_cache_config_manager() -> CacheConfigManager:
    """获取全局缓存配置管理器"""
    global _cache_config_manager
    if _cache_config_manager is None:
        _cache_config_manager = CacheConfigManager()
    return _cache_config_manager


def init_cache_config() -> CacheConfigManager:
    """初始化缓存配置管理器"""
    global _cache_config_manager
    _cache_config_manager = CacheConfigManager()
    return _cache_config_manager