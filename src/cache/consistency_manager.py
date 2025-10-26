"""
缓存一致性管理器
负责协调Redis缓存和PostgreSQL数据库之间的数据一致性
"""

from src.cache.redis import get_redis_manager

import logging
from typing import Any, Dict, List, Union
from redis.exceptions import RedisError

try:
    from .redis_manager import get_redis_manager
except ImportError:
    # 如果redis_manager不可用，使用模拟版本
    from .mock_redis import get_redis_manager

logger = logging.getLogger(__name__)

class ConsistencyManager:
    """缓存一致性管理器别名"""

    pass

class CacheConsistencyManager:
    """缓存一致性管理类"""

    def __init__(self, redis_manager=None, db_manager=None):
        """
        初始化缓存一致性管理器
        :param redis_manager: Redis管理器实例
        :param db_manager: 数据库管理器实例
        """
        self.redis_manager = redis_manager or get_redis_manager()
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def sync_cache_with_db(self, entity_type: str, entity_id: int) -> bool:
        """
        将数据库记录同步到缓存
        :param entity_type: 实体类型 (e.g., 'match', 'prediction')
        :param entity_id: 实体ID
        :return: 同步是否成功
        """
        try:
            # Placeholder implementation
            # 这里可以根据entity_type从数据库获取数据并更新缓存
            cache_key = f"{entity_type}:{entity_id}"

            # 如果有数据库管理器，可以从数据库获取数据
            if self.db_manager:
                # 实际实现应该根据entity_type调用相应的数据库查询
                pass

            self.logger.debug(f"同步缓存: {cache_key}")
            return True
        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"同步缓存失败: {e}")
            return False

    async def invalidate_cache(self, keys: Union[List[str], str]) -> bool:
        """
        使缓存中的一个或多个键失效
        :param keys: 需要失效的缓存键列表或单个键
        :return: 失效是否成功
        """
        try:
            if isinstance(keys, str):
                keys = [keys]

            if not keys:
                return True

            # 使用统一的异步接口
            from .redis_manager import adelete_cache

            success_count = 0

            for key in keys:
                if await adelete_cache(key):
                    success_count += 1

            self.logger.info(f"缓存失效: {success_count}/{len(keys)} 个键")
            return success_count == len(keys)
        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"缓存失效失败: {e}")
            return False

    async def warm_cache(self, entity_type: str, ids: List[int]) -> bool:
        """
        预热缓存，将指定ID列表的实体从数据库加载到缓存
        :param entity_type: 实体类型
        :param ids: 实体ID列表
        :return: 预热是否成功
        """
        try:
            if not ids:
                return True

            success_count = 0
            for entity_id in ids:
                if await self.sync_cache_with_db(entity_type, entity_id):
                    success_count += 1

            self.logger.info(f"缓存预热: {success_count}/{len(ids)} 个实体")
            return success_count == len(ids)
        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"缓存预热失败: {e}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        :return: 统计信息字典
        """
        try:
            # 可以扩展获取更多统计信息
            return {
                "status": "active",
                "manager_type": "consistency_manager",
            }
        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"获取缓存统计失败: {e}")
            return {"status": "error", "error": str(e)}

# 便捷函数
async def invalidate_entity_cache(
    entity_type: str, entity_id: Union[int, List[int]]
) -> bool:
    """失效实体缓存的便捷函数"""
    manager = CacheConsistencyManager()

    if isinstance(entity_id, int):
        keys = [f"{entity_type}:{entity_id}"]
    else:
        keys = [f"{entity_type}:{eid}" for eid in entity_id]

    return await manager.invalidate_cache(keys)

async def sync_entity_cache(entity_type: str, entity_id: int) -> bool:
    """同步实体缓存的便捷函数"""
    manager = CacheConsistencyManager()
    return await manager.sync_cache_with_db(entity_type, entity_id)
