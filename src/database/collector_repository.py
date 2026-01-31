#!/usr/bin/env python3
"""
[Genesis.Standardization] Collector Repository - FotMob 数据采集仓储层
========================================================================

本模块实现了 Repository 模式，负责所有与 FotMob 数据采集相关的数据库操作。
从 collection_service.py (1843 行) 中提取 SQL 查询，实现职责分离。

设计原则:
- 单一职责: 只负责数据库 IO 操作
- 依赖倒置: 依赖连接池抽象而非具体实现
- 可测试性: 支持依赖注入和 Mock

SQL 操作迁移:
- test_connection(): SELECT 1 (原 collection_service.py:369)
- save_match_data(): INSERT ... ON CONFLICT (原 collection_service.py:658-680)
- batch_save_match_data(): 批量 INSERT ... ON CONFLICT (原 collection_service.py:756-778)

Author: Genesis.Standardization
Version: V1.0
Date: 2026-01-31
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class MatchData:
    """比赛数据模型

    对应 collection_service.py 中的数据结构
    """

    fotmob_id: str
    home_team: str | None
    away_team: str | None
    home_score: int | None
    away_score: int | None
    status: str | None
    match_time: datetime | None
    venue: dict | None
    lineups: dict | None
    stats: dict | None
    metadata: dict | None
    data_source: str = "fotmob"
    collection_time: datetime | None = None


@dataclass
class BatchSaveResult:
    """批量保存结果"""

    successful_count: int
    failed_count: int
    errors: list[str]
    elapsed_time: float


# ============================================================================
# Collector Repository
# ============================================================================


class CollectorRepository:
    """
    [Genesis.Standardization] FotMob 数据采集仓储

    负责所有与 FotMob 数据采集相关的数据库操作：
    - 连接测试
    - 单场比赛数据保存 (UPSERT)
    - 批量比赛数据保存 (事务保护)

    Example:
        >>> repo = CollectorRepository(db_pool)
        >>> await repo.test_connection()
        >>> await repo.save_match_data(match_data, connection)
    """

    # SQL 语句常量
    SQL_TEST_CONNECTION = "SELECT 1"

    SQL_UPSERT_MATCH = """
    INSERT INTO matches (
        fotmob_id, home_team, away_team, home_score, away_score,
        status, match_time, venue, lineups, stats, metadata,
        data_source, collection_time
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
    )
    ON CONFLICT (fotmob_id) DO UPDATE SET
        home_team = EXCLUDED.home_team,
        away_team = EXCLUDED.away_team,
        home_score = EXCLUDED.home_score,
        away_score = EXCLUDED.away_score,
        status = EXCLUDED.status,
        match_time = EXCLUDED.match_time,
        venue = EXCLUDED.venue,
        lineups = EXCLUDED.lineups,
        stats = EXCLUDED.stats,
        metadata = EXCLUDED.metadata,
        collection_time = EXCLUDED.collection_time,
        updated_at = CURRENT_TIMESTAMP
    """

    def __init__(self, db_pool):
        """
        初始化仓储

        Args:
            db_pool: asyncpg 数据库连接池 (DatabasePool 实例)
        """
        self.db_pool = db_pool
        logger.info("✅ [Genesis.Standardization] CollectorRepository 初始化完成")

    # ========================================================================
    # 连接测试
    # ========================================================================

    async def test_connection(self) -> bool:
        """
        测试数据库连接

        迁移自 collection_service.py:369

        Returns:
            bool: 连接是否成功
        """
        try:
            async with self.db_pool.connection() as conn:
                await conn.fetchval(self.SQL_TEST_CONNECTION)
            logger.info("✅ 数据库连接测试成功")
            return True
        except Exception as e:
            logger.error(f"❌ 数据库连接测试失败: {e}")
            return False

    # ========================================================================
    # 单场比赛保存
    # ========================================================================

    async def save_match_data(
        self,
        data: MatchData | dict[str, Any],
        connection: asyncpg.Connection,
    ) -> str:
        """
        保存单场比赛数据 (UPSERT)

        迁移自 collection_service.py:658-680

        Args:
            data: 比赛数据 (MatchData 对象或字典)
            connection: asyncpg 连接对象

        Returns:
            str: 执行结果描述

        Raises:
            asyncpg.PostgresError: 数据库错误
        """
        # 处理数据格式
        if isinstance(data, dict):
            fotmob_id = data.get("fotmob_id") or data.get("match_id")
            home_team = data.get("home_team")
            away_team = data.get("away_team")
            home_score = data.get("home_score")
            away_score = data.get("away_score")
            status = data.get("status")
            match_time = data.get("match_time")
            venue = data.get("venue")
            lineups = data.get("lineups")
            stats = data.get("stats")
            metadata = data.get("xg")  # 原 collection_service.py:695 使用 xg 作为 metadata
            data_source = "fotmob"
            collection_time = datetime.utcnow()
        else:
            fotmob_id = data.fotmob_id
            home_team = data.home_team
            away_team = data.away_team
            home_score = data.home_score
            away_score = data.away_score
            status = data.status
            match_time = data.match_time
            venue = data.venue
            lineups = data.lineups
            stats = data.stats
            metadata = data.metadata
            data_source = data.data_source
            collection_time = data.collection_time or datetime.utcnow()

        result = await connection.execute(
            self.SQL_UPSERT_MATCH,
            fotmob_id,
            home_team,
            away_team,
            home_score,
            away_score,
            status,
            match_time,
            venue,
            lineups,
            stats,
            metadata,
            data_source,
            collection_time,
        )

        logger.info(f"✅ 比赛数据已保存: {fotmob_id}")
        return result

    # ========================================================================
    # 批量保存
    # ========================================================================

    async def batch_save_match_data(
        self,
        matches_data: list[dict[str, Any]],
        connection: asyncpg.Connection,
    ) -> BatchSaveResult:
        """
        批量保存比赛数据 (单个事务)

        迁移自 collection_service.py:756-824

        Args:
            matches_data: 比赛数据列表，每个元素包含 data 和 task
            connection: asyncpg 连接对象

        Returns:
            BatchSaveResult: 批量保存结果

        Raises:
            asyncpg.PostgresError: 数据库错误
        """
        import time

        start_time = time.time()
        successful_count = 0
        failed_count = 0
        errors = []

        for match_info in matches_data:
            try:
                data = match_info.get("data", {})
                task = match_info.get("task", {})

                # 提取 match_id
                fotmob_id = (
                    data.get("fotmob_id")
                    or data.get("match_id")
                    or getattr(task, "match_id", None)
                )

                if not fotmob_id:
                    failed_count += 1
                    error_msg = "缺少 match_id"
                    errors.append(error_msg)
                    logger.warning(f"⚠️  {error_msg}")
                    continue

                # 执行 UPSERT
                await connection.execute(
                    self.SQL_UPSERT_MATCH,
                    fotmob_id,
                    data.get("home_team"),
                    data.get("away_team"),
                    data.get("home_score"),
                    data.get("away_score"),
                    data.get("status"),
                    data.get("match_time"),
                    data.get("venue"),
                    data.get("lineups"),
                    data.get("stats"),
                    data.get("xg"),  # metadata
                    "fotmob",
                    datetime.utcnow(),
                )

                successful_count += 1
                logger.debug(f"✅ 批量保存成功: {fotmob_id}")

            except Exception as e:
                failed_count += 1
                error_msg = f"保存失败 {fotmob_id}: {e!s}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")

        elapsed_time = time.time() - start_time

        logger.info(
            f"📊 批量保存完成: {successful_count} 成功, {failed_count} 失败, "
            f"耗时 {elapsed_time:.2f}s"
        )

        return BatchSaveResult(
            successful_count=successful_count,
            failed_count=failed_count,
            errors=errors,
            elapsed_time=elapsed_time,
        )


# ============================================================================
# 工厂函数
# ============================================================================


async def create_collector_repository(
    db_pool=None,
) -> CollectorRepository:
    """
    创建采集器仓储实例

    Args:
        db_pool: 数据库连接池 (可选，默认使用全局连接池)

    Returns:
        CollectorRepository: 仓储实例
    """
    if db_pool is None:
        from src.database.db_pool import get_db_pool

        db_pool = await get_db_pool()

    return CollectorRepository(db_pool)


# 导出
__all__ = [
    "BatchSaveResult",
    "CollectorRepository",
    "MatchData",
    "create_collector_repository",
]
