#!/usr/bin/env python3
"""
V26.5 Failover 采集器 - 数据源自动切换
========================================

核心功能：
    1. 主备数据源自动切换（OddsPortal → FotMob）
    2. Try-Except 级联逻辑
    3. Failover 事件记录
    4. 容错处理（双数据源都失败时不崩溃）

设计原则：
    - 透明切换：上层调用者无需关心数据源切换
    - 日志完整：记录每次 Failover 事件
    - 容错优先：即使双数据源都失败也不中断流程

Author: TDD Expert & Fault-Tolerance Architect
Version: V26.5
Date: 2026-01-06
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any

from src.api.collectors.fotmob_core import FotMobCoreCollector

logger = logging.getLogger(__name__)


# ============================================================================
# Failover 事件记录
# ============================================================================


@dataclass
class FailoverEvent:
    """Failover 事件记录"""

    match_id: int
    league_id: int | None
    season: str | None
    primary_source: str
    primary_error: str | None
    fallback_source: str
    fallback_success: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat)


class FailoverLogger:
    """Failover 事件日志记录器"""

    def __init__(self):
        self.events: list[FailoverEvent] = []

    def log_event(self, event: FailoverEvent) -> None:
        """记录 Failover 事件"""
        self.events.append(event)

        # 记录到日志
        if event.fallback_success:
            logger.info(
                f"🔄 Failover 成功: {event.primary_source} → {event.fallback_source} | "
                f"Match ID: {event.match_id} | League: {event.league_id}"
            )
        else:
            logger.warning(
                f"⚠️ Failover 失败: {event.primary_source} 和 {event.fallback_source} 都失败 | "
                f"Match ID: {event.match_id} | League: {event.league_id}"
            )

    def get_summary(self) -> dict[str, Any]:
        """获取 Failover 统计摘要"""
        total_events = len(self.events)
        successful_failovers = sum(1 for e in self.events if e.fallback_success)
        failed_failovers = total_events - successful_failovers

        return {
            "total_failovers": total_events,
            "successful_failovers": successful_failovers,
            "failed_failovers": failed_failovers,
            "success_rate": successful_failovers / total_events if total_events > 0 else 0.0,
        }


# ============================================================================
# Failover 采集器
# ============================================================================


class FailoverCollector:
    """
    V26.5 Failover 采集器 - 数据源自动切换

    功能：
        1. 主备数据源级联采集（OddsPortal → FotMob）
        2. 自动检测主数据源失败/空数据
        3. 透明切换到备用数据源
        4. 完整的 Failover 事件记录

    使用示例：
        >>> collector = FailoverCollector()
        >>> success = collector.harvest_match_with_league(match_id=12345, league_id=47, season="2324")
    """

    def __init__(
        self,
        primary_source: str = "oddsportal",
        fallback_source: str = "fotmob",
        enable_ghost_protocol: bool = True,
    ):
        """
        初始化 Failover 采集器

        Args:
            primary_source: 主数据源 ('oddsportal' 或 'fotmob')
            fallback_source: 备用数据源 ('oddsportal' 或 'fotmob')
            enable_ghost_protocol: 是否启用 Ghost Protocol（OddsPortal 需要）
        """
        self.primary_source = primary_source
        self.fallback_source = fallback_source
        self.enable_ghost_protocol = enable_ghost_protocol
        self.failover_logger = FailoverLogger()

        # 初始化采集器实例
        self._init_collectors()

    def _init_collectors(self) -> None:
        """初始化采集器实例"""
        # OddsPortal 采集器（异步，需要 Playwright）
        self.oddsportal_extractor = None  # 延迟初始化

        # FotMob 采集器（同步，requests）
        self.fotmob_collector = FotMobCoreCollector()

    def harvest_match_with_league(
        self,
        match_id: int,
        league_id: int | None = None,
        season: str | None = None,
    ) -> bool:
        """
        V26.5: 带 Failover 的比赛采集（级联逻辑）

        采集流程：
            1. 尝试主数据源采集
            2. 如果主数据源失败/返回空，切换到备用源
            3. 记录 Failover 事件
            4. 返回最终采集结果

        Args:
            match_id: 比赛 ID
            league_id: 联赛 ID（用于动态哨兵阈值）
            season: 赛季代码（如 '2324'）

        Returns:
            bool: 采集是否成功（主源或备用源成功即返回 True）
        """
        primary_success = False
        primary_error = None

        # Step 1: 尝试主数据源
        try:
            if self.primary_source == "oddsportal":
                # OddsPortal 是异步采集器，这里暂时跳过
                # 实际使用时需要异步上下文
                primary_success = False
                primary_error = "OddsPortal requires async context"
            elif self.primary_source == "fotmob":
                primary_success = self._try_fotmob(match_id, league_id, season)

        except Exception as e:
            primary_success = False
            primary_error = str(e)
            logger.debug(f"主数据源异常: {self.primary_source} - {e}")

        # Step 2: 如果主数据源失败，尝试备用源
        if primary_success:
            # 主数据源成功，无需 Failover
            logger.debug(f"✅ 主数据源成功: {self.primary_source} | Match ID: {match_id}")
            return True

        # 主数据源失败，触发 Failover
        logger.warning(
            f"⚠️ 主数据源失败: {self.primary_source} | Match ID: {match_id} | Error: {primary_error}"
        )
        logger.info(f"🔄 触发 Failover: {self.primary_source} → {self.fallback_source}")

        fallback_success = False

        try:
            if self.fallback_source == "fotmob":
                fallback_success = self._try_fotmob(match_id, league_id, season)
            elif self.fallback_source == "oddsportal":
                fallback_success = False  # OddsPortal 需要异步上下文
                logger.warning("OddsPortal 作为备用源需要异步上下文")

        except Exception as e:
            fallback_success = False
            logger.exception(f"备用数据源异常: {self.fallback_source} - {e}")

        # Step 3: 记录 Failover 事件
        event = FailoverEvent(
            match_id=match_id,
            league_id=league_id,
            season=season,
            primary_source=self.primary_source,
            primary_error=primary_error,
            fallback_source=self.fallback_source,
            fallback_success=fallback_success,
        )
        self.failover_logger.log_event(event)

        # Step 4: 返回结果
        if fallback_success:
            logger.info(f"✅ Failover 成功 | Match ID: {match_id}")
        else:
            logger.error(f"❌ Failover 失败 | Match ID: {match_id}")

        return fallback_success

    def _try_fotmob(
        self, match_id: int, league_id: int | None = None, season: str | None = None
    ) -> bool:
        """
        尝试使用 FotMob 采集

        Args:
            match_id: 比赛 ID
            league_id: 联赛 ID
            season: 赛季代码

        Returns:
            bool: 采集是否成功
        """
        return self.fotmob_collector.harvest_match_with_league(
            match_id=match_id,
            league_id=league_id,
            season=season,
        )

    def get_failover_summary(self) -> dict[str, Any]:
        """
        获取 Failover 统计摘要

        Returns:
            统计摘要字典
        """
        return self.failover_logger.get_summary()

    def reset_failover_stats(self) -> None:
        """重置 Failover 统计（用于新批次）"""
        self.failover_logger.events.clear()


# ============================================================================
# 便捷函数
# ============================================================================


def create_failover_collector(
    primary_source: str = "oddsportal",
    fallback_source: str = "fotmob",
) -> FailoverCollector:
    """
    创建 Failover 采集器（工厂函数）

    Args:
        primary_source: 主数据源
        fallback_source: 备用数据源

    Returns:
        FailoverCollector 实例
    """
    return FailoverCollector(
        primary_source=primary_source,
        fallback_source=fallback_source,
    )
