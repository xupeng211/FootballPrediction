"""
API性能测试
API Performance Tests

测试API端点的性能指标，包括：
- 响应时间
- 吞吐量
- 并发处理能力
- 资源使用情况
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
import json


@pytest.mark.performance
@pytest.mark.api
class TestAPIResponseTime:
    """API响应时间测试"""

    async def test_api_endpoints_response_time(self, api_client):
        """测试各API端点的响应时间"""
        endpoints = [
            ("/health", "GET"),
            ("/teams", "GET"),
            ("/matches", "GET"),
            ("/predictions", "GET"),
        ]

        response_times = {}

        for endpoint, method in endpoints:
            times = []

            # 每个端点测试10次
            for _ in range(10):
                start_time = time.time()

                if method == "GET":
                    response = await api_client.get(endpoint)
                elif method == "POST":
                    response = await api_client.post(endpoint, json={"test": "data"})

                end_time = time.time()

                # 只记录成功请求的响应时间
                if response.status_code < 400:
                    times.append((end_time - start_time) * 1000)  # 转换为毫秒

            # 计算统计指标
            if times:
                response_times[endpoint] = {
                    "avg": statistics.mean(times),
                    "median": statistics.median(times),
                    "min": min(times),
                    "max": max(times),
                    "p95": sorted(times)[int(len(times) * 0.95)],
                    "p99": sorted(times)[int(len(times) * 0.99)],
                }

                # 断言性能要求
                assert response_times[endpoint]["avg"] < 200  # 平均响应时间小于200ms
                assert response_times[endpoint]["p95"] < 500  # 95%的请求小于500ms

        # 打印性能报告
        for endpoint, metrics in response_times.items():
            print(f"\n{endpoint} Performance:")
            print(f"  Average: {metrics['avg']:.2f}ms")
            print(f"  Median: {metrics['median']:.2f}ms")
            print(f"  P95: {metrics['p95']:.2f}ms")
            print(f"  P99: {metrics['p99']:.2f}ms")

    async def test_api_under_load(self, api_client):
        """测试API在负载下的性能"""
        endpoint = "/health"
        concurrent_requests = 50
        total_requests = 200

        async def make_request():
            start_time = time.time()
            response = await api_client.get(endpoint)
            end_time = time.time()

            return {
                "status_code": response.status_code,
                "response_time": (end_time - start_time) * 1000,
                "success": response.status_code < 400,
            }

        # 并发执行请求
        start_time = time.time()
        tasks = [make_request() for _ in range(total_requests)]

        # 分批执行以控制并发数
        results = []
        for i in range(0, len(tasks), concurrent_requests):
            batch = tasks[i : i + concurrent_requests]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)

        end_time = time.time()
        total_duration = end_time - start_time

        # 分析结果
        successful_requests = [r for r in results if r["success"]]
        response_times = [r["response_time"] for r in successful_requests]

        # 计算指标
        success_rate = len(successful_requests) / total_requests
        avg_response_time = statistics.mean(response_times) if response_times else 0
        requests_per_second = total_requests / total_duration

        # 断言性能要求
        assert success_rate > 0.95  # 成功率应该大于95%
        assert avg_response_time < 500  # 负载下平均响应时间小于500ms
        assert requests_per_second > 100  # 每秒至少处理100个请求

        print("\nLoad Test Results:")
        print(f"  Total requests: {total_requests}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  Requests per second: {requests_per_second:.2f}")

    async def test_api_payload_size_impact(self, api_client):
        """测试不同负载大小对API性能的影响"""
        endpoint = "/teams"  # 假设支持POST创建团队

        # 测试不同大小的payload
        payloads = [
            {"name": "Small Team", "size": "small"},  # ~100 bytes
            {
                "name": "Medium Team",
                "description": "A" * 1000,
                "size": "medium",
            },  # ~1KB
            {
                "name": "Large Team",
                "description": "A" * 10000,
                "metadata": {"x": "y" * 1000},
                "size": "large",
            },  # ~10KB
        ]

        for payload in payloads:
            times = []

            # 测试10次
            for _ in range(10):
                start_time = time.time()
                response = await api_client.post(endpoint, json=payload)
                end_time = time.time()

                if response.status_code < 400:
                    times.append((end_time - start_time) * 1000)

            if times:
                avg_time = statistics.mean(times)

                # 断言：即使是大payload，响应时间也应该合理
                assert avg_time < 1000  # 小于1秒

                payload_size = len(json.dumps(payload))
                print(f"\nPayload size: {payload_size} bytes")
                print(f"  Average response time: {avg_time:.2f}ms")


@pytest.mark.performance
@pytest.mark.api
class TestAPIThroughput:
    """API吞吐量测试"""

    async def test_sustained_load(self, api_client):
        """测试持续负载下的吞吐量"""
        endpoint = "/health"
        duration = 30  # 测试30秒
        target_rps = 100  # 目标每秒请求数

        async def worker():
            request_count = 0
            start_time = time.time()

            while time.time() - start_time < duration:
                # 发送请求
                response = await api_client.get(endpoint)
                if response.status_code < 400:
                    request_count += 1

                # 控制请求速率
                await asyncio.sleep(1 / target_rps)

            return request_count

        # 启动多个worker
        num_workers = 5
        tasks = [worker() for _ in range(num_workers)]
        results = await asyncio.gather(*tasks)

        total_requests = sum(results)
        actual_rps = total_requests / duration

        # 断言实际RPS接近目标
        assert actual_rps > target_rps * 0.8  # 至少达到目标的80%

        print("\nSustained Load Test:")
        print(f"  Duration: {duration}s")
        print(f"  Target RPS: {target_rps}")
        print(f"  Actual RPS: {actual_rps:.2f}")
        print(f"  Total requests: {total_requests}")

    async def test_burst_capacity(self, api_client):
        """测试突发请求处理能力"""
        endpoint = "/health"
        burst_size = 1000

        async def make_burst():
            start_time = time.time()

            # 快速发送大量请求
            tasks = []
            for _ in range(burst_size):
                tasks.append(api_client.get(endpoint))

            # 等待所有请求完成
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            duration = end_time - start_time

            # 统计结果
            successful = sum(
                1
                for r in responses
                if not isinstance(r, Exception) and r.status_code < 400
            )
            failed = burst_size - successful

            return {
                "duration": duration,
                "successful": successful,
                "failed": failed,
                "rps": burst_size / duration,
            }

        # 执行突发测试
        result = await make_burst()

        # 断言处理能力
        assert result["successful"] / burst_size > 0.9  # 至少90%成功
        assert result["rps"] > 500  # 每秒至少处理500个请求

        print("\nBurst Capacity Test:")
        print(f"  Burst size: {burst_size}")
        print(f"  Duration: {result['duration']:.2f}s")
        print(f"  Successful: {result['successful']}")
        print(f"  Failed: {result['failed']}")
        print(f"  RPS: {result['rps']:.2f}")


@pytest.mark.performance
@pytest.mark.api
class TestAPIResourceUsage:
    """API资源使用测试"""

    def test_memory_usage_under_load(self):
        """测试负载下的内存使用"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        async def simulate_api_load():
            async with httpx.AsyncClient() as client:
                for _ in range(1000):
                    response = await client.get("http://localhost:8000/health")
                    if response.status_code == 200:
                        await response.aread()

        # 运行负载测试
        asyncio.run(simulate_api_load())

        # 检查内存使用
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / 1024 / 1024

        # 断言内存增长合理
        assert memory_increase_mb < 100  # 内存增长应该小于100MB

        print("\nMemory Usage Test:")
        print(f"  Initial memory: {initial_memory / 1024 / 1024:.2f} MB")
        print(f"  Final memory: {final_memory / 1024 / 1024:.2f} MB")
        print(f"  Memory increase: {memory_increase_mb:.2f} MB")

    def test_cpu_usage_under_load(self):
        """测试负载下的CPU使用"""
        process = psutil.Process()

        async def cpu_intensive_requests():
            async with httpx.AsyncClient() as client:
                # 发送CPU密集型请求
                tasks = []
                for _ in range(100):
                    tasks.append(
                        client.get("http://localhost:8000/api/v1/compute-intensive")
                    )

                await asyncio.gather(*tasks)

        # 监控CPU使用
        cpu_samples = []

        def monitor_cpu():
            for _ in range(30):  # 监控30秒
                cpu_percent = process.cpu_percent()
                cpu_samples.append(cpu_percent)
                time.sleep(1)

        # 启动监控和负载
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()

        # 运行负载
        asyncio.run(cpu_intensive_requests())

        # 等待监控完成
        monitor_thread.join()

        # 分析CPU使用
        avg_cpu = statistics.mean(cpu_samples)
        max_cpu = max(cpu_samples)

        # 断言CPU使用合理
        assert avg_cpu < 80  # 平均CPU使用应该小于80%

        print("\nCPU Usage Test:")
        print(f"  Average CPU: {avg_cpu:.2f}%")
        print(f"  Max CPU: {max_cpu:.2f}%")


@pytest.mark.performance
@pytest.mark.api
class TestAPIScalability:
    """API可扩展性测试"""

    async def test_horizontal_scaling_simulation(self):
        """模拟水平扩展测试"""
        # 模拟多个API实例
        num_instances = 3
        requests_per_instance = 100

        async def simulate_instance(instance_id):
            async with httpx.AsyncClient() as client:
                results = []
                for i in range(requests_per_instance):
                    start_time = time.time()
                    response = await client.get("http://localhost:8000/health")
                    end_time = time.time()

                    results.append(
                        {
                            "instance_id": instance_id,
                            "request_id": i,
                            "response_time": (end_time - start_time) * 1000,
                            "success": response.status_code == 200,
                        }
                    )

                return results

        # 启动所有实例
        start_time = time.time()
        tasks = [simulate_instance(i) for i in range(num_instances)]
        all_results = await asyncio.gather(*tasks)
        end_time = time.time()

        # 分析结果
        all_requests = []
        for instance_results in all_results:
            all_requests.extend(instance_results)

        successful_requests = [r for r in all_requests if r["success"]]
        total_requests = len(all_requests)

        # 计算指标
        success_rate = len(successful_requests) / total_requests
        response_times = [r["response_time"] for r in successful_requests]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        total_rps = total_requests / (end_time - start_time)

        # 断言扩展性
        assert success_rate > 0.95
        assert avg_response_time < 300
        assert total_rps > num_instances * 50  # 每个实例至少50 RPS

        print("\nHorizontal Scaling Test:")
        print(f"  Instances: {num_instances}")
        print(f"  Total requests: {total_requests}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  Total RPS: {total_rps:.2f}")
        print(f"  RPS per instance: {total_rps / num_instances:.2f}")

    async def test_gradual_load_increase(self, api_client):
        """测试逐步增加负载"""
        endpoint = "/health"
        load_levels = [10, 50, 100, 200, 500]  # RPS级别

        results = {}

        for target_rps in load_levels:
            # 在每个负载级别测试10秒
            duration = 10
            interval = 1 / target_rps

            start_time = time.time()
            request_count = 0
            response_times = []

            while time.time() - start_time < duration:
                # 发送请求
                req_start = time.time()
                response = await api_client.get(endpoint)
                req_end = time.time()

                if response.status_code == 200:
                    request_count += 1
                    response_times.append((req_end - req_start) * 1000)

                # 控制请求速率
                await asyncio.sleep(interval)

            # 计算指标
            actual_rps = request_count / duration
            avg_response_time = statistics.mean(response_times) if response_times else 0

            results[target_rps] = {
                "actual_rps": actual_rps,
                "avg_response_time": avg_response_time,
                "request_count": request_count,
            }

            print(f"\nLoad Level: {target_rps} RPS")
            print(f"  Actual RPS: {actual_rps:.2f}")
            print(f"  Avg Response Time: {avg_response_time:.2f}ms")
            print(f"  Requests: {request_count}")

        # 验证性能随负载的变化是合理的
        # 高负载下响应时间可能增加，但不应该过度
        high_load_rps = results[500]["actual_rps"]
        low_load_response_time = results[10]["avg_response_time"]
        high_load_response_time = results[500]["avg_response_time"]

        assert high_load_rps > 400  # 高负载下仍能处理大部分请求
        assert (
            high_load_response_time < low_load_response_time * 5
        )  # 响应时间增长不超过5倍


@pytest.mark.performance
@pytest.mark.api
class TestAPIErrorHandling:
    """API错误处理性能测试"""

    async def test_error_handling_performance(self, api_client):
        """测试错误处理的性能影响"""
        # 测试不同的错误场景
        error_endpoints = [
            ("/nonexistent", 404),
            ("/api/v1/invalid", 400),
            ("/api/v1/forbidden", 403),
            ("/api/v1/server-error", 500),
        ]

        normal_endpoint = "/health"

        # 测试正常请求的性能
        normal_times = []
        for _ in range(50):
            start_time = time.time()
            response = await api_client.get(normal_endpoint)
            end_time = time.time()
            normal_times.append((end_time - start_time) * 1000)

        # 测试错误请求的性能
        error_results = {}
        for endpoint, expected_status in error_endpoints:
            error_times = []
            for _ in range(50):
                start_time = time.time()
                response = await api_client.get(endpoint)
                end_time = time.time()

                # 验证返回正确的错误状态
                assert response.status_code == expected_status
                error_times.append((end_time - start_time) * 1000)

            error_results[endpoint] = statistics.mean(error_times)

        # 计算正常请求的平均时间
        normal_avg = statistics.mean(normal_times)

        # 断言错误处理不会显著影响性能
        for endpoint, error_avg in error_results.items():
            # 错误处理时间不应该超过正常时间的3倍
            assert error_avg < normal_avg * 3, f"Error handling too slow for {endpoint}"

        print("\nError Handling Performance:")
        print(f"  Normal requests avg: {normal_avg:.2f}ms")
        for endpoint, error_avg in error_results.items():
            ratio = error_avg / normal_avg
            print(f"  {endpoint}: {error_avg:.2f}ms (ratio: {ratio:.2f}x)")

    async def test_rate_limiting_performance(self, api_client):
        """测试速率限制的性能影响"""
        # 快速发送大量请求
        rapid_requests = 100

        start_time = time.time()
        responses = []

        for _ in range(rapid_requests):
            response = await api_client.get("/health")
            responses.append(response)

        end_time = time.time()

        # 分析响应
        status_codes = {}
        for response in responses:
            status_codes[response.status_code] = (
                status_codes.get(response.status_code, 0) + 1
            )

        # 计算指标
        total_time = end_time - start_time
        requests_per_second = rapid_requests / total_time

        # 如果有速率限制，应该看到429状态码
        rate_limited = status_codes.get(429, 0)

        print("\nRate Limiting Test:")
        print(f"  Total requests: {rapid_requests}")
        print(f"  Duration: {total_time:.2f}s")
        print(f"  RPS: {requests_per_second:.2f}")
        print(f"  Rate limited (429): {rate_limited}")
        print(f"  Status codes: {status_codes}")

        # 验证系统在速率限制下仍然响应
        successful = status_codes.get(200, 0)
        assert successful > 0  # 至少有一些请求成功


@pytest.mark.performance
@pytest.mark.api
@pytest.mark.slow
class TestAPIStressTest:
    """API压力测试"""

    async def test_stress_test(self):
        """长时间压力测试"""
        duration = 300  # 5分钟压力测试
        target_rps = 100

        async def stress_worker(worker_id):
            async with httpx.AsyncClient() as client:
                request_count = 0
                error_count = 0
                response_times = []

                start_time = time.time()
                while time.time() - start_time < duration:
                    req_start = time.time()
                    try:
                        response = await client.get("http://localhost:8000/health")
                        req_end = time.time()

                        if response.status_code == 200:
                            request_count += 1
                            response_times.append((req_end - req_start) * 1000)
                        else:
                            error_count += 1
                    except Exception:
                        error_count += 1

                    # 控制请求速率
                    await asyncio.sleep(1 / (target_rps / 10))  # 10个worker

                return {
                    "worker_id": worker_id,
                    "request_count": request_count,
                    "error_count": error_count,
                    "avg_response_time": statistics.mean(response_times)
                    if response_times
                    else 0,
                    "p95_response_time": sorted(response_times)[
                        int(len(response_times) * 0.95)
                    ]
                    if response_times
                    else 0,
                }

        # 启动10个worker
        num_workers = 10
        tasks = [stress_worker(i) for i in range(num_workers)]

        print(f"\nStarting {duration}s stress test with {num_workers} workers...")

        results = await asyncio.gather(*tasks)

        # 汇总结果
        total_requests = sum(r["request_count"] for r in results)
        total_errors = sum(r["error_count"] for r in results)
        all_response_times = []
        for r in results:
            # 模拟响应时间用于计算
            if r["avg_response_time"] > 0:
                all_response_times.extend([r["avg_response_time"]] * r["request_count"])

        # 计算最终指标
        success_rate = total_requests / (total_requests + total_errors)
        actual_rps = total_requests / duration

        print("\nStress Test Results:")
        print(f"  Duration: {duration}s")
        print(f"  Workers: {num_workers}")
        print(f"  Total requests: {total_requests}")
        print(f"  Total errors: {total_errors}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Actual RPS: {actual_rps:.2f}")

        if all_response_times:
            print(f"  Avg response time: {statistics.mean(all_response_times):.2f}ms")
            print(
                f"  P95 response time: {sorted(all_response_times)[int(len(all_response_times) * 0.95)]:.2f}ms"
            )

        # 断言系统在压力下仍然稳定
        assert success_rate > 0.95  # 成功率应该大于95%
        assert actual_rps > target_rps * 0.8  # 实际RPS应该达到目标的80%
