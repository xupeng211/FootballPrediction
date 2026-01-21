#!/usr/bin/env python3
"""
V41.77 代理健康检查模块 - 心跳检测与自愈
==========================================

本模块实现代理端口的健康检查和自动剔除：
1. 心跳检测：定期检查代理端口可用性
2. 自动剔除：不可用端口从池中移除
3. 自愈机制：端口恢复后自动加入
4. 代理池管理：动态维护可用端口列表

Author: 首席系统架构师
Version: V41.77
Date: 2026-01-15
"""

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import socket
import time

import aiohttp
import requests

logger = logging.getLogger(__name__)


@dataclass
class ProxyPortStatus:
    """代理端口状态"""
    port: int
    is_healthy: bool
    last_check: datetime
    last_success: datetime | None = None
    last_failure: datetime | None = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    failure_reason: str = ""


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    port: int
    is_healthy: bool
    response_time: float
    ip_address: str | None = None
    error: str = ""


class ProxyHealthChecker:
    """
    V41.77: 代理健康检查器

    功能：
    - 心跳检测代理端口
    - 自动剔除不可用端口
    - 自愈机制
    - 代理池动态管理
    """

    def __init__(
        self,
        proxy_host: str = "127.0.0.1",
        check_interval: int = 60,
        max_consecutive_failures: int = 3,
        recovery_check_interval: int = 300,
    ):
        """
        初始化健康检查器

        Args:
            proxy_host: 代理主机
            check_interval: 检查间隔（秒）
            max_consecutive_failures: 最大连续失败次数
            recovery_check_interval: 恢复检查间隔（秒）
        """
        self.proxy_host = proxy_host
        self.check_interval = check_interval
        self.max_consecutive_failures = max_consecutive_failures
        self.recovery_check_interval = recovery_check_interval

        # 端口状态跟踪
        self.port_status: dict[int, ProxyPortStatus] = {}
        self.available_ports: set[int] = set()
        self.failed_ports: set[int] = set()

        # 运行状态
        self.is_running = False
        self._check_task: asyncio.Task | None = None

        logger.info(
            f"✅ V41.77 ProxyHealthChecker 初始化完成 "
            f"(host={proxy_host}, check_interval={check_interval}s)"
        )

    def set_ports(self, ports: list[int]) -> None:
        """
        设置初始代理端口列表

        Args:
            ports: 端口列表
        """
        now = datetime.now()

        for port in ports:
            self.port_status[port] = ProxyPortStatus(
                port=port,
                is_healthy=True,  # 初始假设健康
                last_check=now,
            )
            self.available_ports.add(port)

        logger.info(f"📋 代理端口列表已设置: {len(ports)} 个端口")

    def get_available_ports(self) -> list[int]:
        """
        获取当前可用端口列表

        Returns:
            可用端口列表
        """
        return sorted(self.available_ports)

    def get_healthy_ports(self) -> list[int]:
        """
        获取健康端口列表

        Returns:
            健康端口列表
        """
        return [
            port for port, status in self.port_status.items()
            if status.is_healthy
        ]

    async def check_port(self, port: int, timeout: float = 5.0) -> HealthCheckResult:
        """
        检查单个端口的健康状态

        Args:
            port: 端口号
            timeout: 超时时间

        Returns:
            HealthCheckResult 对象
        """
        start_time = time.time()

        try:
            # 方法 1: TCP 连接测试
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.proxy_host, port))
            sock.close()

            if result == 0:
                # TCP 连接成功
                response_time = (time.time() - start_time) * 1000

                # 方法 2: HTTP 请求测试（获取 IP）
                ip_address = await self._get_proxy_ip(port, timeout)

                return HealthCheckResult(
                    port=port,
                    is_healthy=True,
                    response_time=response_time,
                    ip_address=ip_address,
                    error=""
                )
            return HealthCheckResult(
                port=port,
                is_healthy=False,
                response_time=0,
                ip_address=None,
                error=f"TCP connection failed (code={result})"
            )

        except socket.gaierror:
            return HealthCheckResult(
                port=port,
                is_healthy=False,
                response_time=0,
                ip_address=None,
                error="DNS resolution failed"
            )
        except TimeoutError:
            return HealthCheckResult(
                port=port,
                is_healthy=False,
                response_time=timeout * 1000,
                ip_address=None,
                error="Connection timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                port=port,
                is_healthy=False,
                response_time=0,
                ip_address=None,
                error=str(e)
            )

    async def _get_proxy_ip(self, port: int, timeout: float = 5.0) -> str | None:
        """
        通过代理获取 IP 地址

        Args:
            port: 代理端口
            timeout: 超时时间

        Returns:
            IP 地址或 None
        """
        try:
            proxy_url = f"http://{self.proxy_host}:{port}"
            timeout_obj = aiohttp.ClientTimeout(total=timeout)

            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.get(
                    "https://api.ipify.org?format=text",
                    proxy=proxy_url,
                    timeout=timeout_obj
                ) as response:
                    if response.status == 200:
                        return await response.text()

            return None

        except Exception as e:
            logger.debug(f"获取代理 IP 失败 ({port}): {e}")
            return None

    def update_port_status(self, result: HealthCheckResult) -> None:
        """
        更新端口状态

        Args:
            result: 健康检查结果
        """
        port = result.port
        now = datetime.now()

        if port not in self.port_status:
            self.port_status[port] = ProxyPortStatus(
                port=port,
                is_healthy=True,
                last_check=now,
            )

        status = self.port_status[port]
        status.last_check = now

        if result.is_healthy:
            status.is_healthy = True
            status.last_success = now
            status.consecutive_failures = 0
            status.consecutive_successes += 1
            status.failure_reason = ""

            # 从失败列表移除
            if port in self.failed_ports:
                self.failed_ports.remove(port)
                logger.info(f"✅ 端口 {port} 已恢复")

            # 加入可用列表
            self.available_ports.add(port)

        else:
            status.is_healthy = False
            status.last_failure = now
            status.consecutive_failures += 1
            status.consecutive_successes = 0
            status.failure_reason = result.error

            # 从可用列表移除
            if port in self.available_ports:
                self.available_ports.remove(port)

            # 连续失败达到阈值，加入失败列表
            if status.consecutive_failures >= self.max_consecutive_failures:
                if port not in self.failed_ports:
                    self.failed_ports.add(port)
                    logger.warning(
                        f"❌ 端口 {port} 已标记为不可用 "
                        f"(连续失败 {status.consecutive_failures} 次): {result.error}"
                    )

    async def check_all_ports(self, ports: list[int] | None = None) -> dict[int, HealthCheckResult]:
        """
        检查所有端口的健康状态

        Args:
            ports: 要检查的端口列表（默认为所有端口）

        Returns:
            端口到检查结果的映射
        """
        if ports is None:
            ports = self.get_healthy_ports()

        results = {}

        # 并发检查所有端口
        tasks = [self.check_port(port) for port in ports]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(check_results):
            if isinstance(result, Exception):
                port = ports[i]
                results[port] = HealthCheckResult(
                    port=port,
                    is_healthy=False,
                    response_time=0,
                    ip_address=None,
                    error=str(result)
                )
            else:
                results[result.port] = result
                self.update_port_status(result)

        return results

    async def check_failed_ports(self) -> dict[int, HealthCheckResult]:
        """
        检查失败端口是否恢复

        Returns:
            端口到检查结果的映射
        """
        if not self.failed_ports:
            return {}

        failed_ports_list = list(self.failed_ports)
        results = {}

        logger.info(f"🔍 检查 {len(failed_ports_list)} 个失败端口...")

        for port in failed_ports_list:
            result = await self.check_port(port)
            results[port] = result

            if result.is_healthy:
                logger.info(f"✅ 端口 {port} 已恢复")
            else:
                logger.debug(f"⏳ 端口 {port} 仍未恢复")

        return results

    async def start_background_check(self) -> None:
        """启动后台健康检查任务"""
        if self.is_running:
            logger.warning("⚠️  健康检查任务已在运行")
            return

        self.is_running = True
        self._check_task = asyncio.create_task(self._background_check_loop())

        logger.info("🔄 V41.77: 后台健康检查任务已启动")

    async def stop_background_check(self) -> None:
        """停止后台健康检查任务"""
        if not self.is_running:
            return

        self.is_running = False

        if self._check_task:
            self._check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._check_task

        logger.info("⏹️  后台健康检查任务已停止")

    async def _background_check_loop(self) -> None:
        """后台检查循环"""
        recovery_check_time = None

        while self.is_running:
            try:
                now = datetime.now()

                # 定期检查健康端口
                await self.check_all_ports()

                # 定期检查失败端口（自愈）
                if recovery_check_time is None or now >= recovery_check_time:
                    await self.check_failed_ports()
                    recovery_check_time = now + timedelta(seconds=self.recovery_check_interval)

                # 等待下次检查
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.info("⏹️  健康检查任务被取消")
                break
            except Exception as e:
                logger.exception(f"❌ 健康检查任务出错: {e}")
                await asyncio.sleep(self.check_interval)

    def get_status_summary(self) -> dict:
        """
        获取状态摘要

        Returns:
            状态摘要字典
        """
        return {
            "total_ports": len(self.port_status),
            "available_ports": len(self.available_ports),
            "failed_ports": len(self.failed_ports),
            "is_running": self.is_running,
            "available_port_list": sorted(self.available_ports),
            "failed_port_list": sorted(self.failed_ports),
        }


# ============================================================================
# 同步包装函数（用于非异步环境）
# ============================================================================

def check_proxy_port_sync(host: str, port: int, timeout: float = 5.0) -> HealthCheckResult:
    """
    同步检查代理端口健康状态

    Args:
        host: 代理主机
        port: 端口号
        timeout: 超时时间

    Returns:
        HealthCheckResult 对象
    """
    start_time = time.time()

    try:
        # TCP 连接测试
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            response_time = (time.time() - start_time) * 1000

            # HTTP 请求测试
            ip_address = None
            try:
                proxies = {
                    "http": f"http://{host}:{port}",
                    "https": f"http://{host}:{port}",
                }
                response = requests.get(
                    "https://api.ipify.org?format=text",
                    proxies=proxies,
                    timeout=timeout
                )
                if response.status_code == 200:
                    ip_address = response.text.strip()
            except Exception:
                pass  # IP 获取失败不影响健康状态

            return HealthCheckResult(
                port=port,
                is_healthy=True,
                response_time=response_time,
                ip_address=ip_address,
                error=""
            )
        return HealthCheckResult(
            port=port,
            is_healthy=False,
            response_time=0,
            ip_address=None,
            error=f"TCP connection failed (code={result})"
        )

    except Exception as e:
        return HealthCheckResult(
            port=port,
            is_healthy=False,
            response_time=0,
            ip_address=None,
            error=str(e)
        )


# ============================================================================
# 便捷函数
# ============================================================================

def create_proxy_health_checker(
    proxy_ports: list[int],
    proxy_host: str = "127.0.0.1",
    check_interval: int = 60,
) -> ProxyHealthChecker:
    """
    创建并配置代理健康检查器

    Args:
        proxy_ports: 代理端口列表
        proxy_host: 代理主机
        check_interval: 检查间隔

    Returns:
        ProxyHealthChecker 实例
    """
    checker = ProxyHealthChecker(
        proxy_host=proxy_host,
        check_interval=check_interval,
    )
    checker.set_ports(proxy_ports)

    return checker


if __name__ == "__main__":
    # 测试代理健康检查

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s"
    )

    async def test():
        # 测试 19 端口
        ports = list(range(7891, 7910))

        checker = create_proxy_health_checker(
            proxy_ports=ports,
            proxy_host="172.25.16.1",  # WSL2 主机
            check_interval=30,
        )

        # 执行一次检查
        results = await checker.check_all_ports()


        for _port, result in sorted(results.items()):
            if result.ip_address:
                pass
            if result.error:
                pass


        checker.get_status_summary()

    asyncio.run(test())
