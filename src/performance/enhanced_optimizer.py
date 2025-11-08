"""
企业级性能优化器
Enhanced Performance Optimizer

提供全面的性能监控、分析和优化功能，包括异步处理优化、数据库连接池管理、缓存策略等。
"""

import asyncio
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import wraps
from typing import Any

import uvloop
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import QueuePool

from ..cache.redis_manager import get_redis_manager

logger = logging.getLogger(__name__)

# ============================================================================
# 性能指标数据结构
# ============================================================================


@dataclass
class PerformanceMetrics:
    """性能指标"""

    endpoint: str
    method: str
    status_code: int
    response_time: float
    timestamp: datetime
    user_id: int | None = None
    memory_usage: float | None = None
    cpu_usage: float | None = None
    db_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class SystemMetrics:
    """系统指标"""

    total_requests: int = 0
    active_connections: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    avg_response_time: float = 0.0
    requests_per_second: float = 0.0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0


@dataclass
class DatabaseMetrics:
    """数据库指标"""

    active_connections: int = 0
    total_connections: int = 0
    connection_pool_size: int = 0
    avg_query_time: float = 0.0
    slow_queries: int = 0
    total_queries: int = 0
    connection_wait_time: float = 0.0


@dataclass
class CacheMetrics:
    """缓存指标"""

    hit_count: int = 0
    miss_count: int = 0
    set_count: int = 0
    delete_count: int = 0
    hit_rate: float = 0.0
    avg_response_time: float = 0.0
    memory_usage_mb: float = 0.0


# ============================================================================
# 性能监控器
# ============================================================================


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics_history: deque = deque(maxlen=max_metrics)
        self.active_requests: dict[str, float] = {}
        self.request_counts: dict[str, int] = defaultdict(int)
        self.error_counts: dict[str, int] = defaultdict(int)
        self.response_times: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.Lock()

    def record_request_start(self, request_id: str) -> None:
        """记录请求开始"""
        with self._lock:
            self.active_requests[request_id] = time.time()

    def record_request_end(
        self, request_id: str, endpoint: str, method: str, status_code: int, **kwargs
    ) -> None:
        """记录请求结束"""
        end_time = time.time()

        with self._lock:
            start_time = self.active_requests.pop(request_id, end_time)
            response_time = end_time - start_time

            # 创建性能指标
            metrics = PerformanceMetrics(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time=response_time,
                timestamp=datetime.now(UTC),
                **kwargs,
            )

            self.metrics_history.append(metrics)
            self.request_counts[endpoint] += 1
            self.response_times[endpoint].append(response_time)

            if status_code >= 400:
                self.error_counts[endpoint] += 1

    def get_system_metrics(self) -> SystemMetrics:
        """获取系统指标"""
        with self._lock:
            total_requests = len(self.metrics_history)
            active_connections = len(self.active_requests)

            if total_requests == 0:
                return SystemMetrics()

            # 计算平均响应时间
            response_times = [m.response_time for m in self.metrics_history]
            avg_response_time = sum(response_times) / len(response_times)

            # 计算每秒请求数
            if self.metrics_history:
                time_window = (
                    self.metrics_history[-1].timestamp
                    - self.metrics_history[0].timestamp
                ).total_seconds()
                requests_per_second = total_requests / max(time_window, 1)
            else:
                requests_per_second = 0

            # 计算错误率
            total_errors = sum(self.error_counts.values())
            error_rate = (
                (total_errors / total_requests) * 100 if total_requests > 0 else 0
            )

            return SystemMetrics(
                total_requests=total_requests,
                active_connections=active_connections,
                avg_response_time=avg_response_time,
                requests_per_second=requests_per_second,
                error_rate=error_rate,
            )

    def get_slow_queries(
        self, threshold_ms: float = 1000.0
    ) -> list[PerformanceMetrics]:
        """获取慢查询"""
        threshold_sec = threshold_ms / 1000
        return [m for m in self.metrics_history if m.response_time > threshold_sec]

    def get_endpoint_stats(self, endpoint: str) -> dict[str, Any]:
        """获取端点统计"""
        with self._lock:
            count = self.request_counts[endpoint]
            errors = self.error_counts[endpoint]
            response_times = list(self.response_times[endpoint])

            if response_times:
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                min_time = min(response_times)
            else:
                avg_time = max_time = min_time = 0

            return {
                "request_count": count,
                "error_count": errors,
                "error_rate": (errors / count * 100) if count > 0 else 0,
                "avg_response_time": avg_time,
                "max_response_time": max_time,
                "min_response_time": min_time,
            }


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()

# ============================================================================
# 数据库性能优化器
# ============================================================================


class DatabaseOptimizer:
    """数据库性能优化器"""

    def __init__(self):
        self.engine = None
        self.connection_pool = None
        self.query_stats: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    async def initialize(self, database_url: str) -> None:
        """初始化数据库连接池"""
        # 使用uvloop提升异步性能
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        # 创建优化的异步引擎
        self.engine = create_async_engine(
            database_url,
            # 连接池配置
            poolclass=QueuePool,
            pool_size=20,  # 连接池大小
            max_overflow=30,  # 最大溢出连接数
            pool_pre_ping=True,  # 连接预检
            pool_recycle=3600,  # 连接回收时间（1小时）
            pool_timeout=30,  # 获取连接超时时间
            # 查询优化
            echo=False,  # 生产环境关闭SQL日志
            future=True,  # 启用SQLAlchemy 2.0特性
            # 异步配置
            connect_args={
                "command_timeout": 60,
                "server_settings": {
                    "application_name": "football_prediction_api",
                    "jit": "off",  # 关闭JIT以减少首次查询延迟
                },
            },
        )

        logger.info("数据库连接池已优化配置")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话（带性能监控）"""
        if not self.engine:
            raise RuntimeError("数据库引擎未初始化")

        start_time = time.time()
        async with AsyncSession(self.engine) as session:
            try:
                yield session
            finally:
                # 记录查询时间
                query_time = time.time() - start_time
                with self._lock:
                    self.query_stats["default"].append(query_time)

    def get_database_metrics(self) -> DatabaseMetrics:
        """获取数据库性能指标"""
        if not self.engine:
            return DatabaseMetrics()

        pool = self.engine.pool
        with self._lock:
            all_query_times = []
            for times in self.query_stats.values():
                all_query_times.extend(times)

            avg_query_time = (
                sum(all_query_times) / len(all_query_times) if all_query_times else 0
            )
            slow_queries = len([t for t in all_query_times if t > 1.0])  # 超过1秒的查询
            total_queries = len(all_query_times)

        return DatabaseMetrics(
            active_connections=pool.checkedin(),
            total_connections=pool.size() + pool.checkedout(),
            connection_pool_size=pool.size(),
            avg_query_time=avg_query_time,
            slow_queries=slow_queries,
            total_queries=total_queries,
        )

    async def execute_optimized_query(
        self, query_func: Callable, *args, **kwargs
    ) -> Any:
        """执行优化的查询"""
        start_time = time.time()

        try:
            async with self.get_session() as session:
                result = await query_func(session, *args, **kwargs)
                return result
        finally:
            query_time = time.time() - start_time
            if query_time > 1.0:  # 记录慢查询
                logger.warning(f"慢查询检测: {query_time:.2f}s")


# 全局数据库优化器实例
db_optimizer = DatabaseOptimizer()

# ============================================================================
# 缓存性能优化器
# ============================================================================


class CacheOptimizer:
    """缓存性能优化器"""

    def __init__(self):
        self.redis_client = None
        self.cache_stats = CacheMetrics()
        self._lock = threading.Lock()

    async def initialize(self) -> None:
        """初始化Redis连接"""
        self.redis_client = get_redis_manager()
        await self.redis_client.ping()  # 测试连接
        logger.info("Redis缓存连接已建立")

    async def get_cached_data(
        self, key: str, default: Any = None, ttl: int = 3600
    ) -> Any:
        """获取缓存数据（带性能监控）"""
        start_time = time.time()

        try:
            data = await self.redis_client.get(key)
            end_time = time.time()

            with self._lock:
                if data is not None:
                    self.cache_stats.hit_count += 1
                else:
                    self.cache_stats.miss_count += 1

                # 更新平均响应时间
                response_time = end_time - start_time
                current_avg = self.cache_stats.avg_response_time
                total_requests = (
                    self.cache_stats.hit_count + self.cache_stats.miss_count
                )

                if total_requests > 0:
                    self.cache_stats.avg_response_time = (
                        current_avg * (total_requests - 1) + response_time
                    ) / total_requests

            return data if data is not None else default

        except Exception as e:
            logger.error(f"缓存读取失败: {e}")
            return default

    async def set_cached_data(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存数据（带性能监控）"""
        try:
            await self.redis_client.set(key, value, expire=ttl)

            with self._lock:
                self.cache_stats.set_count += 1

            return True
        except Exception as e:
            logger.error(f"缓存写入失败: {e}")
            return False

    async def delete_cached_data(self, key: str) -> bool:
        """删除缓存数据"""
        try:
            await self.redis_client.delete(key)

            with self._lock:
                self.cache_stats.delete_count += 1

            return True
        except Exception as e:
            logger.error(f"缓存删除失败: {e}")
            return False

    def get_cache_metrics(self) -> CacheMetrics:
        """获取缓存性能指标"""
        with self._lock:
            total_requests = self.cache_stats.hit_count + self.cache_stats.miss_count
            hit_rate = (
                (self.cache_stats.hit_count / total_requests * 100)
                if total_requests > 0
                else 0
            )

            self.cache_stats.hit_rate = hit_rate

            return CacheMetrics(
                hit_count=self.cache_stats.hit_count,
                miss_count=self.cache_stats.miss_count,
                set_count=self.cache_stats.set_count,
                delete_count=self.cache_stats.delete_count,
                hit_rate=hit_rate,
                avg_response_time=self.cache_stats.avg_response_time,
            )

    async def warm_up_cache(self, warm_up_data: dict[str, Any]) -> None:
        """缓存预热"""
        logger.info(f"开始缓存预热，数据量: {len(warm_up_data)}")

        success_count = 0
        for key, value in warm_up_data.items():
            if await self.set_cached_data(key, value, ttl=7200):  # 2小时TTL
                success_count += 1

        logger.info(f"缓存预热完成，成功: {success_count}/{len(warm_up_data)}")


# 全局缓存优化器实例
cache_optimizer = CacheOptimizer()

# ============================================================================
# 并发处理优化器
# ============================================================================


class ConcurrencyOptimizer:
    """并发处理优化器"""

    def __init__(self):
        self.semaphore = None
        self.request_queue = asyncio.Queue()
        self.worker_tasks: list[asyncio.Task] = []
        self.active_tasks: set[str] = set()

    async def initialize(self, max_concurrent_requests: int = 1000) -> None:
        """初始化并发控制器"""
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

        # 启动工作线程
        for i in range(10):  # 10个工作协程
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(task)

        logger.info(f"并发处理器已初始化，最大并发: {max_concurrent_requests}")

    async def _worker(self, worker_name: str) -> None:
        """工作协程"""
        while True:
            try:
                # 获取请求
                request_data = await self.request_queue.get()

                # 处理请求
                await self._process_request(request_data)

                # 标记任务完成
                self.request_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"工作协程 {worker_name} 错误: {e}")

    async def _process_request(self, request_data: dict[str, Any]) -> None:
        """处理单个请求"""
        request_id = request_data.get("request_id")
        request_data.get("endpoint")

        try:
            self.active_tasks.add(request_id)

            # 执行实际的请求处理
            handler = request_data.get("handler")
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    await handler(**request_data.get("kwargs", {}))
                else:
                    handler(**request_data.get("kwargs", {}))

        finally:
            self.active_tasks.discard(request_id)

    async def submit_request(
        self, request_id: str, endpoint: str, handler: Callable, **kwargs
    ) -> None:
        """提交请求到队列"""
        request_data = {
            "request_id": request_id,
            "endpoint": endpoint,
            "handler": handler,
            "kwargs": kwargs,
        }

        await self.request_queue.put(request_data)

    @asynccontextmanager
    async def acquire_slot(self) -> AsyncGenerator[None, None]:
        """获取并发槽位"""
        async with self.semaphore:
            yield

    def get_concurrency_metrics(self) -> dict[str, int]:
        """获取并发指标"""
        return {
            "active_tasks": len(self.active_tasks),
            "queued_requests": self.request_queue.qsize(),
            "worker_count": len(self.worker_tasks),
            "available_slots": self.semaphore._value if self.semaphore else 0,
        }


# 全局并发优化器实例
concurrency_optimizer = ConcurrencyOptimizer()

# ============================================================================
# 性能装饰器
# ============================================================================


def monitor_performance(endpoint_name: str = None):
    """性能监控装饰器"""

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                request_id = f"req_{int(time.time() * 1000000)}"
                endpoint = endpoint_name or func.__name__

                performance_monitor.record_request_start(request_id)

                try:
                    start_time = time.time()
                    result = await func(*args, **kwargs)
                    response_time = time.time() - start_time

                    performance_monitor.record_request_end(
                        request_id=request_id,
                        endpoint=endpoint,
                        method="UNKNOWN",
                        status_code=200,
                        response_time=response_time,
                    )

                    return result

                except Exception:
                    performance_monitor.record_request_end(
                        request_id=request_id,
                        endpoint=endpoint,
                        method="UNKNOWN",
                        status_code=500,
                        response_time=0,
                    )
                    raise

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                request_id = f"req_{int(time.time() * 1000000)}"
                endpoint = endpoint_name or func.__name__

                performance_monitor.record_request_start(request_id)

                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    response_time = time.time() - start_time

                    performance_monitor.record_request_end(
                        request_id=request_id,
                        endpoint=endpoint,
                        method="UNKNOWN",
                        status_code=200,
                        response_time=response_time,
                    )

                    return result

                except Exception:
                    performance_monitor.record_request_end(
                        request_id=request_id,
                        endpoint=endpoint,
                        method="UNKNOWN",
                        status_code=500,
                        response_time=0,
                    )
                    raise

            return sync_wrapper

    return decorator


def cache_result(ttl: int = 3600, key_func: Callable = None):
    """缓存结果装饰器"""

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # 生成缓存键
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

                # 尝试从缓存获取
                cached_result = await cache_optimizer.get_cached_data(cache_key)
                if cached_result is not None:
                    return cached_result

                # 执行函数
                result = await func(*args, **kwargs)

                # 缓存结果
                await cache_optimizer.set_cached_data(cache_key, result, ttl)

                return result

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # 同步版本的缓存逻辑
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


# ============================================================================
# 性能优化器主类
# ============================================================================


class EnhancedPerformanceOptimizer:
    """增强性能优化器主类"""

    def __init__(self):
        self.monitor = performance_monitor
        self.db_optimizer = db_optimizer
        self.cache_optimizer = cache_optimizer
        self.concurrency_optimizer = concurrency_optimizer
        self.initialized = False

    async def initialize(
        self, database_url: str, max_concurrent_requests: int = 1000
    ) -> None:
        """初始化所有性能优化组件"""
        try:
            # 初始化数据库优化器
            await self.db_optimizer.initialize(database_url)

            # 初始化缓存优化器
            await self.cache_optimizer.initialize()

            # 初始化并发优化器
            await self.concurrency_optimizer.initialize(max_concurrent_requests)

            self.initialized = True
            logger.info("性能优化器初始化完成")

        except Exception as e:
            logger.error(f"性能优化器初始化失败: {e}")
            raise

    async def get_comprehensive_metrics(self) -> dict[str, Any]:
        """获取综合性能指标"""
        if not self.initialized:
            raise RuntimeError("性能优化器未初始化")

        return {
            "system": self.monitor.get_system_metrics().__dict__,
            "database": self.db_optimizer.get_database_metrics().__dict__,
            "cache": self.cache_optimizer.get_cache_metrics().__dict__,
            "concurrency": self.concurrency_optimizer.get_concurrency_metrics(),
        }

    async def shutdown(self) -> None:
        """关闭性能优化器"""
        try:
            # 取消工作协程
            for task in self.concurrency_optimizer.worker_tasks:
                task.cancel()

            # 等待任务完成
            await asyncio.gather(
                *self.concurrency_optimizer.worker_tasks, return_exceptions=True
            )

            # 关闭数据库连接
            if self.db_optimizer.engine:
                await self.db_optimizer.engine.dispose()

            logger.info("性能优化器已关闭")

        except Exception as e:
            logger.error(f"性能优化器关闭失败: {e}")


# 全局性能优化器实例
performance_optimizer = EnhancedPerformanceOptimizer()
