#!/usr/bin/env python3
"""
认证集成测试脚本
Authentication Integration Test Script

该脚本模拟完整的认证链路：
1. TokenManager 获取认证令牌
2. RateLimiter 控制请求频率
3. ProxyPool 获取代理
4. 发起HTTP请求（Mock）
5. 错误处理和重试机制

使用示例:
    python scripts/auth_integration_test.py --fotmob --requests 20
    python scripts/auth_integration_test.py --demo --verbose

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
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.collectors.auth import (
    TokenManager,
    FotMobAuthProvider,
    MockAuthProvider,
    create_token_manager,
    create_fotmob_provider,
    create_mock_provider,
)
from src.collectors.rate_limiter import RateLimiter, create_rate_limiter
from src.collectors.proxy_pool import ProxyPool, create_proxy_pool, RotationStrategy


class AuthIntegrationTester:
    """认证集成测试器"""

    def __init__(self, args):
        # 保存args引用
        self.args = args

        # 设置默认值
        self.num_requests = getattr(args, 'num_requests', 10)
        self.rate_limit = getattr(args, 'rate_limit', 5.0)
        self.burst = getattr(args, 'burst', 10)
        self.use_proxies = getattr(args, 'use_proxies', False)
        self.proxy_strategy = getattr(args, 'proxy_strategy', 'weighted_random')
        self.fotmob = getattr(args, 'fotmob', False)
        self.verbose = getattr(args, 'verbose', False)
        self.token_info = getattr(args, 'token_info', False)
        self.timeout = getattr(args, 'timeout', 10.0)
        self.token_ttl = getattr(args, 'token_ttl', 300.0)
        self.refresh_threshold = getattr(args, 'refresh_threshold', 60.0)
        self.force_refresh = getattr(args, 'force_refresh', False)
        self.request_timeout = getattr(args, 'request_timeout', 10.0)
        self.concurrent = getattr(args, 'concurrent', False)

        self.token_manager: Optional[TokenManager] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.proxy_pool: Optional[ProxyPool] = None

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'token_refreshes': 0,
            'proxy_rotations': 0,
            'rate_limited_requests': 0,
            'errors': []
        }

    async def setup(self) -> None:
        """设置测试环境"""
        print("🔧 设置认证集成测试环境...")

        # 1. 设置TokenManager
        self.token_manager = create_token_manager(
            default_ttl=self.token_ttl,
            cache_refresh_threshold=self.refresh_threshold
        )

        if self.fotmob:
            # 使用FotMob认证
            fotmob_provider = create_fotmob_provider(timeout=self.timeout)
            await self.token_manager.register_provider(fotmob_provider)
            print("✅ 注册FotMob认证提供者")
        else:
            # 使用模拟认证
            mock_provider = MockAuthProvider(
                "demo_provider",
                f"demo_token_{int(time.time())}",
                self.token_ttl
            )
            await self.token_manager.register_provider(mock_provider)
            print("✅ 注册模拟认证提供者")

        # 2. 设置RateLimiter
        self.rate_limiter = create_rate_limiter({
            "api_requests": {
                "rate": self.rate_limit,
                "burst": self.burst,
                "max_wait_time": self.request_timeout
            }
        })
        print(f"✅ 设置速率限制器: {self.rate_limit} QPS, 突发容量 {self.burst}")

        # 3. 设置ProxyPool
        if self.use_proxies:
            proxy_urls = [
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8081",
                "http://127.0.0.1:8082",
                "socks5://127.0.0.1:1080"
            ]
            self.proxy_pool = create_proxy_pool(
                proxy_urls,
                strategy=RotationStrategy(self.proxy_strategy),
                auto_health_check=False
            )
            await self.proxy_pool.initialize()
            print(f"✅ 设置代理池: {len(proxy_urls)} 个代理，策略: {self.proxy_strategy}")
        else:
            print("⚠️  跳过代理池设置（不使用代理）")

        print("✅ 环境设置完成")

    async def teardown(self) -> None:
        """清理测试环境"""
        print("🧹 清理测试环境...")

        if self.proxy_pool:
            await self.proxy_pool.close()
        print("✅ 代理池已关闭")

    async def simulate_request(self, request_id: int) -> dict[str, Any]:
        """
        模拟单个HTTP请求

        Args:
            request_id: 请求ID

        Returns:
            Dict[str, Any]: 请求结果
        """
        start_time = time.monotonic()
        result = {
            'request_id': request_id,
            'start_time': start_time,
            'success': False,
            'error': None,
            'token_used': None,
            'proxy_used': None,
            'rate_limited': False,
            'response_time': 0.0
        }

        try:
            # 1. 获取认证令牌
            if self.verbose:
                print(f"   📋 请求 {request_id}: 获取认证令牌...")

            token = await self.token_manager.get_token(
                "fotmob" if self.fotmob else "demo_provider",
                force_refresh=self.force_refresh
            )

            if not token.is_valid:
                raise Exception("Invalid authentication token")

            result['token_used'] = token.value[:20] + "..."

            # 2. 应用速率限制
            if self.verbose:
                print(f"   🚦 请求 {request_id}: 应用速率限制...")

            async with self.rate_limiter.acquire("api_requests"):
                rate_limit_time = time.monotonic()
                wait_time = rate_limit_time - start_time
                if wait_time > 0.1:  # 等待超过0.1秒
                    result['rate_limited'] = True
                    self.stats['rate_limited_requests'] += 1

                # 3. 获取代理（如果启用）
                proxy = None
                if self.proxy_pool:
                    if self.verbose:
                        print(f"   🌐 请求 {request_id}: 获取代理...")

                    proxy = await self.proxy_pool.get_proxy()
                    if proxy:
                        result['proxy_used'] = proxy.url
                        self.stats['proxy_rotations'] += 1
                    else:
                        raise Exception("No available proxy")

                # 4. 模拟HTTP请求
                if self.verbose:
                    print(f"   📡 请求 {request_id}: 发起HTTP请求...")

                request_result = await self._mock_http_request(token, proxy if self.use_proxies else None)

                if request_result['success']:
                    result['success'] = True
                    self.stats['successful_requests'] += 1
                else:
                    result['error'] = request_result['error']
                    self.stats['failed_requests'] += 1

            result['response_time'] = time.monotonic() - start_time

            # 5. 记录使用统计
            if self.use_proxies and proxy:
                await self.proxy_pool.record_proxy_result(
                    proxy, result['success'], result['response_time'] * 1000
                )

        except Exception as e:
            result['error'] = str(e)
            result['response_time'] = time.monotonic() - start_time
            self.stats['failed_requests'] += 1
            self.stats['errors'].append({
                'request_id': request_id,
                'error': str(e),
                'timestamp': time.monotonic()
            })

        self.stats['total_requests'] += 1
        return result

    async def _mock_http_request(self, token, proxy=None) -> dict[str, Any]:
        """
        模拟HTTP请求

        Args:
            token: 认证令牌
            proxy: 代理对象（可选）

        Returns:
            Dict[str, Any]: 请求结果
        """
        try:
            # 模拟网络延迟
            await asyncio.sleep(0.05 + (hash(token.value) % 10) * 0.01)  # 50-150ms

            # 模拟成功率（80%）
            import random
            if random.random() < 0.8:
                return {
                    'success': True,
                    'status_code': 200,
                    'response': {"data": "mock_response_data"}
                }
            else:
                return {
                    'success': False,
                    'status_code': 500,
                    'error': "Simulated server error"
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def run_requests(self) -> None:
        """运行请求测试"""
        print(f"\n🚀 开始执行 {self.num_requests} 个请求测试...")
        print(f"   配置: 认证={'FotMob' if self.fotmob else 'Demo'}")
        print(f"   配置: 速率限制={self.rate_limit} QPS, 突发={self.burst}")
        print(f"   配置: 代理={'启用' if self.use_proxies else '禁用'}")

        # 请求结果收集
        results = []

        if self.concurrent:
            # 并发请求
            print("🔄 使用并发请求模式...")
            tasks = [
                self.simulate_request(i)
                for i in range(self.num_requests)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # 串行请求
            print("🔄 使用串行请求模式...")
            for i in range(self.num_requests):
                result = await self.simulate_request(i)
                results.append(result)

        # 处理结果
        successful_results = [r for r in results if not isinstance(r, Exception) and r['success']]
        failed_results = [r for r in results if not isinstance(r, Exception) and not r['success']]

        # 输出结果摘要
        await self._print_results_summary(successful_results, failed_results, results)

    async def _print_results_summary(self, successful: list[dict], failed: list[dict], all_results: list[Any]) -> None:
        """打印结果摘要"""
        print("\n📊 请求结果摘要:")
        print(f"   总请求数: {len(all_results)}")
        print(f"   成功请求: {len(successful)} ({len(successful)/len(all_results)*100:.1f}%)")
        print(f"   失败请求: {len(failed)} ({len(failed)/len(all_results)*100:.1f}%)")

        if self.verbose and successful:
            # 显示成功的请求
            print("\n✅ 成功请求详情:")
            for result in successful[:5]:  # 只显示前5个
                print(f"   请求 {result['request_id']}: "
                      f"{result['response_time']:.3f}s, "
                      f"Token: {result['token_used']}, "
                      f"代理: {result['proxy_used'] or '无'}")

        if self.verbose and failed:
            # 显示失败的请求
            print("\n❌ 失败请求详情:")
            for result in failed[:5]:  # 只显示前5个
                print(f"   请求 {result['request_id']}: "
                      f"{result['response_time']:.3f}s, "
                      f"错误: {result['error']}")

        # 代理使用统计
        if self.use_proxies and self.proxy_pool:
            proxy_stats = self.proxy_pool.get_stats()
            print("\n🌐 代理池统计:")
            print(f"   总代理: {proxy_stats['total']}")
            print(f"   活跃: {proxy_stats['active']}")
            print(f"   禁用: {proxy_stats['banned']}")
            print(f"   健康: {proxy_stats['healthy']}")

        # Token Manager统计
        if self.token_manager:
            token_stats = await self.token_manager.get_stats()
            print("\n🔑 认证管理器统计:")
            print(f"   提供者: {token_stats['total_providers']}")
            print(f"   有效令牌: {token_stats['valid_tokens']}")
            print(f"   过期令牌: {token_stats['expired_tokens']}")
            print(f"   总使用次数: {token_stats['total_usage']}")

        # 速率限制统计
        print("\n🚦 速率限制统计:")
        print(f"   被限流请求: {self.stats['rate_limited_requests']}")
        print(f"   限流率: {self.stats['rate_limited_requests']/self.stats['total_requests']*100:.1f}%")

    async def print_detailed_stats(self) -> None:
        """打印详细统计信息"""
        print("\n📋 详细统计信息:")
        print(json.dumps(self.stats, indent=2, ensure_ascii=False))

        if self.token_info and self.token_manager:
            token_info = await self.token_manager.get_token_info()
            print("\n🔑 令牌详细信息:")
            print(json.dumps(token_info, indent=2, ensure_ascii=False))


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="认证集成测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基础测试
  python scripts/auth_integration_test.py --demo --requests 10

  # FotMob认证测试
  python scripts/auth_integration_test.py --fotmob --requests 20

  # 高并发测试
  python scripts/auth_integration_test.py --demo --requests 100 --concurrent

  # 使用代理池
  python scripts/auth_integration_test.py --demo --requests 50 --use-proxies
        """
    )

    # 认证配置
    parser.add_argument(
        "--fotmob",
        action="store_true",
        help="使用FotMob认证（默认使用Demo认证）"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="使用Demo认证（默认）"
    )
    parser.add_argument(
        "--token-ttl",
        type=float,
        default=300.0,
        help="令牌生存时间（秒） (默认: 300)"
    )
    parser.add_argument(
        "--refresh-threshold",
        type=float,
        default=60.0,
        help="令牌刷新阈值（秒） (默认: 60)"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="强制刷新令牌"
    )

    # 请求配置
    parser.add_argument(
        "--requests", "-n",
        type=int,
        default=10,
        help="请求数量 (默认: 10)"
    )
    parser.add_argument(
        "--concurrent",
        action="store_true",
        help="并发执行请求"
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=5.0,
        help="速率限制 QPS (默认: 5.0)"
    )
    parser.add_argument(
        "--burst",
        type=int,
        default=10,
        help="突发容量 (默认: 10)"
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=10.0,
        help="请求超时时间（秒） (默认: 10)"
    )

    # 代理配置
    parser.add_argument(
        "--use-proxies",
        action="store_true",
        help="启用代理池"
    )
    parser.add_argument(
        "--proxy-strategy",
        choices=["random", "round_robin", "weighted_random", "health_first"],
        default="weighted_random",
        help="代理轮询策略 (默认: weighted_random)"
    )

    # 输出配置
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    parser.add_argument(
        "--token-info",
        action="store_true",
        help="显示令牌详细信息"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="网络请求超时时间（秒） (默认: 10)"
    )

    args = parser.parse_args()

    # 默认使用demo认证
    if not args.fotmob and not args.demo:
        args.demo = True

    return args


async def main():
    """主函数"""
    args = parse_args()

    try:
        tester = AuthIntegrationTester(args)
        await tester.setup()
        await tester.run_requests()
        await tester.print_detailed_stats()

    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
    except Exception as e:
        print(f"❌ 错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        if 'tester' in locals():
            await tester.teardown()


if __name__ == "__main__":
    asyncio.run(main())
