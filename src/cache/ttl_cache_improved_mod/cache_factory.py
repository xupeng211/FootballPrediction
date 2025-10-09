"""

"""




    """缓存工厂类

    """

        """



        """

        """


        """

        """


        """

        """


        """

        """


        """

        """

        """

        """

        """

        """

        """

        """

        """

        """

        """

        """

        """

        """

        """


缓存工厂类
Cache Factory
提供创建不同类型缓存的工厂方法。
Provides factory methods for creating different types of caches.
class CacheFactory:
    提供创建不同类型缓存的静态方法。
    Provides static methods for creating different types of caches.
    @staticmethod
    def create_cache(
        cache_type: str = "sync",
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        cleanup_interval: float = 60.0,
    ) -> Union[TTLCache, AsyncTTLCache]:
        创建缓存实例
        Args:
            cache_type: 缓存类型 ('sync' 或 'async')
            max_size: 最大缓存项数
            default_ttl: 默认TTL（秒）
            cleanup_interval: 清理间隔（秒）
        Returns:
            Union[TTLCache, AsyncTTLCache]: 缓存实例
        Raises:
            ValueError: 当cache_type不支持时
        if cache_type == "async":
            return AsyncTTLCache(max_size, default_ttl, cleanup_interval)
        elif cache_type == "sync":
            return TTLCache(max_size, default_ttl, cleanup_interval)
        else:
            raise ValueError(f"不支持的缓存类型: {cache_type}")
    @staticmethod
    def create_lru_cache(max_size: int = 128) -> TTLCache:
        创建LRU缓存
        Args:
            max_size: 最大缓存项数
        Returns:
            TTLCache: LRU缓存实例
        return TTLCache(max_size=max_size)
    @staticmethod
    def create_ttl_cache(
        max_size: int = 1000,
        default_ttl: float = 3600,
    ) -> TTLCache:
        创建TTL缓存
        Args:
            max_size: 最大缓存项数
            default_ttl: 默认TTL（秒）
        Returns:
            TTLCache: TTL缓存实例
        return TTLCache(max_size=max_size, default_ttl=default_ttl)
    @staticmethod
    def create_async_lru_cache(max_size: int = 128) -> AsyncTTLCache:
        创建异步LRU缓存
        Args:
            max_size: 最大缓存项数
        Returns:
            AsyncTTLCache: 异步LRU缓存实例
        return AsyncTTLCache(max_size=max_size)
    @staticmethod
    def create_async_ttl_cache(
        max_size: int = 1000,
        default_ttl: float = 3600,
    ) -> AsyncTTLCache:
        创建异步TTL缓存
        Args:
            max_size: 最大缓存项数
            default_ttl: 默认TTL（秒）
        Returns:
            AsyncTTLCache: 异步TTL缓存实例
        return AsyncTTLCache(max_size=max_size, default_ttl=default_ttl)
    @staticmethod
    def create_prediction_cache() -> TTLCache:
        创建预测缓存（预设配置）
        Returns:
            TTLCache: 预测缓存实例
        return TTLCache(max_size=10000, default_ttl=1800)  # 30分钟
    @staticmethod
    def create_feature_cache() -> TTLCache:
        创建特征缓存（预设配置）
        Returns:
            TTLCache: 特征缓存实例
        return TTLCache(max_size=5000, default_ttl=3600)  # 1小时
    @staticmethod
    def create_odds_cache() -> TTLCache:
        创建赔率缓存（预设配置）
        Returns:
            TTLCache: 赔率缓存实例
        return TTLCache(max_size=20000, default_ttl=300)  # 5分钟
    @staticmethod
    def create_session_cache() -> TTLCache:
        创建会话缓存（预设配置）
        Returns:
            TTLCache: 会话缓存实例
        return TTLCache(max_size=1000, default_ttl=7200)  # 2小时
    @staticmethod
    def create_config_cache() -> TTLCache:
        创建配置缓存（预设配置）
        Returns:
            TTLCache: 配置缓存实例
        return TTLCache(max_size=500, default_ttl=86400)  # 24小时
    @staticmethod
    def get_available_types() -> list:
        获取可用的缓存类型
        Returns:
            list: 缓存类型列表
        return ["sync", "async"]
    @staticmethod
    def get_preset_configs() -> dict:
        获取预设配置
        Returns:
            dict: 预设配置字典
        return {
            "prediction": {"max_size": 10000, "default_ttl": 1800},
            "feature": {"max_size": 5000, "default_ttl": 3600}, Union
            "odds": {"max_size": 20000, "default_ttl": 300},
            "session": {"max_size": 1000, "default_ttl": 7200},
            "config": {"max_size": 500, "default_ttl": 86400},
        }