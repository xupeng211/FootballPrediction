#!/usr/bin/env python3
"""
V41.186 MatchAligner - 数据对齐逻辑审计
====================================================================

核心功能：
    - 从 aligned_matches 表拉取缺失赔率的比赛
    - 强制校验比赛时间，时差 > 2 小时标记为异常
    - ID 互信机制：FotMob ID + OddsPortal Hash 确认匹配

Usage:
    from src.services.match_aligner import MatchAligner

    aligner = MatchAligner()
    missing = await aligner.get_missing_odds_matches()
    aligned = await aligner.validate_alignment(match_id, oddsportal_hash)

Author: V41.186 Integration Team
Date: 2026-01-19
Version: V41.186 "终极缝合"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_config, get_database_url

logger = logging.getLogger("V41.186")


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class MatchAlignment:
    """比赛对齐数据"""
    match_id: str
    fotmob_id: str | None = None
    oddsportal_hash: str | None = None
    oddsportal_url: str | None = None
    fotmob_time: datetime | None = None
    oddsportal_time: datetime | None = None
    time_diff_hours: float | None = None
    time_valid: bool = True
    alignment_confidence: float = 0.0
    notes: str = ""

    def is_valid(self) -> bool:
        """检查对齐是否有效"""
        return (
            self.match_id and
            self.oddsportal_hash and
            self.time_valid and
            self.alignment_confidence >= 0.7
        )


@dataclass
class MissingOddsMatch:
    """缺失赔率的比赛"""
    match_id: str
    league_name: str
    season: str
    home_team: str
    away_team: str
    match_time: datetime
    has_hash: bool
    has_url: bool

    def needs_harvest(self) -> bool:
        """检查是否需要收割赔率"""
        return self.has_hash or self.has_url


# =============================================================================
# MatchAligner - 核心对齐引擎
# =============================================================================

class MatchAligner:
    """V41.186 比赛对齐器 - 数据源对齐审计"""

    # 时差阈值（小时）
    TIME_DIFF_THRESHOLD = 2.0

    # 置信度阈值
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self):
        self.config = get_config()
        self._conn = None

    def _get_connection(self):
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(get_database_url())
        return self._conn

    def close(self):
        """关闭数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()

    # ========================================================================
    # 查询方法
    # ========================================================================

    def get_missing_odds_matches(self, limit: int | None = None) -> list[MissingOddsMatch]:
        """
        获取缺失赔率的比赛列表

        查询逻辑：
            1. 从 matches 表（Source_F）中查找
            2. LEFT JOIN matches_mapping 表（Source_O）
            3. 筛选没有赔率数据的记录
        """
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT
                m.match_id,
                m.league_name,
                m.season,
                m.home_team,
                m.away_team,
                m.match_date,
                mm.oddsportal_hash IS NOT NULL AS has_hash,
                mm.oddsportal_url IS NOT NULL AS has_url
            FROM matches m
            LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
            WHERE 1=1
                AND (mm.oddsportal_hash IS NULL OR mm.oddsportal_url IS NULL)
                -- 确保比赛已经发生（有技术统计）
                AND m.technical_features IS NOT NULL
                -- 优先处理最近的数据
            ORDER BY m.match_date DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        try:
            cursor.execute(query)
            rows = cursor.fetchall()

            matches = []
            for row in rows:
                matches.append(MissingOddsMatch(
                    match_id=row['match_id'],
                    league_name=row['league_name'],
                    season=row['season'],
                    home_team=row['home_team'],
                    away_team=row['away_team'],
                    match_time=row['match_date'],
                    has_hash=row['has_hash'],
                    has_url=row['has_url']
                ))

            logger.info(f"📊 找到 {len(matches)} 场缺失赔率的比赛")
            return matches

        except Exception as e:
            logger.error(f"❌ 查询缺失赔率比赛失败: {e}")
            return []

    def validate_alignment(
        self,
        match_id: str,
        oddsportal_hash: str,
        oddsportal_time: datetime | None = None
    ) -> MatchAlignment:
        """
        验证比赛对齐

        检查项：
            1. match_id 是否存在于 matches 表
            2. oddsportal_hash 格式是否有效（8 字符）
            3. 比赛时间是否匹配（时差 < 2 小时）
        """
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 查询 FotMob 比赛数据
        query = """
            SELECT match_id, home_team, away_team, match_date, league_name, season
            FROM matches
            WHERE match_id = %s
        """

        try:
            cursor.execute(query, (match_id,))
            row = cursor.fetchone()

            if not row:
                return MatchAlignment(
                    match_id=match_id,
                    time_valid=False,
                    alignment_confidence=0.0,
                    notes="match_id 不存在于 matches 表"
                )

            fotmob_time = row['match_date']
            alignment = MatchAlignment(
                match_id=match_id,
                fotmob_id=match_id,
                oddsportal_hash=oddsportal_hash,
                fotmob_time=fotmob_time,
                oddsportal_time=oddsportal_time,
                notes=""
            )

            # 验证 hash 格式
            if not self._validate_hash_format(oddsportal_hash):
                alignment.time_valid = False
                alignment.notes += "Hash 格式无效；"
                alignment.alignment_confidence = 0.0
                return alignment

            # 验证时间
            if oddsportal_time:
                time_diff = abs((fotmob_time - oddsportal_time).total_seconds() / 3600)
                alignment.time_diff_hours = time_diff

                if time_diff > self.TIME_DIFF_THRESHOLD:
                    alignment.time_valid = False
                    alignment.notes += f"时差过大 ({time_diff:.1f}h > {self.TIME_DIFF_THRESHOLD}h)；"
                    alignment.alignment_confidence = max(0, 1.0 - (time_diff / 10))
                else:
                    alignment.alignment_confidence = 1.0 - (time_diff / self.TIME_DIFF_THRESHOLD) * 0.1

            # 如果没有提供时间，默认认为有效
            else:
                alignment.alignment_confidence = 0.9
                alignment.notes += "未提供 OddsPortal 时间；"

            # 检查是否已有对齐记录
            existing = self._check_existing_alignment(match_id, oddsportal_hash)
            if existing:
                alignment.notes += "已有对齐记录；"

            return alignment

        except Exception as e:
            logger.error(f"❌ 验证对齐失败: {e}")
            return MatchAlignment(
                match_id=match_id,
                oddsportal_hash=oddsportal_hash,
                time_valid=False,
                alignment_confidence=0.0,
                notes=f"验证失败: {str(e)}"
            )

    def _validate_hash_format(self, hash_value: str) -> bool:
        """验证 hash 格式（8 字符字母数字组合）"""
        if not hash_value:
            return False
        return len(hash_value) == 8 and hash_value.isalnum()

    def _check_existing_alignment(self, match_id: str, oddsportal_hash: str) -> bool:
        """检查是否已存在对齐记录"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT 1 FROM matches_mapping
            WHERE fotmob_id = %s AND oddsportal_hash = %s
        """

        cursor.execute(query, (match_id, oddsportal_hash))
        return cursor.fetchone() is not None

    # ========================================================================
    # 写入方法
    # ========================================================================

    def save_alignment(
        self,
        match_id: str,
        oddsportal_hash: str,
        oddsportal_url: str,
        mapping_method: str = "v41_186_auto",
        confidence: float = 1.0
    ) -> bool:
        """
        保存对齐记录到 matches_mapping 表

        使用 UPSERT 逻辑：
            - 如果记录存在，更新 confidence 和 updated_at
            - 如果不存在，插入新记录
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO matches_mapping (
                fotmob_id, oddsportal_hash, oddsportal_url, match_date,
                mapping_method, confidence, review_status
            ) VALUES (
                %s, %s, %s,
                (SELECT match_time FROM matches WHERE match_id = %s),
                %s, %s, 'approved'
            )
            ON CONFLICT (fotmob_id, oddsportal_hash)
            DO UPDATE SET
                oddsportal_url = EXCLUDED.oddsportal_url,
                confidence = EXCLUDED.confidence,
                updated_at = NOW(),
                review_status = 'approved'
        """

        try:
            cursor.execute(query, (
                match_id, oddsportal_hash, oddsportal_url, match_id,
                mapping_method, confidence
            ))
            conn.commit()

            logger.info(f"✅ 保存对齐记录: {match_id} -> {oddsportal_hash}")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ 保存对齐记录失败: {e}")
            return False

    # ========================================================================
    # 批量操作
    # ========================================================================

    def get_alignment_stats(self) -> dict[str, Any]:
        """获取对齐统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        stats = {}

        # 总比赛数
        cursor.execute("SELECT COUNT(*) as total FROM matches WHERE technical_features IS NOT NULL")
        stats['total_matches'] = cursor.fetchone()['total']

        # 有 hash 的数量
        cursor.execute("""
            SELECT COUNT(*) as count FROM matches m
            LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
            WHERE mm.oddsportal_hash IS NOT NULL
        """)
        stats['has_hash'] = cursor.fetchone()['count']

        # 缺失 hash 的数量
        stats['missing_hash'] = stats['total_matches'] - stats['has_hash']

        # 有赔率数据的数量
        cursor.execute("""
            SELECT COUNT(DISTINCT match_id) as count FROM odds
            WHERE bookmaker = 'Pinnacle' AND home_odds IS NOT NULL
        """)
        stats['has_odds'] = cursor.fetchone()['count']

        # 对齐率
        if stats['total_matches'] > 0:
            stats['alignment_rate'] = stats['has_hash'] / stats['total_matches'] * 100
        else:
            stats['alignment_rate'] = 0.0

        # 赔率覆盖率
        if stats['total_matches'] > 0:
            stats['odds_coverage'] = stats['has_odds'] / stats['total_matches'] * 100
        else:
            stats['odds_coverage'] = 0.0

        return stats


# =============================================================================
# 便捷函数
# =============================================================================

def get_match_aligner() -> MatchAligner:
    """获取 MatchAligner 实例"""
    return MatchAligner()


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    aligner = MatchAligner()

    # 获取统计
    stats = aligner.get_alignment_stats()
    print("\n📊 对齐统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 获取缺失赔率的比赛（前 10 场）
    print("\n🔍 缺失赔率的比赛（前 10 场）:")
    missing = aligner.get_missing_odds_matches(limit=10)
    for m in missing[:5]:
        print(f"  {m.match_id}: {m.home_team} vs {m.away_team} ({m.match_time.date()})")

    aligner.close()
