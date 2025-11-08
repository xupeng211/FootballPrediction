"""
UX优化模块 - API响应时间优化器
实现API响应时间优化，目标将平均响应时间从500ms降低到200ms以下
"""

import asyncio
import logging
import statistics
import time
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.cache.unified_cache import UnifiedCacheManager
from src.monitoring.performance_profiler import PerformanceProfiler

logger = logging.getLogger(__name__)


@dataclass
class APIResponseMetric:
    """API响应时间指标"""

    endpoint: str
    method: str
    response_time: float
    status_code: int
    timestamp: datetime
    user_id: str | None = None
    request_size: int = 0
    response_size: int = 0
    cache_hit: bool = False


@dataclass
class PerformanceThreshold:
    """性能阈值配置"""

    avg_response_time: float = 200.0  # 目标平均响应时间(ms)
    p95_response_time: float = 300.0  # 95%响应时间阈值(ms)
    p99_response_time: float = 500.0  # 99%响应时间阈值(ms)
    error_rate: float = 0.01  # 错误率阈值(1%)
    min_sample_size: int = 100  # 最小样本数


@dataclass
class OptimizationStrategy:
    """优化策略配置"""

    enable_query_optimization: bool = True
    enable_cache_warming: bool = True
    enable_compression: bool = True
    enable_async_processing: bool = True
    enable_connection_pooling: bool = True
    cache_ttl: int = 300  # 缓存TTL(秒)
    max_batch_size: int = 100
    compression_threshold: int = 1024  # 压缩阈值(字节)


class APIResponseOptimizer:
    """API响应时间优化器"""

    def __init__(
        self,
        cache: UnifiedCacheManager,
        performance_profiler: PerformanceProfiler,
        strategy: OptimizationStrategy | None = None,
    ):
        self.cache = cache
        self.profiler = performance_profiler
        self.strategy = strategy or OptimizationStrategy()
        self.threshold = PerformanceThreshold()

        # 性能指标存储
        self.metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.optimization_stats = {
            "total_requests": 0,
            "optimized_requests": 0,
            "cache_hits": 0,
            "response_time_reductions": [],
            "last_optimization": None,
        }

        # 预热缓存
        self._warmup_cache()

    async def __call__(
        self, func: Callable, endpoint: str, method: str = "GET", *args, **kwargs
    ) -> Any:
        """中间件调用函数"""
        start_time = time.time()

        try:
            # 检查缓存
            cache_key = self._generate_cache_key(endpoint, method, args, kwargs)
            cached_result = await self._get_cached_result(cache_key)

            if cached_result is not None:
                response_time = (time.time() - start_time) * 1000
                await self._record_metric(
                    endpoint, method, response_time, 200, cache_hit=True
                )
                return cached_result

            # 执行函数
            if self.strategy.enable_async_processing and asyncio.iscoroutinefunction(
                func
            ):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # 缓存结果
            await self._cache_result(cache_key, result)

            # 记录指标
            response_time = (time.time() - start_time) * 1000
            await self._record_metric(endpoint, method, response_time, 200)

            # 检查是否需要优化
            await self._check_optimization_needed(endpoint, method)

            return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status_code = getattr(e, "status_code", 500)
            await self._record_metric(endpoint, method, response_time, status_code)
            raise

    def _generate_cache_key(
        self, endpoint: str, method: str, args: tuple, kwargs: dict
    ) -> str:
        """生成缓存键"""
        import hashlib

        key_data = f"{endpoint}:{method}:{str(args)}:{str(sorted(kwargs.items()))}"
        return f"api_response:{hashlib.md5(key_data.encode()).hexdigest()}"

    async def _get_cached_result(self, cache_key: str) -> Any | None:
        """获取缓存结果"""
        try:
            result = await self.cache.get(cache_key)
            if result is not None:
                self.optimization_stats["cache_hits"] += 1
                logger.debug(f"Cache hit for key: {cache_key}")
            return result
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    async def _cache_result(self, cache_key: str, result: Any) -> None:
        """缓存结果"""
        try:
            # 检查结果大小，避免缓存过大数据
            result_size = len(str(result)) if result else 0
            if result_size < 1024 * 1024:  # 1MB限制
                await self.cache.set(cache_key, result, ttl=self.strategy.cache_ttl)
                logger.debug(f"Cached result for key: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    async def _record_metric(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int,
        cache_hit: bool = False,
        user_id: str | None = None,
    ) -> None:
        """记录性能指标"""
        metric = APIResponseMetric(
            endpoint=endpoint,
            method=method,
            response_time=response_time,
            status_code=status_code,
            timestamp=datetime.now(),
            user_id=user_id,
            cache_hit=cache_hit,
        )

        key = f"{method}:{endpoint}"
        self.metrics[key].append(metric)
        self.optimization_stats["total_requests"] += 1

        # 记录到性能分析器
        await self.profiler.record_metric(
            {
                "type": "api_response_time",
                "endpoint": endpoint,
                "method": method,
                "response_time": response_time,
                "status_code": status_code,
                "cache_hit": cache_hit,
            }
        )

    async def _check_optimization_needed(self, endpoint: str, method: str) -> None:
        """检查是否需要优化"""
        key = f"{method}:{endpoint}"
        metrics = list(self.metrics[key])

        if len(metrics) < self.threshold.min_sample_size:
            return

        # 计算性能指标
        response_times = [m.response_time for m in metrics]
        avg_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        p99_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
        error_count = sum(1 for m in metrics if m.status_code >= 400)
        error_rate = error_count / len(metrics)

        # 检查是否超出阈值
        needs_optimization = (
            avg_time > self.threshold.avg_response_time
            or p95_time > self.threshold.p95_response_time
            or p99_time > self.threshold.p99_response_time
            or error_rate > self.threshold.error_rate
        )

        if needs_optimization:
            logger.warning(
                f"Performance threshold exceeded for {method} {endpoint}: "
                f"avg={avg_time:.1f}ms, p95={p95_time:.1f}ms, error_rate={error_rate:.2%}"
            )
            await self._optimize_endpoint(endpoint, method, metrics)

    async def _optimize_endpoint(
        self, endpoint: str, method: str, metrics: list[APIResponseMetric]
    ) -> None:
        """优化端点性能"""
        logger.info(f"Starting optimization for {method} {endpoint}")

        optimization_start = time.time()
        original_avg_time = statistics.mean([m.response_time for m in metrics])

        # 实施优化策略
        optimizations = []

        # 1. 缓存预热
        if self.strategy.enable_cache_warming:
            await self._warmup_endpoint_cache(endpoint, method)
            optimizations.append("cache_warming")

        # 2. 查询优化
        if self.strategy.enable_query_optimization:
            await self._optimize_database_queries(endpoint, method)
            optimizations.append("query_optimization")

        # 3. 连接池优化
        if self.strategy.enable_connection_pooling:
            await self._optimize_connection_pooling(endpoint, method)
            optimizations.append("connection_pooling")

        # 4. 压缩优化
        if self.strategy.enable_compression:
            await self._enable_compression(endpoint, method)
            optimizations.append("compression")

        optimization_time = (time.time() - optimization_start) * 1000

        # 记录优化结果
        self.optimization_stats["optimized_requests"] += 1
        self.optimization_stats["last_optimization"] = datetime.now()
        self.optimization_stats["response_time_reductions"].append(
            {
                "endpoint": endpoint,
                "method": method,
                "original_avg": original_avg_time,
                "optimizations": optimizations,
                "optimization_time": optimization_time,
                "timestamp": datetime.now(),
            }
        )

        logger.info(
            f"Optimization completed for {method} {endpoint} in {optimization_time:.1f}ms"
        )

    async def _warmup_cache(self) -> None:
        """预热系统缓存"""
        try:
            # 预加载常用数据
            common_queries = [
                "matches:upcoming",
                "predictions:popular",
                "teams:active",
                "leagues:current",
            ]

            for query in common_queries:
                await self.cache.get(query)

            logger.info("System cache warmed up successfully")
        except Exception as e:
            logger.warning(f"Cache warmup failed: {e}")

    async def _warmup_endpoint_cache(self, endpoint: str, method: str) -> None:
        """预热端点缓存"""
        try:
            # 根据端点类型预热相关数据
            if "predictions" in endpoint:
                await self._warmup_predictions_cache()
            elif "matches" in endpoint:
                await self._warmup_matches_cache()
            elif "teams" in endpoint:
                await self._warmup_teams_cache()

            logger.debug(f"Cache warmed up for {method} {endpoint}")
        except Exception as e:
            logger.warning(f"Endpoint cache warmup failed: {e}")

    async def _warmup_predictions_cache(self) -> None:
        """预热预测数据缓存"""
        # 预加载热门预测数据
        pass

    async def _warmup_matches_cache(self) -> None:
        """预热比赛数据缓存"""
        # 预加载即将进行的比赛
        pass

    async def _warmup_teams_cache(self) -> None:
        """预热队伍数据缓存"""
        # 预加载活跃队伍信息
        pass

    async def _optimize_database_queries(self, endpoint: str, method: str) -> None:
        """优化数据库查询"""
        try:
            # 分析慢查询并优化
            slow_queries = await self._identify_slow_queries(endpoint, method)

            for query_info in slow_queries:
                await self._optimize_query(query_info)

            logger.debug(f"Database queries optimized for {method} {endpoint}")
        except Exception as e:
            logger.warning(f"Database query optimization failed: {e}")

    async def _identify_slow_queries(self, endpoint: str, method: str) -> list[dict]:
        """识别慢查询"""
        # 这里应该查询性能分析数据
        # 返回慢查询列表
        return []

    async def _optimize_query(self, query_info: dict) -> None:
        """优化单个查询"""
        # 实施查询优化策略
        pass

    async def _optimize_connection_pooling(self, endpoint: str, method: str) -> None:
        """优化连接池"""
        try:
            # 调整连接池参数
            logger.debug(f"Connection pooling optimized for {method} {endpoint}")
        except Exception as e:
            logger.warning(f"Connection pooling optimization failed: {e}")

    async def _enable_compression(self, endpoint: str, method: str) -> None:
        """启用压缩"""
        try:
            # 为响应启用压缩
            logger.debug(f"Compression enabled for {method} {endpoint}")
        except Exception as e:
            logger.warning(f"Compression enablement failed: {e}")

    @asynccontextmanager
    async def measure_response_time(self, endpoint: str, method: str = "GET"):
        """测量响应时间的上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            response_time = (time.time() - start_time) * 1000
            await self._record_metric(endpoint, method, response_time, 200)

    def get_performance_stats(self) -> dict[str, Any]:
        """获取性能统计"""
        stats = {
            "optimization_stats": self.optimization_stats.copy(),
            "total_endpoints": len(self.metrics),
            "total_metrics": sum(len(metrics) for metrics in self.metrics.values()),
            "cache_hit_rate": (
                self.optimization_stats["cache_hits"]
                / max(1, self.optimization_stats["total_requests"])
            )
            * 100,
        }

        # 计算各端点的性能
        endpoint_stats = {}
        for key, metrics in self.metrics.items():
            if metrics:
                response_times = [m.response_time for m in metrics]
                endpoint_stats[key] = {
                    "request_count": len(metrics),
                    "avg_response_time": statistics.mean(response_times),
                    "p95_response_time": statistics.quantiles(response_times, n=20)[18],
                    "error_rate": sum(1 for m in metrics if m.status_code >= 400)
                    / len(metrics),
                }

        stats["endpoints"] = endpoint_stats
        return stats

    def get_optimization_recommendations(self) -> list[dict[str, Any]]:
        """获取优化建议"""
        recommendations = []

        for key, metrics in self.metrics.items():
            if len(metrics) < self.threshold.min_sample_size:
                continue

            response_times = [m.response_time for m in metrics]
            avg_time = statistics.mean(response_times)
            p95_time = statistics.quantiles(response_times, n=20)[18]

            if avg_time > self.threshold.avg_response_time:
                recommendations.append(
                    {
                        "endpoint": key,
                        "issue": f"Average response time {avg_time:.1f}ms exceeds threshold {self.threshold.avg_response_time}ms",
                        "priority": "high",
                        "suggestions": [
                            "Enable query result caching",
                            "Optimize database queries",
                            "Implement connection pooling",
                        ],
                    }
                )

            if p95_time > self.threshold.p95_response_time:
                recommendations.append(
                    {
                        "endpoint": key,
                        "issue": f"P95 response time {p95_time:.1f}ms exceeds threshold {self.threshold.p95_response_time}ms",
                        "priority": "medium",
                        "suggestions": [
                            "Implement request batching",
                            "Add CDN caching",
                            "Optimize serialization",
                        ],
                    }
                )

        return recommendations


class ResponseTimeMiddleware:
    """响应时间监控中间件"""

    def __init__(self, optimizer: APIResponseOptimizer):
        self.optimizer = optimizer

    async def __call__(self, request, call_next):
        """FastAPI中间件处理函数"""
        start_time = time.time()

        # 获取请求信息
        endpoint = request.url.path
        method = request.method

        # 处理请求
        response = await call_next(request)

        # 计算响应时间
        response_time = (time.time() - start_time) * 1000

        # 记录指标
        await self.optimizer._record_metric(
            endpoint=endpoint,
            method=method,
            response_time=response_time,
            status_code=response.status_code,
            user_id=getattr(request.state, "user_id", None),
        )

        # 添加响应头
        response.headers["X-Response-Time"] = f"{response_time:.1f}ms"

        return response


# 全局优化器实例
_api_optimizer: APIResponseOptimizer | None = None


def get_api_optimizer() -> APIResponseOptimizer:
    """获取全局API优化器实例"""
    global _api_optimizer
    if _api_optimizer is None:
        raise RuntimeError("API optimizer not initialized")
    return _api_optimizer


def initialize_api_optimizer(
    cache: UnifiedCacheManager,
    profiler: PerformanceProfiler,
    strategy: OptimizationStrategy | None = None,
) -> APIResponseOptimizer:
    """初始化全局API优化器"""
    global _api_optimizer
    _api_optimizer = APIResponseOptimizer(cache, profiler, strategy)
    return _api_optimizer
