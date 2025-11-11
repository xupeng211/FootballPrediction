#!/usr/bin/env python3
"""
Redis缓存性能测试工具
Redis Cache Performance Test Tool

测试缓存系统的性能指标，包括命中率、响应时间等。
"""

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass
from typing import Any

import aiohttp
import numpy as np

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestConfig:
    """测试配置"""

    api_base_url: str = "http://localhost:8000"
    concurrent_requests: int = 50
    total_requests: int = 1000
    test_duration: int = 60  # 秒
    endpoints: list[str] = None
    payload_variants: dict[str, list[dict]] = None

    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = [
                "/predictions-srs/predict",
                "/predictions-srs/predict/batch",
                "/predictions-srs/metrics",
                "/betting/recommendations/12345",
                "/health"
            ]

        if self.payload_variants is None:
            self.payload_variants = {
                "/predictions-srs/predict": [
                    {
                        "match_info": {
                            "match_id": random.randint(1000, 9999),
                            "home_team": f"Team_{random.randint(1, 20)}",
                            "away_team": f"Team_{random.randint(21, 40)}",
                            "league": "Premier League",
                            "match_date": "2025-11-05T20:00:00Z"
                        },
                        "include_confidence": True,
                        "include_features": False
                    }
                    for _ in range(10)
                ],
                "/predictions-srs/predict/batch": [
                    {
                        "matches": [
                            {
                                "match_id": random.randint(1000, 9999),
                                "home_team": f"Team_{random.randint(1, 20)}",
                                "away_team": f"Team_{random.randint(21, 40)}",
                                "league": "Premier League",
                                "match_date": "2025-11-05T20:00:00Z"
                            }
                            for _ in range(random.randint(1, 5))
                        ],
                        "include_confidence": True,
                        "max_concurrent": 10
                    }
                    for _ in range(5)
                ]
            }


@dataclass
class TestResult:
    """测试结果"""

    total_requests: int
    successful_requests: int
    failed_requests: int
    cache_hits: int
    cache_misses: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    cache_hit_rate: float
    error_rate: float


class CachePerformanceTester:
    """缓存性能测试器"""

    def __init__(self, config: TestConfig):
        self.config = config
        self.session = None
        self.results = []

    async def __aenter__(self):
        """异步上下文管理器入口"""
        # 创建HTTP会话
        connector = aiohttp.TCPConnector(
            limit=self.config.concurrent_requests,
            limit_per_host=self.config.concurrent_requests,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )

        timeout = aiohttp.ClientTimeout(
            total=30,
            connect=10,
            sock_read=10
        )

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def run_single_request(self, endpoint: str) -> dict[str, Any]:
        """执行单个请求"""
        start_time = time.time()

        try:
            # 选择请求方法和数据
            if endpoint.startswith("/predictions-srs/predict"):
                if "/batch" in endpoint:
                    payload = random.choice(self.config.payload_variants.get(endpoint, [{}]))
                    async with self.session.post(
                        f"{self.config.api_base_url}{endpoint}",
                        json=payload
                    ) as response:
                        content = await response.text()
                        response_time = time.time() - start_time

                        return {
                            "status_code": response.status,
                            "response_time": response_time,
                            "success": response.status == 200,
                            "cache_hit": response.headers.get("X-Cache") == "HIT",
                            "content_length": len(content),
                            "error": None
                        }
                else:
                    payload = random.choice(self.config.payload_variants.get(endpoint, [{}]))
                    async with self.session.post(
                        f"{self.config.api_base_url}{endpoint}",
                        json=payload
                    ) as response:
                        content = await response.text()
                        response_time = time.time() - start_time

                        return {
                            "status_code": response.status,
                            "response_time": response_time,
                            "success": response.status == 200,
                            "cache_hit": response.headers.get("X-Cache") == "HIT",
                            "content_length": len(content),
                            "error": None
                        }
            else:
                async with self.session.get(f"{self.config.api_base_url}{endpoint}") as response:
                    content = await response.text()
                    response_time = time.time() - start_time

                    return {
                        "status_code": response.status,
                        "response_time": response_time,
                        "success": response.status == 200,
                        "cache_hit": response.headers.get("X-Cache") == "HIT",
                        "content_length": len(content),
                        "error": None
                    }

        except Exception as e:
            response_time = time.time() - start_time
            return {
                "status_code": 0,
                "response_time": response_time,
                "success": False,
                "cache_hit": False,
                "content_length": 0,
                "error": str(e)
            }

    async def run_concurrent_requests(self, num_requests: int) -> list[dict[str, Any]]:
        """执行并发请求"""
        # 创建任务列表
        tasks = []
        for _ in range(num_requests):
            endpoint = random.choice(self.config.endpoints)
            task = self.run_single_request(endpoint)
            tasks.append(task)

        # 执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤异常结果
        valid_results = []
        for result in results:
            if isinstance(result, dict):
                valid_results.append(result)
            else:
                # 处理异常
                valid_results.append({
                    "status_code": 0,
                    "response_time": 0,
                    "success": False,
                    "cache_hit": False,
                    "content_length": 0,
                    "error": str(result)
                })

        return valid_results

    def calculate_metrics(self, results: list[dict[str, Any]]) -> TestResult:
        """计算性能指标"""
        if not results:
            raise ValueError("没有测试结果")

        # 基础统计
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r["success"])
        failed_requests = total_requests - successful_requests

        # 缓存统计
        cache_hits = sum(1 for r in results if r["cache_hit"])
        cache_misses = total_requests - cache_hits

        # 响应时间统计
        response_times = [r["response_time"] for r in results]
        avg_response_time = np.mean(response_times)
        min_response_time = np.min(response_times)
        max_response_time = np.max(response_times)
        p95_response_time = np.percentile(response_times, 95)
        p99_response_time = np.percentile(response_times, 99)

        # 计算其他指标
        cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0
        error_rate = failed_requests / total_requests if total_requests > 0 else 0

        return TestResult(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=successful_requests / sum(response_times) if sum(response_times) > 0 else 0,
            cache_hit_rate=cache_hit_rate,
            error_rate=error_rate
        )

    async def run_performance_test(self) -> TestResult:
        """运行性能测试"""
        logger.info("开始缓存性能测试...")
        logger.info(f"配置: {self.config.concurrent_requests}并发, {self.config.total_requests}总请求")

        all_results = []
        start_time = time.time()

        # 分批执行请求
        batch_size = self.config.concurrent_requests
        remaining_requests = self.config.total_requests

        while remaining_requests > 0:
            current_batch_size = min(batch_size, remaining_requests)
            logger.info(f"执行批次: {current_batch_size} 请求")

            # 执行当前批次
            batch_results = await self.run_concurrent_requests(current_batch_size)
            all_results.extend(batch_results)

            remaining_requests -= current_batch_size

            # 显示进度
            completed = self.config.total_requests - remaining_requests
            progress = (completed / self.config.total_requests) * 100
            logger.info(f"进度: {progress:.1f}% ({completed}/{self.config.total_requests})")

            # 短暂休息避免过载
            await asyncio.sleep(0.1)

        total_time = time.time() - start_time
        logger.info(f"测试完成，总耗时: {total_time:.2f}秒")

        # 计算最终指标
        final_result = self.calculate_metrics(all_results)
        final_result.requests_per_second = final_result.total_requests / total_time

        return final_result

    def print_results(self, result: TestResult):
        """打印测试结果"""





        # 性能评级
        if result.cache_hit_rate >= 0.8:
            pass
        elif result.cache_hit_rate >= 0.6:
            pass
        else:
            pass

        if result.avg_response_time <= 0.1:
            pass
        elif result.avg_response_time <= 0.5:
            pass
        else:
            pass



    async def run_warmup_test(self, warmup_requests: int = 100):
        """运行预热测试"""
        logger.info(f"开始预热测试 ({warmup_requests} 请求)...")

        warmup_results = await self.run_concurrent_requests(warmup_requests)
        warmup_success = sum(1 for r in warmup_results if r["success"])

        logger.info(f"预热完成: {warmup_success}/{warmup_requests} 成功")

    async def save_results(self, result: TestResult, filename: str = "cache_performance_test.json"):
        """保存测试结果"""
        results_data = {
            "timestamp": time.time(),
            "config": {
                "api_base_url": self.config.api_base_url,
                "concurrent_requests": self.config.concurrent_requests,
                "total_requests": self.config.total_requests,
                "endpoints": self.config.endpoints
            },
            "results": {
                "total_requests": result.total_requests,
                "successful_requests": result.successful_requests,
                "failed_requests": result.failed_requests,
                "cache_hits": result.cache_hits,
                "cache_misses": result.cache_misses,
                "avg_response_time": result.avg_response_time,
                "min_response_time": result.min_response_time,
                "max_response_time": result.max_response_time,
                "p95_response_time": result.p95_response_time,
                "p99_response_time": result.p99_response_time,
                "requests_per_second": result.requests_per_second,
                "cache_hit_rate": result.cache_hit_rate,
                "error_rate": result.error_rate
            }
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)

        logger.info(f"测试结果已保存到: {filename}")


async def main():
    """主函数"""
    # 创建测试配置
    config = TestConfig(
        api_base_url="http://localhost:8000",
        concurrent_requests=20,
        total_requests=500
    )

    # 运行性能测试
    async with CachePerformanceTester(config) as tester:
        # 预热
        await tester.run_warmup_test()

        # 正式测试
        result = await tester.run_performance_test()

        # 显示结果
        tester.print_results(result)

        # 保存结果
        await tester.save_results(result)

        # 验证缓存性能
        if result.cache_hit_rate < 0.6:
            logger.warning("缓存命中率较低，建议检查缓存配置")
        elif result.cache_hit_rate > 0.9:
            logger.info("缓存性能优秀！")

        if result.avg_response_time > 0.5:
            logger.warning("平均响应时间较长，建议优化性能")
        else:
            logger.info("响应速度良好！")


if __name__ == "__main__":
    asyncio.run(main())
