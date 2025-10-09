"""
测试缓存键管理器
"""

import pytest

from src.cache.redis.core.key_manager import CacheKeyManager


class TestCacheKeyManager:
    """测试缓存键管理器"""

    def test_build_key_basic(self):
        """测试基础键构建"""
        key = CacheKeyManager.build_key("match", 123, "features")
        assert key == "match:123:features"

    def test_build_key_with_kwargs(self):
        """测试带额外参数的键构建"""
        key = CacheKeyManager.build_key("team", 1, "stats", type="recent")
        assert key == "team:1:stats:type:recent"

    def test_build_key_with_none(self):
        """测试包含None值的键构建"""
        key = CacheKeyManager.build_key("match", None, 123, "", "features")
        assert key == "match:123:features"

    def test_build_key_with_zero(self):
        """测试包含0值的键构建"""
        key = CacheKeyManager.build_key("match", 0, "features")
        assert key == "match:0:features"

    def test_build_key_unknown_prefix(self):
        """测试未知前缀的键构建"""
        key = CacheKeyManager.build_key("unknown", 123, "features")
        assert key == "unknown:123:features"

    def test_get_ttl(self):
        """测试获取TTL"""
        assert CacheKeyManager.get_ttl("match_info") == 3600
        assert CacheKeyManager.get_ttl("odds_data") == 900
        assert CacheKeyManager.get_ttl("default") == 3600
        assert CacheKeyManager.get_ttl("unknown") == 3600

    def test_match_features_key(self):
        """测试比赛特征键"""
        key = CacheKeyManager.match_features_key(123)
        assert key == "match:123:features"

    def test_team_stats_key(self):
        """测试球队统计键"""
        key = CacheKeyManager.team_stats_key(1, "recent")
        assert key == "team:1:stats:type:recent"

    def test_odds_key(self):
        """测试赔率键"""
        key = CacheKeyManager.odds_key(123, "all")
        assert key == "odds:123:all"

    def test_prediction_key(self):
        """测试预测结果键"""
        key = CacheKeyManager.prediction_key(123, "latest")
        assert key == "predictions:123:latest"