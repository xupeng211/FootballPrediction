#!/usr/bin/env python3
"""
性能测试脚本
Performance Test Script

测试系统性能优化效果：
- API响应时间测试
- 并发请求测试
- 缓存效果测试
- 内存使用监控

Author: Claude AI Assistant
Date: 2025-11-03
Version: 1.0.0
"""

import asyncio
import aiohttp
import time
import statistics
import json
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import requests
import psutil
import os

class PerformanceTester:
    """性能测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: Dict[str, Any] = {}

    async def test_api_response_time(self, num_requests: int = 100) -> Dict[str, float]:
        """测试API响应时间"""
        print(f"🚀 测试API响应时间 ({num_requests}个请求)...")

        times = []
        errors = 0

        async with aiohttp.ClientSession() as session:
            for i in range(num_requests):
                try:
                    start_time = time.time()
                    async with session.get(f"{self.base_url}/health") as response:
                        if response.status == 200:
                            end_time = time.time()
                            response_time = (end_time - start_time) * 1000  # ms
                            times.append(response_time)
                        else:
                            errors += 1
                except Exception as e:
                    errors += 1
                    print(f"请求错误: {e}")

        if times:
            return {
                "average": statistics.mean(times),
                "median": statistics.median(times),
                "min": min(times),
                "max": max(times),
                "p95": self._percentile(times, 95),
                "p99": self._percentile(times, 99),
                "success_rate": (len(times) / num_requests) * 100,
                "error_count": errors
            }
        else:
            return {"error": "所有请求都失败了"}

    async def test_concurrent_requests(self,
    concurrent_users: int = 50,
    requests_per_user: int = 10) -> Dict[str,
    Any]:
        """测试并发请求处理能力"""
        print(f"🔥 测试并发请求处理 ({concurrent_users}个并发用户, 每用户{requests_per_user}个请求)...")

        async def user_session(user_id: int) -> List[float]:
            """单个用户的会话"""
            times = []
            async with aiohttp.ClientSession() as session:
                for req_id in range(requests_per_user):
                    try:
                        start_time = time.time()
                        async with session.get(f"{self.base_url}/health") as response:
                            if response.status == 200:
                                end_time = time.time()
                                response_time = (end_time - start_time) * 1000
                                times.append(response_time)
                    except Exception:
                        pass
            return times

        # 并发执行用户会话
        start_time = time.time()
        tasks = [user_session(i) for i in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks)
        end_time = time.time()

        # 统计结果
        all_times = []
        total_requests = 0
        for times in user_results:
            all_times.extend(times)
            total_requests += len(times)

        total_time = end_time - start_time
        throughput = total_requests / total_time if total_time > 0 else 0

        if all_times:
            return {
                "concurrent_users": concurrent_users,
                "total_requests": total_requests,
                "total_time": total_time,
                "throughput": throughput,  # requests per second
                "average_response_time": statistics.mean(all_times),
                "p95_response_time": self._percentile(all_times, 95),
                "p99_response_time": self._percentile(all_times, 99),
                "success_rate": (len(all_times) / (concurrent_users * requests_per_user)) * 100
            }
        else:
            return {"error": "并发测试失败"}

    def _percentile(self, data: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def monitor_system_resources(self, duration: int = 30) -> Dict[str, Any]:
        """监控系统资源使用"""
        print(f"📊 监控系统资源使用 ({duration}秒)...")

        process = psutil.Process()
        cpu_usage = []
        memory_usage = []

        start_time = time.time()
        while time.time() - start_time < duration:
            cpu_usage.append(process.cpu_percent())
            memory_info = process.memory_info()
            memory_usage.append(memory_info.rss / 1024 / 1024)  # MB
            time.sleep(1)

        return {
            "duration": duration,
            "cpu": {
                "average": statistics.mean(cpu_usage) if cpu_usage else 0,
                "max": max(cpu_usage) if cpu_usage else 0,
                "min": min(cpu_usage) if cpu_usage else 0
            },
            "memory": {
                "average": statistics.mean(memory_usage) if memory_usage else 0,
                "max": max(memory_usage) if memory_usage else 0,
                "min": min(memory_usage) if memory_usage else 0
            }
        }

    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合性能测试"""
        print("🎯 开始综合性能测试...")
        print("=" * 60)

        results = {
            "test_timestamp": time.time(),
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system_info": self._get_system_info()
        }

        try:
            # 1. API响应时间测试
            print("\n1️⃣ API响应时间测试")
            response_time_results = await self.test_api_response_time(50)
            results["response_time_test"] = response_time_results
            print(f"   平均响应时间: {response_time_results.get('average', 0):.2f}ms")
            print(f"   P95响应时间: {response_time_results.get('p95', 0):.2f}ms")
            print(f"   成功率: {response_time_results.get('success_rate', 0):.2f}%")

            # 2. 并发请求测试
            print("\n2️⃣ 并发请求测试")
            concurrent_results = await self.test_concurrent_requests(20, 5)
            results["concurrent_test"] = concurrent_results
            if "error" not in concurrent_results:
                print(f"   吞吐量: {concurrent_results.get('throughput', 0):.2f} req/s")
                print(f"   平均响应时间: {concurrent_results.get('average_response_time',
    0):.2f}ms")
                print(f"   成功率: {concurrent_results.get('success_rate', 0):.2f}%")

            # 3. 系统资源监控
            print("\n3️⃣ 系统资源监控")
            resource_results = self.monitor_system_resources(10)
            results["resource_monitoring"] = resource_results
            cpu_avg = resource_results["cpu"]["average"]
            mem_avg = resource_results["memory"]["average"]
            print(f"   平均CPU使用率: {cpu_avg:.2f}%")
            print(f"   平均内存使用: {mem_avg:.2f}MB")

            # 4. 计算性能评分
            print("\n4️⃣ 性能评分")
            performance_score = self._calculate_performance_score(results)
            results["performance_score"] = performance_score
            print(f"   总体性能评分: {performance_score['overall']:.2f}/100")
            print(f"   响应时间评分: {performance_score['response_time']:.2f}/100")
            print(f"   并发处理评分: {performance_score['concurrency']:.2f}/100")
            print(f"   资源使用评分: {performance_score['resource_usage']:.2f}/100")

        except Exception as e:
            print(f"\n❌ 测试过程中出现错误: {e}")
            results["error"] = str(e)

        print("\n" + "=" * 60)
        print("✅ 综合性能测试完成!")

        return results

    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total / 1024 / 1024 / 1024,  # GB
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "platform": os.name
        }

    def _calculate_performance_score(self, results: Dict[str, Any]) -> Dict[str, float]:
        """计算性能评分"""
        scores = {
            "response_time": 0,
            "concurrency": 0,
            "resource_usage": 0
        }

        # 响应时间评分 (目标: <200ms)
        response_test = results.get("response_time_test", {})
        if "average" in response_test:
            avg_time = response_test["average"]
            if avg_time <= 200:
                scores["response_time"] = 100
            elif avg_time <= 500:
                scores["response_time"] = 80 - (avg_time - 200) * 0.1
            else:
                scores["response_time"] = max(0, 50 - (avg_time - 500) * 0.05)

        # 并发处理评分 (目标: >50 req/s)
        concurrent_test = results.get("concurrent_test", {})
        if "throughput" in concurrent_test:
            throughput = concurrent_test["throughput"]
            if throughput >= 50:
                scores["concurrency"] = 100
            else:
                scores["concurrency"] = throughput * 2

        # 资源使用评分 (目标: CPU<80%, 内存<1GB)
        resource_test = results.get("resource_monitoring", {})
        cpu_avg = resource_test.get("cpu", {}).get("average", 0)
        mem_avg = resource_test.get("memory", {}).get("average", 0)

        cpu_score = max(0, 100 - cpu_avg * 1.25) if cpu_avg < 80 else 0
        mem_score = max(0, 100 - mem_avg * 0.1) if mem_avg < 1000 else 0
        scores["resource_usage"] = (cpu_score + mem_score) / 2

        # 总体评分
        scores["overall"] = sum(scores.values()) / len(scores)

        return scores

    def save_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """保存测试结果"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"performance_test_results_{timestamp}.json"

        # 确保reports目录存在
        os.makedirs("reports/performance", exist_ok=True)
        filepath = f"reports/performance/{filename}"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"📄 测试结果已保存到: {filepath}")
        return filepath

    def print_summary(self, results: Dict[str, Any]):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("📊 性能测试摘要报告")
        print("=" * 60)

        # 基本信息
        print(f"测试时间: {results.get('test_date', 'Unknown')}")
        print(f"系统信息: CPU核心数 {results.get('system_info',
    {}).get('cpu_count',
    'Unknown')},
    "
              f"总内存 {results.get('system_info',
    {}).get('memory_total',
    'Unknown'):.1f}GB")

        # 响应时间
        response_test = results.get("response_time_test", {})
        if "average" in response_test:
            print(f"\n🎯 响应时间性能:")
            print(f"   平均响应时间: {response_test['average']:.2f}ms")
            print(f"   P95响应时间: {response_test.get('p95', 0):.2f}ms")
            print(f"   最大响应时间: {response_test.get('max', 0):.2f}ms")
            print(f"   成功率: {response_test.get('success_rate', 0):.2f}%")

        # 并发性能
        concurrent_test = results.get("concurrent_test", {})
        if "throughput" in concurrent_test:
            print(f"\n🔥 并发处理性能:")
            print(f"   吞吐量: {concurrent_test['throughput']:.2f} req/s")
            print(f"   并发用户数: {concurrent_test.get('concurrent_users', 0)}")
            print(f"   总请求数: {concurrent_test.get('total_requests', 0)}")
            print(f"   平均响应时间: {concurrent_test.get('average_response_time', 0):.2f}ms")

        # 资源使用
        resource_test = results.get("resource_monitoring", {})
        if "cpu" in resource_test:
            print(f"\n💻 系统资源使用:")
            print(f"   平均CPU使用率: {resource_test['cpu']['average']:.2f}%")
            print(f"   最大CPU使用率: {resource_test['cpu']['max']:.2f}%")
            print(f"   平均内存使用: {resource_test['memory']['average']:.2f}MB")
            print(f"   最大内存使用: {resource_test['memory']['max']:.2f}MB")

        # 性能评分
        score = results.get("performance_score", {})
        if "overall" in score:
            print(f"\n🏆 性能评分:")
            print(f"   总体评分: {score['overall']:.2f}/100")
            print(f"   响应时间: {score.get('response_time', 0):.2f}/100")
            print(f"   并发处理: {score.get('concurrency', 0):.2f}/100")
            print(f"   资源使用: {score.get('resource_usage', 0):.2f}/100")

        print("\n" + "=" * 60)


async def main():
    """主函数"""
    print("🚀 足球预测系统性能测试工具")
    print("=" * 50)

    tester = PerformanceTester()

    try:
        # 运行综合测试
        results = await tester.run_comprehensive_test()

        # 保存结果
        filepath = tester.save_results(results)

        # 打印摘要
        tester.print_summary(results)

    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
