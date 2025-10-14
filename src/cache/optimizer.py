from typing import Any, Dict, List, Optional, Union
"""
Redis缓存优化器
提供缓存策略、性能优化和监控功能
"""

import asyncio
import json
import time
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import aioredis
from aioredis import Redis
from functools import wraps
import hashlib
import pickle
import zlib
from datetime import datetime, timedelta

from src.core.logging import get_logger
from src.core.config import get_settings

logger = get_logger(__name__)


class CacheStrategy(Enum):
    """缓存策略枚举"""
    LRU = "lru"
    LFU = "lfu"
    RANDOM = "random"
    TTL = "ttl"
    NOEVICTION = "noeviction"


@dataclass
class CacheMetrics:
    """缓存指标"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    avg_response_time: float = 0.0
    memory_usage: int = 0
    total_keys: int = 0
    expired_keys: int = 0
    evicted_keys: int = 0

    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """未命中率"""
        return 1.0 - self.hit_rate


class CacheOptimizer:
    """Redis缓存优化器"""

    def __init__(self):
        self.settings = get_settings()
        self.redis: Optional[Redis] = None
        self.metrics = CacheMetrics()
        self.key_patterns = {}
        self.compression_threshold = 1024  # 1KB以上启用压缩
        self.default_ttl = 3600  # 默认1小时

    async def initialize(self):
        """初始化Redis连接"""
        try:
            self.redis = Redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )

            # 测试连接
            await self.redis.ping()
            logger.info("Redis连接成功")

            # 初始化监控
            await self._setup_monitoring()

        except Exception as e:
            logger.error("Redis连接失败", error=str(e))
            raise

    async def _setup_monitoring(self):
        """设置监控任务"""
        asyncio.create_task(self._collect_metrics())

    async def _collect_metrics(self):
        """定期收集指标"""
        while True:
            try:
                if self.redis:
                    # 获取Redis信息
                    info = await self.redis.info()

                    # 更新指标
                    self.metrics.memory_usage = info.get('used_memory', 0)
                    self.metrics.total_keys = info.get('db0', {}).get('keys', 0)
                    self.metrics.expired_keys = info.get('expired_keys', 0)
                    self.metrics.evicted_keys = info.get('evicted_keys', 0)

                # 每30秒收集一次
                await asyncio.sleep(30)

            except Exception as e:
                logger.error("收集指标失败", error=str(e))
                await asyncio.sleep(30)

    def get_cache_key(self, prefix: str, key: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 组合键名
        if args or kwargs:
            # 对参数进行序列化
            params = str(args) + str(sorted(kwargs.items()))
            params_hash = hashlib.md5(params.encode()).hexdigest()[:8]
            cache_key = f"{prefix}:{key}:{params_hash}"
        else:
            cache_key = f"{prefix}:{key}"

        # 记录键模式
        if prefix not in self.key_patterns:
            self.key_patterns[prefix] = 0
        self.key_patterns[prefix] += 1

        return cache_key

    async def get(
        self,
        key: str,
        default: Any = None,
        use_compression: bool = True
    ) -> Any:
        """获取缓存值"""
        start_time = time.time()

        try:
            value = await self.redis.get(key)

            if value is not None:
                self.metrics.hits += 1

                # 解压缩（如果需要）
                if use_compression and value.startswith('COMPRESSED:'):
                    value = await self._decompress(value[11:])

                # 反序列化
                if value.startswith('JSON:'):
                    return json.loads(value[5:])
                elif value.startswith('PICKLE:'):
                    return pickle.loads(value[7:])
                else:
                    return value
            else:
                self.metrics.misses += 1
                return default

        except Exception as e:
            self.metrics.errors += 1
            logger.error("缓存获取失败", key=key, error=str(e))
            return default

        finally:
            # 更新平均响应时间
            duration = time.time() - start_time
            self.metrics.avg_response_time = (
                (self.metrics.avg_response_time * (self.metrics.hits + self.metrics.misses - 1) + duration)
                / (self.metrics.hits + self.metrics.misses)
            )

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        use_compression: bool = True,
        serialize: str = 'json'
    ) -> bool:
        """设置缓存值"""
        try:
            self.metrics.sets += 1

            # 序列化值
            if serialize == 'json':
                serialized = 'JSON:' + json.dumps(value, default=str)
            elif serialize == 'pickle':
                serialized = 'PICKLE:' + pickle.dumps(value).hex()
            else:
                serialized = str(value)

            # 压缩（如果需要）
            if use_compression and len(serialized) > self.compression_threshold:
                serialized = 'COMPRESSED:' + await self._compress(serialized)

            # 设置缓存
            if ttl:
                return await self.redis.setex(key, ttl, serialized)
            else:
                return await self.redis.set(key, serialized)

        except Exception as e:
            self.metrics.errors += 1
            logger.error("缓存设置失败", key=key, error=str(e))
            return False

    async def delete(self, *keys: str) -> int:
        """删除缓存键"""
        try:
            self.metrics.deletes += 1
            return await self.redis.delete(*keys)
        except Exception as e:
            self.metrics.errors += 1
            logger.error("缓存删除失败", keys=keys, error=str(e))
            return 0

    async def delete_pattern(self, pattern: str) -> int:
        """根据模式删除缓存键"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.delete(*keys)
            return 0
        except Exception as e:
            logger.error("模式删除失败", pattern=pattern, error=str(e))
            return 0

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error("检查键存在失败", key=key, error=str(e))
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """设置键过期时间"""
        try:
            return await self.redis.expire(key, ttl)
        except Exception as e:
            logger.error("设置过期时间失败", key=key, error=str(e))
            return False

    async def ttl(self, key: str) -> int:
        """获取键剩余时间"""
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error("获取TTL失败", key=key, error=str(e))
            return -1

    async def increment(self, key: str, amount: int = 1) -> int:
        """递增计数器"""
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error("递增失败", key=key, error=str(e))
            return 0

    async def increment_float(self, key: str, amount: float = 1.0) -> float:
        """递增浮点计数器"""
        try:
            return await self.redis.incrbyfloat(key, amount)
        except Exception as e:
            logger.error("递增浮点失败", key=key, error=str(e))
            return 0.0

    async def get_memory_usage(self, key: str) -> int:
        """获取键的内存使用"""
        try:
            return await self.redis.memory_usage(key)
        except Exception as e:
            logger.error("获取内存使用失败", key=key, error=str(e))
            return 0

    async def optimize_memory(self) -> Dict[str, Any]:
        """优化内存使用"""
        logger.info("开始优化Redis内存...")

        results = {
            'actions': [],
            'memory_freed': 0
        }

        try:
            # 1. 清理过期键
            expired_count = await self.delete_pattern('*:*:*EXPIRED*')
            if expired_count > 0:
                results['actions'].append(f"清理了 {expired_count} 个过期键")

            # 2. 压缩大键
            big_keys = await self._find_big_keys(min_size=10240)  # 10KB以上
            for key_info in big_keys:
                key = key_info['key']
                value = await self.get(key, use_compression=False)
                if value is not None:
                    # 重新设置并启用压缩
                    await self.set(key, value, use_compression=True)
                    results['actions'].append(f"压缩大键: {key}")

            # 3. 执行内存碎片整理
            if self.redis:
                await self.redis.command("MEMORY PURGE")
                results['actions'].append("执行内存碎片整理")

            # 4. 更新内存策略
            info = await self.redis.info()
            memory_usage = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)

            if max_memory > 0:
                usage_rate = memory_usage / max_memory
                if usage_rate > 0.9:
                    # 内存使用率过高，建议调整策略
                    results['actions'].append("内存使用率过高，建议增加max_memory或调整淘汰策略")

            logger.info("内存优化完成", actions=results['actions'])
            return results

        except Exception as e:
            logger.error("内存优化失败", error=str(e))
            return results

    async def _find_big_keys(self, min_size: int = 10240) -> List[Dict[str, Any]:
        """查找大键"""
        big_keys = []
        cursor = 0

        while True:
            try:
                cursor, keys = await self.redis.scan(cursor, match="*", count=100)

                for key in keys:
                    memory_usage = await self.get_memory_usage(key)
                    if memory_usage >= min_size:
                        big_keys.append({
                            'key': key,
                            'size': memory_usage,
                            'type': await self.redis.type(key)
                        })

                if cursor == 0:
                    break

            except Exception as e:
                logger.error("扫描大键失败", error=str(e))
                break

        return big_keys

    async def _compress(self, data: str) -> str:
        """压缩数据"""
        compressed = zlib.compress(data.encode())
        return compressed.hex()

    async def _decompress(self, hex_data: str) -> str:
        """解压缩数据"""
        compressed = bytes.fromhex(hex_data)
        decompressed = zlib.decompress(compressed)
        return decompressed.decode()

    async def get_slow_log(self, count: int = 10) -> List[Dict[str, Any]:
        """获取慢查询日志"""
        try:
            slow_log = await self.redis.slowlog_get(count)
            return [
                {
                    'id': entry[0],
                    'timestamp': datetime.fromtimestamp(entry[1]).isoformat(),
                    'duration': entry[2],
                    'command': ' '.join(entry[3])
                }
                for entry in slow_log
            ]
        except Exception as e:
            logger.error("获取慢查询日志失败", error=str(e))
            return []

    async def analyze_key_patterns(self) -> Dict[str, Any]:
        """分析键模式"""
        analysis = {
            'total_patterns': len(self.key_patterns),
            'patterns': {}
        }

        # 统计各模式的使用情况
        for pattern, count in self.key_patterns.items():
            # 获取该模式下的键数量
            keys = await self.redis.keys(f"{pattern}:*")
            analysis['patterns'][pattern] = {
                'access_count': count,
                'key_count': len(keys),
                'memory_usage': 0
            }

            # 计算内存使用
            for key in keys[:100]:  # 只计算前100个键避免耗时过长
                analysis['patterns'][pattern]['memory_usage'] += await self.get_memory_usage(key)

        return analysis

    async def cache_warmup(self, warmup_data: Dict[str, Any]):
        """缓存预热"""
        logger.info("开始缓存预热...")

        success_count = 0
        total_count = len(warmup_data)

        for key, value in warmup_data.items():
            try:
                await self.set(key, value, ttl=self.default_ttl)
                success_count += 1
            except Exception as e:
                logger.error("预热失败", key=key, error=str(e))

        logger.info(f"缓存预热完成: {success_count}/{total_count}")
        return {
            'success': success_count,
            'total': total_count,
            'success_rate': success_count / total_count if total_count > 0 else 0
        }

    async def flush_db(self) -> bool:
        """清空数据库（谨慎使用）"""
        logger.warning("准备清空Redis数据库")
        try:
            await self.redis.flushdb()
            logger.warning("Redis数据库已清空")
            return True
        except Exception as e:
            logger.error("清空数据库失败", error=str(e))
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """获取缓存指标"""
        return {
            **asdict(self.metrics),
            'hit_rate_percent': self.metrics.hit_rate * 100,
            'key_patterns': dict[str, Any](sorted(self.key_patterns.items(), key=lambda x: x[1], reverse=True))
        }

    async def close(self):
        """关闭连接"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis连接已关闭")


# 全局缓存优化器实例
cache_optimizer = CacheOptimizer()


# 缓存装饰器
def cache_result(
    prefix: str,
    ttl: int = 3600,
    use_compression: bool = True,
    serialize: str = 'json',
    key_func: Callable = None
):
    """缓存结果装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_optimizer.get_cache_key(
                    prefix,
                    func.__name__,
                    *args,
                    **kwargs
                )

            # 尝试从缓存获取
            cached = await cache_optimizer.get(cache_key)
            if cached is not None:
                return cached

            # 执行函数
            result = await func(*args, **kwargs)

            # 缓存结果
            await cache_optimizer.set(cache_key, result, ttl=ttl, use_compression=use_compression, serialize=serialize)

            return result

        return wrapper
    return decorator


# 分布式锁装饰器
def distributed_lock(
    lock_name: str,
    timeout: int = 10,
    retry_delay: float = 0.1
):
    """分布式锁装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            lock_key = f"lock:{lock_name}"
            lock_value = str(time.time())

            # 获取锁
            acquired = await cache_optimizer.redis.set(lock_key, lock_value, nx=True, ex=timeout)
            if not acquired:
                # 等待并重试
                retries = int(timeout / retry_delay)
                for _ in range(retries):
                    await asyncio.sleep(retry_delay)
                    acquired = await cache_optimizer.redis.set(lock_key, lock_value, nx=True, ex=timeout)
                    if acquired:
                        break

                if not acquired:
                    raise TimeoutError(f"无法获取分布式锁: {lock_name}")

            try:
                # 执行函数
                return await func(*args, **kwargs)
            finally:
                # 释放锁
                await cache_optimizer.delete(lock_key)

        return wrapper
    return decorator
