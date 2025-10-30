#!/usr/bin/env python3
"""
性能基准测试脚本
Performance Benchmark Script

用于测试系统性能，包括API响应时间、并发处理能力和资源使用情况。
"""

import asyncio
import json
import logging
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import psutil
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console = Console()


@dataclass
class BenchmarkResult:
    """基准测试结果"""

    name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    cpu_usage: float
    memory_usage: float
    duration: float


class PerformanceBenchmark:
    """性能基准测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.console = Console()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def get_system_metrics(self) -> Dict[str, float]:
        """获取系统指标"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_used_gb": memory.used / (1024**3),
            "memory_total_gb": memory.total / (1024**3),
        }

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 尝试多个健康检查端点
            endpoints = ["/health", "/api/health", "/"]
            for endpoint in endpoints:
                try:
                    response = await self.client.get(f"{self.base_url}{endpoint}")
                    if response.status_code == 200:
                        logger.info(f"Health check successful via {endpoint}")
                        return True
            except Exception:
                    continue
            return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def single_request(self, endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """单个请求测试"""
        start_time = time.time()
        success = False
        error_message = None
        status_code = None

        try:
            if method.upper() == "GET":
                response = await self.client.get(f"{self.base_url}{endpoint}", **kwargs)
            elif method.upper() == "POST":
                response = await self.client.post(f"{self.base_url}{endpoint}", **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")

            end_time = time.time()
            response_time = end_time - start_time
            success = 200 <= response.status_code < 400
            status_code = response.status_code

            if not success:
                error_message = f"HTTP {status_code}"

        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            error_message = str(e)
            status_code = None

        return {
            "success": success,
            "response_time": response_time,
            "status_code": status_code,
            "error_message": error_message,
        }

    async def load_test(
        self,
        endpoint: str,
        concurrent_users: int = 10,
        requests_per_user: int = 20,
        method: str = "GET",
        **kwargs,
    ) -> BenchmarkResult:
        """负载测试"""
        console.print(f"🚀 开始负载测试: {method} {endpoint}")
        console.print(f"👥 并发用户数: {concurrent_users}")
        console.print(f"📊 每用户请求数: {requests_per_user}")

        start_time = time.time()
        self.get_system_metrics()

        # 收集所有请求结果
        all_response_times = []
        successful_requests = 0
        failed_requests = 0

        async def user_session():
            """单个用户会话"""
            nonlocal successful_requests, failed_requests

            user_response_times = []

            for _ in range(requests_per_user):
                result = await self.single_request(endpoint, method, **kwargs)

                user_response_times.append(result["response_time"])

                if result["success"]:
                    successful_requests += 1
                else:
                    failed_requests += 1

                # 短暂延迟避免过于频繁的请求
                await asyncio.sleep(0.1)

            return user_response_times

        # 执行并发用户会话
        tasks = [user_session() for _ in range(concurrent_users)]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("执行负载测试...", total=None)

            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            progress.update(task, description="负载测试完成!")

        # 收集所有响应时间
        for user_times in results:
            if isinstance(user_times, list):
                all_response_times.extend(user_times)

        end_time = time.time()
        final_system_metrics = self.get_system_metrics()
        total_duration = end_time - start_time

        # 计算统计数据
        if all_response_times:
            avg_response_time = statistics.mean(all_response_times)
            min_response_time = min(all_response_times)
            max_response_time = max(all_response_times)

            # 计算百分位数
            sorted_times = sorted(all_response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)
            p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
            p99_response_time = sorted_times[min(p99_index, len(sorted_times) - 1)]
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0

        total_requests = concurrent_users * requests_per_user
        requests_per_second = total_requests / total_duration if total_duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0

        return BenchmarkResult(
            name=f"{method} {endpoint}",
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            cpu_usage=final_system_metrics["cpu_usage"],
            memory_usage=final_system_metrics["memory_usage"],
            duration=total_duration,
        )

    def display_result(self, result: BenchmarkResult):
        """显示测试结果"""
        # 创建结果表格
        table = Table(title=f"🏁 性能测试结果: {result.name}")

        table.add_column("指标", style="cyan", no_wrap=True)
        table.add_column("数值", style="green")
        table.add_column("单位", style="yellow")

        table.add_row("总请求数", f"{result.total_requests:,}", "个")
        table.add_row("成功请求", f"{result.successful_requests:,}", "个")
        table.add_row("失败请求", f"{result.failed_requests:,}", "个")
        table.add_row("成功率", f"{100 - result.error_rate:.2f}", "%")
        table.add_row("错误率", f"{result.error_rate:.2f}", "%")
        table.add_row("", "", "")
        table.add_row("平均响应时间", f"{result.avg_response_time:.3f}", "秒")
        table.add_row("最小响应时间", f"{result.min_response_time:.3f}", "秒")
        table.add_row("最大响应时间", f"{result.max_response_time:.3f}", "秒")
        table.add_row("95%响应时间", f"{result.p95_response_time:.3f}", "秒")
        table.add_row("99%响应时间", f"{result.p99_response_time:.3f}", "秒")
        table.add_row("", "", "")
        table.add_row("请求速率", f"{result.requests_per_second:.2f}", "请求/秒")
        table.add_row("测试时长", f"{result.duration:.2f}", "秒")
        table.add_row("", "", "")
        table.add_row("CPU使用率", f"{result.cpu_usage:.1f}", "%")
        table.add_row("内存使用率", f"{result.memory_usage:.1f}", "%")

        self.console.print(table)

        # 显示性能评估
        self.evaluate_performance(result)

    def evaluate_performance(self, result: BenchmarkResult):
        """评估性能表现"""
        console.print("\n📊 性能评估:", style="bold blue")

        # 响应时间评估
        if result.avg_response_time < 0.1:
            console.print("✅ 响应时间: 优秀 (< 100ms)", style="green")
        elif result.avg_response_time < 0.5:
            console.print("⚠️  响应时间: 良好 (100-500ms)", style="yellow")
        else:
            console.print("❌ 响应时间: 需要优化 (> 500ms)", style="red")

        # 错误率评估
        if result.error_rate == 0:
            console.print("✅ 错误率: 完美 (0%)", style="green")
        elif result.error_rate < 1:
            console.print("✅ 错误率: 优秀 (< 1%)", style="green")
        elif result.error_rate < 5:
            console.print("⚠️  错误率: 可接受 (1-5%)", style="yellow")
        else:
            console.print("❌ 错误率: 需要优化 (> 5%)", style="red")

        # 吞吐量评估
        if result.requests_per_second > 1000:
            console.print("✅ 吞吐量: 优秀 (> 1000 RPS)", style="green")
        elif result.requests_per_second > 500:
            console.print("✅ 吞吐量: 良好 (500-1000 RPS)", style="green")
        elif result.requests_per_second > 100:
            console.print("⚠️  吞吐量: 可接受 (100-500 RPS)", style="yellow")
        else:
            console.print("❌ 吞吐量: 需要优化 (< 100 RPS)", style="red")

        # 系统资源评估
        if result.cpu_usage < 50:
            console.print("✅ CPU使用: 正常 (< 50%)", style="green")
        elif result.cpu_usage < 80:
            console.print("⚠️  CPU使用: 较高 (50-80%)", style="yellow")
        else:
            console.print("❌ CPU使用: 过高 (> 80%)", style="red")

        if result.memory_usage < 70:
            console.print("✅ 内存使用: 正常 (< 70%)", style="green")
        elif result.memory_usage < 85:
            console.print("⚠️  内存使用: 较高 (70-85%)", style="yellow")
        else:
            console.print("❌ 内存使用: 过高 (> 85%)", style="red")

    async def run_comprehensive_benchmark(self):
        """运行综合基准测试"""
        console.print("🚀 开始综合性能基准测试", style="bold blue")

        # 首先进行健康检查
        if not await self.health_check():
            console.print("❌ 应用健康检查失败，请确保应用正在运行", style="red")
            return

        console.print("✅ 应用健康检查通过", style="green")

        # 测试场景列表
        test_scenarios = [
            {"name": "健康检查", "endpoint": "/api/health", "users": 20, "requests": 10},
            {"name": "根端点", "endpoint": "/", "users": 10, "requests": 20},
            {"name": "轻负载", "endpoint": "/api/health", "users": 50, "requests": 20},
            {"name": "重负载", "endpoint": "/", "users": 100, "requests": 10},
        ]

        results = []

        for scenario in test_scenarios:
            console.print(f"\n{'='*60}")
            console.print(f"测试场景: {scenario['name']}", style="bold")
            console.print(f"{'='*60}")

            try:
                result = await self.load_test(
                    endpoint=scenario["endpoint"],
                    concurrent_users=scenario["users"],
                    requests_per_user=scenario["requests"],
                )

                results.append(result)
                self.display_result(result)

            except Exception as e:
                console.print(f"❌ 测试失败: {e}", style="red")
                logger.error(f"Benchmark failed for {scenario['name']}: {e}")

        # 显示总结
        if results:
            self.display_summary(results)

    def display_summary(self, results: List[BenchmarkResult]):
        """显示测试总结"""
        console.print(f"\n{'='*60}")
        console.print("📊 综合性能测试总结", style="bold blue")
        console.print(f"{'='*60}")

        # 创建总结表格
        summary_table = Table(title="性能对比")
        summary_table.add_column("测试场景", style="cyan")
        summary_table.add_column("平均响应时间", style="green")
        summary_table.add_column("请求/秒", style="yellow")
        summary_table.add_column("错误率", style="red")
        summary_table.add_column("CPU%", style="blue")
        summary_table.add_column("内存%", style="magenta")

        for result in results:
            summary_table.add_row(
                result.name,
                f"{result.avg_response_time:.3f}s",
                f"{result.requests_per_second:.1f}",
                f"{result.error_rate:.2f}%",
                f"{result.cpu_usage:.1f}%",
                f"{result.memory_usage:.1f}%",
            )

        console.print(summary_table)

        # 总体评估
        avg_error_rate = statistics.mean([r.error_rate for r in results])
        avg_response_time = statistics.mean([r.avg_response_time for r in results])
        total_rps = sum([r.requests_per_second for r in results])

        console.print("\n📈 总体指标:")
        console.print(f"  平均错误率: {avg_error_rate:.2f}%")
        console.print(f"  平均响应时间: {avg_response_time:.3f}s")
        console.print(f"  总吞吐量: {total_rps:.1f} RPS")

        # 建议
        console.print("\n💡 优化建议:")
        if avg_error_rate > 1:
            console.print("  - 考虑增加错误处理和重试机制")
        if avg_response_time > 0.5:
            console.print("  - 考虑优化数据库查询和缓存策略")
        if any(r.cpu_usage > 80 for r in results):
            console.print("  - 考虑水平扩展或代码优化")
        if any(r.memory_usage > 85 for r in results):
            console.print("  - 检查内存泄漏或增加内存")


async def main():
    """主函数"""
    console.print("🏃‍♂️ 足球预测系统性能基准测试", style="bold blue")
    console.print("=" * 60)

    # 从环境变量或命令行参数获取基础URL
    import os

    base_url = os.getenv("BASE_URL", "http://localhost:8000")

    async with PerformanceBenchmark(base_url) as benchmark:
        await benchmark.run_comprehensive_benchmark()


if __name__ == "__main__":
    asyncio.run(main())
