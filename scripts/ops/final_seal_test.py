#!/usr/bin/env python3
"""
V41.122 "终极封测" - 全链路闭环验证脚本

核心功能:
1. Scout 阶段: 发现 5 场英超比赛 ID
2. Core 阶段: 调用重构后的 backfill_missing_features()
3. 断言验证: 检查 home_team_id 和 technical_features

Author: 首席 DevOps 工程师
Version: V41.122
Date: 2026-01-17
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import psycopg2
from psycopg2.extras import RealDictCursor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_connection():
    """获取数据库连接（使用统一配置）"""
    from src.config_unified import get_config

    config = get_config()
    db = config.database

    return psycopg2.connect(
        host=db.host,
        port=db.port,
        database=db.name,
        user=db.user,
        password=db.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )


def scout_premier_league_matches(limit: int = 5) -> list[str]:
    """
    Scout 阶段: 发现英超比赛 ID

    Args:
        limit: 最多返回的比赛数量

    Returns:
        match_id 列表
    """
    conn = get_database_connection()

    try:
        with conn.cursor() as cur:
            # 查询英超 2024/2025 赛季的比赛
            cur.execute("""
                SELECT match_id
                FROM matches
                WHERE league_name = 'Premier League'
                  AND season = '2024/2025'
                ORDER BY match_date DESC
                LIMIT %s
            """, (limit,))

            rows = cur.fetchall()
            match_ids = [row['match_id'] for row in rows]

            logger.info(f"🔍 Scout 阶段: 发现 {len(match_ids)} 场英超比赛")
            for i, match_id in enumerate(match_ids, 1):
                logger.info(f"   [{i}] {match_id}")

            return match_ids

    finally:
        conn.close()


def core_backfill_phase(match_ids: list[str]) -> dict:
    """
    Core 阶段: 调用重构后的 backfill_missing_features()

    Args:
        match_ids: 比赛 ID 列表

    Returns:
        回补结果字典
    """
    from src.api.collectors.fotmob_core import FotMobCoreCollector

    logger.info("=" * 60)
    logger.info("⚙️  Core 阶段: 调用 backfill_missing_features()")
    logger.info("=" * 60)

    collector = FotMobCoreCollector()

    result = collector.backfill_missing_features(
        match_ids=match_ids,
        concurrent_workers=3,
        dry_run=False
    )

    return result


def verify_backfill_results(match_ids: list[str]) -> dict:
    """
    断言验证: 检查数据库记录

    Args:
        match_ids: 比赛 ID 列表

    Returns:
        验证结果字典
    """
    conn = get_database_connection()

    try:
        with conn.cursor() as cur:
            results = {
                "total": len(match_ids),
                "with_home_team_id": 0,
                "with_technical_features": 0,
                "with_xg_data": 0,
                "details": []
            }

            for match_id in match_ids:
                cur.execute("""
                    SELECT
                        match_id,
                        home_team_id,
                        away_team_id,
                        technical_features,
                        COALESCE(
                            technical_features->>'home_xg',
                            technical_features->'home'->>'xg'
                        ) as home_xg
                    FROM matches
                    WHERE match_id = %s
                """, (match_id,))

                row = cur.fetchone()

                if row:
                    detail = {
                        "match_id": match_id,
                        "has_home_team_id": row['home_team_id'] is not None,
                        "has_technical_features": row['technical_features'] is not None,
                        "has_xg": row['home_xg'] is not None,
                        "home_xg": row['home_xg']
                    }
                    results["details"].append(detail)

                    if detail["has_home_team_id"]:
                        results["with_home_team_id"] += 1
                    if detail["has_technical_features"]:
                        results["with_technical_features"] += 1
                    if detail["has_xg"]:
                        results["with_xg_data"] += 1

        return results

    finally:
        conn.close()


def print_verification_report(results: dict) -> bool:
    """
    打印验证报告

    Args:
        results: 验证结果字典

    Returns:
        是否全部通过验证
    """
    logger.info("=" * 60)
    logger.info("📊 验证报告")
    logger.info("=" * 60)

    total = results["total"]
    with_home_team_id = results["with_home_team_id"]
    with_technical_features = results["with_technical_features"]
    with_xg = results["with_xg_data"]

    logger.info(f"总比赛数: {total}")
    logger.info(f"✅ 有 home_team_id: {with_home_team_id}/{total}")
    logger.info(f"✅ 有 technical_features: {with_technical_features}/{total}")
    logger.info(f"✅ 有 xG 数据: {with_xg}/{total}")

    logger.info("")
    logger.info("详细结果:")
    for detail in results["details"]:
        status = "✅" if detail["has_xg"] else "❌"
        logger.info(f"  {status} {detail['match_id']}: "
                   f"home_team_id={detail['has_home_team_id']}, "
                   f"features={detail['has_technical_features']}, "
                   f"xg={detail['home_xg']}")

    logger.info("=" * 60)

    # 判断是否全部通过
    all_passed = (
        with_home_team_id == total and
        with_technical_features == total and
        with_xg == total
    )

    if all_passed:
        logger.info("🎉 V41.122 终极封测: 全部通过！")
    else:
        logger.error("🚨 V41.122 终极封测: 部分验证失败！")

    return all_passed


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("V41.122 终极封测 - 全链路闭环验证")
    logger.info("=" * 60)
    logger.info(f"开始时间: {datetime.now().isoformat()}")

    try:
        # 阶段 1: Scout
        logger.info("")
        match_ids = scout_premier_league_matches(limit=5)

        if not match_ids:
            logger.error("🚨 Scout 阶段失败: 未发现任何比赛")
            return 1

        # 阶段 2: Core
        logger.info("")
        backfill_result = core_backfill_phase(match_ids)

        logger.info("")
        logger.info("回补结果:")
        logger.info(f"  成功: {backfill_result['successful']}")
        logger.info(f"  失败: {backfill_result['failed']}")
        logger.info(f"  含特征: {backfill_result['with_features']}")
        logger.info(f"  无特征: {backfill_result['without_features']}")

        # 阶段 3: Verify
        logger.info("")
        verify_results = verify_backfill_results(match_ids)
        all_passed = print_verification_report(verify_results)

        logger.info("")
        logger.info(f"结束时间: {datetime.now().isoformat()}")

        return 0 if all_passed else 1

    except Exception as e:
        logger.exception(f"💥 终极封测异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
