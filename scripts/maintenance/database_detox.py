#!/usr/bin/env python3
"""
V53.0 数据库"排毒"脚本
=====================

识别并标记 prematch_features 表中的污染赔率数据。
污染定义：返还率 > 100% 的记录，即 1/H + 1/D + 1/A < 1.0

Author: Senior Data Engineer
Date: 2026-01-01
"""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_unified import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    settings = get_settings()

    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Step 1: 检查是否已存在 is_polluted 字段
            logger.info("Step 1: 检查表结构...")
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'prematch_features'
                AND column_name = 'is_polluted';
            """)

            if cur.fetchone():
                logger.info("is_polluted 字段已存在")
            else:
                # 添加 is_polluted 字段
                logger.info("添加 is_polluted 字段...")
                cur.execute("""
                    ALTER TABLE prematch_features
                    ADD COLUMN is_polluted BOOLEAN DEFAULT FALSE;
                """)
                conn.commit()
                logger.info("is_polluted 字段已添加")

            # Step 2: 识别污染数据
            logger.info("Step 2: 识别污染数据（返还率 > 100%）...")

            # 计算返还率并标记污染数据
            cur.execute("""
                UPDATE prematch_features
                SET is_polluted = TRUE
                WHERE closing_home_odds IS NOT NULL
                  AND closing_draw_odds IS NOT NULL
                  AND closing_away_odds IS NOT NULL
                  AND closing_home_odds > 0
                  AND closing_draw_odds > 0
                  AND closing_away_odds > 0
                  AND (1.0 / closing_home_odds +
                       1.0 / closing_draw_odds +
                       1.0 / closing_away_odds) < 0.97;  -- 返还率 > 103% 视为污染
            """)

            polluted_count = cur.rowcount
            conn.commit()
            logger.info(f"已标记 {polluted_count} 条污染记录")

            # Step 3: 统计污染数据
            logger.info("Step 3: 统计污染数据...")

            cur.execute("""
                SELECT
                    COUNT(*) as total_records,
                    SUM(CASE WHEN is_polluted = TRUE THEN 1 ELSE 0 END) as polluted_records,
                    SUM(CASE WHEN is_polluted = FALSE OR is_polluted IS NULL THEN 1 ELSE 0 END) as clean_records,
                    ROUND(AVG(CASE
                        WHEN closing_home_odds IS NOT NULL
                             AND closing_draw_odds IS NOT NULL
                             AND closing_away_odds IS NOT NULL
                        THEN (1.0 / closing_home_odds +
                              1.0 / closing_draw_odds +
                              1.0 / closing_away_odds)
                        ELSE NULL
                    END)::numeric, 4) as avg_implied_probability
                FROM prematch_features
                WHERE closing_home_odds IS NOT NULL;
            """)

            stats = cur.fetchone()
            logger.info("=== 数据库排毒统计 ===")
            logger.info(f"  总记录数（有赔率）: {stats['total_records']}")
            logger.info(f"  污染记录数: {stats['polluted_records']}")
            logger.info(f"  清洁记录数: {stats['clean_records']}")
            logger.info(f"  平均隐含概率: {stats['avg_implied_probability']}")
            logger.info(f"  污染比例: {stats['polluted_records'] / stats['total_records'] * 100:.2f}%")

            # Step 4: 展示污染数据样本
            logger.info("Step 4: 展示污染数据样本（前5条）...")

            cur.execute("""
                SELECT
                    pf.match_id,
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    pf.closing_home_odds,
                    pf.closing_draw_odds,
                    pf.closing_away_odds,
                    ROUND((1.0 / pf.closing_home_odds +
                          1.0 / pf.closing_draw_odds +
                          1.0 / pf.closing_away_odds)::numeric, 4) as implied_probability,
                    ROUND((100.0 / (
                        1.0 / pf.closing_home_odds +
                        1.0 / pf.closing_draw_odds +
                        1.0 / pf.closing_away_odds
                    ))::numeric, 2) as payout_rate
                FROM prematch_features pf
                JOIN matches m ON pf.match_id = m.match_id
                WHERE pf.is_polluted = TRUE
                ORDER BY pf.match_id
                LIMIT 5;
            """)

            samples = cur.fetchall()
            logger.info("\n污染数据样本:")
            logger.info("-" * 120)
            for sample in samples:
                logger.info(f"  Match {sample['match_id']}: {sample['home_team']} vs {sample['away_team']}")
                logger.info(f"    日期: {sample['match_date']}")
                logger.info(f"    赔率: H={sample['closing_home_odds']:.2f}, D={sample['closing_draw_odds']:.2f}, A={sample['closing_away_odds']:.2f}")
                logger.info(f"    隐含概率: {sample['implied_probability']:.4f}")
                logger.info(f"    返还率: {sample['payout_rate']:.2f}%")
                logger.info("")

            logger.info("=== 数据库排毒完成 ===")
            logger.info(f"已标记 {polluted_count} 条污染记录为 is_polluted=TRUE")
            logger.info("V53.0 真实赔率系统已准备就绪")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
