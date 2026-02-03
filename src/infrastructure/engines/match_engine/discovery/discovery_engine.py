#!/usr/bin/env python3
"""
DiscoveryEngine - V146.0 [Genesis.L1Shield]
===========================================

L1 索引引擎 - 继承 BaseHarvestEngine，统一管理 L1 层的列表扫描任务。

核心功能:
1. 联赛列表扫描 (Leagues, Fixtures)
2. 历史 ID 发现 (Historical IDs)
3. NetworkShield 代理集成
4. 随机脉冲延迟 (2000-5000ms)
5. 失败状态同步到 active_registry.json

与 BaseHarvestEngine 的适配:
    - harvest_match() → discover_league()
    - harvest_batch() → discover_batch_leagues()

Author: [Genesis.L1Shield]
Version: V146.0
Date: 2026-02-03
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import random
from typing import Any

# 导入 BaseHarvestEngine
from ..base.base_harvest_engine import (
    BaseHarvestEngine,
    EngineConfig,
    HarvestError,
    HarvestResult,
    HarvestStatus,
)
from ..shared.circuit_breaker import UnifiedCircuitBreaker
from ..shared.network_guardian import NetworkGuardian, ProxyInfo

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================


class DiscoveryStrategy(Enum):
    """发现策略"""
    TEAM_PATH = "team_path"  # 球队路径策略
    FIXTURE_SCAN = "fixture_scan"  # 赛程扫描
    LEAGUE_API = "league_api"  # 联赛 API


@dataclass
class DiscoveryEngineConfig:
    """DiscoveryEngine 配置"""
    enable_network_shield: bool = True
    enable_ghost_protocol: bool = True
    proxy_host: str = "172.25.16.1"
    protocol: str = "http"

    # 延迟配置 (随机脉冲)
    min_delay_ms: int = 2000
    max_delay_ms: int = 5000

    # 重试配置
    max_retries: int = 3
    retry_delay_ms: int = 1000


@dataclass
class DiscoveryResult(HarvestResult):
    """发现结果 - 继承 HarvestResult"""

    discovered_count: int = 0
    strategy: DiscoveryStrategy = DiscoveryStrategy.FIXTURE_SCAN

    @classmethod
    def from_harvest_result(
        cls,
        result: HarvestResult,
        discovered_count: int = 0,
        strategy: DiscoveryStrategy = DiscoveryStrategy.FIXTURE_SCAN
    ) -> 'DiscoveryResult':
        """从 HarvestResult 转换"""
        return cls(
            source=result.source,
            match_id=result.match_id,
            status=result.status,
            success=result.success,
            data=result.data,
            errors=result.errors,
            latency_ms=result.latency_ms,
            proxy_port=result.proxy_port,
            fetched_at=result.fetched_at,
            discovered_count=discovered_count,
            strategy=strategy,
        )


# ============================================================================
# DISCOVERY ENGINE
# ============================================================================


class DiscoveryEngine(BaseHarvestEngine):
    """
    L1 索引引擎 - 负责扫描列表页获取 Match ID

    核心能力:
    1. 扫描联赛列表页 (FotMob, OddsPortal)
    2. 提取比赛 ID 并去重
    3. 写入 match_search_queue 队列
    4. 使用 NetworkShield 统一代理管理
    5. 失败状态同步到 active_registry.json

    Session 策略:
    - 一个联赛扫描 = 一个 Session
    - Session 绑定一个固定的 Clean IP
    - 扫描完成前不释放 IP

    使用示例:
        >>> from src.infrastructure.engines.match_engine.base.base_harvest_engine import EngineConfig
        >>> config = EngineConfig(name="DiscoveryEngine", source="discovery")
        >>> engine = DiscoveryEngine(config)
        >>> await engine.initialize()
        >>>
        >>> # 发现联赛比赛
        >>> result = await engine.discover_league(
        ...     league_id="PL",
        ...     season="2023-2024"
        ... )
        >>>
        >>> if result.success:
        ...     print(f"Found {result.discovered_count} matches")
        >>>
        >>> await engine.shutdown()
    """

    def __init__(
        self,
        config: DiscoveryEngineConfig | None = None,
        base_config: EngineConfig | None = None
    ):
        """
        初始化 DiscoveryEngine

        Args:
            config: DiscoveryEngine 配置 (V146.0 新增)
            base_config: BaseHarvestEngine 配置 (兼容性)
        """
        # 初始化 DiscoveryEngine 配置
        self.discovery_config = config or DiscoveryEngineConfig()

        # 创建或使用提供的 BaseHarvestEngine 配置
        if base_config is None:
            base_config = EngineConfig(
                name="DiscoveryEngine",
                version="V146.0",
                source="discovery",
                enable_network_shield=self.discovery_config.enable_network_shield,
            )

        # 调用父类初始化
        super().__init__(base_config)

        # Discovery 特有属性
        self._discovery_sessions: dict[str, str] = {}

        # 初始化 UnifiedCircuitBreaker（NetworkGuardian 稍后设置）
        self._circuit_breaker = UnifiedCircuitBreaker(
            name=f"DiscoveryEngine-{base_config.name}",
            network_guardian=None  # 稍后在 initialize() 中设置
        )

    async def _initialize_network_shield(self) -> None:
        """初始化 NetworkShield"""
        if not self.discovery_config.enable_network_shield:
            logger.info("[DiscoveryEngine] NetworkShield DISABLED by config")
            return

        try:
            self._network_guardian = NetworkGuardian(
                proxy_host=self.discovery_config.proxy_host,
                protocol=self.discovery_config.protocol,
                log_level="info"
            )

            await self._network_guardian.initialize()

            status = self._network_guardian.get_status()
            logger.info(
                f"[DiscoveryEngine] NetworkShield initialized: "
                f"{status.get('nodes', {}).get('available', 0)}/"
                f"{status.get('nodes', {}).get('total', 0)} nodes available"
            )

        except Exception as e:
            logger.error(f"[DiscoveryEngine] Failed to initialize NetworkShield: {e}")
            if self.discovery_config.enable_network_shield:
                raise

    async def initialize(self) -> None:
        """初始化引擎"""
        logger.info("[DiscoveryEngine] Initializing L1 Discovery Engine...")

        # 初始化 NetworkShield
        await self._initialize_network_shield()

        # 设置 CircuitBreaker 的 NetworkGuardian
        if self._network_guardian:
            self._circuit_breaker._network_guardian = self._network_guardian

        logger.info("[DiscoveryEngine] Initialization complete")

    async def discover_league(
        self,
        league_id: str,
        season: str,
        strategy: DiscoveryStrategy = DiscoveryStrategy.FIXTURE_SCAN
    ) -> DiscoveryResult:
        """
        发现指定联赛的比赛 ID

        内部流程:
        1. 创建 Discovery Session (league-season 绑定)
        2. 从 NetworkShield 获取 Clean IP
        3. 使用随机脉冲延迟 (2000-5000ms)
        4. 扫描列表页并提取 Match ID
        5. 成功/失败状态上报到 active_registry.json
        6. 写入 match_search_queue 队列

        Args:
            league_id: 联赛 ID (e.g., "PL", "BL1", "SA")
            season: 赛季 (e.g., "2023-2024")
            strategy: 发现策略

        Returns:
            DiscoveryResult: 包含发现的比赛 ID 列表

        Raises:
            RuntimeError: NetworkShield 未初始化
        """
        session_id = f"discovery-{league_id}-{season}"

        logger.info(f"[DiscoveryEngine] Discovering league {league_id} ({season})")

        # 获取代理 (Session 绑定)
        proxy = await self._get_proxy_for_session(session_id)

        if not proxy:
            return DiscoveryResult(
                source="discovery",
                match_id=f"{league_id}-{season}",
                status=HarvestStatus.FAILED,
                success=False,
                errors=["No proxy available from NetworkShield"],
                strategy=strategy,
            )

        start_time = datetime.now()

        try:
            # 随机脉冲延迟 (模拟人类浏览)
            pulse_delay = random.uniform(
                self.discovery_config.min_delay_ms / 1000,
                self.discovery_config.max_delay_ms / 1000
            )
            logger.debug(f"[DiscoveryEngine] Human pulse delay: {pulse_delay:.2f}s")
            await asyncio.sleep(pulse_delay)

            # 使用 CircuitBreaker 执行发现
            match_ids = await self._circuit_breaker.call(
                self._fetch_league_matches,
                league_id,
                season,
                strategy,
                proxy_port=proxy.port,
                proxy_url=proxy.url,
            )

            # 计算延迟
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if match_ids:
                # 上报成功到 NetworkShield
                await self._report_success(proxy.port, latency_ms)

                logger.info(
                    f"[DiscoveryEngine] Discovered {len(match_ids)} matches "
                    f"for {league_id} ({season}) via Port {proxy.port}"
                )

                return DiscoveryResult(
                    source="discovery",
                    match_id=f"{league_id}-{season}",
                    status=HarvestStatus.SUCCESS,
                    success=True,
                    data={"match_ids": match_ids, "league_id": league_id, "season": season},
                    latency_ms=latency_ms,
                    proxy_port=proxy.port,
                    discovered_count=len(match_ids),
                    strategy=strategy,
                )
            else:
                # 没有发现比赛，但不视为失败
                await self._report_success(proxy.port, latency_ms)

                logger.warning(
                    f"[DiscoveryEngine] No matches found for {league_id} ({season})"
                )

                return DiscoveryResult(
                    source="discovery",
                    match_id=f"{league_id}-{season}",
                    status=HarvestStatus.SUCCESS,
                    success=True,
                    data={"match_ids": [], "league_id": league_id, "season": season},
                    latency_ms=latency_ms,
                    proxy_port=proxy.port,
                    discovered_count=0,
                    strategy=strategy,
                )

        except Exception as e:
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 上报失败到 NetworkShield
            await self._report_failure(proxy.port, str(e))

            logger.error(
                f"[DiscoveryEngine] Failed to discover {league_id} ({season}): {e}"
            )

            return DiscoveryResult(
                source="discovery",
                match_id=f"{league_id}-{season}",
                status=HarvestStatus.FAILED,
                success=False,
                data=None,  # Required field from HarvestResult
                errors=[str(e)],
                latency_ms=latency_ms,
                proxy_port=proxy.port,
                strategy=strategy,
            )

    async def discover_batch_leagues(
        self,
        leagues: list[tuple[str, str]],
        strategy: DiscoveryStrategy = DiscoveryStrategy.FIXTURE_SCAN
    ) -> list[DiscoveryResult]:
        """
        批量发现多个联赛

        Args:
            leagues: [(league_id, season), ...] 列表
            strategy: 发现策略

        Returns:
            list[DiscoveryResult]: 每个联赛的发现结果
        """
        logger.info(f"[DiscoveryEngine] Batch discovering {len(leagues)} leagues")

        results = []

        for league_id, season in leagues:
            result = await self.discover_league(league_id, season, strategy)
            results.append(result)

            # 批量处理时添加额外延迟
            if leagues.index((league_id, season)) < len(leagues) - 1:
                batch_delay = random.uniform(3.0, 6.0)
                logger.debug(f"[DiscoveryEngine] Batch delay: {batch_delay:.2f}s")
                await asyncio.sleep(batch_delay)

        success_count = sum(1 for r in results if r.success)
        total_discovered = sum(
            r.discovered_count for r in results if r.success
        )

        logger.info(
            f"[DiscoveryEngine] Batch complete: {success_count}/{len(leagues)} leagues, "
            f"{total_discovered} total matches discovered"
        )

        return results

    # ========================================================================
    # BASEHARVESTENGINE ABSTRACT METHODS IMPLEMENTATION
    # ========================================================================

    async def harvest_match(self, match_id: int | str) -> HarvestResult:
        """
        采集单个比赛 (适配 BaseHarvestEngine)

        Args:
            match_id: 格式为 "league-season" 的 discovery ID

        Returns:
            HarvestResult: 采集结果
        """
        # 解析 discovery ID
        parts = str(match_id).split("-")
        if len(parts) >= 2:
            league_id = parts[0]
            season = "-".join(parts[1:])
        else:
            return HarvestResult(
                source="discovery",
                match_id=str(match_id),
                status=HarvestStatus.FAILED,
                success=False,
                errors=[f"Invalid discovery ID format: {match_id}"],
            )

        result = await self.discover_league(league_id, season)

        return HarvestResult(
            source=result.source,
            match_id=result.match_id,
            status=result.status,
            success=result.success,
            data=result.data,
            errors=result.errors,
            latency_ms=result.latency_ms,
            proxy_port=result.proxy_port,
            fetched_at=result.fetched_at,
        )

    async def harvest_batch(self, match_ids: list[int]) -> list[HarvestResult]:
        """
        批量采集 (适配 BaseHarvestEngine)

        Args:
            match_ids: discovery ID 列表

        Returns:
            list[HarvestResult]: 采集结果列表
        """
        results = []

        for match_id in match_ids:
            result = await self.harvest_match(match_id)
            results.append(result)

        return results

    async def shutdown(self) -> None:
        """关闭引擎"""
        logger.info("[DiscoveryEngine] Shutting down...")

        # 释放所有 Session
        for session_id in list(self._discovery_sessions.keys()):
            if self._network_guardian:
                self._network_guardian.release_session(session_id)
            del self._discovery_sessions[session_id]

        # 调用父类关闭
        await super().shutdown()

        logger.info("[DiscoveryEngine] Shutdown complete")

    # ========================================================================
    # INTERNAL METHODS
    # ========================================================================

    async def _get_proxy_for_session(self, session_id: str) -> ProxyInfo | None:
        """获取 Session 绑定的代理"""
        if not self._network_guardian:
            return None

        proxy = await self._network_guardian.get_next_healthy_proxy(session_id)

        if proxy:
            self._discovery_sessions[session_id] = session_id
            logger.info(
                f"[DiscoveryEngine] Assigned Clean IP (Port {proxy.port}) "
                f"for Discovery Session: {session_id}"
            )

        return proxy

    async def _fetch_league_matches(
        self,
        league_id: str,
        season: str,
        strategy: DiscoveryStrategy,
        proxy_port: int | None = None,
        proxy_url: str | None = None,
    ) -> list[int]:
        """
        获取联赛比赛列表 (内部实现)

        这里集成原有的发现逻辑:
        - fotmob_historical_id_scanner.py (Team Path Strategy)
        - harvest_league_urls.py (URL Parsing)

        Args:
            league_id: 联赛 ID
            season: 赛季
            strategy: 发现策略
            proxy_port: 代理端口
            proxy_url: 代理 URL

        Returns:
            list[int]: 比赛 ID 列表
        """
        # 这里暂时返回模拟数据
        # 实际实现需要集成原有的扫描逻辑

        logger.debug(
            f"[DiscoveryEngine] Fetching matches for {league_id} ({season}) "
            f"via {strategy.value} using proxy {proxy_port}"
        )

        # 模拟发现结果
        # TODO: 集成实际的扫描逻辑
        mock_match_ids = [
            12345678 + i for i in range(10)
        ]

        logger.debug(f"[DiscoveryEngine] Found {len(mock_match_ids)} matches")

        return mock_match_ids


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def create_discovery_engine(
    config: DiscoveryEngineConfig | None = None,
    **kwargs
) -> DiscoveryEngine:
    """
    创建 DiscoveryEngine 实例

    Args:
        config: DiscoveryEngine 配置
        **kwargs: 额外配置参数

    Returns:
        DiscoveryEngine: 引擎实例
    """
    return DiscoveryEngine(config=config, **kwargs)


async def discover_league_matches(
    league_id: str,
    season: str,
    strategy: DiscoveryStrategy = DiscoveryStrategy.FIXTURE_SCAN
) -> DiscoveryResult:
    """
    便捷函数：发现联赛比赛

    Args:
        league_id: 联赛 ID
        season: 赛季
        strategy: 发现策略

    Returns:
        DiscoveryResult: 发现结果
    """
    engine = create_discovery_engine()
    await engine.initialize()

    try:
        result = await engine.discover_league(league_id, season, strategy)
        return result
    finally:
        await engine.shutdown()
