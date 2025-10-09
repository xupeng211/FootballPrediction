"""
缓存键管理器

统一管理缓存Key的命名规则和TTL策略
"""

from typing import Optional


class CacheKeyManager:
    """
    缓存Key命名规范管理器

    统一管理缓存Key的命名规则和TTL策略
    """

    # Key前缀定义
    PREFIXES = {
        "match": "match",
        "team": "team",
        "odds": "odds",
        "features": "features",
        "predictions": "predictions",
        "stats": "stats",
    }

    # TTL配置 (秒) - 优化后的配置
    TTL_CONFIG = {
        "match_info": 3600,  # 比赛信息: 1小时 (提升缓存时间)
        "match_features": 7200,  # 比赛特征: 2小时 (提升缓存时间)
        "team_stats": 14400,  # 球队统计: 4小时 (提升缓存时间)
        "team_features": 7200,  # 球队特征: 2小时 (提升缓存时间)
        "odds_data": 900,  # 赔率数据: 15分钟 (提升缓存时间)
        "predictions": 7200,  # 预测结果: 2小时 (提升缓存时间)
        "historical_stats": 28800,  # 历史统计: 8小时 (大幅提升缓存时间)
        "upcoming_matches": 1800,  # 即将开始的比赛: 30分钟
        "league_table": 3600,  # 联赛积分榜: 1小时
        "team_form": 7200,  # 球队近期状态: 2小时
        "head_to_head": 14400,  # 历史交锋: 4小时
        "model_metrics": 3600,  # 模型指标: 1小时
        "default": 3600,  # 默认: 1小时 (提升默认缓存时间)
    }

    @classmethod
    def build_key(cls, prefix: str, *args, **kwargs) -> str:
        """
        构建缓存Key

        格式: {prefix}:{arg1}:{arg2}...[:additional_info]

        Args:
            prefix: Key前缀
            *args: Key组成部分
            **kwargs: 额外的Key信息

        Returns:
            str: 格式化的Key

        Examples:
            build_key('match', 123, 'features') -> 'match:123:features'
            build_key('team', 1, 'stats', type='recent') -> 'team:1:stats:recent'
        """
        import logging

        logger = logging.getLogger(__name__)

        if prefix not in cls.PREFIXES:
            logger.warning(f"未知的Key前缀: {prefix}")

        # 构建基础Key
        key_parts = [cls.PREFIXES.get(str(prefix), prefix)]
        # 过滤掉None和空字符串，但保留数字0
        key_parts.extend(
            str(arg)
            for arg in args
            if arg is not None and (str(arg).strip() or str(arg) == "0")
        )

        # 添加额外信息
        for k, v in kwargs.items():
            key_parts.append(f"{k}:{v}")

        return ":".join(key_parts)

    @classmethod
    def get_ttl(cls, cache_type: str) -> int:
        """
        获取缓存TTL

        Args:
            cache_type: 缓存类型

        Returns:
            int: TTL秒数
        """
        return cls.TTL_CONFIG.get(str(cache_type), cls.TTL_CONFIG["default"])

    # 常用Key模式定义
    @staticmethod
    def match_features_key(match_id: int) -> str:
        """比赛特征Key: match:{id}:features"""
        return CacheKeyManager.build_key("match", match_id, "features")

    @staticmethod
    def team_stats_key(team_id: int, stats_type: str = "recent") -> str:
        """球队统计Key: team:{id}:stats:{type}"""
        return CacheKeyManager.build_key("team", team_id, "stats", type=stats_type)

    @staticmethod
    def odds_key(match_id: int, bookmaker: str = "all") -> str:
        """赔率Key: odds:{match_id}:{bookmaker}"""
        return CacheKeyManager.build_key("odds", match_id, bookmaker)

    @staticmethod
    def prediction_key(match_id: int, model_version: str = "latest") -> str:
        """预测结果Key: predictions:{match_id}:{model_version}"""
        return CacheKeyManager.build_key("predictions", match_id, model_version)