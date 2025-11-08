"""
UX优化简单性能测试
测试API响应时间优化的核心功能
"""

import asyncio
import statistics
import time
from typing import Any

import pytest


class MockCache:
    """模拟缓存实现"""

    def __init__(self):
        self._cache = {}

    async def get(self, key: str, default: Any = None):
        await asyncio.sleep(0.001)  # 模拟网络延迟
        return self._cache.get(key, default)

    async def set(self, key: str, value: Any, ttl: int = 300):
        await asyncio.sleep(0.001)  # 模拟网络延迟
        self._cache[key] = value
        return True

    async def delete(self, key: str):
        await asyncio.sleep(0.001)
        self._cache.pop(key, None)
        return True

    async def exists(self, key: str):
        await asyncio.sleep(0.001)
        return key in self._cache


class MockProfiler:
    """模拟性能分析器"""

    async def record_metric(self, metric: dict):
        # 模拟记录指标
        pass


class SimpleAPIOptimizer:
    """简化的API优化器"""

    def __init__(self, cache, profiler):
        self.cache = cache
        self.profiler = profiler
        self.metrics = []
        self.cache_hits = 0
        self.total_requests = 0

    async def optimize_call(self, func, *args, **kwargs):
        """优化API调用"""
        start_time = time.time()
        self.total_requests += 1

        try:
            # 生成缓存键
            cache_key = f"api:{hash(str(args) + str(sorted(kwargs.items())))}"

            # 尝试从缓存获取
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                self.cache_hits += 1
                response_time = (time.time() - start_time) * 1000
                self.metrics.append(response_time)
                return cached_result

            # 执行原函数
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # 缓存结果
            await self.cache.set(cache_key, result)

            # 记录指标
            response_time = (time.time() - start_time) * 1000
            self.metrics.append(response_time)

            return result

        except Exception:
            response_time = (time.time() - start_time) * 1000
            self.metrics.append(response_time)
            raise

    def get_stats(self):
        """获取统计信息"""
        if not self.metrics:
            return {"avg_response_time": 0, "cache_hit_rate": 0, "total_requests": 0}

        return {
            "avg_response_time": statistics.mean(self.metrics),
            "p95_response_time": (
                statistics.quantiles(self.metrics, n=20)[18]
                if len(self.metrics) > 20
                else max(self.metrics)
            ),
            "cache_hit_rate": (
                (self.cache_hits / self.total_requests) * 100
                if self.total_requests > 0
                else 0
            ),
            "total_requests": self.total_requests,
        }


class TestSimplePerformance:
    """简单性能测试"""

    @pytest.fixture
    def mock_cache(self):
        """模拟缓存"""
        return MockCache()

    @pytest.fixture
    def mock_profiler(self):
        """模拟性能分析器"""
        return MockProfiler()

    @pytest.fixture
    def optimizer(self, mock_cache, mock_profiler):
        """API优化器"""
        return SimpleAPIOptimizer(mock_cache, mock_profiler)

    @pytest.mark.asyncio
    async def test_basic_performance_optimization(self, optimizer):
        """测试基本性能优化"""

        # 模拟API函数
        async def api_function(param: str):
            await asyncio.sleep(0.05)  # 模拟50ms处理时间
            return f"processed_{param}"

        # 第一次调用（缓存未命中）
        start_time = time.time()
        result1 = await optimizer.optimize_call(api_function, "test_param")
        first_call_time = (time.time() - start_time) * 1000

        # 第二次调用（缓存命中）
        start_time = time.time()
        result2 = await optimizer.optimize_call(api_function, "test_param")
        second_call_time = (time.time() - start_time) * 1000

        # 验证结果
        assert result1 == result2 == "processed_test_param"

        # 验证性能提升
        assert second_call_time < first_call_time  # 缓存应该更快

        # 验证统计信息
        stats = optimizer.get_stats()
        assert stats["total_requests"] == 2
        assert stats["cache_hit_rate"] == 50.0  # 1次命中，2次请求
        assert stats["avg_response_time"] > 0

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, optimizer):
        """性能基准测试"""

        # 模拟快速API函数
        async def fast_api_function(data_id: int):
            await asyncio.sleep(0.01)  # 10ms处理时间
            return {"id": data_id, "data": f"result_{data_id}"}

        # 执行多次调用
        response_times = []
        iterations = 50

        for i in range(iterations):
            start_time = time.time()
            await optimizer.optimize_call(fast_api_function, i)
            response_time = (time.time() - start_time) * 1000
            response_times.append(response_time)

        # 计算统计数据
        avg_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]

        # 验证性能目标
        assert avg_time < 100, f"平均响应时间 {avg_time:.2f}ms 超过目标 100ms"
        assert p95_time < 150, f"P95响应时间 {p95_time:.2f}ms 超过目标 150ms"

        # 验证优化器统计
        stats = optimizer.get_stats()
        assert stats["total_requests"] == iterations
        assert stats["avg_response_time"] < 100

        print("✅ 性能基准测试通过:")
        print(f"   平均响应时间: {avg_time:.2f}ms")
        print(f"   P95响应时间: {p95_time:.2f}ms")
        print(f"   总请求数: {iterations}")

    @pytest.mark.asyncio
    async def test_cache_effectiveness(self, optimizer):
        """测试缓存效果"""

        # 模拟慢API函数
        async def slow_api_function(param: str):
            await asyncio.sleep(0.1)  # 100ms处理时间
            return f"slow_result_{param}"

        # 第一轮调用（缓存未命中）
        first_round_times = []
        for i in range(5):
            start_time = time.time()
            await optimizer.optimize_call(
                slow_api_function, f"param_{i % 2}"
            )  # 重复参数
            response_time = (time.time() - start_time) * 1000
            first_round_times.append(response_time)

        # 第二轮调用（部分缓存命中）
        second_round_times = []
        for i in range(5):
            start_time = time.time()
            await optimizer.optimize_call(
                slow_api_function, f"param_{i % 2}"
            )  # 重复参数
            response_time = (time.time() - start_time) * 1000
            second_round_times.append(response_time)

        # 验证缓存效果
        first_round_avg = statistics.mean(first_round_times)
        second_round_avg = statistics.mean(second_round_times)

        assert second_round_avg < first_round_avg, "缓存应该提升性能"

        stats = optimizer.get_stats()
        assert (
            stats["cache_hit_rate"] > 30
        ), f"缓存命中率 {stats['cache_hit_rate']:.1f}% 过低"

        print("✅ 缓存效果测试通过:")
        print(f"   第一轮平均时间: {first_round_avg:.2f}ms")
        print(f"   第二轮平均时间: {second_round_avg:.2f}ms")
        print(f"   缓存命中率: {stats['cache_hit_rate']:.1f}%")

    @pytest.mark.asyncio
    async def test_concurrent_performance(self, optimizer):
        """测试并发性能"""

        async def concurrent_api_function(param: str):
            await asyncio.sleep(0.02)  # 20ms处理时间
            return f"concurrent_{param}"

        # 并发执行多个请求
        tasks = []
        start_time = time.time()

        for i in range(20):
            task = optimizer.optimize_call(concurrent_api_function, f"param_{i}")
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000

        # 验证结果
        assert len(results) == 20
        assert all(result.startswith("concurrent_") for result in results)

        # 验证并发性能
        avg_time_per_request = total_time / 20
        assert (
            avg_time_per_request < 50
        ), f"并发平均时间 {avg_time_per_request:.2f}ms 过高"

        stats = optimizer.get_stats()
        print("✅ 并发性能测试通过:")
        print(f"   总执行时间: {total_time:.2f}ms")
        print(f"   平均每请求时间: {avg_time_per_request:.2f}ms")
        print("   总请求数: 20")


@pytest.mark.asyncio
async def test_target_response_time():
    """测试目标响应时间 < 200ms"""
    cache = MockCache()
    profiler = MockProfiler()
    optimizer = SimpleAPIOptimizer(cache, profiler)

    # 模拟中等复杂度的API
    async def medium_api_function(operation: str, data: dict):
        # 模拟数据处理时间
        await asyncio.sleep(0.03)  # 30ms基础处理
        if "complex" in operation:
            await asyncio.sleep(0.05)  # 复杂操作额外50ms

        return {"operation": operation, "processed": True, "data_size": len(data)}

    # 执行多种操作测试
    operations = [
        ("simple", {"key": "value"}),
        ("simple", {"items": [1, 2, 3]}),
        ("complex", {"large_data": list(range(100))}),
        ("simple", {"test": True}),
        ("complex", {"nested": {"a": 1, "b": 2}}),
    ]

    response_times = []

    for operation, data in operations:
        # 第一次调用
        start_time = time.time()
        await optimizer.optimize_call(medium_api_function, operation, data)
        first_time = (time.time() - start_time) * 1000
        response_times.append(first_time)

        # 第二次调用（应该命中缓存）
        start_time = time.time()
        await optimizer.optimize_call(medium_api_function, operation, data)
        second_time = (time.time() - start_time) * 1000
        response_times.append(second_time)

    # 验证目标
    avg_time = statistics.mean(response_times)
    max_time = max(response_times)

    assert avg_time < 200, f"平均响应时间 {avg_time:.2f}ms 超过200ms目标"
    assert max_time < 300, f"最大响应时间 {max_time:.2f}ms 过高"

    stats = optimizer.get_stats()
    cache_hit_rate = stats["cache_hit_rate"]

    print("✅ 目标响应时间测试通过:")
    print(f"   平均响应时间: {avg_time:.2f}ms (目标: <200ms)")
    print(f"   最大响应时间: {max_time:.2f}ms")
    print(f"   缓存命中率: {cache_hit_rate:.1f}%")
    print(f"   总请求数: {len(response_times)}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_target_response_time())
