"""
集成测试：采集器与速率限制器协同工作
Integration Test: Collector with Rate Limiter

该模块测试BaseCollectorProtocol、DummyCollector和RateLimiter的协同工作，
验证：
1. 采集器正确使用速率限制器
2. 速率限制效果符合预期
3. 并发安全性和错误处理
4. 资源清理和状态管理

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import pytest
import time

from src.collectors.interface import BaseCollectorProtocol
from src.collectors.dummy_collector import DummyCollector, create_dummy_collector
from src.collectors.rate_limiter import RateLimiter, RateLimitConfig


class TestCollectorWithRateLimiter:
    """采集器与速率限制器集成测试"""

    @pytest.fixture
    async def rate_limiter(self):
        """创建测试用的速率限制器 - 5 QPS，突发2"""
        config = {"dummy": {"rate": 5.0, "burst": 2}}  # 5 QPS，突发容量2
        return RateLimiter(config)

    @pytest.fixture
    async def collector_with_limiter(self, rate_limiter):
        """创建带有速率限制器的采集器"""
        config = {
            "delay_range": (0.01, 0.02),  # 很短的模拟延迟
            "error_rate": 0.0,  # 无错误模式
            "failure_mode": False,
        }
        collector = DummyCollector(config, rate_limiter)
        yield collector
        await collector.close()

    @pytest.mark.asyncio
    async def test_collector_limiter_integration(self, collector_with_limiter):
        """测试采集器与速率限制器集成"""
        # 验证采集器实现了协议
        assert isinstance(collector_with_limiter, BaseCollectorProtocol)
        assert hasattr(collector_with_limiter, "rate_limiter")

        # 第一次调用应该立即成功（突发容量）
        start_time = time.monotonic()
        fixtures = await collector_with_limiter.collect_fixtures(47, "2024-2025")
        elapsed = time.monotonic() - start_time

        assert elapsed < 0.1  # 应该立即完成
        assert len(fixtures) > 0
        assert fixtures[0]["league_id"] == 47

    @pytest.mark.asyncio
    async def test_rate_limiting_effect(self, collector_with_limiter):
        """测试速率限制效果 - 20个并发调用，期望约4秒完成"""
        num_requests = 20
        expected_min_time = (num_requests - 2) / 5.0  # 突发2个后，每个请求0.2秒
        expected_max_time = expected_min_time + 0.5  # 允许0.5秒误差

        results = []
        start_time = time.monotonic()

        # 创建20个并发任务
        async def collect_with_timing(request_id: int):
            task_start = time.monotonic()
            fixtures = await collector_with_limiter.collect_fixtures(request_id)
            task_end = time.monotonic()

            results.append(
                {
                    "request_id": request_id,
                    "start_time": task_start,
                    "end_time": task_end,
                    "duration": task_end - task_start,
                    "fixtures_count": len(fixtures),
                }
            )

        tasks = [collect_with_timing(i) for i in range(num_requests)]
        await asyncio.gather(*tasks)

        total_elapsed = time.monotonic() - start_time

        # 验证结果
        assert (
            total_elapsed >= expected_min_time
        ), f"总耗时 {total_elapsed:.3f}s 小于期望最小值 {expected_min_time:.3f}s"
        assert (
            total_elapsed <= expected_max_time
        ), f"总耗时 {total_elapsed:.3f}s 超过期望最大值 {expected_max_time:.3f}s"
        assert len(results) == num_requests
        assert all(r["fixtures_count"] > 0 for r in results)

        print(f"✅ 速率限制测试通过: {num_requests}个请求耗时 {total_elapsed:.3f}s")

    @pytest.mark.asyncio
    async def test_concurrent_safety(self, collector_with_limiter):
        """测试并发安全性"""
        num_tasks = 50
        results = []

        async def worker(task_id: int):
            try:
                fixtures = await collector_with_limiter.collect_fixtures(task_id % 5)
                results.append(
                    {
                        "task_id": task_id,
                        "success": True,
                        "fixtures_count": len(fixtures),
                    }
                )
            except Exception as e:
                results.append({"task_id": task_id, "success": False, "error": str(e)})

        # 创建大量并发任务
        tasks = [worker(i) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        # 验证结果
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        assert (
            len(successful) >= num_tasks * 0.95
        ), f"成功率过低: {len(successful)}/{num_tasks}"
        assert len(failed) == 0, f"存在失败的请求: {failed}"
        assert all(r["fixtures_count"] > 0 for r in successful)

        print(f"✅ 并发安全测试通过: {len(successful)}/{num_tasks} 成功")

    @pytest.mark.asyncio
    async def test_different_rate_configs(self):
        """测试不同的速率配置"""
        # 测试1: 高速率配置
        fast_config = RateLimitConfig(rate=20.0, burst=20)
        fast_limiter = RateLimiter({"fast": fast_config})
        fast_collector = create_dummy_collector({}, fast_limiter)

        # 测试2: 低速率配置
        slow_config = RateLimitConfig(rate=1.0, burst=2)
        slow_limiter = RateLimiter({"slow": slow_config})
        slow_collector = create_dummy_collector({}, slow_limiter)

        try:
            # 并发测试不同速率
            start_time = time.monotonic()

            fast_tasks = [fast_collector.collect_fixtures(1, "2024") for _ in range(10)]

            slow_tasks = [slow_collector.collect_fixtures(2, "2024") for _ in range(5)]

            await asyncio.gather(*fast_tasks, *slow_tasks)

            total_time = time.monotonic() - start_time

            # 验证结果：快速任务应该更快完成
            assert total_time < 10.0  # 10个快速任务和5个慢速任务应该很快完成

            print(f"✅ 不同速率配置测试通过: 总耗时 {total_time:.3f}s")

        finally:
            await fast_collector.close()
            await slow_collector.close()

    @pytest.mark.asyncio
    async def test_rate_limiter_error_handling(self):
        """测试速率限制器错误处理"""
        # 配置短超时
        config = RateLimitConfig(rate=1.0, burst=0, max_wait_time=0.1)  # 无突发，短超时
        limiter = RateLimiter({"test": config})
        collector = create_dummy_collector({}, limiter)

        try:
            # 第一次调用应该成功
            await collector.collect_fixtures(1)

            # 第二次调用应该超时
            with pytest.raises(asyncio.TimeoutError):
                await collector.collect_fixtures(2)

        finally:
            await collector.close()

    @pytest.mark.asyncio
    async def test_collector_lifecycle(self, rate_limiter):
        """测试采集器生命周期"""
        collector = create_dummy_collector({}, rate_limiter)

        try:
            # 正常使用
            fixtures = await collector.collect_fixtures(47)
            assert len(fixtures) > 0

            # 健康检查
            health = await collector.check_health()
            assert "status" in health
            assert health["status"] in ["healthy", "degraded", "unhealthy"]

            # 验证采集器未关闭
            assert not collector._closed

        finally:
            # 清理资源
            await collector.close()
            assert collector._closed

    @pytest.mark.asyncio
    async def test_multiple_collectors_shared_limiter(self):
        """测试多个采集器共享一个速率限制器"""
        # 创建共享的速率限制器：5 QPS，突发5
        shared_limiter = RateLimiter({"shared": {"rate": 5.0, "burst": 5}})

        collector1 = create_dummy_collector(
            {"delay_range": (0.01, 0.01)}, shared_limiter
        )
        collector2 = create_dummy_collector(
            {"delay_range": (0.01, 0.01)}, shared_limiter
        )

        try:
            start_time = time.monotonic()

            # 两个采集器并发调用，总共应该受到5 QPS的限制
            tasks = []
            for i in range(5):
                tasks.append(collector1.collect_fixtures(i))
                tasks.append(collector2.collect_fixtures(i))

            await asyncio.gather(*tasks)

            total_time = time.monotonic() - start_time

            # 10个请求，5 QPS，期望至少2秒
            assert total_time >= 1.8, f"共享限流时间太短: {total_time:.3f}s"
            assert total_time <= 3.0, f"共享限流时间过长: {total_time:.3f}s"

            print(f"✅ 共享限流器测试通过: {total_time:.3f}s")

        finally:
            await collector1.close()
            await collector2.close()

    @pytest.mark.asyncio
    async def test_performance_metrics(self, rate_limiter):
        """测试性能指标"""
        collector = create_dummy_collector(
            {"delay_range": (0.001, 0.002)}, rate_limiter
        )

        try:
            num_requests = 100
            start_time = time.monotonic()

            # 批量请求
            tasks = [collector.collect_fixtures(i) for i in range(num_requests)]
            await asyncio.gather(*tasks)

            total_time = time.monotonic() - start_time
            avg_time_per_request = total_time / num_requests
            requests_per_second = num_requests / total_time

            print("性能指标:")
            print(f"  请求数量: {num_requests}")
            print(f"  总耗时: {total_time:.3f}s")
            print(f"  平均耗时/请求: {avg_time_per_request:.3f}s")
            print(f"  请求速率: {requests_per_second:.1f} RPS")

            # 验证性能合理性
            assert (
                requests_per_second > 4.0
            ), f"请求速率过低: {requests_per_second:.1f} RPS"
            assert (
                avg_time_per_request < 0.5
            ), f"平均延迟过高: {avg_time_per_request:.3f}s"

        finally:
            await collector.close()


@pytest.mark.asyncio
async def test_end_to_end_scenario():
    """端到端场景测试"""
    print("🧪 开始端到端集成测试...")
    print("=" * 50)

    # 创建速率限制器：5 QPS，突发3
    limiter_config = {"dummy": {"rate": 5.0, "burst": 3, "max_wait_time": 30.0}}
    limiter = RateLimiter(limiter_config)

    # 创建采集器
    collector_config = {
        "delay_range": (0.01, 0.03),
        "error_rate": 0.0,
        "failure_mode": False,
    }
    collector = DummyCollector(collector_config, limiter)

    try:
        # 阶段1: 突发测试（前3个请求应该立即完成）
        print("阶段1: 突发容量测试")
        burst_start = time.monotonic()

        burst_tasks = []
        for i in range(3):
            task = asyncio.create_task(collector.collect_fixtures(100 + i))
            burst_tasks.append(task)

        burst_results = await asyncio.gather(*burst_tasks)
        burst_time = time.monotonic() - burst_start

        assert burst_time < 0.2, f"突发测试时间过长: {burst_time:.3f}s"
        assert all(len(result) > 0 for result in burst_results)
        print(f"✅ 突发测试: 3个请求耗时 {burst_time:.3f}s")

        # 阶段2: 速率限制测试（后续请求应该受限）
        print("\\n阶段2: 速率限制测试")
        rate_limit_start = time.monotonic()

        # 再发送15个请求，应该受到5 QPS限制
        rate_limit_tasks = []
        for i in range(15):
            task = asyncio.create_task(collector.collect_fixtures(200 + i))
            rate_limit_tasks.append(task)

        await asyncio.gather(*rate_limit_tasks)
        rate_limit_time = time.monotonic() - rate_limit_start

        # 15个请求在5 QPS下应该至少3秒
        assert rate_limit_time >= 2.5, f"限流时间不足: {rate_limit_time:.3f}s"
        assert rate_limit_time <= 4.0, f"限流时间过长: {rate_limit_time:.3f}s"
        print(f"✅ 速率限制测试: 15个请求耗时 {rate_limit_time:.3f}s")

        # 阶段3: 状态验证
        print("\\n阶段3: 状态验证")
        health = await collector.check_health()
        assert health["status"] == "healthy"

        limiter_status = limiter.get_status("dummy")
        print(f"✅ 健康检查: {health['status']}")
        print(
            f"✅ 速率限制器状态: {limiter_status['available_tokens']:.1f}/{limiter_status['capacity']} 令牌"
        )

        total_requests = 18  # 3 + 15
        total_time = burst_time + rate_limit_time
        overall_rps = total_requests / total_time

        print("\\n📊 端到端测试总结:")
        print(f"  总请求数: {total_requests}")
        print(f"  总耗时: {total_time:.3f}s")
        print(f"  平均速率: {overall_rps:.1f} RPS")
        print("  理论速率: 5.0 RPS (配置值)")
        print(f"  效率比率: {overall_rps/5.0:.2f}")

        # 验证整体效率
        assert 3.0 <= overall_rps <= 6.0, f"整体速率不合理: {overall_rps:.1f} RPS"

        print("\\n🎉 端到端测试全部通过！")
        return True

    finally:
        await collector.close()


if __name__ == "__main__":
    # 运行端到端测试
    asyncio.run(test_end_to_end_scenario())
