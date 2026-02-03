#!/usr/bin/env python3
"""
Golden Data Merger - V1.0.0 [Genesis.UnifiedEngine]
====================================================

黄金数据缝合器 - L1+L2+L3 数据流统一编排器

Core Features:
- 顺序执行：L1 → L2 → L3 → Features
- 断点续传：检查 matches 表状态，跳过已完成阶段
- 原子操作：任何阶段失败不影响其他阶段的独立性
- NetworkShield 集成：所有网络请求通过统一代理管理

Data Layers:
- L1: Basic match data (match_id, teams, league, date)
- L2: FotMob API data (ratings, shots, possession)
- L3: OddsPortal odds data (opening/closing odds, history)

Author: [Genesis.UnifiedEngine]
Version: V1.0.0
Date: 2026-02-03
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from typing import Any, Dict, List, Optional

# Database imports
import psycopg2
from psycopg2.extensions import connection as pg_connection

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================


class LayerStatus(Enum):
    """数据层状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class LayerResult:
    """单层数据采集结果"""
    layer: str  # L1, L2, L3, Features
    status: LayerStatus
    data: Dict[str, Any] | None = None
    error: str | None = None
    rows_affected: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MergeSummary:
    """完整融合摘要"""
    match_id: str
    l1_result: LayerResult
    l2_result: LayerResult | None = None
    l3_result: LayerResult | None = None
    features_result: LayerResult | None = None
    total_latency_ms: int = 0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None

    @property
    def is_complete_success(self) -> bool:
        """检查是否所有层都成功"""
        results = [self.l1_result]
        if self.l2_result:
            results.append(self.l2_result)
        if self.l3_result:
            results.append(self.l3_result)
        if self.features_result:
            results.append(self.features_result)
        return all(r.status == LayerStatus.COMPLETE for r in results)


# ============================================================================
# GOLDEN DATA MERGER
# ============================================================================


class GoldenDataMerger:
    """
    黄金数据缝合器

    统一管理 L1+L2+L3+Features 的顺序执行，支持断点续传和原子操作。

    Usage:
        >>> merger = GoldenDataMerger()
        >>> summary = await merger.merge_match(
        ...     match_id="12345",
        ...     league_name="Premier League",
        ...     season="2024-2025"
        ... )
        >>> print(f"Success: {summary.is_complete_success}")
    """

    def __init__(
        self,
        db_host: str | None = None,
        db_name: str = "football_db",
        db_user: str | None = None,
        db_password: str | None = None,
        db_port: int = 5432,
        enable_network_shield: bool = True,
    ):
        """初始化 GoldenDataMerger

        Args:
            db_host: 数据库主机
            db_name: 数据库名称（必须为 football_db）
            db_user: 数据库用户
            db_password: 数据库密码
            db_port: 数据库端口
            enable_network_shield: 是否启用 NetworkShield
        """
        # Import settings for database configuration
        try:
            from src.config_unified import get_settings
            settings = get_settings()

            self.db_config = {
                "host": db_host or settings.db_host,
                "dbname": db_name,
                "user": db_user or settings.db_user,
                "password": db_password or (settings.db_password.get_secret_value() if hasattr(settings.db_password, "get_secret_value") else settings.db_password),
                "port": db_port,
            }
        except Exception as e:
            # Fallback to manual configuration
            self.db_config = {
                "host": db_host or self._detect_db_host(),
                "dbname": db_name,
                "user": db_user or "football_user",
                "password": db_password or "change-me-in-production",
                "port": db_port,
            }

        self.enable_network_shield = enable_network_shield
        self._network_guardian = None
        self._conn: pg_connection | None = None

        self.logger = logging.getLogger(f"GoldenMerger")

    def _detect_db_host(self) -> str:
        """智能检测数据库主机"""
        import os

        # Docker 环境检测
        if os.environ.get("DOCKER_ENV") == "true":
            return "db"

        # WSL2 环境检测
        try:
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    return "172.25.16.1"
        except Exception:
            pass

        # 默认本地环境
        return "localhost"

    # ========================================================================
    # DATABASE CONNECTION
    # ========================================================================

    def _get_connection(self) -> pg_connection:
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(**self.db_config)
            self._conn.autocommit = False
        return self._conn

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None

    # ========================================================================
    # LAYER STATUS CHECKING
    # ========================================================================

    def check_l1_status(self, match_id: str) -> LayerStatus:
        """检查 L1 基础数据状态（matches 表）"""
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    CASE
                        WHEN match_id IS NULL THEN 'pending'
                        WHEN home_team IS NOT NULL AND away_team IS NOT NULL
                             AND league_name IS NOT NULL THEN 'complete'
                        ELSE 'pending'
                    END as status
                FROM matches
                WHERE match_id = %s
            """, (match_id,))

            result = cur.fetchone()
            if not result:
                return LayerStatus.PENDING

            status_str = result[0]
            return LayerStatus(status_str)

        finally:
            cur.close()

    def check_l2_status(self, match_id: str) -> LayerStatus:
        """检查 L2 FotMob 数据状态（metrics_multi_source_data 表）"""
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    CASE
                        WHEN COUNT(*) = 0 THEN 'pending'
                        WHEN SUM(CASE WHEN final_h IS NOT NULL THEN 1 ELSE 0 END) > 0
                             THEN 'complete'
                        ELSE 'pending'
                    END as status
                FROM metrics_multi_source_data
                WHERE match_id = %s AND source_name = 'fotmob'
            """, (match_id,))

            result = cur.fetchone()
            if not result:
                return LayerStatus.PENDING

            status_str = result[0]
            return LayerStatus(status_str)

        finally:
            cur.close()

    def check_l3_status(self, match_id: str) -> LayerStatus:
        """检查 L3 OddsPortal 数据状态"""
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    CASE
                        WHEN COUNT(*) = 0 THEN 'pending'
                        WHEN SUM(CASE WHEN init_h IS NOT NULL THEN 1 ELSE 0 END) > 0
                             THEN 'complete'
                        ELSE 'pending'
                    END as status
                FROM metrics_multi_source_data
                WHERE match_id = %s
                  AND source_name IN ('Entity_P', 'Entity_B365', 'Pinacles')
            """, (match_id,))

            result = cur.fetchone()
            if not result:
                return LayerStatus.PENDING

            status_str = result[0]
            return LayerStatus(status_str)

        finally:
            cur.close()

    def check_features_status(self, match_id: str) -> LayerStatus:
        """检查特征工程状态"""
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    CASE
                        WHEN COUNT(*) = 0 THEN 'pending'
                        WHEN feature_vector IS NOT NULL THEN 'complete'
                        ELSE 'pending'
                    END as status
                FROM match_features
                WHERE match_id = %s
            """, (match_id,))

            result = cur.fetchone()
            if not result:
                return LayerStatus.PENDING

            status_str = result[0]
            return LayerStatus(status_str)

        finally:
            cur.close()

    # ========================================================================
    # LAYER EXECUTION
    # ========================================================================

    async def execute_l1(
        self,
        match_id: str,
        league_name: str | None = None,
        season: str | None = None,
        team_names: tuple[str, str] | None = None,
    ) -> LayerResult:
        """执行 L1 基础数据采集

        Args:
            match_id: 比赛 ID
            league_name: 联赛名称
            season: 赛季
            team_names: (主队, 客队) 元组

        Returns:
            LayerResult: L1 层结果
        """
        self.logger.info(f"[L1] Starting basic match data collection: {match_id}")

        try:
            conn = self._get_connection()
            cur = conn.cursor()

            # 检查是否已存在
            cur.execute("SELECT match_id FROM matches WHERE match_id = %s", (match_id,))
            if cur.fetchone():
                self.logger.info(f"[L1] Match already exists: {match_id}")
                return LayerResult(
                    layer="L1",
                    status=LayerStatus.COMPLETE,
                    data={"match_id": match_id},
                    rows_affected=0,
                )

            # 插入基础数据
            insert_query = """
                INSERT INTO matches (match_id, league_name, season, home_team, away_team, match_date)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (match_id) DO NOTHING
            """

            home_team, away_team = team_names or ("Unknown", "Unknown")

            cur.execute(
                insert_query,
                (match_id, league_name or "Unknown", season or "2024-2025", home_team, away_team)
            )
            conn.commit()

            rows_affected = cur.rowcount
            cur.close()

            self.logger.info(f"[L1] Complete: {match_id} ({rows_affected} rows)")

            return LayerResult(
                layer="L1",
                status=LayerStatus.COMPLETE,
                data={"match_id": match_id, "league": league_name, "season": season},
                rows_affected=rows_affected,
            )

        except Exception as e:
            self.logger.error(f"[L1] Failed: {e}")
            return LayerResult(
                layer="L1",
                status=LayerStatus.FAILED,
                error=str(e),
            )

    async def execute_l2(
        self,
        match_id: str,
        force: bool = False,
    ) -> LayerResult:
        """执行 L2 FotMob 数据采集

        Args:
            match_id: 比赛 ID
            force: 强制重新采集

        Returns:
            LayerResult: L2 层结果
        """
        self.logger.info(f"[L2] Starting FotMob data collection: {match_id}")

        # 检查状态
        if not force and self.check_l2_status(match_id) == LayerStatus.COMPLETE:
            self.logger.info(f"[L2] Already complete: {match_id}")
            return LayerResult(
                layer="L2",
                status=LayerStatus.COMPLETE,
                data={"match_id": match_id},
            )

        try:
            # 动态导入 FotMobEngine
            from src.infrastructure.engines.match_engine.fotmob import (
                FotMobEngine,
                FotMobEngineConfig,
            )

            # 使用 from_settings() 加载配置（包含 base_url）
            config = FotMobEngineConfig.from_settings()
            config.enable_network_shield = self.enable_network_shield

            engine = FotMobEngine(config)
            await engine.initialize()

            result = await engine.harvest_match(match_id)

            await engine.shutdown()

            if result.success:
                self.logger.info(f"[L2] Complete: {match_id}")
                return LayerResult(
                    layer="L2",
                    status=LayerStatus.COMPLETE,
                    data=result.data,
                    rows_affected=1,
                )
            else:
                self.logger.warning(f"[L2] Partial/Failed: {match_id} - {result.errors}")
                return LayerResult(
                    layer="L2",
                    status=LayerStatus.PARTIAL if result.data else LayerStatus.FAILED,
                    data=result.data,
                    error="; ".join(result.errors) if result.errors else "Unknown error",
                )

        except Exception as e:
            self.logger.error(f"[L2] Failed: {e}")
            return LayerResult(
                layer="L2",
                status=LayerStatus.FAILED,
                error=str(e),
            )

    async def execute_l3(
        self,
        match_id: str,
        force: bool = False,
    ) -> LayerResult:
        """执行 L3 OddsPortal 数据采集

        Args:
            match_id: 比赛 ID
            force: 强制重新采集

        Returns:
            LayerResult: L3 层结果
        """
        self.logger.info(f"[L3] Starting OddsPortal data collection: {match_id}")

        # 检查状态
        if not force and self.check_l3_status(match_id) == LayerStatus.COMPLETE:
            self.logger.info(f"[L3] Already complete: {match_id}")
            return LayerResult(
                layer="L3",
                status=LayerStatus.COMPLETE,
                data={"match_id": match_id},
            )

        try:
            # 动态导入 OddsPortal engine
            from src.infrastructure.engines.match_engine.base import EngineConfig

            # TODO: [Genesis.SmokeTest] Create OddsPortalEngine
            # For now, skip L3 collection and return a placeholder result
            self.logger.warning(f"[L3] OddsPortalEngine not implemented yet, skipping: {match_id}")
            return LayerResult(
                layer="L3",
                status=LayerStatus.PENDING,
                data=None,
                error="OddsPortalEngine not yet implemented - use --skip-l3 or QuantHarvester.js",
            )

        except Exception as e:
            self.logger.error(f"[L3] Failed: {e}")
            return LayerResult(
                layer="L3",
                status=LayerStatus.FAILED,
                error=str(e),
            )

    # ========================================================================
    # MAIN MERGE METHOD
    # ========================================================================

    async def merge_match(
        self,
        match_id: str,
        league_name: str | None = None,
        season: str | None = None,
        team_names: tuple[str, str] | None = None,
        force: bool = False,
        skip_l2: bool = False,
        skip_l3: bool = False,
    ) -> MergeSummary:
        """
        融合单场比赛的完整数据流

        执行顺序：L1 → L2 → L3 → Features
        支持断点续传：自动跳过已完成的阶段

        Args:
            match_id: 比赛 ID
            league_name: 联赛名称
            season: 赛季 (格式: 2024-2025)
            team_names: (主队, 客队) 元组
            force: 强制重新执行所有阶段
            skip_l2: 跳过 L2 采集
            skip_l3: 跳过 L3 采集

        Returns:
            MergeSummary: 完整融合摘要
        """
        import time
        start_time = time.time()

        self.logger.info(f"{'='*60}")
        self.logger.info(f"[GOLDEN MERGER] Starting: {match_id}")
        self.logger.info(f"{'='*60}")

        # NetworkShield 初始化
        if self.enable_network_shield:
            try:
                from src.infrastructure.engines.match_engine.shared import NetworkGuardian

                self._network_guardian = NetworkGuardian(
                    proxy_host="172.25.16.1",
                    log_level="info"
                )
                await self._network_guardian.initialize()

                status = self._network_guardian.get_status()
                self.logger.info(
                    f"[NetworkShield] Initialized: "
                    f"{status.get('nodes', {}).get('active', 0)}/"
                    f"{status.get('nodes', {}).get('total', 0)} nodes available"
                )
            except Exception as e:
                self.logger.warning(f"[NetworkShield] Initialization failed: {e}")

        # 执行 L1
        l1_result = await self.execute_l1(
            match_id=match_id,
            league_name=league_name,
            season=season,
            team_names=team_names,
        )

        if l1_result.status == LayerStatus.FAILED:
            self.logger.error(f"[GOLDEN MERGER] L1 failed, aborting: {match_id}")
            return MergeSummary(match_id=match_id, l1_result=l1_result)

        # 执行 L2
        l2_result = None
        if not skip_l2:
            if force or self.check_l2_status(match_id) != LayerStatus.COMPLETE:
                l2_result = await self.execute_l2(match_id, force=force)

        # 执行 L3
        l3_result = None
        if not skip_l3:
            if force or self.check_l3_status(match_id) != LayerStatus.COMPLETE:
                l3_result = await self.execute_l3(match_id, force=force)

        # 计算总延迟
        total_latency_ms = int((time.time() - start_time) * 1000)

        summary = MergeSummary(
            match_id=match_id,
            l1_result=l1_result,
            l2_result=l2_result,
            l3_result=l3_result,
            total_latency_ms=total_latency_ms,
            completed_at=datetime.now().isoformat(),
        )

        self.logger.info(f"{'='*60}")
        self.logger.info(f"[GOLDEN MERGER] Complete: {match_id}")
        self.logger.info(f"  L1: {l1_result.status.value}")
        if l2_result:
            self.logger.info(f"  L2: {l2_result.status.value}")
        if l3_result:
            self.logger.info(f"  L3: {l3_result.status.value}")
        self.logger.info(f"  Total Latency: {total_latency_ms}ms")
        self.logger.info(f"  Success: {summary.is_complete_success}")
        self.logger.info(f"{'='*60}")

        return summary

    async def merge_batch(
        self,
        match_ids: List[str],
        force: bool = False,
        skip_l2: bool = False,
        skip_l3: bool = False,
        concurrency: int = 3,
    ) -> List[MergeSummary]:
        """
        批量融合多场比赛数据

        Args:
            match_ids: 比赛 ID 列表
            force: 强制重新执行所有阶段
            skip_l2: 跳过 L2 采集
            skip_l3: 跳过 L3 采集
            concurrency: 并发数

        Returns:
            List[MergeSummary]: 融合摘要列表
        """
        self.logger.info(f"[GOLDEN MERGER] Batch mode: {len(match_ids)} matches, concurrency={concurrency}")

        semaphore = asyncio.Semaphore(concurrency)

        async def merge_with_semaphore(match_id: str) -> MergeSummary:
            async with semaphore:
                return await self.merge_match(match_id, force=force, skip_l2=skip_l2, skip_l3=skip_l3)

        tasks = [merge_with_semaphore(mid) for mid in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        summaries = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                summaries.append(MergeSummary(
                    match_id=match_ids[i],
                    l1_result=LayerResult(layer="L1", status=LayerStatus.FAILED, error=str(result))
                ))
            else:
                summaries.append(result)

        return summaries

    def __del__(self):
        """析构函数 - 确保数据库连接关闭"""
        self.close()
