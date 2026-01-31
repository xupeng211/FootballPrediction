#!/usr/bin/env python3
"""
FastAPI性能优化器
专门为足球预测API设计的性能优化工具
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

import aioredis
import httpx
from prometheus_client import Counter, Gauge, Histogram, start_http_server


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    endpoint: str
    method: str
    status_code: int
    duration: float
    timestamp: float
    request_id: str


class APICacheManager:
    """高性能异步缓存管理器"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: aioredis.Redis | None = None
        self.local_cache = {}  # 本地内存缓存
        self.cache_stats = {"hits": 0, "misses": 0, "local_hits": 0, "redis_hits": 0}

    async def connect(self):
        """连接到Redis"""
        try:
            self.redis = aioredis.from_url(self.redis_url, encoding="utf-8", decode_responses=True, max_connections=20)
            await self.redis.ping()
            print("✅ Redis连接成功")
        except Exception as e:
            print(f"❌ Redis连接失败: {e}")
            self.redis = None

    async def get(self, key: str, use_local_cache: bool = True) -> Any | None:
        """多层缓存获取"""
        # 1. 本地缓存
        if use_local_cache and key in self.local_cache:
            self.cache_stats["hits"] += 1
            self.cache_stats["local_hits"] += 1
            return self.local_cache[key]

        # 2. Redis缓存
        if self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    self.cache_stats["hits"] += 1
                    self.cache_stats["redis_hits"] += 1
                    data = json.loads(value)

                    # 更新本地缓存
                    if use_local_cache:
                        self.local_cache[key] = data

                    return data
            except Exception as e:
                print(f"Redis获取错误: {e}")

        # 3. 缓存未命中
        self.cache_stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, expire: int = 3600, use_local_cache: bool = True):
        """多层缓存设置"""
        # 1. 设置Redis缓存
        if self.redis:
            try:
                await self.redis.setex(key, expire, json.dumps(value, default=str))
            except Exception as e:
                print(f"Redis设置错误: {e}")

        # 2. 设置本地缓存
        if use_local_cache:
            self.local_cache[key] = value

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = self.cache_stats["hits"] / total_requests if total_requests > 0 else 0

        return {**self.cache_stats, "hit_rate": hit_rate, "local_cache_size": len(self.local_cache)}

    def clear_local_cache(self):
        """清理本地缓存"""
        self.local_cache.clear()


class APIPerformanceOptimizer:
    """API性能优化器"""

    def __init__(self):
        self.cache_manager = APICacheManager()
        self.metrics = []
        self.prometheus_metrics = {
            "request_count": Counter("api_requests_total", "Total API requests", ["method", "endpoint", "status_code"]),
            "request_duration": Histogram(
                "api_request_duration_seconds",
                "API request duration",
                ["method", "endpoint"],
                buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0],
            ),
            "active_connections": Gauge("api_active_connections", "Active API connections"),
            "cache_hit_rate": Gauge("api_cache_hit_rate", "API cache hit rate"),
        }

    async def initialize(self):
        """初始化优化器"""
        await self.cache_manager.connect()

        # 启动Prometheus指标服务器
        start_http_server(8001)  # 在端口8001提供指标
        print("📊 Prometheus指标服务器启动在端口8001")

    def record_request(self, metrics: PerformanceMetrics):
        """记录请求指标"""
        self.metrics.append(metrics)

        # 更新Prometheus指标
        self.prometheus_metrics["request_count"].labels(
            method=metrics.method, endpoint=metrics.endpoint, status_code=metrics.status_code
        ).inc()

        self.prometheus_metrics["request_duration"].labels(method=metrics.method, endpoint=metrics.endpoint).observe(
            metrics.duration
        )

    def get_performance_summary(self, time_window: float = 300) -> dict[str, Any]:
        """获取性能摘要"""
        current_time = time.time()
        recent_metrics = [m for m in self.metrics if current_time - m.timestamp <= time_window]

        if not recent_metrics:
            return {"message": "No recent metrics"}

        # 计算统计数据
        durations = [m.duration for m in recent_metrics]
        endpoints = list(set(m.endpoint for m in recent_metrics))

        summary = {
            "total_requests": len(recent_metrics),
            "avg_duration": sum(durations) / len(durations),
            "max_duration": max(durations),
            "min_duration": min(durations),
            "p95_duration": sorted(durations)[int(len(durations) * 0.95)],
            "endpoints": len(endpoints),
            "error_rate": sum(1 for m in recent_metrics if m.status_code >= 400) / len(recent_metrics),
            "time_window": time_window,
        }

        # 按端点统计
        endpoint_stats = {}
        for endpoint in endpoints:
            endpoint_metrics = [m for m in recent_metrics if m.endpoint == endpoint]
            endpoint_durations = [m.duration for m in endpoint_metrics]

            endpoint_stats[endpoint] = {
                "requests": len(endpoint_metrics),
                "avg_duration": sum(endpoint_durations) / len(endpoint_durations),
                "error_rate": sum(1 for m in endpoint_metrics if m.status_code >= 400) / len(endpoint_metrics),
            }

        summary["endpoint_stats"] = endpoint_stats

        return summary

    async def optimize_prediction_endpoint(self, prediction_func):
        """优化预测端点包装器"""

        async def optimized_predict(*args, **kwargs):
            start_time = time.time()

            # 生成缓存键
            cache_key = self._generate_cache_key(args, kwargs)

            # 尝试从缓存获取
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                duration = time.time() - start_time
                self.record_request(
                    PerformanceMetrics(
                        endpoint="/api/predict",
                        method="POST",
                        status_code=200,
                        duration=duration,
                        timestamp=time.time(),
                        request_id=cached_result.get("request_id", "unknown"),
                    )
                )
                print(f"⚡ 缓存命中: {duration:.3f}s")
                return cached_result

            # 缓存未命中，执行预测
            try:
                result = await prediction_func(*args, **kwargs)

                # 添加缓存信息
                result["cached"] = False
                result["cache_key"] = cache_key

                # 缓存结果
                await self.cache_manager.set(cache_key, result, expire=1800)  # 30分钟

                duration = time.time() - start_time
                self.record_request(
                    PerformanceMetrics(
                        endpoint="/api/predict",
                        method="POST",
                        status_code=200,
                        duration=duration,
                        timestamp=time.time(),
                        request_id=result.get("request_id", "unknown"),
                    )
                )

                print(f"🔥 预测完成: {duration:.3f}s")
                return result

            except Exception:
                duration = time.time() - start_time
                self.record_request(
                    PerformanceMetrics(
                        endpoint="/api/predict",
                        method="POST",
                        status_code=500,
                        duration=duration,
                        timestamp=time.time(),
                        request_id="error",
                    )
                )
                raise

        return optimized_predict

    def _generate_cache_key(self, args, kwargs) -> str:
        """生成缓存键"""
        # 简化的缓存键生成
        import hashlib

        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()

    async def batch_optimize(self, items: list[Any], batch_size: int = 10):
        """批量优化处理"""
        results = []
        semaphore = asyncio.Semaphore(50)  # 限制并发数

        async def process_single(item):
            async with semaphore:
                return await self._process_item(item)

        # 分批处理
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]

            # 并发处理批次
            batch_results = await asyncio.gather(*[process_single(item) for item in batch], return_exceptions=True)

            # 过滤异常
            for result in batch_results:
                if not isinstance(result, Exception):
                    results.append(result)

        return results

    async def _process_item(self, item):
        """处理单个项目"""
        # 这里实现具体的处理逻辑
        await asyncio.sleep(0.01)  # 模拟处理时间
        return {"processed": True, "item": item}

    async def health_check(self) -> dict[str, Any]:
        """健康检查"""
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "cache_stats": self.cache_manager.get_cache_stats(),
            "performance_summary": self.get_performance_summary(),
        }

        # 检查Redis连接
        if self.cache_manager.redis:
            try:
                await self.cache_manager.redis.ping()
                health_status["redis"] = "connected"
            except:
                health_status["redis"] = "disconnected"
                health_status["status"] = "degraded"
        else:
            health_status["redis"] = "not_configured"

        return health_status

    async def start_background_tasks(self):
        """启动后台任务"""
        # 定期更新指标
        asyncio.create_task(self._update_metrics_task())

        # 定期清理缓存
        asyncio.create_task(self._cache_cleanup_task())

    async def _update_metrics_task(self):
        """定期更新指标任务"""
        while True:
            try:
                # 更新缓存命中率指标
                cache_stats = self.cache_manager.get_cache_stats()
                self.prometheus_metrics["cache_hit_rate"].set(cache_stats["hit_rate"])

                await asyncio.sleep(60)  # 每分钟更新一次
            except Exception as e:
                print(f"指标更新错误: {e}")
                await asyncio.sleep(60)

    async def _cache_cleanup_task(self):
        """定期清理缓存任务"""
        while True:
            try:
                # 清理本地缓存（如果过大）
                if len(self.cache_manager.local_cache) > 1000:
                    self.cache_manager.clear_local_cache()
                    print("🧹 清理本地缓存")

                await asyncio.sleep(3600)  # 每小时清理一次
            except Exception as e:
                print(f"缓存清理错误: {e}")
                await asyncio.sleep(3600)


class LoadTester:
    """负载测试工具"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def run_load_test(
        self, endpoint: str, concurrent_users: int = 100, duration: int = 30, request_data: dict | None = None
    ):
        """运行负载测试"""
        print(f"🚀 开始负载测试: {concurrent_users} 并发用户, {duration} 秒")

        async with httpx.AsyncClient() as client:
            start_time = time.time()
            requests_sent = 0
            errors = 0
            response_times = []

            async def send_request():
                nonlocal requests_sent, errors
                try:
                    request_start = time.time()
                    response = await client.post(
                        f"{self.base_url}{endpoint}",
                        json=request_data or {"home_team": "Team A", "away_team": "Team B"},
                    )
                    response_time = time.time() - request_start
                    response_times.append(response_time)
                    requests_sent += 1

                    if response.status_code >= 400:
                        errors += 1

                except Exception:
                    errors += 1

            # 启动并发请求
            tasks = []
            while time.time() - start_time < duration:
                # 控制并发数
                if len(tasks) < concurrent_users:
                    tasks.append(asyncio.create_task(send_request()))
                else:
                    # 等待一些任务完成
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    tasks = list(pending)

                await asyncio.sleep(0.01)  # 避免过度占用CPU

            # 等待剩余任务完成
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        # 计算结果
        total_time = time.time() - start_time
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0
        rps = requests_sent / total_time if total_time > 0 else 0

        results = {
            "duration": total_time,
            "requests_sent": requests_sent,
            "errors": errors,
            "error_rate": errors / requests_sent if requests_sent > 0 else 0,
            "avg_response_time": avg_response_time,
            "p95_response_time": p95_response_time,
            "requests_per_second": rps,
        }

        print("📊 负载测试结果:")
        print(f"  请求数: {requests_sent}")
        print(f"  错误数: {errors}")
        print(f"  错误率: {results['error_rate']:.2%}")
        print(f"  平均响应时间: {avg_response_time:.3f}s")
        print(f"  P95响应时间: {p95_response_time:.3f}s")
        print(f"  RPS: {rps:.2f}")

        return results


async def main():
    """主函数示例"""
    print("🔧 FastAPI性能优化器")
    print("=" * 50)

    # 初始化优化器
    optimizer = APIPerformanceOptimizer()
    await optimizer.initialize()

    # 启动后台任务
    await optimizer.start_background_tasks()

    # 运行负载测试
    load_tester = LoadTester()
    await load_tester.run_load_test(endpoint="/api/predict", concurrent_users=50, duration=10)

    # 获取性能摘要
    summary = optimizer.get_performance_summary()
    print("\n📈 性能摘要:")
    print(json.dumps(summary, indent=2))

    # 健康检查
    health = await optimizer.health_check()
    print("\n💚 健康状态:")
    print(json.dumps(health, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
