#!/usr/bin/env python3
"""
代理池验证 CLI 工具
Proxy Pool Verification CLI Tool

该脚本提供了代理池的命令行验证功能，支持：
1. 从文件或命令行加载代理
2. 健康检查和性能测试
3. 代理池工作流程演示
4. 统计信息输出

使用示例:
    python scripts/proxy_check.py --source list.txt --check-url http://httpbin.org/ip
    python scripts/proxy_check.py --proxies "http://127.0.0.1:8080,http://127.0.0.1:8081" --test-count 10

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 1.0.0
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import List, Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.collectors.proxy_pool import (
    Proxy,
    ProxyPool,
    RotationStrategy,
    create_proxy_pool,
    create_file_proxy_pool,
)


class ProxyCheckCLI:
    """代理池检查命令行界面"""

    def __init__(self):
        self.args = self.parse_args()
        self.pool: Optional[ProxyPool] = None

    def parse_args(self) -> argparse.Namespace:
        """解析命令行参数"""
        parser = argparse.ArgumentParser(
            description="代理池验证和测试工具",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例用法:
  # 从文件加载代理并检查健康状态
  python scripts/proxy_check.py --source proxies.txt --check-url http://httpbin.org/ip

  # 从命令行指定代理并测试
  python scripts/proxy_check.py --proxies "http://127.0.0.1:8080,http://127.0.0.1:8081" --test-count 20

  # 演示完整的代理池工作流程
  python scripts/proxy_check.py --demo --verbose

  # 使用加权随机策略
  python scripts/proxy_check.py --source proxies.txt --strategy weighted_random --test-count 50
            """
        )

        # 代理源选择（互斥）
        source_group = parser.add_mutually_exclusive_group(required=True)
        source_group.add_argument(
            "--source", "-s",
            type=str,
            help="代理文件路径（每行一个代理URL）"
        )
        source_group.add_argument(
            "--proxies", "-p",
            type=str,
            help="逗号分隔的代理URL列表"
        )
        source_group.add_argument(
            "--demo", "-d",
            action="store_true",
            help="使用演示代理进行完整工作流程展示"
        )

        # 策略选择
        parser.add_argument(
            "--strategy",
            choices=["random", "round_robin", "weighted_random", "health_first"],
            default="weighted_random",
            help="代理轮询策略 (默认: weighted_random)"
        )

        # 测试配置
        parser.add_argument(
            "--test-count", "-n",
            type=int,
            default=10,
            help="测试次数 (默认: 10)"
        )
        parser.add_argument(
            "--check-url",
            type=str,
            default="http://httpbin.org/ip",
            help="健康检查URL (默认: http://httpbin.org/ip)"
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=10.0,
            help="请求超时时间（秒） (默认: 10.0)"
        )

        # 输出控制
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="详细输出"
        )
        parser.add_argument(
            "--json-output",
            action="store_true",
            help="JSON格式输出结果"
        )
        parser.add_argument(
            "--no-health-check",
            action="store_true",
            help="跳过健康检查（仅测试轮询和评分）"
        )

        # 代理池配置
        parser.add_argument(
            "--max-fail-count",
            type=int,
            default=5,
            help="最大失败次数阈值 (默认: 5)"
        )
        parser.add_argument(
            "--min-score",
            type=float,
            default=30.0,
            help="最小分数阈值 (默认: 30.0)"
        )

        return parser.parse_args()

    async def create_proxy_pool(self) -> ProxyPool:
        """根据参数创建代理池"""
        if self.args.demo:
            # 演示模式：使用一些示例代理（这些会失败，但可以演示机制）
            demo_proxies = [
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8081",
                "http://127.0.0.1:8082",
                "http://user:pass@127.0.0.1:8083",
                "socks5://127.0.0.1:1080"
            ]
            if self.args.verbose:
                print("🎭 演示模式：使用示例代理列表")
            pool = create_proxy_pool(
                demo_proxies,
                strategy=RotationStrategy(self.args.strategy),
                max_fail_count=self.args.max_fail_count,
                min_score_threshold=self.args.min_score,
                health_check_url=self.args.check_url,
                health_check_timeout=self.args.timeout,
                auto_health_check=not self.args.no_health_check,
                health_check_interval=60.0,  # 演示模式缩短检查间隔
            )

        elif self.args.source:
            # 从文件加载
            if self.args.verbose:
                print(f"📁 从文件加载代理: {self.args.source}")
            pool = create_file_proxy_pool(
                self.args.source,
                strategy=RotationStrategy(self.args.strategy),
                max_fail_count=self.args.max_fail_count,
                min_score_threshold=self.args.min_score,
                health_check_url=self.args.check_url,
                health_check_timeout=self.args.timeout,
                auto_health_check=not self.args.no_health_check,
            )

        else:  # self.args.proxies
            # 从命令行加载
            proxy_urls = [url.strip() for url in self.args.proxies.split(",")]
            if self.args.verbose:
                print(f"📝 从命令行加载 {len(proxy_urls)} 个代理")
            pool = create_proxy_pool(
                proxy_urls,
                strategy=RotationStrategy(self.args.strategy),
                max_fail_count=self.args.max_fail_count,
                min_score_threshold=self.args.min_score,
                health_check_url=self.args.check_url,
                health_check_timeout=self.args.timeout,
                auto_health_check=not self.args.no_health_check,
            )

        return pool

    async def run(self) -> None:
        """运行主程序"""
        try:
            await self.initialize_pool()
            await self.run_tests()
            await self.show_results()

        except KeyboardInterrupt:
            print("\n⚠️  用户中断操作")
        except Exception as e:
            print(f"❌ 错误: {e}")
            if self.args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
        finally:
            await self.cleanup()

    async def initialize_pool(self) -> None:
        """初始化代理池"""
        if self.args.verbose:
            print("🔄 正在初始化代理池...")

        self.pool = await self.create_proxy_pool()
        await self.pool.initialize()

        stats = self.pool.get_stats()
        print(f"✅ 代理池初始化完成")
        print(f"   总代理数: {stats['total']}")
        print(f"   活跃代理: {stats['active']}")
        print(f"   健康代理: {stats['healthy']}")
        print(f"   轮询策略: {self.args.strategy}")
        print(f"   健康检查: {'启用' if not self.args.no_health_check else '禁用'}")

    async def run_tests(self) -> None:
        """运行测试"""
        if self.args.verbose:
            print(f"\n🧪 开始执行 {self.args.test_count} 次测试...")

        test_results = []
        proxy_usage = {}

        for i in range(self.args.test_count):
            try:
                # 获取代理
                start_time = time.monotonic()
                proxy = await self.pool.get_proxy()
                get_time = time.monotonic() - start_time

                if proxy is None:
                    result = {
                        "test_id": i + 1,
                        "success": False,
                        "error": "No available proxy",
                        "get_time": get_time,
                    }
                    test_results.append(result)
                    if self.args.verbose:
                        print(f"   测试 {i+1:2d}: ❌ 无可用代理")
                    continue

                # 记录代理使用情况
                proxy_url = proxy.url
                if proxy_url not in proxy_usage:
                    proxy_usage[proxy_url] = {
                        "count": 0,
                        "successes": 0,
                        "failures": 0,
                        "response_times": []
                    }

                proxy_usage[proxy_url]["count"] += 1

                # 执行健康检查（如果启用）
                if not self.args.no_health_check:
                    check_start = time.monotonic()
                    success = await self._check_proxy_health(proxy)
                    check_time = time.monotonic() - check_start
                    response_time = check_time * 1000 if success else None
                else:
                    # 模拟成功率（80%）
                    import random
                    success = random.random() < 0.8
                    response_time = 100 + random.randint(-20, 50) if success else None
                    check_time = 0.1

                # 记录结果
                await self.pool.record_proxy_result(proxy, success, response_time)

                result = {
                    "test_id": i + 1,
                    "success": success,
                    "proxy": proxy_url,
                    "get_time": get_time,
                    "check_time": check_time,
                    "response_time": response_time,
                    "proxy_score": proxy.score,
                    "proxy_fail_count": proxy.fail_count,
                }

                test_results.append(result)

                if success:
                    proxy_usage[proxy_url]["successes"] += 1
                    if response_time:
                        proxy_usage[proxy_url]["response_times"].append(response_time)
                    if self.args.verbose:
                        print(f"   测试 {i+1:2d}: ✅ {proxy_url} ({response_time:.0f}ms)")
                else:
                    proxy_usage[proxy_url]["failures"] += 1
                    if self.args.verbose:
                        print(f"   测试 {i+1:2d}: ❌ {proxy_url}")

            except Exception as e:
                result = {
                    "test_id": i + 1,
                    "success": False,
                    "error": str(e),
                }
                test_results.append(result)
                if self.args.verbose:
                    print(f"   测试 {i+1:2d}: ❌ 异常 - {e}")

        self.test_results = test_results
        self.proxy_usage = proxy_usage

    async def _check_proxy_health(self, proxy: Proxy) -> bool:
        """检查单个代理的健康状况"""
        try:
            import aiohttp
            from urllib.parse import quote

            proxy_url = proxy.url
            if proxy.username and proxy.password:
                auth_string = f"{quote(proxy.username)}:{quote(proxy.password)}"
                proxy_url = proxy_url.replace('://', f'://{auth_string}@')

            timeout = aiohttp.ClientTimeout(total=self.args.timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    self.args.check_url,
                    proxy=proxy_url,
                    ssl=False
                ) as response:
                    return response.status == 200

        except Exception:
            return False

    async def show_results(self) -> None:
        """显示测试结果"""
        if not hasattr(self, 'test_results'):
            return

        # 统计测试结果
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.get("success", False))
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0

        # 获取最终代理池状态
        final_stats = self.pool.get_stats()
        proxy_details = self.pool.get_proxies_info()

        results = {
            "test_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": round(success_rate, 2),
            },
            "proxy_pool_stats": final_stats,
            "proxy_details": proxy_details,
            "proxy_usage": getattr(self, 'proxy_usage', {}),
            "test_results": self.test_results if self.args.verbose else None,
        }

        if self.args.json_output:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            self._print_results(results)

    def _print_results(self, results: dict) -> None:
        """以人类可读格式打印结果"""
        print(f"\n📊 测试结果摘要:")
        print(f"   总测试次数: {results['test_summary']['total_tests']}")
        print(f"   成功次数: {results['test_summary']['successful_tests']}")
        print(f"   失败次数: {results['test_summary']['failed_tests']}")
        print(f"   成功率: {results['test_summary']['success_rate']}%")

        print(f"\n🏊 代理池最终状态:")
        stats = results['proxy_pool_stats']
        print(f"   总代理数: {stats['total']}")
        print(f"   活跃代理: {stats['active']}")
        print(f"   被禁用: {stats['banned']}")
        print(f"   健康代理: {stats['healthy']}")
        print(f"   平均分数: {stats['avg_score']}")
        if stats['avg_response_time']:
            print(f"   平均响应时间: {stats['avg_response_time']}ms")

        if results['proxy_usage']:
            print(f"\n📈 代理使用统计:")
            for proxy_url, usage in results['proxy_usage'].items():
                success_rate = (usage['successes'] / usage['count']) * 100 if usage['count'] > 0 else 0
                avg_response = sum(usage['response_times']) / len(usage['response_times']) if usage['response_times'] else 0
                print(f"   {proxy_url}")
                print(f"     使用次数: {usage['count']}")
                print(f"     成功/失败: {usage['successes']}/{usage['failures']}")
                print(f"     成功率: {success_rate:.1f}%")
                if avg_response:
                    print(f"     平均响应时间: {avg_response:.0f}ms")

        if self.args.verbose and results['test_results']:
            print(f"\n📋 详细测试结果:")
            for result in results['test_results']:
                status = "✅" if result.get("success", False) else "❌"
                proxy = result.get("proxy", "N/A")
                response_time = result.get("response_time")
                time_str = f"({response_time:.0f}ms)" if response_time else ""
                print(f"   {status} 测试 {result['test_id']:2d}: {proxy} {time_str}")

    async def cleanup(self) -> None:
        """清理资源"""
        if self.pool:
            await self.pool.close()


def main():
    """主函数"""
    cli = ProxyCheckCLI()
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()