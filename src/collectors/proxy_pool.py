"""代理池管理器 - 反爬对抗核心组件
Proxy Pool Manager - Anti-Scraping Core Component.

提供智能代理轮换、健康检查、性能监控等功能。
"""

import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import aiohttp
import backoff
from src.core.logging import get_logger

logger = get_logger(__name__)


class ProxyStatus(Enum):
    """代理状态枚举."""
    ACTIVE = "active"
    FAILED = "failed"
    TESTING = "testing"
    BANNED = "banned"


@dataclass
class ProxyConfig:
    """代理配置."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: str = "http"  # http, https, socks5

    @property
    def url(self) -> str:
        """生成代理URL."""
        if self.username and self.password:
            return f"{self.proxy_type}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type}://{self.host}:{self.port}"

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class ProxyStats:
    """代理统计信息."""
    success_count: int = 0
    failure_count: int = 0
    total_response_time: float = 0.0
    last_used: Optional[float] = None
    last_success: Optional[float] = None
    ban_count: int = 0

    @property
    def success_rate(self) -> float:
        """成功率."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    @property
    def avg_response_time(self) -> float:
        """平均响应时间."""
        return self.total_response_time / max(self.success_count, 1)


class ProxyPool:
    """智能代理池管理器."""

    def __init__(
        self,
        proxy_list: list[ProxyConfig],
        max_retries: int = 3,
        test_timeout: int = 10,
        health_check_interval: int = 300,  # 5分钟
        ban_threshold: int = 5,  # 连续失败5次视为被封
        cooldown_time: int = 3600,  # 冷却时间1小时
    ):
        self.proxies: dict[ProxyConfig, ProxyStats] = {proxy: ProxyStats() for proxy in proxy_list}
        self.active_proxies: set[ProxyConfig] = set(proxy_list)
        self.failed_proxies: set[ProxyConfig] = set()
        self.banned_proxies: set[ProxyConfig] = set()

        self.max_retries = max_retries
        self.test_timeout = test_timeout
        self.health_check_interval = health_check_interval
        self.ban_threshold = ban_threshold
        self.cooldown_time = cooldown_time

        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None

        logger.info(f"代理池初始化完成，共{len(proxy_list)}个代理")

    async def start_health_check(self):
        """启动健康检查任务."""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("代理池健康检查任务已启动")

    async def stop_health_check(self):
        """停止健康检查任务."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            logger.info("代理池健康检查任务已停止")

    async def _health_check_loop(self):
        """健康检查循环."""
        while True:
            try:
                await self._check_all_proxies()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查异常: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟

    async def _check_all_proxies(self):
        """检查所有代理的健康状态."""
        logger.info("开始代理健康检查...")

        tasks = []
        for proxy in list(self.proxies.keys()):
            if proxy not in self.banned_proxies:
                tasks.append(self._test_proxy(proxy))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        active_count = len(self.active_proxies)
        failed_count = len(self.failed_proxies)
        banned_count = len(self.banned_proxies)

        logger.info(
            f"代理健康检查完成: 活跃={active_count}, 失败={failed_count}, 封禁={banned_count}"
        )

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=2,
        base=1,
        max_value=10
    )
    async def _test_proxy(self, proxy: ProxyConfig) -> bool:
        """测试代理是否可用."""
        stats = self.proxies[proxy]

        try:
            start_time = time.time()

            # 使用httpbin.org测试代理
            test_url = "http://httpbin.org/ip"

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.test_timeout)
            ) as session:
                async with session.get(test_url, proxy=proxy.url) as response:
                    if response.status == 200:
                        await response.json()
                        response_time = time.time() - start_time

                        # 更新统计信息
                        async with self._lock:
                            stats.success_count += 1
                            stats.total_response_time += response_time
                            stats.last_success = time.time()
                            stats.last_used = time.time()

                            # 重置失败计数
                            stats.failure_count = 0

                            # 如果代理之前失败，现在恢复
                            if proxy in self.failed_proxies:
                                self.failed_proxies.remove(proxy)
                                self.active_proxies.add(proxy)
                                logger.info(f"代理 {proxy} 已恢复")

                        logger.debug(f"代理 {proxy} 测试成功，响应时间: {response_time:.2f}s")
                        return True
                    else:
                        raise aiohttp.ClientError(f"HTTP {response.status}")

        except Exception as e:
            async with self._lock:
                stats.failure_count += 1
                stats.last_used = time.time()

                # 检查是否达到封禁阈值
                if stats.failure_count >= self.ban_threshold:
                    stats.ban_count += 1
                    self.banned_proxies.add(proxy)
                    if proxy in self.active_proxies:
                        self.active_proxies.remove(proxy)
                    if proxy in self.failed_proxies:
                        self.failed_proxies.remove(proxy)
                    logger.warning(f"代理 {proxy} 连续失败{stats.failure_count}次，标记为封禁")
                else:
                    if proxy not in self.failed_proxies:
                        self.failed_proxies.add(proxy)
                        if proxy in self.active_proxies:
                            self.active_proxies.remove(proxy)
                    logger.warning(f"代理 {proxy} 测试失败 ({stats.failure_count}/{self.ban_threshold}): {e}")

            return False

    async def get_proxy(self) -> Optional[ProxyConfig]:
        """获取最佳代理."""
        async with self._lock:
            # 如果没有活跃代理，尝试恢复一些失败代理
            if not self.active_proxies:
                if self.failed_proxies:
                    # 随机选择一个失败代理进行测试
                    proxy = random.choice(list(self.failed_proxies))
                    if await self._test_proxy(proxy):
                        return proxy

                logger.error("没有可用的代理")
                return None

            # 选择响应时间最短的活跃代理
            best_proxy = min(
                self.active_proxies,
                key=lambda p: self.proxies[p].avg_response_time
            )

            # 更新使用时间
            self.proxies[best_proxy].last_used = time.time()

            return best_proxy

    async def mark_proxy_failed(self, proxy: ProxyConfig, error: Exception):
        """标记代理失败."""
        async with self._lock:
            stats = self.proxies[proxy]
            stats.failure_count += 1

            # 检查是否需要封禁
            if stats.failure_count >= self.ban_threshold:
                stats.ban_count += 1
                self.banned_proxies.add(proxy)
                if proxy in self.active_proxies:
                    self.active_proxies.remove(proxy)
                if proxy in self.failed_proxies:
                    self.failed_proxies.remove(proxy)
                logger.error(f"代理 {proxy} 被标记为封禁，错误: {error}")
            else:
                if proxy not in self.failed_proxies:
                    self.failed_proxies.add(proxy)
                    if proxy in self.active_proxies:
                        self.active_proxies.remove(proxy)
                logger.warning(f"代理 {proxy} 标记为失败，错误: {error}")

    async def mark_proxy_success(self, proxy: ProxyConfig, response_time: float):
        """标记代理成功."""
        async with self._lock:
            stats = self.proxies[proxy]
            stats.success_count += 1
            stats.total_response_time += response_time
            stats.last_success = time.time()
            stats.last_used = time.time()

            # 重置失败计数
            stats.failure_count = 0

            # 确保代理在活跃集合中
            if proxy not in self.active_proxies:
                self.active_proxies.add(proxy)
            if proxy in self.failed_proxies:
                self.failed_proxies.remove(proxy)
            if proxy in self.banned_proxies:
                # 检查是否可以解封（冷却时间）
                if stats.last_success and (time.time() - stats.last_success) > self.cooldown_time:
                    self.banned_proxies.remove(proxy)
                    logger.info(f"代理 {proxy} 冷却时间已过，解封")

    def get_stats(self) -> dict:
        """获取代理池统计信息."""
        total_proxies = len(self.proxies)
        active_count = len(self.active_proxies)
        failed_count = len(self.failed_proxies)
        banned_count = len(self.banned_proxies)

        # 计算平均成功率
        total_success_rate = 0.0
        total_response_time = 0.0
        proxy_count = 0

        for stats in self.proxies.values():
            if stats.success_count > 0:
                total_success_rate += stats.success_rate
                total_response_time += stats.avg_response_time
                proxy_count += 1

        avg_success_rate = total_success_rate / max(proxy_count, 1)
        avg_response_time = total_response_time / max(proxy_count, 1)

        return {
            "total_proxies": total_proxies,
            "active_proxies": active_count,
            "failed_proxies": failed_count,
            "banned_proxies": banned_count,
            "availability_rate": active_count / total_proxies if total_proxies > 0 else 0,
            "avg_success_rate": avg_success_rate,
            "avg_response_time": avg_response_time,
            "health_check_interval": self.health_check_interval,
        }

    @classmethod
    def from_env(cls) -> "ProxyPool":
        """从环境变量创建代理池."""
        import os

        proxy_configs = []

        # 从环境变量读取代理列表
        proxy_list_str = os.getenv("PROXY_LIST", "")
        if proxy_list_str:
            for proxy_str in proxy_list_str.split(","):
                proxy_str = proxy_str.strip()
                if proxy_str:
                    # 支持格式: host:port 或 username:password@host:port
                    if "@" in proxy_str:
                        auth_part, addr_part = proxy_str.split("@", 1)
                        if ":" in auth_part:
                            username, password = auth_part.split(":", 1)
                        else:
                            username, password = auth_part, None
                    else:
                        username, password = None, None
                        addr_part = proxy_str

                    if ":" in addr_part:
                        host, port_str = addr_part.split(":", 1)
                        port = int(port_str)

                        proxy_configs.append(ProxyConfig(
                            host=host.strip(),
                            port=port,
                            username=username,
                            password=password
                        ))

        # 如果没有配置代理，返回空代理池
        if not proxy_configs:
            logger.warning("未配置代理列表，代理池将为空")

        return cls(proxy_configs)


# 全局代理池实例
_proxy_pool: Optional[ProxyPool] = None


async def get_proxy_pool() -> ProxyPool:
    """获取全局代理池实例."""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPool.from_env()
        await _proxy_pool.start_health_check()
    return _proxy_pool


async def close_proxy_pool():
    """关闭代理池."""
    global _proxy_pool
    if _proxy_pool:
        await _proxy_pool.stop_health_check()
        _proxy_pool = None
