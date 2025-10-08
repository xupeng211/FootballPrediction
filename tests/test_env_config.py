import os
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, AsyncMock

"""
测试环境配置

提供测试专用的配置和mock管理
"""
# 添加src到Python路径
test_dir = Path(__file__).parent
project_root = test_dir.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


def configure_test_environment() -> Dict[str, Any]:
    """
    配置测试环境

    Returns:
        Dict: 配置信息
    """
    # 设置测试环境变量
    test_env_vars = {
        "TESTING": "true",
        "ENVIRONMENT": "test",
        "MINIMAL_API_MODE": "true",
        "FAST_FAIL": "false",
        "ENABLE_METRICS": "false",
        "METRICS_ENABLED": "false",
        "ENABLED_SERVICES": "[]",
        "DATABASE_URL": "sqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6380/1",  # 不同db
        "FEAST_DISABLE_REDIS": "true",
    }

    # 应用环境变量
    for key, value in test_env_vars.items():
        os.environ.setdefault(key, value)

    return test_env_vars


def mock_redis_cluster() -> None:
    """
    预先Mock Redis集群模块
    解决Redis/Feast版本兼容性问题
    """

    class RedisClusterStub:
        """Redis集群的轻量级Mock实现"""

        def __init__(self, *args, **kwargs):
            pass

        def ping(self):
            return True

        def get(self, key):
            return None

        def set(self, key, value, ex=None):
            return True

        def exists(self, key):
            return False

        def delete(self, key):
            return 0

        def close(self):
            pass

    class ClusterNodeStub:
        """集群节点的轻量级Mock实现"""

        def __init__(self, *args, **kwargs):
            pass

    # 创建并注册mock
    redis_cluster_mock = MagicMock()
    redis_cluster_mock.RedisCluster = RedisClusterStub
    redis_cluster_mock.ClusterNode = ClusterNodeStub

    # 添加到sys.modules，防止导入错误
    sys.modules["redis.cluster"] = redis_cluster_mock

    # 也Mock相关的redis.asyncio模块
    redis_asyncio_mock = MagicMock()
    redis_asyncio_mock.RedisCluster = RedisClusterStub
    sys.modules["redis.asyncio.cluster"] = redis_asyncio_mock


def initialize_test_mocks() -> Dict[str, Any]:
    """
    初始化所有测试用的Mock

    Returns:
        Dict: Mock实例集合
    """
    mocks = {}

    # Mock数据质量监控器

    mock_dqm = MagicMock()
    mock_dqm.generate_quality_report = AsyncMock(
        return_value={
            "overall_status": "healthy",
            "quality_score": 95.0,
            "anomalies": {"count": 0, "items": []},
            "report_time": "2025-10-04T10:00:00",
            "checks": {
                "data_freshness": {"status": "pass", "score": 100},
                "data_completeness": {"status": "pass", "score": 95},
                "data_consistency": {"status": "pass", "score": 90},
            },
        }
    )
    mocks["data_quality_monitor"] = mock_dqm

    # Mock特征存储
    mock_feature_store = MagicMock()
    mock_feature_store.get_online_features = AsyncMock(return_value=None)
    mock_feature_store.get_historical_features = AsyncMock(return_value=None)
    mocks["feature_store"] = mock_feature_store

    return mocks


# 配置和初始化
configure_test_environment()
mock_redis_cluster()
_test_mocks = initialize_test_mocks()
