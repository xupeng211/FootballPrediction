#!/usr/bin/env python3
"""
生产环境压力测试和性能验证脚本
Production Environment Stress Testing and Performance Validation Script

Phase G Week 5 Day 2 - 压力测试和性能验证
"""

import asyncio
import aiohttp
import time
import json
import statistics
import argparse
import sys
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import random
import string

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stress_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestConfig:
    """测试配置"""
    base_url: str = "http://localhost:8000"
    concurrent_users: int = 1000
    duration: int = 300  # 5分钟
    ramp_up_time: int = 30  # 30秒渐进加载
    requests_per_second: int = 100
    timeout: int = 10
    think_time: float = 0.1  # 模拟用户思考时间

@dataclass
class TestResult:
    """测试结果"""
    url: str
    status_code: int
    response_time: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p90_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float

class StressTester:
    """压力测试器"""

    def __init__(self, config: TestConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
        self.stop_event = asyncio.Event()

        # 测试端点
        self.test_endpoints = [
            "/health",
            "/api/v1/predictions/simple",
            "/api/v1/teams",
            "/api/v1/matches",
            "/api/v1/user/profile"
        ]

        # 模拟用户数据
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ]

    async def setup_session(self) -> aiohttp.ClientSession:
        """设置HTTP会话"""
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        connector = aiohttp.TCPConnector(
            limit=1000,  # 连接池大小
            limit_per_host=500,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )

        return aiohttp.ClientSession(
            timeout=timeout,
            connector=connector
        )

    def generate_test_data(self) -> Dict[str, Any]:
        """生成测试数据"""
        return {
            "home_team": "Team " + ''.join(random.choices(string.ascii_uppercase, k=3)),
            "away_team": "Team " + ''.join(random.choices(string.ascii_uppercase, k=3)),
            "match_date": "2024-01-01",
            "competition": "Test League"
        }

    async def single_request(self, session: aiohttp.ClientSession, endpoint: str, user_id: int) -> TestResult:
        """执行单个请求"""
        url = f"{self.config.base_url}{endpoint}"
        start_time = time.time()

        headers = {
            "User-Agent": random.choice(self.user_agents),
            "X-User-ID": str(user_id),
            "Content-Type": "application/json"
        }

        try:
            if endpoint == "/api/v1/predictions/simple":
                # POST请求，发送测试数据
                data = self.generate_test_data()
                async with session.post(url, json=data, headers=headers) as response:
                    content = await response.text()
                    response_time = time.time() - start_time
                    return TestResult(
                        url=url,
                        status_code=response.status,
                        response_time=response_time,
                        timestamp=datetime.now(),
                        success=response.status < 400,
                        error_message=None if response.status < 400 else f"HTTP {response.status}"
                    )
            else:
                # GET请求
                async with session.get(url, headers=headers) as response:
                    content = await response.text()
                    response_time = time.time() - start_time
                    return TestResult(
                        url=url,
                        status_code=response.status,
                        response_time=response_time,
                        timestamp=datetime.now(),
                        success=response.status < 400,
                        error_message=None if response.status < 400 else f"HTTP {response.status}"
                    )

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return TestResult(
                url=url,
                status_code=0,
                response_time=response_time,
                timestamp=datetime.now(),
                success=False,
                error_message="Timeout"
            )

        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                url=url,
                status_code=0,
                response_time=response_time,
                timestamp=datetime.now(),
                success=False,
                error_message=str(e)
            )

    async def user_simulation(self, session: aiohttp.ClientSession, user_id: int, duration: int) -> None:
        """模拟单个用户行为"""
        start_time = time.time()

        while time.time() - start_time < duration and not self.stop_event.is_set():
            # 随机选择端点
            endpoint = random.choice(self.test_endpoints)

            # 执行请求
            result = await self.single_request(session, endpoint, user_id)
            self.results.append(result)

            # 模拟用户思考时间
            if self.config.think_time > 0:
                await asyncio.sleep(self.config.think_time)

    async def ramp_up_users(self, session: aiohttp.ClientSession, total_users: int, ramp_time: int) -> List[asyncio.Task]:
        """渐进式增加用户"""
        tasks = []
        users_per_second = total_users / ramp_time

        for i in range(total_users):
            delay = i / users_per_second
            task = asyncio.create_task(
                self.delayed_user_simulation(session, i + 1, delay)
            )
            tasks.append(task)

        return tasks

    async def delayed_user_simulation(self, session: aiohttp.ClientSession, user_id: int, delay: float) -> None:
        """延迟启动用户模拟"""
        await asyncio.sleep(delay)
        await self.user_simulation(session, user_id, self.config.duration)

    async def run_stress_test(self) -> None:
        """运行压力测试"""
        logger.info(f"🚀 开始压力测试...")
        logger.info(f"📊 配置: {self.config.concurrent_users}并发用户, {self.config.duration}秒持续时间")
        logger.info(f"🎯 目标: P95响应时间 < 200ms, 错误率 < 0.1%")

        self.start_time = datetime.now()

        # 创建HTTP会话
        async with await self.setup_session() as session:
            # 渐进式加载用户
            tasks = await self.ramp_up_users(
                session,
                self.config.concurrent_users,
                self.config.ramp_up_time
            )

            logger.info(f"✅ 已启动{len(tasks)}个并发用户任务")

            # 等待所有任务完成
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"❌ 测试执行异常: {e}")
            finally:
                self.stop_event.set()

        self.end_time = datetime.now()
        logger.info(f"✅ 压力测试完成，耗时: {(self.end_time - self.start_time).total_seconds():.2f}秒")

    def calculate_metrics(self) -> PerformanceMetrics:
        """计算性能指标"""
        if not self.results:
            raise ValueError("没有测试结果")

        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]

        response_times = [r.response_time for r in successful_results]

        if not response_times:
            raise ValueError("没有成功的请求")

        total_duration = (self.end_time - self.start_time).total_seconds()

        return PerformanceMetrics(
            total_requests=len(self.results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p50_response_time=statistics.quantiles(response_times, n=100)[49],
            p90_response_time=statistics.quantiles(response_times, n=100)[89],
            p95_response_time=statistics.quantiles(response_times, n=100)[94],
            p99_response_time=statistics.quantiles(response_times, n=100)[98],
            requests_per_second=len(self.results) / total_duration,
            error_rate=len(failed_results) / len(self.results)
        )

    def evaluate_performance(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """评估性能表现"""
        evaluation = {
            "overall_grade": "A+",
            "passed_all_tests": True,
            "issues": [],
            "recommendations": []
        }

        # P95响应时间检查 (目标: < 200ms)
        if metrics.p95_response_time < 100:
            evaluation["overall_grade"] = "A+"
            evaluation["recommendations"].append("✅ P95响应时间优秀 (< 100ms)")
        elif metrics.p95_response_time < 200:
            evaluation["overall_grade"] = "A"
            evaluation["recommendations"].append("✅ P95响应时间良好 (< 200ms)")
        elif metrics.p95_response_time < 500:
            evaluation["overall_grade"] = "B"
            evaluation["overall_grade"] = "B"
            evaluation["issues"].append("⚠️ P95响应时间一般 (> 200ms)")
            evaluation["recommendations"].append("考虑优化API响应时间")
        else:
            evaluation["overall_grade"] = "C"
            evaluation["passed_all_tests"] = False
            evaluation["issues"].append("❌ P95响应时间过慢 (> 500ms)")
            evaluation["recommendations"].append("必须优化API响应时间")

        # 错误率检查 (目标: < 0.1%)
        error_rate_percent = metrics.error_rate * 100
        if error_rate_percent < 0.01:
            evaluation["recommendations"].append("✅ 错误率优秀 (< 0.01%)")
        elif error_rate_percent < 0.1:
            evaluation["recommendations"].append("✅ 错误率良好 (< 0.1%)")
        elif error_rate_percent < 1.0:
            evaluation["overall_grade"] = "B" if evaluation["overall_grade"] == "A+" else evaluation["overall_grade"]
            evaluation["issues"].append(f"⚠️ 错误率偏高 ({error_rate_percent:.2f}%)")
            evaluation["recommendations"].append("检查系统稳定性")
        else:
            evaluation["overall_grade"] = "C"
            evaluation["passed_all_tests"] = False
            evaluation["issues"].append(f"❌ 错误率过高 ({error_rate_percent:.2f}%)")
            evaluation["recommendations"].append("必须修复系统错误")

        # RPS检查
        if metrics.requests_per_second >= 100:
            evaluation["recommendations"].append(f"✅ 吞吐量优秀 ({metrics.requests_per_second:.1f} RPS)")
        elif metrics.requests_per_second >= 50:
            evaluation["recommendations"].append(f"✅ 吞吐量良好 ({metrics.requests_per_second:.1f} RPS)")
        else:
            evaluation["overall_grade"] = "B" if evaluation["overall_grade"] == "A+" else evaluation["overall_grade"]
            evaluation["issues"].append(f"⚠️ 吞吐量较低 ({metrics.requests_per_second:.1f} RPS)")
            evaluation["recommendations"].append("考虑优化系统吞吐量")

        return evaluation

    def generate_report(self, metrics: PerformanceMetrics, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试报告"""
        return {
            "test_info": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": (self.end_time - self.start_time).total_seconds(),
                "configuration": {
                    "concurrent_users": self.config.concurrent_users,
                    "duration": self.config.duration,
                    "ramp_up_time": self.config.ramp_up_time,
                    "base_url": self.config.base_url
                }
            },
            "performance_metrics": {
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "success_rate_percent": (metrics.successful_requests / metrics.total_requests) * 100,
                "error_rate_percent": metrics.error_rate * 100,
                "requests_per_second": metrics.requests_per_second,
                "response_times": {
                    "avg_ms": metrics.avg_response_time * 1000,
                    "min_ms": metrics.min_response_time * 1000,
                    "max_ms": metrics.max_response_time * 1000,
                    "p50_ms": metrics.p50_response_time * 1000,
                    "p90_ms": metrics.p90_response_time * 1000,
                    "p95_ms": metrics.p95_response_time * 1000,
                    "p99_ms": metrics.p99_response_time * 1000
                }
            },
            "evaluation": evaluation,
            "endpoint_analysis": self.analyze_endpoints()
        }

    def analyze_endpoints(self) -> Dict[str, Any]:
        """分析各端点性能"""
        endpoint_stats = {}

        for result in self.results:
            endpoint = result.url.split('/')[-1] or 'root'
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    "requests": 0,
                    "successful": 0,
                    "failed": 0,
                    "response_times": []
                }

            endpoint_stats[endpoint]["requests"] += 1
            if result.success:
                endpoint_stats[endpoint]["successful"] += 1
                endpoint_stats[endpoint]["response_times"].append(result.response_time)
            else:
                endpoint_stats[endpoint]["failed"] += 1

        # 计算每个端点的统计信息
        for endpoint, stats in endpoint_stats.items():
            if stats["response_times"]:
                stats["avg_response_time"] = statistics.mean(stats["response_times"])
                stats["p95_response_time"] = statistics.quantiles(stats["response_times"], n=100)[94]
                stats["success_rate"] = stats["successful"] / stats["requests"]
            else:
                stats["avg_response_time"] = 0
                stats["p95_response_time"] = 0
                stats["success_rate"] = 0

        return endpoint_stats

    def save_report(self, report: Dict[str, Any], filename: str = None) -> str:
        """保存测试报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stress_test_report_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"📄 测试报告已保存: {filename}")
        return filename

    def print_summary(self, metrics: PerformanceMetrics, evaluation: Dict[str, Any]) -> None:
        """打印测试摘要"""
        print("\n" + "="*60)
        print("🎯 压力测试结果摘要")
        print("="*60)

        print(f"📊 基础指标:")
        print(f"   总请求数: {metrics.total_requests:,}")
        print(f"   成功请求: {metrics.successful_requests:,}")
        print(f"   失败请求: {metrics.failed_requests:,}")
        print(f"   成功率: {(metrics.successful_requests/metrics.total_requests)*100:.2f}%")
        print(f"   吞吐量: {metrics.requests_per_second:.1f} RPS")

        print(f"\n⚡ 响应时间:")
        print(f"   平均: {metrics.avg_response_time*1000:.1f}ms")
        print(f"   P50: {metrics.p50_response_time*1000:.1f}ms")
        print(f"   P90: {metrics.p90_response_time*1000:.1f}ms")
        print(f"   P95: {metrics.p95_response_time*1000:.1f}ms")
        print(f"   P99: {metrics.p99_response_time*1000:.1f}ms")

        print(f"\n🏆 性能评估:")
        print(f"   总体评级: {evaluation['overall_grade']}")
        print(f"   测试结果: {'✅ 通过' if evaluation['passed_all_tests'] else '❌ 失败'}")

        if evaluation['issues']:
            print(f"\n⚠️ 发现问题:")
            for issue in evaluation['issues']:
                print(f"   - {issue}")

        if evaluation['recommendations']:
            print(f"\n💡 建议:")
            for rec in evaluation['recommendations']:
                print(f"   - {rec}")

        print("="*60)

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="生产环境压力测试工具")
    parser.add_argument("--url", default="http://localhost:8000", help="测试URL")
    parser.add_argument("--users", type=int, default=1000, help="并发用户数")
    parser.add_argument("--duration", type=int, default=300, help="测试持续时间(秒)")
    parser.add_argument("--ramp-up", type=int, default=30, help="渐进加载时间(秒)")
    parser.add_argument("--rps", type=int, default=100, help="每秒请求数")
    parser.add_argument("--timeout", type=int, default=10, help="请求超时时间(秒)")

    args = parser.parse_args()

    # 创建测试配置
    config = TestConfig(
        base_url=args.url,
        concurrent_users=args.users,
        duration=args.duration,
        ramp_up_time=args.ramp_up,
        requests_per_second=args.rps,
        timeout=args.timeout
    )

    # 创建测试器
    tester = StressTester(config)

    # 设置信号处理
    def signal_handler(signum, frame):
        logger.info("🛑 收到停止信号，正在优雅关闭...")
        tester.stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 运行压力测试
        await tester.run_stress_test()

        # 计算指标
        metrics = tester.calculate_metrics()

        # 评估性能
        evaluation = tester.evaluate_performance(metrics)

        # 生成报告
        report = tester.generate_report(metrics, evaluation)

        # 保存报告
        report_file = tester.save_report(report)

        # 打印摘要
        tester.print_summary(metrics, evaluation)

        # 返回结果
        if evaluation['passed_all_tests']:
            logger.info("🎉 压力测试通过！系统性能满足要求。")
            return 0
        else:
            logger.error("❌ 压力测试失败！系统性能需要优化。")
            return 1

    except Exception as e:
        logger.error(f"❌ 测试执行异常: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)