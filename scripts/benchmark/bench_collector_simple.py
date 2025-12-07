#!/usr/bin/env python3
"""P1-7 采集器压测脚本 - 简化版
P1-7 Collector Load Testing Script - Simplified Version.

专注于RateLimiter性能测试，避免复杂的collector依赖。
Focus on RateLimiter performance testing, avoiding complex collector dependencies.

Author: Claude Code
Version: 1.0.0
"""

import asyncio
import time
import json
import sys
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

# 添加项目路径
sys.path.insert(0, '/app')

from src.collectors.rate_limiter import RateLimiter


@dataclass
class BenchmarkResult:
    """基准测试结果."""
    test_name: str
    concurrent_requests: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time: float
    min_response_time: float
    max_response_time: float
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    rate_limit_hits: int


@dataclass
class RequestMetric:
    """单个请求指标."""
    request_id: int
    start_time: float
    end_time: float
    response_time: float
    success: bool
    rate_limited: bool = False
    error_message: Optional[str] = None


class SimpleCollectorBenchmarker:
    """简化采集器基准测试器."""

    def __init__(self):
        """初始化基准测试器."""
        self.rate_limiter = None
        self.results: list[RequestMetric] = []

    async def setup(self):
        """设置测试环境."""
        print("🔧 初始化简化采集器压测环境...")

        try:
            # 初始化RateLimiter
            rate_limit_config = {
                "test_domain": {
                    "rate": 10.0,  # 10 QPS限制
                    "burst": 20,  # 突发限制
                    "max_wait_time": 60.0  # 最大等待60秒
                },
                "default": {
                    "rate": 5.0,  # 默认5 QPS
                    "burst": 10,  # 突发限制
                    "max_wait_time": 60.0
                }
            }
            self.rate_limiter = RateLimiter(rate_limit_config)

            print("✅ RateLimiter初始化完成")
            print("   📊 配置: test_domain 10 QPS, default 5 QPS")

        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            raise

    async def simulate_request(self, request_id: int, domain: str = "test_domain") -> RequestMetric:
        """模拟单个请求."""
        start_time = time.time()
        success = False
        rate_limited = False
        error_message = None

        try:
            # 使用RateLimiter进行限流控制
            async with self.rate_limiter.acquire(domain):
                # 模拟网络请求和数据获取
                await asyncio.sleep(0.05)  # 模拟50ms网络延迟
                await asyncio.sleep(0.02)  # 模拟20ms数据处理

                success = True
                # print(f"   ✅ Request {request_id}: 成功 (domain: {domain})")

        except Exception as e:
            if "rate limit" in str(e).lower() or "timeout" in str(e).lower():
                rate_limited = True
                error_message = f"Rate limited: {e}"
            else:
                error_message = f"Request failed: {e}"
            # print(f"   ❌ Request {request_id}: 失败 - {error_message}")

        end_time = time.time()
        response_time = end_time - start_time

        return RequestMetric(
            request_id=request_id,
            start_time=start_time,
            end_time=end_time,
            response_time=response_time,
            success=success,
            rate_limited=rate_limited,
            error_message=error_message
        )

    async def run_rate_limiter_test(self):
        """专门测试RateLimiter效果."""
        print("\n🎯 RateLimiter专项测试")
        print("-" * 30)

        domains = ["test_domain", "default"]

        for domain in domains:
            print(f"\n   📊 测试域名: {domain}")
            print(f"      理论QPS: {self.rate_limiter.config[domain].rate}")

            # 测试连续请求
            request_times = []

            for i in range(5):
                start = time.time()
                async with self.rate_limiter.acquire(domain):
                    await asyncio.sleep(0.01)  # 模拟处理时间
                end = time.time()
                request_time = end - start
                request_times.append(request_time)
                print(f"      请求 {i+1}: 间隔 {request_time*1000:.1f}ms")

            avg_interval = statistics.mean(request_times) if request_times else 0
            expected_interval = 1000 / self.rate_limiter.config[domain].rate

            print(f"      理论间隔: {expected_interval:.0f}ms")
            print(f"      实际平均间隔: {avg_interval*1000:.1f}ms")
            print(f"      限流效果: {'有效' if avg_interval >= expected_interval * 0.8 else '无效'}")

    async def run_concurrent_test(self, concurrent_count: int = 50, test_name: str = "") -> BenchmarkResult:
        """运行并发测试."""
        if test_name:
            print(f"\n🚀 {test_name}: {concurrent_count} 个并发请求")
        else:
            print(f"\n🚀 并发测试: {concurrent_count} 个并发请求")
        print("-" * 50)

        # 清空之前的结果
        self.results.clear()

        # 记录开始时间
        overall_start = time.time()

        # 创建并发任务
        tasks = []
        for i in range(concurrent_count):
            domain = "test_domain" if i % 2 == 0 else "default"  # 交替使用不同域名
            task = asyncio.create_task(
                self.simulate_request(i + 1, domain),
                name=f"request_{i+1}"
            )
            tasks.append(task)

        # 执行并发任务
        print(f"   ⏳ 执行 {len(tasks)} 个并发请求...")
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        # 记录结束时间
        overall_end = time.time()

        # 处理结果
        for i, task_result in enumerate(completed_tasks):
            if isinstance(task_result, RequestMetric):
                self.results.append(task_result)
            else:
                # 处理异常
                self.results.append(RequestMetric(
                    request_id=i + 1,
                    start_time=overall_start,
                    end_time=time.time(),
                    response_time=time.time() - overall_start,
                    success=False,
                    error_message=f"Task exception: {str(task_result)}"
                ))

        # 计算基准结果
        total_time = overall_end - overall_start
        successful_requests = len([r for r in self.results if r.success])
        failed_requests = len(self.results) - successful_requests
        rate_limit_hits = len([r for r in self.results if r.rate_limited])

        response_times = [r.response_time for r in self.results]
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p50_response_time = statistics.median(response_times) if response_times else 0

        if len(response_times) >= 20:
            sorted_times = sorted(response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)
            p95_response_time = sorted_times[p95_index]
            p99_response_time = sorted_times[p99_index]
        else:
            p95_response_time = max_response_time
            p99_response_time = max_response_time

        requests_per_second = len(self.results) / total_time if total_time > 0 else 0
        error_rate = (failed_requests / len(self.results)) * 100 if self.results else 0

        return BenchmarkResult(
            test_name=test_name or f"Concurrent_{concurrent_count}",
            concurrent_requests=concurrent_count,
            total_requests=len(self.results),
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_time=total_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            avg_response_time=avg_response_time,
            p50_response_time=p50_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            rate_limit_hits=rate_limit_hits
        )

    async def generate_report(self, results: list[BenchmarkResult]) -> str:
        """生成基准测试报告."""
        print("\n📋 生成基准测试报告")
        print("-" * 50)

        report_lines = [
            "# P1-7 采集器基准测试报告",
            "# P1-7 Collector Benchmark Report",
            "",
            f"**测试时间**: {datetime.now().isoformat()}",
            "**测试版本**: P1-7 v1.0.0",
            "",
            "## 📊 测试结果摘要",
            "",
            "| 测试场景 | 并发数 | 总请求数 | 成功数 | 失败数 | RPS | 平均响应时间 | P95响应时间 | 错误率 | 限流命中 |",
            "|----------|--------|----------|--------|--------|-----|-------------|-------------|--------|----------|",
        ]

        for result in results:
            report_lines.append(
                f"| {result.test_name} | {result.concurrent_requests} | "
                f"{result.total_requests} | {result.successful_requests} | "
                f"{result.failed_requests} | {result.requests_per_second:.2f} | "
                f"{result.avg_response_time*1000:.1f}ms | "
                f"{result.p95_response_time*1000:.1f}ms | "
                f"{result.error_rate:.2f}% | {result.rate_limit_hits} |"
            )

        report_lines.extend([
            "",
            "## 🎯 性能指标分析",
            "",
            f"- **平均RPS**: {statistics.mean([r.requests_per_second for r in results]):.2f}",
            f"- **平均响应时间**: {statistics.mean([r.avg_response_time*1000 for r in results]):.1f}ms",
            f"- **平均P95响应时间**: {statistics.mean([r.p95_response_time*1000 for r in results]):.1f}ms",
            f"- **平均成功率**: {statistics.mean([(r.successful_requests/r.total_requests)*100 for r in results]):.2f}%",
            f"- **平均限流命中**: {statistics.mean([r.rate_limit_hits for r in results]):.1f}",
            "",
            "## 🔍 性能分析",
            ""
        ])

        # 性能分析
        avg_rps = statistics.mean([r.requests_per_second for r in results])
        avg_response_time = statistics.mean([r.avg_response_time*1000 for r in results])
        avg_rate_limit_hits = statistics.mean([r.rate_limit_hits for r in results])

        if avg_rps >= 8 and avg_response_time <= 200:
            performance_level = "优秀"
        elif avg_rps >= 5 and avg_response_time <= 500:
            performance_level = "良好"
        else:
            performance_level = "需要优化"

        report_lines.extend([
            f"- **整体性能评级**: {performance_level}",
            f"- **RateLimiter效果**: {'有效' if avg_rate_limit_hits > 0 else '未触发'}",
            f"- **并发处理能力**: {max([r.concurrent_requests for r in results])} 并发",
            "",
            "## 📈 优化建议",
            ""
        ])

        if avg_rate_limit_hits > len(results) * 2:  # 如果平均限流命中数较高
            report_lines.extend([
                "1. **调整限流策略**: 当前限流较为严格，可适当提高QPS限制",
                "2. **增加并发容量**: 系统可以承受更高的并发负载",
                "3. **优化缓存策略**: 减少对限流器的依赖"
            ])
        else:
            report_lines.extend([
                "1. **并发数优化**: 当前系统可以处理更高的并发数",
                "2. **性能监控**: 持续监控系统性能指标",
                "3. **资源利用**: 评估系统资源使用情况"
            ])

        report_lines.extend([
            "",
            f"**报告生成时间**: {datetime.now().isoformat()}",
        ])

        return "\n".join(report_lines)

    async def run_benchmark(self):
        """运行完整的基准测试."""
        print("🚀 开始P1-7采集器基准测试 (简化版)")
        print("=" * 60)

        try:
            # 设置环境
            await self.setup()

            # RateLimiter专项测试
            await self.run_rate_limiter_test()

            # 并发测试 - 不同的并发级别
            test_scenarios = [
                (10, "小并发测试"),
                (25, "中等并发测试"),
                (50, "高并发测试"),
                (100, "极高并发测试")
            ]
            all_results = []

            for concurrent_count, test_name in test_scenarios:
                result = await self.run_concurrent_test(concurrent_count, test_name)
                all_results.append(result)

                # 打印即时结果
                print("\n📊 即时结果:")
                print(f"   ✅ 总请求数: {result.total_requests}")
                print(f"   ✅ 成功请求: {result.successful_requests}")
                print(f"   ❌ 失败请求: {result.failed_requests}")
                print(f"   📈 RPS: {result.requests_per_second:.2f}")
                print(f"   ⏱️  平均响应时间: {result.avg_response_time*1000:.1f}ms")
                print(f"   ⏱️  P95响应时间: {result.p95_response_time*1000:.1f}ms")
                print(f"   ❌ 错误率: {result.error_rate:.2f}%")
                print(f"   🚦 限流命中: {result.rate_limit_hits}")

                # 测试间隔
                if concurrent_count != test_scenarios[-1][0]:
                    print("\n⏳ 等待 3 秒后进行下一个测试...")
                    await asyncio.sleep(3)

            # 生成报告
            report = await self.generate_report(all_results)

            # 保存报告
            report_path = "/app/reports/benchmark_collector_baseline.md"
            try:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n✅ 报告已保存: {report_path}")
            except Exception as e:
                print(f"\n⚠️ 报告保存失败: {e}")

            return report, all_results

        except Exception as e:
            print(f"\n❌ 基准测试失败: {e}")
            import traceback
            traceback.print_exc()
            return None, []


async def main():
    """主函数."""
    benchmarker = SimpleCollectorBenchmarker()
    report, results = await benchmarker.run_benchmark()

    if report and results:
        print("\n" + "=" * 60)
        print("🎯 P1-7采集器基准测试完成")
        print("=" * 60)

        # 总结
        avg_rps = statistics.mean([r.requests_per_second for r in results])
        avg_success_rate = statistics.mean([(r.successful_requests/r.total_requests)*100 for r in results])
        avg_p95 = statistics.mean([r.p95_response_time*1000 for r in results])
        avg_rate_limit_hits = statistics.mean([r.rate_limit_hits for r in results])

        print(f"📊 平均RPS: {avg_rps:.2f}")
        print(f"📊 平均成功率: {avg_success_rate:.2f}%")
        print(f"📊 平均P95响应时间: {avg_p95:.1f}ms")
        print(f"📊 平均限流命中: {avg_rate_limit_hits:.1f}")

        # 性能评估
        if avg_rps >= 8 and avg_success_rate >= 90 and avg_p95 <= 500:
            print("🏆 性能评级: 优秀")
        elif avg_rps >= 5 and avg_success_rate >= 80 and avg_p95 <= 1000:
            print("👍 性能评级: 良好")
        else:
            print("⚠️ 性能评级: 需要优化")

        print("\n🚀 P1-7采集器压测数据已准备就绪！")

        return True
    else:
        print("❌ 测试失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
