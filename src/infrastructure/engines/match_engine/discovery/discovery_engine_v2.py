#!/usr/bin/env python3
"""
Unified Discovery Engine - V1.1.0 [Genesis.L1Evolution]
=========================================================

继承 BaseHarvestEngine 的统一发现引擎，提供标准化的收割接口，
内部使用 DynamicDiscoveryEngine 实现双模降级架构。

Core Features:
- 继承 BaseHarvestEngine 统一接口
- 双模降级: API → DOM → Cross-Platform
- NetworkShield 集成
- Ghost Protocol 集成
- 配置自愈

Author: [Genesis.L1Evolution]
Version: V1.1.0
Date: 2026-02-03
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..base.base_harvest_engine import (
    BaseHarvestEngine,
    EngineConfig,
    EngineStatistics,
    HarvestResult,
    HarvestStatus
)
from .dynamic_discovery_engine import (
    DynamicDiscoveryEngine,
    DiscoveryConfig,
    DiscoveryResult,
    DiscoveryStatus as DiscoveryStatusV2,
    DiscoveryMode
)

logger = logging.getLogger(__name__)


class UnifiedDiscoveryEngine(BaseHarvestEngine):
    """
    统一发现引擎 - 继承 BaseHarvestEngine 接口

    内部使用 DynamicDiscoveryEngine 实现双模降级架构，
    提供与 Match Engine 兼容的标准化接口。

    使用示例:
        >>> from src.infrastructure.engines.match_engine.discovery import UnifiedDiscoveryEngine
        >>>
        >>> engine = UnifiedDiscoveryEngine()
        >>> await engine.initialize()
        >>>
        >>> # 发现联赛比赛
        >>> result = await engine.discover_league(
        ...     league_id=48,
        ...     league_name="Championship",
        ...     season="2024-2025"
        ... )
        >>>
        >>> # 转换为标准 HarvestResult
        >>> harvest_result = await engine.harvest_league(48, "Championship", "2024-2025")
    """

    def __init__(self, config: EngineConfig | None = None):
        if config is None:
            config = EngineConfig(
                name="UnifiedDiscovery",
                version="1.1.0",
                source="fotmob_discovery",
                enable_network_shield=True,
                timeout_seconds=30,
                max_retries=3
            )
        super().__init__(config)

        # 内部使用 DynamicDiscoveryEngine
        self._dynamic_engine = DynamicDiscoveryEngine()

    async def initialize(self) -> None:
        """初始化引擎"""
        await super().initialize()

        # 初始化内部 DynamicDiscoveryEngine
        await self._dynamic_engine.initialize()

        self.logger.info(
            f"[{self.config.name}] Initialized V{self.config.version} "
            f"with dual-mode discovery capability"
        )

    async def shutdown(self) -> None:
        """关闭引擎"""
        await self._dynamic_engine.shutdown()
        await super().shutdown()

    async def harvest_match(self, match_id: str) -> HarvestResult:
        """
        收割单场比赛数据

        注意: 此方法主要用于与 BaseHarvestEngine 接口兼容。
        对于发现联赛比赛，应使用 discover_league() 方法。

        Args:
            match_id: 比赛 ID

        Returns:
            HarvestResult: 收割结果
        """
        self.logger.debug(f"[{self.config.name}] Harvesting match: {match_id}")

        # 对于单场比赛，我们只返回一个占位结果
        # 实际的数据采集应该使用 FotMobEngine
        return HarvestResult(
            source=self.config.source,
            match_id=match_id,
            status=HarvestStatus.SUCCESS,
            success=True,
            data={"match_id": match_id, "note": "Use FotMobEngine for full data"},
            metadata={"method": "unified_discovery_placeholder"}
        )

    async def discover_league(
        self,
        league_id: int,
        league_name: str,
        season: str = "2024-2025",
        force_dom: bool = False
    ) -> DiscoveryResult:
        """
        发现联赛比赛（直接暴露 DynamicDiscoveryEngine 的接口）

        Args:
            league_id: 联赛 ID
            league_name: 联赛名称
            season: 赛季
            force_dom: 强制使用 DOM 模式

        Returns:
            DiscoveryResult: 发现结果
        """
        return await self._dynamic_engine.discover_league(
            league_id=league_id,
            league_name=league_name,
            season=season,
            force_dom=force_dom
        )

    async def harvest_league(
        self,
        league_id: int,
        league_name: str,
        season: str = "2024-2025"
    ) -> HarvestResult:
        """
        发现联赛比赛（返回标准 HarvestResult 格式）

        此方法提供与 BaseHarvestEngine 兼容的接口，
        将 DiscoveryResult 转换为 HarvestResult。

        Args:
            league_id: 联赛 ID
            league_name: 联赛名称
            season: 赛季

        Returns:
            HarvestResult: 标准收割结果
        """
        discovery_result = await self.discover_league(
            league_id=league_id,
            league_name=league_name,
            season=season
        )

        # 转换状态
        status_mapping = {
            DiscoveryStatusV2.SUCCESS: HarvestStatus.SUCCESS,
            DiscoveryStatusV2.PARTIAL: HarvestStatus.PARTIAL,
            DiscoveryStatusV2.FAILED: HarvestStatus.FAILED,
            DiscoveryStatusV2.RATE_LIMITED: HarvestStatus.RATE_LIMITED,
            DiscoveryStatusV2.DEGRADED: HarvestStatus.SUCCESS,  # 降级但成功
        }

        harvest_status = status_mapping.get(
            discovery_result.status,
            HarvestStatus.FAILED
        )

        # 转换数据
        data = {
            "league_id": league_id,
            "league_name": league_name,
            "season": season,
            "matches": [
                {
                    "match_id": m.match_id,
                    "home_team": m.home_team,
                    "away_team": m.away_team,
                    "source": m.source
                }
                for m in discovery_result.matches
            ]
        }

        return HarvestResult(
            source=self.config.source,
            match_id=f"league_{league_id}",
            status=harvest_status,
            success=(discovery_result.status == DiscoveryStatusV2.SUCCESS),
            data=data,
            errors=discovery_result.errors,
            latency_ms=discovery_result.latency_ms,
            metadata={
                "discovery_mode": discovery_result.mode.value,
                "degraded": discovery_result.degraded,
                **discovery_result.metadata
            }
        )

    async def auto_repair_config(self) -> bool:
        """
        触发配置自愈

        当 API 失败率过高时，自动调用 DynamicDiscoveryEngine 的
        配置自愈功能。

        Returns:
            bool: 是否成功修复配置
        """
        return await self._dynamic_engine.auto_repair_config()


# ============================================================================
# FACTORY FUNCTION
# ============================================================================


def create_unified_discovery_engine(
    league_id: int | None = None,
    league_name: str | None = None
) -> UnifiedDiscoveryEngine:
    """
    工厂函数：创建统一发现引擎

    Args:
        league_id: 默认联赛 ID
        league_name: 默认联赛名称

    Returns:
        UnifiedDiscoveryEngine: 引擎实例
    """
    config = EngineConfig(
        name="UnifiedDiscovery",
        version="1.1.0",
        source="fotmob_discovery",
        enable_network_shield=True
    )

    engine = UnifiedDiscoveryEngine(config)

    # 可以设置默认联赛
    if league_id and league_name:
        engine._dynamic_engine.config = DiscoveryConfig(
            league_id=league_id,
            league_name=league_name
        )

    return engine
