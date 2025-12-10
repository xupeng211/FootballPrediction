"""
统一速率限制器实现 (基于Token Bucket算法)
Unified Rate Limiter Implementation (Token Bucket Algorithm)

基于 Token Bucket (令牌桶) 算法的异步速率限制器，支持：
1. 分域名独立限流
2. 配置驱动的动态策略
3. Async Context Manager 接口
4. 并发安全的令牌操作

算法原理：
- 令牌桶以恒定速率填充令牌
- 每个请求消耗一个令牌
- 桶容量限制了突发流量的大小
- 无令牌时请求需要等待

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any,  Optional


@dataclass
class RateLimitConfig:
    """
    速率限制配置类

    Args:
        rate: 每秒补充的令牌数 (QPS)
        burst: 桶的最大容量 (突发令牌数)
        max_wait_time: 最大等待时间 (秒)，None表示无限等待
    """

    rate: float
    burst: int
    max_wait_time: Optional[float] = None

    def __post_init__(self) -> None:
        """验证配置参数"""
        if self.rate <= 0:
            raise ValueError("Rate must be positive")
        if self.burst <= 0:
            raise ValueError("Burst must be positive")
        if self.max_wait_time is not None and self.max_wait_time < 0:
            raise ValueError("max_wait_time must be non-negative")


@dataclass
class TokenBucket:
    """
    令牌桶实现

    使用 asyncio.Lock 保证并发安全
    """

    tokens: float
    capacity: float
    refill_rate: float
    last_refill: float = field(default_factory=lambda: time.monotonic())
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        """初始化令牌桶"""
        if self.tokens > self.capacity:
            self.tokens = self.capacity

    async def consume(self, tokens: int = 1) -> bool:
        """
        消耗令牌

        Args:
            tokens: 要消耗的令牌数

        Returns:
            bool: 是否成功消耗令牌
        """
        async with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def wait_for_tokens(
        self, tokens: int = 1, timeout: Optional[float] = None
    ) -> bool:
        """
        等待直到有足够的令牌

        Args:
            tokens: 需要的令牌数
            timeout: 超时时间 (秒)

        Returns:
            bool: 是否成功获取令牌
        """
        start_time = time.monotonic()

        while True:
            async with self.lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

                # 计算需要等待的时间
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.refill_rate

                # 检查超时
                if timeout is not None:
                    elapsed = time.monotonic() - start_time
                    remaining_time = timeout - elapsed

                    if remaining_time <= 0:
                        return False

                    wait_time = min(wait_time, remaining_time)

            # 等待令牌补充
            await asyncio.sleep(wait_time)

    def _refill(self) -> None:
        """补充令牌（非线程安全，需要在锁内调用）"""
        now = time.monotonic()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now


class RateLimiter:
    """
    统一速率限制器

    基于 Token Bucket 算法实现多域名并发限流控制。
    支持配置驱动的动态策略和 Async Context Manager 接口。

    使用示例:
        config = {
            "fotmob.com": {"rate": 2.0, "burst": 5},
            "fbref.com": {"rate": 1.0, "burst": 3},
            "default": {"rate": 1.0, "burst": 1}
        }

        limiter = RateLimiter(config)

        # 使用 Async Context Manager
        async with limiter.acquire("fotmob.com"):
            # 在此范围内执行请求
            await some_http_request()
    """

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        default_config: Optional[RateLimitConfig] = None,
    ) -> None:
        """
        初始化速率限制器

        Args:
            config: 域名配置字典
            default_config: 默认配置
        """
        self.config: dict[str, RateLimitConfig] = {}
        self.buckets: dict[str, TokenBucket] = {}
        self._default_config = default_config or RateLimitConfig(
            rate=1.0, burst=1, max_wait_time=30.0
        )

        # 解析配置
        if config:
            self._parse_config(config)

        # 添加默认配置
        if "default" not in self.config:
            self.config["default"] = self._default_config

    def _parse_config(self, config: dict[str, Any]) -> None:
        """
        解析配置字典

        Args:
            config: 配置字典，支持两种格式：
                1. {"domain": {"rate": 2.0, "burst": 5}}
                2. {"domain": RateLimitConfig(2.0, 5)}
        """
        for domain, cfg in config.items():
            if isinstance(cfg, dict):
                # 字典格式配置
                rate = cfg.get("rate", 1.0)
                burst = cfg.get("burst", 1)
                max_wait_time = cfg.get("max_wait_time")
                self.config[domain] = RateLimitConfig(
                    rate=float(rate), burst=int(burst), max_wait_time=max_wait_time
                )
            elif isinstance(cfg, RateLimitConfig):
                # 直接使用 RateLimitConfig 对象
                self.config[domain] = cfg
            else:
                raise ValueError(f"Invalid config for domain {domain}: {cfg}")

    def _get_bucket(self, domain: str) -> TokenBucket:
        """
        获取或创建域名的令牌桶

        Args:
            domain: 域名

        Returns:
            TokenBucket: 令牌桶实例
        """
        if domain not in self.buckets:
            # 使用域名特定配置或默认配置
            config = self.config.get(domain, self.config["default"])
            self.buckets[domain] = TokenBucket(
                tokens=config.burst, capacity=config.burst, refill_rate=config.rate
            )
        return self.buckets[domain]

    @asynccontextmanager
    async def acquire(self, domain: str, tokens: int = 1):
        """
        获取令牌的 Async Context Manager

        Args:
            domain: 域名
            tokens: 需要的令牌数

        Yields:
            None: 成功获取令牌

        Raises:
            asyncio.TimeoutError: 超时未获取令牌
            RuntimeError: 速率限制配置错误
        """
        bucket = self._get_bucket(domain)
        config = self.config.get(domain, self.config["default"])

        # 尝试立即获取令牌
        if await bucket.consume(tokens):
            yield
            return

        # 需要等待令牌
        try:
            success = await bucket.wait_for_tokens(
                tokens=tokens, timeout=config.max_wait_time
            )

            if not success:
                raise TimeoutError(
                    f"Rate limit exceeded for domain {domain}: "
                    f"waited {config.max_wait_time}s without acquiring {tokens} tokens"
                )

            yield

        except asyncio.CancelledError:
            # 任务被取消，释放令牌
            async with bucket.lock:
                bucket.tokens = min(bucket.capacity, bucket.tokens + tokens)
            raise

    async def try_acquire(self, domain: str, tokens: int = 1) -> bool:
        """
        尝试立即获取令牌（非阻塞）

        Args:
            domain: 域名
            tokens: 需要的令牌数

        Returns:
            bool: 是否成功获取令牌
        """
        bucket = self._get_bucket(domain)
        return await bucket.consume(tokens)

    async def wait_for_available(self, domain: str, tokens: int = 1) -> float:
        """
        等待令牌可用并返回等待时间

        Args:
            domain: 域名
            tokens: 需要的令牌数

        Returns:
            float: 实际等待时间（秒）
        """
        start_time = time.monotonic()
        bucket = self._get_bucket(domain)
        config = self.config.get(domain, self.config["default"])

        await bucket.wait_for_tokens(tokens, config.max_wait_time)
        return time.monotonic() - start_time

    def get_status(self, domain: Optional[str] = None) -> dict[str, Any]:
        """
        获取速率限制器状态

        Args:
            domain: 特定域名，None表示所有域名

        Returns:
            dict[str, Any]: 状态信息
        """
        if domain:
            if domain not in self.buckets:
                return {"error": f"No bucket found for domain: {domain}"}

            bucket = self.buckets[domain]
            config = self.config.get(domain, self.config["default"])

            return {
                "domain": domain,
                "available_tokens": bucket.tokens,
                "capacity": bucket.capacity,
                "rate": bucket.refill_rate,
                "config": {
                    "rate": config.rate,
                    "burst": config.burst,
                    "max_wait_time": config.max_wait_time,
                },
            }
        else:
            # 返回所有域名的状态
            status = {}
            for d, bucket in self.buckets.items():
                config = self.config.get(d, self.config["default"])
                status[d] = {
                    "available_tokens": bucket.tokens,
                    "capacity": bucket.capacity,
                    "rate": bucket.refill_rate,
                    "config": {
                        "rate": config.rate,
                        "burst": config.burst,
                        "max_wait_time": config.max_wait_time,
                    },
                }
            return status

    def update_config(self, domain: str, config: RateLimitConfig) -> None:
        """
        更新域名配置

        Args:
            domain: 域名
            config: 新的速率限制配置
        """
        self.config[domain] = config

        # 如果已存在令牌桶，需要重新创建以应用新配置
        if domain in self.buckets:
            del self.buckets[domain]

    def remove_domain(self, domain: str) -> None:
        """
        移除域名配置和令牌桶

        Args:
            domain: 要移除的域名
        """
        if domain in self.config:
            del self.config[domain]
        if domain in self.buckets:
            del self.buckets[domain]

    async def clear_all(self) -> None:
        """清空所有令牌桶"""
        for bucket in self.buckets.values():
            async with bucket.lock:
                bucket.tokens = 0.0


# 便利函数
def create_rate_limiter(
    config: Optional[dict[str, Any]] = None,
    default_rate: float = 1.0,
    default_burst: int = 1,
) -> RateLimiter:
    """
    创建速率限制器的便利函数

    Args:
        config: 域名配置字典
        default_rate: 默认速率
        default_burst: 默认突发容量

    Returns:
        RateLimiter: 速率限制器实例
    """
    default_config = RateLimitConfig(
        rate=default_rate, burst=default_burst, max_wait_time=30.0
    )

    return RateLimiter(config, default_config)


# 模块导出
__all__ = [
    "RateLimiter",
    "RateLimitConfig",
    "TokenBucket",
    "create_rate_limiter",
]
