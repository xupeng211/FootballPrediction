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
import json
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
    # V171.000: 多模型预测结果
    prediction_result: Dict[str, Any] | None = None
    # V171.001: 基本面数据
    fundamentals: Dict[str, Any] | None = None
    # V171.001: 异常检测
    anomaly_analysis: Dict[str, Any] | None = None

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

        # V171.001: 采集并写入基本面数据（阵容、伤停、身价）
        fundamentals_harvested = False
        try:
            fundamentals_harvested = await self._harvest_and_save_fundamentals(match_id)
            if fundamentals_harvested:
                self.logger.info(f"[V171.001] Fundamentals harvested and saved for {match_id}")
        except Exception as e:
            self.logger.warning(f"[V171.001] Fundamentals harvest failed: {e}")

        # V171.000: 调用 MultiModelValidator 进行多模型预测
        prediction_result = None
        try:
            from src.ml.inference.multi_model_validator import MultiModelValidator

            validator = MultiModelValidator()
            validation = await validator.validate_match(
                match_id=match_id,
                league_name=league_name
            )
            validator.close()

            prediction_result = {
                "final_prediction": validation.final_prediction,
                "final_confidence": validation.final_confidence,
                "consensus_level": validation.consensus_level.value,
                "agreement_ratio": validation.agreement_ratio,
                "models_count": validation.models_count,
                "voting_breakdown": validation.voting_breakdown,
                "recommended_bet": validation.recommended_bet,
            }

            self.logger.info(
                f"[V171] Multi-Model Prediction: {validation.final_prediction} "
                f"(Confidence: {validation.final_confidence:.1%}, "
                f"Consensus: {validation.consensus_level.value})"
            )

        except Exception as e:
            self.logger.warning(f"[V171] Multi-Model Validation failed: {e}")

        # V171.001: 加载基本面数据
        fundamentals = None
        anomaly_analysis = None

        try:
            fundamentals = await self._load_fundamentals(match_id)
            if fundamentals:
                self.logger.info(f"[V171.001] Fundamentals loaded for {match_id}")

                # V171.001: 执行异常检测
                anomaly_analysis = self._analyze_anomalies(
                    odds_data={"l1": l1_result, "l2": l2_result, "l3": l3_result},
                    fundamentals=fundamentals,
                    prediction=prediction_result
                )

                if anomaly_analysis.get("detected"):
                    self.logger.warning(
                        f"[V171.001] Anomaly detected: {anomaly_analysis.get('type', 'Unknown')}"
                    )
        except Exception as e:
            self.logger.warning(f"[V171.001] Fundamentals loading failed: {e}")

        # 计算总延迟
        total_latency_ms = int((time.time() - start_time) * 1000)

        summary = MergeSummary(
            match_id=match_id,
            l1_result=l1_result,
            l2_result=l2_result,
            l3_result=l3_result,
            total_latency_ms=total_latency_ms,
            completed_at=datetime.now().isoformat(),
            prediction_result=prediction_result,
            fundamentals=fundamentals,
            anomaly_analysis=anomaly_analysis,
        )

        self.logger.info(f"{'='*60}")
        self.logger.info(f"[GOLDEN MERGER] Complete: {match_id}")
        self.logger.info(f"  L1: {l1_result.status.value}")
        if l2_result:
            self.logger.info(f"  L2: {l2_result.status.value}")
        if l3_result:
            self.logger.info(f"  L3: {l3_result.status.value}")
        if prediction_result:
            self.logger.info(
                f"  Prediction: {prediction_result['final_prediction']} "
                f"({prediction_result['final_confidence']:.1%}, "
                f"{prediction_result['consensus_level']})"
            )
        if fundamentals:
            home_missing = len(fundamentals.get("home_missing", []))
            away_missing = len(fundamentals.get("away_missing", []))
            mv_gap = fundamentals.get("market_value_gap", 0)
            self.logger.info(
                f"  Fundamentals: {home_missing}H/{away_missing}A missing, "
                f"MV Gap: €{abs(mv_gap)/1e6:.1f}M"
            )
        if anomaly_analysis and anomaly_analysis.get("detected"):
            self.logger.warning(
                f"  ⚠️ Anomaly: {len(anomaly_analysis['anomalies'])} detected, "
                f"confidence adjustment: {anomaly_analysis['confidence_adjustment']:.2f}"
            )
        self.logger.info(f"  Total Latency: {total_latency_ms}ms")
        self.logger.info(f"  Success: {summary.is_complete_success}")
        self.logger.info(f"{'='*60}")

        return summary

    # ========================================================================
    # V171.001: FUNDAMENTALS LOADING
    # ========================================================================

    async def _harvest_and_save_fundamentals(self, match_id: str) -> bool:
        """采集并保存基本面数据

        尝试多种数据源采集阵容、伤停、身价数据，并写入 match_fundamentals 表。

        Args:
            match_id: 比赛 ID

        Returns:
            是否成功采集并保存
        """
        import aiohttp

        self.logger.info(f"[Fundamentals] Harvesting data for match: {match_id}")

        fundamentals_data = None

        # 方法1: 尝试从 FotMob API 获取
        try:
            fundamentals_data = await self._fetch_fotmob_fundamentals(match_id)
            if fundamentals_data:
                self.logger.info(f"[Fundamentals] Got data from FotMob API")
        except Exception as e:
            self.logger.warning(f"[Fundamentals] FotMob API failed: {e}")

        # 方法2: 如果 FotMob 失败，尝试调用 Node.js FundamentalHarvester
        if not fundamentals_data:
            try:
                fundamentals_data = await self._call_js_fundamental_harvester(match_id)
                if fundamentals_data:
                    self.logger.info(f"[Fundamentals] Got data from JS FundamentalHarvester")
            except Exception as e:
                self.logger.warning(f"[Fundamentals] JS Harvester failed: {e}")

        # 如果获取到数据，写入数据库
        if fundamentals_data:
            try:
                await self._save_fundamentals_to_db(match_id, fundamentals_data)
                self.logger.info(f"[Fundamentals] Saved to match_fundamentals table")
                return True
            except Exception as e:
                self.logger.error(f"[Fundamentals] Failed to save: {e}")
                return False

        return False

    async def _fetch_fotmob_fundamentals(self, match_id: str) -> Dict[str, Any] | None:
        """从 FotMob API 获取基本面数据

        Args:
            match_id: FotMob match ID

        Returns:
            基本面数据字典
        """
        import aiohttp
        import json

        url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Origin": "https://www.fotmob.com",
            "Referer": "https://www.fotmob.com/"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                return self._parse_fotmob_fundamentals(data, match_id)

    def _parse_fotmob_fundamentals(self, data: Dict[str, Any], match_id: str) -> Dict[str, Any]:
        """解析 FotMob API 返回的基本面数据

        Args:
            data: FotMob API 响应数据
            match_id: 比赛 ID

        Returns:
            结构化的基本面数据
        """
        result = {
            "match_id": match_id,
            "home_squad": {"formation": None, "starters": [], "missing_players": []},
            "away_squad": {"formation": None, "starters": [], "missing_players": []},
            "injuries": [],
            "suspensions": [],
            "market_value_gap": None
        }

        content = data.get("content", {})

        # 递归查找 lineup 数据
        def find_lineup(obj, depth=0):
            if depth > 8 or not obj or not isinstance(obj, dict):
                return None
            if obj.get("home") and obj.get("away"):
                if obj.get("home", {}).get("lineup") or obj.get("away", {}).get("lineup"):
                    return obj
            for key, val in obj.items():
                if isinstance(val, dict):
                    found = find_lineup(val, depth + 1)
                    if found:
                        return found
            return None

        lineup_data = find_lineup(content)

        if lineup_data:
            home = lineup_data.get("home", {})
            away = lineup_data.get("away", {})

            result["home_squad"]["formation"] = home.get("formation")
            result["away_squad"]["formation"] = away.get("formation")

            # 提取首发球员
            for player in home.get("lineup", []):
                result["home_squad"]["starters"].append({
                    "name": player.get("name") or player.get("playerName", "Unknown"),
                    "position": player.get("position") or player.get("role"),
                    "rating": player.get("rating")
                })

            for player in away.get("lineup", []):
                result["away_squad"]["starters"].append({
                    "name": player.get("name") or player.get("playerName", "Unknown"),
                    "position": player.get("position") or player.get("role"),
                    "rating": player.get("rating")
                })

            # 提取缺阵球员
            for player in home.get("missingPlayers", []):
                result["home_squad"]["missing_players"].append({
                    "name": player.get("name", "Unknown"),
                    "reason": player.get("reason", "Unknown")
                })

            for player in away.get("missingPlayers", []):
                result["away_squad"]["missing_players"].append({
                    "name": player.get("name", "Unknown"),
                    "reason": player.get("reason", "Unknown")
                })

        return result

    async def _call_js_fundamental_harvester(self, match_id: str) -> Dict[str, Any] | None:
        """调用 Node.js FundamentalHarvester

        Args:
            match_id: 比赛 ID

        Returns:
            基本面数据
        """
        import asyncio
        import json

        cmd = [
            "node", "-e",
            f"""
const {{ FundamentalHarvester }} = require('./src/infrastructure/engines/FundamentalHarvester.js');

async function main() {{
    const harvester = new FundamentalHarvester();
    try {{
        const data = await harvester.harvest('{match_id}', {{ saveToDb: false }});
        console.log(JSON.stringify(data));
    }} catch (e) {{
        console.error(JSON.stringify({{ error: e.message }}));
    }} finally {{
        await harvester.close();
    }}
}}

main();
"""
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/app"
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

        if proc.returncode != 0:
            return None

        try:
            return json.loads(stdout.decode().strip())
        except json.JSONDecodeError:
            return None

    async def _save_fundamentals_to_db(self, match_id: str, data: Dict[str, Any]) -> None:
        """保存基本面数据到数据库

        Args:
            match_id: 比赛 ID
            data: 基本面数据
        """
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO match_fundamentals (
                    match_id, home_formation, away_formation,
                    home_starters, away_starters,
                    home_missing, away_missing,
                    injuries, suspensions, market_value_gap
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id) DO UPDATE SET
                    home_formation = EXCLUDED.home_formation,
                    away_formation = EXCLUDED.away_formation,
                    home_starters = EXCLUDED.home_starters,
                    away_starters = EXCLUDED.away_starters,
                    home_missing = EXCLUDED.home_missing,
                    away_missing = EXCLUDED.away_missing,
                    injuries = EXCLUDED.injuries,
                    suspensions = EXCLUDED.suspensions,
                    market_value_gap = EXCLUDED.market_value_gap,
                    updated_at = NOW()
            """, (
                match_id,
                data.get("home_squad", {}).get("formation"),
                data.get("away_squad", {}).get("formation"),
                json.dumps(data.get("home_squad", {}).get("starters", [])),
                json.dumps(data.get("away_squad", {}).get("starters", [])),
                json.dumps(data.get("home_squad", {}).get("missing_players", [])),
                json.dumps(data.get("away_squad", {}).get("missing_players", [])),
                json.dumps(data.get("injuries", [])),
                json.dumps(data.get("suspensions", [])),
                data.get("market_value_gap")
            ))

            conn.commit()

        finally:
            cur.close()

    async def _load_fundamentals(self, match_id: str) -> Dict[str, Any] | None:
        """加载基本面数据

        Args:
            match_id: 比赛 ID

        Returns:
            基本面数据字典
        """
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    home_formation, away_formation,
                    home_starters, away_starters,
                    home_missing, away_missing,
                    injuries, suspensions, market_value_gap
                FROM match_fundamentals
                WHERE match_id = %s
            """, (match_id,))

            row = cur.fetchone()
            if not row:
                return None

            return {
                "home_formation": row[0],
                "away_formation": row[1],
                "home_starters": row[2] or [],
                "away_starters": row[3] or [],
                "home_missing": row[4] or [],
                "away_missing": row[5] or [],
                "injuries": row[6] or [],
                "suspensions": row[7] or [],
                "market_value_gap": float(row[8]) if row[8] else 0.0
            }

        except Exception as e:
            self.logger.warning(f"Failed to load fundamentals: {e}")
            return None

        finally:
            cur.close()

    def _analyze_anomalies(
        self,
        odds_data: Dict[str, Any],
        fundamentals: Dict[str, Any],
        prediction: Dict[str, Any] | None
    ) -> Dict[str, Any]:
        """分析赔率异常与基本面关联

        检测:
        1. 赔率剧烈波动 vs 核心球员缺阵
        2. 模型预测与市场赔率背离
        3. 身价差距与赔率不匹配

        Args:
            odds_data: 赔率数据
            fundamentals: 基本面数据
            prediction: 预测结果

        Returns:
            异常分析结果
        """
        anomalies = []
        result = {"detected": False, "anomalies": [], "confidence_adjustment": 1.0}

        # 1. 检查核心球员缺阵
        home_missing = fundamentals.get("home_missing", [])
        away_missing = fundamentals.get("away_missing", [])

        key_players_home = len([p for p in home_missing if self._is_key_player(p)])
        key_players_away = len([p for p in away_missing if self._is_key_player(p)])

        if key_players_home > 0 or key_players_away > 0:
            anomaly = {
                "type": "KEY_PLAYER_MISSING",
                "severity": "HIGH" if (key_players_home + key_players_away) >= 2 else "MEDIUM",
                "details": {
                    "home_key_missing": key_players_home,
                    "away_key_missing": key_players_away
                }
            }
            anomalies.append(anomaly)

        # 2. 检查身价差距
        mv_gap = fundamentals.get("market_value_gap", 0)
        if abs(mv_gap) > 100_000_000:  # > 1亿欧元差距
            anomaly = {
                "type": "HUGE_MARKET_VALUE_GAP",
                "severity": "MEDIUM",
                "details": {
                    "gap_eur": mv_gap,
                    "direction": "home_stronger" if mv_gap > 0 else "away_stronger"
                }
            }
            anomalies.append(anomaly)

        # 3. 检查预测与市场背离
        if prediction:
            # 获取市场隐含概率
            l1_data = odds_data.get("l1")
            if l1_data and hasattr(l1_data, "raw_data"):
                raw = l1_data.raw_data or {}
                avg_odds = raw.get("avg_odds", {})
                final_h = avg_odds.get("final_h", 2.0)
                final_d = avg_odds.get("final_d", 3.3)
                final_a = avg_odds.get("final_a", 3.5)

                # 市场隐含概率
                total = 1/final_h + 1/final_d + 1/final_a
                market_probs = {
                    "Home": (1/final_h) / total,
                    "Draw": (1/final_d) / total,
                    "Away": (1/final_a) / total
                }

                # 模型预测
                model_pred = prediction.get("final_prediction", "")
                model_conf = prediction.get("final_confidence", 0.5)
                market_prob = market_probs.get(model_pred, 0.33)

                # 如果模型置信度与市场概率差距过大
                gap = abs(model_conf - market_prob)
                if gap > 0.15:  # 15% 差距
                    anomaly = {
                        "type": "MODEL_MARKET_DIVERGENCE",
                        "severity": "MEDIUM",
                        "details": {
                            "model_prediction": model_pred,
                            "model_confidence": model_conf,
                            "market_probability": market_prob,
                            "gap": gap
                        }
                    }
                    anomalies.append(anomaly)

        # 汇总结果
        if anomalies:
            result["detected"] = True
            result["anomalies"] = anomalies

            # 根据异常数量调整置信度
            severity_weights = {"HIGH": 0.15, "MEDIUM": 0.08, "LOW": 0.03}
            total_penalty = sum(severity_weights.get(a["severity"], 0) for a in anomalies)
            result["confidence_adjustment"] = max(0.5, 1.0 - total_penalty)

        return result

    def _is_key_player(self, player: Dict[str, Any]) -> bool:
        """判断是否为核心球员

        Args:
            player: 球员信息

        Returns:
            是否为核心球员
        """
        # 基于位置的权重判断
        position = player.get("position", "")
        key_positions = ["GK", "CB", "CM", "ST", "CF", "CAM", "CDM"]
        if position in key_positions:
            return True

        # 基于评分判断
        rating = player.get("rating")
        if rating and rating >= 7.0:
            return True

        return False

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
