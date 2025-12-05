"""智能请求频率控制器 - 反爬对抗组件
Intelligent Rate Limiter - Anti-Scraping Component.

提供自适应请求频率控制、智能延迟调节等功能。
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from src.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitStrategy(Enum):
    """频率限制策略."""
    CONSERVATIVE = "conservative"  # 保守策略：较长延迟
    NORMAL = "normal"             # 正常策略：标准延迟
    AGGRESSIVE = "aggressive"     # 激进策略：较短延迟
    ADAPTIVE = "adaptive"         # 自适应策略：根据响应调整


@dataclass
class RequestConfig:
    """请求配置."""
    min_delay: float = 1.0        # 最小延迟（秒）
    max_delay: float = 10.0       # 最大延迟（秒）
    base_delay: float = 2.0       # 基础延迟（秒）
    burst_limit: int = 5          # 突发请求限制
    recovery_time: float = 30.0   # 恢复时间（秒）

    # 延迟增加因子
    error_delay_multiplier: float = 2.0  # 错误时延迟倍数
    success_delay_reduction: float = 0.9  # 成功时延迟缩减因子


@dataclass
class DomainStats:
    """域名统计信息."""
    domain: str
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_request_time: float = 0.0
    last_success_time: float = 0.0
    last_error_time: float = 0.0
    current_delay: float = 2.0
    consecutive_errors: int = 0
    consecutive_successes: int = 0
    total_response_time: float = 0.0
    avg_response_time: float = 0.0

    @property
    def success_rate(self) -> float:
        """成功率."""
        if self.request_count == 0:
            return 0.0
        return self.success_count / self.request_count

    @property
    def error_rate(self) -> float:
        """错误率."""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count


class RateLimiter:
    """智能请求频率控制器."""

    def __init__(
        self,
        strategy: RateLimitStrategy = RateLimitStrategy.ADAPTIVE,
        config: RequestConfig = None,
        max_domains: int = 100
    ):
        self.strategy = strategy
        self.config = config or RequestConfig()
        self.max_domains = max_domains

        # 域名统计信息
        self.domain_stats: dict[str, DomainStats] = {}
        self._lock = asyncio.Lock()

        # 全局请求计数器
        self.global_request_count = 0
        self.global_last_request_time = 0.0

        logger.info(f"频率控制器初始化完成，策略: {strategy.value}")

    async def wait_for_slot(self, domain: str) -> float:
        """等待请求时机，返回实际延迟时间."""
        async with self._lock:
            stats = self._get_or_create_stats(domain)

            # 计算延迟时间
            delay = await self._calculate_delay(stats)

            # 应用延迟
            if delay > 0:
                logger.debug(f"域名 {domain} 延迟 {delay:.2f}s")
                await asyncio.sleep(delay)

            # 更新统计信息
            stats.last_request_time = time.time()
            self.global_last_request_time = time.time()
            self.global_request_count += 1

            return delay

    async def _calculate_delay(self, stats: DomainStats) -> float:
        """计算延迟时间."""
        current_time = time.time()

        if self.strategy == RateLimitStrategy.CONSERVATIVE:
            return self._conservative_delay(stats, current_time)
        elif self.strategy == RateLimitStrategy.NORMAL:
            return self._normal_delay(stats, current_time)
        elif self.strategy == RateLimitStrategy.AGGRESSIVE:
            return self._aggressive_delay(stats, current_time)
        elif self.strategy == RateLimitStrategy.ADAPTIVE:
            return await self._adaptive_delay(stats, current_time)
        else:
            return self.config.base_delay

    def _conservative_delay(self, stats: DomainStats, current_time: float) -> float:
        """保守策略延迟计算."""
        # 使用较长的基础延迟
        base_delay = self.config.base_delay * 2.0

        # 考虑连续错误
        if stats.consecutive_errors > 0:
            base_delay *= (1 + stats.consecutive_errors * 0.5)

        # 确保最小延迟
        return max(base_delay, self.config.min_delay * 2.0)

    def _normal_delay(self, stats: DomainStats, current_time: float) -> float:
        """正常策略延迟计算."""
        # 基础延迟 + 随机波动
        delay = self.config.base_delay + random.uniform(-0.5, 0.5)

        # 错误惩罚
        if stats.consecutive_errors > 0:
            delay *= (1 + stats.consecutive_errors * 0.3)

        return max(delay, self.config.min_delay)

    def _aggressive_delay(self, stats: DomainStats, current_time: float) -> float:
        """激进策略延迟计算."""
        # 较短的基础延迟
        delay = self.config.base_delay * 0.7

        # 随机波动较小
        delay += random.uniform(-0.2, 0.2)

        # 错误惩罚较轻
        if stats.consecutive_errors > 0:
            delay *= (1 + stats.consecutive_errors * 0.2)

        return max(delay, self.config.min_delay * 0.5)

    async def _adaptive_delay(self, stats: DomainStats, current_time: float) -> float:
        """自适应策略延迟计算."""
        # 基于成功率和响应时间动态调整
        delay = stats.current_delay

        # 根据成功率调整
        if stats.request_count > 5:  # 有足够样本时才调整
            success_rate = stats.success_rate

            if success_rate < 0.8:  # 成功率低，增加延迟
                delay *= 1.5
            elif success_rate > 0.95:  # 成功率高，减少延迟
                delay *= 0.8

        # 根据连续错误调整
        if stats.consecutive_errors > 0:
            delay *= (1 + stats.consecutive_errors * 0.4)

        # 根据响应时间调整
        if stats.avg_response_time > 5.0:  # 响应慢，增加延迟
            delay *= 1.2

        # 添加随机性避免模式识别
        delay += random.uniform(-delay * 0.1, delay * 0.1)

        # 应用配置限制
        delay = max(delay, self.config.min_delay)
        delay = min(delay, self.config.max_delay)

        return delay

    async def record_success(self, domain: str, response_time: float):
        """记录成功请求."""
        async with self._lock:
            stats = self._get_or_create_stats(domain)

            stats.request_count += 1
            stats.success_count += 1
            stats.last_success_time = time.time()
            stats.consecutive_errors = 0
            stats.consecutive_successes += 1
            stats.total_response_time += response_time
            stats.avg_response_time = stats.total_response_time / stats.success_count

            # 自适应调整当前延迟
            if self.strategy == RateLimitStrategy.ADAPTIVE:
                # 连续成功时逐渐减少延迟
                if stats.consecutive_successes >= 3:
                    stats.current_delay *= self.config.success_delay_reduction
                    stats.current_delay = max(stats.current_delay, self.config.min_delay)

            logger.debug(f"域名 {domain} 成功记录，响应时间: {response_time:.2f}s")

    async def record_error(self, domain: str, error_type: str = "unknown"):
        """记录错误请求."""
        async with self._lock:
            stats = self._get_or_create_stats(domain)

            stats.request_count += 1
            stats.error_count += 1
            stats.last_error_time = time.time()
            stats.consecutive_errors += 1
            stats.consecutive_successes = 0

            # 自适应调整当前延迟
            if self.strategy == RateLimitStrategy.ADAPTIVE:
                # 错误时增加延迟
                stats.current_delay *= self.config.error_delay_multiplier
                stats.current_delay = min(stats.current_delay, self.config.max_delay)

            logger.warning(f"域名 {domain} 错误记录 ({error_type})，连续错误: {stats.consecutive_errors}")

    def _get_or_create_stats(self, domain: str) -> DomainStats:
        """获取或创建域名统计信息."""
        if domain not in self.domain_stats:
            # 限制域名数量
            if len(self.domain_stats) >= self.max_domains:
                # 移除最旧的域名
                oldest_domain = min(
                    self.domain_stats.keys(),
                    key=lambda d: self.domain_stats[d].last_request_time
                )
                del self.domain_stats[oldest_domain]
                logger.info(f"移除最旧域名统计: {oldest_domain}")

            self.domain_stats[domain] = DomainStats(
                domain=domain,
                current_delay=self.config.base_delay
            )

        return self.domain_stats[domain]

    def get_domain_stats(self, domain: str) -> Optional[DomainStats]:
        """获取域名统计信息."""
        return self.domain_stats.get(domain)

    def get_all_stats(self) -> dict[str, DomainStats]:
        """获取所有域名统计信息."""
        return self.domain_stats.copy()

    def get_global_stats(self) -> dict:
        """获取全局统计信息."""
        total_requests = sum(stats.request_count for stats in self.domain_stats.values())
        total_successes = sum(stats.success_count for stats in self.domain_stats.values())
        total_errors = sum(stats.error_count for stats in self.domain_stats.values())

        avg_success_rate = total_successes / total_requests if total_requests > 0 else 0.0

        return {
            "strategy": self.strategy.value,
            "total_requests": total_requests,
            "global_request_count": self.global_request_count,
            "total_successes": total_successes,
            "total_errors": total_errors,
            "success_rate": avg_success_rate,
            "active_domains": len(self.domain_stats),
            "config": {
                "min_delay": self.config.min_delay,
                "max_delay": self.config.max_delay,
                "base_delay": self.config.base_delay,
            }
        }

    async def reset_stats(self, domain: str = None):
        """重置统计信息."""
        async with self._lock:
            if domain:
                if domain in self.domain_stats:
                    del self.domain_stats[domain]
                    logger.info(f"重置域名统计: {domain}")
            else:
                self.domain_stats.clear()
                self.global_request_count = 0
                self.global_last_request_time = 0.0
                logger.info("重置所有统计信息")

    def set_strategy(self, strategy: RateLimitStrategy):
        """设置频率限制策略."""
        old_strategy = self.strategy
        self.strategy = strategy
        logger.info(f"频率策略变更: {old_strategy.value} -> {strategy.value}")

    async def adjust_delays(self, factor: float):
        """批量调整所有域名的延迟."""
        async with self._lock:
            for stats in self.domain_stats.values():
                stats.current_delay *= factor
                stats.current_delay = max(stats.current_delay, self.config.min_delay)
                stats.current_delay = min(stats.current_delay, self.config.max_delay)

            logger.info(f"所有域名延迟调整: {factor:.2f}x")


# 全局频率控制器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取全局频率控制器实例."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def wait_for_request_slot(domain: str) -> float:
    """等待请求时机的便捷函数."""
    return await get_rate_limiter().wait_for_slot(domain)


async def record_request_success(domain: str, response_time: float):
    """记录成功请求的便捷函数."""
    await get_rate_limiter().record_success(domain, response_time)


async def record_request_error(domain: str, error_type: str = "unknown"):
    """记录错误请求的便捷函数."""
    await get_rate_limiter().record_error(domain, error_type)
