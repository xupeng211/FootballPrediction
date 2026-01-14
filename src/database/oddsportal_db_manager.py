#!/usr/bin/env python3
"""V150.33 OddsPortal Database Manager - 数据库同步层.

This module provides the database synchronization layer for OddsPortal
scraped data. It handles safe data merging, conflict resolution, and
transaction management.

Core Features:
    - Safe JSONB merge using jsonb_set or || operators
    - Transaction management with automatic rollback
    - Batch write support for bulk operations
    - Conflict detection and resolution
    - Audit trail for all database operations

Example:
    >>> from src.database.oddsportal_db_manager import OddsPortalDBManager
    >>> db = OddsPortalDBManager()
    >>> await db.sync_match_data(result)
    >>> await db.sync_batch(results)

Author: 高级数据架构师 & 自动化工程专家
Version: V150.33
Date: 2026-01-09
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection
from psycopg2 import sql as psycopg2_sql
from contextlib import contextmanager

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ==============================================================================
# Data Classes
# ==============================================================================


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    match_id: str
    rows_affected: int = 0
    error: Optional[str] = None
    operation: str = "upsert"  # upsert, merge, skip


@dataclass
class BatchSyncResult:
    """批量同步结果"""
    total: int
    successful: int
    failed: int
    skipped: int
    results: List[SyncResult] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)


# ==============================================================================
# Database Manager
# ==============================================================================


class OddsPortalDBManager:
    """V150.33 OddsPortal 数据库管理器

    功能:
    - 安全将抓取数据同步到 matches_mapping 表
    - 使用 JSONB 操作符避免覆盖现有字段
    - 支持批量写入和事务管理
    - 提供完整的审计日志

    Example:
        >>> db = OddsPortalDBManager()
        >>> result = await db.sync_match_data(scraped_result)
        >>> print(f"同步成功: {result.success}, 行影响: {result.rows_affected}")
    """

    # 表名常量
    TABLE_NAME = "matches_mapping"
    L2_FIELD = "l2_raw_json"
    MATCH_ID_FIELD = "fotmob_id"  # V150.34: 修复，使用实际存在的 fotmob_id 字段

    # JSONB 键名
    ODDSPORTAL_KEY = "oddsportal"
    SNAPSHOT_KEY = "snapshot"
    METADATA_KEY = "metadata"

    def __init__(self, conn: Optional[connection] = None):
        """初始化数据库管理器

        Args:
            conn: 数据库连接 (None = 自动创建)
        """
        self._conn = conn
        self._own_connection = conn is None

        if self._own_connection:
            self._conn = self._create_connection()

    def _create_connection(self) -> connection:
        """创建数据库连接"""
        settings = get_settings()
        return psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor
        )

    @property
    def conn(self) -> connection:
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = self._create_connection()
        return self._conn

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        try:
            yield self.conn
            self.conn.commit()
            logger.debug("事务提交成功")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"事务回滚: {e}")
            raise

    def _build_l2_json_payload(self, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建 L2 JSON 数据载荷

        Args:
            scraped_data: 从 OddsPortalScraper 返回的数据

        Returns:
            符合 l2_raw_json 结构的字典
        """
        # 提取核心数据
        payload = {
            self.ODDSPORTAL_KEY: {
                self.SNAPSHOT_KEY: scraped_data.get("data", {}),
                self.METADATA_KEY: {
                    "source_url": scraped_data.get("source_url"),
                    "proxy": scraped_data.get("proxy"),
                    "extraction_time": scraped_data.get("extraction_time"),
                    "scraper_version": "V150.33",
                    "stats": scraped_data.get("stats", {})
                }
            }
        }
        return payload

    def sync_match_data(
        self,
        scraped_data: Dict[str, Any],
        sync_mode: str = "merge"
    ) -> SyncResult:
        """同步单场比赛数据到数据库

        Args:
            scraped_data: 从 OddsPortalScraper.fetch_snapshot() 返回的数据
            sync_mode: 同步模式
                - "merge": 合并到现有 l2_raw_json (默认，推荐)
                - "replace": 完全替换 l2_raw_json
                - "skip": 仅当 l2_raw_json 为空时写入

        Returns:
            SyncResult 对象
        """
        match_id = scraped_data.get("match_id")

        if not match_id:
            return SyncResult(
                success=False,
                match_id="",
                error="缺少 match_id"
            )

        if not scraped_data.get("success"):
            return SyncResult(
                success=False,
                match_id=match_id,
                error="采集失败，跳过同步"
            )

        try:
            with self.transaction():
                with self.conn.cursor() as cur:
                    # 构建载荷
                    payload = self._build_l2_json_payload(scraped_data)
                    payload_json = json.dumps(payload, ensure_ascii=False)

                    # 检查现有数据
                    cur.execute(
                        f"SELECT {self.L2_FIELD} FROM {self.TABLE_NAME} "
                        f"WHERE {self.MATCH_ID_FIELD} = %s",
                        (match_id,)
                    )
                    existing = cur.fetchone()

                    if existing and existing.get(self.L2_FIELD):
                        existing_l2 = existing[self.L2_FIELD]

                        if sync_mode == "skip":
                            logger.info(f"[{match_id}] 跳过: 已存在数据")
                            return SyncResult(
                                success=True,
                                match_id=match_id,
                                rows_affected=0,
                                operation="skip"
                            )

                        elif sync_mode == "merge":
                            # 使用 JSONB || 操作符合并
                            cur.execute(
                                f"UPDATE {self.TABLE_NAME} "
                                f"SET {self.L2_FIELD} = {self.L2_FIELD} || %s::jsonb, "
                                f"updated_at = NOW() "
                                f"WHERE {self.MATCH_ID_FIELD} = %s",
                                (payload_json, match_id)
                            )

                        elif sync_mode == "replace":
                            # 完全替换
                            cur.execute(
                                f"UPDATE {self.TABLE_NAME} "
                                f"SET {self.L2_FIELD} = %s::jsonb, "
                                f"updated_at = NOW() "
                                f"WHERE {self.MATCH_ID_FIELD} = %s",
                                (payload_json, match_id)
                            )
                    else:
                        # 插入新记录
                        cur.execute(
                            f"INSERT INTO {self.TABLE_NAME} "
                            f"({self.MATCH_ID_FIELD}, {self.L2_FIELD}, created_at, updated_at) "
                            f"VALUES (%s, %s::jsonb, NOW(), NOW()) "
                            f"ON CONFLICT ({self.MATCH_ID_FIELD}) "
                            f"DO UPDATE SET "
                            f"{self.L2_FIELD} = EXCLUDED.{self.L2_FIELD} || %s::jsonb, "
                            f"updated_at = NOW()",
                            (match_id, payload_json, payload_json)
                        )

                    rows_affected = cur.rowcount

            logger.info(f"[{match_id}] 同步成功: {rows_affected} 行受影响 (模式: {sync_mode})")

            return SyncResult(
                success=True,
                match_id=match_id,
                rows_affected=rows_affected,
                operation=sync_mode
            )

        except Exception as e:
            logger.error(f"[{match_id}] 同步失败: {e}")
            return SyncResult(
                success=False,
                match_id=match_id,
                error=str(e)
            )

    def sync_batch(
        self,
        scraped_results: List[Dict[str, Any]],
        sync_mode: str = "merge",
        batch_size: int = 50
    ) -> BatchSyncResult:
        """批量同步数据

        Args:
            scraped_results: 从 OddsPortalScraper 返回的结果列表
            sync_mode: 同步模式 (merge/replace/skip)
            batch_size: 批量大小

        Returns:
            BatchSyncResult 对象
        """
        total = len(scraped_results)
        results: List[SyncResult] = []
        errors: Dict[str, int] = {}

        for i, scraped_data in enumerate(scraped_results):
            result = self.sync_match_data(scraped_data, sync_mode)
            results.append(result)

            if not result.success:
                error_type = result.error or "unknown"
                errors[error_type] = errors.get(error_type, 0) + 1

            # 批量提交
            if (i + 1) % batch_size == 0:
                logger.info(f"批量进度: {i + 1}/{total}")

        successful = sum(1 for r in results if r.success and r.operation != "skip")
        failed = sum(1 for r in results if not r.success)
        skipped = sum(1 for r in results if r.operation == "skip")

        logger.info(f"批量同步完成: {successful} 成功, {failed} 失败, {skipped} 跳过")

        return BatchSyncResult(
            total=total,
            successful=successful,
            failed=failed,
            skipped=skipped,
            results=results,
            errors=errors
        )

    def verify_sync(self, match_id: str) -> Optional[Dict[str, Any]]:
        """验证同步结果

        Args:
            match_id: 8 位短哈希 ID

        Returns:
            数据库中的 l2_raw_json 数据，如果不存在返回 None
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"SELECT {self.MATCH_ID_FIELD}, {self.L2_FIELD}, created_at, updated_at "
                    f"FROM {self.TABLE_NAME} "
                    f"WHERE {self.MATCH_ID_FIELD} = %s",
                    (match_id,)
                )
                result = cur.fetchone()

                if result and result.get(self.L2_FIELD):
                    return {
                        "match_id": result[self.MATCH_ID_FIELD],
                        "l2_raw_json": result[self.L2_FIELD],
                        "created_at": result["created_at"].isoformat() if result.get("created_at") else None,
                        "updated_at": result["updated_at"].isoformat() if result.get("updated_at") else None,
                        "has_oddsportal_data": self.ODDSPORTAL_KEY in result.get(self.L2_FIELD, {})
                    }
                return None

        except Exception as e:
            logger.error(f"[{match_id}] 验证失败: {e}")
            return None

    def get_missing_match_ids(self, expected_ids: List[str]) -> List[str]:
        """获取缺失的 match_id 列表

        Args:
            expected_ids: 预期的 match_id 列表

        Returns:
            数据库中不存在的 match_id 列表
        """
        try:
            with self.conn.cursor() as cur:
                placeholders = ",".join(["%s"] * len(expected_ids))
                cur.execute(
                    f"SELECT {self.MATCH_ID_FIELD} FROM {self.TABLE_NAME} "
                    f"WHERE {self.MATCH_ID_FIELD} IN ({placeholders})",
                    expected_ids
                )
                existing = {row[self.MATCH_ID_FIELD] for row in cur.fetchall()}
                missing = [mid for mid in expected_ids if mid not in existing]
                return missing

        except Exception as e:
            logger.error(f"获取缺失 ID 失败: {e}")
            return []

    def get_sync_statistics(self) -> Dict[str, Any]:
        """获取同步统计信息

        Returns:
            统计信息字典
        """
        try:
            with self.conn.cursor() as cur:
                # 总记录数（使用安全的标识符处理）
                query = psycopg2_sql.SQL("SELECT COUNT(*) as total FROM {}").format(
                    psycopg2_sql.Identifier(self.TABLE_NAME)
                )
                cur.execute(query)
                total = cur.fetchone()["total"]

                # 有 l2_raw_json 的记录数（使用安全的标识符处理）
                query = psycopg2_sql.SQL("SELECT COUNT(*) as count FROM {} WHERE {} IS NOT NULL").format(
                    psycopg2_sql.Identifier(self.TABLE_NAME),
                    psycopg2_sql.Identifier(self.L2_FIELD)
                )
                cur.execute(query)
                with_l2 = cur.fetchone()["count"]

                # 有 oddsportal 数据的记录数（使用安全的标识符处理）
                query = psycopg2_sql.SQL("SELECT COUNT(*) as count FROM {} WHERE {} -> %s IS NOT NULL").format(
                    psycopg2_sql.Identifier(self.TABLE_NAME),
                    psycopg2_sql.Identifier(self.L2_FIELD)
                )
                cur.execute(query, (self.ODDSPORTAL_KEY,))
                with_oddsportal = cur.fetchone()["count"]

                return {
                    "total_matches": total,
                    "with_l2_data": with_l2,
                    "with_oddsportal_data": with_oddsportal,
                    "l2_coverage": f"{with_l2/total*100:.2f}%" if total > 0 else "0%",
                    "oddsportal_coverage": f"{with_oddsportal/total*100:.2f}%" if total > 0 else "0%"
                }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def close(self) -> None:
        """关闭数据库连接"""
        if self._own_connection and self._conn and not self._conn.closed:
            self._conn.close()
            logger.debug("数据库连接已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ==============================================================================
# Convenience Functions
# ==============================================================================


def sync_scraped_result(scraped_data: Dict[str, Any], sync_mode: str = "merge") -> SyncResult:
    """便捷函数：同步单个采集结果

    Example:
        >>> from src.database.oddsportal_db_manager import sync_scraped_result
        >>> result = sync_scraped_result(scraped_data)
        >>> print(f"成功: {result.success}")
    """
    with OddsPortalDBManager() as db:
        return db.sync_match_data(scraped_data, sync_mode)


def sync_scraped_batch(scraped_results: List[Dict[str, Any]], sync_mode: str = "merge") -> BatchSyncResult:
    """便捷函数：批量同步采集结果

    Example:
        >>> from src.database.oddsportal_db_manager import sync_scraped_batch
        >>> batch_result = sync_scraped_batch(results)
        >>> print(f"成功: {batch_result.successful}/{batch_result.total}")
    """
    with OddsPortalDBManager() as db:
        return db.sync_batch(scraped_results, sync_mode)
