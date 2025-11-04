#!/usr/bin/env python3
"""
查询缓存实现脚本
Query Caching Implementation Script

实现Redis缓存层，提升查询性能，目标缓存命中率 > 80%。
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from typing import Any, Optional, Union

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.core.config import get_settings
except ImportError:
    # 如果无法导入配置，使用默认值
    class MockSettings:
        def __init__(self):
            self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    def get_settings():
        return MockSettings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryCache:
    """查询缓存管理器"""

    def __init__(self):
        """初始化查询缓存"""
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache = {}  # 内存缓存后备
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }

    async def connect(self):
        """连接Redis"""
        try:
            self.redis_client = redis.Redis.from_url(
                self.settings.redis_url or "redis://localhost:6379",
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # 测试连接
            await self.redis_client.ping()
            logger.info("✅ Redis缓存连接成功")

        except Exception as e:
            logger.warning(f"⚠️ Redis连接失败，将使用内存缓存: {e}")
            self.redis_client = None

    def _generate_cache_key(self, query: str, params: dict[str, Any] = None) -> str:
        """生成缓存键"""
        key_data = f"{query}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, cache_key: str) -> Optional[Any]:
        """获取缓存值"""
        # 尝试从Redis获取
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    self.cache_stats['hits'] += 1
                    return json.loads(cached_data)
            except Exception as e:
                logger.error(f"❌ Redis获取缓存失败: {e}")

        # 从内存缓存获取
        if cache_key in self.memory_cache:
            self.cache_stats['hits'] += 1
            return self.memory_cache[cache_key]

        self.cache_stats['misses'] += 1
        return None

    async def set(self, cache_key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存值"""
        # 尝试设置到Redis
        redis_success = False
        if self.redis_client:
            try:
                cached_data = json.dumps(value, default=str)
                await self.redis_client.setex(cache_key, ttl, cached_data)
                redis_success = True
                self.cache_stats['sets'] += 1
            except Exception as e:
                logger.error(f"❌ Redis设置缓存失败: {e}")

        # 设置到内存缓存
        self.memory_cache[cache_key] = value
        if not redis_success:
            self.cache_stats['sets'] += 1

        return True

    async def delete(self, cache_key: str) -> bool:
        """删除缓存"""
        # 尝试从Redis删除
        redis_success = False
        if self.redis_client:
            try:
                await self.redis_client.delete(cache_key)
                redis_success = True
                self.cache_stats['deletes'] += 1
            except Exception as e:
                logger.error(f"❌ Redis删除缓存失败: {e}")

        # 从内存缓存删除
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
            if not redis_success:
                self.cache_stats['deletes'] += 1

        return True

    async def invalidate_pattern(self, pattern: str) -> int:
        """按模式删除缓存"""
        if not self.redis_client:
            return 0

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted_count = await self.redis_client.delete(*keys)
                self.cache_stats['deletes'] += deleted_count
                return deleted_count
            return 0

        except Exception as e:
            logger.error(f"❌ 批量删除缓存失败: {e}")
            return 0

    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        if total_requests == 0:
            return 0.0
        return (self.cache_stats['hits'] / total_requests) * 100

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        hit_rate = self.get_hit_rate()
        return {
            **self.cache_stats,
            'hit_rate': hit_rate,
            'total_requests': self.cache_stats['hits'] + self.cache_stats['misses']
        }

    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()


class CachedUserRepository:
    """带缓存的用户仓储"""

    def __init__(self, user_repository, cache: QueryCache):
        """初始化缓存用户仓储"""
        self.user_repository = user_repository
        self.cache = cache

    async def get_by_email(self, email: str, session: AsyncSession = None) -> Optional[Any]:
        """带缓存的根据邮箱获取用户"""
        cache_key = f"user:email:{email}"

        # 尝试从缓存获取
        cached_user = await self.cache.get(cache_key)
        if cached_user:
            logger.debug(f"📦 缓存命中: user:email:{email}")
            return cached_user

        # 从数据库获取
        user = await self.user_repository.get_by_email(email, session)
        if user:
            # 缓存结果 (1小时)
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'role': user.role,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None
            }
            await self.cache.set(cache_key, user_data, ttl=3600)
            logger.debug(f"💾 缓存设置: user:email:{email}")

        return user

    async def get_by_username(self, username: str, session: AsyncSession = None) -> Optional[Any]:
        """带缓存的根据用户名获取用户"""
        cache_key = f"user:username:{username}"

        # 尝试从缓存获取
        cached_user = await self.cache.get(cache_key)
        if cached_user:
            logger.debug(f"📦 缓存命中: user:username:{username}")
            return cached_user

        # 从数据库获取
        user = await self.user_repository.get_by_username(username, session)
        if user:
            # 缓存结果 (1小时)
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'role': user.role,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None
            }
            await self.cache.set(cache_key, user_data, ttl=3600)
            logger.debug(f"💾 缓存设置: user:username:{username}")

        return user

    async def get_active_users(self, limit: int = 10, session: AsyncSession = None) -> list[Any]:
        """带缓存的获取活跃用户"""
        cache_key = f"users:active:{limit}"

        # 尝试从缓存获取
        cached_users = await self.cache.get(cache_key)
        if cached_users:
            logger.debug(f"📦 缓存命中: users:active:{limit}")
            return cached_users

        # 从数据库获取
        users = await self.user_repository.get_list(skip=0, limit=limit, active_only=True, session=session)
        if users:
            # 缓存结果 (30分钟)
            users_data = []
            for user in users:
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_active': user.is_active,
                    'role': user.role,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None
                })
            await self.cache.set(cache_key, users_data, ttl=1800)
            logger.debug(f"💾 缓存设置: users:active:{limit}")

        return users

    async def invalidate_user_cache(self, user_id: int = None, email: str = None, username: str = None):
        """使用户缓存失效"""
        invalidated_keys = []

        if user_id:
            # 按用户ID失效缓存
            pattern = f"user:*:{user_id}:*"
            count = await self.cache.invalidate_pattern(pattern)
            invalidated_keys.extend([f"user_id:{user_id}"] * count)

        if email:
            # 失效邮箱缓存
            await self.cache.delete(f"user:email:{email}")
            invalidated_keys.append(f"user:email:{email}")

        if username:
            # 失效用户名缓存
            await self.cache.delete(f"user:username:{username}")
            invalidated_keys.append(f"user:username:{username}")

        # 失效用户列表缓存
        await self.cache.invalidate_pattern("users:active:*")
        invalidated_keys.append("users:active:*")

        logger.info(f"🗑️ 缓存失效: {invalidated_keys}")

        return invalidated_keys


class CachePerformanceMonitor:
    """缓存性能监控器"""

    def __init__(self, cache: QueryCache):
        """初始化缓存性能监控器"""
        self.cache = cache
        self.monitoring_enabled = True

    async def start_monitoring(self):
        """开始监控缓存性能"""
        logger.info("📊 开始缓存性能监控...")

        while self.monitoring_enabled:
            try:
                stats = self.cache.get_cache_stats()
                hit_rate = stats['hit_rate']

                logger.info(f"📈 缓存性能统计:")
                logger.info(f"  - 命中率: {hit_rate:.2f}%")
                logger.info(f"  - 命中数: {stats['hits']}")
                logger.info(f"  - 未命中数: {stats['misses']}")
                logger.info(f"  - 设置数: {stats['sets']}")
                logger.info(f"  - 删除数: {stats['deletes']}")

                # 检查是否达到目标命中率
                if hit_rate >= 80:
                    logger.info("🎯 缓存命中率已达到目标 (≥80%)")
                else:
                    logger.warning(f"⚠️ 缓存命中率未达标: {hit_rate:.2f}% < 80%")

                # 等待30秒再次检查
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"❌ 缓存监控出错: {e}")
                await asyncio.sleep(30)

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_enabled = False
        logger.info("⏹️ 缓存性能监控已停止")


async def test_cache_performance():
    """测试缓存性能"""
    logger.info("🧪 开始缓存性能测试...")

    # 初始化缓存
    cache = QueryCache()
    await cache.connect()

    # 测试基本缓存功能
    start_time = time.time()

    # 设置缓存
    await cache.set("test_key_1", {"data": "value1"}, ttl=3600)
    await cache.set("test_key_2", {"data": "value2"}, ttl=3600)
    await cache.set("test_key_3", {"data": "value3"}, ttl=3600)

    # 获取缓存（应该命中）
    cached_value1 = await cache.get("test_key_1")
    cached_value2 = await cache.get("test_key_2")

    # 获取不存在的缓存（应该未命中）
    cached_value3 = await cache.get("nonexistent_key")

    # 再次获取已存在的缓存（应该命中）
    cached_value4 = await cache.get("test_key_1")

    test_time = time.time() - start_time

    # 输出测试结果
    print("\n" + "="*60)
    print("🎯 缓存性能测试结果")
    print("="*60)
    print(f"✅ 缓存设置功能: 正常")
    print(f"✅ 缓存获取功能: 正常")
    print(f"⏰ 总测试时间: {test_time:.3f}s")
    print(f"📈 缓存统计: {cache.get_cache_stats()}")
    print(f"🎯 缓存命中率: {cache.get_hit_rate():.2f}%")

    # 验证缓存数据
    assert cached_value1 == {"data": "value1"}
    assert cached_value2 == {"data": "value2"}
    assert cached_value3 is None
    assert cached_value4 == {"data": "value1"}
    print("✅ 缓存数据验证通过")

    print("="*60)

    await cache.close()


async def main():
    """主函数"""
    try:
        # 测试缓存性能
        await test_cache_performance()

        logger.info("✅ 查询缓存实现完成")

    except Exception as e:
        logger.error(f"❌ 缓存实现失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())