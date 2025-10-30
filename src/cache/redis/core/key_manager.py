"""
Redis key manager
"""

import hashlib
import json
from typing import Optional


class RedisKeyManager:
    """类文档字符串"""
    pass  # 添加pass语句
    """管理Redis键的类"""

    def __init__(self, prefix: str = "fp"):
    """函数文档字符串"""
    pass  # 添加pass语句
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self.prefix}:{key}"

    def cache_key(self, namespace: str, identifier: str) -> str:
        """生成缓存键"""
        return self._make_key(f"cache:{namespace}:{identifier}")

    def session_key(self, session_id: str) -> str:
        """生成会话键"""
        return self._make_key(f"session:{session_id}")

    def rate_limit_key(self, ip: str, window: int) -> str:
        """生成限流键"""
        return self._make_key(f"rate_limit:{ip}:{window}")

    def health_key(self, service: str) -> str:
        """生成健康检查键"""
        return self._make_key(f"health:{service}")

    def metrics_key(self, metric_name: str, timestamp: Optional[int] = None) -> str:
        """生成指标键"""
        if timestamp:
            return self._make_key(f"metrics:{metric_name}:{timestamp}")
        return self._make_key(f"metrics:{metric_name}")

    def generate_hash_key(self, data: dict) -> str:
        """为数据生成哈希键"""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(json_str.encode(), usedforsecurity=False).hexdigest()

    def pattern_match(self, pattern: str) -> str:
        """生成模式匹配键"""
        return self._make_key(pattern)

    def get_all_keys(self, pattern: str = "*") -> str:
        """获取所有匹配的键"""
        return self._make_key(pattern)

    # 静态方法用于构建键
    @staticmethod
    def build_key(*args, **kwargs) -> str:
        """构建键"""
        parts = [str(arg) for arg in args if arg is not None and arg != ""]
        if kwargs:
            for key, value in kwargs.items():
                parts.append(f"{key}:{value}")
        return ":".join(parts)

    @staticmethod
    def get_ttl(key_type: str) -> int:
        """获取TTL"""
        ttl_map = {"match_info": 3600, "odds_data": 900, "default": 3600}
        return ttl_map.get(key_type, 3600)

    @staticmethod
    def match_features_key(match_id: int) -> str:
        """比赛特征键"""
        return f"match:{match_id}:features"

    @staticmethod
    def team_stats_key(team_id: int, stat_type: str) -> str:
        """球队统计键"""
        return f"team:{team_id}:stats:type:{stat_type}"

    @staticmethod
    def odds_key(match_id: int, odds_type: str) -> str:
        """赔率键"""
        return f"odds:{match_id}:{odds_type}"

    @staticmethod
    def prediction_key(match_id: int, version: str) -> str:
        """预测结果键"""
        return f"predictions:{match_id}:{version}"


# 别名以保持向后兼容
CacheKeyManager = RedisKeyManager
