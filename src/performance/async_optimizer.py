#!/usr/bin/env python3
"""
异步I/O性能优化模块
提供高性能异步操作、连接池优化、批量处理等功能
"""

import asyncio
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, TypeVar

import aiofiles
import aiofiles.os
from sqlalchemy.sql import text

from src.core.logger import get_logger
from src.database.connection import DatabaseManager

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class AsyncPerformanceMetrics:
    """异步性能指标"""

    operation_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    peak_time: float = 0.0
    errors_count: int = 0
    last_reset: float = time.time()


class AsyncConnectionPool:
    """异步连接池优化器"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        min_size: int = 5,
        max_size: int = 20,
        timeout: float = 30.0,
    ):
        self.db_manager = db_manager
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self._pool_size = min_size
        self._active_connections = 0
        self._connection_requests = 0

    @asynccontextmanager
    async def get_connection(self):
        """获取连接池中的连接"""
        start_time = time.time()

        try:
            # 等待可用连接
            while self._active_connections >= self.max_size:
                await asyncio.sleep(0.01)
                if time.time() - start_time > self.timeout:
                    raise TimeoutError("连接池超时")

            self._active_connections += 1
            self._connection_requests += 1

            async with self.db_manager.get_async_session() as session:
                yield session

        finally:
            self._active_connections -= 1

    def get_pool_stats(self) -> dict[str, Any]:
        """获取连接池统计"""
        return {
            "active_connections": self._active_connections,
            "pool_size": self._pool_size,
            "total_requests": self._connection_requests,
            "utilization": self._active_connections / self.max_size,
        }


class AsyncBatchProcessor:
    """异步批量处理器"""

    def __init__(
        self,
        batch_size: int = 100,
        max_concurrent_batches: int = 5,
        timeout: float = 30.0,
    ):
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
        self.timeout = timeout
        self.metrics = AsyncPerformanceMetrics()

    async def process_batch(
        self,
        items: list[T],
        processor: Callable[[list[T]], Any],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[Any]:
        """
        批量处理数据

        Args:
            items: 要处理的数据列表
            processor: 批量处理函数
            progress_callback: 进度回调函数

        Returns:
            处理结果列表
        """
        start_time = time.time()
        results = []

        # 分批处理
        batches = [
            items[i : i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]

        # 创建信号量限制并发批次数
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)

        async def process_single_batch(batch: list[T], batch_index: int) -> Any:
            async with semaphore:
                try:
                    batch_start = time.time()
                    result = await processor(batch)
                    batch_time = time.time() - batch_start

                    # 更新指标
                    self.metrics.operation_count += 1
                    self.metrics.total_time += batch_time
                    self.metrics.avg_time = (
                        self.metrics.total_time / self.metrics.operation_count
                    )
                    self.metrics.peak_time = max(self.metrics.peak_time, batch_time)

                    # 进度回调
                    if progress_callback:
                        progress_callback(batch_index + 1, len(batches))

                    return result

                except Exception as e:
                    self.metrics.errors_count += 1
                    logger.error(f"批次 {batch_index} 处理失败: {e}")
                    raise

        # 并发处理批次
        tasks = [process_single_batch(batch, i) for i, batch in enumerate(batches)]

        try:
            batch_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=self.timeout
            )

            # 处理结果和异常
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"批次处理异常: {result}")
                    results.append(None)
                else:
                    results.append(result)

        except TimeoutError:
            logger.error(f"批量处理超时: {self.timeout}秒")
            raise

        total_time = time.time() - start_time
        logger.info(
            f"批量处理完成: {len(items)}项数据, {len(batches)}个批次, "
            f"耗时 {total_time:.3f}秒"
        )

        return results


class AsyncQueryOptimizer:
    """异步查询优化器"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.query_cache = {}
        self.metrics = AsyncPerformanceMetrics()

    async def execute_optimized_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        use_cache: bool = True,
        fetch_mode: str = "all",  # all, one, many
    ) -> Any:
        """
        执行优化的查询

        Args:
            query: SQL查询语句
            params: 查询参数
            use_cache: 是否使用查询缓存
            fetch_mode: 获取模式

        Returns:
            查询结果
        """
        start_time = time.time()

        # 查询缓存键
        cache_key = f"{query}_{str(params)}" if use_cache else None

        try:
            # 检查缓存
            if cache_key and cache_key in self.query_cache:
                logger.debug(f"使用查询缓存: {cache_key[:50]}...")
                return self.query_cache[cache_key]

            async with self.db_manager.get_async_session() as session:
                # 执行查询
                stmt = text(query)
                result = await session.execute(stmt, params or {})

                # 根据模式获取结果
                if fetch_mode == "one":
                    data = result.scalar_one_or_none()
                elif fetch_mode == "many":
                    data = result.scalars().many()
                else:  # all
                    data = result.scalars().all()

                # 缓存结果（仅对小数据集）
                if cache_key and isinstance(data, (list, tuple)) and len(data) < 1000:
                    self.query_cache[cache_key] = data

                # 更新指标
                query_time = time.time() - start_time
                self.metrics.operation_count += 1
                self.metrics.total_time += query_time
                self.metrics.avg_time = (
                    self.metrics.total_time / self.metrics.operation_count
                )
                self.metrics.peak_time = max(self.metrics.peak_time, query_time)

                logger.debug(f"查询执行完成: {query_time:.3f}秒")

                return data

        except Exception as e:
            self.metrics.errors_count += 1
            logger.error(f"查询执行失败: {e}")
            raise

    async def execute_batch_queries(
        self,
        queries: list[dict[str, Any]],  # [{"query": "...", "params": {...}}, ...]
        max_concurrent: int = 10,
    ) -> list[Any]:
        """
        批量执行查询

        Args:
            queries: 查询列表
            max_concurrent: 最大并发数

        Returns:
            查询结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_single_query(query_data: dict[str, Any]) -> Any:
            async with semaphore:
                return await self.execute_optimized_query(
                    query_data["query"],
                    query_data.get("params"),
                    query_data.get("use_cache", True),
                    query_data.get("fetch_mode", "all"),
                )

        # 并发执行查询
        tasks = [execute_single_query(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"批量查询中的异常: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        return processed_results

    def clear_cache(self):
        """清空查询缓存"""
        self.query_cache.clear()
        logger.info("查询缓存已清空")

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        return {
            "cache_size": len(self.query_cache),
            "operation_count": self.metrics.operation_count,
            "avg_query_time": self.metrics.avg_time,
            "error_rate": (
                self.metrics.errors_count / max(1, self.metrics.operation_count)
            ),
        }


class AsyncFileOptimizer:
    """异步文件操作优化器"""

    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size
        self.metrics = AsyncPerformanceMetrics()

    async def read_file_chunks(
        self,
        file_path: str,
        processor: Callable[[bytes], Any],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Any:
        """
        分块读取文件并处理

        Args:
            file_path: 文件路径
            processor: 数据处理函数
            progress_callback: 进度回调

        Returns:
            处理结果
        """
        start_time = time.time()

        try:
            # 获取文件大小
            file_size = (await aiofiles.os.stat(file_path)).st_size
            processed_bytes = 0

            async with aiofiles.open(file_path, "rb") as file:
                while True:
                    chunk = await file.read(self.chunk_size)
                    if not chunk:
                        break

                    # 处理数据块
                    await processor(chunk)
                    processed_bytes += len(chunk)

                    # 进度回调
                    if progress_callback:
                        progress_callback(processed_bytes, file_size)

            total_time = time.time() - start_time
            logger.info(
                f"异步文件读取完成: {file_path}, "
                f"大小 {file_size} bytes, 耗时 {total_time:.3f}秒"
            )

        except Exception as e:
            self.metrics.errors_count += 1
            logger.error(f"异步文件读取失败: {e}")
            raise

    async def write_file_chunks(
        self,
        file_path: str,
        data_chunks: list[bytes],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """
        分块写入文件

        Args:
            file_path: 文件路径
            data_chunks: 数据块列表
            progress_callback: 进度回调
        """
        start_time = time.time()
        total_chunks = len(data_chunks)

        try:
            async with aiofiles.open(file_path, "wb") as file:
                for i, chunk in enumerate(data_chunks):
                    await file.write(chunk)

                    # 进度回调
                    if progress_callback:
                        progress_callback(i + 1, total_chunks)

            total_time = time.time() - start_time
            total_size = sum(len(chunk) for chunk in data_chunks)

            logger.info(
                f"异步文件写入完成: {file_path}, "
                f"大小 {total_size} bytes, 耗时 {total_time:.3f}秒"
            )

        except Exception as e:
            self.metrics.errors_count += 1
            logger.error(f"异步文件写入失败: {e}")
            raise

    def get_performance_stats(self) -> dict[str, Any]:
        """获取性能统计"""
        return {
            "operation_count": self.metrics.operation_count,
            "avg_time": self.metrics.avg_time,
            "peak_time": self.metrics.peak_time,
            "error_count": self.metrics.errors_count,
            "error_rate": (
                self.metrics.errors_count / max(1, self.metrics.operation_count)
            ),
        }


# 全局优化器实例
_global_connection_pool: AsyncConnectionPool | None = None
_global_batch_processor: AsyncBatchProcessor | None = None
_global_query_optimizer: AsyncQueryOptimizer | None = None
_global_file_optimizer: AsyncFileOptimizer | None = None


def get_connection_pool() -> AsyncConnectionPool:
    """获取全局连接池"""
    global _global_connection_pool
    if _global_connection_pool is None:
        _global_connection_pool = AsyncConnectionPool(DatabaseManager())
    return _global_connection_pool


def get_batch_processor() -> AsyncBatchProcessor:
    """获取全局批量处理器"""
    global _global_batch_processor
    if _global_batch_processor is None:
        _global_batch_processor = AsyncBatchProcessor()
    return _global_batch_processor


def get_query_optimizer() -> AsyncQueryOptimizer:
    """获取全局查询优化器"""
    global _global_query_optimizer
    if _global_query_optimizer is None:
        _global_query_optimizer = AsyncQueryOptimizer(DatabaseManager())
    return _global_query_optimizer


def get_file_optimizer() -> AsyncFileOptimizer:
    """获取全局文件优化器"""
    global _global_file_optimizer
    if _global_file_optimizer is None:
        _global_file_optimizer = AsyncFileOptimizer()
    return _global_file_optimizer


# 便捷装饰器
def async_performance_track(func: Callable) -> Callable:
    """异步性能跟踪装饰器"""

    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.info(f"异步函数 {func.__name__} 执行完成: {execution_time:.3f}秒")

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"异步函数 {func.__name__} 执行失败: {e}, 耗时: {execution_time:.3f}秒"
            )
            raise

    return wrapper


if __name__ == "__main__":

    async def demo_async_optimization():
        """演示异步优化功能"""
        print("🚀 演示异步I/O性能优化")

        # 批量处理演示
        processor = get_batch_processor()

        # 模拟数据
        data = list(range(1000))

        def process_batch(batch: list[int]) -> list[int]:
            return [x * 2 for x in batch]

        def progress_callback(current: int, total: int):
            print(f"进度: {current}/{total} ({current/total*100:.1f}%)")

        results = await processor.process_batch(data, process_batch, progress_callback)

        print(f"✅ 批量处理完成，处理了 {len(results)} 个结果")

        # 查询优化演示
        query_optimizer = get_query_optimizer()

        # 模拟查询
        test_queries = [
            {"query": "SELECT 1 as test", "params": None},
            {"query": "SELECT 2 as test", "params": None},
        ]

        query_results = await query_optimizer.execute_batch_queries(test_queries)
        print(f"✅ 批量查询完成，执行了 {len(query_results)} 个查询")

        # 性能统计
        print(f"📊 批量处理统计: {processor.metrics.__dict__}")
        print(f"📊 查询优化统计: {query_optimizer.get_cache_stats()}")

    asyncio.run(demo_async_optimization())
