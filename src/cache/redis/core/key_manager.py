"""
Redis key manager
"""

from typing import Optional, List
import hashlib
import json


class RedisKeyManager:
    """管理Redis键的类"""

    def __init__(self, prefix: str = "fp"):
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
        return hashlib.md5(json_str.encode()).hexdigest()

    def pattern_match(self, pattern: str) -> str:
        """生成模式匹配键"""
        return self._make_key(pattern)

    def get_all_keys(self, pattern: str = "*") -> str:
        """获取所有匹配的键"""
        return self._make_key(pattern)
