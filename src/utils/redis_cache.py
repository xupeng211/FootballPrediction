"""
真实Redis缓存实现
Real Redis Cache Implementation
"""

import json
import pickle
import redis
from typing import Any, Optional, Union
from .cache_decorators import _generate_cache_key

class RedisCache:
    """Redis缓存客户端"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
        **kwargs
    ):
        """
        初始化Redis客户端

        Args:
            host: Redis主机地址
            port: Redis端口
            db: 数据库编号
            password: 密码
            decode_responses: 是否解码响应
            **kwargs: 其他redis.Redis参数
        """
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses,
            **kwargs
        )
        self.default_ttl = 3600  # 默认1小时

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）

        Returns:
            是否成功
        """
        try:
            # 序列化值
            if not isinstance(value, (str, int, float)):
                value = json.dumps(value, default=str)

            # 设置TTL
            expire_time = ttl or self.default_ttl

            return self.client.setex(key, expire_time, value)
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            缓存值或默认值
        """
        try:
            value = self.client.get(key)
            if value is None:
                return default

            # 尝试反序列化
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            print(f"Redis get error: {e}")
            return default

    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False

    def clear(self) -> bool:
        """清空当前数据库"""
        try:
            return self.client.flushdb()
        except Exception as e:
            print(f"Redis clear error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            print(f"Redis exists error: {e}")
            return False

    def ttl(self, key: str) -> int:
        """获取键的剩余生存时间"""
        try:
            return self.client.ttl(key)
        except Exception as e:
            print(f"Redis TTL error: {e}")
            return -1

    def keys(self, pattern: str = "*") -> list:
        """获取匹配模式的所有键"""
        try:
            return self.client.keys(pattern)
        except Exception as e:
            print(f"Redis keys error: {e}")
            return []

    def info(self) -> dict:
        """获取Redis信息"""
        try:
            return self.client.info()
        except Exception as e:
            print(f"Redis info error: {e}")
            return {}

    def ping(self) -> bool:
        """测试Redis连接"""
        try:
            return self.client.ping()
        except Exception as e:
            print(f"Redis ping error: {e}")
            return False

# 全局Redis实例
_redis_cache: Optional[RedisCache] = None

def get_redis_client(**kwargs) -> RedisCache:
    """获取Redis客户端（单例模式）"""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache(**kwargs)
    return _redis_cache

def redis_cache_decorator(key_prefix: str = "", ttl: int = 3600):
    """
    Redis缓存装饰器

    Args:
        key_prefix: 键前缀
        ttl: 生存时间
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 获取Redis客户端
            redis_client = get_redis_client()

            # 检查连接
            if not redis_client.ping():
                print("Redis不可用，直接执行函数")
                return func(*args, **kwargs)

            # 生成缓存键
            cache_key = f"{key_prefix}:{_generate_cache_key(func.__name__, args, kwargs)}"

            # 尝试从缓存获取
            cached_value = redis_client.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            redis_client.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator

# 使用示例
if __name__ == "__main__":
    # 测试Redis连接
    redis = get_redis_client()

    if redis.ping():
        print("✅ Redis连接成功")

        # 测试基本操作
        redis.set("test:key", {"value": "hello"}, ttl=60)
        value = redis.get("test:key")
        print(f"获取值: {value}")

        # 测试装饰器
        @redis_cache_decorator(prefix="calc", ttl=300)
        def expensive_calculation(x: int) -> int:
            print(f"执行计算: {x} * {x}")
            return x * x

        # 第一次调用
        result1 = expensive_calculation(10)
        print(f"结果: {result1}")

        # 第二次调用（从缓存）
        result2 = expensive_calculation(10)
        print(f"结果: {result2}")

    else:
        print("❌ Redis连接失败")