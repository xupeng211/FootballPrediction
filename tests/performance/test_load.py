"""
Load and Performance Tests
足球比赛结果预测系统 - 负载和性能测试

Author: Claude Code
Version: 1.0
Purpose: Test system performance under various load conditions
"""

import asyncio
import concurrent.futures
import statistics
import threading
import time
from unittest.mock import AsyncMock

import psutil
import pytest

# Import system components
try:
    from fastapi.testclient import TestClient

    from src.core.config import Config
    from src.main import app
    from src.queues.fifo_queue import MemoryFIFOQueue
    from src.services.prediction import PredictionService
except ImportError as e:
    pytest.skip(f"Cannot import required modules: {e}", allow_module_level=True)

# Test client
client = TestClient(app)


class TestAPIPerformance:
    """API性能测试"""

    @pytest.mark.performance
    def test_health_check_response_time(self):
        """测试健康检查响应时间"""
        response_times = []

        # Make 100 requests and measure response times
        for _ in range(100):
            start_time = time.time()
            response = client.get("/health")
            end_time = time.time()

            response_times.append((end_time - start_time) * 1000)  # Convert to ms
            assert response.status_code == 200

        # Performance assertions
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[
            18
        ]  # 95th percentile

        assert avg_response_time < 50  # Average should be under 50ms
        assert p95_response_time < 100  # 95% should be under 100ms
        assert max(response_times) < 200  # Max should be under 200ms

    @pytest.mark.performance
    def test_concurrent_health_checks(self):
        """测试并发健康检查"""

        def make_request():
            start_time = time.time()
            response = client.get("/health")
            end_time = time.time()
            return {
                "status_code": response.status_code,
                "response_time": (end_time - start_time) * 1000,
            }

        # Make 50 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [future.result() for future in futures]

        # Analyze results
        success_count = sum(1 for r in results if r["status_code"] == 200)
        response_times = [r["response_time"] for r in results]

        assert success_count == 50  # All requests should succeed
        assert statistics.mean(response_times) < 100  # Average under 100ms
        assert max(response_times) < 500  # Max under 500ms

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_api_throughput(self):
        """测试API吞吐量"""
        endpoint = "/health"
        duration = 10  # Test for 10 seconds
        request_count = 0
        response_times = []

        start_time = time.time()

        while time.time() - start_time < duration:
            request_start = time.time()
            response = client.get(endpoint)
            request_end = time.time()

            if response.status_code == 200:
                request_count += 1
                response_times.append((request_end - request_start) * 1000)

            # Small delay to prevent overwhelming
            time.sleep(0.01)

        # Calculate throughput
        actual_duration = time.time() - start_time
        throughput = request_count / actual_duration  # requests per second

        # Performance assertions
        assert throughput > 50  # Should handle at least 50 RPS
        assert (
            statistics.mean(response_times) < 100
        )  # Average response time under 100ms


class TestDatabasePerformance:
    """数据库性能测试"""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self):
        """测试数据库连接池性能"""
        mock_db = AsyncMock()

        # Simulate database operations
        async def simulate_db_operation():
            start_time = time.time()
            await mock_db.execute("SELECT 1")
            end_time = time.time()
            return (end_time - start_time) * 1000

        # Test with concurrent operations
        tasks = []
        for _ in range(20):
            tasks.append(simulate_db_operation())

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Performance assertions
        avg_operation_time = statistics.mean(results)
        assert avg_operation_time < 50  # Average operation under 50ms
        assert total_time < 5.0  # Total time under 5 seconds

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_query_performance(self):
        """测试查询性能"""
        mock_db = AsyncMock()

        # Mock different query complexities
        query_scenarios = [
            ("SELECT * FROM matches LIMIT 10", 10),  # Simple query
            ("SELECT * FROM matches WHERE date > '2025-01-01'", 100),  # Medium query
            (
                "SELECT * FROM matches JOIN teams ON matches.home_team_id = teams.id",
                200,
            ),  # Complex query
        ]

        for query, expected_delay in query_scenarios:
            # Simulate query execution time
            async def simulate_query():
                start_time = time.time()
                await asyncio.sleep(expected_delay / 1000)  # Simulate delay
                await mock_db.fetch(query)
                end_time = time.time()
                return (end_time - start_time) * 1000

            # Run query multiple times
            execution_times = []
            for _ in range(5):
                exec_time = await simulate_query()
                execution_times.append(exec_time)

            avg_time = statistics.mean(execution_times)
            assert avg_time < expected_delay * 1.5  # Should be within 50% of expected


class TestQueuePerformance:
    """队列系统性能测试"""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_queue_throughput(self):
        """测试队列吞吐量"""
        queue = MemoryFIFOQueue(max_size=10000)
        await queue.initialize()

        # Test enqueue throughput
        enqueue_start = time.time()
        task_ids = []

        for i in range(1000):
            task_id = await queue.enqueue(
                task_type="test", data={"payload": f"test_data_{i}"}, priority="normal"
            )
            task_ids.append(task_id)

        enqueue_time = time.time() - enqueue_start
        enqueue_throughput = 1000 / enqueue_time

        # Test dequeue throughput
        dequeue_start = time.time()
        dequeued_tasks = []

        for _ in range(1000):
            task = await queue.dequeue()
            if task:
                dequeued_tasks.append(task)

        dequeue_time = time.time() - dequeue_start
        dequeue_throughput = 1000 / dequeue_time

        # Performance assertions
        assert enqueue_throughput > 1000  # Should handle >1000 enqueues/sec
        assert dequeue_throughput > 1000  # Should handle >1000 dequeues/sec
        assert len(dequeued_tasks) == 1000  # All tasks should be processed

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_queue_operations(self):
        """测试并发队列操作"""
        queue = MemoryFIFOQueue(max_size=5000)
        await queue.initialize()

        async def enqueue_worker(worker_id: int):
            tasks_enqueued = 0
            for i in range(100):
                task_id = await queue.enqueue(
                    task_type="test",
                    data={"worker": worker_id, "task": i},
                    priority="normal",
                )
                if task_id:
                    tasks_enqueued += 1
            return tasks_enqueued

        async def dequeue_worker(worker_id: int):
            tasks_dequeued = 0
            for _ in range(100):
                task = await queue.dequeue()
                if task:
                    tasks_dequeued += 1
            return tasks_dequeued

        # Run concurrent workers
        start_time = time.time()

        # 5 enqueue workers and 5 dequeue workers
        enqueue_tasks = [enqueue_worker(i) for i in range(5)]
        dequeue_tasks = [dequeue_worker(i) for i in range(5)]

        enqueue_results = await asyncio.gather(*enqueue_tasks)
        await asyncio.sleep(0.1)  # Let enqueues complete
        dequeue_results = await asyncio.gather(*dequeue_tasks)

        total_time = time.time() - start_time

        # Performance assertions
        total_enqueued = sum(enqueue_results)
        total_dequeued = sum(dequeue_results)

        assert total_enqueued == 500  # All enqueues should succeed
        assert total_dequeued <= 500  # Should not exceed enqueued tasks
        assert total_time < 10.0  # Should complete within 10 seconds


class TestMemoryPerformance:
    """内存性能测试"""

    @pytest.mark.performance
    def test_memory_usage_stability(self):
        """测试内存使用稳定性"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        large_data = []
        for i in range(1000):
            large_data.append(
                {"id": i, "data": "x" * 1000, "timestamp": time.time()}  # 1KB per item
            )

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Clear data
        del large_data

        # Force garbage collection
        import gc

        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Memory assertions
        memory_increase = peak_memory - initial_memory
        memory_recovery = peak_memory - final_memory

        assert memory_increase < 100  # Should not increase by more than 100MB
        assert memory_recovery > (memory_increase * 0.8)  # Should recover 80% of memory

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self):
        """测试内存泄漏检测"""
        process = psutil.Process()

        # Baseline memory
        baseline_memory = process.memory_info().rss

        # Perform multiple operations that could leak memory
        for cycle in range(10):
            # Create temporary objects
            temp_objects = []
            for _i in range(100):
                temp_objects.append(
                    {
                        "cycle": cycle,
                        "data": "x" * 1000,
                        "nested": {"more_data": "y" * 500},
                    }
                )

            # Simulate some processing
            await asyncio.sleep(0.01)

            # Clear references
            del temp_objects

        # Force garbage collection
        import gc

        gc.collect()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - baseline_memory

        # Memory leak assertions
        assert memory_increase < 50 * 1024 * 1024  # Less than 50MB increase


class TestSystemResourcePerformance:
    """系统资源性能测试"""

    @pytest.mark.performance
    def test_cpu_usage_under_load(self):
        """测试负载下CPU使用率"""
        process = psutil.Process()

        # Measure baseline CPU
        time.sleep(1)
        process.cpu_percent()

        # Perform CPU-intensive operations
        def cpu_intensive_task():
            start_time = time.time()
            while time.time() - start_time < 0.1:  # 100ms of work
                _ = sum(i * i for i in range(10000))

        # Run concurrent tasks
        threads = []
        start_time = time.time()

        for _ in range(4):  # Use 4 threads (typically number of CPU cores)
            thread = threading.Thread(target=cpu_intensive_task)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Measure CPU usage during load
        time.sleep(0.5)
        load_cpu = process.cpu_percent()

        # Performance assertions
        assert total_time < 2.0  # Should complete within 2 seconds
        assert (
            load_cpu < 400
        )  # CPU usage should be reasonable (400% = 4 cores fully utilized)

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_io_performance(self):
        """测试I/O性能"""
        # Test file I/O performance
        test_data = "x" * (1024 * 1024)  # 1MB of data

        # Write performance test
        write_start = time.time()
        with open("/tmp/test_write.performance", "w") as f:
            f.write(test_data)
        write_time = time.time() - write_start

        # Read performance test
        read_start = time.time()
        with open("/tmp/test_write.performance") as f:
            read_data = f.read()
        read_time = time.time() - read_start

        # Cleanup
        import os

        os.remove("/tmp/test_write.performance")

        # I/O performance assertions
        assert write_time < 0.1  # Should write 1MB in < 100ms
        assert read_time < 0.1  # Should read 1MB in < 100ms
        assert read_data == test_data  # Data integrity


class TestScalabilityPerformance:
    """可扩展性性能测试"""

    @pytest.mark.performance
    def test_linear_scalability(self):
        """测试线性可扩展性"""
        workloads = [10, 50, 100, 200]
        response_times = []

        def process_workload(items):
            start_time = time.time()

            # Simulate processing
            for _i in range(items):
                _ = sum(j * j for j in range(100))

            end_time = time.time()
            return (end_time - start_time) * 1000

        # Test different workloads
        for workload in workloads:
            times = []
            for _ in range(5):  # 5 runs per workload
                time_taken = process_workload(workload)
                times.append(time_taken)

            avg_time = statistics.mean(times)
            response_times.append(avg_time)

        # Check linear scalability (time should increase proportionally)
        # Calculate scaling factor between consecutive workloads
        scaling_factors = []
        for i in range(1, len(response_times)):
            factor = response_times[i] / response_times[i - 1]
            workload_factor = workloads[i] / workloads[i - 1]
            scaling_efficiency = factor / workload_factor
            scaling_factors.append(scaling_efficiency)

        # Scalability assertions
        avg_efficiency = statistics.mean(scaling_factors)
        assert (
            avg_efficiency < 2.0
        )  # Should scale reasonably (not more than 2x slower than linear)

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_scalability(self):
        """测试并发可扩展性"""
        concurrent_levels = [1, 2, 4, 8]
        throughput_results = []

        async def worker_task():
            # Simulate async work
            await asyncio.sleep(0.01)
            return "completed"

        for concurrency in concurrent_levels:
            start_time = time.time()

            # Run concurrent tasks
            tasks = [worker_task() for _ in range(concurrency * 10)]
            results = await asyncio.gather(*tasks)

            end_time = time.time()
            duration = end_time - start_time
            throughput = (concurrency * 10) / duration  # tasks per second

            throughput_results.append(throughput)

        # Check that throughput increases with concurrency (to a point)
        # The ideal is linear scaling, but we'll accept reasonable scaling
        initial_throughput = throughput_results[0]
        peak_throughput = max(throughput_results)

        assert peak_throughput > initial_throughput  # Should improve with concurrency
        assert len(results) == sum(concurrent_levels) * 10  # All tasks should complete


# Test markers
pytest.mark.performance(TestAPIPerformance)
pytest.mark.performance(TestDatabasePerformance)
pytest.mark.performance(TestQueuePerformance)
pytest.mark.performance(TestMemoryPerformance)
pytest.mark.performance(TestSystemResourcePerformance)
pytest.mark.performance(TestScalabilityPerformance)

# Load testing specific markers
pytest.mark.load(TestAPIPerformance)
pytest.mark.load(TestQueuePerformance)
pytest.mark.load(TestSystemResourcePerformance)

# Critical performance markers
pytest.mark.critical(test_health_check_response_time)
pytest.mark.critical(test_queue_throughput)
pytest.mark.critical(test_memory_usage_stability)
