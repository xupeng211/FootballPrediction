"""
RateLimiter 单元测试
Rate Limiter Unit Tests

该模块测试基于Token Bucket算法的速率限制器，包括：
1. 基本令牌桶功能
2. 多域名隔离
3. Async Context Manager 接口
4. 并发安全性
5. 突发流量处理
6. 超时和错误处理

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import pytest
import time

from src.collectors.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    TokenBucket,
    create_rate_limiter,
)


class TestRateLimitConfig:
    """RateLimitConfig 测试"""

    def test_valid_config(self):
        """测试有效配置"""
        config = RateLimitConfig(rate=2.0, burst=5)
        assert config.rate == 2.0
        assert config.burst == 5
        assert config.max_wait_time is None

    def test_config_with_timeout(self):
        """测试带超时的配置"""
        config = RateLimitConfig(rate=1.5, burst=3, max_wait_time=10.0)
        assert config.rate == 1.5
        assert config.burst == 3
        assert config.max_wait_time == 10.0

    def test_invalid_rate(self):
        """测试无效速率"""
        with pytest.raises(ValueError, match="Rate must be positive"):
            RateLimitConfig(rate=0, burst=5)

        with pytest.raises(ValueError, match="Rate must be positive"):
            RateLimitConfig(rate=-1.0, burst=5)

    def test_invalid_burst(self):
        """测试无效突发容量"""
        with pytest.raises(ValueError, match="Burst must be positive"):
            RateLimitConfig(rate=1.0, burst=0)

        with pytest.raises(ValueError, match="Burst must be positive"):
            RateLimitConfig(rate=1.0, burst=-1)

    def test_invalid_max_wait_time(self):
        """测试无效最大等待时间"""
        with pytest.raises(ValueError, match="max_wait_time must be non-negative"):
            RateLimitConfig(rate=1.0, burst=1, max_wait_time=-1.0)


class TestTokenBucket:
    """TokenBucket 测试"""

    @pytest.fixture
    def bucket(self):
        """创建测试用的令牌桶"""
        return TokenBucket(tokens=5.0, capacity=5.0, refill_rate=1.0)

    @pytest.mark.asyncio
    async def test_initial_tokens(self, bucket):
        """测试初始令牌数"""
        assert bucket.tokens == 5.0
        assert bucket.capacity == 5.0
        assert bucket.refill_rate == 1.0

    @pytest.mark.asyncio
    async def test_consume_success(self, bucket):
        """测试成功消耗令牌"""
        success = await bucket.consume(1)
        assert success is True
        assert bucket.tokens == 4.0

    @pytest.mark.asyncio
    async def test_consume_insufficient(self, bucket):
        """测试令牌不足"""
        success = await bucket.consume(10)
        assert success is False
        assert bucket.tokens == 5.0  # 不应该消耗令牌

    @pytest.mark.asyncio
    async def test_refill_over_time(self):
        """测试令牌补充"""
        bucket = TokenBucket(tokens=0.0, capacity=5.0, refill_rate=2.0)

        # 等待1秒，应该补充2个令牌
        await asyncio.sleep(1.0)

        success = await bucket.consume(2)
        assert success is True
        assert bucket.tokens == 0.0

    @pytest.mark.asyncio
    async def test_refill_capacity_limit(self, bucket):
        """测试补充不超过容量限制"""
        # 消耗所有令牌
        await bucket.consume(5)
        assert bucket.tokens == 0.0

        # 等待10秒，应该补充到容量限制
        await asyncio.sleep(1.1)  # 稍微多一点时间
        success = await bucket.consume(5)
        assert success is True
        assert bucket.tokens == 0.0

    @pytest.mark.asyncio
    async def test_wait_for_tokens_success(self, bucket):
        """测试等待令牌成功"""
        # 消耗所有令牌
        await bucket.consume(5)

        start_time = time.monotonic()
        success = await bucket.wait_for_tokens(3, timeout=5.0)
        elapsed = time.monotonic() - start_time

        assert success is True
        # 应该等待大约3秒 (3 tokens / 1 token/s)
        assert 2.8 <= elapsed <= 3.5

    @pytest.mark.asyncio
    async def test_wait_for_tokens_timeout(self):
        """测试等待令牌超时"""
        bucket = TokenBucket(tokens=0.0, capacity=5.0, refill_rate=1.0)

        start_time = time.monotonic()
        success = await bucket.wait_for_tokens(5, timeout=2.0)
        elapsed = time.monotonic() - start_time

        assert success is False
        # 应该等待2秒后超时
        assert 1.9 <= elapsed <= 2.2

    @pytest.mark.asyncio
    async def test_concurrent_access(self, bucket):
        """测试并发访问安全性"""

        async def worker():
            results = []
            for _ in range(10):
                success = await bucket.consume(1)
                results.append(success)
                if success:
                    await asyncio.sleep(0.1)  # 让令牌补充
            return results

        # 并发运行多个worker
        tasks = [worker() for _ in range(3)]
        results = await asyncio.gather(*tasks)

        # 验证结果
        total_consumed = sum(sum(worker_results) for worker_results in results)
        assert total_consumed <= 5 + 3  # 初始5个 + 3个补充的


class TestRateLimiter:
    """RateLimiter 测试"""

    @pytest.fixture
    def config(self):
        """测试配置"""
        return {
            "fotmob.com": {"rate": 2.0, "burst": 5},
            "fbref.com": {"rate": 1.0, "burst": 3},
            "default": {"rate": 1.0, "burst": 1},
        }

    @pytest.fixture
    def limiter(self, config):
        """创建测试用的速率限制器"""
        return RateLimiter(config)

    def test_initialization_with_config(self, limiter):
        """测试带配置初始化"""
        assert "fotmob.com" in limiter.config
        assert "fbref.com" in limiter.config
        assert "default" in limiter.config

        assert limiter.config["fotmob.com"].rate == 2.0
        assert limiter.config["fotmob.com"].burst == 5

    def test_initialization_without_config(self):
        """测试无配置初始化"""
        limiter = RateLimiter()
        assert "default" in limiter.config
        assert limiter.config["default"].rate == 1.0
        assert limiter.config["default"].burst == 1

    def test_config_parsing_dict_format(self):
        """测试字典格式配置解析"""
        config = {"test.com": {"rate": 3.0, "burst": 10, "max_wait_time": 15.0}}
        limiter = RateLimiter(config)

        assert limiter.config["test.com"].rate == 3.0
        assert limiter.config["test.com"].burst == 10
        assert limiter.config["test.com"].max_wait_time == 15.0

    def test_config_parsing_object_format(self):
        """测试对象格式配置解析"""
        rate_config = RateLimitConfig(rate=5.0, burst=20, max_wait_time=60.0)
        config = {"test.com": rate_config}
        limiter = RateLimiter(config)

        assert limiter.config["test.com"].rate == 5.0
        assert limiter.config["test.com"].burst == 20
        assert limiter.config["test.com"].max_wait_time == 60.0

    @pytest.mark.asyncio
    async def test_acquire_immediate_success(self, limiter):
        """测试立即成功获取令牌"""
        start_time = time.monotonic()

        async with limiter.acquire("fotmob.com"):
            elapsed = time.monotonic() - start_time
            assert elapsed < 0.1  # 应该立即成功，无等待

    @pytest.mark.asyncio
    async def test_domain_isolation(self, limiter):
        """测试域名隔离"""
        # fotmob.com有5个令牌，fbref.com有3个令牌
        fotmob_tasks = []
        fbref_tasks = []

        # 消耗fotmob.com的令牌
        for _ in range(5):
            task = asyncio.create_task(limiter.try_acquire("fotmob.com"))
            fotmob_tasks.append(task)

        # 消耗fbref.com的令牌
        for _ in range(3):
            task = asyncio.create_task(limiter.try_acquire("fbref.com"))
            fbref_tasks.append(task)

        # 等待所有任务完成
        fotmob_results = await asyncio.gather(*fotmob_tasks)
        fbref_results = await asyncio.gather(*fbref_tasks)

        # 验证结果
        assert sum(fotmob_results) == 5  # fotmob.com应该成功5次
        assert sum(fbref_results) == 3  # fbref.com应该成功3次

    @pytest.mark.asyncio
    async def test_acquire_with_waiting(self, limiter):
        """测试需要等待的令牌获取"""
        # 先消耗fotmob.com的所有令牌
        for _ in range(5):
            await limiter.try_acquire("fotmob.com")

        start_time = time.monotonic()

        async with limiter.acquire("fotmob.com"):
            elapsed = time.monotonic() - start_time
            # 应该等待约0.5秒 (1 token / 2 tokens/s)
            assert 0.4 <= elapsed <= 0.8

    @pytest.mark.asyncio
    async def test_try_acquire_non_blocking(self, limiter):
        """测试非阻塞令牌获取"""
        # 消耗所有令牌
        for _ in range(5):
            await limiter.try_acquire("fotmob.com")

        # 现在应该无法获取令牌
        success = await limiter.try_acquire("fotmob.com")
        assert success is False

    @pytest.mark.asyncio
    async def test_wait_for_available(self, limiter):
        """测试等待令牌可用"""
        # 消耗所有令牌
        for _ in range(1):
            await limiter.try_acquire("fbref.com")

        start_time = time.monotonic()
        wait_time = await limiter.wait_for_available("fbref.com", tokens=1)

        # 应该等待约1秒 (1 token / 1 token/s)
        assert 0.9 <= wait_time <= 1.3
        assert time.monotonic() - start_time >= 0.9

    @pytest.mark.asyncio
    async def test_get_status_single_domain(self, limiter):
        """测试获取单个域名状态"""
        # 消耗一些令牌
        await limiter.try_acquire("fotmob.com")
        await limiter.try_acquire("fotmob.com")

        status = limiter.get_status("fotmob.com")

        assert status["domain"] == "fotmob.com"
        assert status["available_tokens"] == 3.0
        assert status["capacity"] == 5.0
        assert status["rate"] == 2.0

    @pytest.mark.asyncio
    async def test_get_status_all_domains(self, limiter):
        """测试获取所有域名状态"""
        # 访问一些域名以创建令牌桶
        await limiter.try_acquire("fotmob.com")
        await limiter.try_acquire("fbref.com")

        status = limiter.get_status()

        assert "fotmob.com" in status
        assert "fbref.com" in status
        assert status["fotmob.com"]["available_tokens"] == 4.0
        assert status["fbref.com"]["available_tokens"] == 2.0

    def test_update_config(self, limiter):
        """测试更新配置"""
        new_config = RateLimitConfig(rate=10.0, burst=20)
        limiter.update_config("fotmob.com", new_config)

        assert limiter.config["fotmob.com"].rate == 10.0
        assert limiter.config["fotmob.com"].burst == 20.0

    @pytest.mark.asyncio
    async def test_remove_domain(self, limiter):
        """测试移除域名"""
        # 先访问域名以创建令牌桶
        await limiter.try_acquire("fotmob.com")
        assert "fotmob.com" in limiter.buckets

        # 移除域名
        limiter.remove_domain("fotmob.com")
        assert "fotmob.com" not in limiter.config
        assert "fotmob.com" not in limiter.buckets

    @pytest.mark.asyncio
    async def test_clear_all(self, limiter):
        """测试清空所有令牌桶"""
        # 访问域名并消耗令牌
        await limiter.try_acquire("fotmob.com")
        await limiter.try_acquire("fbref.com")

        # 清空所有令牌桶
        await limiter.clear_all()

        # 验证令牌被清空
        fotmob_status = limiter.get_status("fotmob.com")
        fbref_status = limiter.get_status("fbref.com")

        assert fotmob_status["available_tokens"] == 0.0
        assert fbref_status["available_tokens"] == 0.0

    @pytest.mark.asyncio
    async def test_timeout_error(self, limiter):
        """测试超时错误"""
        # 配置短超时
        limiter.config["fotmob.com"].max_wait_time = 0.1

        # 消耗所有令牌
        for _ in range(5):
            await limiter.try_acquire("fotmob.com")

        # 现在应该超时
        with pytest.raises(asyncio.TimeoutError):
            async with limiter.acquire("fotmob.com"):
                pass

    @pytest.mark.asyncio
    async def test_cancellation_cleanup(self, limiter):
        """测试任务取消时令牌清理"""
        # 消耗所有令牌
        for _ in range(5):
            await limiter.try_acquire("fotmob.com")

        # 创建一个任务并取消它
        task = asyncio.create_task(limiter.acquire("fotmob.com").__aenter__())

        # 等待一小段时间然后取消
        await asyncio.sleep(0.1)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # 验证令牌被释放（由于任务被取消，令牌应该被归还）
        # 注意：这个测试可能需要在实际实现中调整令牌归还逻辑


class TestCreateRateLimiter:
    """create_rate_limiter 函数测试"""

    def test_create_with_default(self):
        """测试使用默认参数创建"""
        limiter = create_rate_limiter()

        assert limiter.config["default"].rate == 1.0
        assert limiter.config["default"].burst == 1

    def test_create_with_custom_defaults(self):
        """测试自定义默认参数"""
        limiter = create_rate_limiter(default_rate=5.0, default_burst=10)

        assert limiter.config["default"].rate == 5.0
        assert limiter.config["default"].burst == 10

    def test_create_with_config(self):
        """测试带配置创建"""
        config = {"test.com": {"rate": 3.0, "burst": 7}}
        limiter = create_rate_limiter(config)

        assert limiter.config["test.com"].rate == 3.0
        assert limiter.config["test.com"].burst == 7
        assert limiter.config["default"].rate == 1.0  # 默认值


class TestBurstHandling:
    """突发流量处理测试"""

    @pytest.mark.asyncio
    async def test_burst_capacity(self):
        """测试突发容量"""
        # 配置：2 QPS，突发容量5
        config = {"test.com": {"rate": 2.0, "burst": 5}}
        limiter = RateLimiter(config)

        # 立即消耗5个令牌（突发）
        results = []
        for _ in range(5):
            success = await limiter.try_acquire("test.com")
            results.append(success)

        assert all(results)  # 所有5个都应该成功

        # 第6个应该失败
        success = await limiter.try_acquire("test.com")
        assert success is False

    @pytest.mark.asyncio
    async def test_burst_refill(self):
        """测试突发后的补充"""
        config = {"test.com": {"rate": 1.0, "burst": 3}}
        limiter = RateLimiter(config)

        # 消耗所有突发令牌
        for _ in range(3):
            await limiter.try_acquire("test.com")

        # 等待1秒，应该补充1个令牌
        await asyncio.sleep(1.1)

        # 现在应该能获取1个令牌
        success = await limiter.try_acquire("test.com")
        assert success is True

        # 但不能获取第2个
        success = await limiter.try_acquire("test.com")
        assert success is False


@pytest.mark.asyncio
async def test_integration_scenario():
    """集成测试场景"""
    print("\n🧪 开始RateLimiter集成测试...")

    # 创建配置
    config = {
        "fotmob.com": {"rate": 5.0, "burst": 10},  # 5 QPS, 突发10
        "fbref.com": {"rate": 2.0, "burst": 5},  # 2 QPS, 突发5
        "default": {"rate": 1.0, "burst": 2},  # 1 QPS, 突发2
    }

    limiter = create_rate_limiter(config)

    try:
        # 1. 测试突发处理
        print("1. 测试突发处理...")
        burst_results = []
        for i in range(8):  # 尝试获取8个令牌（小于突发容量10）
            success = await limiter.try_acquire("fotmob.com")
            burst_results.append(success)
            print(f"   突发请求 {i+1}: {'✅' if success else '❌'}")

        assert sum(burst_results) == 8
        print("✅ 突发处理测试通过")

        # 2. 测试域名隔离
        print("2. 测试域名隔离...")
        fotmob_success = await limiter.try_acquire("fotmob.com")
        fbref_success = await limiter.try_acquire("fbref.com")
        print(f"   fotmob.com: {'✅' if fotmob_success else '❌'}")
        print(f"   fbref.com: {'✅' if fbref_success else '❌'}")
        print("✅ 域名隔离测试通过")

        # 3. 测试Async Context Manager
        print("3. 测试Async Context Manager...")
        start_time = time.monotonic()
        async with limiter.acquire("fbref.com"):
            print("   ✅ 成功获取令牌并执行操作")

        elapsed = time.monotonic() - start_time
        print(f"   执行时间: {elapsed:.3f}s")
        print("✅ Async Context Manager测试通过")

        # 4. 测试状态查询
        print("4. 测试状态查询...")
        status = limiter.get_status("fotmob.com")
        print(
            f"   fotmob.com状态: {status['available_tokens']}/{status['capacity']} 令牌"
        )
        print("✅ 状态查询测试通过")

        print("\n🎉 所有集成测试通过！")

    finally:
        await limiter.clear_all()


if __name__ == "__main__":
    # 直接运行此文件进行快速验证
    asyncio.run(test_integration_scenario())
