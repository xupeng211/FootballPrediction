#!/usr/bin/env python3
"""
压力测试脚本
Stress Testing Script

对API端点进行压力测试，验证系统在高负载下的性能表现。
"""

import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import sys

class StressTestResults:
    """压力测试结果"""
    def __init__(self):
        self.requests: List[float] = []
        self.errors: List[str] = []
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

    def add_request(self, duration: float, success: bool, error: str = None):
        """添加请求结果"""
        self.requests.append(duration)
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error:
                self.errors.append(error)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.requests:
            return {
                "total_requests": 0,
                "success_rate": 0.0,
                "error_rate": 0.0,
                "avg_response_time": 0.0,
                "min_response_time": 0.0,
                "max_response_time": 0.0,
                "p95_response_time": 0.0,
                "p99_response_time": 0.0,
                "requests_per_second": 0.0,
                "errors": []
            }

        # 计算百分位数
        sorted_times = sorted(self.requests)
        n = len(sorted_times)
        p95 = sorted_times[int(n * 0.95)] if n > 0 else 0
        p99 = sorted_times[int(n * 0.99)] if n > 0 else 0

        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.successful_requests / self.total_requests) * 100,
            "error_rate": (self.failed_requests / self.total_requests) * 100,
            "avg_response_time": statistics.mean(self.requests),
            "min_response_time": min(self.requests),
            "max_response_time": max(self.requests),
            "p95_response_time": p95,
            "p99_response_time": p99,
            "requests_per_second": self.total_requests / (sum(self.requests) or 1),
            "errors": self.errors[:10]  # 只显示前10个错误
        }

async def single_request(session: aiohttp.ClientSession, url: str, method: str = "GET",
                        data: Dict = None) -> tuple[float, bool, str]:
    """执行单个请求"""
    start_time = time.time()
    try:
        if method == "GET":
            async with session.get(url) as response:
                if response.status == 200:
                    duration = time.time() - start_time
                    return duration, True, None
                else:
                    duration = time.time() - start_time
                    return duration, False, f"HTTP {response.status}"
        elif method == "POST" and data:
            async with session.post(url, json=data) as response:
                if response.status in [200, 201]:
                    duration = time.time() - start_time
                    return duration, True, None
                else:
                    duration = time.time() - start_time
                    return duration, False, f"HTTP {response.status}"
    except Exception as e:
        duration = time.time() - start_time
        return duration, False, str(e)

async def stress_test(url: str, concurrent_users: int, total_requests: int,
                     method: str = "GET", data: Dict = None) -> StressTestResults:
    """执行压力测试"""
    print("🚀 开始压力测试...")
    print(f"📊 URL: {url}")
    print(f"👥 并发用户: {concurrent_users}")
    print(f"🔢 总请求数: {total_requests}")
    print(f"🔧 HTTP方法: {method}")

    results = StressTestResults()

    # 创建HTTP会话
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    connector = aiohttp.TCPConnector(limit=concurrent_users * 2)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # 分批执行请求
        batch_size = concurrent_users
        batches = (total_requests + batch_size - 1) // batch_size

        print(f"📦 执行 {batches} 批次，每批 {batch_size} 个请求...")

        for batch_num in range(batches):
            start_batch = batch_num * batch_size
            end_batch = min(start_batch + batch_size, total_requests)
            batch_requests = end_batch - start_batch

            print(f"⏳ 执行第 {batch_num + 1}/{batches} 批次 ({batch_requests} 个请求)...")

            # 并发执行当前批次
            tasks = []
            for _ in range(batch_requests):
                task = single_request(session, url, method, data)
                tasks.append(task)

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 收集结果
            for result in batch_results:
                if isinstance(result, Exception):
                    results.add_request(0, False, str(result))
                else:
                    duration, success, error = result
                    results.add_request(duration, success, error)

            # 显示进度
            progress = ((batch_num + 1) / batches) * 100
            print(f"✅ 完成 {progress:.1f}% ({results.total_requests}/{total_requests} 请求)")

    return results

def print_results(results: StressTestResults, test_name: str):
    """打印测试结果"""
    stats = results.get_stats()

    print(f"\n{'='*60}")
    print(f"🎯 {test_name} - 压力测试结果")
    print(f"{'='*60}")
    print(f"📊 总请求数: {stats['total_requests']}")
    print(f"✅ 成功请求: {stats['successful_requests']} ({stats['success_rate']:.1f}%)")
    print(f"❌ 失败请求: {stats['failed_requests']} ({stats['error_rate']:.1f}%)")
    print("")
    print("⚡ 响应时间统计:")
    print(f"   平均: {stats['avg_response_time']:.3f}s")
    print(f"   最小: {stats['min_response_time']:.3f}s")
    print(f"   最大: {stats['max_response_time']:.3f}s")
    print(f"   P95:  {stats['p95_response_time']:.3f}s")
    print(f"   P99:  {stats['p99_response_time']:.3f}s")
    print("")
    print(f"🚀 吞吐量: {stats['requests_per_second']:.1f} RPS")

    if stats['errors']:
        print("")
        print("🚨 错误详情 (前10个):")
        for i, error in enumerate(stats['errors'], 1):
            print(f"   {i}. {error}")

    print(f"{'='*60}")

async def main():
    """主函数"""
    base_url = "http://localhost:8000"

    # 测试配置
    test_configs = [
        {
            "name": "健康检查端点",
            "url": f"{base_url}/health/",
            "concurrent_users": 10,
            "total_requests": 100,
            "method": "GET"
        },
        {
            "name": "存活检查端点",
            "url": f"{base_url}/health/liveness",
            "concurrent_users": 20,
            "total_requests": 200,
            "method": "GET"
        },
        {
            "name": "预测端点",
            "url": f"{base_url}/api/v1/predictions/1",
            "concurrent_users": 5,
            "total_requests": 50,
            "method": "GET"
        }
    ]

    all_results = []

    for config in test_configs:
        try:
            results = await stress_test(**config)
            print_results(results, config["name"])
            all_results.append((config["name"], results))

            # 测试间隔
            if config != test_configs[-1]:
                print("⏳ 等待 5 秒后开始下一个测试...")
                await asyncio.sleep(5)

        except KeyboardInterrupt:
            print("\n⚠️ 用户中断测试")
            break
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            continue

    # 生成总结报告
    if all_results:
        print(f"\n{'='*80}")
        print("📋 压力测试总结报告")
        print(f"{'='*80}")

        for test_name, results in all_results:
            stats = results.get_stats()
            print(f"🎯 {test_name}:")
            print(f"   请求: {stats['total_requests']} | 成功率: {stats['success_rate']:.1f}% | "
                  f"平均响应: {stats['avg_response_time']:.3f}s | RPS: {stats['requests_per_second']:.1f}")

        # 整体评估
        total_requests = sum(r.total_requests for _, r in all_results)
        total_successful = sum(r.successful_requests for _, r in all_results)
        overall_success_rate = (total_successful / total_requests) * 100 if total_requests > 0 else 0

        print("\n🏆 整体表现:")
        print(f"   总请求数: {total_requests}")
        print(f"   整体成功率: {overall_success_rate:.1f}%")

        if overall_success_rate >= 95:
            print("   ✅ 系统性能优秀")
        elif overall_success_rate >= 90:
            print("   ⚠️ 系统性能良好")
        else:
            print("   ❌ 系统性能需要改进")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 用户取消测试")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        sys.exit(1)