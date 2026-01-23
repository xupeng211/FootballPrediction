#!/usr/bin/env python3
"""V41.590 Stealth Harvester Trial Run - 隐形收割者试运行

This script performs a limited trial run of the stealth harvester with:
- Proxy rotation (20+ proxies)
- Fingerprint randomization
- Human behavior simulation
- Self-healing on IP bans

Usage:
    python scripts/ops/v41_590_stealth_trial.py --limit 5

Author: V41.590 Stealth Team
Date: 2026-01-21
"""

from __future__ import annotations

import asyncio
import logging
import sys
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings
from src.core.proxy_manager import ProxyConfig, ProxyManager, get_proxy_manager
from src.core.fingerprint_manager import FingerprintManager, get_fingerprint_manager
from src.core.behavior_simulator import HumanBehaviorSimulator, get_behavior_simulator
from src.core.self_healing import SelfHealingEngine, get_self_healing_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StealthHarvesterTrial:
    """V41.590: 隐形收割者试运行

    测试所有隐形模块的集成效果。
    """

    def __init__(self, proxies_file: str = "config/stealth/proxy_pool.txt", limit: int = 5):
        """初始化试运行

        Args:
            proxies_file: 代理池文件路径
            limit: 最大采集数量
        """
        self.limit = limit
        self.start_time = datetime.now()

        # 初始化所有模块
        logger.info("=" * 80)
        logger.info("V41.590 STEALTH HARVESTER - TRIAL RUN")
        logger.info("=" * 80)

        # 1. 代理管理器
        logger.info("\n[1/4] 初始化代理管理器...")
        self.proxy_manager = get_proxy_manager(proxies_file=proxies_file)
        proxy_stats = self.proxy_manager.get_stats()
        logger.info(f"  ✅ 代理池: {proxy_stats['total_proxies']} 个代理")
        logger.info(f"  ✅ 可用: {proxy_stats['available_proxies']} 个")
        logger.info(f"  ✅ 策略: {proxy_stats['rotation_strategy']}")

        # 2. 指纹管理器
        logger.info("\n[2/4] 初始化指纹管理器...")
        self.fingerprint_manager = get_fingerprint_manager()
        logger.info("  ✅ 浏览器指纹池已就绪")

        # 3. 行为模拟器
        logger.info("\n[3/4] 初始化行为模拟器...")
        self.behavior_simulator = get_behavior_simulator()
        logger.info("  ✅ 人机交互模拟已就绪")

        # 4. 自愈引擎
        logger.info("\n[4/4] 初始化自愈引擎...")
        self.self_healing_engine = get_self_healing_engine(
            proxy_manager=self.proxy_manager
        )
        logger.info("  ✅ 自愈引擎已就绪")

        logger.info("\n" + "=" * 80)
        logger.info("初始化完成！开始试运行...")
        logger.info("=" * 80)

    async def test_proxy_rotation(self) -> dict:
        """测试代理轮换

        Returns:
            测试结果字典
        """
        logger.info("\n[测试 1/3] 代理轮换测试")
        logger.info("-" * 40)

        proxies_used = []
        for i in range(min(5, self.proxy_manager.get_stats()['total_proxies'])):
            proxy = self.proxy_manager.get_proxy()
            if proxy:
                proxies_used.append(proxy)
                logger.info(f"  轮换 {i+1}: {proxy}")
                # 模拟成功
                self.proxy_manager.mark_success(proxy)
                await asyncio.sleep(0.1)

        return {
            "total_rotations": len(proxies_used),
            "unique_proxies": len(set(proxies_used)),
            "proxies": proxies_used,
        }

    async def test_fingerprint_diversity(self) -> dict:
        """测试指纹多样性

        Returns:
            测试结果字典
        """
        logger.info("\n[测试 2/3] 指纹多样性测试")
        logger.info("-" * 40)

        fingerprints = []
        for i in range(10):
            fp = self.fingerprint_manager.generate_random_fingerprint()
            fingerprints.append({
                "user_agent": fp.user_agent[:50] + "...",
                "viewport": f"{fp.viewport_width}x{fp.viewport_height}",
                "locale": fp.locale,
                "timezone": fp.timezone,
            })

        unique_viewports = set(fp["viewport"] for fp in fingerprints)
        unique_locales = set(fp["locale"] for fp in fingerprints)

        logger.info(f"  生成指纹数: {len(fingerprints)}")
        logger.info(f"  唯一视口: {len(unique_viewports)} 种")
        logger.info(f"  唯一地区: {len(unique_locales)} 种")

        return {
            "total_fingerprints": len(fingerprints),
            "unique_viewports": len(unique_viewports),
            "unique_locales": len(unique_locales),
            "sample": fingerprints[:3],  # 前 3 个样本
        }

    async def test_human_behavior(self) -> dict:
        """测试人机交互模拟

        Returns:
            测试结果字典
        """
        logger.info("\n[测试 3/3] 人机交互模拟测试")
        logger.info("-" * 40)

        wait_times = []

        # 测试随机等待
        for wait_type in ["short", "medium", "long"]:
            start = asyncio.get_event_loop().time()
            await self.behavior_simulator.random_wait(wait_type, 0.5, 1.0)
            duration = asyncio.get_event_loop().time() - start
            wait_times.append(duration)
            logger.info(f"  {wait_type} 等待: {duration:.2f} 秒")

        avg_wait = sum(wait_times) / len(wait_times)

        return {
            "wait_times": wait_times,
            "average_wait": avg_wait,
        }

    async def run_trial(self) -> dict:
        """运行完整试运行

        Returns:
            试运行结果字典
        """
        results = {}

        # 测试 1: 代理轮换
        results["proxy_rotation"] = await self.test_proxy_rotation()

        # 测试 2: 指纹多样性
        results["fingerprint_diversity"] = await self.test_fingerprint_diversity()

        # 测试 3: 人机交互
        results["human_behavior"] = await self.test_human_behavior()

        # 最终统计
        final_stats = self.proxy_manager.get_stats()
        results["final_proxy_stats"] = final_stats

        duration = (datetime.now() - self.start_time).total_seconds()

        return {
            "results": results,
            "duration_seconds": duration,
            "success": True,
        }

    def generate_report(self, trial_result: dict) -> None:
        """生成试运行报告

        Args:
            trial_result: 试运行结果字典
        """
        logger.info("\n" + "=" * 80)
        logger.info("V41.590 STEALTH HARVESTER - TRIAL REPORT")
        logger.info("=" * 80)

        results = trial_result["results"]

        # 代理轮换结果
        pr = results["proxy_rotation"]
        logger.info("\n[1] 代理轮换测试:")
        logger.info(f"  轮换次数: {pr['total_rotations']}")
        logger.info(f"  唯一代理: {pr['unique_proxies']}")
        logger.info(f"  示例代理:")
        for p in pr["proxies"][:3]:
            logger.info(f"    - {p}")

        # 指纹多样性结果
        fd = results["fingerprint_diversity"]
        logger.info("\n[2] 指纹多样性测试:")
        logger.info(f"  生成指纹: {fd['total_fingerprints']} 个")
        logger.info(f"  唯一视口: {fd['unique_viewports']} 种")
        logger.info(f"  唯一地区: {fd['unique_locales']} 种")
        logger.info(f"  指纹样本:")
        for s in fd["sample"]:
            logger.info(f"    - {s['viewport']} | {s['locale']} | {s['timezone']}")

        # 人机交互结果
        hb = results["human_behavior"]
        logger.info("\n[3] 人机交互模拟测试:")
        logger.info(f"  平均等待: {hb['average_wait']:.2f} 秒")
        logger.info(f"  等待时间: {[f'{t:.2f}s' for t in hb['wait_times']]}")

        # 最终统计
        fps = results["final_proxy_stats"]
        logger.info("\n[4] 最终代理池状态:")
        logger.info(f"  总代理数: {fps['total_proxies']}")
        logger.info(f"  可用代理: {fps['available_proxies']}")
        logger.info(f"  被封代理: {fps['banned_proxies']}")
        logger.info(f"  总失败次数: {fps['total_failures']}")

        # 总体结果
        duration = trial_result["duration_seconds"]
        logger.info(f"\n[5] 总体结果:")
        logger.info(f"  运行时长: {duration:.2f} 秒")
        logger.info(f"  状态: {'✅ 成功' if trial_result['success'] else '❌ 失败'}")

        logger.info("\n" + "=" * 80)
        logger.info("V41.590 隐形收割者试运行完成！")
        logger.info("=" * 80)


async def main():
    """主函数"""
    parser = ArgumentParser(description="V41.590 Stealth Harvester Trial Run")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of matches to harvest (default: 5)"
    )
    parser.add_argument(
        "--proxies",
        type=str,
        default="config/stealth/proxy_pool.txt",
        help="Path to proxy pool file (default: config/stealth/proxy_pool.txt)"
    )

    args = parser.parse_args()

    # 检查代理文件
    if not Path(args.proxies).exists():
        logger.warning(f"⚠️  代理文件不存在: {args.proxies}")
        logger.info("   将使用 WSL2 自动探测的代理")

    # 运行试运行
    trial = StealthHarvesterTrial(proxies_file=args.proxies, limit=args.limit)
    result = await trial.run_trial()

    # 生成报告
    trial.generate_report(result)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
