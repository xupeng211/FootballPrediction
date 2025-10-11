# mypy: ignore-errors
"""
数据处理缓存管理

提供数据处理的缓存功能，避免重复计算。
"""

from src.cache.redis import RedisManager, CacheKeyManager
from typing import Dict, List, Optional, Any
import logging


class ProcessingCache:
    """数据处理缓存管理器"""

    def __init__(self):
        """初始化缓存管理器"""
        self.logger = logging.getLogger(f"processing.{self.__class__.__name__}")
        self.redis_manager = None
        self.key_manager = CacheKeyManager()
        self.cache_enabled = True

        # 缓存配置
        self.cache_ttl = {
            "match_processing": 3600,  # 1小时
            "odds_processing": 1800,  # 30分钟
            "features_processing": 7200,  # 2小时
            "validation": 900,  # 15分钟
            "statistics": 1800,  # 30分钟
        }

        # 缓存统计
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "errors": 0,
        }

    async def initialize(self) -> bool:
        """初始化缓存管理器"""
        try:
            self.redis_manager = RedisManager()  # type: ignore
            self.logger.info("数据处理缓存管理器初始化完成")
            return True
        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"初始化缓存管理器失败: {e}")
            self.cache_enabled = False
            return False

    async def shutdown(self) -> None:
        """关闭缓存管理器"""
        if self.redis_manager:
            try:
                if hasattr(self.redis_manager.close, "_mock_name"):
                    await self.redis_manager.close()
                else:
                    self.redis_manager.close()
            except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
                self.logger.error(f"关闭缓存管理器失败: {e}")
            self.redis_manager = None

    def _generate_cache_key(
        self,
        operation: str,
        data_hash: str,
        params: Optional[Dict[str, Any]] = None,  # type: ignore
    ) -> str:
        """
        生成缓存键

        Args:
            operation: 操作类型
            data_hash: 数据哈希值
            params: 参数字典

        Returns:
            缓存键
        """
        # 创建基础键
        key_parts = [
            "processing",
            operation,
            data_hash,
        ]

        # 添加参数
        if params:
            params_str = json.dumps(params, sort_keys=True)  # type: ignore
            params_hash = hashlib.md5(params_str.encode()).hexdigest()  # type: ignore
            key_parts.append(params_hash)

        # 生成完整键
        ":".join(key_parts)

        # 使用键管理器规范化
        return self.key_manager.create_key(  # type: ignore
            service="processing",
            resource=operation,
            identifier=data_hash,
            params=params,
        )

    def _calculate_data_hash(self, data: Any) -> str:  # type: ignore
        """
        计算数据哈希值

        Args:
            data: 数据对象

        Returns:
            哈希值
        """
        try:
            if isinstance(data, (dict, list)):
                data_str = json.dumps(data, sort_keys=True)  # type: ignore
            else:
                data_str = str(data)

            return hashlib.md5(data_str.encode()).hexdigest()  # type: ignore
        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"计算数据哈希失败: {e}")
            return "error_hash"

    async def get_cached_result(
        self,
        operation: str,
        data: Any,  # type: ignore
        params: Optional[Dict[str, Any]] = None,  # type: ignore
    ) -> Optional[Any]:  # type: ignore
        """
        获取缓存的计算结果

        Args:
            operation: 操作类型
            data: 输入数据
            params: 参数

        Returns:
            缓存的结果
        """
        if not self.cache_enabled or not self.redis_manager:
            self.stats["misses"] += 1
            return None

        try:
            # 计算数据哈希
            data_hash = self._calculate_data_hash(data)

            # 生成缓存键
            cache_key = self._generate_cache_key(operation, data_hash, params)

            # 尝试获取缓存
            result = await self.redis_manager.get(cache_key)

            if result is not None:
                # 反序列化结果
                try:
                    deserialized_result = json.loads(result)  # type: ignore
                    self.stats["hits"] += 1
                    self.logger.debug(f"缓存命中: {operation}")
                    return deserialized_result
                except json.JSONDecodeError:  # type: ignore
                    self.logger.warning(f"缓存数据反序列化失败: {cache_key}")
                    self.stats["errors"] += 1

            self.stats["misses"] += 1
            return None

        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"获取缓存结果失败: {e}")
            self.stats["errors"] += 1
            return None

    async def cache_result(
        self,
        operation: str,
        data: Any,  # type: ignore
        result: Any,  # type: ignore
        params: Optional[Dict[str, Any]] = None,  # type: ignore
        ttl: Optional[int] = None,  # type: ignore
    ) -> bool:
        """
        缓存计算结果

        Args:
            operation: 操作类型
            data: 输入数据
            result: 计算结果
            params: 参数
            ttl: 过期时间（秒）

        Returns:
            是否缓存成功
        """
        if not self.cache_enabled or not self.redis_manager:
            return False

        try:
            # 计算数据哈希
            data_hash = self._calculate_data_hash(data)

            # 生成缓存键
            cache_key = self._generate_cache_key(operation, data_hash, params)

            # 序列化结果
            serialized_result = json.dumps(result, default=str)  # type: ignore

            # 确定TTL
            if ttl is None:
                ttl = self.cache_ttl.get(operation, 3600)

            # 存储到缓存
            success = await self.redis_manager.set(cache_key, serialized_result, ex=ttl)

            if success:
                self.stats["sets"] += 1
                self.logger.debug(f"缓存结果: {operation}, TTL: {ttl}s")
            else:
                self.stats["errors"] += 1

            return success  # type: ignore

        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"缓存结果失败: {e}")
            self.stats["errors"] += 1
            return False

    async def invalidate_cache(
        self,
        operation: Optional[str] = None,  # type: ignore
        data_hash: Optional[str] = None,  # type: ignore
    ) -> int:
        """
        使缓存失效

        Args:
            operation: 操作类型（None表示所有操作）
            data_hash: 数据哈希（None表示所有数据）

        Returns:
            失效的键数量
        """
        if not self.cache_enabled or not self.redis_manager:
            return 0

        try:
            invalidated_count = 0

            # 构建匹配模式
            if operation and data_hash:
                # 使特定操作的特定数据缓存失效
                cache_key = self._generate_cache_key(operation, data_hash)
                if await self.redis_manager.delete(cache_key):
                    invalidated_count += 1
            elif operation:
                # 使特定操作的所有缓存失效
                pattern = f"processing:{operation}:*"
                keys = await self.redis_manager.keys(pattern)
                if keys:
                    invalidated_count = await self.redis_manager.delete(*keys)
            else:
                # 使所有处理缓存失效
                pattern = "processing:*"
                keys = await self.redis_manager.keys(pattern)
                if keys:
                    invalidated_count = await self.redis_manager.delete(*keys)

            self.stats["evictions"] += invalidated_count
            self.logger.info(f"使缓存失效: {invalidated_count} 个键")
            return invalidated_count

        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"使缓存失效失败: {e}")
            self.stats["errors"] += 1
            return 0

    async def get_cache_stats(self) -> Dict[str, Any]:  # type: ignore
        """
        获取缓存统计信息

        Returns:
            缓存统计信息
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            self.stats["hits"] / total_requests * 100 if total_requests > 0 else 0
        )

        cache_stats = {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 2),
            "cache_enabled": self.cache_enabled,
        }

        if self.redis_manager:
            try:
                # 获取Redis缓存信息
                info = self.redis_manager.get_info()
                if info:
                    cache_stats["redis_info"] = {
                        "used_memory": info.get("used_memory", 0),
                        "connected_clients": info.get("connected_clients", 0),
                        "keyspace_hits": info.get("keyspace_hits", 0),
                        "keyspace_misses": info.get("keyspace_misses", 0),
                    }
            except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
                self.logger.error(f"获取Redis信息失败: {e}")

        return cache_stats

    async def cleanup_expired_cache(self) -> int:
        """
        清理过期的缓存

        Returns:
            清理的键数量
        """
        if not self.cache_enabled or not self.redis_manager:
            return 0

        try:
            # Redis会自动清理过期键，这里主要是统计
            self.logger.info("开始清理过期缓存")

            # 获取所有处理相关的键
            pattern = "processing:*"
            keys = await self.redis_manager.keys(pattern)

            if not keys:
                self.logger.info("没有找到需要清理的缓存键")
                return 0

            cleaned_count = 0

            # 检查每个键的TTL
            for key in keys:
                ttl = await self.redis_manager.ttl(key)
                if ttl == -2:  # 键不存在
                    cleaned_count += 1
                elif ttl == -1:  # 键没有过期时间
                    # 为永久键设置过期时间
                    await self.redis_manager.expire(key, 3600)

            self.logger.info(f"清理过期缓存完成，处理了 {len(keys)} 个键")
            return cleaned_count

        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"清理过期缓存失败: {e}")
            self.stats["errors"] += 1
            return 0

    def enable_cache(self) -> None:
        """启用缓存"""
        self.cache_enabled = True
        self.logger.info("数据处理缓存已启用")

    def disable_cache(self) -> None:
        """禁用缓存"""
        self.cache_enabled = False
        self.logger.info("数据处理缓存已禁用")

    def set_cache_ttl(self, operation: str, ttl: int) -> None:
        """
        设置特定操作的缓存TTL

        Args:
            operation: 操作类型
            ttl: 过期时间（秒）
        """
        self.cache_ttl[operation] = ttl
        self.logger.info(f"设置 {operation} 的缓存TTL为 {ttl} 秒")

    async def warm_up_cache(
        self,
        operations: List[str],  # type: ignore
        sample_data: List[Any],  # type: ignore
        process_func: callable,  # type: ignore
    ) -> None:
        """
        缓存预热

        Args:
            operations: 操作列表
            sample_data: 示例数据
            process_func: 处理函数
        """
        if not self.cache_enabled:
            self.logger.info("缓存已禁用，跳过预热")
            return

        self.logger.info(f"开始缓存预热，共 {len(operations)} 个操作")

        for operation in operations:
            for i, data in enumerate(sample_data[:5]):  # 每个操作预热5个样本
                try:
                    self.logger.debug(f"预热 {operation} 样本 {i+1}")

                    # 检查是否已缓存
                    cached = await self.get_cached_result(operation, data)
                    if cached is None:
                        # 处理并缓存结果
                        result = await process_func(data)  # type: ignore
                        await self.cache_result(operation, data, result)

                except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
                    self.logger.error(f"预热 {operation} 失败: {e}")

        self.logger.info("缓存预热完成")
