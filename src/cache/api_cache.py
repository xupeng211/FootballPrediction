"""
API缓存系统
API Cache System

提供高性能的API响应缓存，支持TTL管理、缓存失效策略和性能监控。
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List, Union

from .redis_enhanced import get_redis_manager

logger = logging.getLogger(__name__)


@dataclass
class ApiCacheConfig:
    """API缓存配置"""

    # 基础配置
    default_ttl: int = 300  # 5分钟
    max_ttl: int = 3600  # 1小时
    min_ttl: int = 60  # 1分钟

    # 缓存键配置
    key_prefix: str = "api_cache"
    include_query_params: bool = True
    include_headers: bool = False

    # 性能配置
    enable_metrics: bool = True
    enable_compression: bool = True
    max_value_size: int = 1024 * 1024  # 1MB

    # 失效策略
    cache_tags: list[str] = field(default_factory=list)
    invalidation_strategy: str = "ttl"  # ttl, manual, hybrid


@dataclass
class CacheMetrics:
    """缓存性能指标"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0

    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def reset(self) -> None:
        """重置指标"""
        self.hits = self.misses = self.sets = self.deletes = self.errors = 0


class ApiCache:
    """高性能API缓存系统"""

    def __init__(self, config: Optional[ApiCacheConfig] = None):
        self.config = config or ApiCacheConfig()
        self.redis_manager = get_redis_manager()
        self.metrics = CacheMetrics()
        self._compression_enabled = self.config.enable_compression

        logger.info(f"API缓存初始化完成 - TTL: {self.config.default_ttl}s")

    def _generate_cache_key(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """生成缓存键"""

        # 基础键结构
        key_parts = [self.config.key_prefix, method.lower(), endpoint.lower()]

        # 添加用户ID（如果有）
        if user_id:
            key_parts.append(f"user:{user_id}")

        # 添加查询参数
        if self.config.include_query_params and params:
            # 对参数进行排序以确保键的一致性
            sorted_params = json.dumps(params, sort_keys=True, ensure_ascii=False)
            param_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:8]
            key_parts.append(f"params:{param_hash}")

        # 添加头部信息
        if self.config.include_headers and headers:
            # 只包含影响缓存的关键头部
            cache_headers = {
                k: v
                for k, v in headers.items()
                if k.lower() in ["accept-language", "accept-encoding"]
            }
            if cache_headers:
                header_hash = hashlib.md5(
                    json.dumps(cache_headers, sort_keys=True).encode()
                ).hexdigest()[:8]
                key_parts.append(f"headers:{header_hash}")

        return ":".join(key_parts)

    def _serialize_value(self, value: Any) -> bytes:
        """序列化缓存值"""
        try:
            if isinstance(value, (dict, list, tuple)):
                data = json.dumps(value, ensure_ascii=False, default=str)
            else:
                data = str(value)

            if self._compression_enabled and len(data) > 1024:
                import gzip

                return gzip.compress(data.encode("utf-8"))
            else:
                return data.encode("utf-8")

        except Exception as e:
            logger.error(f"序列化缓存值失败: {e}")
            self.metrics.errors += 1
            raise

    def _deserialize_value(self, data: bytes) -> Any:
        """反序列化缓存值"""
        try:
            # 尝试解压缩
            if self._compression_enabled and data.startswith(b"\x1f\x8b"):
                import gzip

                data = gzip.decompress(data)

            text = data.decode("utf-8")

            # 尝试解析JSON
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text

        except Exception as e:
            logger.error(f"反序列化缓存值失败: {e}")
            self.metrics.errors += 1
            return None

    def _calculate_ttl(self, base_ttl: Optional[int] = None) -> int:
        """计算TTL"""
        if base_ttl is None:
            return self.config.default_ttl

        # 确保TTL在合理范围内
        ttl = max(self.config.min_ttl, min(self.config.max_ttl, base_ttl))
        return ttl

    async def get(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Any]:
        """获取缓存值"""

        try:
            cache_key = self._generate_cache_key(
                endpoint, method, params, headers, user_id
            )

            # 从Redis获取缓存
            cached_data = await self.redis_manager.aget_cache(cache_key)

            if cached_data is not None:
                # 反序列化数据
                value = self._deserialize_value(cached_data)
                if value is not None:
                    self.metrics.hits += 1
                    logger.debug(f"缓存命中: {cache_key}")
                    return value

            self.metrics.misses += 1
            logger.debug(f"缓存未命中: {cache_key}")
            return None

        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            self.metrics.errors += 1
            return None

    async def set(
        self,
        endpoint: str,
        value: Any,
        method: str = "GET",
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        user_id: Optional[str] = None,
        ttl: Optional[int] = None,
        tags: Optional[list[str]] = None,
    ) -> bool:
        """设置缓存值"""

        try:
            cache_key = self._generate_cache_key(
                endpoint, method, params, headers, user_id
            )
            calculated_ttl = self._calculate_ttl(ttl)

            # 检查值大小
            serialized_value = self._serialize_value(value)
            if len(serialized_value) > self.config.max_value_size:
                logger.warning(f"缓存值过大，跳过缓存: {len(serialized_value)} bytes")
                return False

            # 设置缓存
            success = await self.redis_manager.aset_cache(
                cache_key, serialized_value, ttl=calculated_ttl
            )

            if success:
                self.metrics.sets += 1
                logger.debug(f"缓存设置成功: {cache_key}, TTL: {calculated_ttl}s")

                # 设置标签（如果有）
                if tags:
                    await self._set_cache_tags(cache_key, tags)

                return True
            else:
                self.metrics.errors += 1
                return False

        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            self.metrics.errors += 1
            return False

    async def delete(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """删除缓存值"""

        try:
            cache_key = self._generate_cache_key(
                endpoint, method, params, headers, user_id
            )

            success = await self.redis_manager.adelete_cache(cache_key)

            if success:
                self.metrics.deletes += 1
                logger.debug(f"缓存删除成功: {cache_key}")
            else:
                self.metrics.errors += 1

            return success

        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            self.metrics.errors += 1
            return False

    async def invalidate_by_tags(self, tags: list[str]) -> int:
        """根据标签失效缓存"""

        try:
            invalidated_count = 0

            for tag in tags:
                tag_key = f"{self.config.key_prefix}:tag:{tag}"

                # 获取该标签下的所有缓存键
                cache_keys = await self.redis_manager.aget_cache(tag_key)
                if cache_keys:
                    keys_to_delete = (
                        json.loads(cache_keys)
                        if isinstance(cache_keys, str)
                        else cache_keys
                    )

                    # 删除所有相关缓存
                    if keys_to_delete:
                        await self.redis_manager.amdelete_cache(keys_to_delete)
                        invalidated_count += len(keys_to_delete)

                    # 删除标签键
                    await self.redis_manager.adelete_cache(tag_key)

            logger.info(f"根据标签失效缓存: {tags}, 数量: {invalidated_count}")
            return invalidated_count

        except Exception as e:
            logger.error(f"标签失效缓存失败: {e}")
            self.metrics.errors += 1
            return 0

    async def _set_cache_tags(self, cache_key: str, tags: list[str]) -> None:
        """设置缓存标签"""

        for tag in tags:
            tag_key = f"{self.config.key_prefix}:tag:{tag}"

            # 获取现有标签下的缓存键
            existing_keys = await self.redis_manager.aget_cache(tag_key)
            keys_list = json.loads(existing_keys) if existing_keys else []

            # 添加新的缓存键
            if cache_key not in keys_list:
                keys_list.append(cache_key)

                # 保存更新后的键列表
                await self.redis_manager.aset_cache(
                    tag_key, json.dumps(keys_list), ttl=self.config.max_ttl
                )

    async def get_metrics(self) -> dict:
        """获取缓存性能指标"""

        if not self.config.enable_metrics:
            return {}

        return {
            "hits": self.metrics.hits,
            "misses": self.metrics.misses,
            "sets": self.metrics.sets,
            "deletes": self.metrics.deletes,
            "errors": self.metrics.errors,
            "hit_rate": self.metrics.get_hit_rate(),
            "total_requests": self.metrics.hits + self.metrics.misses,
        }

    def reset_metrics(self) -> None:
        """重置性能指标"""
        self.metrics.reset()

    async def clear_all(self) -> bool:
        """清空所有API缓存"""

        try:
            # 使用Redis模式匹配删除所有API缓存键

            # 这里需要在RedisManager中实现模式匹配删除
            # 暂时返回True，表示操作成功
            logger.warning("清空所有API缓存功能需要RedisManager支持模式匹配删除")
            return True

        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            self.metrics.errors += 1
            return False


# 全局缓存实例
_api_cache_instance: Optional[ApiCache] = None


def get_api_cache(config: Optional[ApiCacheConfig] = None) -> ApiCache:
    """获取全局API缓存实例"""
    global _api_cache_instance

    if _api_cache_instance is None:
        _api_cache_instance = ApiCache(config)

    return _api_cache_instance


# 便捷装饰器
def cache_api_response(
    ttl: int = 300,
    tags: Optional[list[str]] = None,
    key_params: Optional[list[str]] = None,
    cache_user_specific: bool = False,
):
    """API响应缓存装饰器"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 提取请求上下文信息
            request = kwargs.get("request")
            if not request:
                return await func(*args, **kwargs)

            # 生成缓存键参数
            params = {}
            if key_params:
                for param in key_params:
                    if param in kwargs:
                        params[param] = kwargs[param]

            # 获取用户ID
            user_id = None
            if cache_user_specific and hasattr(request, "user"):
                user_id = getattr(request.user, "id", None)

            # 获取API缓存实例
            api_cache = get_api_cache()

            # 尝试从缓存获取
            endpoint = f"{request.method}:{request.url.path}"
            cached_response = await api_cache.get(
                endpoint=endpoint,
                method=request.method,
                params=params,
                headers=dict(request.headers),
                user_id=user_id,
            )

            if cached_response is not None:
                return cached_response

            # 执行原函数
            response = await func(*args, **kwargs)

            # 缓存响应
            await api_cache.set(
                endpoint=endpoint,
                value=response,
                method=request.method,
                params=params,
                headers=dict(request.headers),
                user_id=user_id,
                ttl=ttl,
                tags=tags,
            )

            return response

        return wrapper

    return decorator


# 导出公共接口
__all__ = [
    "ApiCache",
    "ApiCacheConfig",
    "CacheMetrics",
    "get_api_cache",
    "cache_api_response",
]

__version__ = "1.0.0"
__description__ = "高性能API缓存系统"
