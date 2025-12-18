#!/usr/bin/env python3
"""P1-7 采集器压测脚本
P1-7 Collector Load Testing Script.

对FotMobCollectorV2进行并发压力测试，验证RateLimiter性能。
Stress test FotMobCollectorV2 with concurrent requests to verify RateLimiter performance.

Author: Claude Code
Version: 1.0.0
"""

import asyncio
import time
import sys
import statistics
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

# 添加项目路径
sys.path.insert(0, "/app")

from src.collectors.fotmob.collector_v2 import FotMobCollectorV2
from src.collectors.rate_limiter import RateLimiter


@dataclass
class BenchmarkResult:
    """基准测试结果."""

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
    error_messages: list[str]


@dataclass
class RequestMetric:
    """单个请求指标."""

    request_id: int
    start_time: float
    end_time: float
    response_time: float
    success: bool
    error_message: Optional[str] = None
    data_size: int = 0


class CollectorBenchmarker:
    """采集器基准测试器."""

    def __init__(self):
        """初始化基准测试器."""
        self.collector = None
        self.rate_limiter = None
        self.results: list[RequestMetric] = []

    async def setup(self):
        """设置测试环境."""
        print("🔧 初始化采集器压测环境...")

        try:
            # 初始化RateLimiter - 设置较低的QPS用于测试
            rate_limit_config = {
                "fotmob.com": {
                    "rate": 5.0,  # 5 QPS限制
                    "burst": 10,  # 突发限制
                    "max_wait_time": 30.0,  # 最大等待30秒
                },
                "default": {
                    "rate": 1.0,  # 默认1 QPS
                    "burst": 2,  # 突发限制
                    "max_wait_time": 30.0,
                },
            }
            self.rate_limiter = RateLimiter(rate_limit_config)

            # 初始化FotMobCollectorV2
            self.collector = FotMobCollectorV2(rate_limiter=self.rate_limiter)

            print("✅ 采集器和限流器初始化完成")
            print("   📊 RateLimiter配置: 5 QPS (fotmob.com)")

        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            raise

    async def collect_single_match(self, match_id: int) -> RequestMetric:
        """收集单个比赛数据."""
        request_id = match_id
        start_time = time.time()
        success = False
        error_message = None
        data_size = 0

        try:
            # 模拟数据收集
            result = await self.collector.collect_match_details(match_id)
            end_time = time.time()

            if result:
                success = True
                data_size = len(str(result)) if result else 0
                # print(f"   ✅ Match {match_id}: 成功收集 (大小: {data_size} bytes)")
            else:
                error_message = "No data returned"
                # print(f"   ⚠️  Match {match_id}: 无数据返回")

        except Exception as e:
            end_time = time.time()
            success = False
            error_message = str(e)
            # print(f"   ❌ Match {match_id}: 收集失败 - {error_message}")

        response_time = end_time - start_time

        return RequestMetric(
            request_id=request_id,
            start_time=start_time,
            end_time=end_time,
            response_time=response_time,
            success=success,
            error_message=error_message,
            data_size=data_size,
        )

    async def run_concurrent_test(self, concurrent_count: int = 50) -> BenchmarkResult:
        """运行并发测试."""
        print(f"\n🚀 开始并发测试: {concurrent_count} 个并发请求")
        print("-" * 50)

        # 生成测试用的match_id列表
        test_match_ids = list(range(1, min(concurrent_count + 1, 1000)))

        # 如果请求数超过可用match_id，重复使用
        while len(test_match_ids) < concurrent_count:
            test_match_ids.extend(
                range(1, min(concurrent_count - len(test_match_ids) + 1, 1000))
            )

        print(f"   📊 测试match_id范围: {min(test_match_ids)}-{max(test_match_ids)}")
        print(f"   📊 请求分布: {len(test_match_ids)} 个唯一ID")

        # 清空之前的结果
        self.results.clear()

        # 记录开始时间
        overall_start = time.time()

        # 创建并发任务
        tasks = []
        for i, match_id in enumerate(test_match_ids):
            task = asyncio.create_task(
                self.collect_single_match(match_id), name=f"request_{i + 1}"
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
                self.results.append(
                    RequestMetric(
                        request_id=i + 1,
                        start_time=overall_start,
                        end_time=time.time(),
                        response_time=time.time() - overall_start,
                        success=False,
                        error_message=f"Task exception: {str(task_result)}",
                    )
                )

        # 计算基准结果
        total_time = overall_end - overall_start
        successful_requests = len([r for r in self.results if r.success])
        failed_requests = len(self.results) - successful_requests

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
        error_messages = [
            r.error_message for r in self.results if not r.success and r.error_message
        ]

        return BenchmarkResult(
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
            error_messages=error_messages,
        )

    async def run_rate_limiter_test(self):
        """专门测试RateLimiter效果."""
        print("\n🎯 RateLimiter专项测试")
        print("-" * 30)

        # 测试无RateLimiter的响应时间
        print("   📊 测试无限流时的响应时间...")
        start_time = time.time()
        time.time() - start_time

        # 测试有RateLimiter的限制效果
        print("   📊 测试有限流时的请求间隔...")
        rate_limited_times = []

        for i in range(5):  # 测试5个连续请求
            start = time.time()
            await self.rate_limiter.acquire()
            end = time.time()
            rate_limited_times.append(end - start)
            print(f"      请求 {i + 1}: 间隔 {(end - start) * 1000:.2f}ms")

        avg_interval = statistics.mean(rate_limited_times) if rate_limited_times else 0
        expected_interval = 1000 / 5.0  # 200ms for 5 QPS

        print("   ✅ RateLimiter验证:")
        print(f"      理论间隔: {expected_interval:.0f}ms")
        print(f"      实际平均间隔: {avg_interval * 1000:.1f}ms")
        print(
            f"      限流效果: {'有效' if avg_interval >= expected_interval * 0.8 else '无效'}"
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
            "| 测试场景 | 总请求数 | 成功数 | 失败数 | 成功率 | RPS | 平均响应时间 | P95响应时间 | 错误率 |",
            "|----------|----------|--------|--------|--------|-----|-------------|-------------|--------|",
        ]

        for i, result in enumerate(results):
            report_lines.append(
                f"| 场景 {i + 1} | {result.total_requests} | "
                f"{result.successful_requests} | {result.failed_requests} | "
                f"{(result.successful_requests / result.total_requests) * 100:.1f}% | "
                f"{result.requests_per_second:.2f} | "
                f"{result.avg_response_time * 1000:.1f}ms | "
                f"{result.p95_response_time * 1000:.1f}ms | "
                f"{result.error_rate:.2f}% |"
            )

        report_lines.extend(
            [
                "",
                "## 🎯 性能指标分析",
                "",
                f"- **平均RPS**: {statistics.mean([r.requests_per_second for r in results]):.2f}",
                f"- **平均响应时间**: {statistics.mean([r.avg_response_time * 1000 for r in results]):.1f}ms",
                f"- **平均P95响应时间**: {statistics.mean([r.p95_response_time * 1000 for r in results]):.1f}ms",
                f"- **平均成功率**: {statistics.mean([(r.successful_requests / r.total_requests) * 100 for r in results]):.2f}%",
                "",
                "## 🔍 瓶颈分析",
                "",
            ]
        )

        # 瓶颈分析
        avg_rps = statistics.mean([r.requests_per_second for r in results])
        if avg_rps < 10:
            report_lines.append("- **性能瓶颈**: RPS较低，可能受RateLimiter限制影响")
            report_lines.append("- **建议**: 调整RateLimiter配置或优化采集逻辑")

        avg_error_rate = statistics.mean([r.error_rate for r in results])
        if avg_error_rate > 10:
            report_lines.append("- **稳定性瓶颈**: 错误率较高")
            report_lines.append("- **建议**: 检查外部API可用性和网络连接")

        avg_p95 = statistics.mean([r.p95_response_time * 1000 for r in results])
        if avg_p95 > 5000:
            report_lines.append("- **延迟瓶颈**: P95响应时间较高")
            report_lines.append("- **建议**: 优化数据采集逻辑或增加缓存")

        report_lines.extend(
            [
                "",
                "## 📈 压测建议",
                "",
                "1. **并发数优化**: 根据系统资源调整并发请求数",
                "2. **限流策略**: 根据API限制调整RateLimiter配置",
                "3. **错误处理**: 增强重试机制和错误恢复",
                "4. **监控告警**: 设置性能阈值监控和告警",
                "",
                f"**报告生成时间**: {datetime.now().isoformat()}",
            ]
        )

        return "\n".join(report_lines)

    async def run_benchmark(self):
        """运行完整的基准测试."""
        print("🚀 开始P1-7采集器基准测试")
        print("=" * 60)

        try:
            # 设置环境
            await self.setup()

            # RateLimiter专项测试
            await self.run_rate_limiter_test()

            # 并发测试 - 不同的并发级别
            test_scenarios = [10, 25, 50]  # 不同的并发数
            all_results = []

            for concurrent_count in test_scenarios:
                print(f"\n🎯 测试场景: {concurrent_count} 并发请求")
                print("=" * 40)

                result = await self.run_concurrent_test(concurrent_count)
                all_results.append(result)

                # 打印即时结果
                print("\n📊 即时结果:")
                print(f"   ✅ 总请求数: {result.total_requests}")
                print(f"   ✅ 成功请求: {result.successful_requests}")
                print(f"   ❌ 失败请求: {result.failed_requests}")
                print(
                    f"   📈 成功率: {(result.successful_requests / result.total_requests) * 100:.2f}%"
                )
                print(f"   ⚡ RPS: {result.requests_per_second:.2f}")
                print(f"   ⏱️  平均响应时间: {result.avg_response_time * 1000:.1f}ms")
                print(f"   ⏱️  P95响应时间: {result.p95_response_time * 1000:.1f}ms")
                print(f"   ❌ 错误率: {result.error_rate:.2f}%")

                # 显示错误详情（如果有）
                if result.error_messages:
                    print(f"   🚨 错误详情: {len(result.error_messages)} 个错误")
                    for i, error in enumerate(result.error_messages[:3]):  # 只显示前3个
                        print(f"      {i + 1}. {error}")
                    if len(result.error_messages) > 3:
                        print(f"      ... 还有 {len(result.error_messages) - 3} 个错误")

                # 测试间隔
                if concurrent_count != test_scenarios[-1]:
                    print("\n⏳ 等待 3 秒后进行下一个测试...")
                    await asyncio.sleep(3)

            # 生成报告
            report = await self.generate_report(all_results)

            # 保存报告
            report_path = "/app/reports/benchmark_collector_baseline.md"
            try:
                with open(report_path, "w", encoding="utf-8") as f:
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
    benchmarker = CollectorBenchmarker()
    report, results = await benchmarker.run_benchmark()

    if report and results:
        print("\n" + "=" * 60)
        print("🎯 P1-7采集器基准测试完成")
        print("=" * 60)

        # 总结
        avg_rps = statistics.mean([r.requests_per_second for r in results])
        avg_success_rate = statistics.mean(
            [(r.successful_requests / r.total_requests) * 100 for r in results]
        )
        avg_p95 = statistics.mean([r.p95_response_time * 1000 for r in results])

        print(f"📊 平均RPS: {avg_rps:.2f}")
        print(f"📊 平均成功率: {avg_success_rate:.2f}%")
        print(f"📊 平均P95响应时间: {avg_p95:.1f}ms")

        # 性能评估
        if avg_rps >= 5 and avg_success_rate >= 90 and avg_p95 <= 5000:
            print("🏆 性能评级: 优秀")
        elif avg_rps >= 3 and avg_success_rate >= 80 and avg_p95 <= 10000:
            print("👍 性能评级: 良好")
        else:
            print("⚠️ 性能评级: 需要优化")

        return True
    else:
        print("❌ 测试失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
