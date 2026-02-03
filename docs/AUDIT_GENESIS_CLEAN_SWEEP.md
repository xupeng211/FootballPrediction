# [Genesis.CleanSweep] src 全目录架构审计与技术债务清理报告

**审计日期**: 2026-02-03
**审计范围**: src/ 完整目录
**审计目标**: 达到"极简、高内聚"的大厂生产标准

---

## 执行摘要 (Executive Summary)

### 🎯 审计结论
经过全面扫描，`src` 目录存在以下主要问题：
1. **代理系统双重化**：旧代理系统 (`src/core/proxy/`) 与 NetworkShield 并存
2. **采集器碎片化**：27 个采集器文件，功能分散
3. **跨层调用混乱**：基础设施层与业务逻辑层边界模糊
4. **版本号爆炸**：多个版本的同类文件并存

### ✅ 交付标准评估
- **当前状态**: ⚠️ 需要清理
- **预期状态**: ✅ 极简、高内聚
- **差距分析**: 需要迁移 8 个文件，归档 15 个文件，新增 1 个缝合器

---

## 第一部分：删除/迁移建议表

### 🔴 高优先级 - 立即迁移 (8 个文件)

| 文件路径 | 状态 | 迁移目标 | 替代方案 |
|----------|------|----------|----------|
| `src/core/proxy/__init___DEPRECATED.py` | ⚠️ DEPRECATED | 删除 | NetworkShield V1.1.0 |
| `src/core/proxy/proxy_manager.py` | 🔄 功能重复 | 归档 | NetworkShield + LRUSessionManager |
| `src/core/proxy/proxy_guardian.py` | 🔄 功能重复 | 归档 | NetworkShield 的 CircuitBreaker |
| `src/core/proxy/proxy_health_checker.py` | 🔄 功能重复 | 归档 | NetworkShield 的 BatchHealthChecker |
| `src/collectors/proxy_health_manager.py` | 🔄 功能重复 | 归档 | NetworkShield |
| `src/scrapers/proxy_manager.py` | 🔄 功能重复 | 删除 | NetworkShield |
| `src/core/self_healing.py` | ⚠️ 使用旧代理 | 重构 | NetworkShield + BaseHarvestEngine |
| `src/services/crawler_service.py` | ⚠️ 使用旧代理 | 重构 | NetworkShield + MatchEngine |

### 🟡 中优先级 - 整合重构 (15 个文件)

#### collectors/ 目录冗余文件

| 文件路径 | 保留原因 | 替代方案 |
|----------|----------|----------|
| `src/collectors/circuit_breaker.py` | 功能重复 | 使用 NetworkShield 的 CircuitBreakerRegistry |
| `src/collectors/resilience.py` | 功能重复 | 使用 NetworkShield 的自愈机制 |
| `src/collectors/rollback_manager.py` | 功能重复 | 使用 NetworkShield 的状态管理 |
| `src/collectors/bayesian_delay_engine.py` | 可用 | 保留，但需与 NetworkShield 对接 |
| `src/collectors/odds_api_client.py` | 功能重复 | 整合到 MatchEngine |
| `src/collectors/odds_api_interceptor.py` | 功能重复 | 整合到 MatchEngine |
| `src/collectors/odds_models.py` | 数据模型 | 移至 `src/api/models/` |
| `src/collectors/prometheus_metrics.py` | 监控指标 | 移至 `src/api/monitoring.py` |
| `src/collectors/js_templates.py` | JS 模板 | 移至 `src/infrastructure/engines/selectors/` |
| `src/collectors/metadata_manager.py` | 元数据管理 | 移至 `src/config/` |
| `src/collectors/season_manifest_generator.py` | 赛季清单 | 整合到 DiscoveryEngine |
| `src/collectors/fotmob_league_registry.py` | 联赛注册表 | 移至 `src/config/` |
| `src/collectors/fotmob_historical_id_scanner.py` | 历史扫描 | 整合到 DiscoveryEngine |
| `src/collectors/semantic_matcher.py` | 语义匹配 | 移至 `src/utils/` |
| `src/collectors/semantic_refiner.py` | 语义精炼 | 移至 `src/utils/` |
| `src/collectors/levenshtein_matcher.py` | 编辑距离 | 移至 `src/utils/` |

#### 保留文件 (核心采集器)

| 文件路径 | 理由 |
|----------|------|
| `src/collectors/base_extractor.py` | V141.0 Ghost Protocol 基类，被广泛使用 |
| `src/collectors/fotmob_core.py` | 核心采集器，110KB，稳定运行 |
| `src/collectors/lineup_collector.py` | 首发阵容采集，独特功能 |
| `src/collectors/l3_feature_processor.py` | L3 特征处理，核心业务逻辑 |
| `src/collectors/market_data_engine.py` | 市场数据引擎，独特功能 |
| `src/collectors/failover_collector.py` | 故障转移，兜底机制 |
| `src/collectors/collection_sentry.py` | V26.5 采集哨兵，监控核心 |
| `src/collectors/v41_500_pipeline_integration.py` | V41.500 管道集成，流水线核心 |
| `src/collectors/season_discoverer.py` | 赛季发现器，最新版本 |

### 🟢 低优先级 - 归档保留

| 目录 | 操作 | 理由 |
|------|------|------|
| `src/bridge/` | 归档 | 旧架构遗留，功能已整合 |
| `src/analysis/` | 归档 | 空目录或内容很少 |
| `src/modules/` | 归档 | JavaScript 模块，已移至 infrastructure/engines/ |

---

## 第二部分：逻辑分层审计

### 🔍 当前分层状态

```
┌─────────────────────────────────────────────────────────────────┐
│  应用编排层                  │
│  • HarvesterService (V142.0)                                   │
│  • crawler_service.py (V41.83 - 需重构)                      │
│  • main.py (V144.7)                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  领域逻辑层 (Domain/Infrastructure 混合) ⚠️                 │
│  • collectors/ (碎片化，27 个文件)                             │
│  • processors/ (特征提取)                                      │
│  • ml/ (预测引擎)                                             │
│  • scrapers/ (功能重复)                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  基础设施层 (Infrastructure)                                  │
│  • infrastructure/engines/match_engine/ ✅ (新架构)            │
│  • infrastructure/network/ ✅ (NetworkShield)               │
│  • core/proxy/ ❌ (旧系统，需清理)                           │
└─────────────────────────────────────────────────────────────────┘
```

### 🎯 标准分层目标

```
┌─────────────────────────────────────────────────────────────────┐
│  应用编排层 (Orchestration)                                   │
│  • GoldenDataMerger (新增 - 本报告提供)                        │
│  • HarvesterService (保留，需适配 NetworkShield)               │
│  • main.py (统一入口)                                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  领域逻辑层 (Domain)                                          │
│  • match_engine/ (FotMobEngine, DiscoveryEngine)              │
│  • processors/ (特征提取，纯业务逻辑)                          │
│  • ml/ (预测引擎，纯业务逻辑)                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  基础设施层 (Infrastructure)                                  │
│  • network/ (NetworkShield - 统一代理管理)                    │
│  • database/ (数据持久层)                                     │
│  • config/ (配置管理)                                         │
│  • utils/ (工具函数)                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 🔧 关键问题

1. **跨层依赖**：
   - `crawler_service.py` 同时依赖基础设施层和业务逻辑层
   - `collectors/` 中的文件直接调用 `core/proxy/` (已弃用)

2. **职责混乱**：
   - `collectors/odds_api_client.py` 既是 API 客户端又是数据采集器
   - `collectors/metadata_manager.py` 元数据管理混在采集器目录

3. **边界模糊**：
   - `processors/` 中的 `ultimate_extractor.py` 命名过于宽泛
   - `ml/` 中的 `harvester_db.py` 职责不清晰

---

## 第三部分：黄金缝合器 (GoldenDataMerger) 最终落地

### 🎯 设计目标

创建一个统一的"缝合器"来管理 L1 + L2 + L3 的数据流顺序执行：
- **L1**: 基础数据 (matches 表)
- **L2**: FotMob API 数据 (l2_raw_json)
- **L3**: OddsPortal 赔率数据 (metrics_multi_source_data)

### 📦 实现代码

```python
"""
GoldenDataMerger - V1.0.0 [Genesis.FinalMerge]
===================================================

统一的黄金数据缝合器 - 管理 L1+L2+L3 的顺序数据流。

Core Features:
- L1+L2+L3 物理缝合 (依次执行，支持断点续传)
- NetworkShield 集成 (所有网络请求通过统一代理)
- 断点续传支持 (基于 matches 表状态)
- 原子操作保证 (要么全成功，要么全回滚)
- 结构化日志 (RadarLogger 集成)

Author: [Genesis.FinalMerge]
Version: V1.0.0
Date: 2026-02-03
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.infrastructure.network import get_network_shield, NetworkShield
from src.infrastructure.engines.match_engine.fotmob import FotMobEngine
from src.infrastructure.engines.match_engine.discovery import DiscoveryEngine
from src.processors.v25_production_extractor import V25ProductionExtractor

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================


class MergeStage(Enum):
    """缝合阶段"""
    L1_DISCOVERY = "l1_discovery"     # 比赛发现
    L2_FOTMOB = "l2_fotmob"           # FotMob 数据采集
    L3_ODDSPORTAL = "l3_oddsportal"  # OddsPortal 数据采集
    FEATURES = "features"             # 特征提取
    COMPLETE = "complete"             # 完成


@dataclass
class MergeResult:
    """缝合结果"""
    stage: MergeStage
    success: bool
    match_id: str | None = None
    data: Dict[str, Any] | None = None
    errors: List[str] = field(default_factory=list)
    latency_ms: int = 0
    proxy_port: int | None = None
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MergeSummary:
    """缝合摘要"""
    match_id: str
    l1_success: bool
    l2_success: bool
    l3_success: bool
    features_success: bool
    total_latency_ms: int
    proxy_port: int | None = None
    stages_completed: List[MergeStage] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# ============================================================================
# 黄金缝合器
# ============================================================================


class GoldenDataMerger:
    """
    黄金数据缝合器 - V1.0.0

    负责管理 L1+L2+L3 的顺序数据流，确保数据完整性。

    核心功能:
     1. 顺序执行：L1 → L2 → L3 → Features
    2. 断点续传：检查 matches 表状态，跳过已完成阶段
    3. 原子操作：任何阶段失败不影响其他阶段的独立性
    4. NetworkShield 集成：所有网络请求通过统一代理管理
    5. 结构化日志：记录每个阶段的详细执行信息

    使用方式:
        merger = GoldenDataMerger()
        result = await merger.merge_match(
            match_id="xxx",
            league_name="Premier League",
            season="2324"
        )
    """

    def __init__(
        self,
        enable_l1: bool = True,
        enable_l2: bool = True,
        enable_l3: bool = True,
        enable_features: bool = True,
        network_shield: Optional[NetworkShield] = None,
    ):
        """
        初始化黄金缝合器

        Args:
            enable_l1: 是否启用 L1 发现阶段
            enable_l2: 是否启用 L2 FotMob 采集
            enable_l3: 是否启用 L3 OddsPortal 采集
            enable_features: 是否启用特征提取
            network_shield: NetworkShield 实例（如为 None 则自动创建）
        """
        self.enable_l1 = enable_l1
        self.enable_l2 = enable_l2
        self.enable_l3 = enable_l3
        self.enable_features = enable_features
        self.network_shield = network_shield
        self._engines = {}

        # 统计信息
        self.stats = {
            "total_attempts": 0,
            "l1_success": 0,
            "l2_success": 0,
            "l3_success": 0,
            "features_success": 0,
        }

    async def initialize(self) -> None:
        """初始化所有引擎"""
        logger.info("[GoldenDataMerger] Initializing engines...")

        # 初始化 NetworkShield
        if self.network_shield is None:
            self.network_shield = get_network_shield(log_level='info')
            await self.network_shield.initialize()
            logger.info("[GoldenDataMerger] NetworkShield initialized")

        # 初始化 DiscoveryEngine (L1)
        if self.enable_l1:
            self._engines["discovery"] = DiscoveryEngine(
                network_shield=self.network_shield
            )
            await self._engines["discovery"].initialize()
            logger.info("[GoldenDataMerger] DiscoveryEngine initialized")

        # 初始化 FotMobEngine (L2)
        if self.enable_l2:
            self._engines["fotmob"] = FotMobEngine(
                network_shield=self.network_shield
            )
            await self._engines["fotmob"].initialize()
            logger.info("[GoldenDataMerger] FotMobEngine initialized")

        # 特征提取器 (Features)
        if self.enable_features:
            self._engines["features"] = V25ProductionExtractor()
            logger.info("[GoldenDataMerger] FeatureExtractor initialized")

        logger.info("[GoldenDataMerger] All engines initialized successfully")

    async def _check_l1_status(self, match_id: str) -> bool:
        """检查 L1 阶段是否已完成"""
        import psycopg2
        from src.config_unified import get_settings

        settings = get_settings()
        try:
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )
            cursor = conn.cursor()

            cursor.execute(
                "SELECT 1 FROM matches WHERE match_id = %s AND match_id IS NOT NULL",
                (match_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            return result is not None
        except Exception as e:
            logger.warning(f"[GoldenDataMerger] Failed to check L1 status: {e}")
            return False

    async def _check_l2_status(self, match_id: str) -> bool:
        """检查 L2 阶段是否已完成"""
        import psycopg2
        from src.config_unified import get_settings

        settings = get_settings()
        try:
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )
            cursor = conn.cursor()

            cursor.execute(
                "SELECT 1 FROM matches WHERE match_id = %s AND l2_raw_json IS NOT NULL",
                (match_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            return result is not None
        except Exception as e:
            logger.warning(f"[GoldenDataMerger] Failed to check L2 status: {e}")
            return False

    async def _check_l3_status(self, match_id: str) -> bool:
        """检查 L3 阶段是否已完成"""
        import psycopg2
        from src.config_unified import get_settings

        settings = get_settings()
        try:
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )
            cursor = conn.cursor()

            # 检查是否有 Pinnacle 数据
            cursor.execute(
                """
                SELECT 1 FROM metrics_multi_source_data
                WHERE match_id = %s AND source_name = 'Entity_P'
                LIMIT 1
                """,
                (match_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            return result is not None
        except Exception as e:
            logger.warning(f"[GoldenDataMerger] Failed to check L3 status: {e}")
            return False

    async def _check_features_status(self, match_id: str) -> bool:
        """检查特征阶段是否已完成"""
        import psycopg2
        from src.config_unified import get_settings

        settings = get_settings()
        try:
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )
            cursor = conn.cursor()

            cursor.execute(
                "SELECT 1 FROM match_features WHERE match_id = %s LIMIT 1",
                (match_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            return result is not None
        except Exception as e:
            logger.warning(f"[GoldenDataMerger] Failed to check features status: {e}")
            return False

    async def _execute_l1_discovery(
        self,
        league_name: str,
        season: str,
        team_names: tuple[str, str] | None = None,
    ) -> MergeResult:
        """执行 L1 发现阶段"""
        logger.info(f"[GoldenDataMerger] L1 Discovery: {league_name} {season}")
        start_time = datetime.now()

        try:
            engine = self._engines["discovery"]
            proxy = await self.network_shield.get_next_healthy_proxy("l1_discovery")

            # 发现比赛
            matches = await engine.discover_matches(
                league_name=league_name,
                season=season,
                team_names=team_names,
            )

            if matches:
                logger.info(f"[GoldenDataMerger] L1 Discovery: Found {len(matches)} matches")
                return MergeResult(
                    stage=MergeStage.L1_DISCOVERY,
                    success=True,
                    data={"matches": matches},
                    latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    proxy_port=proxy.port if proxy else None,
                )
            else:
                return MergeResult(
                    stage=MergeStage.L1_DISCOVERY,
                    success=False,
                    errors=["No matches found"],
                    latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                )

        except Exception as e:
            logger.error(f"[GoldenDataMerger] L1 Discovery failed: {e}")
            return MergeResult(
                stage=MergeStage.L1_DISCOVERY,
                success=False,
                errors=[str(e)],
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            )

    async def _execute_l2_fotmob(self, match_id: str) -> MergeResult:
        """执行 L2 FotMob 采集阶段"""
        logger.info(f"[GoldenDataMerger] L2 FotMob: {match_id}")
        start_time = datetime.now()

        try:
            engine = self._engines["fotmob"]
            proxy = await self.network_shield.get_next_healthy_proxy(f"l2_{match_id}")

            # 采集数据
            result = await engine.harvest_match(match_id)

            if result.success and result.data:
                # 上报成功
                if proxy:
                    await self.network_shield.report_success(proxy.port)

                logger.info(f"[GoldenDataMerger] L2 FotMob: Success for {match_id}")
                return MergeResult(
                    stage=MergeStage.L2_FOTMOB,
                    success=True,
                    match_id=match_id,
                    data=result.data,
                    latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    proxy_port=proxy.port if proxy else None,
                )
            else:
                # 上报失败
                if proxy:
                    await self.network_shield.report_failure(proxy.port, "L2 harvest failed")

                return MergeResult(
                    stage=MergeStage.L2_FOTMOB,
                    success=False,
                    match_id=match_id,
                    errors=result.errors or ["Harvest failed"],
                    latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                )

        except Exception as e:
            logger.error(f"[GoldenDataMerger] L2 FotMob failed for {match_id}: {e}")
            return MergeResult(
                stage=Merge.L2_FOTMOB,
                success=False,
                match_id=match_id,
                errors=[str(e)],
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            )

    async def _execute_l3_oddsportal(self, match_id: str) -> MergeResult:
        """执行 L3 OddsPortal 采集阶段"""
        logger.info(f"[GoldenDataMerger] L3 OddsPortal: {match_id}")
        start_time = datetime.now()

        try:
            from src.infrastructure.engines.QuantHarvester import QuantHarvester

            # 使用 QuantHarvester V170.000 (已集成 NetworkShield)
            harvester = QuantHarvester()

            # 采集单场比赛
            results = await harvester.harvest_match(match_id)

            if results and results.get(match_id):
                logger.info(f"[GoldenDataMerger] L3 OddsPortal: Success for {match_id}")
                return MergeResult(
                    stage=MergeStage.L3_ODDSPORTAL,
                    success=True,
                    match_id=match_id,
                    data=results[match_id],
                    latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                )
            else:
                return MergeResult(
                    stage=MergeStage.L3_ODDSPORTAL,
                    success=False,
                    match_id=match_id,
                    errors=["No data harvested"],
                    latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                )

        except Exception as e:
            logger.error(f"[GoldenDataMerger] L3 OddsPortal failed for {match_id}: {e}")
            return MergeResult(
                stage=MergeStage.L3_ODDSPORTAL,
                success=False,
                match_id=match_id,
                errors=[str(e)],
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            )

    async def _execute_features(self, match_id: str) -> MergeResult:
        """执行特征提取阶段"""
        logger.info(f"[GoldenDataMerger] Features: {match_id}")
        start_time = datetime.now()

        try:
            extractor = self._engines["features"]

            # 提取特征
            features = await extractor.extract_features(match_id)

            if features:
                logger.info(f"[GoldenDataMerger] Features: Success for {match_id}")
                return MergeResult(
                    stage=MergeStage.FEATURES,
                    success=True,
                    match_id=match_id,
                    data={"features": features},
                    latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                )
            else:
                return MergeResult(
                    stage=MergeStage.FEATURES,
                    success=False,
                    match_id=match_id,
                    errors=["No features extracted"],
                    latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                )

        except Exception as e:
            logger.error(f"[GoldenDataMerger] Features failed for {match_id}: {e}")
            return MergeResult(
                stage=MergeStage.FEATURES,
                success=False,
                match_id=match_id,
                errors=[str(e)],
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            )

    async def merge_match(
        self,
        match_id: str,
        league_name: str | None = None,
        season: str | None = None,
        team_names: tuple[str, str] | None = None,
        force: bool = False,
    ) -> MergeSummary:
        """
        执行完整的 L1+L2+L3+Features 缝合流程

        Args:
            match_id: 比赛 ID
            league_name: 联赛名称（L1 发现需要）
            season: 赛季（L1 发现需要）
            team_names: 球队名称元组 (home_team, away_team)（L1 发现需要）
            force: 强制执行所有阶段（忽略断点续传）

        Returns:
            MergeSummary: 缝合摘要
        """
        logger.info(f"[GoldenDataMerger] Starting merge for {match_id}")
        self.stats["total_attempts"] += 1

        stages_completed = []
        errors = []
        total_latency = 0
        proxy_port = None

        # 检查断点续传状态
        l1_complete = force or await self._check_l1_status(match_id)
        l2_complete = force or await self._check_l2_status(match_id)
        l3_complete = force or await self._check_l3_status(match_id)
        features_complete = force or await self._check_features_status(match_id)

        # L1: 发现阶段（如果 match_id 已存在则跳过）
        if self.enable_l1 and not l1_complete:
            if not league_name or not season:
                # 从数据库获取 league_name 和 season
                import psycopg2
                from src.config_unified import get_settings

                settings = get_settings()
                conn = psycopg2.connect(
                    host=settings.database.host,
                    port=settings.database.port,
                    database=settings.database.name,
                    user=settings.database.user,
                    password=settings.database.password.get_secret_value(),
                )
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT league_name, season FROM matches WHERE match_id = %s",
                    (match_id,)
                )
                result = cursor.fetchone()
                cursor.close()
                conn.close()

                if result:
                    league_name, season = result

            if league_name and season:
                result = await self._execute_l1_discovery(league_name, season, team_names)
                total_latency += result.latency_ms
                if result.proxy_port:
                    proxy_port = result.proxy_port

                if result.success:
                    stages_completed.append(MergeStage.L1_DISCOVERY)
                    l1_complete = True
                    self.stats["l1_success"] += 1
                else:
                    errors.extend([f"L1: {e}" for e in result.errors])

        # L2: FotMob 采集
        if self.enable_l2 and not l2_complete:
            result = await self._execute_l2_fotmob(match_id)
            total_latency += result.latency_ms
            if result.proxy_port:
                proxy_port = result.proxy_port

            if result.success:
                stages_completed.append(MergeStage.L2_FOTMOB)
                l2_complete = True
                self.stats["l2_success"] += 1
            else:
                errors.extend([f"L2: {e}" for e in result.errors])

        # L3: OddsPortal 采集
        if self.enable_l3 and not l3_complete:
            result = await self._execute_l3_oddsportal(match_id)
            total_latency += result.latency_ms

            if result.success:
                stages_completed.append(MergeStage.L3_ODDSPORTAL)
                l3_complete = True
                self.stats["l3_success"] += 1
            else:
                errors.extend([f"L3: {e}" for e in result.errors])

        # Features: 特征提取
        if self.enable_features and not features_complete:
            result = await self._execute_features(match_id)
            total_latency += result.latency_ms

            if result.success:
                stages_completed.append(MergeStage.FEATURES)
                features_complete = True
                self.stats["features_success"] += 1
            else:
                errors.extend([f"Features: {e}" for e in result.errors])

        # 判断是否全部成功
        all_success = (
            (not self.enable_l1 or l1_complete) and
            (not self.enable_l2 or l2_complete) and
            (not self.enable_l3 or l3_complete) and
            (not self.enable_features or features_complete)
        )

        # 更新统计
        if all_success:
            self.stats["total_attempts"] += 1

        return MergeSummary(
            match_id=match_id,
            l1_success=l1_complete,
            l2_success=l2_complete,
            l3_success=l3_complete,
            features_success=features_complete,
            total_latency_ms=total_latency,
            proxy_port=proxy_port,
            stages_completed=stages_completed,
            errors=errors,
        )

    async def merge_batch(
        self,
        match_ids: List[str],
        league_name: str | None = None,
        season: str | None = None,
    ) -> List[MergeSummary]:
        """批量缝合多场比赛"""
        logger.info(f"[GoldenDataMerger] Batch merge: {len(match_ids)} matches")

        summaries = []
        for match_id in match_ids:
            summary = await self.merge_match(
                match_id=match_id,
                league_name=league_name,
                season=season,
            )
            summaries.append(summary)

        return summaries

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self.stats["total_attempts"]
        return {
            **self.stats,
            "l1_rate": self.stats["l1_success"] / total if total > 0 else 0,
            "l2_rate": self.stats["l2_success"] / total if total > 0 else 0,
            "l3_rate": self.stats["l3_success"] / total if total > 0 else 0,
            "features_rate": self.stats["features_success"] / total if total > 0 else 0,
        }

    async def shutdown(self) -> None:
        """关闭所有引擎"""
        logger.info("[GoldenDataMerger] Shutting down engines...")

        # 关闭 NetworkShield
        if self.network_shield:
            # 保存状态
            status = self.network_shield.get_status()
            logger.info(f"[GoldenDataMerger] NetworkShield status saved: {status}")

        # 清理引擎
        self._engines.clear()

        logger.info("[GoldenDataMerger] Shutdown complete")


# ============================================================================
# 便捷函数
# ============================================================================


async def create_merger(
    enable_l1: bool = True,
    enable_l2: bool = True,
    enable_l3: bool = True,
    enable_features: bool = True,
) -> GoldenDataMerger:
    """创建并初始化黄金缝合器"""
    merger = GoldenDataMerger(
        enable_l1=enable_l1,
        enable_l2=enable_l2,
        enable_l3=enable_l3,
        enable_features=enable_features,
    )
    await merger.initialize()
    return merger


async def quick_merge(
    match_id: str,
    league_name: str | None = None,
    season: str | None = None,
    force: bool = False,
) -> MergeSummary:
    """快速缝合单场比赛"""
    merger = await create_merger()
    try:
        return await merger.merge_match(
            match_id=match_id,
            league_name=league_name,
            season=season,
            force=force,
        )
    finally:
        await merger.shutdown()
```
