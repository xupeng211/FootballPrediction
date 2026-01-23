#!/usr/bin/env python3
"""V41.610 Proxy Grand Census - 代理池大检阅

对代理池进行深度压力测试，包括：
- 去重和格式校验
- 高并发连通性测试
- 响应速度分级
- 匿名性检查
- 自动黑名单生成

Usage:
    python scripts/ops/v41_610_proxy_census.py [--concurrent 20] [--timeout 15]

Author: V41.610 Proxy Audit Team
Date: 2026-01-22
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import socket
import sys
import time
from argparse import ArgumentParser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp
import requests

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Proxy Quality Tiers
# ============================================================================


@dataclass
class ProxyQuality:
    """代理质量等级"""
    name: str
    max_latency_ms: float
    min_success_rate: float
    color: str


QUALITY_TIERS = {
    "elite": ProxyQuality("精锐", 1000, 0.95, "🟢"),
    "standard": ProxyQuality("步兵", 5000, 0.80, "🟡"),
    "slow": ProxyQuality("伤兵", 10000, 0.50, "🔴"),
    "dead": ProxyQuality("阵亡", float("inf"), 0.0, "⚫"),
}


# ============================================================================
# Proxy Test Result
# ============================================================================


@dataclass
class ProxyTestResult:
    """代理测试结果"""
    proxy: str
    proxy_host: str  # 提取的主机名
    proxy_port: int  # 提取的端口
    proxy_type: str  # http / socks5

    # 连通性测试
    success: bool = False
    response_time_ms: float | None = None
    status_code: int | None = None
    error: str | None = None

    # 匿名性测试
    real_ip_leaked: bool = False
    detected_ip: str | None = None
    anonymous_level: str = "Unknown"  # Elite / Anonymous / Transparent / Unknown

    # 多次测试统计
    attempts: int = 0
    successful_attempts: int = 0
    avg_response_time: float | None = None

    # 质量评级
    quality_tier: str = "unknown"

    def calculate_quality(self) -> str:
        """计算质量等级"""
        if not self.success or self.real_ip_leaked:
            return "dead"

        avg_time = self.avg_response_time or self.response_time_ms or 999999

        if avg_time < QUALITY_TIERS["elite"].max_latency_ms:
            return "elite"
        elif avg_time < QUALITY_TIERS["standard"].max_latency_ms:
            return "standard"
        else:
            return "slow"


# ============================================================================
# Census Report
# ============================================================================


@dataclass
class CensusReport:
    """代理池检阅报告"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # 统计数据
    total_proxies_loaded: int = 0
    unique_proxies: int = 0
    duplicates_removed: int = 0
    format_errors: int = 0

    # 测试结果
    total_tested: int = 0
    elite_count: int = 0
    standard_count: int = 0
    slow_count: int = 0
    dead_count: int = 0

    # 速度统计
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    avg_latency_ms: float | None = None

    # 匿名性统计
    anonymous_elite: int = 0
    anonymous: int = 0
    transparent: int = 0
    leaked: int = 0

    # 详细结果
    results: list[ProxyTestResult] = field(default_factory=list)

    # 推荐配置
    recommended_workers: int = 0
    estimated_harvest_time_hours: float = 0.0


# ============================================================================
# Proxy Census Manager
# ============================================================================


class ProxyCensusManager:
    """V41.610: 代理池检阅管理器"""

    def __init__(
        self,
        proxies_file: str = "config/stealth/proxy_pool.txt",
        target_url: str = "https://www.oddsportal.com",
        ip_check_url: str = "https://api.ipify.org?format=json",
        timeout: int = 15,
        concurrent: int = 20,
    ):
        """初始化检阅管理器

        Args:
            proxies_file: 代理池文件路径
            target_url: 测试目标 URL
            ip_check_url: IP 检查 API
            timeout: 请求超时（秒）
            concurrent: 并发测试数
        """
        self.proxies_file = proxies_file
        self.target_url = target_url
        self.ip_check_url = ip_check_url
        self.timeout = timeout
        self.concurrent = concurrent

        self.report = CensusReport()
        self.proxies: list[str] = []
        self.detected_real_ip: str | None = None

    def load_and_clean_proxies(self) -> list[str]:
        """加载并清理代理池

        执行：
        1. 去除重复
        2. 格式校验
        3. 去除注释和空行

        Returns:
            清理后的代理列表
        """
        logger.info(f"\n{'='*70}")
        logger.info("Step 1: 弹药箱全检查 (Pool Loading & Cleaning)")
        logger.info(f"{'='*70}")

        file_path = Path(self.proxies_file)
        if not file_path.exists():
            logger.error(f"代理文件不存在: {self.proxies_file}")
            return []

        raw_proxies = []
        with open(file_path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # 跳过空行和注释
                if not line or line.startswith("#"):
                    continue

                # 格式校验
                if not self._validate_proxy_format(line):
                    logger.warning(f"格式错误 [行 {line_num}]: {line}")
                    self.report.format_errors += 1
                    continue

                raw_proxies.append(line)

        self.report.total_proxies_loaded = len(raw_proxies)
        logger.info(f"加载代理: {len(raw_proxies)} 条")

        # 去重
        seen = set()
        unique_proxies = []
        duplicates = 0

        for proxy in raw_proxies:
            # 标准化用于比较（转小写）
            normalized = proxy.lower()
            if normalized in seen:
                duplicates += 1
                logger.debug(f"发现重复: {proxy}")
            else:
                seen.add(normalized)
                unique_proxies.append(proxy)

        self.report.duplicates_removed = duplicates
        self.report.unique_proxies = len(unique_proxies)

        logger.info(f"去重后: {len(unique_proxies)} 条")
        logger.info(f"移除重复: {duplicates} 条")
        logger.info(f"格式错误: {self.report.format_errors} 条")

        self.proxies = unique_proxies
        return unique_proxies

    def _validate_proxy_format(self, proxy: str) -> bool:
        """验证代理格式

        Args:
            proxy: 代理字符串

        Returns:
            是否格式正确
        """
        # 基本格式：protocol://host:port
        pattern = r'^(https?|socks5)://[^:]+:\d{1,5}$'
        return bool(re.match(pattern, proxy.strip()))

    async def get_real_ip(self) -> str | None:
        """获取真实 IP（用于匿名性检测）

        Returns:
            真实 IP 地址
        """
        logger.info("\n检测真实 IP（用于匿名性检测）...")

        try:
            # 不使用代理请求
            async with aiohttp.ClientSession() as session:
                async with session.get(self.ip_check_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    self.detected_real_ip = data.get("ip")
                    logger.info(f"真实 IP: {self.detected_real_ip}")
                    return self.detected_real_ip
        except Exception as e:
            logger.warning(f"无法获取真实 IP: {e}")
            return None

    async def test_proxy_anonymity(self, session: aiohttp.ClientSession, proxy: str) -> dict:
        """测试代理匿名性

        Args:
            session: aiohttp 会话
            proxy: 代理 URL

        Returns:
            匿名性测试结果
        """
        result = {
            "detected_ip": None,
            "leaked": False,
            "anonymous_level": "Unknown",
        }

        try:
            # 通过代理检查 IP
            async with session.get(
                self.ip_check_url,
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=10),
                ssl=False
            ) as resp:
                data = await resp.json()
                detected_ip = data.get("ip")
                result["detected_ip"] = detected_ip

                # 检查是否泄露真实 IP
                if self.detected_real_ip and detected_ip == self.detected_real_ip:
                    result["leaked"] = True
                    result["anonymous_level"] = "Transparent"
                elif detected_ip:
                    result["leaked"] = False
                    # 简单判断：如果没有其他头部信息，算是 Anonymous
                    result["anonymous_level"] = "Anonymous"

        except Exception as e:
            logger.debug(f"匿名性测试失败: {e}")

        return result

    async def test_proxy_single(self, session: aiohttp.ClientSession, proxy: str) -> ProxyTestResult:
        """测试单个代理（完整测试）

        Args:
            session: aiohttp 会话
            proxy: 代理 URL

        Returns:
            测试结果
        """
        # 解析代理信息
        parsed = urlparse(proxy)
        proxy_host = parsed.hostname or parsed.hostname or "unknown"
        proxy_port = parsed.port or 0
        proxy_type = parsed.scheme or "http"

        result = ProxyTestResult(
            proxy=proxy,
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_type=proxy_type,
        )

        # 目标网站连通性测试
        start_time = time.time()
        try:
            async with session.get(
                self.target_url,
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                ssl=False
            ) as resp:
                result.response_time_ms = (time.time() - start_time) * 1000
                result.status_code = resp.status

                if resp.status == 200:
                    result.success = True
                    result.successful_attempts = 1
                else:
                    result.error = f"HTTP {resp.status}"

        except asyncio.TimeoutError:
            result.error = "Timeout"
            result.response_time_ms = self.timeout * 1000

        except aiohttp.ClientError as e:
            result.error = str(e)[:100]
            result.response_time_ms = (time.time() - start_time) * 1000

        except Exception as e:
            result.error = f"Unknown: {str(e)[:50]}"

        result.attempts = 1
        result.avg_response_time = result.response_time_ms

        # 匿名性测试（仅对成功的代理）
        if result.success and self.detected_real_ip:
            anonymity = await self.test_proxy_anonymity(session, proxy)
            result.detected_ip = anonymity["detected_ip"]
            result.real_ip_leaked = anonymity["leaked"]
            result.anonymous_level = anonymity["anonymous_level"]

        # 计算质量等级
        result.quality_tier = result.calculate_quality()

        return result

    async def run_census(self) -> CensusReport:
        """运行完整检阅

        Returns:
            检阅报告
        """
        print(f"\n{'='*70}")
        print(f"V41.610 PROXY GRAND CENSUS")
        print(f"{'='*70}")
        print(f"检阅时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"目标网站: {self.target_url}")
        print(f"{'='*70}\n")

        # Step 1: 加载和清理代理
        self.load_and_clean_proxies()

        if not self.proxies:
            logger.error("没有可用的代理进行检阅")
            return self.report

        # Step 2: 获取真实 IP
        await self.get_real_ip()

        # Step 3: 深度压力测试
        logger.info(f"\n{'='*70}")
        logger.info("Step 2: 深度压力测试 (High-Concurrency Stress Test)")
        logger.info(f"{'='*70}")
        logger.info(f"并发数: {self.concurrent}")
        logger.info(f"超时: {self.timeout}s")
        logger.info(f"开始测试...\n")

        # 创建连接池
        connector = aiohttp.TCPConnector(
            limit=self.concurrent,
            limit_per_host=5,
            ttl_dns_cache=300
        )

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 创建测试任务
            tasks = [self.test_proxy_single(session, proxy) for proxy in self.proxies]

            # 并发执行
            results = await asyncio.gather(*tasks)

        self.report.results = results
        self.report.total_tested = len(results)

        # Step 4: 分析结果
        self._analyze_results(results)

        return self.report

    def _analyze_results(self, results: list[ProxyTestResult]):
        """分析测试结果

        Args:
            results: 测试结果列表
        """
        logger.info(f"\n{'='*70}")
        logger.info("Step 3: 优胜劣汰 (Ranking & Filtering)")
        logger.info(f"{'='*70}")

        # 统计各等级数量
        for result in results:
            tier = result.quality_tier
            if tier == "elite":
                self.report.elite_count += 1
            elif tier == "standard":
                self.report.standard_count += 1
            elif tier == "slow":
                self.report.slow_count += 1
            else:
                self.report.dead_count += 1

            # 匿名性统计
            if result.anonymous_level == "Elite":
                self.report.anonymous_elite += 1
            elif result.anonymous_level == "Anonymous":
                self.report.anonymous += 1
            elif result.anonymous_level == "Transparent":
                self.report.transparent += 1

            if result.real_ip_leaked:
                self.report.leaked += 1

        # 计算速度统计
        successful = [r for r in results if r.success and r.response_time_ms]
        if successful:
            latencies = [r.response_time_ms for r in successful]
            self.report.min_latency_ms = min(latencies)
            self.report.max_latency_ms = max(latencies)
            self.report.avg_latency_ms = sum(latencies) / len(latencies)

        # 生成推荐配置
        # 推荐并发数 = 精锐代理数 + 标准代理数的一半
        usable = self.report.elite_count + self.report.standard_count
        self.report.recommended_workers = max(1, min(usable, self.concurrent))

        # 估算收割时间：9,924 场 / (并发数 * 每场 30 秒)
        seconds_per_match = 30  # 保守估计
        total_matches = 9924
        total_seconds = (total_matches / self.report.recommended_workers) * seconds_per_match
        self.report.estimated_harvest_time_hours = total_seconds / 3600

    def print_report(self):
        """打印检阅报告"""
        r = self.report

        print(f"\n{'='*70}")
        print(f"V41.610 PROXY GRAND CENSUS REPORT")
        print(f"{'='*70}")
        print(f"报告时间: {r.timestamp}")
        print(f"\n{'='*70}")
        print(f"📦 Step 1: 弹药箱统计")
        print(f"{'='*70}")
        print(f"  加载总数: {r.total_proxies_loaded}")
        print(f"  去重后:   {r.unique_proxies}")
        print(f"  移除重复: {r.duplicates_removed}")
        print(f"  格式错误: {r.format_errors}")

        print(f"\n{'='*70}")
        print(f"⚔️  Step 2: 战斗力分级")
        print(f"{'='*70}")
        print(f"  🟢 精锐 (<1s):   {r.elite_count:3} 台")
        print(f"  🟡 步兵 (1-5s):  {r.standard_count:3} 台")
        print(f"  🔴 伤兵 (>5s):   {r.slow_count:3} 台")
        print(f"  ⚫ 阵亡:         {r.dead_count:3} 台")
        print(f"  ─────────────────────")
        print(f"  总兵力:         {r.total_tested:3} 台")

        if r.avg_latency_ms:
            print(f"\n{'='*70}")
            print(f"📊 速度统计")
            print(f"{'='*70}")
            print(f"  最快: {r.min_latency_ms:.1f} ms")
            print(f"  最慢: {r.max_latency_ms:.1f} ms")
            print(f"  平均: {r.avg_latency_ms:.1f} ms")

        if r.leaked > 0 or r.transparent > 0:
            print(f"\n{'='*70}")
            print(f"🎭 匿名性检查")
            print(f"{'='*70}")
            print(f"  ✅ 完全匿名: {r.anonymous_elite + r.anonymous}")
            print(f"  ⚠️  透明代理: {r.transparent}")
            print(f"  ❌ IP 泄露: {r.leaked}")

        print(f"\n{'='*70}")
        print(f"🎯 Step 3: 最终建议")
        print(f"{'='*70}")
        print(f"  老板，建议开启: {r.recommended_workers} 线程")
        print(f"  预计收割耗时: {r.estimated_harvest_time_hours:.1f} 小时")
        print(f"  平均每场: {r.estimated_harvest_time_hours * 3600 / 9924:.0f} 秒")

        # 详细结果
        elite_results = [r for r in self.report.results if r.quality_tier == "elite"]
        standard_results = [r for r in self.report.results if r.quality_tier == "standard"]
        dead_results = [r for r in self.report.results if r.quality_tier == "dead"]

        if elite_results:
            print(f"\n{'='*70}")
            print(f"🟢 精锐部队名单")
            print(f"{'='*70}")
            elite_results.sort(key=lambda x: x.response_time_ms or 999999)
            for i, r in enumerate(elite_results, 1):
                print(f"  {i:2}. {r.proxy:40} | {r.response_time_ms:7.1f}ms | IP: {r.detected_ip or 'Unknown'}")

        if standard_results:
            print(f"\n{'='*70}")
            print(f"🟡 步兵部队名单")
            print(f"{'='*70}")
            standard_results.sort(key=lambda x: x.response_time_ms or 999999)
            for i, r in enumerate(standard_results[:10], 1):  # 只显示前 10
                print(f"  {i:2}. {r.proxy:40} | {r.response_time_ms:7.1f}ms")
            if len(standard_results) > 10:
                print(f"     ... 还有 {len(standard_results) - 10} 台")

        if dead_results:
            print(f"\n{'='*70}")
            print(f"⚫ 阵亡名单 (需要淘汰)")
            print(f"{'='*70}")
            for r in dead_results:
                print(f"  - {r.proxy:40} | {r.error}")

        print(f"\n{'='*70}\n")

    def save_blacklist(self, output_file: str = "config/stealth/proxy_blacklist.txt"):
        """生成黑名单文件

        Args:
            output_file: 输出文件路径
        """
        dead_proxies = [r for r in self.report.results if r.quality_tier == "dead"]

        if not dead_proxies:
            logger.info("没有需要淘汰的代理")
            return

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write("# V41.610 Proxy Blacklist - 自动生成\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 淘汰原因: 连接失败/超时/IP 泄露\n")
            f.write("#\n")
            for r in dead_proxies:
                f.write(f"# {r.error}\n")
                f.write(f"{r.proxy}\n")

        logger.info(f"黑名单已生成: {output_file} ({len(dead_proxies)} 个代理)")

    def save_report_json(self, output_file: str | None = None):
        """保存 JSON 报告

        Args:
            output_file: 输出文件路径
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"logs/proxy_census_{timestamp}.json"

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 转换为可序列化格式
        data = {
            "timestamp": self.report.timestamp,
            "summary": {
                "total_proxies_loaded": self.report.total_proxies_loaded,
                "unique_proxies": self.report.unique_proxies,
                "duplicates_removed": self.report.duplicates_removed,
                "format_errors": self.report.format_errors,
                "total_tested": self.report.total_tested,
                "elite_count": self.report.elite_count,
                "standard_count": self.report.standard_count,
                "slow_count": self.report.slow_count,
                "dead_count": self.report.dead_count,
                "min_latency_ms": self.report.min_latency_ms,
                "max_latency_ms": self.report.max_latency_ms,
                "avg_latency_ms": self.report.avg_latency_ms,
                "anonymous_elite": self.report.anonymous_elite,
                "anonymous": self.report.anonymous,
                "transparent": self.report.transparent,
                "leaked": self.report.leaked,
                "recommended_workers": self.report.recommended_workers,
                "estimated_harvest_time_hours": self.report.estimated_harvest_time_hours,
            },
            "results": [
                {
                    "proxy": r.proxy,
                    "proxy_host": r.proxy_host,
                    "proxy_port": r.proxy_port,
                    "proxy_type": r.proxy_type,
                    "success": r.success,
                    "response_time_ms": r.response_time_ms,
                    "status_code": r.status_code,
                    "error": r.error,
                    "real_ip_leaked": r.real_ip_leaked,
                    "detected_ip": r.detected_ip,
                    "anonymous_level": r.anonymous_level,
                    "quality_tier": r.quality_tier,
                }
                for r in self.report.results
            ]
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"报告已保存: {output_file}")


async def main():
    """主函数"""
    parser = ArgumentParser(description="V41.610 Proxy Grand Census")
    parser.add_argument(
        "--proxies",
        type=str,
        default="config/stealth/proxy_pool.txt",
        help="代理池文件路径"
    )
    parser.add_argument(
        "--target",
        type=str,
        default="https://www.oddsportal.com",
        help="测试目标 URL"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="请求超时（秒）"
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=20,
        help="并发测试数量"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="JSON 报告输出路径"
    )

    args = parser.parse_args()

    # 创建检阅管理器
    manager = ProxyCensusManager(
        proxies_file=args.proxies,
        target_url=args.target,
        timeout=args.timeout,
        concurrent=args.concurrent,
    )

    # 运行检阅
    await manager.run_census()

    # 打印报告
    manager.print_report()

    # 保存黑名单
    manager.save_blacklist()

    # 保存 JSON 报告
    manager.save_report_json(args.output)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
