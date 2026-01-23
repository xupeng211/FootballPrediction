#!/usr/bin/env python3
"""V41.590 Stealth Odds Extractor - 隐形赔率收割者

This module integrates all stealth capabilities for evading IP bans
during odds collection from OddsPortal and other sources.

Key Features:
    - Proxy rotation with 20+ pool support
    - Browser fingerprint randomization (Chrome/Edge/Safari/Firefox)
    - Human-like behavior simulation (mouse jitter, random waits)
    - Self-healing on IP bans (automatic proxy rotation)
    - Exponential backoff retry strategy

Author: V41.590 Stealth Team
Date: 2026-01-21
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from playwright.async_api import Page
from playwright.async_api import async_playwright

from src.api.collectors.odds_production_extractor import OddsProductionExtractor
from src.core.behavior_simulator import (
    HumanBehaviorSimulator,
    get_behavior_simulator,
    stealth_wait,
)
from src.core.fingerprint_manager import (
    BrowserFingerprint,
    FingerprintManager,
    get_fingerprint_manager,
)
from src.core.proxy_manager import ProxyConfig, ProxyManager, get_proxy_manager
from src.core.self_healing import (
    SelfHealingEngine,
    get_self_healing_engine,
)

logger = logging.getLogger(__name__)


class StealthOddsExtractor(OddsProductionExtractor):
    """V41.590: 隐形赔率收割者

    继承自 OddsProductionExtractor，集成所有隐形能力。

    特性:
    - 代理池自动轮换 (20+ proxies)
    - 浏览器指纹随机化
    - 人机交互模拟
    - IP 封禁自愈机制

    Example:
        >>> extractor = StealthOddsExtractor(proxies_file="config/stealth/proxy_pool.txt")
        >>> result = await extractor.extract_match_odds("http://oddsportal.com/...")
    """

    def __init__(
        self,
        proxies_file: str | None = "config/stealth/proxy_pool.txt",
        enable_fingerprint: bool = True,
        enable_behavior_sim: bool = True,
        enable_self_healing: bool = True,
    ):
        """初始化隐形收割者

        Args:
            proxies_file: 代理池文件路径
            enable_fingerprint: 是否启用指纹随机化
            enable_behavior_sim: 是否启用行为模拟
            enable_self_healing: 是否启用自愈机制
        """
        # 初始化父类
        super().__init__()

        # 初始化代理管理器
        self.proxy_manager = get_proxy_manager(proxies_file=proxies_file)
        stats = self.proxy_manager.get_stats()
        logger.info(
            f"[StealthExtractor] 代理池初始化: {stats['total_proxies']} 个代理, "
            f"{stats['available_proxies']} 个可用"
        )

        # 初始化指纹管理器
        self.fingerprint_manager = get_fingerprint_manager() if enable_fingerprint else None
        self.enable_fingerprint = enable_fingerprint

        # 初始化行为模拟器
        self.behavior_simulator = get_behavior_simulator() if enable_behavior_sim else None
        self.enable_behavior_sim = enable_behavior_sim

        # 初始化自愈引擎
        self.self_healing_engine = get_self_healing_engine(
            proxy_manager=self.proxy_manager
        ) if enable_self_healing else None
        self.enable_self_healing = enable_self_healing

        # 当前使用的代理
        self._current_proxy: str | None = None

        # 随机种子（每次启动都不同）
        random.seed()

    async def _create_stealth_context(self, playwright_context):
        """创建隐形浏览器上下文

        应用随机指纹和人机交互配置。
        """
        if not self.enable_fingerprint:
            return

        # 生成随机指纹
        fingerprint = self.fingerprint_manager.generate_random_fingerprint()

        # 应用指纹配置
        context_config = fingerprint.to_playwright_context()

        # 添加代理
        if self._current_proxy:
            context_config["proxy"] = {
                "server": self._current_proxy,
            }

        logger.debug(
            f"[StealthExtractor] 应用指纹: "
            f"{fingerprint.user_agent[:50]}... | "
            f"Viewport: {fingerprint.viewport_width}x{fingerprint.viewport_height}"
        )

        return context_config

    async def _simulate_human_behavior(self, page: Page) -> None:
        """模拟人类浏览行为

        Args:
            page: Playwright Page 对象
        """
        if not self.enable_behavior_sim:
            return

        # 随机等待（页面加载后）
        await self.behavior_simulator.random_wait("short", 0.8, 1.5)

        # 偶尔进行微小的页面滚动
        if random.random() > 0.7:  # 30% 概率
            await self.behavior_simulator.natural_scroll(page, "down", distance=random.randint(50, 150))

        logger.debug("[StealthExtractor] 人机交互模拟完成")

    async def _setup_proxy_rotation(self) -> str | None:
        """设置代理轮换

        Returns:
            当前使用的代理 URL
        """
        # 获取新代理
        new_proxy = self.proxy_manager.get_proxy()

        if not new_proxy:
            logger.warning("[StealthExtractor] 没有可用代理！")
            return None

        self._current_proxy = new_proxy
        logger.info(f"[StealthExtractor] 切换代理: {new_proxy}")

        return new_proxy

    async def extract_match_odds(self, match_url: str, **kwargs) -> dict[str, Any]:
        """隐形提取比赛赔率

        Args:
            match_url: 比赛 URL
            **kwargs: 额外参数

        Returns:
            提取结果字典
        """
        # 设置代理
        await self._setup_proxy_rotation()

        # 如果启用自愈，使用自愈引擎执行
        if self.enable_self_healing and self.self_healing_engine:
            async def _extract_operation():
                # 模拟人类行为
                if self.enable_behavior_sim:
                    await stealth_wait("short", 0.8, 1.5)

                # 调用父类的提取方法（需要集成到 async context）
                # 这里需要重构父类以支持 async context injection
                return await super().extract_match_odds(match_url, **kwargs)

            try:
                result = await self.self_healing_engine.execute_with_healing(
                    page=None,  # 需要从 context 中获取
                    operation=_extract_operation,
                    operation_name=f"extract_odds_{match_url}",
                )

                # 标记代理成功
                if self._current_proxy:
                    self.proxy_manager.mark_success(self._current_proxy)

                return result

            except Exception as e:
                # 标记代理失败
                if self._current_proxy:
                    self.proxy_manager.mark_failure(self._current_proxy)

                # 切换到新代理
                await self._setup_proxy_rotation()

                raise

        else:
            # 不启用自愈，直接调用父类方法
            return await super().extract_match_odds(match_url, **kwargs)

    def get_proxy_stats(self) -> dict[str, Any]:
        """获取代理池统计信息

        Returns:
            代理池统计字典
        """
        return self.proxy_manager.get_stats()


# ============================================================================
# Convenience Functions
# ============================================================================


def get_stealth_extractor(
    proxies_file: str = "config/stealth/proxy_pool.txt",
    **kwargs
) -> StealthOddsExtractor:
    """获取隐形收割者单例

    Args:
        proxies_file: 代理池文件路径
        **kwargs: 其他参数

    Returns:
        StealthOddsExtractor 实例
    """
    return StealthOddsExtractor(proxies_file=proxies_file, **kwargs)


# ============================================================================
# CLI Interface
# ============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python stealth_odds_extractor.py <match_url>")
        sys.exit(1)

    match_url = sys.argv[1]

    async def main():
        extractor = get_stealth_extractor()

        # 显示代理池状态
        stats = extractor.get_proxy_stats()
        print(f"\n{'='*60}")
        print(f"V41.590 Stealth Odds Extractor")
        print(f"{'='*60}")
        print(f"代理池状态:")
        print(f"  总代理数: {stats['total_proxies']}")
        print(f"  可用代理: {stats['available_proxies']}")
        print(f"  被封代理: {stats['banned_proxies']}")
        print(f"  轮换策略: {stats['rotation_strategy']}")
        print(f"{'='*60}\n")

        # 执行提取
        result = await extractor.extract_match_odds(match_url)
        print(f"\n提取结果: {result}")

        # 最终统计
        final_stats = extractor.get_proxy_stats()
        print(f"\n最终代理池状态:")
        print(f"  可用代理: {final_stats['available_proxies']}")
        print(f"  总失败次数: {final_stats['total_failures']}")

    asyncio.run(main())
