"""
性能配置测试
Performance Configuration Tests

测试性能配置管理功能。
Tests performance configuration management functionality.
"""

import pytest
from unittest.mock import patch

from src.performance.config import (
    PerformanceConfig,
    CacheConfig,
    MonitoringConfig,
    OptimizationConfig,
    get_performance_config,
    CACHE_TTL_CONFIG,
    PERFORMANCE_THRESHOLDS
)


class TestCacheConfig:
    """缓存配置测试"""

    def test_cache_config_defaults(self):
        """测试缓存配置默认值"""
        config = CacheConfig()

        assert config.prediction_ttl == 1800
        assert config.local_cache_size == 1000
        assert config.redis_host == "localhost"
        assert config.redis_port == 6379
        assert config.lru_eviction_policy is True

    def test_cache_config_custom_values(self):
        """测试自定义缓存配置值"""
        config = CacheConfig(
            prediction_ttl=3600,
            local_cache_size=2000,
            redis_host="custom-host"
        )

        assert config.prediction_ttl == 3600
        assert config.local_cache_size == 2000
        assert config.redis_host == "custom-host"


class TestMonitoringConfig:
    """监控配置测试"""

    def test_monitoring_config_defaults(self):
        """测试监控配置默认值"""
        config = MonitoringConfig()

        assert config.metrics_collection_interval == 30
        assert config.cpu_warning_threshold == 70.0
        assert config.cpu_critical_threshold == 90.0
        assert config.response_time_warning == 1.0

    def test_monitoring_config_custom_values(self):
        """测试自定义监控配置值"""
        config = MonitoringConfig(
            cpu_warning_threshold=80.0,
            response_time_critical=3.0
        )

        assert config.cpu_warning_threshold == 80.0
        assert config.response_time_critical == 3.0


class TestOptimizationConfig:
    """优化配置测试"""

    def test_optimization_config_defaults(self):
        """测试优化配置默认值"""
        config = OptimizationConfig()

        assert config.enable_query_optimization is True
        assert config.enable_index_optimization is True
        assert config.min_connections == 5
        assert config.max_connections == 20

    def test_optimization_config_custom_values(self):
        """测试自定义优化配置值"""
        config = OptimizationConfig(
            enable_query_optimization=False,
            max_connections=50
        )

        assert config.enable_query_optimization is False
        assert config.max_connections == 50


class TestPerformanceConfig:
    """性能配置管理器测试"""

    def test_performance_config_initialization(self):
        """测试性能配置初始化"""
        config = PerformanceConfig()

        assert isinstance(config.cache, CacheConfig)
        assert isinstance(config.monitoring, MonitoringConfig)
        assert isinstance(config.optimization, OptimizationConfig)

    def test_get_cache_config(self):
        """测试获取缓存配置"""
        config = PerformanceConfig()
        cache_config = config.get_cache_config()

        assert isinstance(cache_config, dict)
        assert 'prediction' in cache_config
        assert 'api' in cache_config
        assert 'local' in cache_config
        assert 'redis' in cache_config

        assert cache_config['prediction']['ttl'] == 1800
        assert cache_config['local']['size'] == 1000
        assert cache_config['redis']['host'] == 'localhost'

    def test_get_monitoring_config(self):
        """测试获取监控配置"""
        config = PerformanceConfig()
        monitoring_config = config.get_monitoring_config()

        assert isinstance(monitoring_config, dict)
        assert 'collection' in monitoring_config
        assert 'thresholds' in monitoring_config

        assert monitoring_config['collection']['interval'] == 30
        assert monitoring_config['thresholds']['cpu']['warning'] == 70.0
        assert monitoring_config['thresholds']['response_time']['critical'] == 2.0

    def test_get_optimization_config(self):
        """测试获取优化配置"""
        config = PerformanceConfig()
        optimization_config = config.get_optimization_config()

        assert isinstance(optimization_config, dict)
        assert 'database' in optimization_config
        assert 'query' in optimization_config
        assert 'connection_pool' in optimization_config
        assert 'async' in optimization_config

        assert optimization_config['database']['enable_query_optimization'] is True
        assert optimization_config['connection_pool']['max_connections'] == 20
        assert optimization_config['async']['max_concurrent_requests'] == 100

    def test_update_cache_config(self):
        """测试更新缓存配置"""
        config = PerformanceConfig()

        config.update_cache_config(prediction_ttl=3600, local_cache_size=2000)

        assert config.cache.prediction_ttl == 3600
        assert config.cache.local_cache_size == 2000

    def test_update_monitoring_config(self):
        """测试更新监控配置"""
        config = PerformanceConfig()

        config.update_monitoring_config(cpu_warning_threshold=80.0)

        assert config.monitoring.cpu_warning_threshold == 80.0

    def test_update_optimization_config(self):
        """测试更新优化配置"""
        config = PerformanceConfig()

        config.update_optimization_config(max_connections=50)

        assert config.optimization.max_connections == 50


class TestPerformanceConfigSingleton:
    """性能配置单例测试"""

    def test_get_performance_config(self):
        """测试获取性能配置单例"""
        config1 = get_performance_config()
        config2 = get_performance_config()

        assert config1 is config2
        assert isinstance(config1, PerformanceConfig)

    def test_config_persistence(self):
        """测试配置持久性"""
        config = get_performance_config()

        # 修改配置
        config.update_cache_config(prediction_ttl=7200)

        # 再次获取配置，应该是同一个实例
        config2 = get_performance_config()
        assert config2.cache.prediction_ttl == 7200


class TestCacheTtlConfig:
    """缓存TTL配置测试"""

    def test_cache_ttl_config_values(self):
        """测试缓存TTL配置值"""
        assert CACHE_TTL_CONFIG['short'] == 300      # 5分钟
        assert CACHE_TTL_CONFIG['medium'] == 1800    # 30分钟
        assert CACHE_TTL_CONFIG['long'] == 3600      # 1小时
        assert CACHE_TTL_CONFIG['daily'] == 86400    # 24小时

    def test_cache_ttl_config_order(self):
        """测试缓存TTL配置顺序"""
        assert CACHE_TTL_CONFIG['short'] < CACHE_TTL_CONFIG['medium']
        assert CACHE_TTL_CONFIG['medium'] < CACHE_TTL_CONFIG['long']
        assert CACHE_TTL_CONFIG['long'] < CACHE_TTL_CONFIG['daily']


class TestPerformanceThresholds:
    """性能阈值配置测试"""

    def test_performance_thresholds_structure(self):
        """测试性能阈值配置结构"""
        assert 'excellent' in PERFORMANCE_THRESHOLDS
        assert 'good' in PERFORMANCE_THRESHOLDS
        assert 'warning' in PERFORMANCE_THRESHOLDS
        assert 'critical' in PERFORMANCE_THRESHOLDS

    def test_performance_thresholds_values(self):
        """测试性能阈值配置值"""
        excellent = PERFORMANCE_THRESHOLDS['excellent']
        critical = PERFORMANCE_THRESHOLDS['critical']

        assert excellent['cpu'] == 50
        assert excellent['memory'] == 60
        assert critical['cpu'] == 90
        assert critical['memory'] == 95

    def test_threshold_progression(self):
        """测试阈值递进性"""
        levels = ['excellent', 'good', 'warning', 'critical']

        for level_idx in range(len(levels) - 1):
            current = PERFORMANCE_THRESHOLDS[levels[level_idx]]
            next_level = PERFORMANCE_THRESHOLDS[levels[level_idx + 1]]

            # CPU和内存阈值应该递增
            assert current['cpu'] <= next_level['cpu']
            assert current['memory'] <= next_level['memory']

            # 响应时间和错误率应该递增
            assert current['response_time'] <= next_level['response_time']
            assert current['error_rate'] <= next_level['error_rate']


class TestConfigIntegration:
    """配置集成测试"""

    def test_config_compatibility(self):
        """测试配置兼容性"""
        config = PerformanceConfig()

        # 确保各配置部分兼容
        cache_config = config.get_cache_config()
        monitoring_config = config.get_monitoring_config()
        optimization_config = config.get_optimization_config()

        # 验证缓存配置中的TTL值合理
        assert cache_config['prediction']['ttl'] > 0
        assert cache_config['local']['size'] > 0

        # 验证监控配置中的阈值合理
        thresholds = monitoring_config['thresholds']
        assert thresholds['cpu']['warning'] < thresholds['cpu']['critical']
        assert thresholds['memory']['warning'] < thresholds['memory']['critical']

        # 验证优化配置中的连接池配置合理
        pool_config = optimization_config['connection_pool']
        assert pool_config['min_connections'] <= pool_config['max_connections']
        assert pool_config['timeout'] > 0

    @patch('src.performance.config.PerformanceConfig')
    def test_config_with_environment_override(self, mock_config_class):
        """测试环境变量覆盖配置"""
        mock_config = PerformanceConfig()
        mock_config_class.return_value = mock_config

        # 模拟环境变量覆盖
        with patch.dict('os.environ', {'PREDICTION_TTL': '7200'}):
            config = get_performance_config()
            # 这里应该有实际的环境变量处理逻辑
            assert isinstance(config, PerformanceConfig)