# TODO: Consider creating a fixture for 5 repeated Mock creations

# TODO: Consider creating a fixture for 5 repeated Mock creations

import sys
from unittest.mock import MagicMock

import redis.asyncio

"""
Redis Mocks for Testing

提供Redis相关的Mock实现，解决版本兼容性问题
"""


# 创建所有必要的Redis mock类
class RedisStub:
    """Redis基础类的Mock"""

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


class RedisClusterStub(RedisStub):
    """Redis集群的Mock"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SentinelStub:
    """Redis哨兵的Mock"""

    def __init__(self, *args, **kwargs):
        pass


class ConnectionPoolStub:
    """连接池的Mock"""

    def __init__(self, *args, **kwargs):
        pass


def install_redis_mocks():
    """
    安装所有Redis相关的Mock到sys.modules
    这需要在导入Feast之前调用
    """

    # 创建所有需要的mock模块
    redis_cluster_mock = MagicMock()
    redis_cluster_mock.RedisCluster = RedisClusterStub
    redis_cluster_mock.ClusterNode = type("ClusterNode", (), {})

    redis_asyncio_cluster_mock = MagicMock()
    redis_asyncio_cluster_mock.RedisCluster = RedisClusterStub

    redis_sentinel_mock = MagicMock()
    redis_sentinel_mock.Sentinel = SentinelStub

    redis_asyncio_sentinel_mock = MagicMock()
    redis_asyncio_sentinel_mock.Sentinel = SentinelStub

    redis_connection_pool_mock = MagicMock()
    redis_connection_pool_mock.ConnectionPool = ConnectionPoolStub

    # 添加到sys.modules
    modules_to_mock = {
        "redis.cluster": redis_cluster_mock,
        "redis.asyncio.cluster": redis_asyncio_cluster_mock,
        "redis.sentinel": redis_sentinel_mock,
        "redis.asyncio.sentinel": redis_asyncio_sentinel_mock,
        "redis.connection_pool": redis_connection_pool_mock,
    }

    for module_name, module_mock in modules_to_mock.items():
        sys.modules[module_name] = module_mock

    # 修补已经存在的redis.asyncio模块
    try:
        if not hasattr(redis.asyncio, "RedisCluster"):
            redis.asyncio.RedisCluster = RedisClusterStub
        if not hasattr(redis.asyncio, "Sentinel"):
            redis.asyncio.Sentinel = SentinelStub
    except ImportError:
        pass


# 自动安装
if "pytest" in sys.modules or "unittest" in sys.modules:
    install_redis_mocks()
