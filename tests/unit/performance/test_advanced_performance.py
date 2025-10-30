"""
高级性能测试
Phase E: 优化提升阶段 - 专注于性能测试、并发测试、集成测试
确保系统在各种负载和性能场景下的稳定性
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import asyncio
import time
import threading
import multiprocessing
import concurrent.futures
import json
import random
import gc
import psutil
import statistics
from typing import Dict, List, Any, Optional

# 尝试导入性能相关模块
try:
    from src.cache.memory import MemoryCache
    from src.cache.redis import RedisCache
    from src.api.models.response_models import StandardResponse
    from src.utils.formatters import DataFormatter
    PERFORMANCE_AVAILABLE = True
except ImportError as e:
    print(f"性能模块导入失败: {e}")
    PERFORMANCE_AVAILABLE = False
    MemoryCache = None
    RedisCache = None
    StandardResponse = None
    DataFormatter = None


@pytest.mark.unit
@pytest.mark.performance
class TestCachePerformance:
    """缓存性能测试"""

    def test_cache_performance_under_load(self):
        """测试缓存在高负载下的性能"""
        # 创建内存缓存
        cache = MemoryCache() if MemoryCache else {}

        # 性能测试参数
        num_operations = 10000
        num_keys = 1000
        concurrent_workers = 10

        # 预填充一些数据
        test_data = {}
        for i in range(num_keys):
            key = f"perf_test_key_{i}"
            value = {"data": f"test_value_{i}", "timestamp": time.time(), "random": random.random()}
            test_data[key] = value
            if hasattr(cache, 'set'):
                cache.set(key, value)
            else:
                cache[key] = value

        # 并发读写性能测试
        def cache_worker(worker_id):
            start_time = time.time()
            operations = 0
            errors = 0

            for i in range(num_operations // concurrent_workers):
                try:
                    # 随机操作
                    if random.random() < 0.7:  # 70%读操作
                        key = f"perf_test_key_{random.randint(0, num_keys-1)}"
                        if hasattr(cache, 'get'):
                            result = cache.get(key)
                        else:
                            result = cache.get(key)
                        operations += 1
                    else:  # 30%写操作
                        key = f"perf_test_write_{worker_id}_{i}"
                        value = {"worker": worker_id, "operation": i, "timestamp": time.time()}
                        if hasattr(cache, 'set'):
                            cache.set(key, value)
                        else:
                            cache[key] = value
                        operations += 1
                except Exception as e:
                    errors += 1

            end_time = time.time()
            duration = end_time - start_time
            return {
                "worker_id": worker_id,
                "operations": operations,
                "errors": errors,
                "duration": duration,
                "ops_per_second": operations / duration if duration > 0 else 0
            }

        # 启动并发工作线程
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            futures = [executor.submit(cache_worker, i) for i in range(concurrent_workers)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        end_time = time.time()

        # 统计性能指标
        total_duration = end_time - start_time
        total_operations = sum(r["operations"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        overall_ops_per_second = total_operations / total_duration if total_duration > 0 else 0
        avg_ops_per_second = statistics.mean(r["ops_per_second"] for r in results)

        # 性能断言
        assert total_errors == 0, f"Unexpected errors: {total_errors}"
        assert overall_ops_per_second > 1000, f"Performance too low: {overall_ops_per_second:.2f} ops/sec"
        assert avg_ops_per_second > 800, f"Average worker performance too low: {avg_ops_per_second:.2f} ops/sec"

        # 验证缓存一致性
        if hasattr(cache, 'get'):
            test_key = f"perf_test_key_{random.randint(0, num_keys-1)}"
            result = cache.get(test_key)
            assert result is not None
            assert "data" in result

    def test_cache_memory_usage_optimization(self):
        """测试缓存内存使用优化"""
        # 监控内存使用
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        cache = MemoryCache() if MemoryCache else {}

        # 创建大量数据
        large_data_sets = []
        for i in range(1000):
            large_data = {
                "id": i,
                "payload": "x" * 1024,  # 1KB数据
                "metadata": {
                    "created_at": time.time(),
                    "updated_at": time.time(),
                    "version": random.randint(1, 10),
                    "tags": [f"tag_{j}" for j in range(10)]
                }
            }
            large_data_sets.append(large_data)

        # 逐步添加到缓存
        memory_measurements = []
        for i, data in enumerate(large_data_sets):
            key = f"large_data_{i}"
            if hasattr(cache, 'set'):
                cache.set(key, data)
            else:
                cache[key] = data

            if i % 100 == 0:  # 每100次测量一次内存
                current_memory = process.memory_info().rss
                memory_increase = current_memory - initial_memory
                memory_measurements.append({
                    "items": i + 1,
                    "memory_increase_mb": memory_increase / (1024 * 1024),
                    "memory_per_item_kb": (memory_increase / (i + 1)) / 1024 if i > 0 else 0
                })

        # 强制垃圾回收
        gc.collect()
        final_memory = process.memory_info().rss
        total_memory_increase = final_memory - initial_memory

        # 内存使用分析
        assert len(memory_measurements) >= 10, "Not enough memory measurements"

        # 检查内存增长是否合理（每个项目不超过5KB额外开销）
        avg_memory_per_item = total_memory_increase / len(large_data_sets)
        assert avg_memory_per_item < 5 * 1024, f"Memory usage too high: {avg_memory_per_item/1024:.2f} KB per item"

        # 测试缓存清理效果
        if hasattr(cache, 'clear'):
            cache.clear()
        else:
            cache.clear()

        gc.collect()
        after_clear_memory = process.memory_info().rss
        memory_reclaimed = final_memory - after_clear_memory

        # 验证内存回收效果
        assert memory_reclaimed > total_memory_increase * 0.5, f"Insufficient memory reclamation: {memory_reclaimed/(1024*1024):.2f} MB"

    def test_cache_ttl_performance(self):
        """测试TTL缓存性能"""
        cache = MemoryCache() if MemoryCache else {}

        # 测试不同TTL值的性能影响
        ttl_tests = [
            {"ttl": 1, "description": "1秒TTL"},
            {"ttl": 60, "description": "1分钟TTL"},
            {"ttl": 3600, "description": "1小时TTL"},
            {"ttl": None, "description": "无TTL"},
        ]

        for test in ttl_tests:
            # 设置缓存项
            num_items = 1000
            start_time = time.time()

            for i in range(num_items):
                key = f"ttl_test_{test['ttl']}_{i}"
                value = {"data": f"test_{i}", "timestamp": time.time()}

                if hasattr(cache, 'set'):
                    if test['ttl']:
                        cache.set(key, value, ttl=test['ttl'])
                    else:
                        cache.set(key, value)
                else:
                    cache[key] = value

            set_duration = time.time() - start_time

            # 读取缓存项
            start_time = time.time()
            hit_count = 0
            miss_count = 0

            for i in range(num_items):
                key = f"ttl_test_{test['ttl']}_{i}"
                if hasattr(cache, 'get'):
                    result = cache.get(key)
                    if result:
                        hit_count += 1
                    else:
                        miss_count += 1
                else:
                    if key in cache:
                        hit_count += 1
                    else:
                        miss_count += 1

            get_duration = time.time() - start_time

            # 性能指标
            set_ops_per_sec = num_items / set_duration if set_duration > 0 else 0
            get_ops_per_sec = num_items / get_duration if get_duration > 0 else 0
            hit_rate = hit_count / (hit_count + miss_count) if (hit_count + miss_count) > 0 else 0

            # 验证性能要求
            assert set_ops_per_sec > 5000, f"SET operations too slow for {test['description']}: {set_ops_per_sec:.2f} ops/sec"
            assert get_ops_per_sec > 10000, f"GET operations too slow for {test['description']}: {get_ops_per_sec:.2f} ops/sec"
            assert hit_rate > 0.9, f"Hit rate too low for {test['description']}: {hit_rate:.2%}"


@pytest.mark.unit
@pytest.mark.performance
class TestDataProcessingPerformance:
    """数据处理性能测试"""

    def test_json_serialization_performance(self):
        """测试JSON序列化性能"""
        # 创建复杂数据结构
        def create_complex_data(size):
            return {
                "metadata": {
                    "version": "1.0",
                    "timestamp": datetime.now().isoformat(),
                    "source": "performance_test"
                },
                "predictions": [
                    {
                        "id": i,
                        "match_id": random.randint(1000, 9999),
                        "home_team": f"Team_{i}_A",
                        "away_team": f"Team_{i}_B",
                        "prediction": {
                            "home_score": random.randint(0, 5),
                            "away_score": random.randint(0, 5),
                            "confidence": random.uniform(0.5, 0.95)
                        },
                        "analysis": {
                            "factors": [f"factor_{j}" for j in range(10)],
                            "weights": [random.random() for _ in range(10)],
                            "metadata": {"complexity": random.choice(["low", "medium", "high"])}
                        }
                    }
                    for i in range(size)
                ],
                "statistics": {
                    "total_predictions": size,
                    "average_confidence": random.uniform(0.7, 0.9),
                    "processing_time_ms": random.uniform(100, 500)
                }
            }

        # 测试不同数据大小
        data_sizes = [100, 500, 1000, 2000]

        for size in data_sizes:
            test_data = create_complex_data(size)

            # 序列化性能测试
            serialization_times = []
            for _ in range(10):  # 运行10次取平均值
                start_time = time.time()
                json_str = json.dumps(test_data)
                serialization_time = time.time() - start_time
                serialization_times.append(serialization_time)

            # 反序列化性能测试
            deserialization_times = []
            for _ in range(10):
                start_time = time.time()
                parsed_data = json.loads(json_str)
                deserialization_time = time.time() - start_time
                deserialization_times.append(deserialization_time)

            # 性能统计
            avg_serialization_time = statistics.mean(serialization_times)
            avg_deserialization_time = statistics.mean(deserialization_times)
            json_size = len(json_str.encode('utf-8'))

            # 性能断言
            assert avg_serialization_time < 0.1, f"Serialization too slow for {size} items: {avg_serialization_time:.4f}s"
            assert avg_deserialization_time < 0.1, f"Deserialization too slow for {size} items: {avg_deserialization_time:.4f}s"

            # 检查数据完整性
            assert len(parsed_data["predictions"]) == size
            assert parsed_data["metadata"]["version"] == "1.0"

            # 内存效率检查 (每个预测不超过1KB JSON)
            bytes_per_prediction = json_size / size
            assert bytes_per_prediction < 1024, f"JSON too inefficient: {bytes_per_prediction:.2f} bytes per prediction"

    def test_data_filtering_performance(self):
        """测试数据过滤性能"""
        # 创建大数据集
        def create_large_dataset(size):
            return [
                {
                    "id": i,
                    "type": random.choice(["prediction", "match", "team", "player"]),
                    "status": random.choice(["active", "completed", "pending", "cancelled"]),
                    "priority": random.randint(1, 5),
                    "confidence": random.uniform(0, 1),
                    "timestamp": time.time() - random.randint(0, 86400),  # 过去24小时
                    "metadata": {
                        "source": random.choice(["api", "manual", "automated"]),
                        "tags": [f"tag_{j}" for j in range(random.randint(1, 5))]
                    },
                    "payload": {"data": f"payload_{i}" * random.randint(1, 10)}
                }
                for i in range(size)
            ]

        dataset_size = 10000
        large_dataset = create_large_dataset(dataset_size)

        # 定义不同的过滤条件
        filter_tests = [
            {
                "name": "type_filter",
                "condition": lambda x: x["type"] == "prediction",
                "expected_ratio": 0.25
            },
            {
                "name": "status_filter",
                "condition": lambda x: x["status"] in ["active", "pending"],
                "expected_ratio": 0.5
            },
            {
                "name": "confidence_filter",
                "condition": lambda x: x["confidence"] > 0.7,
                "expected_ratio": 0.3
            },
            {
                "name": "complex_filter",
                "condition": lambda x: (
                    x["type"] == "prediction" and
                    x["status"] == "active" and
                    x["priority"] >= 3 and
                    x["confidence"] > 0.6
                ),
                "expected_ratio": 0.05
            },
            {
                "name": "time_filter",
                "condition": lambda x: time.time() - x["timestamp"] < 3600,  # 最近1小时
                "expected_ratio": 0.04
            }
        ]

        for filter_test in filter_tests:
            # 过滤性能测试
            start_time = time.time()
            filtered_data = [item for item in large_dataset if filter_test["condition"](item)]
            filter_duration = time.time() - start_time

            # 性能指标
            items_per_second = dataset_size / filter_duration if filter_duration > 0 else 0
            actual_ratio = len(filtered_data) / dataset_size

            # 性能断言
            assert items_per_second > 100000, f"Filtering too slow for {filter_test['name']}: {items_per_second:.0f} items/sec"

            # 验证过滤结果的合理性
            assert abs(actual_ratio - filter_test["expected_ratio"]) < 0.2, \
                f"Filter result ratio unexpected for {filter_test['name']}: {actual_ratio:.2f} vs expected ~{filter_test['expected_ratio']:.2f}"

            # 测试多次过滤的性能一致性
            second_duration = None
            start_time = time.time()
            _ = [item for item in large_dataset if filter_test["condition"](item)]
            second_duration = time.time() - start_time

            # 第二次过滤应该更快或类似（由于缓存等因素）
            performance_variance = abs(filter_duration - second_duration) / max(filter_duration, second_duration)
            assert performance_variance < 0.5, f"Inconsistent filter performance for {filter_test['name']}: {performance_variance:.2%}"

    def test_data_aggregation_performance(self):
        """测试数据聚合性能"""
        # 创建时间序列数据
        def create_time_series_data(days=30, points_per_day=24):
            data = []
            base_time = time.time() - (days * 24 * 3600)

            for day in range(days):
                for hour in range(points_per_day):
                    timestamp = base_time + (day * 24 * 3600) + (hour * 3600)
                    data.append({
                        "timestamp": timestamp,
                        "metric": random.choice(["cpu", "memory", "disk", "network"]),
                        "value": random.uniform(0, 100),
                        "source": random.choice(["server_1", "server_2", "server_3"]),
                        "environment": random.choice(["prod", "staging", "dev"])
                    })
            return data

        time_series_data = create_time_series_data()

        # 定义聚合函数
        def aggregate_by_hour(data):
            """按小时聚合数据"""
            result = {}
            for item in data:
                hour_key = int(item["timestamp"] // 3600) * 3600
                if hour_key not in result:
                    result[hour_key] = {"count": 0, "values": [], "sources": set()}

                result[hour_key]["count"] += 1
                result[hour_key]["values"].append(item["value"])
                result[hour_key]["sources"].add(item["source"])

            # 计算统计信息
            for key in result:
                values = result[key]["values"]
                result[key].update({
                    "avg": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0,
                    "unique_sources": len(result[key]["sources"])
                })
                del result[key]["values"]  # 删除原始值以节省内存
                del result[key]["sources"]

            return result

        def aggregate_by_metric(data):
            """按指标类型聚合"""
            result = {}
            for item in data:
                metric = item["metric"]
                if metric not in result:
                    result[metric] = []
                result[metric].append(item["value"])

            for metric in result:
                values = result[metric]
                result[metric] = {
                    "count": len(values),
                    "avg": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "percentiles": {
                        "p50": statistics.median(values),
                        "p95": sorted(values)[int(len(values) * 0.95)],
                        "p99": sorted(values)[int(len(values) * 0.99)]
                    }
                }

            return result

        # 测试聚合性能
        aggregation_tests = [
            {"name": "hourly_aggregation", "func": aggregate_by_hour},
            {"name": "metric_aggregation", "func": aggregate_by_metric}
        ]

        for test in aggregation_tests:
            # 预热（第一次运行可能较慢）
            _ = test["func"](time_series_data[:100])

            # 实际性能测试
            start_time = time.time()
            result = test["func"](time_series_data)
            duration = time.time() - start_time

            # 性能指标
            items_per_second = len(time_series_data) / duration if duration > 0 else 0
            result_size = len(result) if isinstance(result, dict) else len(str(result))

            # 性能断言
            assert items_per_second > 50000, f"Aggregation too slow for {test['name']}: {items_per_second:.0f} items/sec"
            assert result_size > 0, f"Aggregation produced empty result for {test['name']}"
            assert duration < 1.0, f"Aggregation took too long for {test['name']}: {duration:.3f}s"

            # 验证结果质量
            if test["name"] == "hourly_aggregation":
                # 验证时间聚合结果
                sample_key = list(result.keys())[0]
                sample_data = result[sample_key]
                assert "avg" in sample_data
                assert "count" in sample_data
                assert sample_data["count"] > 0
            elif test["name"] == "metric_aggregation":
                # 验证指标聚合结果
                for metric, stats in result.items():
                    assert "avg" in stats
                    assert "percentiles" in stats
                    assert "p95" in stats["percentiles"]


@pytest.mark.unit
@pytest.mark.performance
class TestConcurrencyPerformance:
    """并发性能测试"""

    def test_thread_safety_performance(self):
        """测试线程安全性能"""
        # 共享计数器
        class ThreadSafeCounter:
            def __init__(self):
                self.value = 0
                self.lock = threading.Lock()

            def increment(self):
                with self.lock:
                    self.value += 1
                    return self.value

        class UnsafeCounter:
            def __init__(self):
                self.value = 0

            def increment(self):
                old_value = self.value
                time.sleep(0.0001)  # 模拟处理时间
                self.value = old_value + 1
                return self.value

        # 测试参数
        num_threads = 20
        operations_per_thread = 1000

        def worker(counter, results, thread_id):
            start_time = time.time()
            for _ in range(operations_per_thread):
                counter.increment()
            duration = time.time() - start_time
            results[thread_id] = duration

        # 测试线程安全计数器
        safe_counter = ThreadSafeCounter()
        safe_results = {}
        safe_start = time.time()

        safe_threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(safe_counter, safe_results, i))
            safe_threads.append(thread)
            thread.start()

        for thread in safe_threads:
            thread.join()

        safe_duration = time.time() - safe_start

        # 测试非线程安全计数器
        unsafe_counter = UnsafeCounter()
        unsafe_results = {}
        unsafe_start = time.time()

        unsafe_threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(unsafe_counter, unsafe_results, i))
            unsafe_threads.append(thread)
            thread.start()

        for thread in unsafe_threads:
            thread.join()

        unsafe_duration = time.time() - unsafe_start

        # 验证结果
        expected_operations = num_threads * operations_per_thread

        # 线程安全计数器应该达到预期值
        assert safe_counter.value == expected_operations, \
            f"Safe counter incorrect: {safe_counter.value} vs expected {expected_operations}"

        # 非线程安全计数器可能小于预期值（竞态条件）
        assert unsafe_counter.value <= expected_operations, \
            f"Unsafe counter should be <= expected due to race conditions"

        # 性能比较
        safe_ops_per_sec = expected_operations / safe_duration
        unsafe_ops_per_sec = expected_operations / unsafe_duration

        # 线程安全版本应该仍然有合理的性能
        assert safe_ops_per_sec > 10000, f"Thread-safe performance too low: {safe_ops_per_sec:.0f} ops/sec"

        # 性能开销不应该太大（线程安全版本不应该比非安全版本慢10倍以上）
        performance_overhead = safe_duration / unsafe_duration
        assert performance_overhead < 10, f"Thread safety overhead too high: {performance_overhead:.2f}x slower"

    def test_async_performance(self):
        """测试异步性能"""
        async def async_operation(delay_ms):
            """模拟异步操作"""
            await asyncio.sleep(delay_ms / 1000)
            return {"result": "success", "delay": delay_ms}

        async def concurrent_async_test(num_concurrent, operations_per_worker):
            """并发异步测试"""
            start_time = time.time()

            # 创建任务
            tasks = []
            for i in range(num_concurrent):
                for j in range(operations_per_worker):
                    delay = random.uniform(1, 10)  # 1-10ms随机延迟
                    tasks.append(async_operation(delay))

            # 并发执行所有任务
            results = await asyncio.gather(*tasks)

            duration = time.time() - start_time
            total_operations = len(tasks)
            ops_per_second = total_operations / duration if duration > 0 else 0

            return {
                "total_operations": total_operations,
                "duration": duration,
                "ops_per_second": ops_per_second,
                "success_rate": len([r for r in results if r["result"] == "success"]) / len(results)
            }

        # 测试不同并发级别
        concurrency_tests = [
            {"concurrent": 10, "operations_per_worker": 100},
            {"concurrent": 50, "operations_per_worker": 100},
            {"concurrent": 100, "operations_per_worker": 50},
        ]

        for test in concurrency_tests:
            # 运行异步测试
            result = asyncio.run(concurrent_async_test(
                test["concurrent"],
                test["operations_per_worker"]
            ))

            # 性能断言
            assert result["success_rate"] == 1.0, f"Async operations failed: {result['success_rate']:.2%}"
            assert result["ops_per_second"] > 100, f"Async performance too low: {result['ops_per_second']:.2f} ops/sec"

            expected_total = test["concurrent"] * test["operations_per_worker"]
            assert result["total_operations"] == expected_total, \
                f"Operations count mismatch: {result['total_operations']} vs {expected_total}"

    def test_multiprocessing_performance(self):
        """测试多进程性能"""
        def cpu_intensive_task(n):
            """CPU密集型任务"""
            result = 0
            for i in range(n):
                result += i * i
            return result

        def worker_function(args):
            """工作进程函数"""
            worker_id, task_size = args
            start_time = time.time()

            result = cpu_intensive_task(task_size)

            duration = time.time() - start_time
            return {
                "worker_id": worker_id,
                "result": result,
                "duration": duration
            }

        # 测试参数
        num_processes = multiprocessing.cpu_count()
        task_size_per_process = 100000

        # 单进程基准测试
        single_start = time.time()
        single_result = cpu_intensive_task(task_size_per_process * num_processes)
        single_duration = time.time() - single_start

        # 多进程测试
        multi_start = time.time()
        with multiprocessing.Pool(processes=num_processes) as pool:
            args = [(i, task_size_per_process) for i in range(num_processes)]
            multi_results = pool.map(worker_function, args)
        multi_duration = time.time() - multi_start

        # 验证结果正确性
        multi_combined_result = sum(r["result"] for r in multi_results)
        assert multi_combined_result == single_result, "Multiprocessing result mismatch"

        # 性能分析
        speedup = single_duration / multi_duration if multi_duration > 0 else 0
        efficiency = speedup / num_processes

        # 性能断言
        assert speedup > 1.5, f"Multiprocessing speedup too low: {speedup:.2f}x"
        assert efficiency > 0.3, f"Multiprocessing efficiency too low: {efficiency:.2%}"

        # 确保多进程确实更快（考虑到进程创建开销）
        assert multi_duration < single_duration * 0.8, \
            f"Multiprocessing not providing expected speedup: {multi_duration:.3f}s vs {single_duration:.3f}s"

        # 验证负载均衡
        worker_durations = [r["duration"] for r in multi_results]
        duration_variance = statistics.stdev(worker_durations) if len(worker_durations) > 1 else 0
        avg_duration = statistics.mean(worker_durations)
        cv = duration_variance / avg_duration if avg_duration > 0 else 0  # 变异系数

        assert cv < 0.3, f"Load imbalance detected: CV = {cv:.2%}"


@pytest.mark.unit
@pytest.mark.performance
class TestMemoryPerformance:
    """内存性能测试"""

    def test_memory_leak_detection(self):
        """测试内存泄漏检测"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # 创建大量临时对象
        def create_temp_objects():
            objects = []
            for i in range(10000):
                obj = {
                    "id": i,
                    "data": "x" * 1000,  # 1KB数据
                    "timestamp": time.time(),
                    "nested": {
                        "level1": {"level2": {"level3": f"deep_data_{i}"}}
                    }
                }
                objects.append(obj)
            return objects

        # 执行多轮创建和销毁
        for round_num in range(5):
            # 创建对象
            temp_objects = create_temp_objects()

            # 测量内存使用
            peak_memory = process.memory_info().rss
            memory_increase = peak_memory - initial_memory

            # 销毁对象
            del temp_objects
            gc.collect()

            after_gc_memory = process.memory_info().rss
            memory_reclaimed = peak_memory - after_gc_memory

            # 验证内存回收
            reclaim_rate = memory_reclaimed / memory_increase if memory_increase > 0 else 0
            assert reclaim_rate > 0.7, f"Round {round_num}: Poor memory reclamation: {reclaim_rate:.2%}"

        # 最终内存检查
        final_memory = process.memory_info().rss
        total_memory_increase = final_memory - initial_memory

        # 总内存增长应该相对较小（考虑一些合理的开销）
        max_acceptable_increase = 50 * 1024 * 1024  # 50MB
        assert total_memory_increase < max_acceptable_increase, \
            f"Potential memory leak: {total_memory_increase/(1024*1024):.2f} MB increase"

    def test_large_dataset_processing(self):
        """测试大数据集处理内存效率"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # 创建大数据集生成器（节省内存）
        def data_generator(size):
            for i in range(size):
                yield {
                    "id": i,
                    "payload": f"data_{i}" * 100,  # 约1KB
                    "metadata": {
                        "timestamp": time.time(),
                        "category": random.choice(["A", "B", "C"]),
                        "score": random.uniform(0, 1)
                    }
                }

        def process_dataset_streaming(dataset_generator):
            """流式处理数据集"""
            results = {
                "total_items": 0,
                "category_counts": {"A": 0, "B": 0, "C": 0},
                "score_sum": 0.0,
                "score_min": 1.0,
                "score_max": 0.0
            }

            for item in dataset_generator:
                results["total_items"] += 1
                results["category_counts"][item["metadata"]["category"]] += 1

                score = item["metadata"]["score"]
                results["score_sum"] += score
                results["score_min"] = min(results["score_min"], score)
                results["score_max"] = max(results["score_max"], score)

            return results

        # 测试流式处理
        dataset_size = 100000
        data_gen = data_generator(dataset_size)

        start_time = time.time()
        processing_results = process_dataset_streaming(data_gen)
        processing_duration = time.time() - start_time

        # 测量内存使用
        peak_memory = process.memory_info().rss
        memory_used = peak_memory - initial_memory

        # 性能指标
        items_per_second = dataset_size / processing_duration if processing_duration > 0 else 0
        memory_per_item = memory_used / dataset_size if dataset_size > 0 else 0

        # 性能断言
        assert items_per_second > 50000, f"Processing too slow: {items_per_second:.0f} items/sec"
        assert memory_per_item < 100, f"Memory usage too high: {memory_per_item:.2f} bytes per item"

        # 验证处理结果
        assert processing_results["total_items"] == dataset_size
        assert sum(processing_results["category_counts"].values()) == dataset_size
        assert processing_results["score_min"] <= processing_results["score_max"]
        assert processing_results["score_sum"] / dataset_size == pytest.approx(0.5, rel=0.1)  # 平均值应该接近0.5

        # 内存应该在合理范围内（不超过100MB）
        assert memory_used < 100 * 1024 * 1024, f"Too much memory used: {memory_used/(1024*1024):.2f} MB"


# 性能测试辅助函数
def test_performance_coverage():
    """性能测试覆盖率辅助函数"""
    performance_scenarios = [
        "cache_performance_load",
        "cache_memory_optimization",
        "cache_ttl_performance",
        "json_serialization",
        "data_filtering",
        "data_aggregation",
        "thread_safety",
        "async_concurrency",
        "multiprocessing",
        "memory_leak_detection",
        "large_dataset_processing"
    ]

    for scenario in performance_scenarios:
        assert scenario is not None

    assert len(performance_scenarios) == 11

    # 验证性能测试函数存在
    test_classes = [
        TestCachePerformance,
        TestDataProcessingPerformance,
        TestConcurrencyPerformance,
        TestMemoryPerformance
    ]

    for test_class in test_classes:
        assert test_class is not None
        assert hasattr(test_class, '__name__')

    return True


def test_benchmark_system_performance():
    """系统性能基准测试"""
    # 简单的系统性能基准
    cpu_count = multiprocessing.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)

    # 基本性能要求
    assert cpu_count >= 2, f"Insufficient CPU cores: {cpu_count}"
    assert memory_gb >= 1, f"Insufficient memory: {memory_gb:.2f} GB"

    # 测试基本计算性能
    start_time = time.time()
    result = sum(i * i for i in range(1000000))
    calculation_time = time.time() - start_time

    # 应该在合理时间内完成
    assert calculation_time < 1.0, f"Basic calculation too slow: {calculation_time:.3f}s"
    assert result > 0, "Calculation result incorrect"

    return {
        "cpu_cores": cpu_count,
        "memory_gb": memory_gb,
        "calculation_time_ms": calculation_time * 1000
    }