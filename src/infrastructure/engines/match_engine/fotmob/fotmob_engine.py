#!/usr/bin/env python3
"""
FotMob Engine - V145.0 [Genesis.UnifiedEngine]
==================================================

FotMob L2 数据收割引擎 - 继承 BaseHarvestEngine 并接入 NetworkShield。

迁移自 src/collectors/fotmob_core.py (V144.5)

Core Features:
- 继承 BaseHarvestEngine 统一接口
- NetworkShield 代理管理（替代 ProxyManager）
- UnifiedCircuitBreaker 熔断保护
- Ghost Protocol 反检测（保留 BaseExtractor 能力）
- 自适应解码（Gzip/Brotli/JSON）
- 联赛分级哨兵
- 断点续传和容错解析

与 Node.js QuantHarvester 的状态同步:
- 失败自动上报到 active_registry.json
- Node.js 端能即时感知 IP 劣化
- 跨语言故障恢复

Author: [Genesis.UnifiedEngine]
Version: V145.0
Date: 2026-02-03
Migration: From src/collectors/fotmob_core.py V144.5
"""

from __future__ import annotations

from datetime import datetime
import gzip
import json
import logging
from pathlib import Path
import random

# 导入原有组件（保持向后兼容）
# 注意：BaseExtractor 在 src/collectors/base_extractor.py
import sys
from typing import Any, Dict, List, Optional

import brotli
import requests

# 导入新的基础设施
from ..base.base_harvest_engine import (
    BaseHarvestEngine,
    EngineConfig,
    EngineStatistics,
    HarvestError,
    HarvestResult,
    HarvestStatus,
)
from ..shared.circuit_breaker import (
    CircuitBreakerConfig,
    UnifiedCircuitBreaker,
    get_circuit_breaker,
)
from ..shared.network_guardian import NetworkGuardian

_project_root = Path(__file__).parent.parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.collectors.base_extractor import BaseExtractor
from src.config_unified import get_settings

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


class FotMobEngineConfig(EngineConfig):
    """FotMob 引擎配置"""

    def __init__(self):
        super().__init__(
            name="FotMobEngine",
            version="145.0",
            source="fotmob",
            enabled=True,
            max_retries=3,
            timeout_seconds=30,
            rate_limit_delay=2000,
            enable_network_shield=True,
            session_timeout_minutes=30
        )

        # FotMob 特定配置
        self.base_url = None  # 从 settings 加载
        self.web_url = None

        # 哨兵配置
        self.min_response_size = 20480  # 20KB 最低标准
        self.max_consecutive_failures = 50
        self.circuit_breaker_timeout = 60

        # Ghost Protocol 配置
        self.enable_ghost_protocol = True

    @classmethod
    def from_settings(cls) -> 'FotMobEngineConfig':
        """从配置系统加载"""
        settings = get_settings()
        config = cls()
        config.base_url = settings.fotmob_base_url
        config.web_url = settings.fotmob_web_url
        return config


# ============================================================================
# FOTMOB ENGINE
# ============================================================================


class FotMobEngine(BaseHarvestEngine):
    """
    FotMob L2 数据收割引擎 - V145.0

    迁移说明:
    - 继承 BaseHarvestEngine (统一接口)
    - 使用 NetworkGuardian 替代 ProxyManager
    - 使用 UnifiedCircuitBreaker 替代独立熔断器
    - 保留 BaseExtractor Ghost Protocol 反检测能力

    使用示例:
        >>> engine = FotMobEngine()
        >>> await engine.initialize()
        >>>
        >>> # 收割单场比赛
        >>> result = await engine.harvest_match(12345678)
        >>> print(f"Success: {result.success}, Data: {result.data}")
        >>>
        >>> # 批量收割
        >>> results = await engine.harvest_batch([12345678, 12345679])
        >>>
        >>> # 关闭引擎
        >>> await engine.shutdown()
    """

    # FotMob API 端点
    API_MATCH_DETAILS = "/api/matches/{match_id}"  # 比赛详情
    API_TEAM_MATCHES = "/api/teams/{team_id}/matches"  # 球队比赛

    # 联赛质量等级配置（保留原逻辑）
    LEAGUE_QUALITY_TIERS = {
        "tier_1_premium": {
            "name": "Tier 1 Premium",
            "min_response_size": 102400,  # 100KB
            "leagues": [47, 87, 94, 118, 126, 53]
        },
        "tier_2_standard": {
            "name": "Tier 2 Standard",
            "min_response_size": 51200,  # 50KB
            "leagues": [48, 78, 95, 129, 155]
        },
        "tier_default": {
            "name": "Default Tier",
            "min_response_size": 20480,  # 20KB
            "leagues": []
        }
    }

    def __init__(self, config: Optional[FotMobEngineConfig] = None):
        """
        初始化 FotMob 引擎

        Args:
            config: 引擎配置（可选，使用默认配置如果为 None）
        """
        if config is None:
            config = FotMobEngineConfig.from_settings()

        super().__init__(config)

        # FotMob 特定属性
        self.api_config = None
        self.league_ids = []
        self.season_mapping = {}

        # Ghost Protocol (BaseExtractor)
        self.base_extractor = None

        # 熔断器（引擎级别）
        self._circuit_breaker: Optional[UnifiedCircuitBreaker] = None

        # HTTP 会话
        self._session: Optional[requests.Session] = None

        # 统计信息
        self.consecutive_failures = 0

        self.logger.info(f"[FotMobEngine] V{config.version} initialized")

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    async def initialize(self) -> None:
        """
        初始化引擎

        1. 调用父类初始化（启用 NetworkShield）
        2. 加载 FotMob 配置
        3. 初始化 BaseExtractor（Ghost Protocol）
        4. 初始化熔断器
        5. 创建 HTTP 会话
        """
        # 父类初始化（启用 NetworkShield）
        await super().initialize()

        # 加载 FotMob 配置
        settings = get_settings()
        self.api_config = settings.fotmob_api
        self.league_ids = self.api_config.LEAGUE_IDS
        self.season_mapping = self.api_config.SEASON_MAPPING

        # 初始化 BaseExtractor（Ghost Protocol）
        if self.config.enable_ghost_protocol:
            self.base_extractor = BaseExtractor()
            self.logger.info("[FotMobEngine] Ghost Protocol enabled")

        # 初始化熔断器（与 NetworkGuardian 集成）
        breaker_config = CircuitBreakerConfig(
            failure_threshold=2,  # 与 NetworkShield 一致
            cooldown_minutes=15,
            enable_network_shield_integration=True
        )

        self._circuit_breaker = UnifiedCircuitBreaker(
            name="fotmob_engine",
            network_guardian=self._network_guardian,
            config=breaker_config
        )

        # 创建 HTTP 会话
        self._session = requests.Session()
        self._refresh_headers()

        self.logger.info(
            f"[FotMobEngine] Fully initialized: "
            f"{len(self.league_ids)} leagues, "
            f"NetworkShield {'enabled' if self._network_guardian else 'disabled'}, "
            f"CircuitBreaker ready"
        )

    async def shutdown(self) -> None:
        """关闭引擎"""
        if self._session:
            self._session.close()
            self._session = None

        # 释放所有会话
        await super().shutdown()

        self.logger.info("[FotMobEngine] Shutdown complete")

    # ========================================================================
    # CORE HARVEST METHODS
    # ========================================================================

    async def harvest_match(self, match_id: int | str) -> HarvestResult:
        """
        收割单场比赛数据

        流程:
        1. 检查熔断器状态
        2. 获取代理（NetworkShield Session 绑定）
        3. 发起请求（带重试）
        4. 验证响应质量
        5. 解码数据（Gzip/Brotli/JSON）
        6. 上报状态到 NetworkShield
        7. 返回 HarvestResult

        Args:
            match_id: 比赛 ID

        Returns:
            HarvestResult: 收割结果
        """
        match_id_str = str(match_id)
        start_time = datetime.now()

        self.logger.info(f"[FotMobEngine] Harvesting match {match_id_str}...")

        # 获取代理（Session 绑定）
        proxy = await self._get_proxy_for_session(match_id_str)
        proxy_port = proxy["port"]
        proxy_url = proxy["url"]

        try:
            # 通过熔断器执行收割
            data = await self._circuit_breaker.call(
                self._fetch_match_data,
                match_id_str,
                proxy_port,
                proxy_url
            )

            # 计算延迟
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 上报成功
            await self._report_success(proxy_port, latency_ms)

            # 更新统计
            self.consecutive_failures = 0

            # 返回结果
            return HarvestResult(
                source=self.config.source,
                match_id=match_id_str,
                status=HarvestStatus.SUCCESS,
                success=True,
                data=data,
                latency_ms=latency_ms,
                proxy_port=proxy_port,
                metadata={
                    "engine_version": self.config.version,
                    "fetched_via": "NetworkShield",
                    "data_size": len(json.dumps(data)) if data else 0
                }
            )

        except Exception as e:
            # 上报失败
            await self._report_failure(proxy_port, str(e))

            # 更新统计
            self.consecutive_failures += 1

            # 返回失败结果
            return HarvestResult(
                source=self.config.source,
                match_id=match_id_str,
                status=HarvestStatus.FAILED,
                success=False,
                data=None,
                errors=[str(e)],
                proxy_port=proxy_port,
                metadata={
                    "consecutive_failures": self.consecutive_failures,
                    "last_error": str(e)
                }
            )

    async def harvest_batch(self, match_ids: List[int | str]) -> List[HarvestResult]:
        """
        批量收割比赛数据

        Args:
            match_ids: 比赛 ID 列表

        Returns:
            List[HarvestResult]: 收割结果列表
        """
        self.logger.info(f"[FotMobEngine] Batch harvesting {len(match_ids)} matches...")

        # 使用父类的批量收割方法（并发执行）
        results = await super().harvest_batch(match_ids)

        # 统计
        success_count = sum(1 for r in results if r.success)
        self.logger.info(
            f"[FotMobEngine] Batch harvest complete: "
            f"{success_count}/{len(match_ids)} successful"
        )

        return results

    # ========================================================================
    # DATA FETCHING (Protected methods)
    # ========================================================================

    async def _fetch_match_data(
        self,
        match_id: str,
        proxy_port: int,
        proxy_url: str
    ) -> Dict[str, Any]:
        """
        获取比赛数据（内部方法，供熔断器调用）

        Args:
            match_id: 比赛 ID
            proxy_port: 代理端口
            proxy_url: 代理 URL

        Returns:
            Dict: 解析后的比赛数据

        Raises:
            requests.RequestException: 请求失败
            ValueError: 数据解析失败
        """
        # 构建 URL
        url = f"{self.config.base_url}{self.API_MATCH_DETAILS.format(match_id=match_id)}"

        # 发起请求
        proxies = {"http": proxy_url, "https": proxy_url}

        response = self._session.get(
            url,
            headers=self._get_headers(),
            proxies=proxies,
            timeout=self.config.timeout_seconds
        )

        # 检查 HTTP 状态
        response.raise_for_status()

        # 验证响应大小
        content = response.content
        if not self._validate_response_size(match_id, content):
            raise ValueError(f"Response size validation failed: {len(content)} bytes")

        # 解码数据
        data = self._decode_response(content)

        return data

    def _decode_response(self, content: bytes) -> Dict[str, Any]:
        """
        自适应解码：智能处理 Gzip/Brotli/原始 JSON

        Args:
            content: 响应内容

        Returns:
            Dict: 解析后的数据

        Raises:
            ValueError: 解码失败
        """
        # 尝试 JSON 解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试 Gzip 解压
        try:
            decompressed = gzip.decompress(content)
            return json.loads(decompressed)
        except (OSError, json.JSONDecodeError):
            pass

        # 尝试 Brotli 解压
        try:
            decompressed = brotli.decompress(content)
            return json.loads(decompressed)
        except (brotli.error, json.JSONDecodeError):
            pass

        # 所有方式失败
        raise ValueError("Failed to decode response: tried JSON, Gzip, Brotli")

    def _validate_response_size(self, match_id: str, content: bytes) -> bool:
        """
        验证响应大小（联赛分级哨兵）

        Args:
            match_id: 比赛 ID
            content: 响应内容

        Returns:
            bool: 是否通过验证
        """
        content_size = len(content)

        if content_size < self.config.min_response_size:
            self.logger.warning(
                f"[FotMobEngine] Response too small: {content_size} bytes "
                f"(min: {self.config.min_response_size})"
            )
            return False

        return True

    # ========================================================================
    # HTTP CLIENT
    # ========================================================================

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头（Ghost Protocol）"""
        if self.base_extractor:
            # 使用 BaseExtractor 的随机 UA
            ua = BaseExtractor.get_random_user_agent()
            viewport = BaseExtractor.get_random_viewport()
        else:
            # 默认 UA
            ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            viewport = {"width": 1920, "height": 1080}

        return {
            "User-Agent": ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"{self.config.web_url}/",
            "Origin": self.config.web_url,
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }

    def _refresh_headers(self) -> None:
        """刷新请求头（每次请求更新 UA）"""
        if self._session:
            self._session.headers.update(self._get_headers())


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_fotmob_engine(
    config: Optional[FotMobEngineConfig] = None
) -> FotMobEngine:
    """
    工厂函数：创建 FotMob 引擎

    Args:
        config: 引擎配置（可选）

    Returns:
        FotMobEngine: 引擎实例
    """
    if config is None:
        config = FotMobEngineConfig.from_settings()

    return FotMobEngine(config)


# 便捷函数
async def harvest_fotmob_match(match_id: int | str) -> HarvestResult:
    """
    便捷函数：收割单场比赛

    Args:
        match_id: 比赛 ID

    Returns:
        HarvestResult: 收割结果
    """
    engine = create_fotmob_engine()
    await engine.initialize()

    try:
        result = await engine.harvest_match(match_id)
        return result
    finally:
        await engine.shutdown()
