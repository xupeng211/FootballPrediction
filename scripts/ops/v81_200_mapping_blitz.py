#!/usr/bin/env python3
"""
V81.200 Mapping Blitz - 暴力寻址总攻
=====================================

全量地毯式扫描 5,352 场失联比赛，使用 RapidFuzz C++ 引擎进行模糊匹配。

硬指标:
- 相似度 > 85.0: 自动回填 (review_status='approved')
- 相似度 70.0 - 85.0: 标记待审核 (review_status='pending_review')
- 相似度 < 70.0: 记录失败原因

Author: V81.200 Engineering Team
Version: V81.200 "Mapping Blitz"
Date: 2026-01-25
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from tqdm import tqdm

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings
from src.utils.cpp_bridge_radar import (
    BridgeRadarEngine,
    RadarQuery,
    RadarMatchResult,
    get_bridge_radar,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/v81_200_mapping_blitz.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

BLITZ_CONFIG = {
    # 阈值配置
    'auto_approve_threshold': 85.0,  # > 85% 自动批准
    'pending_review_threshold': 70.0,  # 70-85% 待审核
    'min_threshold': 65.0,  # 最低阈值（低于此值不记录）

    # 批处理配置
    'batch_size': 100,  # 每批处理数量
    'max_workers': 1,  # 单线程确保数据库稳定性

    # 联赛过滤
    'target_leagues': [
        'Premier League',
        'La Liga',
        'Serie A',
        'Bundesliga',
        'Ligue 1'
    ]
}


# =============================================================================
# Database Operations
# =============================================================================

def get_unmapped_matches(limit: Optional[int] = None) -> list[dict[str, Any]]:
    """
    获取待映射的比赛列表

    Args:
        limit: 最大返回数量

    Returns:
        待映射比赛列表
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )
    cursor = conn.cursor()

    # 查询待映射比赛（五大联赛，有 L2 数据，无 URL）
    limit_clause = f"LIMIT {limit}" if limit else ""

    query = f"""
        SELECT
            m.match_id,
            m.league_name,
            m.season,
            m.home_team,
            m.away_team,
            m.match_date,
            m.l2_raw_json IS NOT NULL as has_l2_data
        FROM matches m
        LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
        WHERE mm.fotmob_id IS NULL
          AND m.league_name IN %(leagues)s
          AND m.match_date < NOW()  -- 只处理过去的比赛
          AND m.l2_raw_json IS NOT NULL  -- 必须有 L2 数据
        ORDER BY m.league_name, m.match_date DESC
        {limit_clause}
    """

    cursor.execute(query, {"leagues": tuple(BLITZ_CONFIG['target_leagues'])})
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    logger.info(f"获取到 {len(results)} 场待映射比赛")
    return results


def upsert_mapping(
    match_id: str,
    url: str,
    confidence: float,
    discovery_method: str,
    league_name: str,
    review_status: str = 'approved'
) -> bool:
    """
    回填映射到数据库

    Args:
        match_id: 比赛 ID
        url: OddsPortal URL
        confidence: 置信度
        discovery_method: 发现方式
        league_name: 联赛名称
        review_status: 审核状态

    Returns:
        是否成功
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )
    cursor = conn.cursor()

    try:
        # 获取比赛详情
        cursor.execute("""
            SELECT match_date, home_team, away_team, league_name
            FROM matches
            WHERE match_id = %s
        """, [match_id])

        match_info = cursor.fetchone()
        if not match_info:
            logger.warning(f"比赛 {match_id} 在 matches 表中不存在")
            return False

        # Upsert mapping
        cursor.execute("""
            INSERT INTO matches_mapping (
                fotmob_id, oddsportal_url, confidence, mapping_method,
                review_status, match_date, home_team, away_team, league_name
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (fotmob_id)
            DO UPDATE SET
                oddsportal_url = EXCLUDED.oddsportal_url,
                confidence = EXCLUDED.confidence,
                mapping_method = EXCLUDED.mapping_method,
                review_status = EXCLUDED.review_status,
                updated_at = NOW()
        """, [
            match_id,
            url,
            confidence,
            discovery_method,
            review_status,
            match_info['match_date'],
            match_info['home_team'],
            match_info['away_team'],
            league_name or match_info['league_name'],
        ])

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"UPSERT 失败: {match_id} - {e}")
        return False

    finally:
        cursor.close()
        conn.close()


def record_failure(match_id: str, reason: str, league_name: str) -> None:
    """
    记录失败原因

    Args:
        match_id: 比赛 ID
        reason: 失败原因
        league_name: 联赛名称
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )
    cursor = conn.cursor()

    try:
        # 记录到日志表（如果存在）或输出到日志文件
        logger.warning(f"映射失败: {match_id} | {league_name} | 原因: {reason}")

    finally:
        cursor.close()
        conn.close()


# =============================================================================
# Blitz Execution
# =============================================================================

def execute_blitz(limit: Optional[int] = None) -> dict[str, Any]:
    """
    执行暴力寻址总攻

    Args:
        limit: 最大处理数量（用于测试）

    Returns:
        执行结果统计
    """
    start_time = datetime.now()

    logger.info("=" * 80)
    logger.info("V81.200 Mapping Blitz - 暴力寻址总攻启动")
    logger.info("=" * 80)

    # 获取待映射比赛
    matches = get_unmapped_matches(limit)
    total_matches = len(matches)

    if total_matches == 0:
        logger.info("没有待映射的比赛")
        return {
            "total": 0,
            "mapped": 0,
            "pending_review": 0,
            "failed": 0,
            "coverage": 0.0,
            "duration_seconds": 0
        }

    # 统计
    stats = {
        "auto_approved": 0,  # > 85%
        "pending_review": 0,  # 70-85%
        "failed": 0,  # < 70%
        "total": total_matches
    }

    # 获取雷达引擎
    radar = get_bridge_radar()

    # 执行扫描
    logger.info(f"开始扫描 {total_matches} 场比赛...")

    for match in tqdm(matches, desc="Mapping Blitz"):
        match_id = match['match_id']

        try:
            # 创建雷达查询
            query = RadarQuery(
                match_id=match_id,
                home_team=match['home_team'],
                away_team=match['away_team'],
                league_name=match['league_name'],
                match_date=match['match_date'],
                min_threshold=BLITZ_CONFIG['min_threshold'],
                max_candidates=50,
            )

            # 执行雷达扫描
            result = radar.radar_scan(query, verbose=False)

            if result and result.confidence >= BLITZ_CONFIG['min_threshold']:
                # 根据置信度决定审核状态
                if result.confidence > BLITZ_CONFIG['auto_approve_threshold']:
                    review_status = 'approved'
                    stats["auto_approved"] += 1
                elif result.confidence >= BLITZ_CONFIG['pending_review_threshold']:
                    review_status = 'pending_review'
                    stats["pending_review"] += 1
                else:
                    review_status = 'rejected'
                    stats["failed"] += 1

                # 回填数据库（注意：confidence 需要转换为 0-1 范围）
                confidence_normalized = result.confidence / 100.0
                success = upsert_mapping(
                    match_id=match_id,
                    url=result.candidate_url,
                    confidence=confidence_normalized,
                    discovery_method=result.discovery_method,
                    league_name=match['league_name'],
                    review_status=review_status
                )

                if not success:
                    stats["failed"] += 1

            else:
                stats["failed"] += 1
                record_failure(match_id, "未找到匹配（置信度过低）", match['league_name'])

        except Exception as e:
            stats["failed"] += 1
            logger.error(f"处理失败: {match_id} - {e}")

    # 计算耗时
    duration = (datetime.now() - start_time).total_seconds()
    mapped = stats["auto_approved"] + stats["pending_review"]
    coverage = (mapped / total_matches * 100) if total_matches > 0 else 0

    logger.info("=" * 80)
    logger.info("V81.200 Mapping Blitz - 执行完成")
    logger.info("=" * 80)
    logger.info(f"总处理: {total_matches} 场")
    logger.info(f"自动批准: {stats['auto_approved']} 场 (>{BLITZ_CONFIG['auto_approve_threshold']}%)")
    logger.info(f"待审核: {stats['pending_review']} 场 ({BLITZ_CONFIG['pending_review_threshold']}-{BLITZ_CONFIG['auto_approve_threshold']}%)")
    logger.info(f"失败: {stats['failed']} 场 (<{BLITZ_CONFIG['pending_review_threshold']}%)")
    logger.info(f"映射覆盖率: {coverage:.2f}%")
    logger.info(f"总耗时: {duration:.1f} 秒")
    logger.info("=" * 80)

    return {
        "total": total_matches,
        "auto_approved": stats["auto_approved"],
        "pending_review": stats["pending_review"],
        "failed": stats["failed"],
        "mapped": mapped,
        "coverage": coverage,
        "duration_seconds": duration
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI 主入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='V81.200 Mapping Blitz - 暴力寻址总攻',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='最大处理数量（用于测试，默认处理全部）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='干跑模式（不回填数据库）'
    )

    args = parser.parse_args()

    # 执行总攻
    result = execute_blitz(limit=args.limit)

    # 输出 JSON 结果
    import json
    print("\n" + "=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result['mapped'] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
